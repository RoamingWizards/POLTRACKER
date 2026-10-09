"""add secondary signal count, committee temporal status and the rule-met marker to trade_context

Revision ID: 0013
Revises: 0012
Create Date: 2026-10-08 15:00:00.000000

Additive only: three nullable columns on trade_context (derived data). Rows written before this migration keep NULL in them.
"""
from alembic import op
import sqlalchemy as sa


revision = '0013'
down_revision = '0012'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('trade_context', schema=None) as batch_op:
        batch_op.add_column(sa.Column('secondary_signal_count', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('committee_temporal_status', sa.String(length=30), nullable=True))
        batch_op.add_column(sa.Column('meets_flag_rule', sa.Boolean(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('trade_context', schema=None) as batch_op:
        for name in ('meets_flag_rule', 'committee_temporal_status', 'secondary_signal_count'):
            batch_op.drop_column(name)
