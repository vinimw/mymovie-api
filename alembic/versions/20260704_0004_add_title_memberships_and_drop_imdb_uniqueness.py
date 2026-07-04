"""add title memberships and drop global imdb uniqueness

Revision ID: 20260704_0004
Revises: 20260704_0003
Create Date: 2026-07-04 15:20:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260704_0004"
down_revision = "20260704_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "title_memberships",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("watched_title_id", sa.Integer(), nullable=False),
        sa.Column("user_email", sa.String(length=255), nullable=False),
        sa.ForeignKeyConstraint(["watched_title_id"], ["watched_titles.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("watched_title_id", "user_email", name="uq_title_memberships_title_user"),
    )
    op.create_index("ix_title_memberships_watched_title_id", "title_memberships", ["watched_title_id"], unique=False)
    op.create_index("ix_title_memberships_user_email", "title_memberships", ["user_email"], unique=False)

    op.execute("DROP INDEX IF EXISTS ix_watched_titles_imdb_id")
    op.execute("ALTER TABLE watched_titles DROP CONSTRAINT IF EXISTS watched_titles_imdb_id_key")
    op.create_index("ix_watched_titles_imdb_id", "watched_titles", ["imdb_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_watched_titles_imdb_id", table_name="watched_titles")
    op.create_index("ix_watched_titles_imdb_id", "watched_titles", ["imdb_id"], unique=True)
    op.execute("ALTER TABLE watched_titles ADD CONSTRAINT watched_titles_imdb_id_key UNIQUE (imdb_id)")

    op.drop_index("ix_title_memberships_user_email", table_name="title_memberships")
    op.drop_index("ix_title_memberships_watched_title_id", table_name="title_memberships")
    op.drop_table("title_memberships")
