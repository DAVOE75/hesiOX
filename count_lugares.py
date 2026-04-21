from app import app
from models import LugarNoticia
from extensions import db

with app.app_context():
    total = LugarNoticia.query.count()
    borrados = LugarNoticia.query.filter_by(borrado=True).count()
    print(f"Total: {total}")
    print(f"Borrados: {borrados}")
