"""add show_on_dashboard, include_in_total; fix credit_card opening_balance

Revision ID: 3b4c5d6e7f8a
Revises: 2a3b4c5d6e7f
Create Date: 2026-06-26 10:00:00.000000+00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "3b4c5d6e7f8a"
down_revision: str | Sequence[str] | None = "2a3b4c5d6e7f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _column_exists(table_name: str, column_name: str, bind) -> bool:
    from sqlalchemy import inspect as sa_inspect

    columns = [c["name"] for c in sa_inspect(bind).get_columns(table_name)]
    return column_name in columns


def upgrade() -> None:
    bind = op.get_bind()

    with op.batch_alter_table("accounts") as batch_op:
        if not _column_exists("accounts", "show_on_dashboard", bind):
            batch_op.add_column(
                sa.Column("show_on_dashboard", sa.Boolean(), nullable=False, server_default=sa.text("true"))
            )
        if not _column_exists("accounts", "include_in_total", bind):
            batch_op.add_column(
                sa.Column("include_in_total", sa.Boolean(), nullable=False, server_default=sa.text("true"))
            )

    op.execute(
        "UPDATE accounts SET opening_balance = 0 WHERE type = 'CREDIT_CARD' AND opening_balance > 0"
    )


def downgrade() -> None:
    bind = op.get_bind()

    with op.batch_alter_table("accounts") as batch_op:
        if _column_exists("accounts", "include_in_total", bind):
            batch_op.drop_column("include_in_total")
        if _column_exists("accounts", "show_on_dashboard", bind):
            batch_op.drop_column("show_on_dashboard")
