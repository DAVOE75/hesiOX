from app import app
from models import PasajeroSirio, Ciudad
from extensions import db

def fix():
    with app.app_context():
        # Encontrar los que están en el "cluster de Tarancón"
        pasajeros = PasajeroSirio.query.filter(PasajeroSirio.lat == 40.0, PasajeroSirio.lon == -3.0).all()
        print(f"Encontrados {len(pasajeros)} pasajeros en el cluster (40.0, -3.0)")
        
        fixed_count = 0
        unset_count = 0
        
        for p in pasajeros:
            # Intentar buscar el municipio en la tabla Ciudad
            if p.municipio:
                ciudad = Ciudad.query.filter(Ciudad.name.ilike(p.municipio)).first()
                if ciudad and ciudad.lat and ciudad.lon:
                    p.lat = ciudad.lat
                    p.lon = ciudad.lon
                    fixed_count += 1
                else:
                    # Si no hay ciudad, desvincular del centro de España
                    p.lat = None
                    p.lon = None
                    unset_count += 1
            else:
                p.lat = None
                p.lon = None
                unset_count += 1
        
        db.session.commit()
        print(f"Sincronización finalizada:")
        print(f"  Pasajeros reubicados correctamente: {fixed_count}")
        print(f"  Coordenadas eliminadas (sin municipio conocido): {unset_count}")

if __name__ == "__main__":
    fix()
