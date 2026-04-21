import os
import sys

# Añadir el path del proyecto para importar app y models
sys.path.append('/opt/hesiox')

from app import app
from models import db, LloydsFicha

def populate_lloyds():
    with app.app_context():
        # Verificamos si ya existe para no duplicar (basado en el survey_no o simplemente vaciando si es necesario)
        existing = LloydsFicha.query.filter_by(survey_no_numero_inspeccion="6147").first()
        if existing:
            print("Ya existe un registro con el Nº de Inspección 6147. Actualizando...")
            ficha = existing
        else:
            print("Creando nuevo registro exhaustivo de Lloyd's Survey Nº 6147...")
            ficha = LloydsFicha()
        
        # 1. ENCABEZADO Y DATOS GENERALES
        ficha.survey_no_numero_inspeccion = "6147"
        ficha.survey_held_at_inspeccion_en = "Glasgow"
        ficha.date_first_survey_fecha_primera_inspeccion = "June 5th 1882"
        ficha.last_survey_ultima_inspeccion = "June 16th 1883"
        ficha.vessel_type_tipo_buque = "Iron Steam Ship / Two Decked (Spar Decked)"
        ficha.master_capitan = "P. G. Pagliano"
        ficha.built_at_construido_en = "Glasgow"
        ficha.when_built_cuando_construido = "1882-3 (Launched Mar. 24, 1883)"
        ficha.by_whom_built_por_quien_construido = "Robert Napier & Sons"
        ficha.owners_propietarios = "Melpro Piaggio & Co."
        ficha.port_belonging_puerto_pertenencia = "Genoa"
        ficha.destined_voyage_viaje_destinado = "Genoa"

        # 2. TONELAJE Y DIMENSIONES
        ficha.gross_tonnage_tonelaje_bruto = "3823.83"
        ficha.net_tonnage_tonelaje_neto = "2400.65"
        ficha.length_overall_eslora_total = "378.33"
        ficha.length_between_pp_eslora_entre_pp = "380 Registro / 378.33 Construcción"
        ficha.breadth_extreme_manga_maxima = "42.08"
        ficha.depth_of_hold_puntal_bodega = "32.65"
        ficha.depth_moulded_puntal_de_construccion = "27.04 (to top of upper deck beams)"

        # 3. ESTRUCTURA (QUILAS, RODA, CUADERNAS)
        ficha.keel_material_material_quilla = "Iron (Solid)"
        ficha.keel_size_dimension_quilla = "9 1/2 x 3 1/4"
        ficha.stem_material_material_roda = "Iron (Forged)"
        ficha.stem_size_dimension_roda = "9 1/2 x 3 1/4"
        ficha.stern_post_material_material_codaste = "Iron (Forged)"
        ficha.stern_post_size_dimension_codaste = "9 1/2 x 4 1/2"
        ficha.frames_material_material_cuadernas = "Steel / Angle Iron"
        ficha.frames_spacing_espaciado_cuadernas = "24 inches (centre to centre)"
        ficha.frames_size_dimension_cuadernas = "5 x 3 1/2 x 9/16"
        ficha.reverse_frames_reves_cuadernas = "3 1/2 x 3 1/2 x 7/16"
        ficha.floors_material_material_varengas = "Steel Plate"
        ficha.floors_size_dimension_varengas = "26 x 13/32 at mid line"
        ficha.floors_thickness_espesor_varengas = "13/32"

        # 4. SOBREQUILLAS Y PALMEJARES
        ficha.keelsons_main_sobrequilla_principal = "13 x 15/32 (Bulb Plate)"
        ficha.keelsons_intercostal_sobrequilla_intercostal = "Intercostal Plate 10/32"
        ficha.side_keelsons_sobrequillas_laterales = "Double Angle 6 x 4 x 9/16"
        ficha.bilge_keelsons_sobrequillas_pantoque = "18 x 14/32"
        ficha.bilge_stringers_palmejares_pantoque = "Double Angle 6 x 4 x 9/16"
        ficha.side_stringers_palmejares_laterales = "7 x 5 x 10/32"

        # 5. BAOS Y CUBIERTAS
        ficha.upper_deck_beams_baos_cubierta_superior = "7 1/2 x 4 1/2 x 9/16"
        ficha.main_deck_beams_baos_cubierta_principal = "9 x 5 x 9/16"
        ficha.lower_deck_beams_baos_cubierta_inferior = "10 x 6 x 14/32"
        ficha.deck_material_material_cubiertas = "Yellow Pine (Upper) / Iron (Main)"
        ficha.deck_thickness_espesor_cubiertas = "4\" (Upper) / 10/32 (Main)"

        # 6. PLANCHAJE EXTERIOR
        ficha.plating_garboard_strakes_tracas_aparadura = "18/32 to 16/32 at ends"
        ficha.plating_bottom_strakes_tracas_fondo = "16/32 to 14/32 at ends"
        ficha.plating_bilge_strakes_tracas_pantoque = "17/32 (Double for 1/2 length)"
        ficha.plating_side_strakes_tracas_costado = "15/32 to 13/32 at ends"
        ficha.plating_sheer_strakes_tracas_cinta = "18/32 to 16/32 at ends"
        ficha.plating_upper_works_obras_muertas = "14/32 (Steel)"

        # 7. REMACHADO Y FIJACIONES
        ficha.riveting_keel_remachado_quilla = "Double riveted, 1 1/4 diameter"
        ficha.riveting_stem_remachado_roda = "Double riveted, 1 1/4 diameter"
        ficha.riveting_butts_remachado_topes = "Treble riveted for 2/3 length amdiships"
        ficha.riveting_edges_remachado_costuras = "Double riveted throughout"
        ficha.riveting_size_diametro_remaches = "7/8 amdiships, 3/4 at ends"

        # 8. MAMPAROS Y ESTANQUEIDAD
        ficha.bulkheads_no_numero_mamparos = "8 bulkheads"
        ficha.bulkheads_height_altura_mamparos = "Extending to Spar Deck (Collision) / Main Deck"
        ficha.bulkheads_thickness_espesor_mamparos = "10/32 to 8/32"
        ficha.water_tight_doors_puertas_estancas = "Water-tight doors fitted on Main Deck"

        # 9. EQUIPAMIENTO (MÁSTILES, ANCLAS, BOTES)
        ficha.masts_no_numero_mastiles = "2 Masts (Steel)"
        ficha.rigging_type_tipo_aparejo = "Brig Rigged"
        ficha.sails_velas = "Full suit of sails including Fore, Main, Staysails"
        ficha.boats_no_numero_botes = "7 Boats (6 Lifeboats, 1 Gig, 1 Cutter)"
        ficha.anchors_no_numero_anclas = "3 Bower, 1 Stream, 1 Kedge"
        ficha.anchors_weight_peso_anclas = "Bower: 43 1/2 cwt, 41 cwt, 38 cwt"
        ficha.cables_length_longitud_cadenas = "300 Fathoms of 2 1/8 iron chain"
        ficha.pumps_no_numero_bombas = "5 Pumps (Double acting)"

        # 10. MÁQUINAS Y CALDERAS
        ficha.engine_type_tipo_maquina = "Compound Inverted Surface Condensing"
        ficha.engine_hp_caballos_maquina = "850 Nominal Horse Power"
        ficha.boilers_no_numero_calderas = "3 Steel Boilers"
        ficha.boilers_pressure_presion_calderas = "80 lbs per sq. inch"
        ficha.boilers_material_material_calderas = "Steel"
        ficha.propeller_type_tipo_helice = "Forged Iron Propeller (4 blades)"

        # 11. OBSERVACIONES E INSPECCIÓN
        ficha.general_remarks_observaciones_generales = (
            "This is a Spar decked vessel built under special survey in accordance with the Rules and plans submitted. "
            "The ballast tanks were tested prior to launching and found satisfactory. The collision bulkhead was also "
            "tested by filling the forepeak with water to the height of the main deck and proved to be tight. "
            "Materials and workmanship good."
        )
        ficha.class_assigned_clase_asignada = "100 A1"
        ficha.date_of_class_fecha_clase = "June 15th 1883"
        ficha.surveyor_signature_firma_inspector = "B. G. Davidson / R. Napier & Sons"

        if not existing:
            db.session.add(ficha)
        db.session.commit()
        print("✅ Ficha S.S. Sirio poblada con éxito desde el Lloyd's Survey.")

if __name__ == "__main__":
    populate_lloyds()
