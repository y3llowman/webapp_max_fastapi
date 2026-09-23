"""Отдельный процесс-планировщик (сервис `worker` в docker-compose: `python -m radar.worker`).
Не запускайте APScheduler внутри uvicorn с несколькими воркерами — задачи задвоятся.

Расписание (Europe/Moscow):
  03:00 ежедневно      sync_egrul        снимок ЕГРЮЛ → состояния + diff
  04:00 11-го числа    sync_msp          реестр МСП публикуется 10-го
  05:00 ежедневно      materialize       сроки на 60 дней вперёд + повторы критичных
  06:00 ежедневно      check_banks       «БАНКИНФОРМ» по ИНН + БИК из профиля
  07:00 ежедневно      ingest_laws       pravo.gov.ru → словарные правила → лента или модерация (law_ingest.py)
  сразу после модерации fan_out_feed     одобренный акт → run_feed() по всем профилям
  пн 04:30             check_inspections ЕРКНМ: плановые проверки по ИНН/ОГРН
  пн 05:30             check_certs       Росаккредитация: сроки сертификатов/деклараций по ИНН
  каждую минуту        dispatch          outbox → MAX (≤ 10 rps, лимит API 30 rps)
  09:00 понедельник    weekly_digest     сводка на 2 недели
"""
from __future__ import annotations

import asyncio
from dataclasses import asdict
from datetime import date, datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from ..data_fetching import egrul_client, rmsp_client
from . import detectors as det
from .deadlines import Profile, materialize as materialize_deadlines
from .planner import plan, tz_for

MSK = "Europe/Moscow"


# ---- точки интеграции с вашим кодом (TODO) ---------------------------------
async def fetch_egrul(inn: str) -> dict | None:
    extract = await asyncio.to_thread(egrul_client.get_extract, inn)
    return asdict(extract) if extract is not None else None


async def fetch_msp(inn: str) -> dict | None:
    record = await asyncio.to_thread(rmsp_client.fetch_by_inn, inn)
    return asdict(record) if record is not None else None


async def save_snapshot(inn, source, data) -> dict | None: ...  # вернуть ПРЕДЫДУЩИЙ снимок
async def upsert_events(inn, source, drafts) -> list: ...  # см. правила ключей в models.py
async def open_condition_keys(inn, source) -> dict[str, str]: ...  # {key: type} открытых состояний
async def close_conditions(inn, keys) -> list: ...         # resolved_at=now, вернуть закрытые
async def region_of(inn: str) -> str | None: ...           # businesses.region_code
async def schedule(event, slots) -> None: ...              # INSERT notifications ON CONFLICT DO NOTHING


async def process_egrul(inn: str, today: date) -> None:
    cur = await fetch_egrul(inn)
    if cur is None:
        return
    prev = await save_snapshot(inn, "egrul", cur)
    drafts = det.egrul_conditions(cur, today) + det.egrul_changes(prev, cur, today)
    new_events = await upsert_events(inn, "egrul", drafts)   # только реально новые
    gone = det.reconcile_conditions(await open_condition_keys(inn, "egrul"), drafts)
    closed = await close_conditions(inn, gone)               # + ON_RESOLVE → «отметка снята»
    now, tz = datetime.now(timezone.utc), tz_for(await region_of(inn))
    for ev in new_events:
        await schedule(ev, plan(ev.type, ev.due, now, tz))


async def sync_egrul() -> None:
    today = date.today()
    for inn in []:  # TODO: SELECT inn FROM businesses JOIN users WHERE is_active
        try:
            await process_egrul(inn, today)
        except Exception as e:  # один сбой не должен ронять весь прогон
            print("egrul sync failed", inn, e)
        await asyncio.sleep(2)  # бережём источник: ~30 запросов в минуту


async def sync_msp() -> None: ...      # аналогично: msp_conditions + msp_changes
async def materialize() -> None: ...   # Profile из businesses+business_profiles → materialize_deadlines
async def dispatch() -> None: ...      # SELECT … FOR UPDATE SKIP LOCKED; группировка сроков по дате
async def weekly_digest() -> None: ...
async def check_banks() -> None: ...        # det.bank_conditions
async def ingest_laws() -> None: ...        # law_ingest.run_daily
async def fan_out_feed(feed_id: int) -> None: ...  # вызывается из callback feed:<id>:approve
async def check_inspections() -> None: ...  # det.inspection_events
async def check_certs() -> None: ...        # det.cert_events


def build_scheduler() -> AsyncIOScheduler:
    s = AsyncIOScheduler(timezone=MSK)
    s.add_job(sync_egrul, CronTrigger(hour=3, minute=0, jitter=600), id="egrul", max_instances=1)
    s.add_job(sync_msp, CronTrigger(day=11, hour=4), id="msp", max_instances=1)
    s.add_job(materialize, CronTrigger(hour=5), id="deadlines", max_instances=1)
    s.add_job(dispatch, IntervalTrigger(minutes=1), id="dispatch", max_instances=1, coalesce=True)
    s.add_job(weekly_digest, CronTrigger(day_of_week="mon", hour=8, minute=55), id="digest")
    s.add_job(check_banks, CronTrigger(hour=6), id="banks", max_instances=1)
    s.add_job(ingest_laws, CronTrigger(hour=7), id="laws", max_instances=1)
    s.add_job(check_inspections, CronTrigger(day_of_week="mon", hour=4, minute=30), id="knm")
    s.add_job(check_certs, CronTrigger(day_of_week="mon", hour=5, minute=30), id="fsa")
    return s


if __name__ == "__main__":
    async def main():
        build_scheduler().start()
        await asyncio.Event().wait()
    asyncio.run(main())
