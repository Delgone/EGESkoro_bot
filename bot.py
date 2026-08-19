"""
Точка входа. Инициализирует БД, планировщик и запускает polling.
"""
import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from database.engine import init_db
from handlers import menu, settings, start
from middlewares.subscription import SubscriptionMiddleware
from services.scheduler import setup_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


async def main() -> None:
    # 1. База данных
    await init_db()
    logger.info("БД инициализирована")

    # 2. Bot + Dispatcher
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())

    # 3. Middleware проверки подписки (навешиваем на все сообщения и колбэки)
    dp.message.middleware(SubscriptionMiddleware())
    dp.callback_query.middleware(SubscriptionMiddleware())

    # 4. Роутеры (start первым — там check_subscription)
    dp.include_router(start.router)
    dp.include_router(menu.router)
    dp.include_router(settings.router)

    # 5. Планировщик ежедневных уведомлений
    scheduler = setup_scheduler(bot)
    scheduler.start()
    logger.info("Планировщик запущен")

    # 6. Polling
    try:
        logger.info("Бот запущен")
        # Пробрасываем scheduler, чтобы он был доступен в хендлерах (для таймера концентрации)
        await dp.start_polling(
            bot,
            scheduler=scheduler,
            allowed_updates=dp.resolve_used_update_types()
        )
    finally:
        scheduler.shutdown()
        await bot.session.close()
        logger.info("Бот остановлен")


if __name__ == "__main__":
    asyncio.run(main())