from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import CHANNEL_USERNAME, SUBJECT_WAVES, SUBJECTS, SUPPORT_USERNAME, WAVES


# ──────────────────────────────────────────────────────────────
# Главное меню
# ──────────────────────────────────────────────────────────────

def main_menu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📊 Мой статус",   callback_data="menu:status")
    builder.button(text="💬 Фраза дня",    callback_data="menu:today")
    builder.button(text="🍅 Фокус",        callback_data="menu:focus")
    builder.button(text="⚙️ Настройки",    callback_data="menu:settings")
    builder.button(text="✅ Сдал экзамен", callback_data="menu:done")
    builder.adjust(2, 1, 2)
    return builder.as_markup()


# ──────────────────────────────────────────────────────────────
# Проверка подписки на канал
# ──────────────────────────────────────────────────────────────

def subscription_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📢 Подписаться на канал", url=f"https://t.me/{CHANNEL_USERNAME}")
    builder.button(text="✅ Я подписался",         callback_data="check_subscription")
    builder.adjust(1)
    return builder.as_markup()


# ──────────────────────────────────────────────────────────────
# Онбординг — выбор класса
# ──────────────────────────────────────────────────────────────

def grade_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="10 класс", callback_data="grade:10")
    builder.button(text="11 класс", callback_data="grade:11")
    builder.adjust(2)
    return builder.as_markup()


# ──────────────────────────────────────────────────────────────
# Выбор часового пояса
# ──────────────────────────────────────────────────────────────

TIMEZONE_OPTIONS: list[tuple[str, str]] = [
    ("Москва (UTC+3)",        "Europe/Moscow"),
    ("Самара (UTC+4)",        "Europe/Samara"),
    ("Екатеринбург (UTC+5)",  "Asia/Yekaterinburg"),
    ("Новосибирск (UTC+7)",   "Asia/Novosibirsk"),
    ("Владивосток (UTC+10)",  "Asia/Vladivostok"),
]

def timezone_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for label, tz in TIMEZONE_OPTIONS:
        builder.button(text=label, callback_data=f"tz:{tz}")
    builder.adjust(1)
    return builder.as_markup()


# ──────────────────────────────────────────────────────────────
# Выбор времени уведомлений
# ──────────────────────────────────────────────────────────────

NOTIFY_HOURS: list[int] = [6, 7, 8, 9, 10]

def notify_time_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for h in NOTIFY_HOURS:
        builder.button(text=f"{h:02d}:00", callback_data=f"notify:{h}:0")
    builder.adjust(3)
    return builder.as_markup()


# ──────────────────────────────────────────────────────────────
# Мультиселект предметов
# ──────────────────────────────────────────────────────────────

def subjects_kb(selected: set[str]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for subj in SUBJECTS:
        mark = "✅ " if subj in selected else ""
        builder.button(text=f"{mark}{subj}", callback_data=f"subj:{subj}")
    builder.button(text="➡️ Продолжить", callback_data="subj:confirm")
    builder.adjust(1)
    return builder.as_markup()


# ──────────────────────────────────────────────────────────────
# Выбор волны — только доступные для предмета
# ──────────────────────────────────────────────────────────────

def wave_kb(subject: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    available = SUBJECT_WAVES.get(subject, list(WAVES.keys()))
    for wave_key in available:
        wave_label = WAVES[wave_key]
        builder.button(text=wave_label, callback_data=f"wave:{subject}:{wave_key}")
    builder.adjust(1)
    return builder.as_markup()


# ──────────────────────────────────────────────────────────────
# Меню настроек
# ──────────────────────────────────────────────────────────────

def settings_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🕐 Время уведомлений", callback_data="settings:time")
    builder.button(text="📚 Предметы и волны",  callback_data="settings:subjects")
    builder.button(text="🌍 Часовой пояс",      callback_data="settings:timezone")
    builder.button(text="🛌 Взять перерыв",     callback_data="settings:rest")
    builder.button(text="💡 Пожелания и баги",  url=f"https://t.me/{SUPPORT_USERNAME}")
    builder.button(text="◀️ Назад",             callback_data="menu:back")
    builder.adjust(1)
    return builder.as_markup()


# ──────────────────────────────────────────────────────────────
# Список предметов для «Сдал экзамен»
# ──────────────────────────────────────────────────────────────

def done_subjects_kb(active_subjects: list[str]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for subj in active_subjects:
        builder.button(text=subj, callback_data=f"done:{subj}")
    builder.button(text="◀️ Назад", callback_data="menu:back")
    builder.adjust(1)
    return builder.as_markup()


# ──────────────────────────────────────────────────────────────
# Подтверждение действия
# ──────────────────────────────────────────────────────────────

def confirm_kb(yes_data: str, no_data: str = "menu:back") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Да",  callback_data=yes_data)
    builder.button(text="❌ Нет", callback_data=no_data)
    builder.adjust(2)
    return builder.as_markup()


# ──────────────────────────────────────────────────────────────
# Новые механики (Капсула времени, Фокус, Отдых, Рефлексия)
# ──────────────────────────────────────────────────────────────

def skip_capsule_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Пропустить ➡️", callback_data="capsule:skip")
    return builder.as_markup()


def focus_subject_kb(active_subjects: list[str]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for subj in active_subjects:
        builder.button(text=subj, callback_data=f"focus:subj:{subj}")
    builder.button(text="◀️ Назад", callback_data="menu:back")
    builder.adjust(1)
    return builder.as_markup()


def focus_time_kb(subject: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for t in [25, 45, 60]:
        builder.button(text=f"{t} мин", callback_data=f"focus:time:{subject}:{t}")
    builder.button(text="◀️ Назад", callback_data="menu:focus")
    builder.adjust(3, 1)
    return builder.as_markup()


def rest_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="1 день", callback_data="rest:1")
    builder.button(text="3 дня", callback_data="rest:3")
    builder.button(text="5 дней", callback_data="rest:5")
    builder.button(text="❌ Отключить отдых", callback_data="rest:0")
    builder.button(text="◀️ Назад", callback_data="menu:settings")
    builder.adjust(3, 1, 1)
    return builder.as_markup()


def reflection_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Да", callback_data="reflection:yes")
    builder.button(text="❌ Нет", callback_data="reflection:no")
    builder.adjust(2)
    return builder.as_markup()