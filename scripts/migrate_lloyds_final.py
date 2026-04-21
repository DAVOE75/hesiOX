import psycopg2
import re

DB_URL = "postgresql://hesiox_user:garciap1975@localhost/hesiox"

def convert_ft_to_m(val_str):
    if not val_str or "(" in str(val_str): return val_str
    match = re.search(r"(\d+\.?\d*)", str(val_str))
    if match:
        val = float(match.group(1))
        metric = round(val * 0.3048, 2)
        return f"{metric} m ({val} ft)"
    return val_str

def convert_in_to_cm(val_str):
    if not val_str or "(" in str(val_str): return val_str
    match = re.search(r"(\d+\.?\d*)", str(val_str))
    if match:
        val = float(match.group(1))
        metric = round(val * 2.54, 2)
        return f"{metric} cm ({val} in)"
    return val_str

def convert_fathoms_to_m(val_str):
    if not val_str or "(" in str(val_str): return val_str
    match = re.search(r"(\d+\.?\d*)", str(val_str))
    if match:
        val = float(match.group(1))
        metric = round(val * 1.8288, 2)
        return f"{metric} m ({val} fathoms)"
    return val_str

def translate_term(term):
    if not term or "(" in str(term): return term
    translations = {
        "Acero": "Acero (Steel)",
        "Hierro": "Hierro (Iron)",
        "Madera": "Madera (Wood)",
        "Pino": "Pino (Pine)",
        "Teca": "Teca (Teak)",
        "Roble": "Roble (Oak)",
        "Teak": "Teca (Teak)",
        "Steel": "Acero (Steel)",
        "Iron": "Hierro (Iron)"
    }
    return translations.get(term, term)

def run_migration():
    try:
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()

        # 1. Fetch data from sirio_ficha
        cur.execute("SELECT * FROM public.sirio_ficha WHERE id = 1")
        colnames = [desc[0] for desc in cur.description]
        row = cur.fetchone()
        
        print(f"DEBUG: colnames: {colnames}")
        print(f"DEBUG: row: {row}")
        
        if not row:
            print("No source data in sirio_ficha for ID 1.")
            return
            
        data = dict(zip(colnames, row))
        print(f"DEBUG: data: {data}")
        print(f"Migrating data for {data.get('nombre_barco', 'S.S. Sirio')}...")

        # 2. Check if Lloyds record exists, else create
        cur.execute("SELECT id FROM lloyds_register_survey_inspeccion_absoluta LIMIT 1")
        l_row = cur.fetchone()
        if l_row:
            target_id = l_row[0]
            print(f"Updating existing Lloyds record ID: {target_id}")
        else:
            cur.execute("INSERT INTO lloyds_register_survey_inspeccion_absoluta DEFAULT VALUES RETURNING id")
            target_id = cur.fetchone()[0]
            print(f"Created new Lloyds record ID: {target_id}")

        # 3. Mapping and conversion
        mapping = {
            # Dimensions
            'length_overall_eslora_total': (data.get('longitud_total'), convert_ft_to_m),
            'breadth_extreme_manga_maxima': (data.get('manga_fuera'), convert_ft_to_m),
            'depth_of_hold_puntal_bodega': (data.get('puntal_bodega'), convert_ft_to_m),
            'eslora_perpendicular': (data.get('eslora_perpendicular'), convert_ft_to_m),
            
            # Tonnage
            'gross_tonnage_tonelaje_bruto': (data.get('tonelaje_bruto'), lambda x: f"{x} t ({x} tons)" if x else None),
            'net_tonnage_tonelaje_neto': (data.get('tonelaje_neto'), lambda x: f"{x} t ({x} tons)" if x else None),
            
            # Masts
            'mast_fore_length': (data.get('mastil_trinquete_longitud'), convert_ft_to_m),
            'mast_main_length': (data.get('mastil_mayor_longitud'), convert_ft_to_m),
            'mast_mizzen_length': (data.get('mastil_mesana_longitud'), convert_ft_to_m),
            'mast_fore_dia': (data.get('mastil_trinquete_diametro'), convert_in_to_cm),
            'mast_main_dia': (data.get('mastil_mayor_diametro'), convert_in_to_cm),
            'mast_mizzen_dia': (data.get('mastil_mesana_diametro'), convert_in_to_cm),
            
            # Cables
            'cable_chain_length': (data.get('cadenas_ancla_longitud'), convert_fathoms_to_m),
            'cable_chain_size': (data.get('cadenas_ancla_tamano'), convert_in_to_cm),
            
            # Chronology
            'survey_1st_frame': (data.get('cronologia_quillas'), str),
            'survey_2nd_plating': (data.get('cronologia_planchaje'), str),
            'survey_3rd_beams': (data.get('cronologia_cuadernas'), str),
            'survey_5th_launched': (data.get('cronologia_botadura'), str),
            
            # Info general
            'built_at_construido_en': (f"{data.get('puesto_construccion', '')}, {data.get('lugar_construccion', '')}", str),
            'when_built_cuando_construido': (data.get('fecha_construccion'), str),
            'by_whom_built_por_quien_construido': (data.get('empresa_constructora'), str),
            'port_belonging_puerto_pertenencia': (data.get('puerto_registro'), str),
            'survey_no_numero_inspeccion': (data.get('numero_oficial'), str),
            
            # Materials
            'keel_material_material_quilla': (data.get('material_casco'), translate_term),
            'deck_material_material_cubiertas': (data.get('cubierta_material'), translate_term),
            'rigging_type_tipo_aparejo': (data.get('aparejo_tipo'), translate_term)
        }

        for col, (raw_val, func) in mapping.items():
            print(f"DEBUG: Processing {col} with raw_val: {raw_val}")
            if raw_val is not None:
                try:
                    new_val = func(raw_val)
                    print(f"  SUCCESS: {col}: {raw_val} -> {new_val}")
                    cur.execute(f"UPDATE lloyds_register_survey_inspeccion_absoluta SET {col} = %s WHERE id = %s", (new_val, target_id))
                except Exception as e:
                    print(f"  ERROR processing {col}: {e}")
            else:
                print(f"  SKIP: {col} is None")

        conn.commit()
        print("Migration and unit conversion complete.")
        cur.close()
        conn.close()

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    run_migration()
