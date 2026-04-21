
from app import app
from extensions import db
from models import Ciudad, LugarNoticia
import re

def clean_location_name(name):
    if not name: return ""
    prefijos = [
        r'^á\s+', r'^a\s+', r'^en\s+', r'^de\s+', r'^desde\s+', 
        r'^hasta\s+', r'^hacia\s+', r'^por\s+'
    ]
    cleaned = name.strip()
    for p in prefijos:
        cleaned = re.sub(p, '', cleaned, flags=re.IGNORECASE).strip()
    if cleaned and cleaned[0].islower():
        cleaned = cleaned[0].upper() + cleaned[1:]
    return cleaned

with app.app_context():
    print("Iniciando auditoría de base de datos...")
    
    # 1. Auditoría Ciudad
    ciudades = Ciudad.query.all()
    count_c = 0
    for c in ciudades:
        new_name = clean_location_name(c.name)
        if new_name != c.name:
            print(f"[CIUDAD] Limpiando: '{c.name}' -> '{new_name}'")
            # Verificar si ya existe el nombre limpio
            existe = Ciudad.query.filter_by(name=new_name).first()
            if existe and existe.id != c.id:
                print(f"  [!] El destino '{new_name}' ya existe. Fusionando...")
                # En este caso particular de Ciudad, podríamos borrar el duplicado sucio
                db.session.delete(c)
            else:
                c.name = new_name
            count_c += 1
            
    # 2. Auditoría LugarNoticia
    lugares = LugarNoticia.query.all()
    count_l = 0
    for l in lugares:
        new_name = clean_location_name(l.nombre)
        if new_name != l.nombre:
            print(f"[LUGAR_NOTICIA] Limpiando: '{l.nombre}' -> '{new_name}'")
            # Verificar si ya existe en la misma noticia
            existe = LugarNoticia.query.filter_by(noticia_id=l.noticia_id, nombre=new_name).first()
            if existe and existe.id != l.id:
                print(f"  [!] '{new_name}' ya existe en noticia {l.noticia_id}. Fusionando frecuencia...")
                existe.frecuencia += l.frecuencia
                db.session.delete(l)
            else:
                l.nombre = new_name
            count_l += 1
            
    print(f"Resumen: {count_c} ciudades corregidas, {count_l} lugares de noticia corregidos.")
    db.session.commit()
    print("Cambios guardados.")
