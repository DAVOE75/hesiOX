from app import app
from extensions import db
from models import VectorLayer
import json

with app.app_context():
    layers = VectorLayer.query.all()
    for l in layers:
        geo = json.loads(l.geojson_data)
        features = geo.get('features', [])
        if features:
            coords = features[0]['geometry']['coordinates']
            # If it has more than 50 points, it might be an elevation profile
            if len(coords) > 50:
                print(f"ID: {l.id}, Nombre: {l.nombre}, Puntos: {len(coords)}")
