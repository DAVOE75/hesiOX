"""
Migración: Crear tablas para Gestión de Rutas e IA Atmosférica
Fecha: 2026-03-09
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from extensions import db
from app import app

def migrate():
    """Crea las tablas simulation_routes y simulation_logs si no existen"""
    
    with app.app_context():
        # SQL para crear las tablas
        sql = """
        -- 1. Tabla de Rutas
        CREATE TABLE IF NOT EXISTS simulation_routes (
            id SERIAL PRIMARY KEY,
            proyecto_id INTEGER NOT NULL REFERENCES proyectos(id) ON DELETE CASCADE,
            nombre VARCHAR(255) NOT NULL,
            descripcion TEXT,
            waypoints TEXT NOT NULL DEFAULT '[]',
            cronograma TEXT NOT NULL DEFAULT '[]',
            configuracion TEXT DEFAULT '{}',
            creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            modificado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- 2. Tabla de Logs de IA
        CREATE TABLE IF NOT EXISTS simulation_logs (
            id SERIAL PRIMARY KEY,
            route_id INTEGER NOT NULL REFERENCES simulation_routes(id) ON DELETE CASCADE,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            sim_time TIMESTAMP NOT NULL,
            lat FLOAT NOT NULL,
            lon FLOAT NOT NULL,
            weather_layer_id VARCHAR(100),
            analysis TEXT NOT NULL,
            modifier FLOAT DEFAULT 1.0
        );
        
        -- Índices
        CREATE INDEX IF NOT EXISTS idx_sim_route_proyecto ON simulation_routes(proyecto_id);
        CREATE INDEX IF NOT EXISTS idx_sim_log_route ON simulation_logs(route_id);
        CREATE INDEX IF NOT EXISTS idx_sim_log_time ON simulation_logs(sim_time);
        """
        
        try:
            db.session.execute(db.text(sql))
            db.session.commit()
            print("✅ Tablas de Simulación creadas exitosamente")
            print("✅ Índices creados correctamente")
            return True
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error al crear tablas: {e}")
            return False

if __name__ == '__main__':
    success = migrate()
    if success:
        print("\n🎉 Migración de Simulación completada con éxito")
    else:
        print("\n⚠️ La migración falló.")
