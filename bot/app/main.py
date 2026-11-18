import logging
import secrets
from contextlib import asynccontextmanager

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import Update
from fastapi import FastAPI, Header, HTTPException, Request

from app.config import get_settings
from app.db import Database
from app.factory import build_dispatcher
from app.menus import set_commands
from app.services import jobs
from app.services import opportunities as opportunities_store
from app.services.bootstrap import ensure_owner
from app.services.storage import SupabaseStorage

logger = logging.getLogger("naps.web")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    db = Database(settings.database_url)
    await db.connect()
    bot = Bot(settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    bucket = SupabaseStorage(settings.supabase_url, settings.supabase_service_role_key, settings.storage_bucket)
    dispatcher = build_dispatcher(db, settings, bucket)

    await ensure_owner(db, settings.owner_id)
    if settings.public_url.startswith("https://"):
        await bot.set_webhook(f"{settings.public_url.rstrip('/')}/webhook/{settings.webhook_secret}")
    await set_commands(bot, db)

    app.state.settings = settings
    app.state.db = db
    app.state.bot = bot
    app.state.bucket = bucket
    app.state.dispatcher = dispatcher
    try:
        yield
    finally:
        await bot.session.close()
        await bucket.close()
        await db.close()


app = FastAPI(lifespan=lifespan, title="NAPS Physics Library bot", docs_url=None, redoc_url=None)


@app.get("/")
async def root() -> dict:
    return {"service": "NAPS Physics Library bot"}


@app.get("/health")
async def health(request: Request) -> dict:
    db: Database = request.app.state.db
    try:
        materials = await db.fetchval("select count(*) from materials")
        students = await db.fetchval("select count(*) from students")
    except Exception:
        logger.exception("Health check failed")
        raise HTTPException(status_code=503, detail="Database is not reachable")
    return {"ok": True, "materials": materials, "students": students}


@app.post("/cron/tick")
async def cron_tick(request: Request, x_cron_secret: str = Header(default="")) -> dict:
    settings = request.app.state.settings
    if not secrets.compare_digest(x_cron_secret, settings.cron_secret):
        raise HTTPException(status_code=401, detail="Bad cron secret")
    db: Database = request.app.state.db
    await db.fetchval("select 1")
    queued = await jobs.process(db, request.app.state.bot)
    archived = await opportunities_store.archive_expired(db)
    return {"ok": True, "jobs": queued, "opportunities_archived": archived}


@app.post("/webhook/{secret}")
async def webhook(secret: str, request: Request) -> dict:
    settings = request.app.state.settings
    if not secrets.compare_digest(secret, settings.webhook_secret):
        raise HTTPException(status_code=403, detail="Bad webhook secret")

    payload = await request.json()
    bot: Bot = request.app.state.bot
    dispatcher = request.app.state.dispatcher
    update = Update.model_validate(payload, context={"bot": bot})
    try:
        await dispatcher.feed_update(bot, update)
    except Exception:
        logger.exception("Update %s failed", update.update_id)
    return {"ok": True}
