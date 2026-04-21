import sys
import os
import re

# Add the application directory to the path
sys.path.append('/opt/hesiox')

from app import app
from models import db, LloydsFicha

def convert_ft_to_m(val_str):
    if not val_str or "(" in val_str: return val_str
    # Extract number
    match = re.search(r"(\d+\.?\d*)", val_str)
    if match:
        val = float(match.group(1))
        metric = round(val * 0.3048, 2)
        return f"{metric} m ({val} ft)"
    return val_str

def convert_in_to_cm(val_str):
    if not val_str or "(" in val_str: return val_str
    match = re.search(r"(\d+\.?\d*)", val_str)
    if match:
        val = float(match.group(1))
        metric = round(val * 2.54, 2)
        return f"{metric} cm ({val} in)"
    return val_str

def convert_fathoms_to_m(val_str):
    if not val_str or "(" in val_str: return val_str
    match = re.search(r"(\d+\.?\d*)", val_str)
    if match:
        val = float(match.group(1))
        metric = round(val * 1.8288, 2)
        return f"{metric} m ({val} fathoms)"
    return val_str

def translate_term(term):
    if not term or "(" in term: return term
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
    print("Initializing Flask app context...")
    with app.app_context():
        ficha = LloydsFicha.query.first()
        if not ficha:
            print("No ficha found.")
            return

        print(f"Updating ficha ID: {ficha.id}")

        # Dimensions
        dims = [
            'length_overall_eslora_total', 'length_between_pp_eslora_entre_pp',
            'breadth_extreme_manga_maxima', 'depth_of_hold_puntal_bodega',
            'depth_moulded_puntal_de_construccion'
        ]
        for field in dims:
            if hasattr(ficha, field):
                val = getattr(ficha, field)
                new_val = convert_ft_to_m(val)
                setattr(ficha, field, new_val)
                print(f"  {field}: {val} -> {new_val}")

        # Tonnage
        tons = ['gross_tonnage_tonelaje_bruto', 'net_tonnage_tonelaje_neto']
        for field in tons:
            if hasattr(ficha, field):
                val = getattr(ficha, field)
                if val and "(" not in val:
                    match = re.search(r"(\d+\.?\d*)", val)
                    if match:
                        num = float(match.group(1))
                        new_val = f"{num} t ({num} tons)"
                        setattr(ficha, field, new_val)
                        print(f"  {field}: {val} -> {new_val}")

        # Masts
        masts = [
            'mast_fore_length', 'mast_main_length', 'mast_mizzen_length'
        ]
        for field in masts:
            if hasattr(ficha, field):
                val = getattr(ficha, field)
                new_val = convert_ft_to_m(val)
                setattr(ficha, field, new_val)
                print(f"  {field}: {val} -> {new_val}")

        masts_dia = [
            'mast_fore_dia', 'mast_main_dia', 'mast_mizzen_dia'
        ]
        for field in masts_dia:
            if hasattr(ficha, field):
                val = getattr(ficha, field)
                new_val = convert_in_to_cm(val)
                setattr(ficha, field, new_val)
                print(f"  {field}: {val} -> {new_val}")

        # Cables & Chains
        cables = [
            'cable_chain_length', 'cable_towline_length', 'cable_hawser_length', 'cable_warp_length'
        ]
        for field in cables:
            if hasattr(ficha, field):
                val = getattr(ficha, field)
                new_val = convert_fathoms_to_m(val)
                setattr(ficha, field, new_val)
                print(f"  {field}: {val} -> {new_val}")

        cables_size = [
            'cable_chain_size', 'cable_towline_size', 'cable_hawser_size', 'cable_warp_size'
        ]
        for field in cables_size:
            if hasattr(ficha, field):
                val = getattr(ficha, field)
                new_val = convert_in_to_cm(val)
                setattr(ficha, field, new_val)
                print(f"  {field}: {val} -> {new_val}")

        # Materials
        mats = [
            'keel_material_material_quilla', 'stem_material_material_roda',
            'stern_post_material_material_codaste', 'frames_material_material_cuadernas',
            'floors_material_material_varengas', 'deck_material_material_cubiertas',
            'rigging_type_tipo_aparejo'
        ]
        for field in mats:
            if hasattr(ficha, field):
                val = getattr(ficha, field)
                new_val = translate_term(val)
                setattr(ficha, field, new_val)
                print(f"  {field}: {val} -> {new_val}")

        db.session.commit()
        print("Update complete and committed.")

if __name__ == "__main__":
    run_update()
