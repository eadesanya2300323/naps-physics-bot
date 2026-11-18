import re
from datetime import date

KINDS = ("internship", "scholarship", "siwes", "competition", "other")

KIND_LABELS = {
    "internship": "Internships",
    "scholarship": "Scholarships",
    "siwes": "SIWES",
    "competition": "Competitions",
    "other": "Other",
}

EDITABLE_FIELDS = ("title", "organisation", "deadline", "levels", "url", "description")

COLUMN_FOR_FIELD = {
    "title": "title",
    "organisation": "organisation",
    "deadline": "deadline",
    "levels": "levels",
    "url": "url",
    "description": "description",
    "kind": "kind",
}

LEVELS = ("100", "200", "300", "400")


def parse_deadline(value: str | None) -> date | None:
    if not value:
        return None
    text = value.strip()
    if not text:
        return None
    match = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", text)
    if not match:
        raise ValueError("Send the deadline as 2026-11-30, or tap Skip.")
    try:
        return date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
    except ValueError as error:
        raise ValueError("That date does not exist.") from error


def parse_levels(value: str | None) -> list[str] | None:
    if not value:
        return None
    text = re.sub(r"[,\s]+", " ", value).strip().lower()
    if not text or text == "all":
        return None
    tokens = [token.removesuffix("l") for token in text.split(" ")]
    chosen = [token for token in tokens if token in LEVELS]
    if not chosen:
        raise ValueError("Send levels as 200 300, or tap Skip.")
    return sorted(set(chosen))


def parse_url(value: str | None) -> str | None:
    if not value:
        return None
    text = value.strip()
    if not text:
        return None
    if not text.startswith(("http://", "https://")):
        raise ValueError("Send a link that starts with http:// or https://, or tap Skip.")
    if len(text) > 500:
        raise ValueError("That link is too long.")
    return text


def close_label(deadline: date | None) -> str:
    if deadline is None:
        return "No deadline"
    return f"Closes {deadline.strftime('%d %b %Y')}"


def days_left(deadline: date | None, today: date) -> int | None:
    if deadline is None:
        return None
    return (deadline - today).days


def is_open(archived: bool, deadline: date | None, today: date) -> bool:
    if archived:
        return False
    if deadline is None:
        return True
    return deadline >= today


def level_label(levels: list[str] | None) -> str:
    if not levels:
        return "All levels"
    return ", ".join(f"{level}L" for level in levels)


async def page(db, kind: str | None, offset: int, limit: int):
    total = await db.fetchval(
        "select count(*) from opportunities where archived = false "
        "and (deadline is null or deadline >= current_date) and ($1::text is null or kind = $1)",
        kind,
    )
    rows = await db.fetch(
        "select * from opportunities where archived = false "
        "and (deadline is null or deadline >= current_date) and ($1::text is null or kind = $1) "
        "order by deadline nulls last, created_at desc limit $2 offset $3",
        kind,
        limit,
        offset,
    )
    return rows, total


async def one(db, identifier: int):
    return await db.fetchrow("select * from opportunities where id = $1", identifier)


async def create(db, kind: str, title: str, organisation, deadline, levels, url, description, created_by: int) -> int:
    return await db.fetchval(
        "insert into opportunities (kind, title, organisation, deadline, levels, url, description, created_by) "
        "values ($1, $2, $3, $4, $5, $6, $7, $8) returning id",
        kind,
        title,
        organisation,
        deadline,
        levels,
        url,
        description,
        created_by,
    )


async def update_field(db, identifier: int, field: str, value) -> None:
    column = COLUMN_FOR_FIELD[field]
    await db.execute(f"update opportunities set {column} = $2 where id = $1", identifier, value)


async def archive(db, identifier: int) -> None:
    await db.execute("update opportunities set archived = true where id = $1", identifier)


async def remove(db, identifier: int) -> None:
    await db.execute("delete from opportunities where id = $1", identifier)


async def archive_expired(db) -> int:
    return int(
        await db.fetchval(
            "with expired as (update opportunities set archived = true "
            "where archived = false and deadline is not null and deadline < current_date returning 1) "
            "select count(*) from expired"
        )
    )
