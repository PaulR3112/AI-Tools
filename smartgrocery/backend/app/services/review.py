"""Admin: stav ingestion behov a review queue."""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ingestion.pipeline import date_range, range_end_inclusive
from app.models import ExtractionRun, Offer, OfferCondition, ValidationEvent
from app.schemas import OfferCorrection, ReviewDecision, ReviewItemOut, RunOut


class ReviewError(Exception):
    pass


def list_runs(session: Session, source_id: int | None = None, limit: int = 50) -> list[RunOut]:
    q = select(ExtractionRun).order_by(ExtractionRun.checked_at.desc()).limit(min(limit, 200))
    if source_id is not None:
        q = q.where(ExtractionRun.source_endpoint_id == source_id)
    return [RunOut.model_validate(r) for r in session.scalars(q)]


def list_review(session: Session, limit: int = 100) -> list[ReviewItemOut]:
    q = (
        select(ValidationEvent)
        .where(ValidationEvent.status == "open", ValidationEvent.severity.in_(("review", "reject", "warning")))
        .order_by(ValidationEvent.created_at)
        .limit(min(limit, 500))
    )
    return [ReviewItemOut.model_validate(e) for e in session.scalars(q)]


def resolve(session: Session, event_id: int, decision: ReviewDecision) -> ReviewItemOut:
    event = session.get(ValidationEvent, event_id)
    if event is None:
        raise ReviewError("Položka neexistuje")
    if event.status != "open":
        raise ReviewError(f"Položka je už uzavretá ({event.status})")

    offer = session.get(Offer, event.offer_id) if event.offer_id else None
    if decision.action == "fix" and offer is None:
        raise ReviewError("Zamietnutá ponuka nemá záznam na opravu; použi re-extrakciu")

    if decision.action == "approve":
        # bez ponuky (varovanie, zamietnutý záznam) = len potvrdenie, že to niekto videl
        if offer is not None:
            offer.status = "active"
        status = "approved"
    elif decision.action == "reject":
        if offer is not None:
            offer.status = "rejected"
        status = "rejected"
    else:
        assert offer is not None
        if decision.correction is None:
            raise ReviewError("Oprava vyžaduje pole correction")
        _correct(session, offer, decision.correction)
        status = "fixed"

    # rozhodnutie platí pre všetky otvorené nálezy tej istej ponuky
    now = datetime.now(timezone.utc)
    related = [event]
    if event.offer_id is not None:
        related = list(
            session.scalars(
                select(ValidationEvent).where(
                    ValidationEvent.offer_id == event.offer_id, ValidationEvent.status == "open"
                )
            )
        )
    for e in related:
        e.status = status
        e.resolved_at = now
    session.commit()
    return ReviewItemOut.model_validate(event)


def _correct(session: Session, old: Offer, c: OfferCorrection) -> Offer:
    """Oprava = nový riadok + superseded_by na starom; cena sa nikdy neprepisuje UPDATE-om."""
    fields = c.model_dump(exclude_unset=True)
    valid_from = fields.pop("valid_from", None) or old.validity.lower
    valid_to = fields.pop("valid_to", None) or range_end_inclusive(old.validity)
    if valid_from > valid_to:
        raise ReviewError("valid_from > valid_to")
    new = Offer(
        flyer_version_id=old.flyer_version_id,
        store_id=old.store_id,
        extraction_run_id=old.extraction_run_id,
        category_id=old.category_id,
        raw_name=fields.get("raw_name", old.raw_name),
        brand=fields.get("brand", old.brand),
        price=fields.get("price", old.price),
        regular_price=fields.get("regular_price", old.regular_price),
        currency=old.currency,
        quantity=fields.get("quantity", old.quantity),
        unit=fields.get("unit", old.unit),
        pack_count=fields.get("pack_count", old.pack_count),
        price_type=fields.get("price_type", old.price_type),
        validity=date_range(valid_from, valid_to),
        source_page=old.source_page,
        bbox=old.bbox,
        confidence=None,
        status="active",
        conditions=[OfferCondition(kind=x.kind, value=x.value, note=x.note) for x in old.conditions],
    )
    session.add(new)
    session.flush()
    old.superseded_by = new.id
    return new
