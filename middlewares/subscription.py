"""
Middleware проверки подписки на канал.
Пропускает только пользователей, подписанных на CHANNEL_USERNAME.
Исключение — callback «check_subscription» (кнопка «Я подписался»).
"""
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware, Bot
from aiogram.types import CallbackQuery, Message, TelegramObject

from config import CHANNEL_USERNAME
from keyboards.builders import subscription_kb

SUBSCRIPTION_TEXT = (
    "👋 Привет!\n\n"
    "Чтобы пользоваться ботом, подпишись на наш канал — "
    "там выходят полезные материалы для подготовки к ЕГЭ.\n\n"
    "После подписки нажми кнопку ниже 👇"
)


async def _is_subscribed(bot: Bot, user_id: int) -> bool:
    """Проверяет, подписан ли пользователь на канал."""
    try:
        member = await bot.get_chat_member(f"@{CHANNEL_USERNAME}", user_id)
        return member.status not in ("left", "kicked", "banned")
    except Exception:
        # Если бот не админ канала или канал не найден — пропускаем проверку
        return True


class SubscriptionMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        bot: Bot = data["bot"]

        # Определяем user_id и способ ответа в зависимости от типа события
        if isinstance(event, Message):
            user_id = event.from_user.id

            if not await _is_subscribed(bot, user_id):
                await event.answer(SUBSCRIPTION_TEXT, reply_markup=subscription_kb())
                return  # блокируем дальнейшую обработку

        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id

            # Кнопку «Я подписался» обрабатываем отдельно — пропускаем в хендлер
            if event.data == "check_subscription":
                return await handler(event, data)

            if not await _is_subscribed(bot, user_id):
                await event.answer(
                    "Сначала подпишись на канал 👇", show_alert=True
                )
                # Показываем сообщение с кнопкой подписки
                await bot.send_message(
                    user_id,
                    SUBSCRIPTION_TEXT,
                    reply_markup=subscription_kb(),
                )
                return

        return await handler(event, data)
