from app import app
from extensions import db
from models import VectorLayer

with app.app_context():
    layers = VectorLayer.query.filter_by(visible=False).all()
    for l in layers:
        print(f"ID: {l.id}, Nombre: {l.nombre}, Invisible!")
