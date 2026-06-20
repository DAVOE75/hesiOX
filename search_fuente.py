from app import app
from extensions import db
from models import VectorLayer

with app.app_context():
    layers = db.session.execute("SELECT id, nombre FROM vector_layers WHERE nombre ILIKE '%Fuente%'").fetchall()
    for row in layers:
        print(f"ID: {row[0]}, Nombre: {row[1]}")
