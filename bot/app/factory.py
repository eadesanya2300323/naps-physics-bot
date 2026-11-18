import logging

from aiogram import Dispatcher
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ErrorEvent

from app.handlers import (
    admin_commands,
    admin_upload,
    browse,
    events,
    feedback,
    fyp,
    library,
    material,
    opportunities,
    search,
    start,
)
from app.middleware.access import AccessMiddleware

logger = logging.getLogger("naps.bot")


async def error_handler(event: ErrorEvent) -> None:
    logger.exception("Update failed", exc_info=event.exception)
    update = event.update
    try:
        if update.callback_query is not None and update.callback_query.message is not None:
            await update.callback_query.message.answer("Something went wrong. Try again.")
        elif update.message is not None:
            await update.message.answer("Something went wrong. Try again.")
    except TelegramBadRequest:
        pass


def build_dispatcher(db, settings, bucket) -> Dispatcher:
    dispatcher = Dispatcher(storage=MemoryStorage(), db=db, settings=settings, bucket=bucket)
    middleware = AccessMiddleware()
    dispatcher.message.middleware(middleware)
    dispatcher.callback_query.middleware(middleware)
    dispatcher.include_routers(
        start.router,
        browse.router,
        search.router,
        material.router,
        library.router,
        opportunities.router,
        fyp.router,
        feedback.router,
        events.router,
        admin_upload.router,
        admin_commands.router,
    )
    dispatcher.errors.register(error_handler)
    return dispatcher
