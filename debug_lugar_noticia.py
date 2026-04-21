
import sys, os
sys.path.append('/opt/hesiox')
from app import app, db
from models import LugarNoticia

with app.app_context():
    try:
        # Get some records with type
        lugares = LugarNoticia.query.filter(LugarNoticia.tipo_lugar != 'unknown').limit(20).all()
        print(f"Total lugares con tipo != 'unknown' (limit 20): {len(lugares)}")
        for l in lugares:
            print(f"- {l.nombre}: tipo_lugar='{l.tipo_lugar}'")
            
        # Get count per tipo_lugar
        from sqlalchemy import func
        counts = db.session.query(LugarNoticia.tipo_lugar, func.count(LugarNoticia.id)).group_by(LugarNoticia.tipo_lugar).all()
        print("\nConteos por tipo_lugar:")
        for t, c in counts:
            print(f"- {t}: {c}")
            
    except Exception as e:
        print("Error:", e)
