"""Merge heads

Revision ID: 9f53e7f22db9
Revises: 1a5085ed9759, 202603_add_semantic_embeddings
Create Date: 2026-03-16 18:02:42.816174

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9f53e7f22db9'
down_revision = ('1a5085ed9759', '202603_add_semantic_embeddings')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
