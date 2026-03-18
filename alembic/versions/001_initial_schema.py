"""Initial schema with all 5 tables

Revision ID: 001
Revises:
Create Date: 2026-03-17
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "developers",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("username", sa.String(100), unique=True, nullable=False),
        sa.Column("display_name", sa.String(200), nullable=False),
        sa.Column("api_key", sa.String(64), unique=True, nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "prompts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("developer_id", sa.Uuid(), sa.ForeignKey("developers.id"), nullable=False),
        sa.Column("session_id", sa.String(200), nullable=False),
        sa.Column("prompt_text", sa.Text(), nullable=False),
        sa.Column("source_tool", sa.String(50), nullable=False, server_default="claude_code"),
        sa.Column("project_name", sa.String(200)),
        sa.Column("ticket_number", sa.String(50)),
        sa.Column("metadata", sa.JSON()),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_prompts_submitted_at", "prompts", ["submitted_at"])
    op.create_index("ix_prompts_developer_id", "prompts", ["developer_id"])
    op.create_index("ix_prompts_ticket_number", "prompts", ["ticket_number"])

    op.create_table(
        "daily_reports",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("report_date", sa.Date(), unique=True, nullable=False),
        sa.Column("summary_text", sa.Text()),
        sa.Column("total_prompts", sa.Integer(), server_default="0"),
        sa.Column("flagged_count", sa.Integer(), server_default="0"),
        sa.Column("developer_count", sa.Integer(), server_default="0"),
        sa.Column("llm_model_used", sa.String(100)),
        sa.Column("status", sa.String(20), server_default="pending"),
        sa.Column("error_message", sa.Text()),
        sa.Column("review_started_at", sa.DateTime(timezone=True)),
        sa.Column("review_completed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "prompt_flags",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("prompt_id", sa.Uuid(), sa.ForeignKey("prompts.id"), nullable=False),
        sa.Column(
            "daily_report_id", sa.Uuid(), sa.ForeignKey("daily_reports.id"), nullable=False
        ),
        sa.Column("flag_type", sa.String(50), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_prompt_flags_prompt_id", "prompt_flags", ["prompt_id"])
    op.create_index("ix_prompt_flags_daily_report_id", "prompt_flags", ["daily_report_id"])

    op.create_table(
        "product_docs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("filename", sa.String(500), unique=True, nullable=False),
        sa.Column("display_name", sa.String(500), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("doc_type", sa.String(50), nullable=False, server_default="general"),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("uploaded_by", sa.String(200)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("prompt_flags")
    op.drop_table("daily_reports")
    op.drop_table("prompts")
    op.drop_table("product_docs")
    op.drop_table("developers")
