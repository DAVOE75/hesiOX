"""
Alembic migration: Eliminar restricción única antigua sobre nombre en publicaciones
"""
from alembic import op
import sqlalchemy as sa

# Alembic identifiers
revision = 'b2c3d4e5f6a7'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None
"""
Migración: Eliminar restricción única antigua sobre nombre en publicaciones
"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    # Elimina la restricción única antigua (puede llamarse publicaciones_nombre_key)
    op.drop_constraint('publicaciones_nombre_key', 'publicaciones', type_='unique')
    # No hace falta crear la nueva, ya existe por migración anterior

def downgrade():
    # Vuelve a crear la restricción única antigua (solo si es necesario revertir)
    op.create_unique_constraint('publicaciones_nombre_key', 'publicaciones', ['nombre'])
