"""add official politician enrichment and committee assignments

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-07 13:00:00.000000

Additive only: new nullable columns and a new table. No existing row, id or trade is touched.
"""
from alembic import op
import sqlalchemy as sa


revision = '0006'
down_revision = '0005'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('politicians', schema=None) as batch_op:
        batch_op.add_column(sa.Column('bioguide_id', sa.String(length=10), nullable=True))
        batch_op.add_column(sa.Column('district', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('official_url', sa.String(length=300), nullable=True))
        batch_op.add_column(sa.Column('active', sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column('term_start_year', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('term_end_year', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('enriched_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('enrichment_source', sa.String(length=40), nullable=True))
        batch_op.add_column(sa.Column('enrichment_status', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('enrichment_note', sa.String(length=500), nullable=True))
        batch_op.add_column(sa.Column('enrichment_checked_at', sa.DateTime(), nullable=True))
        batch_op.create_unique_constraint(batch_op.f('uq_politicians_bioguide_id'), ['bioguide_id'])

    op.create_table(
        'committee_assignments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('politician_id', sa.Integer(), nullable=False),
        sa.Column('committee_name', sa.String(length=300), nullable=False),
        sa.Column('committee_code', sa.String(length=20), nullable=False),
        sa.Column('subcommittee_name', sa.String(length=300), nullable=True),
        sa.Column('subcommittee_code', sa.String(length=20), nullable=False),
        sa.Column('role', sa.String(length=60), nullable=False),
        sa.Column('chamber', sa.String(length=10), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=True),
        sa.Column('end_date', sa.Date(), nullable=True),
        sa.Column('source', sa.String(length=40), nullable=False),
        sa.Column('source_url', sa.String(length=300), nullable=True),
        sa.Column('fetched_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['politician_id'], ['politicians.id'], name=op.f('fk_committee_assignments_politician_id_politicians')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_committee_assignments')),
        sa.UniqueConstraint('politician_id', 'committee_code', 'subcommittee_code', 'source',
                            name=op.f('uq_committee_assignments_politician_id')),
    )
    op.create_index(op.f('ix_committee_assignments_politician_id'), 'committee_assignments', ['politician_id'])


def downgrade() -> None:
    op.drop_index(op.f('ix_committee_assignments_politician_id'), table_name='committee_assignments')
    op.drop_table('committee_assignments')
    with op.batch_alter_table('politicians', schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f('uq_politicians_bioguide_id'), type_='unique')
        for column in ('enrichment_checked_at', 'enrichment_note', 'enrichment_status', 'enrichment_source',
                       'enriched_at', 'term_end_year', 'term_start_year', 'active', 'official_url', 'district',
                       'bioguide_id'):
            batch_op.drop_column(column)
