from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker
from sqlalchemy.pool import StaticPool

from src.backend.config import settings

Base = declarative_base()


def _engine_options(database_url: str) -> dict:
    if database_url.startswith("sqlite"):
        options: dict = {"connect_args": {"check_same_thread": False}}
        if database_url == "sqlite:///:memory:":
            options["poolclass"] = StaticPool
        return options
    return {"pool_pre_ping": True}


def _create_engine(database_url: str) -> Engine:
    return create_engine(database_url, future=True, **_engine_options(database_url))


engine = _create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def configure_database(database_url: str) -> None:
    global engine, SessionLocal
    engine.dispose()
    engine = _create_engine(database_url)
    SessionLocal.configure(bind=engine)


@contextmanager
def session_scope() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_database(*, seed_admins: bool = True) -> None:
    from src.backend.application.services.auth_service import seed_bootstrap_admins
    from src.backend.infrastructure import models  # noqa: F401

    settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
    _reset_legacy_hierarchy_schema()
    Base.metadata.create_all(bind=engine)
    _ensure_incremental_schema()
    if seed_admins:
        seed_bootstrap_admins()


def _reset_legacy_hierarchy_schema() -> None:
    inspector = inspect(engine)
    if "hierarchy_nodes" not in inspector.get_table_names():
        return
    column_names = {column["name"] for column in inspector.get_columns("hierarchy_nodes")}
    has_assigned_user_schema = {"display_name", "assigned_user_id"}.issubset(column_names)
    has_legacy_schema = bool({"title", "node_type"} & column_names)
    if has_assigned_user_schema and not has_legacy_schema:
        return

    with engine.begin() as connection:
        connection.execute(text("DROP TABLE IF EXISTS hierarchy_connections"))
        connection.execute(text("DROP TABLE IF EXISTS hierarchy_nodes"))


def _ensure_incremental_schema() -> None:
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    if "workspace_members" in table_names:
        column_names = {column["name"] for column in inspector.get_columns("workspace_members")}
        if "connector_manager" not in column_names:
            with engine.begin() as connection:
                connection.execute(
                    text("ALTER TABLE workspace_members ADD COLUMN connector_manager BOOLEAN NOT NULL DEFAULT 0")
                )
