import logging
from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from bot.config import load_config
from bot.database import db

router = Router()
logger = logging.getLogger(__name__)
config = load_config()


@router.message(Command("auto_approve"))
async def cmd_auto_approve(message: Message, command: CommandObject):
    if message.from_user.id not in config.admins:
        return

    arg = command.args.lower() if command.args else None

    if arg in ("on", "вкл"):
        await db.set_setting("auto_approve", "true")
        await message.answer("✅ Автоматическое одобрение заявок включено.")
        logger.info(f"Пользователь {message.from_user.id} включил auto_approve")
    elif arg in ("off", "выкл"):
        await db.set_setting("auto_approve", "false")
        await message.answer("❌ Автоматическое одобрение заявок отключено.")
        logger.info(f"Пользователь {message.from_user.id} отключил auto_approve")
    else:
        value = await db.get_setting("auto_approve")
        current_state = "включено ✅" if value == "true" else "отключено ❌"
        await message.answer(
            f"Текущее состояние автоматического одобрения: {current_state}\n"
            "Используйте /auto_approve on|вкл или /auto_approve off|выкл для изменения."
        )


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    if message.from_user.id not in config.admins:
        return

    current_state = await state.get_state()
    if current_state is None:
        await message.answer("🚫 Нет активного действия для отмены.")
        return

    await state.clear()
    await message.answer("🚫 Действие отменено.")
    logger.info(f"Пользователь {message.from_user.id} сбросил состояние: {current_state}")


@router.message(Command("help"))
async def cmd_help(message: Message):
    if message.from_user.id not in config.admins:
        return

    help_text = (
        "📋 Список доступных команд:\n\n"
        "/help — Показать это сообщение\n"
        "/auto_approve on|вкл — Включить автоматическое одобрение заявок\n"
        "/auto_approve off|выкл — Отключить автоматическое одобрение заявок\n"
        "/auto_approve — Проверить текущее состояние\n"
        "/cancel — Отменить текущее действие\n"
        "/broadcast — Отправить сообщение всем пользователям, которым бот уже писал"
    )
    await message.answer(help_text)


async def is_auto_approve_enabled() -> bool:
    value = await db.get_setting("auto_approve")
    return value == "true"
