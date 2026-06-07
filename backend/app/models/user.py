import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Boolean, DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base
from app.models.enums import Plan


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    plan: Mapped[Plan] = mapped_column(
        String(20), default=Plan.free, nullable=False
    )
    stripe_customer_id: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )
    stripe_subscription_id: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )
    backtest_count_today: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    backtest_count_reset_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    strategies: Mapped[list["Strategy"]] = relationship(
        "Strategy", back_populates="owner", lazy="selectin"
    )
    backtest_results: Mapped[list["BacktestResult"]] = relationship(
        "BacktestResult", back_populates="owner", lazy="selectin"
    )
