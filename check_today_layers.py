from app import app
from extensions import db
from models import VectorLayer
from datetime import datetime, date

with app.app_context():
    today = date.today()
    layers = VectorLayer.query.all()
    print(f"Total capas: {len(layers)}")
    for l in layers:
        # Check if today is in the names or if there's something suspicious
        if "Fuente Roja" in l.nombre or (l.id >= 80):
             print(f"ID: {l.id}, Nombre: {l.nombre}, Proyecto: {l.proyecto_id}")
