"""
Планировщик ежедневных уведомлений.
Каждую минуту проверяем, у каких пользователей пора слать сообщение.
"""
import logging
from datetime import datetime

import pytz
from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from config import REMINDER_DAYS
from database.engine import AsyncSessionLocal
from database.models import User, UserSubject
from services.phrases import (
    build_daily_message,
    build_exam_day_message,
    build_pre_exam_message,
    get_phrase,
)
from keyboards.builders import reflection_kb

logger = logging.getLogger(__name__)


async def send_focus_end(bot: Bot, user_id: int, subject: str) -> None:
    """Отправка уведомления об окончании таймера фокуса (Pomodoro)"""
    try:
        await bot.send_message(
            user_id,
            f"⏰ Время вышло!\n\n"
            f"Трекер концентрации по предмету «{subject}» завершен. "
            f"Как успехи? Что удалось сделать? Обязательно похвали себя!",
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Ошибка при отправке фокуса пользователю {user_id}: {e}")


async def _send_daily_notifications(bot: Bot) -> None:
    """Главная задача планировщика — рассылка по всем активным пользователям."""
    now_utc = datetime.utcnow()

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User)
            .where(User.is_active == True)
            .options(selectinload(User.subjects))
        )
        users: list[User] = result.scalars().all()

    for user in users:
        try:
            tz = pytz.timezone(user.timezone)
            now_local = datetime.now(tz)

            # Проверка 1: Наступило ли время утреннего сообщения
            if now_local.hour == user.notify_hour and now_local.minute == user.notify_minute:
                active = [s for s in user.subjects if not s.is_passed and s.exam_date]
                if not active:
                    continue

                # Режим отдыха блокирует спецсообщения
                is_resting = user.rest_until and now_utc < user.rest_until
                special_sent = False

                if not is_resting:
                    # Проверяем спецситуации для каждого предмета
                    for subj in active:
                        days_left = subj.days_left
                        if days_left is None:
                            continue

                        if days_left == 0:
                            await bot.send_message(
                                user.telegram_id,
                                build_exam_day_message(subj.subject_name, user.capsule_message),
                            )
                            special_sent = True

                        elif days_left in REMINDER_DAYS:
                            await bot.send_message(
                                user.telegram_id,
                                build_pre_exam_message(subj.subject_name, days_left),
                            )
                            special_sent = True

                # Если спецсообщение не отправлялось (или включен отдых) — шлём обычное
                if not special_sent:
                    text = build_daily_message(user, active)
                    await bot.send_message(user.telegram_id, text, parse_mode="HTML")

                # Обновляем индекс фразы, только если не на отдыхе
                if not is_resting:
                    async with AsyncSessionLocal() as session:
                        db_user = await session.get(User, user.id)
                        if db_user:
                            _, next_index = get_phrase(db_user.phrase_index)
                            db_user.phrase_index = next_index
                            await session.commit()

            # Проверка 2: Вечерняя рефлексия ("Золотой час") — спустя 10 часов после утреннего
            reflection_hour = 21
            if now_local.hour == reflection_hour and now_local.minute == user.notify_minute:
                # Если человек на отдыхе, мы его не трогаем
                if user.rest_until and now_utc < user.rest_until:
                    continue

                await bot.send_message(
                    user.telegram_id,
                    "🌙 Время вечерней рефлексии!\n\nВыполнил свой план подготовки на сегодня?",
                    reply_markup=reflection_kb(),
                    parse_mode="HTML"
                )

        except Exception as e:
            logger.error(f"Ошибка при обработке планировщика для пользователя {user.telegram_id}: {e}")


def setup_scheduler(bot: Bot) -> AsyncIOScheduler:
    """Создаёт и возвращает настроенный планировщик."""
    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(
        _send_daily_notifications,
        trigger="cron",
        minute="*",          # каждую минуту — проверяем, у кого сейчас notify_hour:notify_minute
        kwargs={"bot": bot},
        id="daily_notifications",
        replace_existing=True,
    )
    return scheduler