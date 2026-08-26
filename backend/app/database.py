"""PostgreSQL connection pool + schema init (asyncpg, $1 params)."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Sequence

import asyncpg
from loguru import logger

from app.config import settings

_pool: Optional[asyncpg.Pool] = None


async def _init_connection(conn: asyncpg.Connection):
    await conn.set_type_codec("jsonb", encoder=json.dumps, decoder=json.loads, schema="pg_catalog")
    await conn.set_type_codec("json", encoder=json.dumps, decoder=json.loads, schema="pg_catalog")


async def init_db():
    global _pool
    _pool = await asyncpg.create_pool(
        host=settings.PG_HOST, port=settings.PG_PORT,
        database=settings.PG_DB, user=settings.PG_USER, password=settings.PG_PASSWORD,
        min_size=settings.PG_POOL_MIN, max_size=settings.PG_POOL_MAX,
        init=_init_connection,
    )
    await schema_init()
    logger.info(f"PostgreSQL pool ready | {settings.PG_HOST}:{settings.PG_PORT}/{settings.PG_DB}")


async def close_db():
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


def _get_pool() -> asyncpg.Pool:
    if _pool is None:
        raise RuntimeError("DB pool not initialised - call init_db() first")
    return _pool


async def execute_query(query: str, params: Sequence[Any] = ()) -> List[Dict[str, Any]]:
    async with _get_pool().acquire() as conn:
        rows = await conn.fetch(query, *params)
    return [dict(r) for r in rows]


async def execute_one(query: str, params: Sequence[Any] = ()) -> Optional[Dict[str, Any]]:
    async with _get_pool().acquire() as conn:
        row = await conn.fetchrow(query, *params)
    return dict(row) if row else None


async def execute_insert(query: str, params: Sequence[Any] = ()):
    async with _get_pool().acquire() as conn:
        return await conn.execute(query, *params)


async def schema_init():
    """幂等建表。"""
    await execute_insert("""
        CREATE TABLE IF NOT EXISTS users (
            username      TEXT PRIMARY KEY,
            display_name  TEXT NOT NULL DEFAULT '',
            department    TEXT NOT NULL DEFAULT '',
            email         TEXT NOT NULL DEFAULT '',
            auth_source   TEXT NOT NULL DEFAULT 'ldap',
            last_login_at TIMESTAMPTZ,
            login_count   INTEGER NOT NULL DEFAULT 0
        )
    """)
    await execute_insert("""
        CREATE TABLE IF NOT EXISTS login_lockouts (
            username        TEXT PRIMARY KEY,
            fail_count      INTEGER NOT NULL DEFAULT 0,
            locked_until    TIMESTAMPTZ,
            last_attempt_at TIMESTAMPTZ
        )
    """)
