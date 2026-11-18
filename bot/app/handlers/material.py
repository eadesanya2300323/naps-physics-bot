from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery

from app import texts
from app.keyboards import material_keyboard
from app.services import catalog
from app.services.materials import back_target, deliver

router = Router(name="material")


@router.callback_query(F.data.startswith("mat:"))
async def open_material(callback: CallbackQuery, student: dict, db, bucket, settings) -> None:
    try:
        material_id = int(callback.data.split(":")[1])
    except (IndexError, ValueError):
        await callback.answer()
        return
    await callback.answer()
    material = await catalog.material(db, material_id)
    if material is None:
        await callback.message.answer(texts.material_removed_missing())
        return
    await catalog.touch_recent(db, student["id"], material_id)
    await deliver(callback.bot, db, bucket, settings, callback.message.chat.id, dict(material), student["id"])


@router.callback_query(F.data.startswith("fav:"))
async def toggle_save(callback: CallbackQuery, student: dict, db, settings) -> None:
    try:
        material_id = int(callback.data.split(":")[1])
    except (IndexError, ValueError):
        await callback.answer()
        return
    material = await catalog.material(db, material_id)
    if material is None:
        await callback.answer(texts.material_removed_missing(), show_alert=True)
        return
    saved = await catalog.toggle_favourite(db, student["id"], material_id)
    row = dict(material)
    back_label, back_data = back_target(row)
    try:
        await callback.message.edit_reply_markup(
            reply_markup=material_keyboard(row, settings.site_url, saved, back_label, back_data)
        )
    except TelegramBadRequest:
        pass
    await callback.answer(texts.saved_on() if saved else texts.saved_off())
