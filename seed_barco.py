import os
import sys

# Añadir el directorio del proyecto al path para importar modelos
sys.path.append('/opt/hesiox')

from app import app
from models import db, LloydsFicha, SirioPuntoInteractivo

def seed_data():
    with app.app_context():
        # 1. Borrar datos previos si existen (opcional, para limpieza)
        # db.session.query(LloydsFicha).delete()
        # db.session.query(SirioPuntoInteractivo).delete()
        
        # 2. Crear Ficha de Lloyd's (1883)
        if not LloydsFicha.query.first():
            ficha = LloydsFicha(
                survey_no_numero_inspeccion="6147",
                survey_held_at_inspeccion_en="Glasgow",
                date_first_survey_fecha_primera_inspeccion="April 1883",
                last_survey_ultima_inspeccion="June 1883",
                vessel_type_tipo_buque="Steel Screw Steamer",
                master_capitan="G. Gaggino",
                built_at_construido_en="Govan, Glasgow",
                when_built_cuando_construido="1883",
                by_whom_built_por_quien_construido="Robert Napier & Sons",
                owners_propietarios="Società di Navigazione Generale Italiana",
                port_belonging_puerto_pertenencia="Genoa",
                destined_voyage_viaje_destinado="South America",
                
                gross_tonnage_tonelaje_bruto="4141",
                net_tonnage_tonelaje_neto="2656",
                length_overall_eslora_total="391.0 ft",
                length_between_pp_eslora_entre_pp="115.82 m",
                breadth_extreme_manga_maxima="42.2 ft",
                depth_of_hold_puntal_bodega="25.5 ft",
                depth_moulded_puntal_de_construccion="34.2 ft",
                
                keel_material_material_quilla="Steel",
                keel_size_dimension_quilla="10 x 2 1/2 in",
                stem_material_material_roda="Steel",
                frames_material_material_cuadernas="Steel Angle",
                frames_spacing_espaciado_cuadernas="24 in",
                
                engine_type_tipo_maquina="Triple Expansion 3-Cylinder",
                engine_hp_caballos_maquina="600 NHP",
                boilers_no_numero_calderas="4 Double Ended",
                boilers_pressure_presion_calderas="100 lbs",
                propeller_type_tipo_helice="Single Screw, 4 blades",
                
                general_remarks_observaciones_generales="The vessel is strongly built and well subdivided with 7 bulkheads. Machinery by Robert Napier & Sons.",
                class_assigned_clase_asignada="100 A1",
                date_of_class_fecha_clase="12th June 1883",
                surveyor_signature_firma_inspector="James Mollison"
            )
            db.session.add(ficha)
            print("Ficha Lloyd's 1883 creada.")

        # 3. Crear Puntos SIG Interactivos (Ejemplos)
        # Basados en una imagen de 4000x2000px
        puntos_ejemplo = [
            {
                "nombre": "Sala de Máquinas (Engine Room)",
                "categoria": "Maquinaria",
                "descripcion": "Contiene la máquina de triple expansión de 600 NHP y las calderas escocesas.",
                "x": 1950, "y": 900,
                "coordenadas": [[950, 1800], [950, 2100], [800, 2100], [800, 1800]],
                "icono": "fa-gears"
            },
            {
                "nombre": "Salón de 1ª Clase (Dining Saloon)",
                "categoria": "Salones",
                "descripcion": "Gran salón comedor decorado en estilo italiano con capacidad para 80 comensales.",
                "x": 2500, "y": 600,
                "coordenadas": [[550, 2300], [550, 2700], [650, 2700], [650, 2300]],
                "icono": "fa-utensils"
            },
            {
                "nombre": "Puente de Mando (The Bridge)",
                "categoria": "Cubierta",
                "descripcion": "Estación de mando superior con el telégrafo de máquinas y timón principal.",
                "x": 1500, "y": 550,
                "coordenadas": [[530, 1450], [530, 1550], [580, 1550], [580, 1450]],
                "icono": "fa-compass"
            },
            {
                "nombre": "Alojamiento Emigrantes (Third Class)",
                "categoria": "Alojamiento",
                "descripcion": "Dormitorios compartidos para pasajeros de tercera clase (emigrantes) en proa y popa.",
                "x": 1000, "y": 950,
                "coordenadas": [[900, 500], [900, 1500], [1050, 1500], [1050, 500]],
                "icono": "fa-users"
            },
            {
                "nombre": "Pañol de Carga No. 1 (Cargo Hold)",
                "categoria": "Carga",
                "descripcion": "Bodega delantera destinada a equipaje pesado y suministros para la travesía atlántica.",
                "x": 3200, "y": 980,
                "coordenadas": [[900, 3000], [900, 3500], [1050, 3500], [1050, 3000]],
                "icono": "fa-boxes-stacked"
            }
        ]

        if SirioPuntoInteractivo.query.count() == 0:
            for p_data in puntos_ejemplo:
                p = SirioPuntoInteractivo(**p_data)
                db.session.add(p)
            print("Puntos SIG de ejemplo creados.")

        db.session.commit()
        print("Commit realizado con éxito.")

if __name__ == "__main__":
    seed_data()
