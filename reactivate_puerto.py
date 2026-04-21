
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv('/opt/hesiox/.env')

try:
    conn_str = "postgresql://hesiox_user:garciap1975@localhost/hesiox"
    conn = psycopg2.connect(conn_str)
    cur = conn.cursor()
    
    # Check if 'Puerto' exists (active or inactive)
    cur.execute("SELECT id, nombre, activo FROM tipo_ubicacion WHERE codigo = 'puerto' OR nombre ILIKE 'Puerto';")
    row = cur.fetchone()
    
    if row:
        tipo_id, nombre, activo = row
        if not activo:
            print(f"Reactivating type: {nombre} (ID: {tipo_id})")
            cur.execute("UPDATE tipo_ubicacion SET activo = TRUE WHERE id = %s;", (tipo_id,))
            conn.commit()
            print("Successfully reactivated.")
        else:
            print(f"Type '{nombre}' is already active.")
    else:
        print("Type 'Puerto' not found. Creating it...")
        # Get next order if possible, or use a default
        cur.execute("SELECT MAX(orden) FROM tipo_ubicacion;")
        max_orden = cur.fetchone()[0] or 400
        new_orden = max_orden + 1
        
        cur.execute("""
            INSERT INTO tipo_ubicacion (codigo, nombre, categoria, icono, orden, activo, fecha_creacion)
            VALUES ('puerto', 'Puerto', 'Hidrografía', 'fa-solid fa-anchor', %s, TRUE, NOW());
        """, (new_orden,))
        conn.commit()
        print(f"Created 'Puerto' with order {new_orden}.")
        
    cur.close()
    conn.close()
except Exception as e:
    print(f"Error: {e}")
