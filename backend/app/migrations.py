import os
from pathlib import Path

from .db import get_connection


def migration_directory() -> Path:
    env_path = os.getenv("DB_MIGRATIONS_DIR")
    candidates = [
        Path(env_path) if env_path else None,
        Path("/app/database/migrations"),
        Path(__file__).resolve().parents[2] / "database" / "migrations",
        Path.cwd() / "database" / "migrations",
    ]
    for candidate in candidates:
        if candidate and candidate.exists():
            return candidate
    raise RuntimeError("DB migration directory could not be found.")


def ensure_schema_migrations_table() -> None:
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version VARCHAR(120) PRIMARY KEY,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )


def applied_migration_versions() -> set[str]:
    ensure_schema_migrations_table()
    with get_connection() as conn:
        rows = conn.execute("SELECT version FROM schema_migrations").fetchall()
    return {row["version"] for row in rows}


def run_migrations() -> None:
    migrations_dir = migration_directory()
    applied_versions = applied_migration_versions()

    for migration_path in sorted(migrations_dir.glob("*.sql")):
        version = migration_path.stem
        if version in applied_versions:
            continue

        sql = migration_path.read_text(encoding="utf-8").strip()
        if not sql:
            continue

        with get_connection() as conn:
            conn.execute(sql)
            conn.execute(
                "INSERT INTO schema_migrations (version) VALUES (%s)",
                [version],
            )
