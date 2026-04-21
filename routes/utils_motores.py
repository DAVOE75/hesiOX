"""
Secciones del Informe de Maquinaria Lloyd's Register Survey 1883 - S.S. Sirio
Lloyd's Report on Machinery No. 6147 - Glasgow, Junio 1883
Fabricante: R. Napier & Sons, Glasgow
"""

MOTORES_SECTIONS = [
    {
        "title": "I. ENCABEZADO DEL INFORME / MACHINERY REPORT HEADER",
        "fields": [
            ("motor_survey_no", "Nº Informe Maquinaria (Survey No.)"),
            ("motor_survey_held_at", "Inspección Realizada en (Survey Held At)"),
            ("motor_date_first_survey", "Fecha de Primera Inspección (Date of 1st Survey)"),
            ("motor_last_survey", "Última Inspección Maquinaria (Last Survey)"),
            ("motor_vessel_name", "Nombre del Buque (Vessel Name)"),
            ("motor_master", "Capitán (Master)"),
            ("motor_built_at", "Construido en (Built At)"),
            ("motor_when_built", "Año de Construcción (When Built)"),
            ("motor_engineers_by", "Ingenieros (Engineers)"),
            ("motor_boilers_by", "Fabricante de Calderas (Boilers By)"),
            ("motor_registered_horse_power", "Fuerza Nominal Registrada (Registered Horse Power)"),
            ("motor_owners", "Propietarios (Owners)"),
            ("motor_port", "Puerto de Matrícula (Port Belonging To)"),
        ],
        "description": "Datos de cabecera del Informe sobre Maquinaria (Report on Machinery) nº 6147 elaborado por el Lloyd's Register en Glasgow, Junio de 1883."
    },
    {
        "title": "II. MOTORES PRINCIPALES / MAIN ENGINES",
        "fields": [
            ("engine_type_tipo_motor", "Tipo de Motor / Engine Type"),
            ("engine_cylinder_diameter_diametro_cilindro", "Diámetro de Cilindros (mm) / Cylinder Diameter (in)"),
            ("engine_stroke_carrera", "Carrera del Émbolo (mm) / Stroke (in)"),
            ("engine_revolutions_revoluciones", "Revoluciones por minuto / Rev. Per Minute"),
            ("engine_high_pressure_alta_presion", "Presión Alta (bar) / High Pressure (psi)"),
            ("engine_low_pressure_baja_presion", "Presión Baja (bar) / Low Pressure (psi)"),
            ("engine_crankshaft_eje_cigüenal", "Diámetro Eje Cigüeñal (mm) / Crankshaft Diameter (in)"),
            ("engine_crankpin_munequilla", "Tamaño Muñequilla / Crankpin"),
            ("engine_journals_cojinetes", "Cojinetes del Eje / Journals"),
            ("engine_screw_shaft_eje_helice", "Diámetro Eje de Hélice (mm) / Screw Shaft (in)"),
            ("engine_pitch_of_screw_paso_helice", "Paso de Hélice (m) / Pitch of Screw (ft)"),
            ("engine_blades_palas", "Nº de Palas / No. of Blades"),
            ("engine_feathering_palas_articuladas", "Palas Articuladas / Feathering"),
        ],
        "description": "Especificaciones técnicas detalladas de los motores de vapor de acción directa (Direct Acting) que propulsaban el S.S. Sirio, fabricados por R. Napier & Sons de Glasgow. Motores de doble expansión con dos cilindros, uno de alta y uno de baja presión."
    },
    {
        "title": "III. BOMBAS / PUMPS",
        "fields": [
            ("pump_feed_numero_alimentacion", "Nº Bombas de Alimentación / Feed Pumps No."),
            ("pump_feed_diameter_diametro", "Diámetro Bomba Alimentación (mm) / Feed Pump Diameter (in)"),
            ("pump_feed_stroke_carrera", "Carrera Bomba de Alimentación (mm) / Feed Pump Stroke (in)"),
            ("pump_bilge_numero_achique", "Nº Bombas de Achique / Bilge Pumps No."),
            ("pump_bilge_diameter_diametro", "Diámetro Bomba de Achique (mm) / Bilge Pump Diameter (in)"),
            ("pump_separate_overhaul", "Bomba desmontable sin parar / One can be overhauled while at work"),
            ("pump_bilge_from", "Achique desde / Pump from (All Compartments)"),
            ("pump_donkey_engine", "Bomba auxiliar (Donkey Engine)"),
            ("pump_circulating_no", "Nº Bombas Circulación / Circulating Pumps No."),
            ("pump_circulating_type", "Tipo de Bombas / Pump Type (Centrifugal)"),
        ],
        "description": "Sistema de bombeo del buque: bombas de alimentación de calderas, bombas de achique para vaciado de sentinas y bombas circulantes para el sistema de condensación."
    },
    {
        "title": "IV. SISTEMA DE VAPOR Y FUNCIONAMIENTO / STEAM & OPERATION",
        "fields": [
            ("steam_pumps_worked_bombas_accionadas", "Accionamiento de Bombas / Pumps Worked (By Levers)"),
            ("steam_bilge_injections", "Nº Inyecciones de Achique / Bilge Injections"),
            ("steam_oil_connections", "Conexiones de aceite al costado / Oil Connections on Ship's Side"),
            ("steam_discharge_pipes", "Tuberías de descarga / Discharge Pipes Above/Below Waterline"),
            ("steam_discharge_valves", "Válvulas de descarga / Discharge Valves Fitted"),
            ("steam_blue_off_cocks", "Grifos Blue-off / Blue Off Cocks with Spigot"),
            ("steam_cargo_steam_pipes", "Vapor para carga / Steam to Cargo Pipes"),
            ("steam_protected_from", "Protección del calor / Protected From (Iron Casing)"),
            ("steam_oil_pipes_connected", "Aceites y tuberías conectadas / Oil Pipes Connected"),
            ("steam_pipes_cocks_valves", "Tuberías, grifos y válvulas / Pipes, Cocks and Valves"),
            ("steam_store_tube_propeller", "Ejes y hélice inspeccionados / Stern Tube, Propeller Examined"),
            ("steam_screw_shaft_watertight", "Eje estanco / Screw Shaft Watertight"),
            ("steam_working_platform", "Plataforma de trabajo / Working Platform"),
        ],
        "description": "Sistema de control del vapor, conexiones de aceite de maquinaria, disposición de tuberías y accesos de mantenimiento de la planta propulsora."
    },
    {
        "title": "V. CALDERAS PRINCIPALES / MAIN BOILERS",
        "fields": [
            ("boiler_no_numero", "Nº de Calderas / No. of Boilers"),
            ("boiler_description_descripcion", "Descripción de Calderas / Boiler Description"),
            ("boiler_working_pressure_presion_trabajo", "Presión de Trabajo (bar) / Working Pressure (psi)"),
            ("boiler_hydraulic_test_prueba_hidraulica", "Prueba Hidráulica (bar) / Hydraulic Test Pressure (psi)"),
            ("boiler_date_last_test_fecha_prueba", "Fecha Última Prueba / Date of Last Test"),
            ("boiler_superheating_sobrecalentamiento", "Aparato de Sobrecalentamiento / Superheating Apparatus"),
            ("boiler_worked_separately", "Calderas aislables / Can Each Boiler Work Separately"),
            ("boiler_superheater_separately", "Sobrecalentador aislable / Superheater Separately"),
            ("boiler_grate_surface_area", "Superficie de parrilla (m²) / No. Sq. Feet of Grate Surface"),
            ("boiler_each_boiler_grate", "Parrilla por caldera (m²) / Grate Surface Each Boiler"),
            ("boiler_safety_valves_description", "Descripción Válvulas de Seguridad / Safety Valves Description"),
            ("boiler_safety_valves_no", "Nº Válvulas de Seguridad / No. Safety Valves"),
            ("boiler_safety_valves_area", "Área Válvulas de Seguridad (cm²) / Safety Valves Area (sq in)"),
            ("boiler_safety_valves_with_easing_gear", "Válvulas con engranaje aliviador / With Easing Gear"),
        ],
        "description": "Especificaciones de las calderas tubulares horizontales (Round Horizontal) fabricadas por R. Napier & Sons. Las calderas del S.S. Sirio fueron probadas hidráulicamente a 200 psi el 19 de enero de 1883."
    },
    {
        "title": "VI. CONSTRUCCIÓN DE CALDERAS / BOILER CONSTRUCTION",
        "fields": [
            ("boiler_shell_distance_distancia", "Distancia entre calderas (mm) / Distance Between Boilers (in)"),
            ("boiler_shell_diameter_diametro", "Diámetro de la Virola (m) / Diameter of Boiler Shell (ft)"),
            ("boiler_shell_length_longitud", "Longitud de la Virola (m) / Length of Boiler Shell (ft)"),
            ("boiler_riveting_description", "Descripción del Remachado / Riveting of Shell Description"),
            ("boiler_shell_thickness_espesor_virola", "Espesor de la Virola (mm) / Shell Thickness (in)"),
            ("boiler_shell_riveted_pitch", "Paso del Remachado (mm) / Riveted Pitch (in)"),
            ("boiler_plates_thickness", "Espesor de Chapas (mm) / Plate Thickness (in)"),
            ("boiler_percentage_strength", "Porcentaje de Resistencia / % Strength of Joints"),
            ("boiler_working_pressure_by_rules", "Presión según Reglamento (bar) / Working Pressure by Rules (psi)"),
            ("boiler_rings_compressing", "Anillos de compresión / Compressing Rings"),
            ("boiler_manhole_size", "Tamaño de Registro (mm) / Manhole Size (in)"),
            ("boiler_furnaces_no", "Nº de Hogares / No. of Furnaces"),
            ("boiler_furnaces_outside_diameter", "Diámetro exterior de Hogar (mm) / Furnace Outside Diameter (in)"),
        ],
        "description": "Detalles constructivos de las calderas: materiales, espesores de virola, remachado y dimensiones de los hogares (furnaces) donde se genera la combustión."
    },
    {
        "title": "VII. TUBOS Y COLECTORES / TUBES & HEADERS",
        "fields": [
            ("tubes_diameter_diametro", "Diámetro de Tubos (mm) / Tube Diameter (in)"),
            ("tubes_pitch_paso", "Paso entre Tubos (mm) / Tube Pitch (in)"),
            ("tubes_plate_thickness_front", "Espesor Placa Frontal (mm) / Front Tube Plate Thickness (in)"),
            ("tubes_plate_thickness_back", "Espesor Placa Trasera (mm) / Back Tube Plate Thickness (in)"),
            ("tubes_water_spaces", "Espacios de agua (mm) / Water Spaces (in)"),
            ("tubes_superheater_steam_chest", "Colector de vapor / Superheater or Steam Chest"),
            ("combustion_chamber_stays_tirantes", "Tirantes de la Cámara de Combustión / Chamber Stays"),
            ("stays_in_each_furnace", "Tirantes por hogar / Stays in Each Furnace"),
            ("stays_diameter_diametro", "Diámetro de Tirantes (mm) / Stays Diameter (in)"),
            ("stays_length_longitud", "Longitud de Tirantes (mm) / Stays Length (in)"),
        ],
        "description": "Sistema de tubería interna de las calderas, incluyendo los tubos de vapor y agua cuyos parámetros determinan la eficiencia de transmisión de calor."
    },
    {
        "title": "VIII. HOGAR (FURNACE) / FURNACE DETAILS",
        "fields": [
            ("furnace_length_longitud", "Longitud del Hogar (mm) / Furnace Length (in)"),
            ("furnace_thickness_espesor", "Espesor del Hogar (mm) / Furnace Plate Thickness (in)"),
            ("furnace_pitch_of_rings", "Paso de Anillos (mm) / Pitch of Furnace Rings (in)"),
            ("furnace_description_corrugado", "Descripción (Corrugado/Plain) / Furnace Description"),
            ("furnace_working_pressure_by_rules", "Presión de Hogar según Reglamento / Furnace Working Pressure by Rules"),
            ("furnace_working_pressure_shell_by_rules", "Presión de Virola según Reglamento / Shell Working Pressure by Rules"),
        ],
        "description": "Especificaciones de los hogares (furnaces) de cada caldera: los cilindros corrugados de hierro que contienen la combustión del carbón y transmiten el calor al agua."
    },
    {
        "title": "IX. PLACAS FRONTALES Y TRASERAS / FRONT & BACK PLATES",
        "fields": [
            ("plate_stays_worked_by", "Tirantes accionados por / Stays Worked By (Iron Dogs)"),
            ("plate_combustion_chamber_thickness", "Espesor Cámara Combustión (mm) / Combustion Chamber Plate Thickness (in)"),
            ("plate_front_thickness", "Espesor Placa Frontal (mm) / Front Plate Thickness (in)"),
            ("plate_back_thickness", "Espesor Placa Trasera (mm) / Back Plate Thickness (in)"),
            ("plate_pitch_of_stays", "Paso de Tirantes (mm) / Pitch of Stays (in)"),
            ("plate_greatest_pitch_between", "Mayor Paso entre Tirantes / Greatest Pitch Between Stays"),
            ("plate_size_stays_at_smallest_part", "Tamaño Tirante Mínimo / Stays at Smallest Part"),
            ("plate_working_pressure_by_rules", "Presión de Placa según Reglamento / Plate Working Pressure by Rules"),
            ("plate_stays_are_secured_by", "Sujeción de Tirantes / Stays Are Secured By (Double Nuts)"),
        ],
        "description": "Detalles de las placas frontales y traseras de las calderas, incluyendo su sistema de tirantes y las presiones de trabajo admitidas según los reglamentos Lloyd's."
    },
    {
        "title": "X. CALDERA AUXILIAR (DONKEY BOILER) / DONKEY BOILER",
        "fields": [
            ("donkey_description", "Descripción / Donkey Boiler Description"),
            ("donkey_made_at", "Fabricado en / Made At"),
            ("donkey_by_whom", "Por quién / By Whom"),
            ("donkey_when_made", "Año de fabricación / When Made"),
            ("donkey_working_pressure", "Presión de Trabajo (bar) / Working Pressure (psi)"),
            ("donkey_hydraulic_test", "Prueba Hidráulica (bar) / Hydraulic Test Pressure (psi)"),
            ("donkey_certificate_no", "Nº de Certificado / Certificate No."),
            ("donkey_grate_area", "Área de Parrilla (m²) / Grate Area (sq ft)"),
            ("donkey_safety_valves_no", "Nº Válvulas de Seguridad / No. Safety Valves"),
            ("donkey_diameter", "Diámetro de la Caldera (mm) / Boiler Diameter (in)"),
            ("donkey_length", "Longitud de la Caldera (mm) / Boiler Length (in)"),
            ("donkey_riveting_description", "Descripción del Remachado / Riveting Description"),
            ("donkey_rivet_holes", "Taladros de Remaches / Rivet Holes (Punched/Drilled)"),
            ("donkey_pitch_of_rivets", "Paso de Remaches (mm) / Pitch of Rivets (in)"),
            ("donkey_lap_plating", "Solape de chapas / Lap of Plating (in)"),
            ("donkey_furnace_length", "Longitud del Hogar (mm) / Furnace Length (in)"),
            ("donkey_plates_thickness", "Espesor de Chapas (mm) / Plates Thickness (in)"),
            ("donkey_furnace_description", "Descripción del Hogar / Furnace Description (Welded)"),
            ("donkey_working_pressure_furnace", "Presión del Hogar (bar) / Furnace Working Pressure (psi)"),
            ("donkey_working_pressure_shell", "Presión de Virola (bar) / Shell Working Pressure (psi)"),
        ],
        "description": "Caldera auxiliar (Donkey Boiler) de hierro y acero, de tipo horizontal redondo, fabricada por R. Napier & Sons en 1883. Esta caldera auxiliar proveía vapor para las bombas de achique y otros servicios auxiliares del buque."
    },
    {
        "title": "XI. REMARQUES GENERALES / GENERAL REMARKS",
        "fields": [
            ("motor_manufacturer_firma", "Firma Fabricante / Manufacturer Signature"),
            ("motor_general_remarks", "Observaciones Generales / General Remarks"),
            ("motor_class_assigned", "Clase Asignada / Class Assigned"),
            ("motor_certificate_no", "Nº de Certificado / Certificate No."),
            ("motor_date_certificate", "Fecha del Certificado / Date of Certificate"),
            ("motor_entry_fee", "Tasa de Entrada / Amount of Entry Fee"),
            ("motor_surveyor_signature", "Firma del Inspector / Surveyor Signature"),
            ("motor_surveyor_district", "Distrito del Inspector / Surveyor District"),
        ],
        "description": "Evaluación final del inspector Lloyd's sobre el estado de los motores y calderas del S.S. Sirio. Según el documento original: 'The Engines & Boilers of this vessel are of good workmanship and are now in good order and safe working condition and in our opinion eligible to be noted in the Register Books. Lloyd's M.C.6.83'"
    }
]
