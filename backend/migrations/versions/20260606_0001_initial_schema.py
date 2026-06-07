"""initial_schema

Revision ID: 0001
Revises:
Create Date: 2026-06-06
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- users ---
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(200), nullable=True),
        sa.Column(
            "plan",
            sa.String(20),
            nullable=False,
            server_default="free",
        ),
        sa.Column("stripe_customer_id", sa.String(100), nullable=True),
        sa.Column("stripe_subscription_id", sa.String(100), nullable=True),
        sa.Column(
            "backtest_count_today",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "backtest_count_reset_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("email", name=op.f("uq_users_email")),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    # --- strategies ---
    op.create_table(
        "strategies",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column(
            "strategy_type",
            sa.String(20),
            nullable=False,
        ),
        sa.Column(
            "config",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "is_public",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_strategies_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_strategies")),
    )
    op.create_index(
        op.f("ix_strategies_user_id"), "strategies", ["user_id"], unique=False
    )

    # --- backtest_results ---
    op.create_table(
        "backtest_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "strategy_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("ticker", sa.String(20), nullable=False),
        sa.Column(
            "data_source",
            sa.String(20),
            nullable=False,
            server_default="yahoo",
        ),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column(
            "initial_capital",
            sa.Float(),
            nullable=False,
            server_default="10000",
        ),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="pending",
        ),
        # Result metrics
        sa.Column("total_return", sa.Float(), nullable=True),
        sa.Column("annual_return", sa.Float(), nullable=True),
        sa.Column("sharpe_ratio", sa.Float(), nullable=True),
        sa.Column("max_drawdown", sa.Float(), nullable=True),
        sa.Column("win_rate", sa.Float(), nullable=True),
        sa.Column("total_trades", sa.Integer(), nullable=True),
        sa.Column("profit_factor", sa.Float(), nullable=True),
        # Full result blob
        sa.Column("result_data", postgresql.JSONB(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "completed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_backtest_results_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["strategy_id"],
            ["strategies.id"],
            name=op.f("fk_backtest_results_strategy_id_strategies"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_backtest_results")),
    )
    op.create_index(
        op.f("ix_backtest_results_user_id"),
        "backtest_results",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_backtest_results_strategy_id"),
        "backtest_results",
        ["strategy_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_table("backtest_results")
    op.drop_index(op.f("ix_strategies_user_id"), table_name="strategies")
    op.drop_table("strategies")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
