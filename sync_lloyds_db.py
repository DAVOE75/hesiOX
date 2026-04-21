import os
import psycopg2
from dotenv import load_dotenv

load_dotenv('/opt/hesiox/.env')
db_url = os.getenv('DATABASE_URL')

# Reemplazar postgresql+psycopg2 con postgresql para psycopg2.connect
db_url = db_url.replace('postgresql+psycopg2://', 'postgresql://')

fields = [
    # 1. HEADER
    "survey_no_numero_inspeccion", "survey_held_at_inspeccion_en", "date_first_survey_fecha_primera_inspeccion",
    "last_survey_ultima_inspeccion", "vessel_type_tipo_buque", "master_capitan", "built_at_construido_en",
    "when_built_cuando_construido", "by_whom_built_por_quien_construido", "owners_propietarios",
    "port_belonging_puerto_pertenencia", "destined_voyage_viaje_destinado",
    # 2. TONNAGE/DIMENSIONS
    "gross_tonnage_tonelaje_bruto", "net_tonnage_tonelaje_neto", "length_overall_eslora_total",
    "length_between_pp_eslora_entre_pp", "breadth_extreme_manga_maxima", "depth_of_hold_puntal_bodega",
    "depth_moulded_puntal_de_construccion",
    # 3. STRUCTURE
    "keel_material_material_quilla", "keel_size_dimension_quilla", "stem_material_material_roda",
    "stem_size_dimension_roda", "stern_post_material_material_codaste", "stern_post_size_dimension_codaste",
    "frames_material_material_cuadernas", "frames_spacing_espaciado_cuadernas", "frames_size_dimension_cuadernas",
    "reverse_frames_reves_cuadernas", "floors_material_material_varengas", "floors_size_dimension_varengas",
    "floors_thickness_espesor_varengas",
    # 4. KEELSONS & STRINGERS
    "keelsons_main_sobrequilla_principal", "keelsons_intercostal_sobrequilla_intercostal",
    "side_keelsons_sobrequillas_laterales", "bilge_keelsons_sobrequillas_pantoque",
    "bilge_stringers_palmejares_pantoque", "side_stringers_palmejares_laterales",
    # 5. BEAMS & DECKS
    "upper_deck_beams_baos_cubierta_superior", "main_deck_beams_baos_cubierta_principal",
    "lower_deck_beams_baos_cubierta_inferior", "deck_material_material_cubiertas", "deck_thickness_espesor_cubiertas",
    # 6. PLATING
    "plating_garboard_strakes_tracas_aparadura", "plating_bottom_strakes_tracas_fondo",
    "plating_bilge_strakes_tracas_pantoque", "plating_side_strakes_tracas_costado",
    "plating_sheer_strakes_tracas_cinta", "plating_upper_works_obras_muertas",
    # 7. RIVETING
    "riveting_keel_remachado_quilla", "riveting_stem_remachado_roda", "riveting_butts_remachado_topes",
    "riveting_edges_remachado_costuras", "riveting_size_diametro_remaches",
    # 8. BULKHEADS
    "bulkheads_no_numero_mamparos", "bulkheads_height_altura_mamparos", "bulkheads_thickness_espesor_mamparos",
    "water_tight_doors_puertas_estancas",
    # 9. EQUIPMENT
    "masts_no_numero_mastiles", "rigging_type_tipo_aparejo", "sails_velas", "boats_no_numero_botes",
    "anchors_no_numero_anclas", "anchors_weight_peso_anclas", "cables_length_longitud_cadenas",
    "pumps_no_numero_bombas",
    # 10. ENGINES & BOILERS
    "engine_type_tipo_maquina", "engine_hp_caballos_maquina", "boilers_no_numero_calderas",
    "boilers_pressure_presion_calderas", "boilers_material_material_calderas", "propeller_type_tipo_helice",
    # 11. REMARKS
    "general_remarks_observaciones_generales", "class_assigned_clase_asignada", "date_of_class_fecha_clase",
    "surveyor_signature_firma_inspector"
]

try:
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()
    
    # Asegurar que la tabla existe primero (aunque ya debería estar)
    cur.execute("CREATE TABLE IF NOT EXISTS lloyds_register_survey_inspeccion_absoluta (id SERIAL PRIMARY KEY);")
    
    for field in fields:
        col_type = "TEXT" if "remarks" in field else "VARCHAR(255)"
        sql = f"ALTER TABLE lloyds_register_survey_inspeccion_absoluta ADD COLUMN IF NOT EXISTS {field} {col_type};"
        print(f"Agregando columna: {field}")
        cur.execute(sql)
    
    # Asegurar propiedad
    cur.execute("ALTER TABLE lloyds_register_survey_inspeccion_absoluta OWNER TO hesiox_user;")
    
    conn.commit()
    cur.close()
    conn.close()
    print("✅ Base de datos actualizada con éxito.")
except Exception as e:
    print(f"❌ Error: {e}")
