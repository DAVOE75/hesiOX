import sys
import os
import json

# Añadir el directorio actual al path
sys.path.append(os.getcwd())

from app import app
from models import db, PasajeroSirio

with app.app_context():
    pasajero = PasajeroSirio.query.get(11)
    if not pasajero:
        print("No encontrado")
    else:
        # Convert to dict manually to be safe
        data = {c.name: str(getattr(pasajero, c.name)) for c in pasajero.__table__.columns}
        print(json.dumps(data, indent=2))
