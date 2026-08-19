from datetime import datetime
from sqlalchemy import (
    BigInteger, Boolean, DateTime, ForeignKey,
    Integer, String, Time, UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    """Зарегистрированный пользователь бота."""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(128), nullable=False)
    grade: Mapped[int] = mapped_column(Integer, nullable=False)          # 10 или 11
    timezone: Mapped[str] = mapped_column(String(64), default="Europe/Moscow")
    notify_hour: Mapped[int] = mapped_column(Integer, default=8)         # час рассылки
    notify_minute: Mapped[int] = mapped_column(Integer, default=0)
    phrase_index: Mapped[int] = mapped_column(Integer, default=0)        # текущая фраза
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # --- Новые поля для продуктовых фич ---
    streak_count: Mapped[int] = mapped_column(Integer, default=0)
    rest_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    capsule_message: Mapped[str | None] = mapped_column(String, nullable=True)

    subjects: Mapped[list["UserSubject"]] = relationship(
        "UserSubject", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User tg={self.telegram_id} name={self.full_name}>"


class UserSubject(Base):
    """Предмет, который сдаёт пользователь — с индивидуальной датой и волной."""
    __tablename__ = "user_subjects"
    __table_args__ = (
        UniqueConstraint("user_id", "subject_name", name="uq_user_subject"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    subject_name: Mapped[str] = mapped_column(String(64), nullable=False)
    wave: Mapped[str] = mapped_column(String(32), nullable=False)        # ключ из WAVES
    exam_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    is_passed: Mapped[bool] = mapped_column(Boolean, default=False)
    passed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="subjects")

    @property
    def days_left(self) -> int | None:
        if not self.exam_date or self.is_passed:
            return None
        delta = self.exam_date.date() - datetime.utcnow().date()
        return delta.days

    def __repr__(self) -> str:
        return f"<UserSubject {self.subject_name} wave={self.wave}>"


class ExamSchedule(Base):
    """Официальное расписание ЕГЭ — обновляется администратором раз в год."""
    __tablename__ = "exam_schedule"
    __table_args__ = (
        UniqueConstraint("subject_name", "wave", "year", name="uq_schedule"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    subject_name: Mapped[str] = mapped_column(String(64), nullable=False)
    wave: Mapped[str] = mapped_column(String(32), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    exam_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    is_approximate: Mapped[bool] = mapped_column(Boolean, default=False)  # для 10-классников

    def __repr__(self) -> str:
        return f"<ExamSchedule {self.subject_name} {self.wave} {self.year}>"