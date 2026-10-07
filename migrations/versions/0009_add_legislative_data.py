"""add legislative data tables (bills, subjects, committees, sponsor links, actions, hearings)

Revision ID: 0009
Revises: 0008
Create Date: 2026-10-07 17:00:00.000000

Additive only: seven new, empty tables. No existing table is altered.
"""
from alembic import op
import sqlalchemy as sa


revision = '0009'
down_revision = '0008'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'legislation',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('congress', sa.Integer(), nullable=False),
        sa.Column('bill_type', sa.String(length=10), nullable=False),
        sa.Column('bill_number', sa.Integer(), nullable=False),
        sa.Column('title', sa.Text(), nullable=True),
        sa.Column('origin_chamber', sa.String(length=20), nullable=True),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('summary_date', sa.Date(), nullable=True),
        sa.Column('introduced_date', sa.Date(), nullable=True),
        sa.Column('latest_action_date', sa.Date(), nullable=True),
        sa.Column('latest_action_text', sa.Text(), nullable=True),
        sa.Column('policy_area', sa.String(length=200), nullable=True),
        sa.Column('sponsor_bioguide_id', sa.String(length=10), nullable=True),
        sa.Column('sponsor_name', sa.String(length=200), nullable=True),
        sa.Column('cosponsor_count', sa.Integer(), nullable=True),
        sa.Column('source_url', sa.String(length=300), nullable=True),
        sa.Column('api_update_date', sa.Date(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_legislation')),
        sa.UniqueConstraint('congress', 'bill_type', 'bill_number', name=op.f('uq_legislation_congress')),
    )
    op.create_index('ix_legislation_latest_action_date', 'legislation', ['latest_action_date'])

    op.create_table(
        'legislation_subjects',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('legislation_id', sa.Integer(), nullable=False),
        sa.Column('subject', sa.String(length=300), nullable=False),
        sa.ForeignKeyConstraint(['legislation_id'], ['legislation.id'], name=op.f('fk_legislation_subjects_legislation_id_legislation')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_legislation_subjects')),
        sa.UniqueConstraint('legislation_id', 'subject', name=op.f('uq_legislation_subjects_legislation_id')),
    )
    op.create_table(
        'legislation_committees',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('legislation_id', sa.Integer(), nullable=False),
        sa.Column('committee_code', sa.String(length=20), nullable=False),
        sa.Column('committee_name', sa.String(length=300), nullable=False),
        sa.Column('chamber', sa.String(length=20), nullable=True),
        sa.ForeignKeyConstraint(['legislation_id'], ['legislation.id'], name=op.f('fk_legislation_committees_legislation_id_legislation')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_legislation_committees')),
        sa.UniqueConstraint('legislation_id', 'committee_code', name=op.f('uq_legislation_committees_legislation_id')),
    )
    op.create_table(
        'politician_legislation',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('politician_id', sa.Integer(), nullable=False),
        sa.Column('legislation_id', sa.Integer(), nullable=False),
        sa.Column('relationship', sa.String(length=20), nullable=False),
        sa.Column('sponsorship_date', sa.Date(), nullable=True),
        sa.Column('is_original', sa.Boolean(), nullable=True),
        sa.Column('withdrawn_date', sa.Date(), nullable=True),
        sa.ForeignKeyConstraint(['legislation_id'], ['legislation.id'], name=op.f('fk_politician_legislation_legislation_id_legislation')),
        sa.ForeignKeyConstraint(['politician_id'], ['politicians.id'], name=op.f('fk_politician_legislation_politician_id_politicians')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_politician_legislation')),
        sa.UniqueConstraint('politician_id', 'legislation_id', 'relationship', name=op.f('uq_politician_legislation_politician_id')),
    )
    op.create_index('ix_politician_legislation_legislation_id', 'politician_legislation', ['legislation_id'])
    op.create_table(
        'bill_actions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('legislation_id', sa.Integer(), nullable=False),
        sa.Column('action_date', sa.Date(), nullable=False),
        sa.Column('action_text', sa.Text(), nullable=False),
        sa.Column('action_code', sa.String(length=20), nullable=True),
        sa.Column('action_type', sa.String(length=60), nullable=True),
        sa.Column('action_key', sa.String(length=40), nullable=False),
        sa.ForeignKeyConstraint(['legislation_id'], ['legislation.id'], name=op.f('fk_bill_actions_legislation_id_legislation')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_bill_actions')),
        sa.UniqueConstraint('legislation_id', 'action_key', name=op.f('uq_bill_actions_legislation_id')),
    )
    op.create_index('ix_bill_actions_legislation_id_action_date', 'bill_actions', ['legislation_id', 'action_date'])
    op.create_table(
        'hearings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('congress', sa.Integer(), nullable=False),
        sa.Column('chamber', sa.String(length=20), nullable=False),
        sa.Column('jacket_number', sa.Integer(), nullable=False),
        sa.Column('event_id', sa.String(length=40), nullable=True),
        sa.Column('title', sa.Text(), nullable=True),
        sa.Column('citation', sa.String(length=60), nullable=True),
        sa.Column('hearing_date', sa.Date(), nullable=True),
        sa.Column('hearing_end_date', sa.Date(), nullable=True),
        sa.Column('source_url', sa.String(length=300), nullable=True),
        sa.Column('api_update_date', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_hearings')),
        sa.UniqueConstraint('congress', 'chamber', 'jacket_number', name=op.f('uq_hearings_congress')),
    )
    op.create_index('ix_hearings_hearing_date', 'hearings', ['hearing_date'])
    op.create_table(
        'hearing_committees',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('hearing_id', sa.Integer(), nullable=False),
        sa.Column('committee_code', sa.String(length=20), nullable=False),
        sa.Column('committee_name', sa.String(length=300), nullable=False),
        sa.ForeignKeyConstraint(['hearing_id'], ['hearings.id'], name=op.f('fk_hearing_committees_hearing_id_hearings')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_hearing_committees')),
        sa.UniqueConstraint('hearing_id', 'committee_code', name=op.f('uq_hearing_committees_hearing_id')),
    )


def downgrade() -> None:
    op.drop_table('hearing_committees')
    op.drop_index('ix_hearings_hearing_date', table_name='hearings')
    op.drop_table('hearings')
    op.drop_index('ix_bill_actions_legislation_id_action_date', table_name='bill_actions')
    op.drop_table('bill_actions')
    op.drop_index('ix_politician_legislation_legislation_id', table_name='politician_legislation')
    op.drop_table('politician_legislation')
    op.drop_table('legislation_committees')
    op.drop_table('legislation_subjects')
    op.drop_index('ix_legislation_latest_action_date', table_name='legislation')
    op.drop_table('legislation')
