"""add the AI provider to the cached trade context explanations

Revision ID: 0017
Revises: 0016
Create Date: 2026-10-12 09:00:00.000000

Adds `provider` to trade_context_analysis and widens its uniqueness to (trade, context version, mapping version, prompt version, provider, model), so an
explanation from another provider is a separate row instead of replacing or being mistaken for an earlier one. Existing rows were all written by OpenAI and are
backfilled as 'openai'. No explanation text is changed; trade_context is untouched.
Downgrade removes explanations from other providers (generated text, recomputable) so the narrower uniqueness holds, then drops the column.
"""
from alembic import op
import sqlalchemy as sa


revision = '0017'
down_revision = '0016'
branch_labels = None
depends_on = None

OLD = ['trade_id', 'context_version', 'mapping_version', 'prompt_version', 'model']
NEW = ['trade_id', 'context_version', 'mapping_version', 'prompt_version', 'provider', 'model']
NAME = 'uq_trade_context_analysis_trade_id'


def upgrade() -> None:
    with op.batch_alter_table('trade_context_analysis') as batch:
        batch.add_column(sa.Column('provider', sa.String(length=20), nullable=False, server_default='openai'))
        batch.drop_constraint(NAME, type_='unique')
        batch.create_unique_constraint(NAME, NEW)


def downgrade() -> None:
    op.execute("DELETE FROM trade_context_analysis WHERE provider <> 'openai'")
    with op.batch_alter_table('trade_context_analysis') as batch:
        batch.drop_constraint(NAME, type_='unique')
        batch.create_unique_constraint(NAME, OLD)
        batch.drop_column('provider')
