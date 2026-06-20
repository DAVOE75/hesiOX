from app import app
from extensions import db
from models import VectorLayer

with app.app_context():
    names = db.session.execute("SELECT id, nombre, proyecto_id FROM vector_layers ORDER BY id DESC").fetchall()
    for row in names:
        print(f"ID: {row[0]}, Nombre: {row[1]}, Proyecto: {row[2]}")
