from extensions import db
from app import app
from models import Prensa

with app.app_context():
    raw_temas = db.session.query(Prensa.temas).filter(Prensa.temas.isnot(None)).all()
    print(f"Raw temas count: {len(raw_temas)}")
    temas_set = set()
    for (t_str,) in raw_temas:
        if t_str:
            for t in t_str.split(','):
                clean_t = t.strip()
                if clean_t:
                    temas_set.add(clean_t)
    temas = sorted(temas_set)
    print(f"Unique temas: {temas}")
