"""Worker a scheduler – fronta v PostgreSQL (procrastinate), žiadny Redis.

Spustenie: procrastinate --log-level=info --app=app.worker.app worker
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone

import procrastinate
from procrastinate.exceptions import AlreadyEnqueued
from sqlalchemy import select

from app.config import get_settings
from app.db import get_sessionmaker
from app.deps import build_deps
from app.ingestion import pipeline
from app.models import SourceEndpoint

log = logging.getLogger(__name__)

app = procrastinate.App(
    connector=procrastinate.PsycopgConnector(conninfo=get_settings().procrastinate_conninfo),
)


def due_source_ids(now: datetime) -> list[int]:
    """Povolené zdroje, ktorým uplynul interval kontroly."""
    with get_sessionmaker()() as session:
        sources = session.scalars(
            select(SourceEndpoint).where(SourceEndpoint.enabled.is_(True), SourceEndpoint.legal_status == "approved")
        ).all()
        return [
            s.id
            for s in sources
            if s.last_checked_at is None or s.last_checked_at <= now - timedelta(minutes=s.check_interval_minutes)
        ]


@app.periodic(cron="*/5 * * * *")
@app.task(name="schedule_checks", queue="scheduler")
async def schedule_checks(timestamp: int) -> None:
    now = datetime.fromtimestamp(timestamp, tz=timezone.utc)
    for source_id in await asyncio.to_thread(due_source_ids, now):
        try:
            await check_source.configure(queueing_lock=f"source-{source_id}").defer_async(source_id=source_id)
        except AlreadyEnqueued:
            pass


@app.task(
    name="check_source",
    queue="ingestion",
    retry=procrastinate.RetryStrategy(max_attempts=3, exponential_wait=60),
)
def check_source(source_id: int) -> None:
    deps = build_deps()
    with get_sessionmaker()() as session:
        try:
            pipeline.check_source(session, source_id, deps)
        except (pipeline.LegalStatusError, pipeline.CostLimitError) as e:
            # neopakovať – treba zásah človeka alebo nový deň
            log.error("zdroj %s: %s", source_id, e)


@app.periodic(cron="15 3 * * *")
@app.task(name="purge_raw", queue="scheduler")
def purge_raw(timestamp: int) -> None:
    deps = build_deps()
    with get_sessionmaker()() as session:
        n = pipeline.purge_expired_raw(session, deps.storage)
    log.info("retencia: zmazaných %s raw dokumentov", n)
