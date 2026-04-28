import sys
import os
sys.path.append('/opt/hesiox')
from app import app
from models import EdicionTipoRecurso, db

with app.app_context():
    tipos = db.session.query(EdicionTipoRecurso.tipo_recurso).distinct().all()
    print(f"Unique types in editions: {[t[0] for t in tipos]}")
    for t in [t[0] for t in tipos]:
        count = EdicionTipoRecurso.query.filter_by(tipo_recurso=t).count()
        print(f"  - {t}: {count} options")
