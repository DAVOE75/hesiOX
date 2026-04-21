"""
Script para agregar columna red_tipos a la tabla proyectos
"""
import psycopg2
import os

# Leer configuración de variables de entorno o usar defaults
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:PASSWORD@localhost:5432/bibliografia_sirio")

# Parsear URL de conexión
# Formato: postgresql://usuario:contraseña@host:puerto/database
def parse_db_url(url):
    # Remover postgresql://
    url = url.replace("postgresql://", "")
    
    # Separar credenciales y host
    creds, resto = url.split("@")
    usuario, password = creds.split(":")
    
    # Separar host y database
    host_puerto, database = resto.split("/")
    host, puerto = host_puerto.split(":") if ":" in host_puerto else (host_porto, "5432")
    
    return {
        'dbname': database,
        'user': usuario,
        'password': password,
        'host': host,
        'port': int(puerto)
    }

DB_CONFIG = parse_db_url(DATABASE_URL)

def migrar():
    conn = None
    try:
        # Conectar a la base de datos
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        print("✅ Conectado a la base de datos")
        
        # Agregar columna red_tipos
        default_config = '{"tipo1": {"nombre": "Principales", "color": "#ff9800", "forma": "dot", "entidades": []}, "tipo2": {"nombre": "Secundarios", "color": "#03a9f4", "forma": "dot", "entidades": []}, "tipo3": {"nombre": "Lugares", "color": "#4a7c2f", "forma": "square", "entidades": []}}'
        
        cursor.execute("""
            ALTER TABLE proyectos 
            ADD COLUMN IF NOT EXISTS red_tipos TEXT 
            DEFAULT %s;
        """, (default_config,))
        
        print("✅ Columna red_tipos agregada")
        
        # Actualizar proyectos existentes con NULL
        cursor.execute("""
            UPDATE proyectos 
            SET red_tipos = %s
            WHERE red_tipos IS NULL;
        """, (default_config,))
        
        filas_actualizadas = cursor.rowcount
        print(f"✅ {filas_actualizadas} proyectos actualizados con configuración por defecto")
        
        # Verificar
        cursor.execute("SELECT id, nombre, red_tipos FROM proyectos;")
        proyectos = cursor.fetchall()
        
        print(f"\n📊 Estado de proyectos ({len(proyectos)} total):")
        for pid, nombre, config in proyectos:
            estado = "✓ Configurado" if config else "✗ Sin configurar"
            print(f"  - [{pid}] {nombre}: {estado}")
        
        # Confirmar cambios
        conn.commit()
        print("\n✅ Migración completada exitosamente")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error durante la migración: {e}")
        if conn:
            conn.rollback()
        raise

if __name__ == "__main__":
    migrar()
