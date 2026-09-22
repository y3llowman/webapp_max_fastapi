"""Лента изменений: законы, проекты, меры поддержки → кого касается → события.

Каждая запись ленты (FeedItem) несёт «таргетинг» Audience. Матчер сравнивает его
с профилем компании и возвращает уровень:
  direct   — все критерии известны и совпали → событие law.upcoming / support.open
  possible — часть признаков неизвестна → вопрос пользователю (profile.question)
  none     — точно не касается
Вопросы задаём не анкетой на старте, а тогда, когда ответ реально что-то открывает.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta

from .deadlines import REGIME_RU, Profile
from .detectors import Draft, _is_foreign

# ----------------------------------------------------------------- признаки и вопросы
FLAGS = {
    # признак: (вопрос пользователю, фраза «почему вам» при ответе «да»)
    "marketplace_seller": ("Вы продаёте через маркетплейсы (Wildberries, Ozon и т.п.)?", "продаёте через маркетплейсы"),
    "works_with_selfemployed": ("Вы работаете с самозанятыми исполнителями?", "работаете с самозанятыми"),
    "gov_procurement": ("Вы участвуете в госзакупках по 44-ФЗ?", "участвуете в госзакупках"),
    "vat_payer": ("Вы сейчас платите НДС?", "платите НДС"),
    "foreign_workers": ("У вас работают иностранные граждане (включая руководителя)?", "есть работники-иностранцы"),
    "cash_register": ("Вы принимаете оплату от покупателей через кассу (ККТ)?", "работаете с кассой"),
    "marked_goods": ("Вы продаёте или производите маркированные товары?", "работаете с маркировкой"),
}


def profile_hints(egrul: dict) -> dict[str, str]:
    """Что реестры подсказывают, но не доказывают — показываем в тексте вопроса."""
    hints = {}
    if _is_foreign(egrul.get("director")):
        hints["foreign_workers"] = "В ЕГРЮЛ руководитель — иностранный гражданин."
    okveds = [(egrul.get("okved_main") or {}).get("code", "")] + [o["code"] for o in egrul.get("okved_additional") or []]
    if any(c.startswith("47.91") for c in okveds):
        hints["marketplace_seller"] = "У вас есть ОКВЭД 47.91 (торговля через интернет)."
    return hints


# ----------------------------------------------------------------- лента
@dataclass(frozen=True)
class Audience:
    legal_forms: frozenset[str] | None = None      # {"le", "ip"}
    tax_regimes: frozenset[str] | None = None
    okved_prefixes: tuple[str, ...] | None = None
    regions: frozenset[str] | None = None
    msp_categories: frozenset[int] | None = None
    has_employees: bool | None = None
    flags: tuple[str, ...] = ()                    # все должны быть True (ручная разметка)
    any_flags: tuple[str, ...] = ()                # хотя бы один True (разметка по тексту акта)
    okved_main_only: bool = False                  # в тексте «основной вид деятельности»
    exclude_tax_regimes: frozenset[str] | None = None  # «за исключением … применяющих ПСН»


@dataclass(frozen=True)
class FeedItem:
    id: str
    kind: str                     # "law" | "general" (касается всех) | "draft" | "support"
    title: str
    summary: str                  # что меняется, 1–2 предложения
    actions: tuple[str, ...]      # что сделать
    act: str                      # реквизиты акта
    source_url: str
    effective_from: date | None
    audience: Audience
    status: str = "approved"      # pending_review → approved | rejected (модерация is_staff)
    official_url: str | None = None  # pravo.gov.ru; пока пусто — показываем «вторичный источник»
    documents: tuple[str, ...] = ()
    evidence: tuple[dict, ...] = ()  # цитаты из текста акта: {field, values, label, quote}


@dataclass
class Match:
    level: str                    # direct | possible | none
    reasons: list[str] = field(default_factory=list)
    unknown: list[str] = field(default_factory=list)
    fields: list[str] = field(default_factory=list)   # какие поля совпали — для выбора цитат
    flags_yes: list[str] = field(default_factory=list)


NONE = Match("none")


def match(p: Profile, a: Audience) -> Match:
    m = Match("direct")

    def known(name: str, value, ok: bool, reason: str) -> bool:
        if value is None:
            m.unknown.append(name)
            return True
        if ok:
            m.reasons.append(reason)
        return ok

    if a.legal_forms is not None:
        form = "le" if p.is_legal_entity else "ip"
        if form not in a.legal_forms:
            return NONE
        m.reasons.append("вы организация" if p.is_legal_entity else "вы ИП")
        m.fields.append("legal_forms")
    if a.exclude_tax_regimes and p.tax_regime in a.exclude_tax_regimes:
        return NONE
    if a.tax_regimes:
        if not known("tax_regime", p.tax_regime, p.tax_regime in a.tax_regimes,
                     f"режим {REGIME_RU.get(p.tax_regime or '', p.tax_regime)}"):
            return NONE
        m.fields.append("tax_regimes")
    if a.okved_prefixes:
        codes = [c for c in ((p.okved_main,) if a.okved_main_only else (p.okved_main, *p.okved_additional)) if c]
        hit = next((c for c in codes for pref in a.okved_prefixes if c.startswith(pref)), None)
        if not hit:
            return NONE
        m.reasons.append(f"ОКВЭД {hit} ({'основной, ' if hit == p.okved_main else ''}ЕГРЮЛ)")
        m.fields.append("okved_prefixes")
    if a.regions and not known("region", p.region_code, p.region_code in a.regions, f"регион {p.region_code}"):
        return NONE
    if a.msp_categories and not known("msp_category", p.msp_category, p.msp_category in a.msp_categories,
                                      "категория МСП (реестр)"):
        return NONE
    if a.has_employees is not None:
        if not known("has_employees", p.has_employees, p.has_employees == a.has_employees, "есть сотрудники"):
            return NONE
        m.fields.append("has_employees")
    for f in a.flags:
        if not known(f, p.flags.get(f), bool(p.flags.get(f)), FLAGS[f][1]):
            return NONE
        m.fields.append("flags")
    if a.any_flags:                              # OR: достаточно одного «да»
        yes = [f for f in a.any_flags if p.flags.get(f)]
        if yes:
            m.reasons += [FLAGS[f][1] for f in yes]
            m.fields.append("flags")
            m.flags_yes += yes
        else:
            unknown = [f for f in a.any_flags if p.flags.get(f) is None]
            if not unknown:
                return NONE                      # на всё ответили «нет»
            m.unknown += unknown
    if m.unknown:
        m.level = "possible"
    return m


def feed_events(item: FeedItem, p: Profile, today: date) -> list[Draft]:
    if item.status != "approved":
        return []
    if item.effective_from and item.effective_from < today - timedelta(days=30):
        return []                               # давно вступило — не новость
    m = match(p, item.audience)
    if m.level == "none":
        return []
    evidence = [e for e in item.evidence
                if (e["field"] != "flags" and e["field"] in m.fields)
                or (e["field"] == "flags" and any(f in m.flags_yes + m.unknown for f in e["values"]))][:3]
    base = {"item_id": item.id, "evidence": evidence, "title": item.title, "summary": item.summary, "actions": list(item.actions),
            "act": item.act, "source_url": item.official_url or item.source_url,
            "official": bool(item.official_url), "effective_from": item.effective_from,
            "reasons": m.reasons, "documents": list(item.documents)}
    if m.level == "direct":
        et = {"support": "support.open", "draft": "law.draft", "general": "law.general"}.get(item.kind, "law.upcoming")
        return [Draft(et, f"feed:{item.id}:{p.inn}", base,
                      due=item.effective_from if item.effective_from and item.effective_from >= today else None)]
    # possible: один вопрос на признак (общий для всех законов, которым он нужен) + запись в сводку
    out = [Draft("law.possible", f"feed:{item.id}:{p.inn}:possible", {**base, "unknown": m.unknown})]
    for f in m.unknown:
        if f in FLAGS:
            quote = next((e["quote"] for e in item.evidence if f in e.get("values", ())), None)
            out.append(Draft("profile.question", f"q:{p.inn}:{f}",
                             {"flag": f, "question": FLAGS[f][0], "hint": p.hints.get(f), "quote": quote,
                              "because": item.title, "effective_from": item.effective_from}))
    return out


def run_feed(items: list[FeedItem], p: Profile, today: date) -> list[Draft]:
    seen, out = set(), []
    for it in items:
        for d in feed_events(it, p, today):
            if d.key not in seen:                # вопросы по одному признаку склеиваются
                seen.add(d.key)
                out.append(d)
    return out
