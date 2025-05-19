import asyncio
from bot.loader import bot, dp
from bot.handlers import admin, user
from bot.database.db import db  # импортируем объект базы данных
from bot.handlers import broadcast

async def main():
    # Инициализируем базу данных
    await db.init_db()

    # Регистрируем роутеры
    dp.include_routers(
        admin.router,
        user.router,
        broadcast.router
    )

    # Удаляем вебхук и запускаем polling
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
