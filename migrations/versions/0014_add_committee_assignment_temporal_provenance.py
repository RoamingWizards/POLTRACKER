"""add temporal provenance to committee assignments

Revision ID: 0014
Revises: 0013
Create Date: 2026-10-09 09:00:00.000000

Additive columns on committee_assignments (congress_number, temporal_precision, source_type, verified_at, verified_through, history_complete). Existing rows
are House Clerk snapshot rows, so they are marked current_snapshot; nothing else about them changes. The uniqueness rule now includes start_date so one
member can have two separate stints on the same committee.
"""
from alembic import op
import sqlalchemy as sa


revision = '0014'
down_revision = '0013'
branch_labels = None
depends_on = None

OLD = ('politician_id', 'committee_code', 'subcommittee_code', 'source')


def upgrade() -> None:
    with op.batch_alter_table('committee_assignments', schema=None) as batch_op:
        batch_op.add_column(sa.Column('congress_number', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('temporal_precision', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('source_type', sa.String(length=40), nullable=True))
        batch_op.add_column(sa.Column('verified_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('verified_through', sa.Date(), nullable=True))
        batch_op.add_column(sa.Column('history_complete', sa.Boolean(), nullable=True))
        batch_op.drop_constraint('uq_committee_assignments_politician_id', type_='unique')
        batch_op.create_unique_constraint('uq_committee_assignments_politician_id', [*OLD, 'start_date'])
    op.execute("update committee_assignments set temporal_precision = 'current_snapshot', source_type = 'house_clerk_member_data' where source = 'house.clerk'")


def downgrade() -> None:
    # Rows that carry resolution-derived history are removed first: the old uniqueness rule cannot hold two stints, and that history is recomputable.
    op.execute("delete from committee_assignments where source = 'house.resolutions'")
    with op.batch_alter_table('committee_assignments', schema=None) as batch_op:
        batch_op.drop_constraint('uq_committee_assignments_politician_id', type_='unique')
        batch_op.create_unique_constraint('uq_committee_assignments_politician_id', list(OLD))
        for name in ('history_complete', 'verified_through', 'verified_at', 'source_type', 'temporal_precision', 'congress_number'):
            batch_op.drop_column(name)
