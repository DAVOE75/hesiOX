import sys
import os
sys.path.append('/opt/hesiox')
from app import app
from models import EdicionTipoRecurso, db

with app.app_context():
    ediciones = EdicionTipoRecurso.query.all()
    print(f"Total Ediciones: {len(ediciones)}")
    for e in ediciones:
        print(f"  - {e.tipo_recurso}: {e.text} ({e.value})")
