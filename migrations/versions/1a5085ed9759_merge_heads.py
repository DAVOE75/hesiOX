"""Merge heads

Revision ID: 1a5085ed9759
Revises: add_compartida_hemeroteca, add_en_titulo_en_contenido_lugarnoticia
Create Date: 2026-02-21 17:17:33.238172

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1a5085ed9759'
down_revision = ('add_compartida_hemeroteca', 'add_en_titulo_en_contenido_lugarnoticia')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
