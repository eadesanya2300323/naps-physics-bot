async def ensure_owner(db, owner_id: int) -> None:
    await db.execute(
        "insert into admins (telegram_id, role, added_by) values ($1, 'super', $1) "
        "on conflict (telegram_id) do update set role = 'super'",
        owner_id,
    )
