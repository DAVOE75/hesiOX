
import os
from app import app
from models import LugarNoticia
from sqlalchemy import text

with app.app_context():
    print("Checking for names with single quotes...")
    problematic = LugarNoticia.query.filter(LugarNoticia.nombre.like("%'%")).limit(20).all()
    if problematic:
        print(f"Found {len(problematic)} problematic names:")
        for p in problematic:
            print(f"  - {p.nombre}")
    else:
        print("No names with single quotes found.")

    print("\nChecking for names with other special characters...")
    other = LugarNoticia.query.filter(LugarNoticia.nombre.op('~')('[^a-zA-Z0-9 áéíóúÁÉÍÓÚñÑüÜ(),.-]')).limit(10).all()
    if other:
        print(f"Found {len(other)} names with other special characters:")
        for p in other:
            print(f"  - {p.nombre}")
    else:
        print("No names with other special characters found.")
