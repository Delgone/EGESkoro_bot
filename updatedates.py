# fix_dates.py
import asyncio
from sqlalchemy import select
from database.engine import init_db, AsyncSessionLocal
from database.models import UserSubject, ExamSchedule

async def main():
    await init_db()
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(UserSubject).where(UserSubject.exam_date == None)
        )
        subjects = result.scalars().all()
        print(f"Записей без даты: {len(subjects)}")

        fixed = 0
        for us in subjects:
            # Ищем без фильтра по году — берём любую подходящую запись
            sched = await session.execute(
                select(ExamSchedule).where(
                    ExamSchedule.subject_name == us.subject_name,
                    ExamSchedule.wave == us.wave,
                ).order_by(ExamSchedule.year.desc())  # берём самую свежую
            )
            schedule = sched.scalar_one_or_none()
            if schedule:
                us.exam_date = schedule.exam_date
                fixed += 1
                print(f"  ✅ {us.subject_name} → {schedule.exam_date}")
            else:
                print(f"  ❌ Не найдено: {us.subject_name!r} wave={us.wave!r}")

        await session.commit()
        print(f"\nГотово! Обновлено: {fixed} из {len(subjects)}")

asyncio.run(main())