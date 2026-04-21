"""add compartida to hemeroteca

Revision ID: add_compartida_hemeroteca
Revises: 
Create Date: 2026-02-06 15:45:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_compartida_hemeroteca'
down_revision = None  # Update this if you know the previous migration ID
branch_labels = None
depends_on = None


def upgrade():
    # Add compartida column with default True
    op.add_column('hemerotecas', sa.Column('compartida', sa.Boolean(), nullable=False, server_default='1'))


def downgrade():
    # Remove compartida column
    op.drop_column('hemerotecas', 'compartida')
