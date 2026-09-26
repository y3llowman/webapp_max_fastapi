import asyncio
import re
from dataclasses import asdict
from datetime import date

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.depends import get_current_business, get_current_user
from app.api.schemas import Company, Source
from data_fetching import rmsp_client
from databases import get_db
from databases.businesses_db import Business, save_business
from databases.users_db import User
from notifications.models import BusinessProfile, RegistrySnapshot
from notifications.worker import process_egrul, registry_loaded
from radar.deadlines import CATEGORY_RU, HEADCOUNT_RU, REGIME_RU, region_name

router = APIRouter(tags=["company"])


class ConnectRequest(BaseModel):
    inn: str = Field(pattern=r"^(\d{10}|\d{12})$")


async def to_company(db: AsyncSession, business: Business) -> Company:
    full_name = re.sub(r'"([^"]*)"', r"«\1»", business.name)  # ООО "МОСТАР" → ООО «МОСТАР»
    quoted = re.search(r"«[^»]*»", full_name)
    name = quoted.group(0) if quoted else full_name
    # режим и численность — из профиля радара, его заполняют ответы на вопросы бота
    profile = await db.get(BusinessProfile, business.inn)
    regime = REGIME_RU.get(profile.tax_regime) if profile else None
    headcount = profile.headcount if profile else None
    # КПП — из последней выписки ЕГРЮЛ, она скачивается в фоне после подключения
    egrul = (await db.execute(
        select(RegistrySnapshot.data)
        .where(RegistrySnapshot.inn == business.inn, RegistrySnapshot.source == "egrul")
        .order_by(RegistrySnapshot.id.desc()).limit(1)
    )).scalar_one_or_none() or {}
    return Company(
        name=name,
        full_name=full_name,
        initials="".join(word[0] for word in re.findall(r"\w+", name)[:2]).upper(),
        regime=regime or "Режим налогообложения не указан",
        inn=business.inn,
        kpp=egrul.get("kpp"),
        ogrn=business.ogrn,
        okved=f"{business.main_activity_code} — {business.main_activity_name}",
        category=CATEGORY_RU.get(business.category),
        headcount=HEADCOUNT_RU.get(headcount) if headcount is not None else None,
        region=region_name(business.region_code),
        needs_answers=regime is None or headcount is None,
        source=Source(name="Реестр МСП (ФНС)", demo=False, updated_at=business.updated_at.replace(microsecond=0)),
        counterparties=0,  # контрагентов пока не храним
    )


async def load_from_registry(db: AsyncSession, user: User, inn: str) -> Business:
    record = await asyncio.to_thread(rmsp_client.fetch_by_inn, inn)
    if record is None:
        raise HTTPException(status_code=404, detail="INN not found in the SME registry")
    business = await save_business(db, user.id, record)
    await registry_loaded(inn, asdict(record))
    return business


@router.get("/session", response_model=Company, response_model_exclude_none=True)
@router.get("/company", response_model=Company, response_model_exclude_none=True)
async def current_company(
    business: Business = Depends(get_current_business),
    db: AsyncSession = Depends(get_db),
):
    return await to_company(db, business)


@router.post("/session", response_model=Company, response_model_exclude_none=True)
async def connect_company(
    payload: ConnectRequest,
    background: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    business = await load_from_registry(db, user, payload.inn)
    # выписка ЕГРЮЛ (КПП, адрес, директор — для документов) скачивается медленно, поэтому в фоне
    background.add_task(process_egrul, business.inn, date.today())
    return await to_company(db, business)


@router.post("/company/refresh", response_model=Company, response_model_exclude_none=True)
async def refresh_company(
    business: Business = Depends(get_current_business),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await to_company(db, await load_from_registry(db, user, business.inn))
