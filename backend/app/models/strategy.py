import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import StrategyType


class Strategy(Base):
    __tablename__ = "strategies"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    strategy_type: Mapped[StrategyType] = mapped_column(
        String(20), nullable=False
    )
    config: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    owner: Mapped["User"] = relationship("User", back_populates="strategies")
    backtest_results: Mapped[list["BacktestResult"]] = relationship(
        "BacktestResult", back_populates="strategy", lazy="selectin"
    )
