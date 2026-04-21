from app import app, db
from sqlalchemy import text
import os

with app.app_context():
    # 1. Limpiar específicamente ID 1020 si tiene imagen_scan inválida
    print("Checking ID 1020...")
    result = db.session.execute(text("SELECT id, imagen_scan FROM prensa WHERE id = 1020")).fetchone()
    if result:
        id, scan = result
        print(f"ID: {id}, SCAN: {scan}")
        # Si el scan es igual al ID (error común)
        if str(scan) == str(id):
            print(f"FIXING ID {id}: clearing scan '{scan}'")
            db.session.execute(text("UPDATE prensa SET imagen_scan = NULL WHERE id = 1020"))
            db.session.commit()
            print("FIXED ID 1020")
    else:
        print("ID 1020 Not found")

    # 2. Limpieza general de registros donde imagen_scan == id
    print("General cleanup: imagen_scan == id")
    result = db.session.execute(text("UPDATE prensa SET imagen_scan = NULL WHERE CAST(imagen_scan AS CHAR) = CAST(id AS CHAR)"))
    db.session.commit()
    print(f"General cleanup done. Rows affected: {result.rowcount}")

    # 3. Limpieza de archivos que no existen en disco
    print("Broad cleanup: files not on disk")
    all_with_scan = db.session.execute(text("SELECT id, imagen_scan FROM prensa WHERE imagen_scan IS NOT NULL")).fetchall()
    count = 0
    for row in all_with_scan:
        rid, rscan = row
        path = os.path.join('/opt/hesiox/static/uploads', rscan)
        if not os.path.exists(path):
            print(f"Broken file ref: ID {rid} -> {rscan}. Clearing.")
            db.session.execute(text("UPDATE prensa SET imagen_scan = NULL WHERE id = :id"), {"id": rid})
            count += 1
    
    if count > 0:
        db.session.commit()
        print(f"Broad cleanup finished. Cleared {count} references.")
    else:
        print("No more broken references found.")
