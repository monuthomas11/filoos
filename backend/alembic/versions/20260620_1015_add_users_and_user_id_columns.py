"""add users and user_id columns

Revision ID: 2a3b4c5d6e7f
Revises: fb627ac5984d
Create Date: 2026-06-20 10:15:00.000000+00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2a3b4c5d6e7f"
down_revision: str | Sequence[str] | None = "fb627ac5984d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Tables that need user_id added (order matters for downgrade)
_TABLES = ["accounts", "categories", "budgets", "recurring_rules", "transactions"]


def _table_exists(table_name: str, bind) -> bool:
    from sqlalchemy import inspect as sa_inspect

    return table_name in sa_inspect(bind).get_table_names()


def _column_exists(table_name: str, column_name: str, bind) -> bool:
    from sqlalchemy import inspect as sa_inspect

    columns = [c["name"] for c in sa_inspect(bind).get_columns(table_name)]
    return column_name in columns


def upgrade() -> None:
    bind = op.get_bind()

    # create users table (skip if already exists from a partial prior run)
    if not _table_exists("users", bind):
        op.create_table(
            "users",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("email", sa.String(length=255), nullable=False),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("google_sub", sa.String(length=64), nullable=False),
            sa.Column("last_login_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("email"),
            sa.UniqueConstraint("google_sub"),
        )

    # add user_id nullable FK to existing tables (batch mode for SQLite)
    for table in _TABLES:
        if not _column_exists(table, "user_id", bind):
            with op.batch_alter_table(table) as batch_op:
                batch_op.add_column(sa.Column("user_id", sa.Integer(), nullable=True))
                batch_op.create_foreign_key(
                    f"fk_{table}_user_id_users", "users", ["user_id"], ["id"]
                )


def downgrade() -> None:
    bind = op.get_bind()

    for table in reversed(_TABLES):
        if _column_exists(table, "user_id", bind):
            with op.batch_alter_table(table) as batch_op:
                batch_op.drop_constraint(f"fk_{table}_user_id_users", type_="foreignkey")
                batch_op.drop_column("user_id")

    if _table_exists("users", bind):
        op.drop_table("users")
