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


def init_database() -> None:
    from src.backend.infrastructure import models  # noqa: F401
    from src.backend.infrastructure import storage_models  # noqa: F401

    settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
    _reset_legacy_hierarchy_schema()
    Base.metadata.create_all(bind=engine)
    _ensure_incremental_schema()


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
    if "workspaces" in table_names:
        column_names = {column["name"] for column in inspector.get_columns("workspaces")}
        if "organization_id" not in column_names:
            with engine.begin() as connection:
                connection.execute(
                    text("ALTER TABLE workspaces ADD COLUMN organization_id VARCHAR(96)")
                )
        if "join_code" not in column_names:
            with engine.begin() as connection:
                connection.execute(
                    text("ALTER TABLE workspaces ADD COLUMN join_code VARCHAR(32)")
                )
                connection.execute(
                    text(
                        "CREATE UNIQUE INDEX IF NOT EXISTS ix_workspaces_join_code "
                        "ON workspaces (join_code)"
                    )
                )
    if "workspace_invites" not in table_names and "workspaces" in table_names:
        from src.backend.infrastructure import models

        Base.metadata.create_all(bind=engine, tables=[models.WorkspaceInvite.__table__])
        table_names.add("workspace_invites")
    if "workspace_invites" in table_names:
        column_names = {column["name"] for column in inspector.get_columns("workspace_invites")}
        if "join_token" not in column_names:
            with engine.begin() as connection:
                connection.execute(
                    text("ALTER TABLE workspace_invites ADD COLUMN join_token VARCHAR(64)")
                )
                connection.execute(
                    text(
                        "CREATE UNIQUE INDEX IF NOT EXISTS ix_workspace_invites_join_token "
                        "ON workspace_invites (join_token)"
                    )
                )
        if "expires_at" not in column_names:
            with engine.begin() as connection:
                connection.execute(
                    text("ALTER TABLE workspace_invites ADD COLUMN expires_at DATETIME")
                )
                connection.execute(
                    text(
                        "UPDATE workspace_invites "
                        "SET expires_at = datetime(created_at, '+7 days') "
                        "WHERE expires_at IS NULL"
                    )
                )
