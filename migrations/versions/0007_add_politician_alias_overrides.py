"""add reviewed politician alias overrides

Revision ID: 0007
Revises: 0006
Create Date: 2026-10-07 14:00:00.000000

Additive only: one nullable politicians column and one new (empty) table.
"""
from alembic import op
import sqlalchemy as sa


revision = '0007'
down_revision = '0006'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('politicians', schema=None) as batch_op:
        batch_op.add_column(sa.Column('enrichment_method', sa.String(length=40), nullable=True))

    op.create_table(
        'politician_alias_overrides',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('politician_id', sa.Integer(), nullable=False),
        sa.Column('bioguide_id', sa.String(length=10), nullable=False),
        sa.Column('reason', sa.String(length=500), nullable=False),
        sa.Column('source', sa.String(length=200), nullable=False),
        sa.Column('reviewed_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['politician_id'], ['politicians.id'], name=op.f('fk_politician_alias_overrides_politician_id_politicians')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_politician_alias_overrides')),
        sa.UniqueConstraint('politician_id', name=op.f('uq_politician_alias_overrides_politician_id')),
        sa.UniqueConstraint('bioguide_id', name=op.f('uq_politician_alias_overrides_bioguide_id')),
    )


def downgrade() -> None:
    op.drop_table('politician_alias_overrides')
    with op.batch_alter_table('politicians', schema=None) as batch_op:
        batch_op.drop_column('enrichment_method')
