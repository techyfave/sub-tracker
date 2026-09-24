from __future__ import annotations

import asyncio
import os
import subprocess
import sys

import asyncpg
import pytest

EXPECTED_CORE_TABLES = {
    "actions",
    "analyses",
    "audit_events",
    "consents",
    "conversations",
    "evaluation_results",
    "evaluation_runs",
    "messages",
    "plans",
    "prompt_versions",
    "provider_connections",
    "providers",
    "recommendation_decisions",
    "recommendation_evidence",
    "recommendations",
    "savings_records",
    "subscriptions",
    "transactions",
    "usage_events",
}


def _database_urls() -> tuple[str, str]:
    async_url = os.getenv("TEST_DATABASE_URL", "")
    if not async_url:
        pytest.skip("TEST_DATABASE_URL is required for PostgreSQL migration tests")
    return async_url, async_url.replace("postgresql+asyncpg://", "postgresql://", 1)


def _alembic(*arguments: str, database_url: str) -> None:
    environment = {**os.environ, "DATABASE_URL": database_url}
    subprocess.run(
        [sys.executable, "-m", "alembic", *arguments],
        check=True,
        env=environment,
        capture_output=True,
        text=True,
    )


async def _table_names(dsn: str) -> set[str]:
    connection = await asyncpg.connect(dsn)
    try:
        rows = await connection.fetch("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
        return {row["tablename"] for row in rows}
    finally:
        await connection.close()


def test_upgrade_and_downgrade_round_trip_against_postgresql() -> None:
    async_url, asyncpg_dsn = _database_urls()

    _alembic("downgrade", "base", database_url=async_url)
    _alembic("upgrade", "head", database_url=async_url)
    assert asyncio.run(_table_names(asyncpg_dsn)) >= EXPECTED_CORE_TABLES

    _alembic("downgrade", "0c979cdd5fa8", database_url=async_url)
    remaining = asyncio.run(_table_names(asyncpg_dsn))
    assert not EXPECTED_CORE_TABLES.intersection(remaining)
    assert {"users", "refresh_tokens"} <= remaining

    _alembic("upgrade", "head", database_url=async_url)
