"""Deterministický validátor ponúk (kap. 5).

reject  → ponuka sa neuloží ako ponuka, len ako validation_event
review  → uloží sa so status='review' (nie je vo vyhľadávaní) a ide do review queue
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from app.ingestion.normalize import normalize_name, normalize_unit, parse_quantity, to_decimal, unit_price
from app.ingestion.schema import ExtractedOffer
from app.models import UNITS

MAX_PRICE_CHANGE = Decimal("0.60")
# hrubá globálna plauzibilita, kým nie sú kategórie (Kč za kg / l / ks)
GLOBAL_UNIT_PRICE_MAX = Decimal("20000")
LOW_CONFIDENCE = Decimal("0.5")


@dataclass
class Issue:
    severity: str  # reject | review
    code: str
    message: str


@dataclass
class NormalizedOffer:
    raw_name: str
    brand: str | None
    price: Decimal | None
    regular_price: Decimal | None
    quantity: Decimal | None
    unit: str | None
    pack_count: int | None
    price_type: str
    valid_from: date
    valid_to: date
    bbox: list[float] | None
    confidence: Decimal | None
    conditions: list[tuple[str, dict | None]] = field(default_factory=list)
    unit_price: Decimal | None = None
    unit_price_basis: str | None = None


@dataclass
class ValidationResult:
    offer: NormalizedOffer
    issues: list[Issue]

    @property
    def status(self) -> str:
        if any(i.severity == "reject" for i in self.issues):
            return "rejected"
        if any(i.severity == "review" for i in self.issues):
            return "review"
        return "active"


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _conditions(o: ExtractedOffer) -> list[tuple[str, dict | None]]:
    c = o.conditions
    out: list[tuple[str, dict | None]] = []
    if c.loyalty_card:
        out.append(("loyalty_card", {"program": c.loyalty_program} if c.loyalty_program else None))
    if c.min_qty:
        out.append(("min_qty", {"min_qty": c.min_qty}))
    if c.multibuy_buy or c.multibuy_get:
        out.append(("multibuy", {"buy": c.multibuy_buy, "get": c.multibuy_get}))
    if c.app_only:
        out.append(("app_only", None))
    if c.coupon:
        out.append(("coupon", None))
    return out


def validate_offer(
    extracted: ExtractedOffer,
    flyer_from: date,
    flyer_to: date,
    last_price: Callable[[NormalizedOffer], Decimal | None] | None = None,
    unit_price_range: tuple[Decimal | None, Decimal | None] | None = None,
) -> ValidationResult:
    issues: list[Issue] = []

    price = to_decimal(extracted.price)
    regular = to_decimal(extracted.regular_price)
    if price is not None:
        price = price.quantize(Decimal("0.01"))
    if regular is not None:
        regular = regular.quantize(Decimal("0.01"))

    quantity = to_decimal(extracted.quantity)
    unit = extracted.unit
    pack_count = extracted.pack_count
    if unit is not None:
        quantity, unit = normalize_unit(unit, quantity)
    if quantity is None or unit is None:
        # fallback: regex z názvu
        q, u, p = parse_quantity(extracted.raw_name)
        if q is not None and u is not None:
            quantity, unit, pack_count = q, u, pack_count or p
    if pack_count is not None and pack_count < 1:
        pack_count = None

    valid_from = _parse_date(extracted.valid_from) or flyer_from
    valid_to = _parse_date(extracted.valid_to) or flyer_to

    confidence = to_decimal(extracted.confidence)
    bbox = extracted.bbox if len(extracted.bbox) == 4 else None

    offer = NormalizedOffer(
        raw_name=normalize_name(extracted.raw_name),
        brand=normalize_name(extracted.brand) if extracted.brand else None,
        price=price,
        regular_price=regular,
        quantity=quantity,
        unit=unit,
        pack_count=pack_count,
        price_type=extracted.price_type,
        valid_from=valid_from,
        valid_to=valid_to,
        bbox=bbox,
        confidence=confidence.quantize(Decimal("0.01")) if confidence is not None else None,
        conditions=_conditions(extracted),
    )

    # --- tvrdé chyby
    if not offer.raw_name:
        issues.append(Issue("reject", "missing_name", "Chýba názov produktu"))
    if price is None:
        issues.append(Issue("reject", "missing_price", "Chýba cena"))
    elif price <= 0:
        issues.append(Issue("reject", "non_positive_price", f"Cena {price} ≤ 0"))
    if valid_from > valid_to:
        issues.append(Issue("reject", "invalid_validity", f"valid_from {valid_from} > valid_to {valid_to}"))

    if any(i.severity == "reject" for i in issues):
        return ValidationResult(offer, issues)
    assert price is not None

    # --- review
    if regular is not None and regular < price:
        issues.append(Issue("review", "regular_below_price", f"Bežná cena {regular} < akciová {price}"))
    if unit is not None and unit not in UNITS:
        issues.append(Issue("review", "invalid_unit", f"Jednotka {unit} mimo enumu"))
    if valid_from < flyer_from or valid_to > flyer_to:
        issues.append(
            Issue(
                "review",
                "validity_outside_flyer",
                f"Platnosť {valid_from}–{valid_to} mimo letáku {flyer_from}–{flyer_to}",
            )
        )
    if bbox is None:
        issues.append(Issue("review", "missing_bbox", "Chýba výrez ponuky (dôkaz)"))
    if confidence is not None and confidence < LOW_CONFIDENCE:
        issues.append(Issue("review", "low_confidence", f"Nízka istota modelu {confidence}"))

    offer.unit_price, offer.unit_price_basis = unit_price(price, quantity, unit, pack_count, offer.price_type)
    if offer.unit_price is not None:
        lo, hi = unit_price_range or (None, None)
        if offer.unit_price > (hi or GLOBAL_UNIT_PRICE_MAX) or (lo is not None and offer.unit_price < lo):
            issues.append(
                Issue(
                    "review",
                    "implausible_unit_price",
                    f"Jednotková cena {offer.unit_price} Kč/{offer.unit_price_basis}",
                )
            )

    if last_price is not None:
        previous = last_price(offer)
        if previous and previous > 0 and abs(price - previous) / previous > MAX_PRICE_CHANGE:
            issues.append(
                Issue("review", "price_jump", f"Cena {price} sa líši o > 60 % od poslednej známej {previous}")
            )

    return ValidationResult(offer, issues)
