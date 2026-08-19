"""
Скрипт для заполнения базы данных расписанием экзаменов.
"""
import asyncio
from datetime import datetime
from sqlalchemy import delete

from database.engine import init_db, AsyncSessionLocal
from database.models import ExamSchedule

SCHEDULE_2027 = [
    # ─── ДОСРОЧНЫЙ ПЕРИОД (early) ──────────────────────────────
    ("География", "early", datetime(2027, 3, 20)),
    ("Литература", "early", datetime(2027, 3, 20)),
    ("Русский язык", "early", datetime(2027, 3, 24)),
    ("Математика (база)", "early", datetime(2027, 3, 27)),
    ("Математика (профиль)", "early", datetime(2027, 3, 27)),
    ("Биология", "early", datetime(2027, 3, 31)),
    ("Иностранный язык", "early", datetime(2027, 3, 31)),  # Письменная часть
    ("Физика", "early", datetime(2027, 3, 31)),
    ("Информатика", "early", datetime(2027, 4, 7)),
    ("Обществознание", "early", datetime(2027, 4, 7)),
    ("История", "early", datetime(2027, 4, 10)),
    ("Химия", "early", datetime(2027, 4, 10)),

    # ─── ОСНОВНОЙ ПЕРИОД (main) ────────────────────────────────
    ("История", "main", datetime(2027, 6, 1)),
    ("Литература", "main", datetime(2027, 6, 1)),
    ("Химия", "main", datetime(2027, 6, 1)),
    ("Русский язык", "main", datetime(2027, 6, 4)),  # Берем 1-й день (4 июня)
    ("Математика (база)", "main", datetime(2027, 6, 8)),
    ("Математика (профиль)", "main", datetime(2027, 6, 8)),
    ("Обществознание", "main", datetime(2027, 6, 11)),
    ("Физика", "main", datetime(2027, 6, 11)),
    ("Биология", "main", datetime(2027, 6, 15)),
    ("География", "main", datetime(2027, 6, 15)),
    ("Иностранный язык", "main", datetime(2027, 6, 15)),  # Письменная часть
    ("Информатика", "main", datetime(2027, 6, 18)),  # Берем 1-й день (18 июня)

    # ─── ДНИ ПЕРЕСДАЧИ / ПРЕЗИДЕНТСКАЯ ВОЛНА (presidential) ────
    # 8 июля
    ("Иностранный язык", "presidential", datetime(2027, 7, 8)),
    ("Информатика", "presidential", datetime(2027, 7, 8)),
    ("Литература", "presidential", datetime(2027, 7, 8)),
    ("Русский язык", "presidential", datetime(2027, 7, 8)),
    ("Физика", "presidential", datetime(2027, 7, 8)),
    ("Химия", "presidential", datetime(2027, 7, 8)),
    # 9 июля
    ("Биология", "presidential", datetime(2027, 7, 9)),
    ("География", "presidential", datetime(2027, 7, 9)),
    ("Математика (база)", "presidential", datetime(2027, 7, 9)),
    ("Математика (профиль)", "presidential", datetime(2027, 7, 9)),
    ("История", "presidential", datetime(2027, 7, 9)),
    ("Обществознание", "presidential", datetime(2027, 7, 9)),

    # ─── ДОПОЛНИТЕЛЬНЫЙ ПЕРИОД (additional) ────────────────────
    ("Русский язык", "additional", datetime(2027, 9, 4)),
    ("Математика (база)", "additional", datetime(2027, 9, 8)),
]


async def main():
    await init_db()
    async with AsyncSessionLocal() as session:
        # Чистим старые данные за 2027 год, чтобы избежать дублей
        await session.execute(delete(ExamSchedule).where(ExamSchedule.year == 2027))

        # Заливаем новые даты
        for subj, wave, date in SCHEDULE_2027:
            exam = ExamSchedule(
                subject_name=subj,
                wave=wave,
                year=2027,
                exam_date=date,
                is_approximate=False
            )
            session.add(exam)

        await session.commit()
        print(f"✅ Успешно загружено {len(SCHEDULE_2027)} дат экзаменов на 2027 год!")


if __name__ == "__main__":
    asyncio.run(main())