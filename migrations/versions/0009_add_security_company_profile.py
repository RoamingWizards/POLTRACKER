"""add company profile columns to securities

Revision ID: 0009
Revises: 0008
Create Date: 2026-10-07 18:00:00.000000

Additive only: twelve nullable columns on securities. No existing column, row, id or relationship changes.
"""
from alembic import op
import sqlalchemy as sa


revision = '0009'
down_revision = '0008'
branch_labels = None
depends_on = None

COLUMNS = [
    ('company_name', sa.String(length=300)),
    ('cik', sa.String(length=10)),
    ('sic_code', sa.String(length=4)),
    ('industry', sa.String(length=200)),
    ('sector', sa.String(length=100)),
    ('exchange', sa.String(length=40)),
    ('profile_source', sa.String(length=40)),
    ('profile_source_url', sa.String(length=300)),
    ('profile_status', sa.String(length=20)),
    ('profile_note', sa.String(length=300)),
    ('profile_checked_at', sa.DateTime()),
    ('profile_updated_at', sa.DateTime()),
]


def upgrade() -> None:
    with op.batch_alter_table('securities', schema=None) as batch_op:
        for name, type_ in COLUMNS:
            batch_op.add_column(sa.Column(name, type_, nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('securities', schema=None) as batch_op:
        for name, _ in reversed(COLUMNS):
            batch_op.drop_column(name)
