"""add comments to watched titles

Revision ID: 20260703_0002
Revises: 20260630_0001
Create Date: 2026-07-03 16:30:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260703_0002"
down_revision = "20260630_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("watched_titles", sa.Column("comments", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("watched_titles", "comments")
