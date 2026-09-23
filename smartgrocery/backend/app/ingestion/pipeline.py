"""Ingestion pipeline (kap. 4): fetch → raw storage → stránky → extrakcia → validátor → DB."""

import hashlib
import logging
import mimetypes
import time
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import Range
from sqlalchemy.orm import Session

from app.config import Settings
from app.ingestion.adapters import get_adapter
from app.ingestion.extractor import ExtractionError, PageContext, PageExtractor
from app.ingestion.pdf import render_pages
from app.ingestion.schema import PageExtraction
from app.ingestion.storage import Storage
from app.ingestion.validator import NormalizedOffer, validate_offer
from app.models import (
    ExtractionRun,
    Flyer,
    FlyerVersion,
    Offer,
    OfferCondition,
    RawDocument,
    SourceEndpoint,
    ValidationEvent,
)

log = logging.getLogger(__name__)

ALERT_AFTER_FAILURES = 2
BASELINE_RUNS = 5
BASELINE_TOLERANCE = Decimal("0.40")


class LegalStatusError(Exception):
    """Zdroj nemá legal_status = approved – nesmie sa spracovať."""


class CostLimitError(Exception):
    pass


@dataclass
class Deps:
    settings: Settings
    storage: Storage
    extractor: PageExtractor


def _now() -> datetime:
    return datetime.now(timezone.utc)


def date_range(start: date, end: date) -> Range[date]:
    """Uzavretý interval [start, end]; PG ho normalizuje na [start, end+1)."""
    return Range(start, end, bounds="[]")


def range_end_inclusive(r: Range[date]) -> date:
    assert r.upper is not None
    return r.upper - timedelta(days=1) if r.upper_inc is False else r.upper


# ---------------------------------------------------------------- vstupný bod


def check_source(
    session: Session,
    source_id: int,
    deps: Deps,
    *,
    validity_hint: tuple[date, date] | None = None,
    force: bool = False,
) -> ExtractionRun:
    source = session.get(SourceEndpoint, source_id)
    if source is None:
        raise ValueError(f"Zdroj {source_id} neexistuje")
    if source.legal_status != "approved":
        raise LegalStatusError(f"Zdroj {source_id} má legal_status={source.legal_status}; spracovanie zablokované")
    if not source.enabled:
        raise LegalStatusError(f"Zdroj {source_id} je vypnutý")

    s = deps.settings
    run = ExtractionRun(
        source_endpoint_id=source.id,
        status="running",
        parser_version=s.parser_version,
        extraction_version=deps.extractor.extraction_version,
    )
    session.add(run)
    session.flush()
    t0 = time.monotonic()

    try:
        fetched = get_adapter(source.adapter).fetch(source, s.http_user_agent)
    except Exception as e:
        _fail(session, source, run, t0, f"fetch: {e}")
        raise

    source.last_checked_at = _now()
    if fetched.not_modified:
        return _finish_unchanged(session, source, run, t0)
    assert fetched.content is not None

    sha = hashlib.sha256(fetched.content).hexdigest()
    run.content_hash = sha
    if sha == source.last_hash and not force:
        return _finish_unchanged(session, source, run, t0)

    # raw dokument sa uloží pred akýmkoľvek spracovaním
    raw = _store_raw(session, source, sha, fetched.content, fetched.content_type or "application/octet-stream", deps)
    run.raw_document_id = raw.id

    already = session.scalar(
        select(ExtractionRun.id).where(
            ExtractionRun.content_hash == sha,
            ExtractionRun.extraction_version == run.extraction_version,
            ExtractionRun.status == "succeeded",
        )
    )
    if already:
        run.status = "skipped"
        _remember_fetch_state(source, fetched.etag, fetched.last_modified, sha)
        run.finished_at = _now()
        run.duration_ms = int((time.monotonic() - t0) * 1000)
        session.commit()
        return run

    _process_safely(session, run, source, raw, fetched.content, deps, t0, validity_hint=validity_hint)

    _remember_fetch_state(source, fetched.etag, fetched.last_modified, sha)
    source.consecutive_failures = 0
    run.duration_ms = int((time.monotonic() - t0) * 1000)
    session.commit()
    log.info(
        "run %s: %s ponúk, %s review, %s zamietnutých", run.id, run.offers_count, run.review_count, run.rejected_count
    )
    return run


def reextract(
    session: Session, raw_document_id: int, deps: Deps, *, validity_hint: tuple[date, date] | None = None
) -> ExtractionRun:
    """Re-extrakcia z uloženého raw dokumentu (nový prompt/model) bez nového sťahovania."""
    raw = session.get(RawDocument, raw_document_id)
    if raw is None or raw.storage_key is None:
        raise ValueError(f"Raw dokument {raw_document_id} neexistuje alebo už bol zmazaný (retencia)")
    source = session.get(SourceEndpoint, raw.source_endpoint_id)
    assert source is not None
    if source.legal_status != "approved":
        raise LegalStatusError(f"Zdroj {source.id} má legal_status={source.legal_status}")

    run = ExtractionRun(
        source_endpoint_id=source.id,
        raw_document_id=raw.id,
        status="running",
        content_hash=raw.sha256,
        parser_version=deps.settings.parser_version,
        extraction_version=deps.extractor.extraction_version,
    )
    session.add(run)
    session.flush()
    t0 = time.monotonic()
    _process_safely(
        session,
        run,
        source,
        raw,
        deps.storage.get(raw.storage_key),
        deps,
        t0,
        validity_hint=validity_hint,
        count_failure=False,
    )
    run.duration_ms = int((time.monotonic() - t0) * 1000)
    session.commit()
    return run


# ---------------------------------------------------------------- spracovanie


def _process_safely(
    session: Session,
    run: ExtractionRun,
    source: SourceEndpoint,
    raw: RawDocument,
    content: bytes,
    deps: Deps,
    t0: float,
    *,
    validity_hint: tuple[date, date] | None,
    count_failure: bool = True,
) -> None:
    """Spracovanie v savepointe; pri chybe sa zahodia čiastočné ponuky, ale beh a náklady LLM ostanú."""
    nested = session.begin_nested()
    try:
        process_document(session, run, source, raw, content, deps, validity_hint=validity_hint)
        nested.commit()
    except Exception as e:
        usage = (run.model_id, run.input_tokens, run.output_tokens, run.cost_usd)
        nested.rollback()
        run.model_id, run.input_tokens, run.output_tokens, run.cost_usd = usage
        _fail(session, source, run, t0, str(e), count_failure=count_failure)
        raise


def process_document(
    session: Session,
    run: ExtractionRun,
    source: SourceEndpoint,
    raw: RawDocument,
    content: bytes,
    deps: Deps,
    *,
    validity_hint: tuple[date, date] | None = None,
) -> None:
    s = deps.settings
    pages = render_pages(content, raw.content_type, dpi=s.render_dpi)
    reference_date = raw.fetched_at.date() if raw.fetched_at else date.today()
    spent_today = _llm_cost_today(session)

    extracted: list[PageExtraction] = []
    for i, png in enumerate(pages, start=1):
        if spent_today + run.cost_usd >= s.llm_daily_cost_limit_usd:
            raise CostLimitError(
                f"Denný limit nákladov LLM {s.llm_daily_cost_limit_usd} USD dosiahnutý (stránka {i}/{len(pages)})"
            )
        ctx = PageContext(source.store.name, i, len(pages), reference_date)
        result = deps.extractor.extract(png, ctx)
        run.model_id = result.model_id
        run.input_tokens += result.input_tokens
        run.output_tokens += result.output_tokens
        run.cost_usd = _cost(run.input_tokens, run.output_tokens, s)
        extracted.append(result.page)

    flyer_from, flyer_to = validity_hint or _flyer_validity(extracted)
    version = _new_flyer_version(session, source, raw, flyer_from, flyer_to, len(pages))
    run.flyer_version_id = version.id

    for page_no, page in enumerate(extracted, start=1):
        for item in page.offers:
            result = validate_offer(
                item, flyer_from, flyer_to, last_price=lambda o: _last_price(session, source.store_id, o, run.id)
            )
            o = result.offer
            if result.status == "rejected":
                run.rejected_count += 1
                for issue in result.issues:
                    session.add(
                        ValidationEvent(
                            extraction_run_id=run.id,
                            source_page=page_no,
                            severity=issue.severity,
                            code=issue.code,
                            message=issue.message,
                            payload=item.model_dump(mode="json"),
                        )
                    )
                continue

            offer = Offer(
                flyer_version_id=version.id,
                store_id=source.store_id,
                extraction_run_id=run.id,
                raw_name=o.raw_name,
                brand=o.brand,
                price=o.price,
                regular_price=o.regular_price,
                quantity=o.quantity,
                unit=o.unit,
                pack_count=o.pack_count,
                price_type=o.price_type,
                validity=date_range(o.valid_from, o.valid_to),
                source_page=page_no,
                bbox=o.bbox,
                confidence=o.confidence,
                status=result.status,
                conditions=[OfferCondition(kind=k, value=v) for k, v in o.conditions],
            )
            session.add(offer)
            session.flush()
            if result.status == "review":
                run.review_count += 1
            else:
                run.offers_count += 1
            for issue in result.issues:
                session.add(
                    ValidationEvent(
                        extraction_run_id=run.id,
                        offer_id=offer.id,
                        source_page=page_no,
                        severity=issue.severity,
                        code=issue.code,
                        message=issue.message,
                        payload=item.model_dump(mode="json"),
                    )
                )

    _check_baseline(session, source, run)
    run.status = "succeeded"
    run.finished_at = _now()


def _flyer_validity(pages: list[PageExtraction]) -> tuple[date, date]:
    """Platnosť letáku: najčastejšia hodnota zo stránok, inak rozsah dátumov ponúk."""
    pairs = Counter((p.flyer_valid_from, p.flyer_valid_to) for p in pages if p.flyer_valid_from and p.flyer_valid_to)
    for (start, end), _ in pairs.most_common():
        try:
            d1, d2 = date.fromisoformat(start), date.fromisoformat(end)
        except ValueError:
            continue
        if d1 <= d2:
            return d1, d2
    starts, ends = [], []
    for p in pages:
        for o in p.offers:
            try:
                if o.valid_from:
                    starts.append(date.fromisoformat(o.valid_from))
                if o.valid_to:
                    ends.append(date.fromisoformat(o.valid_to))
            except ValueError:
                continue
    if starts and ends and min(starts) <= max(ends):
        return min(starts), max(ends)
    raise ExtractionError("Platnosť letáku sa nedá určiť; zadaj ju ručne (--valid-from/--valid-to)")


def _new_flyer_version(
    session: Session, source: SourceEndpoint, raw: RawDocument, start: date, end: date, page_count: int
) -> FlyerVersion:
    validity = date_range(start, end)
    flyer = session.scalar(
        select(Flyer).where(Flyer.source_endpoint_id == source.id, Flyer.validity == validity).limit(1)
    )
    if flyer is None:
        flyer = Flyer(store_id=source.store_id, source_endpoint_id=source.id, validity=validity)
        session.add(flyer)
        session.flush()
    last = session.scalar(select(func.max(FlyerVersion.version)).where(FlyerVersion.flyer_id == flyer.id)) or 0
    session.execute(update(FlyerVersion).where(FlyerVersion.flyer_id == flyer.id).values(is_current=False))
    version = FlyerVersion(
        flyer_id=flyer.id,
        raw_document_id=raw.id,
        version=last + 1,
        validity=validity,
        page_count=page_count,
        is_current=True,
    )
    session.add(version)
    session.flush()
    return version


def _last_price(session: Session, store_id: int, o: NormalizedOffer, run_id: int) -> Decimal | None:
    """Posledná známa cena „rovnakého“ produktu – kým nie sú canonical products, podľa názvu a balenia."""
    q = select(Offer.price).where(
        Offer.store_id == store_id,
        Offer.status == "active",
        Offer.extraction_run_id != run_id,
        func.lower(Offer.raw_name) == o.raw_name.lower(),
        Offer.price_type == o.price_type,
    )
    q = q.where(Offer.unit == o.unit) if o.unit else q.where(Offer.unit.is_(None))
    q = q.where(Offer.quantity == o.quantity) if o.quantity is not None else q.where(Offer.quantity.is_(None))
    return session.scalar(q.order_by(Offer.created_at.desc()).limit(1))


def _check_baseline(session: Session, source: SourceEndpoint, run: ExtractionRun) -> None:
    counts = session.scalars(
        select(ExtractionRun.offers_count + ExtractionRun.review_count)
        .where(ExtractionRun.source_endpoint_id == source.id, ExtractionRun.status == "succeeded")
        .order_by(ExtractionRun.checked_at.desc())
        .limit(BASELINE_RUNS)
    ).all()
    if not counts:
        return
    baseline = Decimal(sum(counts)) / len(counts)
    current = run.offers_count + run.review_count
    if baseline > 0 and abs(current - baseline) / baseline > BASELINE_TOLERANCE:
        log.warning("ALERT zdroj %s: %s ponúk vs baseline %.1f", source.id, current, baseline)
        session.add(
            ValidationEvent(
                extraction_run_id=run.id,
                severity="warning",
                code="offer_count_deviation",
                message=f"Počet ponúk {current} je mimo ±40 % baseline {baseline:.1f}",
            )
        )


# ---------------------------------------------------------------- pomocné


def _store_raw(
    session: Session, source: SourceEndpoint, sha: str, content: bytes, content_type: str, deps: Deps
) -> RawDocument:
    raw = session.scalar(
        select(RawDocument).where(RawDocument.source_endpoint_id == source.id, RawDocument.sha256 == sha)
    )
    ext = mimetypes.guess_extension(content_type) or ".bin"
    key = f"{source.id}/{sha}{ext}"
    if raw is None:
        raw = RawDocument(
            source_endpoint_id=source.id,
            sha256=sha,
            content_type=content_type,
            size_bytes=len(content),
            fetched_at=_now(),
        )
        session.add(raw)
    if raw.storage_key is None:
        deps.storage.put(key, content)
        raw.storage_key = key
    raw.delete_after = date.today() + timedelta(days=source.raw_retention_days)
    session.flush()
    return raw


def _remember_fetch_state(source: SourceEndpoint, etag: str | None, last_modified: str | None, sha: str) -> None:
    source.etag = etag
    source.last_modified = last_modified
    source.last_hash = sha


def _finish_unchanged(session: Session, source: SourceEndpoint, run: ExtractionRun, t0: float) -> ExtractionRun:
    run.status = "unchanged"
    run.finished_at = _now()
    run.duration_ms = int((time.monotonic() - t0) * 1000)
    source.consecutive_failures = 0
    session.commit()
    return run


def _fail(
    session: Session, source: SourceEndpoint, run: ExtractionRun, t0: float, error: str, count_failure: bool = True
) -> None:
    run.status = "failed"
    run.error = error[:4000]
    run.finished_at = _now()
    run.duration_ms = int((time.monotonic() - t0) * 1000)
    if count_failure:
        source.consecutive_failures += 1
        if source.consecutive_failures >= ALERT_AFTER_FAILURES:
            log.error("ALERT zdroj %s zlyhal %s× po sebe: %s", source.id, source.consecutive_failures, error)
    session.commit()


def _cost(input_tokens: int, output_tokens: int, s: Settings) -> Decimal:
    return (
        Decimal(input_tokens) * s.llm_price_input_per_mtok + Decimal(output_tokens) * s.llm_price_output_per_mtok
    ) / Decimal(1_000_000)


def _llm_cost_today(session: Session) -> Decimal:
    start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    return session.scalar(
        select(func.coalesce(func.sum(ExtractionRun.cost_usd), 0)).where(ExtractionRun.checked_at >= start)
    ) or Decimal("0")


def purge_expired_raw(session: Session, storage: Storage) -> int:
    """Retencia: po uplynutí zmaže raw súbor, ponechá hash a extrahované ponuky."""
    docs = session.scalars(
        select(RawDocument).where(RawDocument.delete_after < date.today(), RawDocument.storage_key.is_not(None))
    ).all()
    for doc in docs:
        assert doc.storage_key is not None
        storage.delete(doc.storage_key)
        doc.storage_key = None
    session.commit()
    return len(docs)
