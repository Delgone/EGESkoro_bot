"""
Редактирование настроек пользователя:
  — время уведомлений
  — часовой пояс
  — предметы и волны
  — режим отдыха (анти-выгорание)
"""
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from database.engine import AsyncSessionLocal
from database.models import ExamSchedule, User, UserSubject
from keyboards.builders import (
    notify_time_kb,
    settings_kb,
    subjects_kb,
    timezone_kb,
    wave_kb,
    rest_kb,
)
from states.onboarding import SettingsFlow

router = Router()


# ──────────────────────────────────────────────────────────────
# Открыть настройки
# ──────────────────────────────────────────────────────────────

@router.callback_query(F.data == "menu:settings")
async def open_settings(callback: CallbackQuery) -> None:
    await callback.message.edit_text(
        "⚙️ <b>Настройки</b>",
        reply_markup=settings_kb(),
        parse_mode="HTML",
    )


# ──────────────────────────────────────────────────────────────
# Редактировать время уведомлений
# ──────────────────────────────────────────────────────────────

@router.callback_query(F.data == "settings:time")
async def settings_time(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(SettingsFlow.editing_time)
    await callback.message.edit_text(
        "В какое время присылать сообщение?",
        reply_markup=notify_time_kb(),
    )


@router.callback_query(SettingsFlow.editing_time, F.data.startswith("notify:"))
async def settings_time_save(callback: CallbackQuery, state: FSMContext) -> None:
    _, hour, minute = callback.data.split(":")

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == callback.from_user.id)
        )
        user = result.scalar_one_or_none()
        if user:
            user.notify_hour = int(hour)
            user.notify_minute = int(minute)
            await session.commit()

    await state.clear()
    await callback.message.edit_text(
        f"✅ Время уведомлений обновлено: <b>{int(hour):02d}:00</b>",
        reply_markup=settings_kb(),
        parse_mode="HTML",
    )


# ──────────────────────────────────────────────────────────────
# Редактировать часовой пояс
# ──────────────────────────────────────────────────────────────

@router.callback_query(F.data == "settings:timezone")
async def settings_timezone(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(SettingsFlow.editing_subjects)  # переиспользуем state
    await callback.message.edit_text(
        "Выбери часовой пояс:",
        reply_markup=timezone_kb(),
    )


@router.callback_query(SettingsFlow.editing_subjects, F.data.startswith("tz:"))
async def settings_timezone_save(callback: CallbackQuery, state: FSMContext) -> None:
    tz = callback.data.split(":", 1)[1]

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == callback.from_user.id)
        )
        user = result.scalar_one_or_none()
        if user:
            user.timezone = tz
            await session.commit()

    await state.clear()
    await callback.message.edit_text(
        f"✅ Часовой пояс обновлён: <b>{tz}</b>",
        reply_markup=settings_kb(),
        parse_mode="HTML",
    )


# ──────────────────────────────────────────────────────────────
# Редактировать предметы: добавить / удалить
# ──────────────────────────────────────────────────────────────

@router.callback_query(F.data == "settings:subjects")
async def settings_subjects(callback: CallbackQuery, state: FSMContext) -> None:
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

    current = {s.subject_name for s in user.subjects if not s.is_passed}
    await state.set_state(SettingsFlow.editing_subjects)
    await state.update_data(
        mode="subjects",
        original_subjects=list(current),
        selected_subjects=list(current),
        waves={},
        wave_queue=[],
        current_wave_idx=0,
    )
    await callback.message.edit_text(
        "Выбери предметы, которые ты сдаёшь.\n"
        "Нажми на предмет, чтобы добавить или убрать. Затем «Продолжить».",
        reply_markup=subjects_kb(current),
    )


@router.callback_query(SettingsFlow.editing_subjects, F.data.startswith("subj:"))
async def settings_subject_toggle(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    # Если мы в режиме часового пояса — пропускаем
    if data.get("mode") != "subjects":
        return

    selected: list[str] = data.get("selected_subjects", [])
    subject = callback.data.split(":", 1)[1]

    if subject == "confirm":
        if not selected:
            await callback.answer("Выбери хотя бы один предмет!", show_alert=True)
            return
        # Определяем новые предметы (которых раньше не было)
        original = set(data.get("original_subjects", []))
        new_subjects = [s for s in selected if s not in original]
        if new_subjects:
            await state.update_data(wave_queue=new_subjects, current_wave_idx=0)
            await state.set_state(SettingsFlow.editing_wave)
            await _ask_wave_settings(callback, state)
        else:
            await _save_subjects(callback, state, selected)
        return

    if subject in selected:
        selected.remove(subject)
    else:
        selected.append(subject)

    await state.update_data(selected_subjects=selected)
    await callback.message.edit_reply_markup(reply_markup=subjects_kb(set(selected)))
    await callback.answer()


async def _ask_wave_settings(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    queue: list[str] = data["wave_queue"]
    idx: int = data["current_wave_idx"]

    if idx >= len(queue):
        await _save_subjects(callback, state, data["selected_subjects"])
        return

    subject = queue[idx]
    await callback.message.edit_text(
        f"Выбери волну для:\n<b>{subject}</b>",
        reply_markup=wave_kb(subject),
        parse_mode="HTML",
    )


@router.callback_query(SettingsFlow.editing_wave, F.data.startswith("wave:"))
async def settings_wave_pick(callback: CallbackQuery, state: FSMContext) -> None:
    _, subject, wave_key = callback.data.split(":", 2)
    data = await state.get_data()
    waves: dict = data.get("waves", {})
    waves[subject] = wave_key
    new_idx = data["current_wave_idx"] + 1
    await state.update_data(waves=waves, current_wave_idx=new_idx)
    await _ask_wave_settings(callback, state)


async def _save_subjects(
    callback: CallbackQuery,
    state: FSMContext,
    selected: list[str],
) -> None:
    from datetime import datetime

    data = await state.get_data()
    waves: dict[str, str] = data.get("waves", {})

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User)
            .where(User.telegram_id == callback.from_user.id)
            .options(selectinload(User.subjects))
        )
        user = result.scalar_one_or_none()
        if not user:
            return

        # Вычисляем правильный год экзамена
        now = datetime.utcnow()
        base_year = now.year + 1 if now.month >= 7 else now.year
        year = base_year + 1 if user.grade == 10 else base_year

        existing = {s.subject_name: s for s in user.subjects}

        # Удаляем предметы, которые убрали
        for name, subj in existing.items():
            if name not in selected:
                await session.delete(subj)

        # Добавляем новые
        for name in selected:
            if name not in existing:
                wave_key = waves.get(name, "main")
                sched_result = await session.execute(
                    select(ExamSchedule).where(
                        ExamSchedule.subject_name == name,
                        ExamSchedule.wave == wave_key,
                        ExamSchedule.year == year,
                    )
                )
                schedule = sched_result.scalar_one_or_none()
                us = UserSubject(
                    user_id=user.id,
                    subject_name=name,
                    wave=wave_key,
                    exam_date=schedule.exam_date if schedule else None,
                )
                session.add(us)

        await session.commit()

    await state.clear()
    await callback.message.edit_text(
        "✅ Предметы обновлены!",
        reply_markup=settings_kb(),
    )


# ──────────────────────────────────────────────────────────────
# Режим отдыха
# ──────────────────────────────────────────────────────────────

@router.callback_query(F.data == "settings:rest")
async def settings_rest(callback: CallbackQuery) -> None:
    await callback.message.edit_text(
        "🛌 <b>Режим «Отдых»</b>\n\n"
        "Чувствуешь выгорание? Поставь отсчет на паузу. "
        "Я перестану присылать тревожные таймеры и буду только напоминать о важности сна.\n\n"
        "На сколько дней берем перерыв?",
        reply_markup=rest_kb(), parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("rest:"))
async def process_rest(callback: CallbackQuery) -> None:
    days = int(callback.data.split(":")[1])

    async with AsyncSessionLocal() as session:
        user = await session.scalar(select(User).where(User.telegram_id == callback.from_user.id))
        if not user:
            return

        if days == 0:
            user.rest_until = None
            text = "Режим отдыха отключен. Возвращаемся к работе! 🚀"
        else:
            from datetime import datetime, timedelta
            user.rest_until = datetime.utcnow() + timedelta(days=days)
            text = f"Понял тебя. Уходим на отдых на {days} дней. 🛌\nНикакого стресса, только восстановление сил!"

        await session.commit()

    await callback.message.edit_text(text, reply_markup=settings_kb())