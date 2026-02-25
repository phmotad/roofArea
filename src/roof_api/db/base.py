"""SQLAlchemy declarative base and shared mixins."""

from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from uuid import uuid4
from datetime import datetime


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
