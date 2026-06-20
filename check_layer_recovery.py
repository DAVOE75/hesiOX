from app import app
from extensions import db
from models import VectorLayer
from sqlalchemy import text

with app.app_context():
    layers = VectorLayer.query.filter(VectorLayer.nombre.ilike('%Fuente Roja%')).all()
    if layers:
        print(f"Capas encontradas ({len(layers)}):")
        for l in layers:
            print(f"ID: {l.id}, Nombre: {l.nombre}, Proyecto: {l.proyecto_id}")
    else:
        print("No se encontraron capas con ese nombre en la base de datos.")
        
    # También buscar en todas las capas para ver si hay algo similar
    all_names = db.session.execute(text("SELECT id, nombre FROM vector_layers ORDER BY id DESC LIMIT 20")).fetchall()
    print("\nÚltimas 20 capas en la DB:")
    for row in all_names:
        print(f"ID: {row[0]}, Nombre: {row[1]}")
