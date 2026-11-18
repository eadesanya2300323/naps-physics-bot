import json
from datetime import UTC, datetime

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandObject
from aiogram.types import BufferedInputFile, CallbackQuery, Message

from app import texts
from app.keyboards import confirm_keyboard
from app.menus import set_admin_commands
from app.services import audit, catalog, settings_store
from app.services.caption import CaptionError, parse_course_line
from app.services.permissions import ROLES, can, is_admin
from app.services.telegram import acknowledge, edit_message

router = Router(name="admin_commands")

BACKUP_TABLES = ("students", "admins", "courses", "materials", "usage_events", "audit_log", "settings")


async def refuse(message: Message) -> None:
    await message.answer("Your role cannot do that.")


def integers(value: str | None) -> list[int]:
    return [int(token) for token in (value or "").split() if token.lstrip("-").isdigit()]


@router.message(Command("addcourse"))
async def add_course(message: Message, command: CommandObject, db, admin_role: str | None) -> None:
    if not can(admin_role, "courses"):
        await refuse(message)
        return
    try:
        code, title, level, semester = parse_course_line(command.args or "")
    except CaptionError as error:
        await message.answer(f"{error}\nSend /addcourse PHY201 | Optics | 200 | 1")
        return

    existing = await catalog.course(db, code)
    if existing:
        await db.execute(
            "update courses set title = $2, level = $3, semester = $4 where code = $1",
            code,
            title,
            level,
            semester,
        )
        await audit.record(db, message.from_user.id, "course.update", code)
        await message.answer(texts.course_updated(code, title, level))
        return

    await db.execute(
        "insert into courses (code, title, level, semester) values ($1, $2, $3, $4)",
        code,
        title,
        level,
        semester,
    )
    await audit.record(db, message.from_user.id, "course.create", code)
    await message.answer(texts.course_added(code, title, level))


@router.message(Command("addadmin"))
async def add_admin(message: Message, command: CommandObject, db, admin_role: str | None) -> None:
    if not can(admin_role, "admins"):
        await refuse(message)
        return
    tokens = (command.args or "").split()
    if len(tokens) != 2 or not tokens[0].isdigit() or tokens[1] not in ROLES:
        await message.answer("Send /addadmin <telegram id> <super|moderator|uploader>")
        return
    telegram_id = int(tokens[0])
    role = tokens[1]
    await db.execute(
        "insert into admins (telegram_id, role, added_by) values ($1, $2, $3) "
        "on conflict (telegram_id) do update set role = excluded.role",
        telegram_id,
        role,
        message.from_user.id,
    )
    await audit.record(db, message.from_user.id, "admin.add", f"{telegram_id}:{role}")
    await set_admin_commands(message.bot, telegram_id)
    await message.answer(texts.admin_added(telegram_id, role))


@router.message(Command("rmadmin"))
async def remove_admin(message: Message, command: CommandObject, db, admin_role: str | None, settings) -> None:
    if not can(admin_role, "admins"):
        await refuse(message)
        return
    target = integers(command.args)
    if not target:
        await message.answer("Send /rmadmin <telegram id>")
        return
    if target[0] == settings.owner_id:
        await message.answer(texts.owner_protected())
        return
    await db.execute("delete from admins where telegram_id = $1", target[0])
    await audit.record(db, message.from_user.id, "admin.remove", str(target[0]))
    await message.answer(texts.admin_removed(target[0]))


@router.message(Command("admins"))
async def list_admins(message: Message, db, admin_role: str | None) -> None:
    if not is_admin(admin_role):
        await refuse(message)
        return
    rows = await db.fetch("select telegram_id, role from admins order by role, telegram_id")
    await message.answer(texts.admin_list(rows))


@router.message(Command("ban"))
async def ban_student(message: Message, command: CommandObject, db, admin_role: str | None) -> None:
    if not can(admin_role, "moderation"):
        await refuse(message)
        return
    target = integers(command.args)
    if not target:
        await message.answer("Send /ban <telegram id>")
        return
    changed = await db.fetchval("update students set banned = true where telegram_id = $1 returning id", target[0])
    if changed is None:
        await message.answer(texts.student_missing())
        return
    await audit.record(db, message.from_user.id, "student.ban", str(target[0]))
    await message.answer(texts.student_banned(target[0]))


@router.message(Command("unban"))
async def unban_student(message: Message, command: CommandObject, db, admin_role: str | None) -> None:
    if not can(admin_role, "moderation"):
        await refuse(message)
        return
    target = integers(command.args)
    if not target:
        await message.answer("Send /unban <telegram id>")
        return
    changed = await db.fetchval(
        "update students set banned = false, active = true where telegram_id = $1 returning id",
        target[0],
    )
    if changed is None:
        await message.answer(texts.student_missing())
        return
    await audit.record(db, message.from_user.id, "student.unban", str(target[0]))
    await message.answer(texts.student_unbanned(target[0]))


@router.message(Command("mute"))
async def mute_student(message: Message, command: CommandObject, db, admin_role: str | None) -> None:
    if not can(admin_role, "moderation"):
        await refuse(message)
        return
    target = integers(command.args)
    if len(target) != 2:
        await message.answer("Send /mute <telegram id> <minutes>")
        return
    telegram_id, minutes = target
    changed = await db.fetchval(
        "update students set muted_until = now() + make_interval(mins => $2::int) "
        "where telegram_id = $1 returning id",
        telegram_id,
        minutes,
    )
    if changed is None:
        await message.answer(texts.student_missing())
        return
    await audit.record(db, message.from_user.id, "student.mute", f"{telegram_id}:{minutes}")
    await message.answer(texts.student_muted(telegram_id, minutes))


@router.message(Command("maintenance"))
async def maintenance(message: Message, command: CommandObject, db, admin_role: str | None) -> None:
    if not can(admin_role, "maintenance"):
        await refuse(message)
        return
    value = (command.args or "").strip()
    if not value:
        await message.answer("Send /maintenance <message> to pause the bot, or /maintenance off to resume it.")
        return
    if value.lower() == "off":
        await settings_store.clear_maintenance(db)
        await audit.record(db, message.from_user.id, "maintenance.off")
        await message.answer(texts.maintenance_off())
        return
    await settings_store.set_maintenance(db, value[:400])
    await audit.record(db, message.from_user.id, "maintenance.on")
    await message.answer(texts.maintenance_set(value[:400]))


@router.message(Command("backup"))
async def backup(message: Message, db, admin_role: str | None) -> None:
    if not can(admin_role, "backup"):
        await refuse(message)
        return
    payload = {}
    for table in BACKUP_TABLES:
        rows = await db.fetch(f"select * from {table}")
        payload[table] = [dict(row) for row in rows]
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    document = BufferedInputFile(json.dumps(payload, default=str, indent=1).encode("utf-8"), filename=f"naps-backup-{stamp}.json")
    await message.answer_document(document, caption="Backup of every table.")
    await audit.record(db, message.from_user.id, "backup.export")


@router.message(Command("transferowner"))
async def transfer_owner(message: Message, command: CommandObject, db, admin_role: str | None) -> None:
    if not can(admin_role, "ownership"):
        await refuse(message)
        return
    target = integers(command.args)
    if not target:
        await message.answer("Send /transferowner <telegram id>")
        return
    await message.answer(
        texts.owner_transfer_prompt(target[0]),
        reply_markup=confirm_keyboard("own", str(target[0])),
    )


@router.callback_query(F.data.startswith("own:"))
async def owner_confirmation(callback: CallbackQuery, db, admin_role: str | None) -> None:
    if not can(admin_role, "ownership"):
        await acknowledge(callback)
        return
    parts = callback.data.split(":")
    if len(parts) != 3 or not parts[2].isdigit():
        await acknowledge(callback)
        return
    target = int(parts[2])
    await acknowledge(callback)
    if parts[1] == "no":
        await edit_message(callback.message, texts.owner_transfer_cancelled())
        return
    await db.execute(
        "insert into admins (telegram_id, role, added_by) values ($1, 'super', $2) "
        "on conflict (telegram_id) do update set role = 'super'",
        target,
        callback.from_user.id,
    )
    await audit.record(db, callback.from_user.id, "owner.transfer", str(target))
    await edit_message(callback.message, texts.owner_transferred(target))
    if callback.bot is not None:
        try:
            await callback.bot.send_message(target, "You are now the owner of the NAPS Physics Library bot.")
        except TelegramBadRequest:
            pass
