"""Service layer – jediné miesto logiky čítania ponúk. Volá ho REST, neskôr MCP aj /v1/ai/query."""

import time
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from typing import Literal

from sqlalchemy import Numeric, Select, case, exists, func, literal, or_, select
from sqlalchemy.orm import Session, selectinload

from app.ingestion.pipeline import range_end_inclusive
from app.models import (
    ApiAuditEvent,
    Category,
    Flyer,
    FlyerVersion,
    Offer,
    OfferCondition,
    SourceEndpoint,
    Store,
)
from app.schemas import (
    CategoryOut,
    ConditionOut,
    FlyerOut,
    OfferDetail,
    OfferOut,
    OfferSource,
    StoreOut,
)

ValidityFilter = Literal["current", "today", "week", "future"]
SortOrder = Literal["relevance", "unit_price", "price"]

MAX_LIMIT = 100


@dataclass
class SearchParams:
    q: str | None = None
    active_at: date = field(default_factory=date.today)
    validity: ValidityFilter = "current"
    store_ids: list[int] = field(default_factory=list)
    category: str | None = None
    price_max: Decimal | None = None
    unit_price_max: Decimal | None = None
    no_loyalty: bool = False
    sort: SortOrder = "relevance"
    limit: int = 20
    offset: int = 0


def _visible() -> list:
    """Vo vyhľadávaní sú len aktívne, nenahradené ponuky z aktuálnej verzie letáku."""
    return [Offer.status == "active", Offer.superseded_by.is_(None), FlyerVersion.is_current.is_(True)]


def _base_query() -> Select:
    return (
        select(Offer)
        .join(FlyerVersion, FlyerVersion.id == Offer.flyer_version_id)
        .options(
            selectinload(Offer.store),
            selectinload(Offer.conditions),
            selectinload(Offer.flyer_version),
        )
    )


def search_offers(session: Session, p: SearchParams) -> list[OfferOut]:
    day = p.active_at
    active_today = Offer.validity.contains(day)

    query = _base_query().where(*_visible())

    if p.validity == "today":
        query = query.where(active_today)
    elif p.validity == "week":
        query = query.where(Offer.validity.overlaps(func.daterange(day, day + timedelta(days=7))))
    elif p.validity == "future":
        query = query.where(func.lower(Offer.validity) > day)
    else:  # current = platí dnes alebo v budúcnosti
        query = query.where(func.upper(Offer.validity) > day)

    if p.store_ids:
        query = query.where(Offer.store_id.in_(p.store_ids))
    if p.category:
        query = query.join(Category, Category.id == Offer.category_id).where(Category.slug == p.category)
    if p.price_max is not None:
        query = query.where(Offer.price <= p.price_max)
    if p.unit_price_max is not None:
        query = query.where(Offer.unit_price <= p.unit_price_max)
    if p.no_loyalty:
        query = query.where(~exists().where(OfferCondition.offer_id == Offer.id, OfferCondition.kind == "loyalty_card"))

    relevance = literal(0.0)
    q = (p.q or "").strip()
    if q:
        needle = func.f_unaccent(literal(q))
        haystack = func.f_unaccent(Offer.raw_name)  # zhoduje sa s trigram indexom ix_offers_name_trgm
        query = query.where(or_(haystack.contains(needle, autoescape=False), needle.op("<%")(haystack)))
        # relevancia po krokoch 0,1 – v rámci kroku rozhoduje platnosť a jednotková cena
        relevance = func.round(func.word_similarity(needle, haystack).cast(Numeric), 1)

    active_first = case((active_today, 0), else_=1)
    unit_price_last = Offer.unit_price.asc().nulls_last()
    if p.sort == "unit_price":
        order = [unit_price_last, Offer.price.asc()]
    elif p.sort == "price":
        order = [Offer.price.asc()]
    else:
        order = [relevance.desc(), active_first, unit_price_last, Offer.price.asc()]
    query = query.order_by(*order, Offer.id).limit(min(p.limit, MAX_LIMIT)).offset(p.offset)

    offers = session.scalars(query).all()
    urls = _source_urls(session, offers)
    return [to_offer_out(o, day, urls) for o in offers]


def get_offer(session: Session, offer_id: int, active_at: date | None = None) -> OfferDetail | None:
    offer = session.scalar(_base_query().where(Offer.id == offer_id))
    if offer is None:
        return None
    day = active_at or date.today()
    base = to_offer_out(offer, day, _source_urls(session, [offer]))
    return OfferDetail(
        **base.model_dump(),
        confidence=offer.confidence,
        status=offer.status,
        extraction_run_id=offer.extraction_run_id,
        created_at=offer.created_at,
    )


def list_stores(session: Session) -> list[StoreOut]:
    return [StoreOut.model_validate(s) for s in session.scalars(select(Store).order_by(Store.name))]


def list_flyers(session: Session, store_id: int | None = None, active_at: date | None = None) -> list[FlyerOut]:
    query = (
        select(FlyerVersion, Flyer, Store, SourceEndpoint)
        .join(Flyer, Flyer.id == FlyerVersion.flyer_id)
        .join(Store, Store.id == Flyer.store_id)
        .join(SourceEndpoint, SourceEndpoint.id == Flyer.source_endpoint_id)
        .where(FlyerVersion.is_current.is_(True))
    )
    if store_id is not None:
        query = query.where(Flyer.store_id == store_id)
    if active_at is not None:
        query = query.where(FlyerVersion.validity.contains(active_at))
    query = query.order_by(Store.name, func.lower(FlyerVersion.validity))
    return [
        FlyerOut(
            id=flyer.id,
            store=StoreOut.model_validate(store),
            valid_from=fv.validity.lower,
            valid_to=range_end_inclusive(fv.validity),
            version=fv.version,
            page_count=fv.page_count,
            document_url=_public_url(src.url),
        )
        for fv, flyer, store, src in session.execute(query)
    ]


def list_categories(session: Session) -> list[CategoryOut]:
    rows = session.scalars(select(Category).order_by(Category.parent_id.nulls_first(), Category.name))
    return [
        CategoryOut(id=c.id, slug=c.slug, name=c.name, parent_id=c.parent_id, unit_basis=c.unit_basis) for c in rows
    ]


def audit(session: Session, channel: str, action: str, params: dict, result_count: int | None, started: float) -> None:
    session.add(
        ApiAuditEvent(
            channel=channel,
            action=action,
            params=params,
            result_count=result_count,
            duration_ms=int((time.monotonic() - started) * 1000),
        )
    )
    session.commit()


# ---------------------------------------------------------------- mapovanie


def _public_url(url: str) -> str | None:
    # lokálne cesty (manuálny import) sa von neposielajú
    return url if url.startswith(("http://", "https://")) else None


def _source_urls(session: Session, offers) -> dict[int, str | None]:
    flyer_ids = {o.flyer_version.flyer_id for o in offers}
    if not flyer_ids:
        return {}
    rows = session.execute(
        select(Flyer.id, SourceEndpoint.url)
        .join(SourceEndpoint, SourceEndpoint.id == Flyer.source_endpoint_id)
        .where(Flyer.id.in_(flyer_ids))
    )
    return {fid: _public_url(url) for fid, url in rows}


def to_offer_out(o: Offer, day: date, urls: dict[int, str | None]) -> OfferOut:
    valid_from = o.validity.lower
    valid_to = range_end_inclusive(o.validity)
    return OfferOut(
        id=o.id,
        raw_name=o.raw_name,
        brand=o.brand,
        store=StoreOut.model_validate(o.store),
        price=o.price,
        regular_price=o.regular_price,
        currency=o.currency,
        quantity=o.quantity,
        unit=o.unit,
        pack_count=o.pack_count,
        unit_price=o.unit_price,
        unit_price_basis=o.unit_price_basis,
        price_type=o.price_type,
        valid_from=valid_from,
        valid_to=valid_to,
        is_active=valid_from <= day <= valid_to,
        conditions=[ConditionOut(kind=c.kind, value=c.value) for c in o.conditions],
        source=OfferSource(
            flyer_id=o.flyer_version.flyer_id,
            flyer_version_id=o.flyer_version_id,
            page=o.source_page,
            bbox=o.bbox,
            document_url=urls.get(o.flyer_version.flyer_id),
        ),
    )
