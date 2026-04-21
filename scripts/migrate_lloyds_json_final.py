import json
import psycopg2
import re

DB_URL = "postgresql://hesiox_user:garciap1975@localhost/hesiox"

def convert_ft_to_m(val_str):
    if not val_str or "(" in str(val_str): return val_str
    # Extract numbers like 380.0 from "380.0 ft"
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

def run_migration():
    try:
        # Load data from the exported JSON
        with open('/opt/hesiox/scripts/sirio_data.json', 'r') as f:
            data = json.load(f)
        
        print(f"Migrating data for S.S. Sirio (JSON format)...")

        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()

        # Check if Lloyds record exists
        cur.execute("SELECT id FROM lloyds_register_survey_inspeccion_absoluta LIMIT 1")
        l_row = cur.fetchone()
        if l_row:
            target_id = l_row[0]
            print(f"Updating existing Lloyds record ID: {target_id}")
        else:
            cur.execute("INSERT INTO lloyds_register_survey_inspeccion_absoluta DEFAULT VALUES RETURNING id")
            target_id = cur.fetchone()[0]
            print(f"Created new Lloyds record ID: {target_id}")

        g = data.get('datos_generales', {})
        e = data.get('datos_estructura', {})
        eq = data.get('datos_equipamiento', {})
        i = data.get('datos_inspecciones', {})
        fij = data.get('datos_fijaciones', {})

        mapping = {
            # Dimensions
            'length_overall_eslora_total': (g.get('Eslora'), convert_ft_to_m),
            'breadth_extreme_manga_maxima': (g.get('Manga'), convert_ft_to_m),
            'depth_of_hold_puntal_bodega': (g.get('Puntal'), convert_ft_to_m),
            
            # Tonnage
            'gross_tonnage_tonelaje_bruto': (g.get('Tonelaje Bruto'), lambda x: f"{x} t ({x} tons)" if x else None),
            'net_tonnage_tonelaje_neto': (g.get('Tonelaje Registro'), lambda x: f"{x} t ({x} tons)" if x else None),
            
            # Info general
            'built_at_construido_en': (f"{g.get('Astillero', '')}, {g.get('Inspección en', '')}".strip(', '), str),
            'when_built_cuando_construido': (g.get('Año'), str),
            'port_belonging_puerto_pertenencia': (g.get('Puerto'), str),
            'survey_no_numero_inspeccion': (g.get('Nº Reporte'), str),
            
            # Materials/Equipment from equipment JSON part
            'cable_chain_length': (eq.get('Cables'), convert_fathoms_to_m),
            
            # Note: The JSON doesn't have exact fields for all 190 columns, 
            # but we populate the main ones found.
        }

        # Handling special strings from structure
        # Example: "Iron, 96 ft (Fore/Main), 82 ft (Mizen)"
        masts = eq.get('Mástiles')
        if masts:
             # Just store as is or simple transliteration
             cur.execute("UPDATE lloyds_register_survey_inspeccion_absoluta SET masts_yards_mastiles_vergas = %s WHERE id = %s", (masts, target_id))

        # Anchors
        cur.execute("UPDATE lloyds_register_survey_inspeccion_absoluta SET anchors_no_numero_anclas = %s WHERE id = %s", (eq.get('Anclas'), target_id))

        for col, (raw_val, func) in mapping.items():
            if raw_val is not None:
                new_val = func(raw_val)
                print(f"  {col}: {raw_val} -> {new_val}")
                cur.execute(f"UPDATE lloyds_register_survey_inspeccion_absoluta SET {col} = %s WHERE id = %s", (new_val, target_id))

        conn.commit()
        print("Migration and unit conversion complete.")
        cur.close()
        conn.close()

    except Exception as ex:
        print(f"Error: {ex}")

if __name__ == "__main__":
    run_migration()
