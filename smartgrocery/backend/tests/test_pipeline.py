"""Integrácia: adaptér → extrakcia (nahraná odpoveď modelu) → validátor → DB."""

from dataclasses import replace
from decimal import Decimal

import pytest
from sqlalchemy import func, select

from app.ingestion import pipeline
from app.ingestion.normalize import unit_price
from app.models import ExtractionRun, FlyerVersion, Offer, RawDocument, ValidationEvent

from .conftest import make_pdf


def test_full_flow_stores_offers_review_and_rejections(session, source, deps):
    run = pipeline.check_source(session, source.id, deps)

    assert run.status == "succeeded"
    assert (run.offers_count, run.review_count, run.rejected_count) == (6, 2, 1)
    assert run.flyer_version_id is not None
    assert run.model_id == "recorded"

    raw = session.get(RawDocument, run.raw_document_id)
    assert raw.storage_key and deps.storage.get(raw.storage_key)[:5] == b"%PDF-"

    fv = session.get(FlyerVersion, run.flyer_version_id)
    assert (fv.validity.lower.isoformat(), pipeline.range_end_inclusive(fv.validity).isoformat()) == (
        "2026-09-23",
        "2026-09-29",
    )
    assert fv.page_count == 2

    codes = set(session.scalars(select(ValidationEvent.code)))
    assert {"missing_price", "regular_below_price", "validity_outside_flyer"} <= codes


def test_db_unit_price_matches_python(session, source, deps):
    pipeline.check_source(session, source.id, deps)
    offers = session.scalars(select(Offer)).all()
    assert offers
    for o in offers:
        assert (o.unit_price, o.unit_price_basis) == unit_price(o.price, o.quantity, o.unit, o.pack_count, o.price_type)
    jogurt = next(o for o in offers if o.raw_name.startswith("Jogurt"))
    assert jogurt.unit_price == Decimal("66.50")


def test_unchanged_content_is_cheap_check(session, source, deps):
    pipeline.check_source(session, source.id, deps)
    run2 = pipeline.check_source(session, source.id, deps)
    assert run2.status == "unchanged"
    assert session.scalar(select(func.count(Offer.id))) == 8


def test_same_hash_and_version_is_not_processed_twice(session, source, deps):
    pipeline.check_source(session, source.id, deps)
    run2 = pipeline.check_source(session, source.id, deps, force=True)
    assert run2.status == "skipped"
    assert session.scalar(select(func.count(Offer.id))) == 8


def test_reextract_with_new_version_creates_new_current_flyer_version(session, source, deps):
    run1 = pipeline.check_source(session, source.id, deps)
    deps.extractor.extraction_version = "recorded-v2"
    run2 = pipeline.reextract(session, run1.raw_document_id, deps)

    assert run2.status == "succeeded"
    v1 = session.get(FlyerVersion, run1.flyer_version_id)
    v2 = session.get(FlyerVersion, run2.flyer_version_id)
    session.refresh(v1)
    assert v1.flyer_id == v2.flyer_id
    assert (v1.version, v1.is_current, v2.version, v2.is_current) == (1, False, 2, True)


def test_pending_legal_status_blocks_processing(session, source, deps):
    source.legal_status = "pending"
    session.commit()
    with pytest.raises(pipeline.LegalStatusError):
        pipeline.check_source(session, source.id, deps)
    assert session.scalar(select(func.count(ExtractionRun.id))) == 0


def test_fetch_failure_is_recorded_and_counted(session, source, deps):
    source.url = "/neexistuje/letak.pdf"
    session.commit()
    for _ in range(2):
        with pytest.raises(FileNotFoundError):
            pipeline.check_source(session, source.id, deps)
    session.refresh(source)
    assert source.consecutive_failures == 2
    assert set(session.scalars(select(ExtractionRun.status))) == {"failed"}


def test_extraction_failure_keeps_run_and_rolls_back_offers(session, source, deps):
    class Boom:
        extraction_version = "boom"

        def extract(self, image_png, ctx):
            if ctx.page_number == 2:
                raise pipeline.ExtractionError("model zlyhal")
            return deps.extractor.extract(image_png, ctx)

    with pytest.raises(pipeline.ExtractionError):
        pipeline.check_source(session, source.id, replace(deps, extractor=Boom()))
    run = session.scalar(select(ExtractionRun))
    assert run.status == "failed" and "model zlyhal" in run.error
    assert session.scalar(select(func.count(Offer.id))) == 0
    # po chybe sa nezapamätá hash → ďalší cyklus to skúsi znova
    session.refresh(source)
    assert source.last_hash is None


def test_cost_limit_stops_extraction(session, source, deps, monkeypatch):
    settings = deps.settings.model_copy(update={"llm_daily_cost_limit_usd": Decimal("0")})
    with pytest.raises(pipeline.CostLimitError):
        pipeline.check_source(session, source.id, replace(deps, settings=settings))


def test_new_document_with_price_jump_goes_to_review(session, source, deps, flyer_pdf):
    pipeline.check_source(session, source.id, deps)
    # nový leták (iný obsah) s rovnakými produktmi, ale cenou Madety 9,90 (−67 %)
    flyer_pdf.write_bytes(make_pdf(3))
    page = deps.extractor.pages[0]
    madeta = page.offers[0].model_copy(update={"price": 9.9})
    deps.extractor.pages[0] = page.model_copy(update={"offers": [madeta]})
    run2 = pipeline.check_source(session, source.id, deps)
    assert run2.review_count == 3  # Madeta (price_jump) + 2 review zo strany 2
    assert "price_jump" in set(
        session.scalars(select(ValidationEvent.code).where(ValidationEvent.extraction_run_id == run2.id))
    )
