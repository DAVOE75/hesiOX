"""
Script para aplicar la migración: agregar campo descripcion_publicacion a prensa
Ejecutar: python migrations/run_add_descripcion_publicacion.py
"""

import sys
import os

# Agregar el directorio raíz al path para poder importar los módulos
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

from extensions import db
from app import app

def aplicar_migracion():
    """Aplica la migración para agregar el campo descripcion_publicacion"""
    with app.app_context():
        try:
            print("🔄 Iniciando migración: agregar descripcion_publicacion a prensa...")
            
            # Leer el archivo SQL
            sql_path = os.path.join(
                os.path.dirname(__file__), 
                'add_descripcion_publicacion_prensa.sql'
            )
            
            with open(sql_path, 'r', encoding='utf-8') as f:
                sql_content = f.read()
            
            # Separar las sentencias SQL (ignorando comentarios y líneas vacías)
            statements = []
            current_statement = []
            
            for line in sql_content.split('\n'):
                line = line.strip()
                # Ignorar comentarios y líneas vacías
                if not line or line.startswith('--'):
                    continue
                
                current_statement.append(line)
                
                # Si la línea termina con punto y coma, ejecutar la sentencia
                if line.endswith(';'):
                    statement = ' '.join(current_statement)
                    statements.append(statement)
                    current_statement = []
            
            # Ejecutar cada sentencia
            for i, statement in enumerate(statements, 1):
                if statement.strip():
                    print(f"  Ejecutando sentencia {i}...")
                    try:
                        db.session.execute(db.text(statement))
                    except Exception as e:
                        # Si el error es que la columna ya existe, continuar
                        if "already exists" in str(e).lower() or "duplicate column" in str(e).lower():
                            print(f"    ⚠️  La columna ya existe (esto es normal)")
                        else:
                            raise
            
            db.session.commit()
            print("✅ Migración completada exitosamente")
            print("\n📋 Verificando columna agregada...")
            
            # Verificar que la columna existe
            result = db.session.execute(db.text("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns 
                WHERE table_name = 'prensa' 
                AND column_name = 'descripcion_publicacion';
            """))
            
            print("\n🔍 Columna encontrada:")
            for row in result:
                print(f"   - {row[0]}: {row[1]} (nullable: {row[2]})")
            
            print("\n✨ ¡Listo! Ahora la descripción histórica de publicación se propagará correctamente.")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error aplicando migración: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    return True

if __name__ == "__main__":
    exito = aplicar_migracion()
    sys.exit(0 if exito else 1)
