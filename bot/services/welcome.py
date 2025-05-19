from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
import os
from asyncio import sleep
from urllib.parse import quote

BASE_MEDIA_PATH = os.path.join(os.path.dirname(__file__), "..", "media")
BASE_MEDIA_PATH = os.path.abspath(BASE_MEDIA_PATH)

def safe_file(path: str) -> FSInputFile:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Файл не найден: {path}")
    return FSInputFile(path)


# Отправляем первое сообщение после одобрения
async def send_first_welcome(user_id: int, bot):
    your_bot_username = (await bot.get_me()).username
    start_link = f"https://t.me/{your_bot_username}?start=activate_protocol"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Узнать результаты💸", url=start_link)]
    ])

    photo_path = os.path.join(BASE_MEDIA_PATH, "welcome.jpg")

    try:
        photo = safe_file(photo_path)
        await bot.send_photo(
            chat_id=user_id,
            photo=photo,
            caption=(
                "👋🏻<b>Привет! Спасибо за подписку на мой канал!</b>\n\n"
                "У меня нет никаких:\n"
                "<blockquote>❌<b>VIP каналов.\n"
                "❌Платных курсов.\n"
                "❌Доверительного управления.</b></blockquote>\n\n"
                "Моя цель набрать <b>100k подписчиков!</b>\n"
                "Я торгую по собственной стратегии с <b>Winrate 90%!</b> тем самым приумножаю свой капитал и помогаю в этом своим подписчикам!\n\n"
                "⚠️<b>Как именно я помогаю:</b>\n"
                "<blockquote>🔸<b>Бесплатно провожу торговые сессии, чтоб вы могли зарабатывать вместе со мной</b>\n"
                "🔸<b>Даю полезный материал для трейдеров и различные торговые стратегии</b></blockquote>\n\n"
                "Нажми кнопку ниже и узнаешь какие результаты ты сможешь делать с <b>первого дня</b>👇🏻"
            ),
            reply_markup=keyboard
        )
    except Exception as e:
        print(f"❌ Ошибка при отправке welcome-сообщения: {e}")


# Обработчик для /start activate_protocol
async def handle_start_activate_protocol(message, bot):
    user_id = message.from_user.id

    your_username = "ray_trdr"  # Заменить на твой ник без @

    # Текст для автозаполнения в строке ввода
    text_for_input = "Активировать протокол"
    encoded_text = quote(text_for_input)

    # Ссылка на ЛС с тобой с автозаполненным текстом
    deep_link_url = f"https://t.me/{your_username}?text={encoded_text}"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Активировать протокол💬", url=deep_link_url)]
    ])

    image_names = ["welcome2.jpg", "welcome3.jpg", "welcome4.jpg", "welcome5.jpg", "welcome6.jpg"]

    try:
        media_files = [safe_file(os.path.join(BASE_MEDIA_PATH, name)) for name in image_names]
        media_group = [{"type": "photo", "media": f} for f in media_files]

        await bot.send_media_group(chat_id=user_id, media=media_group)
        await sleep(1)

        await bot.send_message(
            chat_id=user_id,
            text=(
                "🤝🏻<b>Благодаря моему каналу ты сможешь подружиться с ВАЛЮТНЫМ РЫНКОМ💹</b>\n\n"
                "<blockquote><b>Мы торгуем с понедельника по пятницу и я регулярно выкладываю отчёты!</b></blockquote>\n\n"
                "Мой <b>бесплатный</b> канал с сигналами и обучающим материалами называется:\n"
                "<tg-spoiler><b>The R.A.Y. Protocol</b></tg-spoiler>\n\n"
                "<i>Напиши мне</i>\n"
                "<b>« Активировать протокол »</b>, и я дам пошаговую инструкцию!😉\n\n"
                "❕ВАЖНЫЙ МОМЕНТ❕\n\n"
                "У меня есть <b>БОНУС</b>, который поможет быстро стартануть и увидеть <b>результаты!</b>💰💰💰"
            ),
            reply_markup=keyboard
        )

        await sleep(10)
        await bot.send_message(chat_id=user_id, text="⚡️<b>Важно</b>⚡️\n\n"
                "🔕<b>Не отключай уведомления этого бота.</b>\n"
                "Он будет присылать только полезную информацию.\n\n"
                "Уже скоро что-то отправлю!")

    except Exception as e:
        print(f"❌ Ошибка в activate_protocol: {e}")
