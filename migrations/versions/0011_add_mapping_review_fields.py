"""add human-review fields to committee/industry mappings

Revision ID: 0011
Revises: 0010
Create Date: 2026-10-08 09:00:00.000000

Additive only: four columns on committee_industry_mappings. Existing rows become needs_review, never reviewed.
"""
from alembic import op
import sqlalchemy as sa


revision = '0011'
down_revision = '0010'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('committee_industry_mappings', schema=None) as batch_op:
        batch_op.add_column(sa.Column('review_status', sa.String(length=15), nullable=False, server_default='needs_review'))
        batch_op.add_column(sa.Column('reviewed_by', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('review_note', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('jurisdiction_basis', sa.String(length=30), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('committee_industry_mappings', schema=None) as batch_op:
        for name in ('jurisdiction_basis', 'review_note', 'reviewed_by', 'review_status'):
            batch_op.drop_column(name)
