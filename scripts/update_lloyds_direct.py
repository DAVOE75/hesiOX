import psycopg2
import re

# Database connection details from .env
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
        "Cuerda": "Cuerda (Rope)",
        "Cadena": "Cadena (Chain)",
        "Lona": "Lona (Canvas)",
        "Sencillo": "Sencillo (Single)",
        "Doble": "Doble (Double)",
        "Triple": "Triple (Triple)",
        "Completo": "Completo (Full)",
        "Parcial": "Parcial (Partial)",
    }
    return translations.get(term, term)

def run_update():
    try:
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()
        
        # Get the first record
        cur.execute("SELECT id FROM lloyds_register_survey_inspeccion_absoluta LIMIT 1")
        row = cur.fetchone()
        if not row:
            print("No records found.")
            return
        
        ficha_id = row[0]
        print(f"Updating record ID: {ficha_id}")

        # Fields to update
        # Format: (column_name, conversion_func)
        fields_to_process = [
            ('length_overall_eslora_total', convert_ft_to_m),
            ('length_between_pp_eslora_entre_pp', convert_ft_to_m),
            ('breadth_extreme_manga_maxima', convert_ft_to_m),
            ('depth_of_hold_puntal_bodega', convert_ft_to_m),
            ('depth_moulded_puntal_de_construccion', convert_ft_to_m),
            ('mast_fore_length', convert_ft_to_m),
            ('mast_main_length', convert_ft_to_m),
            ('mast_mizzen_length', convert_ft_to_m),
            ('mast_fore_dia', convert_in_to_cm),
            ('mast_main_dia', convert_in_to_cm),
            ('mast_mizzen_dia', convert_in_to_cm),
            ('cable_chain_length', convert_fathoms_to_m),
            ('cable_chain_size', convert_in_to_cm),
            ('cable_towline_length', convert_fathoms_to_m),
            ('cable_towline_size', convert_in_to_cm),
            ('keel_material_material_quilla', translate_term),
            ('deck_material_material_cubiertas', translate_term),
            ('rigging_type_tipo_aparejo', translate_term),
            ('material_casco', translate_term),
            ('cubierta_material', translate_term),
            ('aparejo_tipo', translate_term)
        ]

        for col, func in fields_to_process:
            try:
                cur.execute(f"SELECT {col} FROM lloyds_register_survey_inspeccion_absoluta WHERE id = %s", (ficha_id,))
                val = cur.fetchone()[0]
                if val:
                    new_val = func(val)
                    if new_val != val:
                        cur.execute(f"UPDATE lloyds_register_survey_inspeccion_absoluta SET {col} = %s WHERE id = %s", (new_val, ficha_id))
                        print(f"  {col}: {val} -> {new_val}")
            except Exception as e:
                # Column might not exist in some versions, skip
                print(f"  Skipping {col}: {e}")
                conn.rollback()
                continue

        # Tonnage special handling
        for col in ['gross_tonnage_tonelaje_bruto', 'net_tonnage_tonelaje_neto', 'tonelaje_registro']:
            try:
                cur.execute(f"SELECT {col} FROM lloyds_register_survey_inspeccion_absoluta WHERE id = %s", (ficha_id,))
                val = cur.fetchone()[0]
                if val and "(" not in str(val):
                    match = re.search(r"(\d+\.?\d*)", str(val))
                    if match:
                        num = float(match.group(1))
                        new_val = f"{num} t ({num} tons)"
                        cur.execute(f"UPDATE lloyds_register_survey_inspeccion_absoluta SET {col} = %s WHERE id = %s", (new_val, ficha_id))
                        print(f"  {col}: {val} -> {new_val}")
            except Exception:
                conn.rollback()
                continue

        conn.commit()
        print("Update complete and committed.")
        cur.close()
        conn.close()

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    run_update()
