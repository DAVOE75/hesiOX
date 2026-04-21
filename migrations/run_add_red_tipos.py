"""
Script para agregar columna red_tipos usando Flask-SQLAlchemy
"""
import sys
sys.path.insert(0, '.')

from app import app, db

def migrar():
    with app.app_context():
        try:
            # Ejecutar ALTER TABLE usando SQLAlchemy
            default_config = '{"tipo1": {"nombre": "Principales", "color": "#ff9800", "forma": "dot", "entidades": []}, "tipo2": {"nombre": "Secundarios", "color": "#03a9f4", "forma": "dot", "entidades": []}, "tipo3": {"nombre": "Lugares", "color": "#4a7c2f", "forma": "square", "entidades": []}}'
            
            print("📊 Agregando columna red_tipos a tabla proyectos...")
            
            # Agregar columna
            db.session.execute(db.text(f"""
                ALTER TABLE proyectos 
                ADD COLUMN IF NOT EXISTS red_tipos TEXT 
                DEFAULT :config;
            """), {"config": default_config})
            
            print("✅ Columna agregada")
            
            # Actualizar proyectos existentes
            result = db.session.execute(db.text("""
                UPDATE proyectos 
                SET red_tipos = :config
                WHERE red_tipos IS NULL;
            """), {"config": default_config})
            
            print(f"✅ {result.rowcount} proyectos actualizados")
            
            # Confirmar
            db.session.commit()
            
            # Verificar
            proyectos = db.session.execute(db.text("SELECT id, nombre FROM proyectos;")).fetchall()
            print(f"\n📋 Proyectos en la base de datos ({len(proyectos)} total):")
            for pid, nombre in proyectos:
                print(f"  - [{pid}] {nombre}")
            
            print("\n✅ Migración completada exitosamente")
            print("🔄 Ahora puedes reiniciar Flask: flask run")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            db.session.rollback()
            raise

if __name__ == "__main__":
    migrar()
