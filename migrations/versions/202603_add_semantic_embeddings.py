"""
Añade columnas para embeddings semánticos

Revision ID: 202603_add_semantic_embeddings
Revises: add_en_titulo_en_contenido_lugarnoticia
Create Date: 2026-03-06 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '202603_add_semantic_embeddings'
down_revision = 'add_en_titulo_en_contenido_lugarnoticia'
branch_labels = None
depends_on = None


def upgrade():
    # Añadir columnas para embeddings semánticos
    op.add_column('prensa', sa.Column('embedding_vector', sa.JSON(), nullable=True))
    op.add_column('prensa', sa.Column('embedding_model', sa.String(length=100), nullable=True))
    op.add_column('prensa', sa.Column('embedding_generado_en', sa.DateTime(), nullable=True))
    
    # Crear índice para búsquedas por modelo
    op.create_index('idx_prensa_embedding_model', 'prensa', ['embedding_model'], unique=False)


def downgrade():
    # Eliminar índice
    op.drop_index('idx_prensa_embedding_model', table_name='prensa')
    
    # Eliminar columnas
    op.drop_column('prensa', 'embedding_generado_en')
    op.drop_column('prensa', 'embedding_model')
    op.drop_column('prensa', 'embedding_vector')
