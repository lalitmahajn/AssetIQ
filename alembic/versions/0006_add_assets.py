"""add_assets

Revision ID: 0006_assets
Revises: 0005_reasons
Create Date: 2026-01-12 12:30:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0006_assets'
down_revision = '0005_reasons'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('assets',
        sa.Column('id', sa.String(length=64), primary_key=True),
        sa.Column('site_code', sa.String(length=16), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('parent_id', sa.String(length=64), nullable=True),
        sa.Column('asset_type', sa.String(length=32), nullable=False, server_default="MACHINE"),
        sa.Column('description', sa.String(length=256), nullable=True),
        sa.Column('created_at_utc', sa.DateTime(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default="true")
    )
    op.create_index(op.f('ix_assets_site_code'), 'assets', ['site_code'], unique=False)
    op.create_index(op.f('ix_assets_parent_id'), 'assets', ['parent_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_assets_parent_id'), table_name='assets')
    op.drop_index(op.f('ix_assets_site_code'), table_name='assets')
    op.drop_table('assets')
