"""
Обработчики главного меню: статус, фраза дня, отметка сданного экзамена, фокус и рефлексия.
"""
from datetime import datetime, timedelta

from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from database.engine import AsyncSessionLocal
from database.models import User, UserSubject
from keyboards.builders import (
    confirm_kb,
    done_subjects_kb,
    main_menu_kb,
    focus_subject_kb,
    focus_time_kb
)
from services.phrases import (
    build_daily_message,
    build_passed_message,
    get_phrase,
)
from services.scheduler import send_focus_end

router = Router()

# ──────────────────────────────────────────────────────────────
# Вызов главного меню командой /menu
# ──────────────────────────────────────────────────────────────

@router.message(Command("menu"))
async def cmd_menu(message: Message) -> None:
    await message.answer(
        "Главное меню 👇",
        reply_markup=main_menu_kb()
    )

# ──────────────────────────────────────────────────────────────
# Хелпер: получить пользователя с предметами
# ──────────────────────────────────────────────────────────────

async def _get_user(telegram_id: int) -> User | None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User)
            .where(User.telegram_id == telegram_id)
            .options(selectinload(User.subjects))
        )
        return result.scalar_one_or_none()


# ──────────────────────────────────────────────────────────────
# Назад в главное меню
# ──────────────────────────────────────────────────────────────

@router.callback_query(F.data == "menu:back")
async def menu_back(callback: CallbackQuery) -> None:
    await callback.message.edit_text(
        "Главное меню 👇",
        reply_markup=main_menu_kb(),
    )


# ──────────────────────────────────────────────────────────────
# 📊 Статус — обратный отсчёт по всем предметам
# ──────────────────────────────────────────────────────────────

@router.callback_query(F.data == "menu:status")
async def menu_status(callback: CallbackQuery) -> None:
    user = await _get_user(callback.from_user.id)
    if not user:
        await callback.answer("Сначала пройди /start", show_alert=True)
        return

    active = [s for s in user.subjects if not s.is_passed]
    if not active:
        await callback.message.edit_text(
            "Все экзамены сданы! 🎉",
            reply_markup=main_menu_kb(),
        )
        return

    lines = ["📊 <b>Твои экзамены:</b>\n"]
    for subj in sorted(active, key=lambda s: s.exam_date or datetime.max):
        days_left = subj.days_left
        if days_left is None:
            lines.append(f"  • {subj.subject_name} — дата уточняется")
        elif days_left == 0:
            lines.append(f"  • {subj.subject_name} — <b>СЕГОДНЯ!</b> 🔥")
        elif days_left < 0:
            lines.append(f"  • {subj.subject_name} — экзамен прошёл")
        else:
            from services.phrases import _days_word
            lines.append(f"  • {subj.subject_name} — {days_left} {_days_word(days_left)}")

    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=main_menu_kb(),
        parse_mode="HTML",
    )


# ──────────────────────────────────────────────────────────────
# 💬 Фраза дня
# ──────────────────────────────────────────────────────────────

@router.callback_query(F.data == "menu:today")
async def menu_today(callback: CallbackQuery) -> None:
    user = await _get_user(callback.from_user.id)
    if not user:
        await callback.answer("Сначала пройди /start", show_alert=True)
        return

    active = [s for s in user.subjects if not s.is_passed and s.exam_date]
    text = build_daily_message(user, active)

    await callback.message.edit_text(
        f"<pre>{text}</pre>",
        reply_markup=main_menu_kb(),
        parse_mode="HTML",
    )


# ──────────────────────────────────────────────────────────────
# ✅ Сдал экзамен — список активных предметов
# ──────────────────────────────────────────────────────────────

@router.callback_query(F.data == "menu:done")
async def menu_done(callback: CallbackQuery) -> None:
    user = await _get_user(callback.from_user.id)
    if not user:
        await callback.answer("Сначала пройди /start", show_alert=True)
        return

    active = [s.subject_name for s in user.subjects if not s.is_passed]
    if not active:
        await callback.message.edit_text(
            "Нет активных предметов 🎉",
            reply_markup=main_menu_kb(),
        )
        return

    await callback.message.edit_text(
        "Какой предмет отметить как сданный?",
        reply_markup=done_subjects_kb(active),
    )


# ──────────────────────────────────────────────────────────────
# ✅ Подтверждение — конкретный предмет
# ──────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("done:"))
async def menu_done_confirm(callback: CallbackQuery) -> None:
    subject_name = callback.data.split(":", 1)[1]
    await callback.message.edit_text(
        f"Точно отметить «{subject_name}» как сданный?",
        reply_markup=confirm_kb(
            yes_data=f"done_confirm:{subject_name}",
            no_data="menu:done",
        ),
    )


@router.callback_query(F.data.startswith("done_confirm:"))
async def menu_done_execute(callback: CallbackQuery) -> None:
    subject_name = callback.data.split(":", 1)[1]

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User)
            .where(User.telegram_id == callback.from_user.id)
            .options(selectinload(User.subjects))
        )
        user = result.scalar_one_or_none()
        if not user:
            await callback.answer("Пользователь не найден", show_alert=True)
            return

        subj = next((s for s in user.subjects if s.subject_name == subject_name), None)
        if not subj:
            await callback.answer("Предмет не найден", show_alert=True)
            return

        subj.is_passed = True
        subj.passed_at = datetime.utcnow()
        await session.commit()

        subjects_left = sum(1 for s in user.subjects if not s.is_passed)

    await callback.message.edit_text(
        build_passed_message(subject_name, subjects_left),
        reply_markup=main_menu_kb() if subjects_left > 0 else None,
    )


# ──────────────────────────────────────────────────────────────
# 🍅 Трекер концентрации (Фокус)
# ──────────────────────────────────────────────────────────────

@router.callback_query(F.data == "menu:focus")
async def menu_focus(callback: CallbackQuery) -> None:
    user = await _get_user(callback.from_user.id)
    if not user:
        await callback.answer("Сначала пройди /start", show_alert=True)
        return

    active = [s.subject_name for s in user.subjects if not s.is_passed]
    if not active:
        await callback.answer("У тебя нет активных предметов!", show_alert=True)
        return

    await callback.message.edit_text(
        "🍅 <b>Трекер концентрации</b>\n\nВыбери предмет, над которым будешь работать:",
        reply_markup=focus_subject_kb(active),
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("focus:subj:"))
async def focus_subject(callback: CallbackQuery) -> None:
    subject = callback.data.split(":", 2)[2]
    await callback.message.edit_text(
        f"Выбран предмет: <b>{subject}</b>\n\nНа сколько минут ставим таймер?",
        reply_markup=focus_time_kb(subject),
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("focus:time:"))
async def focus_time(callback: CallbackQuery, scheduler: AsyncIOScheduler) -> None:
    _, _, subject, mins = callback.data.split(":")
    minutes = int(mins)

    # Ставим задачу в планировщик
    time_end = datetime.utcnow() + timedelta(minutes=minutes)
    scheduler.add_job(
        send_focus_end,
        trigger="date",
        run_date=time_end,
        kwargs={"bot": callback.bot, "user_id": callback.from_user.id, "subject": subject}
    )

    await callback.message.edit_text(
        f"🍅 Засек {minutes} минут на предмет «{subject}».\n\n"
        f"Отложи телефон и не отвлекайся! Жду тебя через {minutes} минут.",
        reply_markup=main_menu_kb()
    )


# ──────────────────────────────────────────────────────────────
# 🌙 Вечерняя рефлексия (Стрик-система)
# ──────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("reflection:"))
async def process_reflection(callback: CallbackQuery) -> None:
    answer = callback.data.split(":")[1]

    async with AsyncSessionLocal() as session:
        user = await session.scalar(select(User).where(User.telegram_id == callback.from_user.id))
        if not user:
            return

        if answer == "yes":
            user.streak_count += 1
            await session.commit()
            await callback.message.edit_text(
                f"Супер! 🔥\nТвой стрик: <b>{user.streak_count} дней</b> подряд.\nТак держать!",
                parse_mode="HTML"
            )
        else:
            user.streak_count = 0
            await session.commit()
            await callback.message.edit_text(
                "Ничего страшного, отдых тоже важен. Завтра обязательно получится! 💪",
                parse_mode="HTML"
            )