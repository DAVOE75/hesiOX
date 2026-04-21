"""
Alembic migration: Añadir campos en_titulo y en_contenido a la tabla lugar_noticia
"""
from alembic import op
import sqlalchemy as sa

revision = 'add_en_titulo_en_contenido_lugarnoticia'
down_revision = '0e707b8f98d5'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('lugar_noticia', sa.Column('en_titulo', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column('lugar_noticia', sa.Column('en_contenido', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.alter_column('lugar_noticia', 'en_titulo', server_default=None)
    op.alter_column('lugar_noticia', 'en_contenido', server_default=None)

def downgrade():
    op.drop_column('lugar_noticia', 'en_titulo')
    op.drop_column('lugar_noticia', 'en_contenido')
