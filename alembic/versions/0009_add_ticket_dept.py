"""add ticket dept

Revision ID: 0009_add_ticket_dept
Revises: 0008_add_asset_description
Create Date: 2026-01-16 12:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "0009_add_ticket_dept"
down_revision = "0008_add_asset_description"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("tickets", sa.Column("assigned_dept", sa.String(length=64), nullable=True))


def downgrade():
    op.drop_column("tickets", "assigned_dept")
