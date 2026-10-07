"""add politician LLM suggestion cache and audit table

Revision ID: 0008
Revises: 0007
Create Date: 2026-10-07 15:00:00.000000

Additive only: one new, empty table.
"""
from alembic import op
import sqlalchemy as sa


revision = '0008'
down_revision = '0007'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'politician_llm_suggestions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('cache_key', sa.String(length=64), nullable=False),
        sa.Column('politician_id', sa.Integer(), nullable=True),
        sa.Column('incoming_name', sa.String(length=200), nullable=False),
        sa.Column('chamber', sa.String(length=10), nullable=False),
        sa.Column('candidate_ids', sa.String(length=2000), nullable=False),
        sa.Column('selected_bioguide_id', sa.String(length=10), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('explanation', sa.String(length=2000), nullable=True),
        sa.Column('alternates', sa.String(length=500), nullable=True),
        sa.Column('model', sa.String(length=80), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('outcome', sa.String(length=12), nullable=True),
        sa.Column('reason', sa.String(length=300), nullable=True),
        sa.Column('decided_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['politician_id'], ['politicians.id'], name=op.f('fk_politician_llm_suggestions_politician_id_politicians')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_politician_llm_suggestions')),
        sa.UniqueConstraint('cache_key', name=op.f('uq_politician_llm_suggestions_cache_key')),
    )
    op.create_index(op.f('ix_politician_llm_suggestions_politician_id'), 'politician_llm_suggestions', ['politician_id'])


def downgrade() -> None:
    op.drop_index(op.f('ix_politician_llm_suggestions_politician_id'), table_name='politician_llm_suggestions')
    op.drop_table('politician_llm_suggestions')
