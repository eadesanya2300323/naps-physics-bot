import asyncio
import logging

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.config import get_settings
from app.db import Database
from app.factory import build_dispatcher
from app.menus import set_commands
from app.services.bootstrap import ensure_owner
from app.services.storage import SupabaseStorage

logger = logging.getLogger("naps.poll")


async def main() -> None:
    settings = get_settings()
    db = Database(settings.database_url)
    await db.connect()
    bot = Bot(settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    bucket = SupabaseStorage(settings.supabase_url, settings.supabase_service_role_key, settings.storage_bucket)
    dispatcher = build_dispatcher(db, settings, bucket)

    await ensure_owner(db, settings.owner_id)
    await bot.delete_webhook()
    await set_commands(bot, db)

    try:
        await dispatcher.start_polling(bot)
    finally:
        await bot.session.close()
        await bucket.close()
        await db.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    asyncio.run(main())
