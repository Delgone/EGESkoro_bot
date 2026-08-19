"""
Онбординг + обработчик кнопки «Я подписался» + Капсула времени.
"""
import logging
import pytz
from datetime import datetime

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select

from database.engine import AsyncSessionLocal
from database.models import ExamSchedule, User, UserSubject
from keyboards.builders import (
    grade_kb,
    main_menu_kb,
    notify_time_kb,
    subjects_kb,
    subscription_kb,
    timezone_kb,
    wave_kb,
    skip_capsule_kb,
)
from states.onboarding import Onboarding

logger = logging.getLogger(__name__)
router = Router()

SUBSCRIPTION_TEXT = (
    "👋 Привет!\n\n"
    "Чтобы пользоваться ботом, подпишись на наш канал — "
    "там выходят полезные материалы для подготовки к ЕГЭ.\n\n"
    "После подписки нажми кнопку ниже 👇"
)


# ──────────────────────────────────────────────────────────────
# Кнопка «Я подписался» — повторная проверка
# ──────────────────────────────────────────────────────────────

@router.callback_query(F.data == "check_subscription")
async def check_subscription(callback: CallbackQuery, state: FSMContext) -> None:
    from config import CHANNEL_USERNAME
    try:
        member = await callback.bot.get_chat_member(
            f"@{CHANNEL_USERNAME}", callback.from_user.id
        )
        subscribed = member.status not in ("left", "kicked", "banned")
    except Exception:
        subscribed = True  # не блокируем если не можем проверить

    if not subscribed:
        await callback.answer(
            "Ты ещё не подписался 🙁 Подпишись и нажми кнопку снова.",
            show_alert=True,
        )
        return

    await callback.answer("Отлично! Добро пожаловать 🎉")

    # Проверяем — может пользователь уже зарегистрирован
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == callback.from_user.id)
        )
        existing = result.scalar_one_or_none()

    if existing:
        await callback.message.edit_text(
            f"С возвращением, {existing.full_name}! 👋",
            reply_markup=main_menu_kb(),
        )
        return

    # Новый пользователь — запускаем онбординг
    await state.set_state(Onboarding.waiting_name)
    await callback.message.edit_text(
        "Как тебя зовут? Введи имя 👇"
    )


# ──────────────────────────────────────────────────────────────
# /start
# ──────────────────────────────────────────────────────────────

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    # Middleware уже проверила подписку — сюда попадаем только подписанные
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == message.from_user.id)
        )
        existing = result.scalar_one_or_none()

    if existing:
        await message.answer(
            f"С возвращением, {existing.full_name}! 👋\n\nЧем могу помочь?",
            reply_markup=main_menu_kb(),
        )
        return

    await state.set_state(Onboarding.waiting_name)
    await message.answer(
        "Привет! Я буду напоминать тебе об ЕГЭ каждый день "
        "и присылать мотивационную фразу.\n\n"
        "Как тебя зовут? Введи имя 👇"
    )


# ──────────────────────────────────────────────────────────────
# Шаг 1: имя
# ──────────────────────────────────────────────────────────────

@router.message(Onboarding.waiting_name)
async def process_name(message: Message, state: FSMContext) -> None:
    name = message.text.strip()
    if len(name) < 2 or len(name) > 50:
        await message.answer("Введи имя от 2 до 50 символов.")
        return
    await state.update_data(name=name)
    await state.set_state(Onboarding.waiting_grade)
    await message.answer(f"Отлично, {name}! В каком ты классе?", reply_markup=grade_kb())


# ──────────────────────────────────────────────────────────────
# Шаг 2: класс
# ──────────────────────────────────────────────────────────────

@router.callback_query(Onboarding.waiting_grade, F.data.startswith("grade:"))
async def process_grade(callback: CallbackQuery, state: FSMContext) -> None:
    grade = int(callback.data.split(":")[1])
    await state.update_data(grade=grade)
    await state.set_state(Onboarding.waiting_timezone)
    await callback.message.edit_text(
        "В каком часовом поясе ты живёшь?", reply_markup=timezone_kb()
    )


# ──────────────────────────────────────────────────────────────
# Шаг 3: часовой пояс
# ──────────────────────────────────────────────────────────────

@router.callback_query(Onboarding.waiting_timezone, F.data.startswith("tz:"))
async def process_timezone(callback: CallbackQuery, state: FSMContext) -> None:
    tz = callback.data.split(":", 1)[1]
    await state.update_data(timezone=tz)
    await state.set_state(Onboarding.waiting_notify_time)
    await callback.message.edit_text(
        "В какое время присылать утреннее сообщение?", reply_markup=notify_time_kb()
    )


# ──────────────────────────────────────────────────────────────
# Шаг 4: время уведомлений
# ──────────────────────────────────────────────────────────────

@router.callback_query(Onboarding.waiting_notify_time, F.data.startswith("notify:"))
async def process_notify_time(callback: CallbackQuery, state: FSMContext) -> None:
    _, hour, minute = callback.data.split(":")
    await state.update_data(notify_hour=int(hour), notify_minute=int(minute))
    await state.update_data(selected_subjects=[], wave_queue=[])
    await state.set_state(Onboarding.selecting_subjects)
    await callback.message.edit_text(
        "Выбери предметы, которые ты сдаёшь на ЕГЭ.\n"
        "Нажимай на каждый нужный предмет, затем «Продолжить».",
        reply_markup=subjects_kb(set()),
    )


# ──────────────────────────────────────────────────────────────
# Шаг 5: мультиселект предметов
# ──────────────────────────────────────────────────────────────

@router.callback_query(Onboarding.selecting_subjects, F.data.startswith("subj:"))
async def process_subject_toggle(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    selected: list[str] = data.get("selected_subjects", [])
    subject = callback.data.split(":", 1)[1]

    if subject == "confirm":
        if not selected:
            await callback.answer("Выбери хотя бы один предмет!", show_alert=True)
            return
        await state.update_data(wave_queue=list(selected), current_wave_idx=0, waves={})
        await _ask_wave(callback, state)
        return

    if subject in selected:
        selected.remove(subject)
    else:
        selected.append(subject)

    await state.update_data(selected_subjects=selected)
    await callback.message.edit_reply_markup(reply_markup=subjects_kb(set(selected)))
    await callback.answer()


# ──────────────────────────────────────────────────────────────
# Шаг 6: волна для каждого предмета
# ──────────────────────────────────────────────────────────────

async def _ask_wave(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    queue: list[str] = data["wave_queue"]
    idx: int = data["current_wave_idx"]

    if idx >= len(queue):
        # Все волны выбраны — переходим к Капсуле времени
        await state.set_state(Onboarding.waiting_capsule)
        await callback.message.edit_text(
            "Почти всё! ✨\n\n"
            "Напиши пару слов себе в будущее — <b>Капсулу времени</b>. "
            "Я пришлю тебе это сообщение прямо в день твоего экзамена для поддержки.\n\n"
            "<i>Можешь написать пожелание или просто пропустить этот шаг.</i>",
            reply_markup=skip_capsule_kb(),
            parse_mode="HTML"
        )
        return

    subject = queue[idx]
    await state.set_state(Onboarding.selecting_wave)
    await callback.message.edit_text(
        f"Выбери волну для предмета:\n<b>{subject}</b>",
        reply_markup=wave_kb(subject),
        parse_mode="HTML",
    )


@router.callback_query(Onboarding.selecting_wave, F.data.startswith("wave:"))
async def process_wave(callback: CallbackQuery, state: FSMContext) -> None:
    _, subject, wave_key = callback.data.split(":", 2)
    data = await state.get_data()
    waves: dict = data.get("waves", {})
    waves[subject] = wave_key
    new_idx = data["current_wave_idx"] + 1
    await state.update_data(waves=waves, current_wave_idx=new_idx)
    await _ask_wave(callback, state)


# ──────────────────────────────────────────────────────────────
# Шаг 7: Капсула времени
# ──────────────────────────────────────────────────────────────

@router.message(Onboarding.waiting_capsule)
async def process_capsule(message: Message, state: FSMContext) -> None:
    await state.update_data(capsule_message=message.text.strip())
    await _finish_onboarding(message, state)


@router.callback_query(Onboarding.waiting_capsule, F.data == "capsule:skip")
async def process_capsule_skip(callback: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(capsule_message=None)
    await _finish_onboarding(callback, state)


# ──────────────────────────────────────────────────────────────
# Финал онбординга
# ──────────────────────────────────────────────────────────────

async def _finish_onboarding(event: Message | CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    user_id = event.from_user.id

    # Переводим локальное время в UTC для правильной работы планировщика
    local_tz = pytz.timezone(data["timezone"])
    now_local = datetime.now(local_tz)
    notify_local = now_local.replace(hour=data["notify_hour"], minute=data["notify_minute"])
    notify_utc = notify_local.astimezone(pytz.utc)

    async with AsyncSessionLocal() as session:
        user = User(
            telegram_id=user_id,
            full_name=data["name"],
            grade=data["grade"],
            timezone=data["timezone"],
            notify_hour=notify_utc.hour,
            notify_minute=notify_utc.minute,
            capsule_message=data.get("capsule_message")
        )
        session.add(user)
        await session.flush()

        # Вычисляем правильный год экзамена
        now = datetime.utcnow()
        # Если регистрация идет во втором полугодии (июль-декабрь), экзамен в следующем году
        base_year = now.year + 1 if now.month >= 7 else now.year
        # Если это 10 класс, накидываем еще один год
        year = base_year + 1 if data["grade"] == 10 else base_year

        for subject_name, wave_key in data["waves"].items():
            sched_result = await session.execute(
                select(ExamSchedule).where(
                    ExamSchedule.subject_name == subject_name,
                    ExamSchedule.wave == wave_key,
                    ExamSchedule.year == year,
                )
            )
            schedule = sched_result.scalar_one_or_none()
            us = UserSubject(
                user_id=user.id,
                subject_name=subject_name,
                wave=wave_key,
                exam_date=schedule.exam_date if schedule else None,
            )
            session.add(us)

        await session.commit()

    await state.clear()

    # Показываем юзеру время в его локальном формате
    hour = data["notify_hour"]
    minute = data["notify_minute"]

    text = (
        f"🎉 Всё готово, {data['name']}!\n\n"
        f"Каждый день в <b>{hour:02d}:{minute:02d}</b> я буду присылать тебе "
        "мотивационную фразу и обратный отсчёт.\n\n"
        "Удачи в подготовке! Ты справишься 💪"
    )

    # Финальное сообщение отправляется по-разному в зависимости от того,
    # написал ли юзер сообщение текстом (Message) или нажал "Пропустить" (CallbackQuery)
    if isinstance(event, Message):
        await event.answer(text, reply_markup=main_menu_kb(), parse_mode="HTML")
    else:
        await event.message.edit_text(text, reply_markup=main_menu_kb(), parse_mode="HTML")