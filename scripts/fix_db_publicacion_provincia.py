
import sys
import os

# Add parent directory to path so we can import app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db
from sqlalchemy import text

def add_provincia_column():
    """
    Script manual para añadir la columna 'provincia' a la tabla 'publicaciones'
    si no existe.
    """
    print("Iniciando parche de base de datos para Publicaciones...")
    
    with app.app_context():
        # Verificar si la columna existe en 'publicaciones'
        inspector = db.inspect(db.engine)
        columns = [c['name'] for c in inspector.get_columns('publicaciones')]
        
        if 'provincia' in columns:
            print("✅ La columna 'provincia' ya existe en la tabla 'publicaciones'.")
            return

        print("⚠️ La columna 'provincia' no existe en 'publicaciones'. Añadiéndola...")
        
        try:
            with db.engine.connect() as conn:
                conn.execute(text("ALTER TABLE publicaciones ADD COLUMN provincia TEXT;"))
                conn.commit()
                
            print("✅ Columna 'provincia' añadida a 'publicaciones' correctamente.")
            
        except Exception as e:
            print(f"❌ Error al añadir columna: {e}")
            try:
                print("Intentando método alternativo...")
                db.session.execute(text("ALTER TABLE publicaciones ADD COLUMN provincia TEXT"))
                db.session.commit()
                print("✅ Columna añadida (método alternativo).")
            except Exception as e2:
                print(f"❌ Falló método alternativo: {e2}")

if __name__ == "__main__":
    add_provincia_column()
