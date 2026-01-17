"""add asset description column

Revision ID: 0008_add_asset_description
Revises: 0007_add_hq_users
Create Date: 2026-01-15

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "0008_add_asset_description"
down_revision = "0007_add_hq_users"
branch_labels = None
depends_on = None


def upgrade():
    # Add description column to assets table (Plant DB)
    op.add_column("assets", sa.Column("description", sa.Text(), nullable=True))


def downgrade():
    op.drop_column("assets", "description")
