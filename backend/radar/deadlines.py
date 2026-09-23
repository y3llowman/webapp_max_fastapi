"""Профиль компании (то, чего нет в реестрах) и справочник налоговых режимов."""
from __future__ import annotations

from dataclasses import dataclass, field

REGIME_RU = {
    "osno": "ОСНО",
    "usn_income": "УСН доходы",
    "usn_ie": "УСН доходы минус расходы",
    "ausn": "АУСН",
    "psn": "патент (ПСН)",
}


@dataclass
class Profile:
    inn: str
    is_legal_entity: bool
    region_code: str | None = None
    okved_main: str | None = None
    okved_additional: tuple[str, ...] = ()
    msp_category: int | None = None
    tax_regime: str | None = None
    has_employees: bool | None = None
    hints: dict[str, str] = field(default_factory=dict)
    flags: dict[str, bool] = field(default_factory=dict)
