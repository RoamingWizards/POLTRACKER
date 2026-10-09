"""add committee/industry mapping table

Revision ID: 0010
Revises: 0009
Create Date: 2026-10-07 20:00:00.000000

Additive only: one new, empty table.
"""
from alembic import op
import sqlalchemy as sa


revision = '0010'
down_revision = '0009'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'committee_industry_mappings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('chamber', sa.String(length=10), nullable=False),
        sa.Column('committee_code', sa.String(length=20), nullable=False),
        sa.Column('subcommittee_code', sa.String(length=20), nullable=True),
        sa.Column('committee_name', sa.String(length=300), nullable=False),
        sa.Column('subcommittee_name', sa.String(length=300), nullable=True),
        sa.Column('sic_start', sa.Integer(), nullable=True),
        sa.Column('sic_end', sa.Integer(), nullable=True),
        sa.Column('industry_pattern', sa.String(length=200), nullable=True),
        sa.Column('relevance_level', sa.String(length=10), nullable=False),
        sa.Column('rationale', sa.Text(), nullable=False),
        sa.Column('jurisdiction_text', sa.Text(), nullable=True),
        sa.Column('source_citation', sa.String(length=300), nullable=True),
        sa.Column('source_url', sa.String(length=300), nullable=False),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.Column('mapping_version', sa.String(length=40), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_committee_industry_mappings')),
    )
    op.create_index('ix_committee_industry_mappings_version_committee', 'committee_industry_mappings', ['mapping_version', 'committee_code'])


def downgrade() -> None:
    op.drop_index('ix_committee_industry_mappings_version_committee', table_name='committee_industry_mappings')
    op.drop_table('committee_industry_mappings')
