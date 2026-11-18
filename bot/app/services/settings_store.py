MAINTENANCE_KEY = "maintenance_message"


async def get_value(db, key: str) -> str | None:
    return await db.fetchval("select value from settings where key = $1", key)


async def set_value(db, key: str, value: str) -> None:
    await db.execute(
        "insert into settings (key, value) values ($1, $2) "
        "on conflict (key) do update set value = excluded.value",
        key,
        value,
    )


async def clear_value(db, key: str) -> None:
    await db.execute("delete from settings where key = $1", key)


async def maintenance_message(db) -> str | None:
    return await get_value(db, MAINTENANCE_KEY)


async def set_maintenance(db, message: str) -> None:
    await set_value(db, MAINTENANCE_KEY, message)


async def clear_maintenance(db) -> None:
    await clear_value(db, MAINTENANCE_KEY)
