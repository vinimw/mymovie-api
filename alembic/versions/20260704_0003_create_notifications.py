"""create notifications table

Revision ID: 20260704_0003
Revises: 20260703_0002
Create Date: 2026-07-04 11:10:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260704_0003"
down_revision = "20260703_0002"
branch_labels = None
depends_on = None


notification_kind_enum = sa.Enum(
    "title_added",
    "title_deleted",
    "title_status_updated",
    "title_rating_updated",
    "title_comment_added",
    "title_comment_updated",
    "title_comment_removed",
    "episodes_added",
    "episode_deleted",
    name="notification_kind_enum",
    native_enum=False,
    create_constraint=True,
)


def upgrade() -> None:
    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("recipient_email", sa.String(length=255), nullable=False),
        sa.Column("actor_email", sa.String(length=255), nullable=False),
        sa.Column("actor_display_name", sa.String(length=120), nullable=False),
        sa.Column("kind", notification_kind_enum, nullable=False),
        sa.Column("title_id", sa.Integer(), nullable=True),
        sa.Column("title_name", sa.String(length=255), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_notifications_recipient_email", "notifications", ["recipient_email"], unique=False)
    op.create_index("ix_notifications_kind", "notifications", ["kind"], unique=False)
    op.create_index("ix_notifications_title_id", "notifications", ["title_id"], unique=False)
    op.create_index("ix_notifications_is_read", "notifications", ["is_read"], unique=False)
    op.create_index("ix_notifications_created_at", "notifications", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_notifications_created_at", table_name="notifications")
    op.drop_index("ix_notifications_is_read", table_name="notifications")
    op.drop_index("ix_notifications_title_id", table_name="notifications")
    op.drop_index("ix_notifications_kind", table_name="notifications")
    op.drop_index("ix_notifications_recipient_email", table_name="notifications")
    op.drop_table("notifications")
