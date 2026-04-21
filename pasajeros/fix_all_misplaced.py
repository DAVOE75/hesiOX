from app import app
from models import PasajeroSirio, Ciudad
from extensions import db
import unicodedata

def normalize(s):
    if not s: return ""
    return "".join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn').lower().strip()

def fix():
    with app.app_context():
        # 1. Definir los "centros de clusters" detectados
        clusters = [
            (40.4190696, -3.6949281), # Madrid (Sol)
            (37.3860715, -6.0106481), # Sevilla
            (43.2627, -2.9253),       # Bilbao
            (43.4623, -3.8),          # Santander
            (42.8464, -2.6679),       # Vitoria-Gasteiz
            (37.2816349, -6.9362086), # Huelva
            (38.3452, -0.4815),       # Alicante
            (37.9787, -0.6822),       # Torrevieja
            (40.0, -3.0),             # Tarancón (viejo)
        ]
        
        fixed_count = 0
        unset_count = 0
        
        # 2. Investigar a CUALQUIER pasajero que tenga estas coordenadas exactas
        for lat, lon in clusters:
            pasajeros = PasajeroSirio.query.filter(
                db.func.abs(PasajeroSirio.lat - lat) < 0.001,
                db.func.abs(PasajeroSirio.lon - lon) < 0.001
            ).all()
            
            if not pasajeros: continue
            
            print(f"Investigando cluster en ({lat}, {lon}) con {len(pasajeros)} pasajeros...")
            
            for p in pasajeros:
                search_terms = []
                if p.municipio: search_terms.append(p.municipio)
                if p.provincia: search_terms.append(p.provincia)
                
                found_ciudad = None
                for term in search_terms:
                    # Dividir por comas por si acaso
                    parts = [t.strip() for t in term.split(',')]
                    for part in parts:
                        if not part or len(part) < 3: continue
                        
                        # Si el municipio es igual al cluster (ej: "Madrid" en cluster Madrid), lo dejamos
                        # Pero si el municipio es "Potenza" en cluster Madrid, lo arreglamos
                        ciudad = Ciudad.query.filter(Ciudad.name.ilike(part)).first()
                        if ciudad and ciudad.lat and ciudad.lon:
                            dist_to_original = abs(ciudad.lat - lat) + abs(ciudad.lon - lon)
                            if dist_to_original > 0.5: # Si la ciudad real está lejos del cluster
                                found_ciudad = ciudad
                                break
                    if found_ciudad: break
                
                if found_ciudad:
                    p.lat = found_ciudad.lat
                    p.lon = found_ciudad.lon
                    fixed_count += 1
                else:
                    # Si no hay match pero es claramente sospechoso (ej: país Italia), lo quitamos
                    is_suspicious = False
                    if p.pais and any(x in p.pais.upper() for x in ["ITALIA", "BRAZIL", "BRASIL", "ARABIA", "AUSTRO-HUNGRIA"]):
                        is_suspicious = True
                    
                    if is_suspicious:
                        p.lat = None
                        p.lon = None
                        unset_count += 1

        db.session.commit()
        print(f"Sincronización por clusters finalizada:")
        print(f"  Pasajeros reubicados: {fixed_count}")
        print(f"  Coordenadas eliminadas (cúmulos erróneos): {unset_count}")

if __name__ == "__main__":
    fix()
