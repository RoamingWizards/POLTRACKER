"""add saved context views and local preferences

Revision ID: 0016
Revises: 0015
Create Date: 2026-10-09 20:00:00.000000

Additive only: two new tables. No existing table or row is touched (trade_context is never written by personalization).
Downgrade drops both tables (user preferences only; the objective trade context is unaffected).
"""
from alembic import op
import sqlalchemy as sa


revision = '0016'
down_revision = '0015'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'context_views',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=80), nullable=False),
        sa.Column('preset', sa.String(length=30), nullable=True),
        sa.Column('rule_json', sa.Text(), nullable=False),
        sa.Column('filters_json', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_context_views')),
        sa.UniqueConstraint('name', name=op.f('uq_context_views_name')),
    )
    op.create_table(
        'app_preferences',
        sa.Column('key', sa.String(length=60), nullable=False),
        sa.Column('value_json', sa.Text(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('key', name=op.f('pk_app_preferences')),
    )


def downgrade() -> None:
    op.drop_table('app_preferences')
    op.drop_table('context_views')
