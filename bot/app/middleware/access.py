from collections.abc import Awaitable, Callable
from time import monotonic
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, TelegramObject

from app import texts
from app.services import settings_store


class AccessMiddleware(BaseMiddleware):
    def __init__(self, throttle_seconds: float = 1.0):
        self._throttle_seconds = throttle_seconds
        self._last_event: dict[int, float] = {}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        if user is None:
            return await handler(event, data)

        db = data["db"]
        display_name = " ".join(part for part in (user.first_name, user.last_name) if part) or None
        student = await db.fetchrow(
            "insert into students (telegram_id, username, display_name, last_seen) values ($1, $2, $3, now()) "
            "on conflict (telegram_id) do update set username = excluded.username, "
            "display_name = excluded.display_name, last_seen = now(), active = true returning *",
            user.id,
            user.username,
            display_name,
        )
        if student["banned"]:
            return None

        role = await db.fetchval("select role from admins where telegram_id = $1", user.id)

        if role is None:
            maintenance = await settings_store.maintenance_message(db)
            if maintenance:
                notice = texts.maintenance_notice(maintenance)
                if isinstance(event, CallbackQuery):
                    await event.answer(notice[:190], show_alert=True)
                else:
                    await event.answer(notice)
                return None

        now = monotonic()
        previous = self._last_event.get(user.id, 0.0)
        if now - previous < self._throttle_seconds:
            if isinstance(event, CallbackQuery):
                await event.answer()
            return None
        self._last_event[user.id] = now

        if len(self._last_event) > 5000:
            self._last_event.clear()

        kind = "callback" if isinstance(event, CallbackQuery) else "message"
        if isinstance(event, CallbackQuery):
            reference = (event.data or "")[:120]
        else:
            reference = ((getattr(event, "text", None) or "")[:120]) or None
        await db.execute(
            "insert into usage_events (student_id, source, kind, ref) values ($1, 'bot', $2, $3)",
            student["id"],
            kind,
            reference,
        )

        data["student"] = dict(student)
        data["admin_role"] = role
        return await handler(event, data)
