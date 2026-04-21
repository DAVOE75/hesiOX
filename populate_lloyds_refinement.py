import sys
import os

# Añadir el path del proyecto para importar db y app
sys.path.append('/opt/hesiox')
from app import app
from models import db, LloydsFicha

def refine_lloyds_data():
    with app.app_context():
        ficha = LloydsFicha.query.first()
        if not ficha:
            ficha = LloydsFicha()
            db.session.add(ficha)
        
        # --- ESTRUCTURA (REFINADO) ---
        ficha.frames_extension_from_to = "Quilla a Regala (Keel to Gunwale)"
        ficha.reversed_angle_irons_extension = "De línea de crujía a palmejar principal y secundario alternativamente (Middle line to Main Stringer and to Sp. on Stringer alternately)"
        ficha.reversed_angle_irons_machinery = "Hasta cubierta superior en cada cuaderna (To spar dk on every frame)"
        ficha.bulkheads_height_altura_mamparos = "Mamparo de colisión hasta cub. superior; resto hasta cub. principal (Collision Blkhd to Spar dk & others to Main dk)"
        
        # --- PLANCHAJE (REFINADO) ---
        ficha.plating_garboard_riveting_to_keel = "Doble remachado, 1 1/4\" diám., centros a 6\" (Double riveted, 1 1/4\" dia, 6\" centres)"
        
        # --- MÁSTILES (REFINADO) ---
        ficha.mast_fore_material = "Hierro y Pino (Iron & Pine)"
        ficha.mast_fore_length = "96.9 pies (96.9 ft)"
        ficha.mast_fore_dia = "27 pulgadas (27 in)"
        
        ficha.mast_main_material = "Hierro y Pino (Iron & Pine)"
        ficha.mast_main_length = "96.9 pies (96.9 ft)"
        ficha.mast_main_dia = "27 pulgadas (27 in)"
        
        ficha.mast_mizzen_material = "Pino (Pine)"
        ficha.mast_mizzen_length = "72.3 pies (72.3 ft)"
        ficha.mast_mizzen_dia = "22 pulgadas (22 in)"

        # --- CADENAS Y CABLES (REFINADO) ---
        ficha.cable_chain_length = "300 Brazas (300 Fathoms)"
        ficha.cable_chain_size = "2 1/8 pulgadas (2 1/8 in)"
        ficha.cable_chain_test = "81.5 Toneladas (81.5 Tons)"
        
        ficha.cable_towline_length = "120 Brazas - Cáñamo (120 Fathoms - Hemp)"
        ficha.cable_towline_size = "13 pulgadas (13 in)"
        
        ficha.cable_hawser_length = "90 Brazas (90 Fathoms)"
        ficha.cable_hawser_size = "11 pulgadas (11 in)"
        
        ficha.cable_warp_length = "90 Brazas (90 Fathoms)"
        ficha.cable_warp_size = "9 pulgadas (9 in)"

        # --- EXTRAS ---
        ficha.engine_room_skylights_const = "Teca sobre brazolas de hierro (Teak on iron comings)"
        ficha.boats_no_numero_botes = "5 Botes en total (3 salvavidas, 1 vapor, 1 gig)"
        
        db.session.commit()
        print("Refined data population complete!")

if __name__ == "__main__":
    refine_lloyds_data()
