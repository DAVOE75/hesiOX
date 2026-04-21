import pandas as pd
import os
import sys

# Añadir el path del proyecto para importar los modelos
project_root = '/opt/hesiox'
sys.path.append(project_root)

from app import app
from models import PasajeroSirio
from extensions import db
from sqlalchemy import or_

def normalize_str(s):
    if not s or pd.isna(s): return ""
    import unicodedata
    s = str(s).strip()
    return "".join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn').lower()

def sync():
    excel_path = os.path.join(project_root, 'pasajeros/viajeros_enriquecidos.xlsx')
    if not os.path.exists(excel_path):
        print(f"Error: No se encuentra el archivo {excel_path}")
        return

    print(f"Leyendo Excel: {excel_path} con openpyxl...")
    import openpyxl
    wb = openpyxl.load_workbook(excel_path, data_only=True)
    sheet = wb.active
    
    # Obtener cabeceras
    rows = list(sheet.rows)
    headers = [c.value.strip() if (c.value and isinstance(c.value, str)) else str(c.value) for c in rows[0]]
    
    # Crear lista de diccionarios (como un DataFrame)
    data = []
    for r in rows[1:]:
        data.append(dict(zip(headers, [c.value for c in r])))
    
    total_rows = len(data)

    with app.app_context():
        total_updated = 0
        total_matched = 0
        
        # Cache de todos los pasajeros para búsqueda por ID y por nombre
        print("Cargando pasajeros de la DB para matching...")
        all_pasajeros = PasajeroSirio.query.all()
        pasajeros_by_id = {p.id: p for p in all_pasajeros}
        pasajeros_by_name = {}
        for p in all_pasajeros:
            key = f"{normalize_str(p.nombre)}|{normalize_str(p.apellidos)}"
            if key not in pasajeros_by_name:
                pasajeros_by_name[key] = []
            pasajeros_by_name[key].append(p)
        
        print(f"Iniciando matching para {total_rows} filas...")
        
        for index, row in enumerate(data):
            pasajero = None
            
            # Intento 1: Por ID
            row_id = row.get('id')
            if row_id and int(row_id) in pasajeros_by_id:
                pasajero = pasajeros_by_id[int(row_id)]
            
            # Intento 2: Por Nombre/Apellidos
            if not pasajero:
                nombre_ex = normalize_str(row.get('nombre'))
                apellidos_ex = normalize_str(row.get('apellidos'))
                key_ex = f"{nombre_ex}|{apellidos_ex}"
                matches = pasajeros_by_name.get(key_ex)
                if matches:
                    pasajero = matches[0]

            if pasajero:
                total_matched += 1
                updated = False
                
                # Mapeo de campos directos
                field_mapping = {
                    'Municipio': 'municipio',
                    'Provincia': 'provincia',
                    'Región': 'region',
                    'pais': 'pais',
                    'pasaje': 'pasaje',
                    'estado': 'estado',
                    'puerto_embarque': 'puerto_embarque',
                    'ciudad_destino': 'ciudad_destino',
                    'ciudad_destino_final': 'ciudad_destino_final',
                    'comentarios': 'comentarios',
                    'hospedaje_cartagena': 'hospedaje_cartagena'
                }
                
                for ex_col, db_field in field_mapping.items():
                    val = row.get(ex_col)
                    if val is not None:
                        # Convertir a string si es necesario
                        if not isinstance(val, (str, bytes)) and val is not None:
                            val = str(val)
                        if getattr(pasajero, db_field) != val:
                            setattr(pasajero, db_field, val)
                            updated = True

                # Coordenadas
                for coord in ['lat', 'lon']:
                    val = row.get(coord)
                    if val is not None:
                        try:
                            f_val = float(val)
                            current_val = getattr(pasajero, coord)
                            if current_val is None or abs(current_val - f_val) > 0.0001:
                                setattr(pasajero, coord, f_val)
                                updated = True
                        except (ValueError, TypeError):
                            pass
                
                # Listas de participación (Booleanos)
                # 'lista_italia' -> en_lista_italia_mvd? (Necesita ser flexible)
                if row.get('lista_italia') is not None:
                    bool_val = bool(row.get('lista_italia'))
                    if pasajero.en_lista_italia_mvd != bool_val:
                        pasajero.en_lista_italia_mvd = bool_val
                        updated = True
                
                if row.get('lista_ravena') is not None:
                    bool_val = bool(row.get('lista_ravena'))
                    if pasajero.en_lista_ravena_sp != bool_val:
                        pasajero.en_lista_ravena_sp = bool_val
                        updated = True

                if row.get('lista_orione') is not None:
                    bool_val = bool(row.get('lista_orione'))
                    if pasajero.en_lista_orione_ge != bool_val:
                        pasajero.en_lista_orione_ge = bool_val
                        updated = True

                if updated:
                    total_updated += 1
            
            if index % 100 == 0:
                print(f"Procesando fila {index}/{total_rows}...")
        
        db.session.commit()
        print(f"\nSincronización completada.")
        print(f"Filas en Excel: {total_rows}")
        print(f"Registros emparejados: {total_matched}")
        print(f"Registros actualizados en DB: {total_updated}")

if __name__ == "__main__":
    sync()
