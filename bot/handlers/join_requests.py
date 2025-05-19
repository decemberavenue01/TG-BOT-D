import logging
import os
from aiogram import Router, F, Bot
from aiogram.filters import Command, CommandObject
from aiogram.types import ChatJoinRequest, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.enums import ParseMode
from asyncio import sleep
from bot.config import ADMINS, WELCOME_MESSAGE
from bot.database import db
from utils.constants import WELCOME_MESSAGE_KEY, WELCOME_PHOTO_KEY, PARSE_MODE_KEY
from utils.helpers import deserialize_entities
from bot.handlers.admin import is_auto_approve_enabled
from bot.services.welcome import send_first_welcome


router = Router()
logger = logging.getLogger(__name__)


@router.chat_join_request()
async def process_join_request(join_request: ChatJoinRequest, bot: Bot):
    user = join_request.from_user
    chat = join_request.chat
    auto_approve = await is_auto_approve_enabled()

    welcome_message_template = await db.get_setting(WELCOME_MESSAGE_KEY) or WELCOME_MESSAGE
    photo_path = await db.get_setting(WELCOME_PHOTO_KEY)
    parse_mode_setting = await db.get_setting(PARSE_MODE_KEY) or "none"

    parse_mode = None
    entities = None

    if parse_mode_setting == "entities":
        welcome_message_template = await db.get_setting("welcome_message_formatted") or WELCOME_MESSAGE
        entities_str = await db.get_setting("welcome_message_entities")
        entities = deserialize_entities(entities_str)
    elif parse_mode_setting == "html":
        parse_mode = ParseMode.HTML
    elif parse_mode_setting == "markdown":
        parse_mode = ParseMode.MARKDOWN

    welcome_text = welcome_message_template.format(
        user_name=user.full_name,
        chat_title=chat.title or ""
    )

    try:
        request_id = await db.add_request(
            user_id=user.id,
            username=user.username,
            full_name=user.full_name,
            chat_id=chat.id,
            chat_title=chat.title or ""
        )

        # Отправляем приветственное сообщение пользователю
        try:
            if photo_path and os.path.exists(photo_path):
                await bot.send_photo(
                    chat_id=user.id,
                    photo=FSInputFile(photo_path),
                    caption=welcome_text,
                    parse_mode=parse_mode,
                    caption_entities=entities
                )
            else:
                await bot.send_message(
                    chat_id=user.id,
                    text=welcome_text,
                    parse_mode=parse_mode,
                    entities=entities
                )
            logger.info(f"Отправлено приветственное сообщение пользователю {user.full_name} (ID: {user.id})")
        except Exception as send_error:
            logger.error(f"Ошибка отправки приветственного сообщения пользователю {user.id}: {send_error}")

        # Готовим сообщение для администратора
        admin_text = f"Новая заявка на вступление в канал {chat.title}\n" \
                     f"от пользователя {user.full_name}"

        if user.username:
            admin_text += f" (@{user.username})"

        admin_text += f"\nID пользователя: {user.id}\n" \
                      f"ID заявки: {request_id}"

        markup = None
        if auto_approve:
            await join_request.approve()
            await db.auto_approve_request(user.id, chat.id)
            admin_text += "\n\nЗаявка была автоматически одобрена"
            logger.info(f"Заявка от пользователя {user.full_name} (ID: {user.id}) автоматически одобрена")
        else:
            approve_button = InlineKeyboardButton(
                text="Одобрить заявку",
                callback_data=f"approve:{request_id}:{user.id}:{chat.id}"
            )
            reject_button = InlineKeyboardButton(
                text="Отклонить",
                callback_data=f"reject:{request_id}:{user.id}:{chat.id}"
            )

            markup = InlineKeyboardMarkup(inline_keyboard=[[approve_button], [reject_button]])

        for admin_id in ADMINS:
            try:
                await bot.send_message(
                    chat_id=admin_id,
                    text=admin_text,
                    reply_markup=markup
                )
            except Exception as e:
                logger.error(f"Не удалось отправить уведомление администратору {admin_id}: {e}")

    except Exception as e:
        logger.error(f"Ошибка при обработке заявки от пользователя {user.id}: {e}")


@router.callback_query(F.data.startswith(("approve:", "reject:")))
async def process_callback(callback_query, bot: Bot):
    if callback_query.from_user.id not in ADMINS:
        await callback_query.answer("У вас нет прав на выполнение этого действия.")
        return

    action, request_id, user_id, chat_id = callback_query.data.split(":")
    request_id = int(request_id)
    user_id = int(user_id)
    chat_id = int(chat_id)

    request_data = await db.get_request_by_id(request_id)

    if not request_data or request_data[6] != "pending":  # столбец status - вероятно индекс 6 (проверь в своей таблице)
        await callback_query.answer("Эта заявка уже обработана или не существует.")
        try:
            await callback_query.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass
        return

    try:
        if action == "approve":
            chat = await bot.get_chat(chat_id)
            await bot.approve_chat_join_request(chat_id=chat_id, user_id=user_id)
            await db.approve_request(request_id, callback_query.from_user.id)
            await callback_query.answer("Заявка одобрена!")

            try:
                # Вместо простого текста вызываем отправку первого кастомного сообщения
                await sleep(1)
                await send_first_welcome(user_id, bot)
            except Exception as send_error:
                logger.error(
                    f"Ошибка отправки приветственного сообщения после одобрения пользователю {user_id}: {send_error}")

            await callback_query.message.edit_text(
                text=f"{callback_query.message.text}\n\n✅ Одобрено администратором {callback_query.from_user.full_name}",
                reply_markup=None
            )

        elif action == "reject":
            await bot.decline_chat_join_request(chat_id=chat_id, user_id=user_id)
            await db.reject_request(request_id, callback_query.from_user.id)
            await callback_query.answer("Заявка отклонена!")

            await callback_query.message.edit_text(
                text=f"{callback_query.message.text}\n\n❌ Отклонено администратором {callback_query.from_user.full_name}",
                reply_markup=None
            )

    except Exception as e:
        logger.error(f"Ошибка при обработке действия {action} для заявки {request_id}: {e}")
        await callback_query.answer(f"Произошла ошибка: {e}", show_alert=True)
