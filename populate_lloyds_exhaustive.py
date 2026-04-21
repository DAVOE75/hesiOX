import sys
import os

# Añadir el path del proyecto para importar db y app
sys.path.append('/opt/hesiox')
from app import app
from models import db, LloydsFicha

def populate_exhaustive():
    with app.app_context():
        # Obtener o crear la ficha (asumimos que solo hay una para el Sirio)
        ficha = LloydsFicha.query.first()
        if not ficha:
            ficha = LloydsFicha()
            db.session.add(ficha)
        
        # --- IMAGE 1: RIGGING & HATCHWAYS ---
        ficha.rigging_standing_running = "Wire & hemp"
        ficha.rigging_quality = "Good"
        ficha.boats_long_boats_no = "3"
        ficha.boats_steam_launch_no = "1"
        ficha.windlass_maker = "Harfield"
        ficha.windlass_condition = "Good"
        ficha.capstan_condition = "Good"
        ficha.rudder_condition = "Good"
        ficha.pumps_condition = "Good"
        ficha.engine_room_skylights_const = "Teak on iron comings"
        ficha.engine_room_skylights_secured = "Slide rods & pins"
        ficha.deadlights_bad_weather = "Gratings and tarpaulins"
        ficha.coal_bunker_openings_const = "C. Iron comings or frames"
        ficha.coal_bunker_openings_lids = "Battens & clutch"
        ficha.coal_bunker_openings_height = "11 in"
        ficha.scuppers_arrangements = "Scuppers and open bulwarks"
        ficha.cargo_hatchways_formed = "Iron Comings 18 high"
        ficha.main_hatch_size = "12 ft x 12 ft"
        ficha.fore_hatch_size = "8 ft 2 in x 7 ft 10 in"
        ficha.quarter_hatch_size = "12 ft x 12 ft"
        ficha.extraordinary_size_framed = "Ordinary size"
        ficha.shifting_beams_arrangement = "One Fore and After"
        ficha.hatches_strong_efficient = "Yes Solid 3 in"

        # --- IMAGE 2: WORKMANSHIP ---
        ficha.workmanship_plating_butts = "Planed"
        ficha.workmanship_carvel_edges = "Yes"
        ficha.workmanship_fillings_solid = "Yes"
        ficha.workmanship_riveting_holes = "Yes"
        ficha.workmanship_riveting_countersunk = "Yes"
        ficha.workmanship_rivets_break = "Only a few"

        # --- IMAGE 3: FRAMES & SIGNATURES ---
        ficha.frames_extension_from_to = "Keel to Gunwale"
        ficha.frames_riveted_rivets_size = "7/8 in. Rivets, about 7 in. apart"
        ficha.reversed_angle_irons_extension = "From middle line to Main Stringer and to Sp. on Stringer alternately"
        ficha.reversed_angle_irons_machinery = "To spar dk on every frame"
        ficha.keelsons_connected_butts = "Yes"
        ficha.iron_quality = "Good Cleveland"
        ficha.manufacturers_trade_mark = "Mossend Glasgow Iron Co, Parkhead, Bol, Vaughan & co"
        ficha.builder_signature = "R. Napier & Sons"
        ficha.surveyor_signature = "W. Davidson"

        # --- RELATIVE PLATING (Handwritten notes in Image 3) ---
        ficha.plating_garboard_riveting_to_keel = "Double riveted, 1 1/4 in. dia, avg 6 ins centre"
        ficha.plating_garboard_edges_riveting = "Double riveted, 7/8 & 15/16 in. dia, avg 3 1/4 ins"
        ficha.plating_bilge_butts_thickness = "Treble riveted, 2/16 thicker than plates"

        # --- PREVIOUS BASIC DATA (Ensuring it persists) ---
        ficha.survey_no_numero_inspeccion = "6147"
        ficha.survey_held_at_inspeccion_en = "Glasgow"
        ficha.vessel_type_tipo_buque = "Spar-decked vessel (Steam)"
        ficha.master_capitan = "G. Niglio"
        ficha.built_at_construido_en = "Govan, Glasgow"
        ficha.when_built_cuando_construido = "June 1883"
        ficha.by_whom_built_por_quien_construido = "R. Napier & Sons"
        ficha.owners_propietarios = "Navigazione Generale Italiana"
        ficha.destined_voyage_viaje_destinado = "South America"
        
        db.session.commit()
        print("Exhaustive data population completed!")

if __name__ == "__main__":
    populate_exhaustive()
