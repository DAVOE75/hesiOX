"""
Migración: Crear tabla vector_layers para capas vectoriales GIS
Fecha: 2026-03-06
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from extensions import db
from app import app

def migrate():
    """Crea la tabla vector_layers si no existe"""
    
    with app.app_context():
        # SQL para crear la tabla
        sql = """
        CREATE TABLE IF NOT EXISTS vector_layers (
            id SERIAL PRIMARY KEY,
            proyecto_id INTEGER NOT NULL REFERENCES proyectos(id) ON DELETE CASCADE,
            nombre VARCHAR(255) NOT NULL,
            descripcion TEXT,
            tipo_geometria VARCHAR(20) NOT NULL DEFAULT 'mixed',
            geojson_data TEXT NOT NULL DEFAULT '{"type":"FeatureCollection","features":[]}',
            color VARCHAR(20) DEFAULT '#ff9800',
            opacidad FLOAT DEFAULT 0.7,
            grosor_linea INTEGER DEFAULT 3,
            visible BOOLEAN DEFAULT TRUE,
            num_features INTEGER DEFAULT 0,
            area_total FLOAT,
            longitud_total FLOAT,
            estilo_personalizado TEXT,
            etiquetas_visibles BOOLEAN DEFAULT FALSE,
            snap_enabled BOOLEAN DEFAULT FALSE,
            creado_por INTEGER REFERENCES usuarios(id),
            modificado_por INTEGER REFERENCES usuarios(id),
            creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            modificado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            vinculado_noticias TEXT
        );
        
        -- Índices para optimizar consultas
        CREATE INDEX IF NOT EXISTS idx_vector_layers_proyecto ON vector_layers(proyecto_id);
        CREATE INDEX IF NOT EXISTS idx_vector_layers_visible ON vector_layers(visible);
        CREATE INDEX IF NOT EXISTS idx_vector_layers_tipo ON vector_layers(tipo_geometria);
        """
        
        try:
            db.session.execute(db.text(sql))
            db.session.commit()
            print("✅ Tabla 'vector_layers' creada exitosamente")
            print("✅ Índices creados correctamente")
            return True
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error al crear tabla: {e}")
            return False

if __name__ == '__main__':
    success = migrate()
    if success:
        print("\n🎉 Migración completada con éxito")
        print("📊 Sistema GIS vectorial listo para usar")
    else:
        print("\n⚠️  La migración falló. Revisa los errores arriba.")
