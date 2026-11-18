from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import BotCommand, BotCommandScopeChat, BotCommandScopeDefault

STUDENT_MENU = (
    ("start", "Pick your level"),
    ("browse", "Browse the library"),
    ("search", "Search by code or title"),
    ("pq", "Past questions for a course"),
    ("library", "Files you saved"),
    ("recent", "Files you opened last"),
    ("pack", "Key files for a level"),
    ("opportunities", "Internships and scholarships"),
    ("templates", "Lab and project templates"),
    ("fyp", "Project topics"),
    ("events", "Merch and ticket links"),
    ("feedback", "Send a message to admins"),
    ("notify", "New-file alerts"),
    ("help", "Command list"),
)

ADMIN_MENU = STUDENT_MENU + (
    ("addcourse", "Add or update a course"),
    ("addopportunity", "Post an opportunity"),
    ("addfyp", "Add a project topic"),
    ("addevent", "Add an event link"),
    ("inbox", "Feedback and reports"),
    ("addadmin", "Give someone admin access"),
    ("rmadmin", "Remove an admin"),
    ("admins", "List admins"),
    ("ban", "Block a student"),
    ("unban", "Unblock a student"),
    ("mute", "Mute a student"),
    ("maintenance", "Pause or resume the bot"),
    ("backup", "Download a JSON backup"),
    ("transferowner", "Hand over ownership"),
)


def build_commands(menu) -> list[BotCommand]:
    return [BotCommand(command=name, description=description) for name, description in menu]


async def set_commands(bot: Bot, db) -> None:
    await bot.set_my_commands(build_commands(STUDENT_MENU), scope=BotCommandScopeDefault())
    admins = await db.fetch("select telegram_id from admins")
    for row in admins:
        await set_admin_commands(bot, row["telegram_id"])


async def set_admin_commands(bot: Bot, telegram_id: int) -> None:
    try:
        await bot.set_my_commands(build_commands(ADMIN_MENU), scope=BotCommandScopeChat(chat_id=telegram_id))
    except TelegramBadRequest:
        return
