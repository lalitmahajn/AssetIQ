"""add_reason_suggestions

Revision ID: 0005_reasons
Revises: 0004_phase3_insights
Create Date: 2026-01-12 11:30:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column
from sqlalchemy import String, Integer, Boolean

# revision identifiers, used by Alembic.
revision = '0005_reasons'
down_revision = '0004_phase3_insights'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # 1. Create table
    op.create_table('reason_suggestions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('site_code', sa.String(length=16), nullable=False),
        sa.Column('text', sa.String(length=256), nullable=False),
        sa.Column('category', sa.String(length=64), nullable=False, server_default="Other"),
        sa.Column('usage_count', sa.Integer(), nullable=False, server_default="0"),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default="true"),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_reason_suggestions_site_code'), 'reason_suggestions', ['site_code'], unique=False)

    # 2. Seed Data
    reason_table = table('reason_suggestions',
        column('site_code', String),
        column('text', String),
        column('category', String),
        column('usage_count', Integer),
        column('is_active', Boolean)
    )

    op.bulk_insert(reason_table, [
        {'site_code': 'P01', 'text': 'Jam at sensor A', 'category': 'Mechanical', 'usage_count': 0, 'is_active': True},
        {'site_code': 'P01', 'text': 'Motor Overheat', 'category': 'Mechanical', 'usage_count': 0, 'is_active': True},
        {'site_code': 'P01', 'text': 'Belt Broken', 'category': 'Mechanical', 'usage_count': 0, 'is_active': True},
        {'site_code': 'P01', 'text': 'Sensor Failure', 'category': 'Electrical', 'usage_count': 0, 'is_active': True},
        {'site_code': 'P01', 'text': 'Power Loss', 'category': 'Electrical', 'usage_count': 0, 'is_active': True},
        {'site_code': 'P01', 'text': 'No Material', 'category': 'Operational', 'usage_count': 0, 'is_active': True},
        {'site_code': 'P01', 'text': 'Operator Break', 'category': 'Operational', 'usage_count': 0, 'is_active': True},
        {'site_code': 'P01', 'text': 'Cleaning', 'category': 'Operational', 'usage_count': 0, 'is_active': True},
        # Add for P02 as well per user request to handle multi-plant
        {'site_code': 'P02', 'text': 'Jam at sensor A', 'category': 'Mechanical', 'usage_count': 0, 'is_active': True},
        {'site_code': 'P02', 'text': 'Motor Overheat', 'category': 'Mechanical', 'usage_count': 0, 'is_active': True},
        {'site_code': 'P02', 'text': 'No Material', 'category': 'Operational', 'usage_count': 0, 'is_active': True},
    ])

def downgrade() -> None:
    op.drop_index(op.f('ix_reason_suggestions_site_code'), table_name='reason_suggestions')
    op.drop_table('reason_suggestions')
