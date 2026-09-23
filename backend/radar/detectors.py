"""Общие примитивы для детекторов событий: черновик события и мелкие проверки реестров."""
from __future__ import annotations

import calendar
from dataclasses import dataclass, field
from datetime import date


@dataclass
class Draft:
    """Черновик события до записи в БД (radar_events): что произошло и когда наступает срок."""
    type: str
    key: str
    payload: dict = field(default_factory=dict)
    due: date | None = None


def add_months(d: date, months: int) -> date:
    """Прибавляет months календарных месяцев к дате, обрезая день до последнего числа месяца."""
    month_index = d.month - 1 + months
    year = d.year + month_index // 12
    month = month_index % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def _is_foreign(director: dict | None) -> bool:
    """True, если гражданство директора (ЕГРЮЛ) указано и это не Россия."""
    citizenship = (director or {}).get("citizenship") or ""
    return bool(citizenship) and "росси" not in citizenship.lower()


# TODO: настоящие признаки (недостоверность, дисквалификация, ликвидация/предстоящее
# исключение) требуют уточнения формулировок ЕГРЮЛ и доработки egrul_client -
# парсер PDF сейчас явно пропускает раздел "Сведения о записях..." (история/статус
# записей), где как раз и видна ликвидация/исключение. Пока не детектируем ничего,
# чтобы worker.process_egrul() отрабатывал целиком, не выдавая ложных срабатываний.
def egrul_conditions(cur: dict, today: date) -> list[Draft]:
    return []


def egrul_changes(prev: dict | None, cur: dict, today: date) -> list[Draft]:
    return []


def reconcile_conditions(open_keys: dict[str, str], drafts: list[Draft]) -> list[str]:
    return []
