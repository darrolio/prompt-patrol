"""Add prompt_saves table

Revision ID: 002
Revises: 001
Create Date: 2026-03-20
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "prompt_saves",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("prompt_id", sa.Uuid(), sa.ForeignKey("prompts.id"), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_prompt_saves_prompt_id", "prompt_saves", ["prompt_id"])


def downgrade() -> None:
    op.drop_table("prompt_saves")
