from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Plan(Base):
    __tablename__ = "plans"

    id: Mapped[int] = mapped_column(primary_key=True)
    category: Mapped[str] = mapped_column(String(80))
    name: Mapped[str] = mapped_column(String(120))
    price: Mapped[int] = mapped_column(Integer)  # whole rupees
    unit: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text)
    features: Mapped[list[str]] = mapped_column(JSON, default=list)
    href: Mapped[str] = mapped_column(String(120))
    cta: Mapped[str] = mapped_column(String(120))
    billing: Mapped[str] = mapped_column(String(20), default="monthly")
    featured: Mapped[bool] = mapped_column(Boolean, default=False)
    position: Mapped[int] = mapped_column(Integer, default=0)


class Contact(Base):
    __tablename__ = "contacts"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(254))
    interest: Mapped[str] = mapped_column(String(80))
    message: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Admin(Base):
    __tablename__ = "admins"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    password_hash: Mapped[str] = mapped_column(String(300))


class PersonalPrice(Base):
    """Price for a personal-class mode (online/offline) over one period."""

    __tablename__ = "personal_prices"
    __table_args__ = (UniqueConstraint("mode", "period"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    mode: Mapped[str] = mapped_column(String(10))  # online | offline
    period: Mapped[str] = mapped_column(String(10))  # hour | week | month
    price: Mapped[int] = mapped_column(Integer)  # whole rupees
    note: Mapped[str] = mapped_column(String(120), default="")


class GroupPrice(Base):
    """Price for online group classes over one period (no offline group classes)."""

    __tablename__ = "group_prices"

    id: Mapped[int] = mapped_column(primary_key=True)
    period: Mapped[str] = mapped_column(String(10), unique=True)  # hour | week | month
    price: Mapped[int] = mapped_column(Integer)  # whole rupees
    note: Mapped[str] = mapped_column(String(120), default="")
