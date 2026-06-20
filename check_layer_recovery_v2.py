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
        # Search specifically for ID 89 if it exists
        l89 = db.session.get(VectorLayer, 89)
        if l89:
            print(f"Capa ID 89 encontrada: {l89.nombre}")
        else:
            print("Capa ID 89 no existe.")

    # List all layers in project 1 (usually the default)
    print("\nCapas en proyecto 1:")
    p1_layers = VectorLayer.query.filter_by(proyecto_id=1).all()
    for l in p1_layers:
        print(f"ID: {l.id}, Nombre: {l.nombre}")
