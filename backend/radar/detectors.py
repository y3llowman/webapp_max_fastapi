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
    """Ключи открытых состояний, которых детектор больше не видит, — их пора закрыть."""
    seen = {d.key for d in drafts}
    return [key for key in open_keys if key not in seen]


MSP_CATEGORY_RU = {1: "микропредприятие", 2: "малое предприятие", 3: "среднее предприятие"}
MSP_CONDITIONS = ("msp.not_found", "msp.excluded")


def msp_changes(inn: str, prev: dict | None, cur: dict | None, today: date) -> list[Draft]:
    """Снимки реестра МСП (asdict(RmspRecord), None — записи нет) → события.
    Открытые состояния msp.not_found / msp.excluded, которых больше нет в черновиках, worker закрывает."""
    if cur is None:
        return [Draft("msp.not_found", key=f"msp.not_found:{inn}", payload={"expected": None})]
    if cur.get("date_excluded"):
        return [Draft("msp.excluded", key=f"msp.excluded:{inn}", payload={"date_excluded": cur["date_excluded"]})]
    if not prev or prev.get("category") == cur["category"] or not prev.get("category"):
        return []
    old, new = prev["category"], cur["category"]
    payload = {"old": MSP_CATEGORY_RU.get(old, "нет данных"), "new": MSP_CATEGORY_RU.get(new, "нет данных"),
               "lost_micro": old == 1 and new > 1}
    due = None
    if payload["lost_micro"]:
        # ст. 309.2 ТК РФ: 4 месяца на локальные нормативные акты после выхода из микропредприятий
        due = add_months(today, 4)
        payload |= {"lna_due": due.isoformat(), "title": "Локальные нормативные акты", "period": "После смены категории МСП",
                    "what": "Утвердите правила внутреннего трудового распорядка, положение об оплате труда и другие ЛНА.",
                    "why": f"вы больше не микропредприятие: теперь {payload['new']}", "basis": "ст. 309.2 ТК РФ"}
    return [Draft("msp.category_changed", key=f"msp.category:{inn}:{old}-{new}:{today}", payload=payload, due=due)]
