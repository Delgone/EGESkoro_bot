# debug_db.py
import asyncio
from sqlalchemy import select
from database.engine import init_db, AsyncSessionLocal
from database.models import UserSubject, ExamSchedule, User

async def main():
    await init_db()
    async with AsyncSessionLocal() as session:

        print("=== РАСПИСАНИЕ (ExamSchedule) ===")
        schedules = (await session.execute(select(ExamSchedule))).scalars().all()
        if not schedules:
            print("  ПУСТО — скрипт seed_schedule.py не отработал!")
        for s in schedules:
            print(f"  {s.subject_name!r:30} | {s.wave:15} | {s.year} | {s.exam_date}")

        print("\n=== ПРЕДМЕТЫ ПОЛЬЗОВАТЕЛЕЙ (UserSubject) ===")
        subjects = (await session.execute(select(UserSubject))).scalars().all()
        if not subjects:
            print("  ПУСТО — пользователи ещё не добавили предметы")
        for s in subjects:
            print(f"  user_id={s.user_id} | {s.subject_name!r:30} | wave={s.wave!r:15} | date={s.exam_date} | passed={s.is_passed}")
if __name__ == "__main__":
    asyncio.run(main())