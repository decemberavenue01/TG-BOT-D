from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import (
    Message, InputFile,
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton,
    ContentType, MessageEntity
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from bot.config import load_config
from bot.database import db
import logging
from typing import List

logging.basicConfig(level=logging.DEBUG)

router = Router()
config = load_config()


class BroadcastStates(StatesGroup):
    waiting_for_text = State()
    waiting_for_media = State()
    waiting_for_button = State()
    preview = State()


@router.message(Command("broadcast"))
async def cmd_broadcast_start(message: Message, state: FSMContext):
    await message.answer("Команда /broadcast получена")
    if message.from_user.id not in config.admins:
        await message.answer("❌ У вас нет прав для запуска рассылки.")
        return

    await state.clear()
    await message.answer(
        "📢 Начинаем создание рассылки.\n"
        "Шаг 1: Отправьте сообщение с нужным текстом (можно с форматированием — спойлеры, зачёркивания и т.п.).\n\n"
        "Или /skip для пропуска."
    )
    await state.set_state(BroadcastStates.waiting_for_text)


@router.message(BroadcastStates.waiting_for_text, F.content_type == ContentType.TEXT)
async def process_text_step(message: Message, state: FSMContext):
    # Сохраняем chat_id и message_id исходного сообщения, чтобы потом его копировать
    await state.update_data(source_chat_id=message.chat.id, source_message_id=message.message_id)
    await message.answer(
        "Шаг 2: Прикрепите фото или «кружок»(video_note), или отправьте /skip для пропуска."
    )
    await state.set_state(BroadcastStates.waiting_for_media)


@router.message(BroadcastStates.waiting_for_text, Command("skip"))
async def skip_text_step(message: Message, state: FSMContext):
    # Если текст пропущен — сохраним пустые данные, чтобы копировать только медиа или кнопку
    await state.update_data(source_chat_id=None, source_message_id=None)
    await message.answer(
        "Шаг 2: Прикрепите фото или «кружок»(video_note), или отправьте /skip для пропуска."
    )
    await state.set_state(BroadcastStates.waiting_for_media)


@router.message(
    BroadcastStates.waiting_for_media,
    F.content_type.in_({ContentType.PHOTO, ContentType.VIDEO_NOTE})
)
async def process_media_step(message: Message, state: FSMContext):
    # Аналогично сохраняем id сообщения с медиа для копирования
    await state.update_data(media_source_chat_id=message.chat.id, media_source_message_id=message.message_id)
    await message.answer(
        "Шаг 3: Отправьте кнопку в формате: текст кнопки / URL ссылки (можно / без пробелов)\n\n"
        "Поддерживаются ссылки типа: www.domain.com, t.me/ссылка_или_изернаейм\n\n"
        "Или отправьте /skip, если кнопка не нужна."
    )
    await state.set_state(BroadcastStates.waiting_for_button)


@router.message(BroadcastStates.waiting_for_media, Command("skip"))
async def skip_media_step(message: Message, state: FSMContext):
    await state.update_data(media_source_chat_id=None, media_source_message_id=None)
    await message.answer(
        "Шаг 3: Отправьте кнопку в формате: текст кнопки / URL ссылки (можно / без пробелов)\n\n"
        "Поддерживаются ссылки типа: www.domain.com, t.me/ссылка_или_изернаейм\n\n"
        "Или отправьте /skip, если кнопка не нужна."
    )
    await state.set_state(BroadcastStates.waiting_for_button)


@router.message(BroadcastStates.waiting_for_button)
async def process_button_step(message: Message, state: FSMContext):
    text = message.text or ""
    if text.lower() == "/skip":
        await state.update_data(button=None)
        await send_preview(message, state)
        return

    if "/" not in text:
        await message.answer("❗ Формат кнопки неверный. Используйте: Текст кнопки / Ссылка")
        return

    btn_text, btn_url = map(str.strip, text.split("/", 1))

    # Автодобавление https:// если ссылка начинается с www. или t.me/
    if not btn_url.startswith(("http://", "https://")):
        if btn_url.startswith(("www.", "t.me/")):
            btn_url = "https://" + btn_url
        else:
            await message.answer("❗ Ссылка должна начинаться с http://, https://, www. или t.me/")
            return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=btn_text, url=btn_url)]
    ])

    await state.update_data(button=keyboard)
    await send_preview(message, state)


async def send_preview(message: Message, state: FSMContext):
    data = await state.get_data()

    source_chat_id = data.get("source_chat_id")
    source_message_id = data.get("source_message_id")
    media_source_chat_id = data.get("media_source_chat_id")
    media_source_message_id = data.get("media_source_message_id")
    button = data.get("button")

    await message.answer("📨 Предпросмотр сообщения:")

    try:
        # Если есть и текст, и медиа — показываем отдельно
        if media_source_chat_id and media_source_message_id:
            # Копируем медиа
            await message.bot.copy_message(
                chat_id=message.chat.id,
                from_chat_id=media_source_chat_id,
                message_id=media_source_message_id
            )
            # Копируем текст с кнопкой
            if source_chat_id and source_message_id:
                await message.bot.copy_message(
                    chat_id=message.chat.id,
                    from_chat_id=source_chat_id,
                    message_id=source_message_id,
                    reply_markup=button
                )
            else:
                # Если текст отсутствует, кнопка приписывается к медиа
                if button:
                    await message.answer(" ", reply_markup=button)
        else:
            # Если только текст
            if source_chat_id and source_message_id:
                await message.bot.copy_message(
                    chat_id=message.chat.id,
                    from_chat_id=source_chat_id,
                    message_id=source_message_id,
                    reply_markup=button
                )
            else:
                await message.answer("❗ Нет сообщения для предпросмотра.")

    except Exception as e:
        await message.answer(f"❗ Ошибка при отправке предпросмотра: {e}")
        return

    await message.answer(
        "Если всё устраивает, отправьте /send для запуска рассылки или /cancel для отмены."
    )
    await state.set_state(BroadcastStates.preview)


@router.message(BroadcastStates.preview, Command("send"))
async def process_send(message: Message, state: FSMContext):
    if message.from_user.id not in config.admins:
        return

    data = await state.get_data()

    source_chat_id = data.get("source_chat_id")
    source_message_id = data.get("source_message_id")
    media_source_chat_id = data.get("media_source_chat_id")
    media_source_message_id = data.get("media_source_message_id")
    button = data.get("button")

    users = await get_all_users()

    sent = 0
    failed = 0

    await message.answer("🚀 Запускаю рассылку...")

    for user_id in users:
        try:
            # Если есть медиа — копируем медиа и текст отдельно
            if media_source_chat_id and media_source_message_id:
                await message.bot.copy_message(
                    chat_id=user_id,
                    from_chat_id=media_source_chat_id,
                    message_id=media_source_message_id
                )
                if source_chat_id and source_message_id:
                    await message.bot.copy_message(
                        chat_id=user_id,
                        from_chat_id=source_chat_id,
                        message_id=source_message_id,
                        reply_markup=button
                    )
                else:
                    if button:
                        await message.bot.send_message(chat_id=user_id, text=" ", reply_markup=button)
            else:
                # Если только текст (или пусто)
                if source_chat_id and source_message_id:
                    await message.bot.copy_message(
                        chat_id=user_id,
                        from_chat_id=source_chat_id,
                        message_id=source_message_id,
                        reply_markup=button
                    )
                else:
                    if button:
                        await message.bot.send_message(chat_id=user_id, text=" ", reply_markup=button)

            sent += 1
        except Exception:
            failed += 1

    await message.answer(f"✅ Рассылка завершена. Отправлено: {sent}, Ошибок: {failed}")
    await state.clear()


@router.message(BroadcastStates.preview, Command("cancel"))
async def cancel_broadcast(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("🚫 Рассылка отменена.")


async def get_all_users() -> List[int]:
    users = []
    rows = await db.get_all_users()  # Метод должен возвращать список строк с user_id
    for row in rows:
        users.append(row[0])
    return users
