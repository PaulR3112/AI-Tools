import secrets
import time
from datetime import date
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_session
from app.schemas import (
    CategoryOut,
    FlyerOut,
    OfferDetail,
    ReviewDecision,
    ReviewItemOut,
    RunOut,
    SearchResponse,
    StoreOut,
)
from app.services import offers as svc
from app.services import review

router = APIRouter(prefix="/v1")
DB = Annotated[Session, Depends(get_session)]


@router.get("/offers/search", response_model=SearchResponse, tags=["offers"])
def search_offers(
    session: DB,
    q: str | None = Query(None, max_length=200),
    active_at: date | None = None,
    validity: svc.ValidityFilter = "current",
    store_id: Annotated[list[int] | None, Query()] = None,
    category: str | None = None,
    price_max: Decimal | None = Query(None, gt=0),
    unit_price_max: Decimal | None = Query(None, gt=0),
    no_loyalty: bool = False,
    sort: svc.SortOrder = "relevance",
    limit: int = Query(20, ge=1, le=svc.MAX_LIMIT),
    offset: int = Query(0, ge=0),
):
    started = time.monotonic()
    params = svc.SearchParams(
        q=q,
        active_at=active_at or date.today(),
        validity=validity,
        store_ids=store_id or [],
        category=category,
        price_max=price_max,
        unit_price_max=unit_price_max,
        no_loyalty=no_loyalty,
        sort=sort,
        limit=limit,
        offset=offset,
    )
    items = svc.search_offers(session, params)
    svc.audit(
        session,
        "rest",
        "search_offers",
        {k: str(v) if isinstance(v, (date, Decimal)) else v for k, v in vars(params).items()},
        len(items),
        started,
    )
    return SearchResponse(items=items, limit=limit, offset=offset, active_at=params.active_at)


@router.get("/offers/{offer_id}", response_model=OfferDetail, tags=["offers"])
def get_offer(offer_id: int, session: DB, active_at: date | None = None):
    offer = svc.get_offer(session, offer_id, active_at)
    if offer is None:
        raise HTTPException(404, "Ponuka neexistuje")
    return offer


@router.get("/stores", response_model=list[StoreOut], tags=["catalog"])
def stores(session: DB):
    return svc.list_stores(session)


@router.get("/flyers", response_model=list[FlyerOut], tags=["catalog"])
def flyers(session: DB, store_id: int | None = None, active_at: date | None = None):
    return svc.list_flyers(session, store_id, active_at)


@router.get("/categories", response_model=list[CategoryOut], tags=["catalog"])
def categories(session: DB):
    return svc.list_categories(session)


# ---------------------------------------------------------------- admin


def require_admin(authorization: str | None = Header(None)) -> None:
    token = get_settings().admin_token
    if not token or token == "change-me":
        raise HTTPException(503, "Admin API je vypnuté – nastav SG_ADMIN_TOKEN")
    expected = f"Bearer {token}"
    if authorization is None or not secrets.compare_digest(authorization, expected):
        raise HTTPException(401, "Neplatný token")


admin = APIRouter(prefix="/v1/admin", tags=["admin"], dependencies=[Depends(require_admin)])


@admin.get("/runs", response_model=list[RunOut])
def runs(session: DB, source_id: int | None = None, limit: int = Query(50, ge=1, le=200)):
    return review.list_runs(session, source_id, limit)


@admin.get("/review", response_model=list[ReviewItemOut])
def review_queue(session: DB, limit: int = Query(100, ge=1, le=500)):
    return review.list_review(session, limit)


@admin.post("/review/{event_id}", response_model=ReviewItemOut)
def review_decide(event_id: int, decision: ReviewDecision, session: DB):
    try:
        return review.resolve(session, event_id, decision)
    except review.ReviewError as e:
        session.rollback()
        raise HTTPException(409, str(e)) from e
