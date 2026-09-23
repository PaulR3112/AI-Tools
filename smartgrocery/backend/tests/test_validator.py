from datetime import date
from decimal import Decimal

from app.ingestion.schema import ExtractedConditions, ExtractedOffer
from app.ingestion.validator import validate_offer

FROM, TO = date(2026, 9, 23), date(2026, 9, 29)
NO_COND = ExtractedConditions(
    loyalty_card=False,
    loyalty_program=None,
    min_qty=None,
    multibuy_buy=None,
    multibuy_get=None,
    app_only=False,
    coupon=False,
)


def offer(**kw) -> ExtractedOffer:
    base = dict(
        raw_name="Tvaroh 250 g",
        brand=None,
        price=29.9,
        regular_price=None,
        quantity=250,
        unit="g",
        pack_count=None,
        price_type="standard",
        conditions=NO_COND,
        valid_from=None,
        valid_to=None,
        bbox=[0.1, 0.1, 0.2, 0.2],
        confidence=0.9,
    )
    base.update(kw)
    return ExtractedOffer(**base)


def codes(result):
    return {i.code for i in result.issues}


def test_valid_offer_is_active_and_inherits_flyer_validity():
    r = validate_offer(offer(), FROM, TO)
    assert r.status == "active"
    assert (r.offer.valid_from, r.offer.valid_to) == (FROM, TO)
    assert r.offer.unit_price == Decimal("119.60")


def test_missing_or_zero_price_is_rejected():
    assert validate_offer(offer(price=None), FROM, TO).status == "rejected"
    assert "non_positive_price" in codes(validate_offer(offer(price=0), FROM, TO))


def test_valid_from_after_valid_to_is_rejected():
    r = validate_offer(offer(valid_from="2026-09-28", valid_to="2026-09-24"), FROM, TO)
    assert "invalid_validity" in codes(r)
    assert r.status == "rejected"


def test_regular_below_price_goes_to_review():
    r = validate_offer(offer(regular_price=19.9), FROM, TO)
    assert r.status == "review"
    assert "regular_below_price" in codes(r)


def test_validity_outside_flyer_goes_to_review():
    r = validate_offer(offer(valid_to="2026-10-10"), FROM, TO)
    assert "validity_outside_flyer" in codes(r)


def test_implausible_unit_price():
    r = validate_offer(offer(price=999, quantity=1, unit="g"), FROM, TO)
    assert "implausible_unit_price" in codes(r)
    r = validate_offer(offer(), FROM, TO, unit_price_range=(Decimal("50"), Decimal("100")))
    assert "implausible_unit_price" in codes(r)


def test_price_jump_over_60_percent():
    r = validate_offer(offer(price=10), FROM, TO, last_price=lambda o: Decimal("30"))
    assert "price_jump" in codes(r)
    r = validate_offer(offer(price=25), FROM, TO, last_price=lambda o: Decimal("30"))
    assert "price_jump" not in codes(r)


def test_quantity_falls_back_to_name_regex():
    r = validate_offer(offer(raw_name="Jogurt 4x150 g", quantity=None, unit=None), FROM, TO)
    assert (r.offer.quantity, r.offer.unit, r.offer.pack_count) == (Decimal("150"), "g", 4)


def test_low_confidence_and_missing_bbox_go_to_review():
    assert "low_confidence" in codes(validate_offer(offer(confidence=0.3), FROM, TO))
    assert "missing_bbox" in codes(validate_offer(offer(bbox=[]), FROM, TO))


def test_conditions_are_mapped():
    cond = NO_COND.model_copy(
        update={"loyalty_card": True, "loyalty_program": "Lidl Plus", "multibuy_buy": 2, "multibuy_get": 1}
    )
    r = validate_offer(offer(conditions=cond, price_type="multibuy"), FROM, TO)
    assert r.offer.conditions == [("loyalty_card", {"program": "Lidl Plus"}), ("multibuy", {"buy": 2, "get": 1})]
