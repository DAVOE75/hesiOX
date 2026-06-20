from app import app
from extensions import db
from models import Proyecto, VectorLayer

with app.app_context():
    proyectos = Proyecto.query.all()
    for p in proyectos:
        layers = VectorLayer.query.filter_by(proyecto_id=p.id).all()
        print(f"Proyecto {p.id}: {p.nombre} ({len(layers)} capas)")
        for l in layers:
            print(f"  - ID {l.id}: {l.nombre}")
