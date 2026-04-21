"""
Alembic migration: Añadir restricción de unicidad (proyecto_id, nombre) en publicaciones
"""
from alembic import op
import sqlalchemy as sa

# Alembic identifiers
revision = 'a1b2c3d4e5f6'
down_revision = None
branch_labels = None
depends_on = None
"""
Migración: Añadir restricción de unicidad (proyecto_id, nombre) en publicaciones
"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    # Elimina la restricción si ya existe (idempotente)
    try:
        op.drop_constraint('uq_publicacion_proyecto_nombre', 'publicaciones', type_='unique')
    except Exception:
        pass
    op.create_unique_constraint(
        'uq_publicacion_proyecto_nombre',
        'publicaciones',
        ['proyecto_id', 'nombre']
    )

def downgrade():
    op.drop_constraint('uq_publicacion_proyecto_nombre', 'publicaciones', type_='unique')
