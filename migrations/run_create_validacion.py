"""
Script para crear la tabla validacion_duplicados
"""
import sys
import os

# Añadir directorio raíz al path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app, db
from models import ValidacionDuplicados

def migrar():
    with app.app_context():
        try:
            print("📊 Creando tabla validacion_duplicados...")
            ValidacionDuplicados.__table__.create(db.engine)
            print("✅ Tabla creada exitosamente")
        except Exception as e:
            if "already exists" in str(e):
                print("⚠️ La tabla ya existe")
            else:
                print(f"❌ Error: {e}")
                raise

if __name__ == "__main__":
    migrar()
