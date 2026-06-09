"""add share link fields to backtest_results

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-08
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("backtest_results", sa.Column("share_slug", sa.String(12), nullable=True))
    op.add_column("backtest_results", sa.Column("is_shared", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("backtest_results", sa.Column("share_created_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("backtest_results", sa.Column("share_view_count", sa.Integer(), nullable=False, server_default="0"))
    op.create_index(op.f("ix_backtest_results_share_slug"), "backtest_results", ["share_slug"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_backtest_results_share_slug"), table_name="backtest_results")
    op.drop_column("backtest_results", "share_view_count")
    op.drop_column("backtest_results", "share_created_at")
    op.drop_column("backtest_results", "is_shared")
    op.drop_column("backtest_results", "share_slug")
