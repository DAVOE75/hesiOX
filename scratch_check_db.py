import psycopg2
try:
    conn = psycopg2.connect("dbname=hesiox user=hesiox password=hesiox host=localhost")
    cur = conn.cursor()
    cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'publicaciones';")
    columns = [row[0] for row in cur.fetchall()]
    print("Columns in publicaciones:", columns)
    
    missing = []
    for col in ['actos_totales', 'escenas_totales', 'reparto_total']:
        if col not in columns:
            missing.append(col)
            
    if missing:
        print("MISSING COLUMNS:", missing)
        print("Adding them now...")
        for col in missing:
            cur.execute(f"ALTER TABLE publicaciones ADD COLUMN {col} TEXT;")
        conn.commit()
        print("Columns added successfully!")
    else:
        print("All theatrical columns exist.")
except Exception as e:
    print("Error:", e)
