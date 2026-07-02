"""create watched titles and episodes tables

Revision ID: 20260630_0001
Revises:
Create Date: 2026-06-30 21:00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260630_0001"
down_revision = None
branch_labels = None
depends_on = None


title_type_enum = sa.Enum("movie", "series", name="title_type_enum", native_enum=False, create_constraint=True)
watch_status_enum = sa.Enum(
    "watched",
    "watching",
    "paused",
    "want_to_watch",
    "abandoned",
    name="watch_status_enum",
    native_enum=False,
    create_constraint=True,
)


def upgrade() -> None:
    op.create_table(
        "watched_titles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("imdb_id", sa.String(length=32), nullable=False, unique=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("original_title", sa.String(length=255), nullable=True),
        sa.Column("title_type", title_type_enum, nullable=False),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("poster_url", sa.String(length=500), nullable=True),
        sa.Column("plot", sa.Text(), nullable=True),
        sa.Column("runtime_minutes", sa.Integer(), nullable=True),
        sa.Column("user_rating", sa.Integer(), nullable=True),
        sa.Column("status", watch_status_enum, nullable=False),
        sa.Column("watched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("user_rating IS NULL OR user_rating BETWEEN 1 AND 5", name="ck_watched_titles_rating"),
    )
    op.create_index("ix_watched_titles_imdb_id", "watched_titles", ["imdb_id"], unique=True)
    op.create_index("ix_watched_titles_status", "watched_titles", ["status"], unique=False)
    op.create_index("ix_watched_titles_title_type", "watched_titles", ["title_type"], unique=False)
    op.create_index("ix_watched_titles_watched_at", "watched_titles", ["watched_at"], unique=False)

    op.create_table(
        "watched_episodes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("watched_title_id", sa.Integer(), nullable=False),
        sa.Column("imdb_episode_id", sa.String(length=32), nullable=False),
        sa.Column("season_number", sa.Integer(), nullable=False),
        sa.Column("episode_number", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("plot", sa.Text(), nullable=True),
        sa.Column("runtime_minutes", sa.Integer(), nullable=True),
        sa.Column("watched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["watched_title_id"], ["watched_titles.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "watched_title_id",
            "imdb_episode_id",
            name="uq_watched_episodes_title_episode",
        ),
    )
    op.create_index(
        "ix_watched_episodes_watched_title_id",
        "watched_episodes",
        ["watched_title_id"],
        unique=False,
    )
    op.create_index(
        "ix_watched_episodes_watched_at",
        "watched_episodes",
        ["watched_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_watched_episodes_watched_at", table_name="watched_episodes")
    op.drop_index("ix_watched_episodes_watched_title_id", table_name="watched_episodes")
    op.drop_table("watched_episodes")

    op.drop_index("ix_watched_titles_watched_at", table_name="watched_titles")
    op.drop_index("ix_watched_titles_title_type", table_name="watched_titles")
    op.drop_index("ix_watched_titles_status", table_name="watched_titles")
    op.drop_index("ix_watched_titles_imdb_id", table_name="watched_titles")
    op.drop_table("watched_titles")
