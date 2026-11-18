import ssl
from contextlib import asynccontextmanager
from urllib.parse import parse_qs, urlparse, urlunparse

import asyncpg


def prepare_dsn(dsn: str) -> tuple[str, ssl.SSLContext | bool]:
    parsed = urlparse(dsn)
    query = parse_qs(parsed.query)
    sslmode = (query.get("sslmode", [""])[0] or query.get("ssl", [""])[0] or "require").lower()
    clean = urlunparse(parsed._replace(query="", params="", fragment=""))
    if sslmode in {"disable", "allow"}:
        return clean, False
    return clean, ssl.create_default_context()


class Database:
    def __init__(self, dsn: str):
        self._dsn = dsn
        self._pool: asyncpg.Pool | None = None

    @property
    def pool(self) -> asyncpg.Pool:
        if self._pool is None:
            raise RuntimeError("Database is not connected")
        return self._pool

    async def connect(self) -> None:
        dsn, ssl_context = prepare_dsn(self._dsn)
        self._pool = await asyncpg.create_pool(
            dsn=dsn,
            ssl=ssl_context,
            min_size=1,
            max_size=5,
            statement_cache_size=0,
            command_timeout=30,
        )

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None

    async def fetch(self, query: str, *args) -> list[asyncpg.Record]:
        return await self.pool.fetch(query, *args)

    async def fetchrow(self, query: str, *args) -> asyncpg.Record | None:
        return await self.pool.fetchrow(query, *args)

    async def fetchval(self, query: str, *args):
        return await self.pool.fetchval(query, *args)

    async def execute(self, query: str, *args) -> str:
        return await self.pool.execute(query, *args)

    @asynccontextmanager
    async def transaction(self):
        async with self.pool.acquire() as connection, connection.transaction():
            yield connection
