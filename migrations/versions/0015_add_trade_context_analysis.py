"""add cached trade context explanations

Revision ID: 0015
Revises: 0014
Create Date: 2026-10-09 18:00:00.000000

Additive only: one new table. No existing table or row is touched. Downgrade drops it (generated text, recomputable).
"""
from alembic import op
import sqlalchemy as sa


revision = '0015'
down_revision = '0014'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'trade_context_analysis',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('trade_id', sa.Integer(), nullable=False),
        sa.Column('context_version', sa.String(length=60), nullable=False),
        sa.Column('mapping_version', sa.String(length=40), nullable=True),
        sa.Column('prompt_version', sa.String(length=20), nullable=False),
        sa.Column('model', sa.String(length=80), nullable=False),
        sa.Column('input_hash', sa.String(length=64), nullable=False),
        sa.Column('context_digest', sa.String(length=64), nullable=False),
        sa.Column('generated_for', sa.String(length=10), nullable=False),
        sa.Column('headline', sa.Text(), nullable=False),
        sa.Column('summary', sa.Text(), nullable=False),
        sa.Column('signals_json', sa.Text(), nullable=False),
        sa.Column('limitations', sa.Text(), nullable=False),
        sa.Column('input_tokens', sa.Integer(), nullable=True),
        sa.Column('output_tokens', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['trade_id'], ['trades.id'], name=op.f('fk_trade_context_analysis_trade_id_trades')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_trade_context_analysis')),
        sa.UniqueConstraint('trade_id', 'context_version', 'mapping_version', 'prompt_version', 'model', name=op.f('uq_trade_context_analysis_trade_id')),
    )
    op.create_index(op.f('ix_trade_context_analysis_trade_id'), 'trade_context_analysis', ['trade_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_trade_context_analysis_trade_id'), table_name='trade_context_analysis')
    op.drop_table('trade_context_analysis')
