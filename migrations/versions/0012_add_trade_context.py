"""add trade context signals and their evidence

Revision ID: 0012
Revises: 0011
Create Date: 2026-10-08 12:00:00.000000

Additive only: two new tables. No existing table or row is touched. Downgrade drops both tables (derived data, recomputable).
"""
from alembic import op
import sqlalchemy as sa


revision = '0012'
down_revision = '0011'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'trade_context',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('trade_id', sa.Integer(), nullable=False),
        sa.Column('context_version', sa.String(length=60), nullable=False),
        sa.Column('mapping_version', sa.String(length=40), nullable=True),
        sa.Column('result_digest', sa.String(length=64), nullable=False),
        sa.Column('analyzed_at', sa.DateTime(), nullable=False),
        sa.Column('committee_relevance', sa.Boolean(), nullable=True),
        sa.Column('trade_size_anomaly', sa.Boolean(), nullable=True),
        sa.Column('disclosure_delay_signal', sa.Boolean(), nullable=True),
        sa.Column('excess_return_signal', sa.Boolean(), nullable=True),
        sa.Column('committee_relevance_reason', sa.String(length=40), nullable=True),
        sa.Column('trade_size_value', sa.Float(), nullable=True),
        sa.Column('trade_size_basis', sa.String(length=30), nullable=True),
        sa.Column('trade_size_percentile', sa.Float(), nullable=True),
        sa.Column('trade_size_sample_size', sa.Integer(), nullable=True),
        sa.Column('trade_size_median', sa.Float(), nullable=True),
        sa.Column('disclosure_delay_days', sa.Integer(), nullable=True),
        sa.Column('performance_status', sa.String(length=30), nullable=True),
        sa.Column('security_return', sa.Float(), nullable=True),
        sa.Column('spy_return', sa.Float(), nullable=True),
        sa.Column('excess_return', sa.Float(), nullable=True),
        sa.Column('excess_return_direction_adjusted', sa.Float(), nullable=True),
        sa.Column('performance_anchor_date', sa.Date(), nullable=True),
        sa.Column('performance_through_date', sa.Date(), nullable=True),
        sa.Column('performance_horizon_days', sa.Integer(), nullable=True),
        sa.Column('signal_count', sa.Integer(), nullable=False),
        sa.Column('flagged_for_contextual_review', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['trade_id'], ['trades.id'], name=op.f('fk_trade_context_trade_id_trades')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_trade_context')),
        sa.UniqueConstraint('trade_id', 'context_version', 'mapping_version', name=op.f('uq_trade_context_trade_id')),
    )
    op.create_index(op.f('ix_trade_context_trade_id'), 'trade_context', ['trade_id'], unique=False)
    op.create_index('ix_trade_context_version_flagged', 'trade_context',
                    ['context_version', 'mapping_version', 'flagged_for_contextual_review'], unique=False)
    op.create_table(
        'trade_context_evidence',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('trade_context_id', sa.Integer(), nullable=False),
        sa.Column('trade_id', sa.Integer(), nullable=False),
        sa.Column('signal_type', sa.String(length=30), nullable=False),
        sa.Column('evidence_type', sa.String(length=30), nullable=False),
        sa.Column('evidence_key', sa.String(length=60), nullable=False),
        sa.Column('committee_code', sa.String(length=20), nullable=True),
        sa.Column('subcommittee_code', sa.String(length=20), nullable=True),
        sa.Column('mapping_id', sa.Integer(), nullable=True),
        sa.Column('source_url', sa.String(length=500), nullable=True),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('metadata_json', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['trade_context_id'], ['trade_context.id'], name=op.f('fk_trade_context_evidence_trade_context_id_trade_context'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['trade_id'], ['trades.id'], name=op.f('fk_trade_context_evidence_trade_id_trades')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_trade_context_evidence')),
        sa.UniqueConstraint('trade_context_id', 'signal_type', 'evidence_key', name=op.f('uq_trade_context_evidence_trade_context_id')),
    )
    op.create_index(op.f('ix_trade_context_evidence_trade_context_id'), 'trade_context_evidence', ['trade_context_id'], unique=False)
    op.create_index(op.f('ix_trade_context_evidence_trade_id'), 'trade_context_evidence', ['trade_id'], unique=False)


def downgrade() -> None:
    op.drop_table('trade_context_evidence')
    op.drop_table('trade_context')
