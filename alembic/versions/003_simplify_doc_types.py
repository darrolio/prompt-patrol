"""Simplify doc_type to product/compliance/technical

Revision ID: 003
Revises: 002
Create Date: 2026-03-21
"""
from typing import Sequence, Union

from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Consolidate old sub-types into "product"
    op.execute(
        "UPDATE product_docs SET doc_type = 'product' "
        "WHERE doc_type IN ('vision', 'roadmap', 'story', 'general')"
    )


def downgrade() -> None:
    # Can't reliably restore original sub-types; leave as "product"
    pass
