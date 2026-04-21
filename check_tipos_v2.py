from app import app
from extensions import db
from models import TipoUbicacion

def diagnostic():
    with app.app_context():
        print("Checking active location types...")
        tipos = TipoUbicacion.query.filter_by(activo=True).all()
        print(f"Found {len(tipos)} active types.")
        for t in tipos:
            print(f" - [{t.codigo}] {t.nombre} (Category: {t.categoria})")
        
        print("\nChecking specifically for 'Puerto' or '410'...")
        puerto = TipoUbicacion.query.filter((TipoUbicacion.nombre == 'Puerto') | (TipoUbicacion.codigo == '410')).all()
        for p in puerto:
            print(f" - [{p.codigo}] {p.nombre} (Active: {p.activo})")

if __name__ == "__main__":
    diagnostic()
