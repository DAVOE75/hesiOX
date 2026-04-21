from app import app
from models import PasajeroSirio, Ciudad
from extensions import db
import unicodedata

def normalize(s):
    if not s: return ""
    # Normalización agresiva: sin acentos, sin espacios, sin guiones
    s = "".join(c for c in unicodedata.normalize('NFD', str(s)) if unicodedata.category(c) != 'Mn')
    return s.lower().replace(' ', '').replace('-', '').strip()

def fix():
    with app.app_context():
        # 1. Caché de ciudades
        ciudades = Ciudad.query.filter(Ciudad.lat.isnot(None)).all()
        ciudades_norm = {}
        for c in ciudades:
            n = normalize(c.name)
            if n not in ciudades_norm or len(c.name) > len(ciudades_norm[n].name):
                ciudades_norm[n] = c
        
        print(f"Diccionario de {len(ciudades_norm)} ciudades cargado.")
        
        # 2. Procesar todos los pasajeros
        pasajeros = PasajeroSirio.query.all()
        fixed_count = 0
        unset_count = 0
        
        # Palabras clave de orígenes reportados como problemáticos
        keywords = ['agrigento', 'asti', 'tigliole', 'massa', 'carrara', 'vollazon', 'santafe', 'pizzo', 'vibovalentia', 'varese', 'gallarate', 'vicenza', 'torino', 'turin', 'ancona', 'oristano']

        for p in pasajeros:
            # Buscar en municipio, provincia y país
            search_text = f"{p.municipio or ''} {p.provincia or ''} {p.pais or ''}"
            norm_text = normalize(search_text)
            
            if not norm_text: continue
            
            found_ciudad = None
            # Intentar match con ciudades conocidas
            # Primero buscamos términos específicos (palabras sueltas en el texto)
            parts = [normalize(t) for t in search_text.replace(',', ' ').split() if len(t) > 3]
            for part in parts:
                if part in ciudades_norm:
                    found_ciudad = ciudades_norm[part]
                    # Si es un match de municipio/provincia, priorizamos
                    break
            
            if found_ciudad:
                # Si las coordenadas actuales son muy diferentes (>0.01), actualizar
                if not p.lat or not p.lon or abs(p.lat - found_ciudad.lat) > 0.01 or abs(p.lon - found_ciudad.lon) > 0.01:
                    p.lat = found_ciudad.lat
                    p.lon = found_ciudad.lon
                    fixed_count += 1
            else:
                # Si no hay match en Ciudad pero es un origen extranjero conocido en una ubicación errónea (España, etc)
                if p.lat and p.lon:
                    # Bounding boxes de clusters reportados: España (inc Canarias), Argentina (Santa Fe area)...
                    in_erroneous_area = False
                    if (27 < p.lat < 45) and (-20 < p.lon < 6): # España / Canarias
                        in_erroneous_area = True
                    if (-35 < p.lat < -30) and (-65 < p.lon < -55): # Santa Fe / Argentina aprox
                        in_erroneous_area = True
                    
                    if in_erroneous_area and any(k in norm_text for k in keywords):
                        p.lat = None
                        p.lon = None
                        unset_count += 1

        db.session.commit()
        print(f"Resultado FINAL DEFINITIVO:")
        print(f"  Pasajeros corregidos/reubicados: {fixed_count}")
        print(f"  Pasajeros con coordenadas eliminadas: {unset_count}")

if __name__ == "__main__":
    fix()
