from dotenv import load_dotenv
import os

load_dotenv()

BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
ADMIN_IDS: list[int] = [int(i) for i in os.getenv("ADMIN_IDS", "").split(",") if i]
DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///ege_bot.db")

CHANNEL_USERNAME: str = os.getenv("CHANNEL_USERNAME", "your_channel")
SUPPORT_USERNAME: str = os.getenv("SUPPORT_USERNAME", "your_username")

# Все доступные предметы ЕГЭ
SUBJECTS: list[str] = [
    "Математика (профиль)",
    "Математика (база)",
    "Русский язык",
    "Физика",
    "Химия",
    "Биология",
    "История",
    "Обществознание",
    "География",
    "Информатика",
    "Литература",
    "Иностранный язык",
]

# Волны сдачи
WAVES: dict[str, str] = {
    "early":        "Досрочная (март–апрель)",
    "main":         "Основная (июнь)",
    "additional":   "Дополнительная (сентябрь)",
    "presidential": "Президентская (сентябрь)",
}

# Какие волны доступны для каждого предмета.
# Если предмета нет в списке волны — кнопка не показывается.
SUBJECT_WAVES: dict[str, list[str]] = {
    "Математика (профиль)": ["early", "main", "presidential"],
    "Математика (база)":    ["early", "main", "additional", "presidential"],
    "Русский язык":         ["early", "main", "additional", "presidential"],
    "Физика":               ["early", "main", "presidential"],
    "Химия":                ["early", "main", "presidential"],
    "Биология":             ["early", "main", "presidential"],
    "История":              ["early", "main", "presidential"],
    "Обществознание":       ["early", "main", "presidential"],
    "География":            ["early", "main", "presidential"],
    "Информатика":          ["early", "main", "presidential"],
    "Литература":           ["early", "main", "presidential"],
    "Иностранный язык":     ["early", "main", "presidential"],
}

# За сколько дней слать спецнапоминание
REMINDER_DAYS: list[int] = [7, 3, 1]
