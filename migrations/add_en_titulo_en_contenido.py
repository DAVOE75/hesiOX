"""
Script de migración para añadir los campos en_titulo y en_contenido a la tabla lugar_noticia
"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    op.add_column('lugar_noticia', sa.Column('en_titulo', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column('lugar_noticia', sa.Column('en_contenido', sa.Boolean(), nullable=False, server_default=sa.false()))

def downgrade():
    op.drop_column('lugar_noticia', 'en_titulo')
    op.drop_column('lugar_noticia', 'en_contenido')
