"""CLI na správu zdrojov a ručné spustenie ingestion.

Príklady:
  smartgrocery migrate
  smartgrocery add-store --code lidl --name Lidl --website https://www.lidl.cz
  smartgrocery add-source --store lidl --url https://.../letak.pdf --kind pdf \\
      --legal-status approved --legal-note "Podmienky webu posúdené 2026-09-24"
  smartgrocery check 1 --valid-from 2026-09-24 --valid-to 2026-09-30
"""

import argparse
import logging
import sys
from datetime import date
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import select, text

from app.db import get_engine, get_sessionmaker
from app.deps import build_deps
from app.ingestion import pipeline
from app.models import LEGAL_STATUSES, SOURCE_KINDS, SourceEndpoint, Store

BACKEND_DIR = Path(__file__).resolve().parent.parent


def _alembic_ini() -> Path:
    # v Dockeri je balík nainštalovaný v site-packages, alembic.ini leží v pracovnom adresári
    for candidate in (Path.cwd() / "alembic.ini", BACKEND_DIR / "alembic.ini"):
        if candidate.exists():
            return candidate
    sys.exit("alembic.ini sa nenašiel – spusti príkaz z adresára backend/")


def cmd_migrate(_: argparse.Namespace) -> None:
    ini = _alembic_ini()
    cfg = Config(str(ini))
    cfg.set_main_option("script_location", str(ini.parent / "alembic"))
    command.upgrade(cfg, "head")
    with get_engine().connect() as conn:
        has_queue = conn.scalar(text("SELECT to_regclass('public.procrastinate_jobs') IS NOT NULL"))
    if not has_queue:
        from app.worker import app as worker_app

        with worker_app.open():
            worker_app.schema_manager.apply_schema()
        print("procrastinate schéma aplikovaná")
    print("DB je aktuálna")


def cmd_add_store(a: argparse.Namespace) -> None:
    with get_sessionmaker()() as s:
        store = Store(code=a.code, name=a.name, website=a.website)
        s.add(store)
        s.commit()
        print(f"store id={store.id}")


def cmd_add_source(a: argparse.Namespace) -> None:
    with get_sessionmaker()() as s:
        store = s.scalar(select(Store).where(Store.code == a.store))
        if store is None:
            sys.exit(f"Obchod '{a.store}' neexistuje")
        src = SourceEndpoint(
            store_id=store.id,
            kind=a.kind,
            adapter="manual",
            url=a.url,
            legal_status=a.legal_status,
            legal_note=a.legal_note,
            legal_reviewed_at=date.today() if a.legal_status != "pending" else None,
            terms_url=a.terms_url,
            robots_url=a.robots_url,
            check_interval_minutes=a.interval,
        )
        s.add(src)
        s.commit()
        print(f"source id={src.id} legal_status={src.legal_status}")


def cmd_set_legal(a: argparse.Namespace) -> None:
    with get_sessionmaker()() as s:
        src = s.get(SourceEndpoint, a.source_id)
        if src is None:
            sys.exit("Zdroj neexistuje")
        src.legal_status = a.status
        src.legal_note = a.note
        src.legal_reviewed_at = date.today()
        s.commit()
        print(f"source id={src.id} legal_status={src.legal_status}")


def _hint(a: argparse.Namespace) -> tuple[date, date] | None:
    if a.valid_from and a.valid_to:
        return date.fromisoformat(a.valid_from), date.fromisoformat(a.valid_to)
    if a.valid_from or a.valid_to:
        sys.exit("Zadaj --valid-from aj --valid-to")
    return None


def _print_run(run) -> None:
    print(
        f"run id={run.id} status={run.status} ponuky={run.offers_count} review={run.review_count} "
        f"zamietnuté={run.rejected_count} cena=${run.cost_usd:.4f}"
    )


def cmd_check(a: argparse.Namespace) -> None:
    deps = build_deps(Path(a.recorded) if a.recorded else None)
    with get_sessionmaker()() as s:
        _print_run(pipeline.check_source(s, a.source_id, deps, validity_hint=_hint(a), force=a.force))


def cmd_reextract(a: argparse.Namespace) -> None:
    deps = build_deps(Path(a.recorded) if a.recorded else None)
    with get_sessionmaker()() as s:
        _print_run(pipeline.reextract(s, a.raw_document_id, deps, validity_hint=_hint(a)))


def cmd_purge_raw(_: argparse.Namespace) -> None:
    deps = build_deps()
    with get_sessionmaker()() as s:
        print(f"zmazaných {pipeline.purge_expired_raw(s, deps.storage)} raw dokumentov")


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    p = argparse.ArgumentParser(prog="smartgrocery")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("migrate", help="Alembic upgrade + schéma fronty").set_defaults(fn=cmd_migrate)

    x = sub.add_parser("add-store")
    x.add_argument("--code", required=True)
    x.add_argument("--name", required=True)
    x.add_argument("--website")
    x.set_defaults(fn=cmd_add_store)

    x = sub.add_parser("add-source")
    x.add_argument("--store", required=True, help="kód obchodu")
    x.add_argument("--url", required=True, help="https://… alebo cesta k lokálnemu PDF/obrázku")
    x.add_argument("--kind", choices=SOURCE_KINDS, default="pdf")
    x.add_argument("--legal-status", choices=LEGAL_STATUSES, default="pending")
    x.add_argument("--legal-note")
    x.add_argument("--terms-url")
    x.add_argument("--robots-url")
    x.add_argument("--interval", type=int, default=30, help="minúty medzi kontrolami")
    x.set_defaults(fn=cmd_add_source)

    x = sub.add_parser("set-legal")
    x.add_argument("source_id", type=int)
    x.add_argument("--status", choices=LEGAL_STATUSES, required=True)
    x.add_argument("--note", required=True)
    x.set_defaults(fn=cmd_set_legal)

    for name, fn, arg in (("check", cmd_check, "source_id"), ("reextract", cmd_reextract, "raw_document_id")):
        x = sub.add_parser(name)
        x.add_argument(arg, type=int)
        x.add_argument("--valid-from")
        x.add_argument("--valid-to")
        x.add_argument("--recorded", help="JSON s nahranou odpoveďou modelu namiesto volania Claude")
        if name == "check":
            x.add_argument("--force", action="store_true", help="spracovať aj nezmenený obsah")
        x.set_defaults(fn=fn)

    sub.add_parser("purge-raw", help="zmazať raw dokumenty po retencii").set_defaults(fn=cmd_purge_raw)

    args = p.parse_args(argv)
    try:
        args.fn(args)
    except (pipeline.LegalStatusError, pipeline.CostLimitError, pipeline.ExtractionError, ValueError) as e:
        sys.exit(f"Chyba: {e}")


if __name__ == "__main__":
    main()
