import re
from datetime import date

from app.services.opportunities import parse_url

MAX_TITLE = 120
MAX_BODY = 800


def parse_event_date(value: str | None) -> date | None:
    if not value:
        return None
    text = value.strip()
    if not text:
        return None
    match = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", text)
    if not match:
        raise ValueError("Send the date as 2026-12-05, or tap Skip.")
    try:
        return date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
    except ValueError as error:
        raise ValueError("That date does not exist.") from error


def parse_event_line(value: str) -> tuple[str, str, date | None, str | None]:
    parts = [part.strip() for part in value.split("|")]
    if len(parts) < 2:
        raise ValueError("Send /addevent Title | URL | YYYY-MM-DD | Description")
    title = re.sub(r"\s+", " ", parts[0]).strip()
    if not title or len(title) > MAX_TITLE:
        raise ValueError("The title must be between 1 and 120 characters.")
    url = parse_url(parts[1])
    if url is None:
        raise ValueError("A link is required.")
    event_date = parse_event_date(parts[2]) if len(parts) > 2 else None
    description = parts[3] if len(parts) > 3 and parts[3] else None
    if description and len(description) > MAX_BODY:
        raise ValueError("The description must be 800 characters or fewer.")
    return title, url, event_date, description


async def listing(db, active: bool):
    return await db.fetch(
        "select * from event_links where active = $1 order by event_date nulls last, id desc",
        active,
    )


async def one(db, identifier: int):
    return await db.fetchrow("select * from event_links where id = $1", identifier)


async def create(db, title: str, url: str, event_date, description) -> int:
    return await db.fetchval(
        "insert into event_links (title, url, event_date, description) values ($1, $2, $3, $4) returning id",
        title,
        url,
        event_date,
        description,
    )


async def set_active(db, identifier: int, active: bool) -> None:
    await db.execute("update event_links set active = $2 where id = $1", identifier, active)
