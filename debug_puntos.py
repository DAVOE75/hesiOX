from app import app
from models import SirioPuntoInteractivo

with app.app_context():
    puntos = SirioPuntoInteractivo.query.all()
    for p in puntos:
        print(f"ID: {p.id}, Nombre: {p.nombre}")
        print(f"  x: {p.x}, y: {p.y}")
        print(f"  coordenadas (type: {type(p.coordenadas)}): {p.coordenadas}")
        print("-" * 20)
