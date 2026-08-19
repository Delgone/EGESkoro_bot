# test_notify.py
import asyncio
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import BOT_TOKEN, REMINDER_DAYS
from database.engine import init_db, AsyncSessionLocal
from database.models import User
from services.phrases import (
    build_daily_message,
    build_exam_day_message,
    build_pre_exam_message,
    get_phrase,
)

async def main():
    await init_db()
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User)
            .where(User.is_active == True)
            .options(selectinload(User.subjects))
        )
        users = result.scalars().all()

    print(f"Найдено пользователей: {len(users)}")

    for user in users:
        active = [s for s in user.subjects if not s.is_passed and s.exam_date]
        print(f"\nПользователь: {user.full_name} (tg_id={user.telegram_id})")
        print(f"  Активных предметов: {len(active)}")
        for s in active:
            print(f"{s.subject_name} — {s.exam_date} — осталось дней: {s.days_left}")

        if not active:
            print("  Пропускаем — нет активных предметов с датами")
            continue

        # Проверяем спецситуации
        special_sent = False
        for subj in active:
            days_left = subj.days_left
            if days_left == 0:
                text = build_exam_day_message(subj.subject_name)
                await bot.send_message(user.telegram_id, text)
                special_sent = True
                print(f"  Отправлено: ДЕНЬ ЭКЗАМЕНА по {subj.subject_name}")
            elif days_left in REMINDER_DAYS:
                text = build_pre_exam_message(subj.subject_name, days_left)
                await bot.send_message(user.telegram_id, text)
                special_sent = True
                print(f"  Отправлено: спецнапоминание за {days_left} дней по {subj.subject_name}")

        if not special_sent:
            text = build_daily_message(user, active)
            await bot.send_message(user.telegram_id, text)
            print(f"  Отправлено: обычное ежедневное сообщение")

        # Обновляем индекс фразы
        async with AsyncSessionLocal() as session:
            db_user = await session.get(User, user.id)
            if db_user:
                _, next_index = get_phrase(db_user.phrase_index)
                db_user.phrase_index = next_index
                await session.commit()

    await bot.session.close()
    print("\nГотово!")

asyncio.run(main())