"""Normalizácia množstva, jednotiek a jednotkovej ceny.

Jednotková cena sa ukladá ako generated column v DB; `unit_price()` tu slúži
len validátoru (plauzibilita) a musí dávať rovnaký výsledok ako UNIT_PRICE_SQL.
"""

import re
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

UNIT_ALIASES = {
    "g": "g",
    "gr": "g",
    "gram": "g",
    "gramů": "g",
    "kg": "kg",
    "ml": "ml",
    "cl": "cl",  # prevedie sa na ml
    "l": "l",
    "lt": "l",
    "litr": "l",
    "litrů": "l",
    "ks": "ks",
    "kus": "ks",
    "kusů": "ks",
    "kusy": "ks",
    "pcs": "ks",
}

_NUM = r"(\d+(?:[.,]\d+)?)"
_UNIT = r"(kg|g|gr|ml|cl|l|lt|ks|kus[yů]?)"
# "4 x 100 g", "4x100g"
_MULTI_RE = re.compile(rf"(\d+)\s*[x×]\s*{_NUM}\s*{_UNIT}\b", re.IGNORECASE)
# "250 g", "1,5 l"
_SINGLE_RE = re.compile(rf"{_NUM}\s*{_UNIT}\b", re.IGNORECASE)


def to_decimal(value: object) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value).replace(",", ".").strip())
    except (InvalidOperation, ValueError):
        return None


def normalize_unit(unit: str | None, quantity: Decimal | None) -> tuple[Decimal | None, str | None]:
    """Vráti (quantity, unit) v enume g/kg/ml/l/ks; neznáma jednotka → (quantity, None)."""
    if unit is None:
        return quantity, None
    u = UNIT_ALIASES.get(unit.strip().lower().rstrip("."))
    if u == "cl":
        return (quantity * 10 if quantity is not None else None), "ml"
    return quantity, u


def parse_quantity(text: str) -> tuple[Decimal | None, str | None, int | None]:
    """Z textu typu 'Madeta tvaroh 250 g' alebo '4x100 g' vytiahne (quantity, unit, pack_count)."""
    m = _MULTI_RE.search(text)
    if m:
        qty, unit = normalize_unit(m.group(3), to_decimal(m.group(2)))
        return qty, unit, int(m.group(1))
    m = _SINGLE_RE.search(text)
    if m:
        qty, unit = normalize_unit(m.group(2), to_decimal(m.group(1)))
        return qty, unit, None
    return None, None, None


def unit_price(
    price: Decimal, quantity: Decimal | None, unit: str | None, pack_count: int | None, price_type: str
) -> tuple[Decimal | None, str | None]:
    """Zrkadlo UNIT_PRICE_SQL: (cena, základ kg/l/ks)."""
    if price_type == "per_kg":
        return price, "kg"
    if unit is None or quantity is None or quantity <= 0:
        return None, None
    total = quantity * (pack_count or 1)
    if unit in ("g", "ml"):
        value = price * 1000 / total
    else:
        value = price / total
    basis = {"g": "kg", "kg": "kg", "ml": "l", "l": "l", "ks": "ks"}[unit]
    # PG round(numeric) zaokrúhľuje half-away-from-zero = HALF_UP pre kladné čísla
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP), basis


def normalize_name(name: str) -> str:
    return re.sub(r"\s+", " ", name).strip()
