import pandas as pd
import openpyxl
import os
import sys

# Path setup
project_root = '/opt/hesiox'
sys.path.append(project_root)

from app import app
from models import PasajeroSirio, Publicacion, db

def sync_publications():
    excel_path = os.path.join(project_root, 'pasajeros/viajeros_enriquecidos.xlsx')
    if not os.path.exists(excel_path):
        print(f"Error: {excel_path} not found")
        return

    print("Reading Excel mapping...")
    wb = openpyxl.load_workbook(excel_path, data_only=True)
    sheet = wb.active
    rows = list(sheet.rows)
    headers = [c.value.strip() if (c.value and isinstance(c.value, str)) else str(c.value) for c in rows[0]]
    
    # Mapping of Excel columns to Publication names
    # As requested by the user
    mapping = {
        'Actas de Inspección Marítima - Embarcados Nápoles\r\nVapor Italia 29/08/1906': 'Actas de Inspección Marítima - Embarcados Nápoles Vapor Italia 29/08/1906',
        'lista_giornale': 'Il Giornale d\'Italia',
        'lista_messagero': 'Il Messaggero',
        'lista_gazzeta_popolo': 'La Gazzetta del Popolo',
        'lista_corriere': 'Corriere della Sera',
        'lista_osservatore': 'L\'Osservatore Romano',
        'lista_canadell': 'Lista Vilavecchia y Canadell',
        'lista_bordo': 'Lista de A Bordo',
        'lista_tripulacion': 'Lista Tripulación',
        'lista_maria_luisa': 'Lista Maria Luisa',
        'lista_sobrevivientes_gazzeta': 'Sobrevivientes Gazzetta d\'Italia',
        'lista_sobrevivientes_cartagena': 'Lista Sobrevivientes Cartagena'
    }

    with app.app_context():
        # 1. Renaming and preparing publications
        print("Updating/Creating publications...")
        
        # Special rename: Lista Gazzetta del Popolo (383) -> Sobrevivientes Gazzetta d'Italia
        p383 = Publicacion.query.get(383)
        if p383:
            print(f"Renaming ID 383: {p383.nombre} -> Sobrevivientes Gazzetta d'Italia")
            p383.nombre = "Sobrevivientes Gazzetta d'Italia"
            p383.tipo_recurso = "Lista de Pasajeros"
        
        # Create/Get all mapping publications
        pub_objects = {}
        for col, pub_name in mapping.items():
            pub = Publicacion.query.filter_by(nombre=pub_name, proyecto_id=1).first()
            if not pub:
                print(f"Creating publication: {pub_name}")
                pub = Publicacion(nombre=pub_name, proyecto_id=1, tipo_recurso="Lista de Pasajeros")
                db.session.add(pub)
            else:
                pub.tipo_recurso = "Lista de Pasajeros"
            pub_objects[col] = pub
            
        db.session.commit()
        
        # 2. Sync passengers
        print("Syncing passengers by name matching...")
        def normalize(s):
            if not s: return ""
            s = str(s).strip().upper()
            import re
            s = re.sub(r'\(.*?\)', '', s).strip()
            return s

        all_db = PasajeroSirio.query.all()
        db_map = {}
        for p in all_db:
            key = f"{normalize(p.nombre)}|{normalize(p.apellidos)}"
            if key not in db_map:
                db_map[key] = p # Just take the first one if duplicates
        
        total_synced = 0
        for i, r in enumerate(rows[1:]):
            row_data = dict(zip(headers, [c.value for c in r]))
            
            ex_key = f"{normalize(row_data.get('nombre'))}|{normalize(row_data.get('apellidos'))}"
            pasajero = db_map.get(ex_key)
            
            if not pasajero:
                continue
            
            # Identify which lists this passenger belongs to
            target_pubs = []
            for col, pub in pub_objects.items():
                val = str(row_data.get(col) or '').strip().upper()
                if val == 'X':
                    target_pubs.append(pub)
            
            # Update publications relationship
            # Note: We keep "prensa" type publications (news) if they were linked manually
            current_pubs = pasajero.publicaciones
            non_list_pubs = [p for p in current_pubs if p.tipo_recurso != "Lista de Pasajeros"]
            
            # Combine non-list with target-lists
            pasajero.publicaciones = non_list_pubs + target_pubs
            total_synced += 1
            
            if total_synced % 100 == 0:
                print(f"Synced {total_synced} passengers...")
        
        db.session.commit()
        print(f"Total passengers synced: {total_synced}")

if __name__ == "__main__":
    sync_publications()
