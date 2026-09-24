from decimal import Decimal

import pytest

from app.ingestion.normalize import normalize_unit, parse_quantity, unit_price

D = Decimal


@pytest.mark.parametrize(
    "text, expected",
    [
        ("Madeta Tvaroh polotučný 250 g", (D("250"), "g", None)),
        ("Mléko 1,5 l", (D("1.5"), "l", None)),
        ("Jogurt 4x150g", (D("150"), "g", 4)),
        ("Jogurt 4 × 150 g", (D("150"), "g", 4)),
        ("Vejce 10 ks", (D("10"), "ks", None)),
        ("Víno 75 cl", (D("750"), "ml", None)),
        ("Kuřecí řízky", (None, None, None)),
    ],
)
def test_parse_quantity(text, expected):
    assert parse_quantity(text) == expected


def test_normalize_unit_unknown():
    assert normalize_unit("bal", D("1")) == (D("1"), None)


@pytest.mark.parametrize(
    "price, qty, unit, pack, ptype, expected",
    [
        (D("29.90"), D("250"), "g", None, "standard", (D("119.60"), "kg")),
        (D("39.90"), D("150"), "g", 4, "standard", (D("66.50"), "kg")),
        (D("19.90"), D("1"), "l", None, "standard", (D("19.90"), "l")),
        (D("29.90"), D("0.5"), "l", None, "multibuy", (D("59.80"), "l")),
        (D("159.90"), None, None, None, "per_kg", (D("159.90"), "kg")),
        (D("49.90"), D("10"), "ks", None, "standard", (D("4.99"), "ks")),
        (D("10.00"), None, "g", None, "standard", (None, None)),
        # zaokrúhlenie half-up ako v PostgreSQL: 0,125 → 0,13
        (D("0.25"), D("2"), "kg", None, "standard", (D("0.13"), "kg")),
    ],
)
def test_unit_price(price, qty, unit, pack, ptype, expected):
    assert unit_price(price, qty, unit, pack, ptype) == expected
