import asyncio
import logging
import re
from datetime import date

from sqlalchemy import select

from maxapi import Dispatcher, F
from maxapi.filters.command import CommandStart
from maxapi.types import ButtonsPayload, CallbackButton, MessageCreated
from maxapi.context import BaseContext, State, StatesGroup

from data_fetching import rmsp_client
from databases.businesses_db import Business
from databases.engine_start import SessionLocal
from databases.users_db import User
from notifications.worker import process_egrul

logger = logging.getLogger(__name__)

dp = Dispatcher()


class OrderState(StatesGroup):
    waiting_for_inn = State()


def is_valid_inn(inn: str) -> bool:
    """Проверяет формат и контрольные суммы ИНН (10 цифр — юрлицо, 12 — физлицо/ИП)."""
    if not re.fullmatch(r"\d{10}|\d{12}", inn):
        return False

    digits = [int(d) for d in inn]

    def checksum(coefficients: tuple[int, ...]) -> int:
        return sum(c * d for c, d in zip(coefficients, digits)) % 11 % 10

    if len(inn) == 10:
        return checksum((2, 4, 10, 3, 5, 9, 4, 6, 8)) == digits[9]

    return (
        checksum((7, 2, 4, 10, 3, 5, 9, 4, 6, 8)) == digits[10]
        and checksum((3, 7, 2, 4, 10, 3, 5, 9, 4, 6, 8)) == digits[11]
    )


SUBJECT_TYPE_RU = {"UL": "юридическое лицо", "IP": "ИП"}
CATEGORY_RU = {1: "микропредприятие", 2: "малое предприятие", 3: "среднее предприятие"}


def _company_summary(record: rmsp_client.RmspRecord) -> str:
    lines = [
        f"Нашли по ИНН {record.inn} в реестре МСП:",
        record.name,
        SUBJECT_TYPE_RU.get(record.subject_type, record.subject_type),
        f"Категория: {CATEGORY_RU.get(record.category, 'нет данных')}",
        f"ОГРН: {record.ogrn}",
        f"Осн. вид деятельности: {record.main_activity_code} — {record.main_activity_name}",
        f"Регион (код): {record.region_code}",
    ]
    if record.phone:
        lines.append(f"Телефон: {record.phone}")
    if record.email:
        lines.append(f"Email: {record.email}")
    if record.website:
        lines.append(f"Сайт: {record.website}")
    lines.append("")
    lines.append("Если что-то из этого неверно — поправьте кнопкой ниже:")
    return "\n".join(lines)


def _correction_keyboard():
    return ButtonsPayload(
        buttons=[
            [CallbackButton(text="Название", payload="fix:name")],
            [CallbackButton(text="ОКВЭД", payload="fix:okved")],
            [CallbackButton(text="Регион", payload="fix:region")],
            [CallbackButton(text="Контакты", payload="fix:contacts")],
        ]
    ).pack()


async def _save_business(max_user_id: int, sender, inn: str, record: rmsp_client.RmspRecord) -> None:
    async with SessionLocal() as db:
        result = await db.execute(select(User).where(User.max_user_id == max_user_id))
        user = result.scalar_one_or_none()
        if user is None:
            user = User(max_user_id=max_user_id)
            db.add(user)
        user.username = sender.username
        user.first_name = sender.first_name
        user.last_name = sender.last_name
        user.inn = inn

        business = await db.get(Business, inn)
        if business is None:
            business = Business(inn=inn)
            db.add(business)
        business.name = record.name
        business.subject_type = record.subject_type
        business.category = record.category
        business.ogrn = record.ogrn
        business.main_activity_code = record.main_activity_code
        business.main_activity_name = record.main_activity_name
        business.region_code = record.region_code
        business.is_new = record.is_new
        business.date_registered = record.date_registered
        business.date_excluded = record.date_excluded
        business.phone = record.phone
        business.email = record.email
        business.website = record.website
        business.has_licenses = record.has_licenses
        business.is_hitech = record.is_hitech
        business.is_partnership = record.is_partnership
        business.is_social = record.is_social

        await db.commit()


def _on_radar_done(task: asyncio.Task) -> None:
    if not task.cancelled() and task.exception() is not None:
        logger.error("Radar processing failed", exc_info=task.exception())


def _start_radar(inn: str) -> None:
    task = asyncio.create_task(process_egrul(inn, date.today()))
    task.add_done_callback(_on_radar_done)


# /start
@dp.message_created(CommandStart())
async def hello(event: MessageCreated, context: BaseContext):
    await context.set_state(OrderState.waiting_for_inn)
    await event.message.answer("Введите свой ИНН:")


@dp.message_created(F.message.body.text == "привет")
async def on_hello(event: MessageCreated):
    await event.message.answer("Привет!")


@dp.message_created(states=OrderState.waiting_for_inn)
async def on_inn(event: MessageCreated, context: BaseContext):
    # inn = (event.message.body.text or "").strip()
    inn = event.message.body.text.strip()

    if not is_valid_inn(inn):
        # пришел некорректный ИНН
        await event.message.answer(
            "Некорректный ИНН. Введите 10 цифр (для организации) "
            "или 12 цифр (для ИП/физлица) без пробелов:"
        )
        return

    if event.message.sender is None:
        return

    record = await asyncio.to_thread(rmsp_client.fetch_by_inn, inn)
    if record is None:
        await event.message.answer(
            f"Компанию с ИНН {inn} не нашли в реестре МСП. "
            "Проверьте номер и отправьте его ещё раз:"
        )
        return

    # пришел корректный ИНН
    await _save_business(event.message.sender.user_id, event.message.sender, inn, record)
    _start_radar(inn)

    await context.set_state(None)
    await event.message.answer(
        _company_summary(record),
        attachments=[_correction_keyboard()],
    )
