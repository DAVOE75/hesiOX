
import os
import re
from app import app
from extensions import db
from models import Ciudad, LugarNoticia, Prensa

def clean_location_name(name):
    if not name: return ""
    # Prefijos comunes extraídos por spaCy que deben normalizarse
    prefijos = [
        r'^á\s+', r'^a\s+', r'^en\s+', r'^de\s+', r'^desde\s+', 
        r'^hasta\s+', r'^hacia\s+', r'^por\s+', r'^para\s+', r'^sobre\s+',
        r'^del\s+', r'^al\s+'
    ]
    cleaned = name.strip()
    for p in prefijos:
        cleaned = re.sub(p, '', cleaned, flags=re.IGNORECASE).strip()
    
    if cleaned and cleaned[0].islower():
        cleaned = cleaned[0].upper() + cleaned[1:]
    return cleaned

def run_cleanup():
    print("🚀 Iniciando cleanup de ubicaciones en PostgreSQL...")
    with app.app_context():
        # 1. Normalizar nombres en la tabla Ciudad (Catálogo global)
        ciudades = Ciudad.query.all()
        count_c = 0
        for ciudad in ciudades:
            new_name = clean_location_name(ciudad.name)
            if new_name != ciudad.name:
                print(f"  [CIUDAD] '{ciudad.name}' -> '{new_name}'")
                # Verificar si ya existe el nombre normalizado para evitar duplicados (IntegrityError)
                existing = Ciudad.query.filter_by(name=new_name).first()
                if existing:
                    print(f"    [!] Duplicado detectado. Borrando '{ciudad.name}'")
                    db.session.delete(ciudad)
                else:
                    ciudad.name = new_name
                count_c += 1
        
        db.session.flush()

        # 2. Normalizar nombres en LugarNoticia (Ubicaciones por noticia)
        lugares = LugarNoticia.query.all()
        count_l = 0
        for lugar in lugares:
            new_name = clean_location_name(lugar.nombre)
            if new_name != lugar.nombre:
                print(f"  [LUGAR_NOTICIA] Noticia:{lugar.noticia_id} '{lugar.nombre}' -> '{new_name}'")
                
                # Verificar si ya existe ese nombre en la MISMA noticia
                existing_in_news = LugarNoticia.query.filter_by(
                    noticia_id=lugar.noticia_id, 
                    nombre=new_name
                ).filter(LugarNoticia.id != lugar.id).first()
                
                if existing_in_news:
                    print(f"    [!] Fusionando frecuencia ({lugar.frecuencia}) con registro existente.")
                    existing_in_news.frecuencia = (existing_in_news.frecuencia or 0) + (lugar.frecuencia or 1)
                    db.session.delete(lugar)
                else:
                    lugar.nombre = new_name
                count_l += 1

        db.session.commit()
        print(f"\n✅ Finalizado. {count_c} ciudades y {count_l} lugares procesados.")

if __name__ == "__main__":
    run_cleanup()
