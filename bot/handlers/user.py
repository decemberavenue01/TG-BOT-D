from aiogram import Router, F
from aiogram.types import ChatJoinRequest, Message
from bot.loader import bot
from bot.database import db
from bot.services.welcome import send_first_welcome, handle_start_activate_protocol

router = Router()

@router.chat_join_request()
async def handle_join_request(event: ChatJoinRequest):
    user_id = event.from_user.id

    # Получаем статус автоодобрения
    auto_approve = await db.get_setting("auto_approve")
    approve = auto_approve == "true"

    if approve:
        try:
            await event.approve()
        except Exception:
            return  # Telegram может не дать одобрить

        # Добавляем пользователя в базу
        await db.add_user(user_id)

        # Отправляем первое приветствие — фото + кнопка запуска /start activate_protocol
        try:
            await send_first_welcome(user_id, bot)
        except Exception as e:
            print(f"Не удалось отправить приветственное сообщение: {e}")
    else:
        # Просто проигнорируем, если автоодобрение выключено
        pass

@router.message(F.text.startswith('/start'))
async def on_start_command(message: Message):
    args = message.text.split(maxsplit=1)
    param = args[1] if len(args) > 1 else None

    try:
        # Всегда вызываем handle_start_activate_protocol, даже если параметра нет
        await handle_start_activate_protocol(message, bot)
    except Exception as e:
        print(f"Ошибка в обработке /start (param={param}): {e}")
