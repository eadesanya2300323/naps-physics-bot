async def record(db, actor: int, action: str, target: str | None = None) -> None:
    await db.execute(
        "insert into audit_log (actor, action, target) values ($1, $2, $3)",
        actor,
        action,
        target,
    )
