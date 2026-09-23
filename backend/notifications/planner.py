"""Планирование окон отправки уведомлений (worker.schedule()).

TODO: реальная логика ("умные часы" 09:00-21:00 по местному времени, разброс
между remind_before из catalog.py) ещё не спроектирована. Здесь — заглушки,
чтобы process_egrul() отрабатывал целиком уже сейчас; schedule() в worker.py
тоже пока заглушка и результат plan() никуда не сохраняет.
"""
from __future__ import annotations

from datetime import date, datetime

DEFAULT_TZ = "Europe/Moscow"


def tz_for(region_code: str | None) -> str:
    return DEFAULT_TZ


def plan(event_type: str, due: date | None, now: datetime, tz: str) -> list:
    return []
