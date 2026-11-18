STATUSES = ("available", "taken", "completed")

STATUS_LABELS = {
    "available": "Available",
    "taken": "Taken",
    "completed": "Completed",
}


def status_label(status: str) -> str:
    return STATUS_LABELS.get(status, status.title())


def valid_status(value: str | None) -> str | None:
    if value is None:
        return None
    lowered = value.strip().lower()
    return lowered if lowered in STATUSES else None


def topic_line(topic) -> str:
    parts = [topic["title"]]
    if topic["supervisor"]:
        parts.append(topic["supervisor"])
    if topic["year"]:
        parts.append(str(topic["year"]))
    parts.append(status_label(topic["status"]))
    return " · ".join(parts)


async def page(db, status: str, supervisor, area, year, keyword, offset: int, limit: int):
    pattern = f"%{keyword}%" if keyword else None
    total = await db.fetchval(
        "select count(*) from fyp_topics where status = $1 "
        "and ($2::text is null or supervisor = $2) and ($3::text is null or area = $3) "
        "and ($4::int is null or year = $4) and ($5::text is null or title ilike $5)",
        status,
        supervisor,
        area,
        year,
        pattern,
    )
    rows = await db.fetch(
        "select * from fyp_topics where status = $1 "
        "and ($2::text is null or supervisor = $2) and ($3::text is null or area = $3) "
        "and ($4::int is null or year = $4) and ($5::text is null or title ilike $5) "
        "order by created_at desc limit $6 offset $7",
        status,
        supervisor,
        area,
        year,
        pattern,
        limit,
        offset,
    )
    return rows, total


async def one(db, identifier: int):
    return await db.fetchrow("select * from fyp_topics where id = $1", identifier)


async def create(db, title: str, supervisor, year, area, description, created_by: int) -> int:
    return await db.fetchval(
        "insert into fyp_topics (title, supervisor, year, area, description, created_by) "
        "values ($1, $2, $3, $4, $5, $6) returning id",
        title,
        supervisor,
        year,
        area,
        description,
        created_by,
    )


async def set_status(db, identifier: int, status: str) -> None:
    await db.execute("update fyp_topics set status = $2 where id = $1", identifier, status)


async def remove(db, identifier: int) -> None:
    await db.execute("delete from fyp_topics where id = $1", identifier)


async def supervisors(db, status: str) -> list[str]:
    rows = await db.fetch(
        "select distinct supervisor from fyp_topics where status = $1 and supervisor is not null order by supervisor",
        status,
    )
    return [row["supervisor"] for row in rows]


async def areas(db, status: str) -> list[str]:
    rows = await db.fetch(
        "select distinct area from fyp_topics where status = $1 and area is not null order by area",
        status,
    )
    return [row["area"] for row in rows]


async def years(db, status: str) -> list[int]:
    rows = await db.fetch(
        "select distinct year from fyp_topics where status = $1 and year is not null order by year desc",
        status,
    )
    return [row["year"] for row in rows]
