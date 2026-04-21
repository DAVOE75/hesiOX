from extensions import db
from app import app
from models import Prensa
from sqlalchemy import or_
from datetime import datetime
import sys

# Initialize Flask app to get DB context
# app = create_app()

with app.app_context():
    print("--- DEBUGGING DATE FILTER ROUND 4 (1882 Issue) ---")

    # 1. Search for 1882 dates in DB to confirm format
    print("\n1. Buscando registros de 1882 en DB:")
    samples_1882 = Prensa.query.filter(Prensa.fecha_original.ilike("%1882%")).limit(10).all()
    for s in samples_1882:
         print(f"   ID: {s.id} | Fecha Original en DB: '{s.fecha_original}'")

    # 2. Test Logic with '13/05/1882' (User input)
    test_input = "13/05/1882"
    print(f"\n2. Probando filtro con input usuario: '{test_input}'")
    
    # --- LOGIC COPY FROM routes/noticias.py ---
    v = test_input.strip()
    formatos = {v}
    dt = None
    try:
        # NOTE: Logic copied from current routes/noticias.py
        if "-" in v:
             parts = v.split('-')
             if len(parts) == 3:
                  dt = datetime(int(parts[0]), int(parts[1]), int(parts[2]))
        elif "/" in v:
             parts = v.split('/')
             if len(parts) == 3:
                  dt = datetime(int(parts[2]), int(parts[1]), int(parts[0]))
        
        if dt:
            y, m, d = dt.year, dt.month, dt.day
            formatos.add(f"{y}-{m:02d}-{d:02d}")  # 2026-02-02
            formatos.add(f"{y}-{m}-{d}")          # 2026-2-2
            formatos.add(f"{d:02d}/{m:02d}/{y}")  # 02/02/2026
            formatos.add(f"{d}/{m}/{y}")          # 2/2/2026
            formatos.add(f"{d:02d}/{m}/{y}")      # 02/2/2026
            formatos.add(f"{d}/{m:02d}/{y}")      # 2/02/2026
             
            print(f"   [DEBUG] Variantes generadas: {formatos}")

    except Exception as e:
        print(f"   [ERROR] Error en conversión: {e}")

    # Query simulation
    query = Prensa.query
    
    # COPYING LOGIC EXACTLY FROM routes/noticias.py
    col_limpia = db.func.lower(db.func.trim(Prensa.fecha_original))
    condiciones = [col_limpia == f.strip().lower() for f in formatos]
    condiciones.extend([Prensa.fecha_original.ilike(f"%{f}%") for f in formatos])

    query = query.filter(or_(*condiciones))
    
    # Debug Query SQL
    # print("[SQL] " + str(query.statement.compile(compile_kwargs={"literal_binds": True})))
    
    count = query.count()
    print(f"   [RESULT] Registros encontrados: {count}")
    if count > 0:
        for s in query.limit(3).all():
             print(f"   MATCH: {s.id} - {s.fecha_original}")
    else:
        print("   NO MATCH FOUND.")
