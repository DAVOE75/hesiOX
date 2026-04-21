import sys
import os
from sqlalchemy import text

# Añadir el path del proyecto para importar db y app
sys.path.append('/opt/hesiox')
from app import app
from models import db

def update_schema():
    new_columns = [
        "keelsons_connected_butts",
        "frames_riveted_rivets_size",
        "plating_garboard_riveting_to_keel",
        "plating_garboard_edges_riveting",
        "plating_bilge_butts_thickness",
        "plating_side_edges_riveting",
        "plating_side_butts_riveting",
        "plating_sheerstrake_edges",
        "plating_sheerstrake_butts",
        "plating_spar_sheerstrake_butts",
        "plating_stringer_plate_butts",
        "plating_spar_stringer_plate_butts",
        "plating_laps_breadth_double",
        "plating_laps_breadth_single",
        "butt_straps_riveted_type",
        "breasthooks_no",
        "crutches_no",
        "workmanship_plating_butts",
        "workmanship_carvel_edges",
        "workmanship_fillings_solid",
        "workmanship_riveting_holes",
        "workmanship_riveting_countersunk",
        "workmanship_rivets_break",
        "rigging_standing_running",
        "rigging_quality",
        "windlass_maker",
        "windlass_condition",
        "capstan_condition",
        "rudder_condition",
        "pumps_condition",
        "boats_long_boats_no",
        "boats_steam_launch_no",
        "engine_room_skylights_const",
        "engine_room_skylights_secured",
        "deadlights_bad_weather",
        "coal_bunker_openings_const",
        "coal_bunker_openings_lids",
        "coal_bunker_openings_height",
        "scuppers_arrangements",
        "cargo_hatchways_formed",
        "main_hatch_size",
        "fore_hatch_size",
        "quarter_hatch_size",
        "extraordinary_size_framed",
        "shifting_beams_arrangement",
        "hatches_strong_efficient",
        "iron_quality",
        "manufacturers_trade_mark",
        "builder_signature",
        "surveyor_signature"
    ]
    
    with app.app_context():
        for col in new_columns:
            try:
                # Comprobar si la columna existe (PostgreSQL)
                check_sql = text(f"SELECT column_name FROM information_schema.columns WHERE table_name='lloyds_register_survey_inspeccion_absoluta' AND column_name='{col}'")
                result = db.session.execute(check_sql).fetchone()
                
                if not result:
                    print(f"Adding column: {col}")
                    add_sql = text(f"ALTER TABLE lloyds_register_survey_inspeccion_absoluta ADD COLUMN {col} VARCHAR(255)")
                    db.session.execute(add_sql)
                    db.session.commit()
                else:
                    print(f"Column {col} already exists.")
            except Exception as e:
                print(f"Error adding {col}: {e}")
                db.session.rollback()

if __name__ == "__main__":
    update_schema()
