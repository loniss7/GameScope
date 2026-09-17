"""create game summaries

Revision ID: 9b2d3e7f4a61
Revises: 63f405c4c177
Create Date: 2026-09-17 12:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "9b2d3e7f4a61"
down_revision: str | None = "63f405c4c177"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "game_summaries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("game_id", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=40), nullable=False),
        sa.Column("model", sa.String(length=120), nullable=False),
        sa.Column("language", sa.String(length=16), nullable=False),
        sa.Column("reviews_hash", sa.String(length=64), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("pros", sa.JSON(), nullable=False),
        sa.Column("cons", sa.JSON(), nullable=False),
        sa.Column("sentiment", sa.JSON(), nullable=False),
        sa.Column("reviews_analyzed", sa.Integer(), nullable=False),
        sa.Column("reviews_total", sa.Integer(), nullable=False),
        sa.Column(
            "generated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["game_id"], ["games.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "game_id",
            "source",
            "model",
            "language",
            "reviews_hash",
            name="uq_game_summary_snapshot",
        ),
    )
    op.create_index(
        "ix_game_summaries_game_id", "game_summaries", ["game_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_game_summaries_game_id", table_name="game_summaries")
    op.drop_table("game_summaries")
