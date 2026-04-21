"""
Script para clasificar ubicaciones existentes según su tipo geográfico.
Re-geocodifica las ubicaciones para obtener el campo 'type' de Nominatim.
"""
import sys
import os
import time
import requests

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from extensions import db
from models import LugarNoticia
from sqlalchemy import distinct

def classify_existing_locations():
    """Clasifica ubicaciones que aún no tienen tipo_lugar definido"""
    with app.app_context():
        # Obtener nombres únicos sin tipo_lugar o con 'unknown'
        lugares_query = db.session.query(
            LugarNoticia.nombre,
            LugarNoticia.lat,
            LugarNoticia.lon
        ).filter(
            (LugarNoticia.tipo_lugar == None) | (LugarNoticia.tipo_lugar == 'unknown')
        ).distinct()
        
        lugares_unicos = lugares_query.all()
        total = len(lugares_unicos)
        
        print(f"Encontradas {total} ubicaciones únicas para clasificar.")
        
        if total == 0:
            print("No hay ubicaciones pendientes de clasificar.")
            return
        
        processed = 0
        classified = 0
        
        for nombre, lat, lon in lugares_unicos:
            # Respetar límites de Nominatim (1 req/segundo)
            time.sleep(1.1)
            
            try:
                # Intentar reverse geocoding si tenemos coordenadas válidas
                if lat and lon and lat != 0 and lon != 0:
                    resp = requests.get('https://nominatim.openstreetmap.org/reverse', 
                        params={
                            'lat': lat,
                            'lon': lon,
                            'format': 'json',
                            'zoom': 18  # Máximo detalle
                        }, 
                        headers={'User-Agent': 'hesiox-classification/1.0'},
                        timeout=5
                    )
                else:
                    # Geocoding directo si no hay coords
                    resp = requests.get('https://nominatim.openstreetmap.org/search', 
                        params={
                            'q': nombre,
                            'format': 'json',
                            'limit': 1
                        }, 
                        headers={'User-Agent': 'hesiox-classification/1.0'},
                        timeout=5
                    )
                
                data = resp.json()
                tipo_detectado = 'unknown'
                
                if isinstance(data, dict) and 'type' in data:
                    # Reverse geocoding response
                    tipo_detectado = data.get('type', 'unknown')
                elif isinstance(data, list) and len(data) > 0:
                    # Search response
                    tipo_detectado = data[0].get('type', 'unknown')
                
                # Actualizar TODAS las entradas con ese nombre
                if tipo_detectado != 'unknown':
                    updated = db.session.query(LugarNoticia).filter(
                        LugarNoticia.nombre == nombre
                    ).update({
                        'tipo_lugar': tipo_detectado
                    }, synchronize_session=False)
                    
                    db.session.commit()
                    classified += updated
                    print(f"[{processed+1}/{total}] ✓ {nombre} → {tipo_detectado} ({updated} registros)")
                else:
                    print(f"[{processed+1}/{total}] ? {nombre} → tipo desconocido")
                    
            except requests.exceptions.Timeout:
                print(f"[{processed+1}/{total}] ✗ {nombre} → timeout")
            except Exception as e:
                print(f"[{processed+1}/{total}] ✗ {nombre} → error: {e}")
            
            processed += 1
        
        print(f"\n{'='*60}")
        print(f"Clasificación completada:")
        print(f"  - Procesados: {processed}/{total}")
        print(f"  - Clasificados: {classified} registros actualizados")
        print(f"{'='*60}")

if __name__ == "__main__":
    print("Iniciando clasificación de ubicaciones existentes...")
    print("NOTA: Este proceso puede tardar varios minutos debido a límites de API.")
    classify_existing_locations()
