LLOYDS_SECTIONS = [
    {
        "title": "I. ENCABEZADO Y DATOS GENERALES / HEADER & GENERAL DATA",
        "fields": [
            ("survey_no_numero_inspeccion", "Nº de Inspección (Survey No.)"),
            ("survey_held_at_inspeccion_en", "Inspección Realizada en (Survey Held At)"),
            ("date_first_survey_fecha_primera_inspeccion", "Fecha de Primera Inspección (Date of 1st Survey)"),
            ("last_survey_ultima_inspeccion", "Última Inspección (Last Survey)"),
            ("vessel_type_tipo_buque", "Tipo de Buque (Vessel Type)"),
            ("master_capitan", "Capitán (Master)"),
            ("built_at_construido_en", "Construido en (Built At)"),
            ("when_built_cuando_construido", "Año de Construcción (When Built)"),
            ("by_whom_built_por_quien_construido", "Constructor (By Whom Built)"),
            ("owners_propietarios", "Propietarios (Owners)"),
            ("port_belonging_puerto_pertenencia", "Puerto de Matrícula (Port Belonging To)"),
            ("destined_voyage_viaje_destinado", "Viaje Destinado (Destined Voyage)"),
            ("launched_lanzado", "Fecha de Botadura (Launched)"),
            ("owners_residence_residencia_propietarios", "Residencia de Propietarios (Residence)")
        ],
        "description": "Datos generales de la inspección de 1883 realizada en Glasgow para la naviera Raggio & Co."
    },
    {
        "title": "II. TONELAJE Y DIMENSIONES / TONNAGE & DIMENSIONS",
        "fields": [
            ("tonnage_under_deck_tonelaje_bajo_cubierta", "Tonelaje bajo Cubierta (Tonnage under Deck)"),
            ("tonnage_third_deck_tonelaje_tercera_cubierta", "Tonelaje 3ª Cubierta o Toldo (3rd, Spar, or Awning Deck)"),
            ("tonnage_houses_on_deck_tonelaje_casetas", "Tonelaje de Casetas en Cubierta (Houses on Deck)"),
            ("tonnage_forecastle_tonelaje_castillo_proa", "Tonelaje de Castillo de Proa (Forecastle)"),
            ("gross_tonnage_tonelaje_bruto", "Tonelaje Bruto (Gross Tonnage)"),
            ("less_crew_space_menos_espacio_tripulacion", "Deducción por Espacio de Tripulación (Less Crew Space)"),
            ("less_engine_room_menos_sala_maquinas", "Deducción por Sala de Máquinas (Less Engine Room)"),
            ("register_tonnage_tonelaje_registro", "Tonelaje de Registro (Register Tonnage as out on Beam)"),
            ("net_tonnage_tonelaje_neto", "Tonelaje Neto (Net Tonnage)"),
            ("length_overall_eslora_total", "Eslora Total (Length Overall)"),
            ("length_between_pp_eslora_entre_pp", "Eslora entre Perpendiculares (Length Between P.P.)"),
            ("breadth_extreme_manga_maxima", "Manga Máxima (Breadth Extreme)"),
            ("depth_of_hold_puntal_bodega", "Puntal de Bodega (Depth Of Hold)"),
            ("depth_keel_to_main_deck_puntal_quilla_cubierta", "Puntal Quilla a Cubierta Ppal. (Depth Keel to Main Deck)"),
            ("half_breadth_moulded_media_manga", "Media Manga Moldeada (Half Breadth moulded)"),
            ("girth_half_midship_frame_perimetro_media_cuaderna", "Perímetro Media Cuaderna Maestra (Girth of Half Midship Frame)"),
            ("first_number_primer_numero", "Primer Número (1st Number)"),
            ("second_number_segundo_numero", "Segundo Número (2nd Number)"),
            ("proportions_breadths_to_length_proporcion_manga_eslora", "Proporción Manga a Eslora (Proportions - Breadths to Length)"),
            ("proportions_depths_to_length_upper_proporcion_puntal_eslora_sup", "Proporc. Puntal a Eslora Sup. (Depths to Length - Upper Deck)"),
            ("proportions_depths_to_length_main_proporcion_puntal_eslora_ppal", "Proporc. Puntal a Eslora Ppal. (Depths to Length - Main Deck)")
        ],
        "description": "<p class=\"mb-3\">Análisis de lo que significa cada línea y la matemática oculta que las relaciona (las medidas están en pies, feet):</p><ol class=\"ps-3\"><li><strong>El tipo de barco:</strong><br>\"THREE DECKED VESSEL\" (Buque de tres cubiertas): En la parte superior, el inspector ha tachado opciones como \"una o dos cubiertas\" y ha dejado claro que es un buque de tres cubiertas.</li><li class=\"mt-3\"><strong>Las medidas básicas (Sección transversal):</strong><ul class=\"small mt-2\"><li><em>Half Breadth (moulded) - 21.04:</em> Es la semimanga moldeada (mitad de la anchura máxima interior). Manga total aprox. 42 pies (12,8 metros).</li><li><em>Depth... to top of Main Deck Beams - 27.04:</em> Es el puntal (profundidad vertical desde quilla a cubierta principal).</li><li><em>Girth of Half Midship Frame - 42.54:</em> Es el perímetro de la semicuaderna maestra (longitud de la curva desde quilla a cubierta).</li></ul></li><li class=\"mt-3\"><strong>Los coeficientes de construcción:</strong><ul class=\"small mt-2\"><li><em>1st Number (Primer Número) - 90.62:</em> \"Número Transversal\", dicta el grosor del esqueleto. Suma de las tres medidas anteriores: 21.04+27.04+42.54 = 90.62.</li><li><em>Length - 378.33:</em> La eslora (longitud) del barco (aprox. 115 metros).</li><li><em>2nd Number (Segundo Número) - 34.284:</em> \"Número Longitudinal\", dicta el grosor del casco. Es el Primer Número por la longitud: 90.62 × 378.33 ≈ 34.284.</li></ul></li><li class=\"mt-3\"><strong>Las proporciones (Proportions):</strong><ul class=\"small mt-2\"><li><em>Breadths to Length - 8.99:</em> Relación longitud/manga. El barco era casi 9 veces más largo que ancho.</li><li><em>Depths to Length (Main Deck) - 13.99:</em> Relación longitud/profundidad (378.33 / 27.04 = 13.99).</li></ul></li></ol><p class=\"mt-3 small border-top pt-2 opacity-75\">En resumen, estás viendo \"el ADN matemático\" que un ingeniero naval usó hace más de un siglo para certificar la solidez necesaria del S.S. Sirio.</p>"
    },
    {
        "title": "III. ESTRUCTURA (QUILLAS, RODA, CUADERNAS) / HULL STRUCTURE",
        "fields": [
            ("keel_material_material_quilla", "Material de la Quilla / Keel Material"),
            ("keel_size_dimension_quilla", "Dimensión de la Quilla (mm) / Keel Size (in)"),
            ("stem_material_material_roda", "Material de la Roda / Stem Material"),
            ("stem_size_dimension_roda", "Dimensión de la Roda (mm) / Stem Size (in)"),
            ("stern_post_material_material_codaste", "Material del Codaste / Stern Post Material"),
            ("stern_post_size_dimension_codaste", "Dimensión del Codaste (mm) / Stern Post Size (in)"),
            ("frames_material_material_cuadernas", "Material de Cuadernas / Frames Material"),
            ("frames_extension_from_to", "Extensión de Cuadernas / Frames Extension (from/to)"),
            ("frames_spacing_espaciado_cuadernas", "Espaciado de Cuadernas (mm) / Frames Spacing (in)"),
            ("frames_size_dimension_cuadernas", "Dimensión de Cuadernas (mm) / Frames Size (in)"),
            ("frames_riveted_rivets_size", "Remachado de Cuadernas (mm) / Frame Riveting (size/dist)"),
            ("reverse_frames_reves_cuadernas", "Angulares Inversos / Reverse Frames"),
            ("reversed_angle_irons_extension", "Extensión Angulares Inversos / R.A.I. Extension"),
            ("reversed_angle_irons_machinery", "R.A.I. en Sala de Máquinas / R.A.I. in Machinery Space"),
            ("floors_material_material_varengas", "Material de Varengas / Floors Material"),
            ("floors_size_dimension_varengas", "Dimensión de Varengas (mm) / Floors Size (in)"),
            ("floors_thickness_espesor_varengas", "Espesor de Varengas (mm) / Floors Thickness (in)")
        ],
        "description": "Detalles del armazón estructural del buque, incluyendo la quilla (columna vertebral), roda y codaste, junto con el espaciado crítico de las cuadernas."
    },
    {
        "title": "IV. SOBREQUILLAS Y PALMEJARES / KEELSONS & STRINGERS",
        "fields": [
            ("keelsons_main_sobrequilla_principal", "Sobrequilla Principal / Main Keelson"),
            ("keelsons_intercostal_sobrequilla_intercostal", "Sobrequilla Intercostal / Intercostal Keelson"),
            ("side_keelsons_sobrequillas_laterales", "Sobrequillas Laterales / Side Keelsons"),
            ("bilge_keelsons_sobrequillas_pantoque", "Sobrequillas de Pantoque / Bilge Keelsons"),
            ("bilge_stringers_palmejares_pantoque", "Palmejares de Pantoque / Bilge Stringers"),
            ("side_stringers_palmejares_laterales", "Palmejares Laterales / Side Stringers"),
            ("keelsons_connected_butts", "Conexión de Topes y Desplazamiento / Keelsons Butts & Shift")
        ],
        "description": "Elementos de refuerzo longitudinal que proporcionan rigidez al fondo y los costados del casco contra esfuerzos de flexión."
    },
    {
        "title": "V. BAOS Y CUBIERTAS / BEAMS & DECKS",
        "fields": [
            ("upper_deck_beams_baos_cubierta_superior", "Baos Cubierta Superior (mm) / Upper Deck Beams (in)"),
            ("main_deck_beams_baos_cubierta_principal", "Baos Cubierta Principal (mm) / Main Deck Beams (in)"),
            ("lower_deck_beams_baos_cubierta_inferior", "Baos Cubierta Inferior (mm) / Lower Deck Beams (in)"),
            ("deck_material_material_cubiertas", "Material de Cubiertas / Deck Material"),
            ("deck_thickness_espesor_cubiertas", "Espesor de Cubiertas (mm) / Deck Thickness (in)")
        ],
        "description": "Soportes transversales (baos) y superficies horizontales que dividen el buque y garantizan su integridad estructural y estanqueidad."
    },
    {
        "title": "VI. PLANCHAJE EXTERIOR (DETALLADO) / DETAILED PLATING",
        "fields": [
            ("plating_garboard_riveting_to_keel", "Remachado Aparadura-Quilla / Riveting Garboard to Keel"),
            ("plating_garboard_edges_riveting", "Remachado Cantos Aparadura / Garboard Edges Riveting"),
            ("plating_bilge_butts_thickness", "Grosor Topes de Pantoque (mm) / Bilge Butts Thickness (in)"),
            ("plating_side_edges_riveting", "Remachado Cantos de Costado / Side Edges Riveting"),
            ("plating_side_butts_riveting", "Remachado Topes de Costado / Side Butts Riveting"),
            ("plating_sheerstrake_edges", "Remachado Cantos de Cinta / Sheerstrake Edges"),
            ("plating_sheerstrake_butts", "Remachado Topes de Cinta / Sheerstrake Butts"),
            ("plating_spar_sheerstrake_butts", "Remachado Topes Cinta Superior / Spar Sheerstrake Butts"),
            ("plating_stringer_plate_butts", "Topes Plancha Palmejar / Stringer Plate Butts"),
            ("plating_spar_stringer_plate_butts", "Topes Palmejar Superior / Spar Stringer Butts"),
            ("plating_laps_breadth_double", "Ancho Solapes Dobles (mm) / Double Laps Breadth (in)"),
            ("plating_laps_breadth_single", "Ancho Solapes Simples (mm) / Single Laps Breadth (in)"),
            ("butt_straps_riveted_type", "Tipo de Remachado en Cubrejuntas / Butt Straps Riveting Type")
        ],
        "description": "Especificación detallada de la piel exterior del buque (planchado) y la compleja técnica de remachado que garantiza su solidez."
    },
    {
        "title": "VII. CALIDAD DE OBRA / WORKMANSHIP",
        "fields": [
            ("workmanship_plating_butts", "Ajuste de Topes del Planchaje / Plating Butts Fit"),
            ("workmanship_carvel_edges", "Ajuste de Cantos de Tingladillo / Carvel Edges Fit"),
            ("workmanship_fillings_solid", "Rellenos en Pieza Única / Solid Fillings"),
            ("workmanship_riveting_holes", "Correspondencia de Taladros / Riveting Holes Fit"),
            ("workmanship_riveting_countersunk", "Avellanado de Taladros / Countersunk Holes"),
            ("workmanship_rivets_break", "Rotura de Remaches / Rivets Break Condition")
        ],
        "description": "Evaluación de la pericia artesanal en el ensamblaje, el ajuste de las planchas y la precisión del remachado, factores críticos para la longevidad del buque."
    },
    {
        "title": "VIII. MAMPAROS / BULKHEADS",
        "fields": [
            ("bulkheads_no_numero_mamparos", "Nº de Mamparos Estancos / No. of Watertight Bulkheads"),
            ("bulkheads_height_altura_mamparos", "Altura de Mamparos (m) / Height of Bulkheads (ft)"),
            ("bulkheads_thickness_espesor_mamparos", "Espesor de Mamparos (mm) / Bulkheads Thickness (in)"),
            ("water_tight_doors_puertas_estancas", "Puertas Estancas / Water-tight Doors"),
            ("breasthooks_no", "Nº de Buzardas / Breasthooks No."),
            ("crutches_no", "Nº de Escobas de Popa / Crutches No.")
        ],
        "description": "Divisiones verticales internas que crean compartimentos estancos, vitales para la flotabilidad en caso de vía de agua."
    },
    {
        "title": "IX. MÁSTILES Y APAREJO / MASTS & RIGGING",
        "fields": [
            ("masts_no_numero_mastiles", "Nº de Mástiles / Masts No."),
            ("rigging_type_tipo_aparejo", "Tipo de Aparejo / Rigging Type"),
            ("rigging_standing_running", "Jarcia Fija y de Labor / Standing & Running Rigging"),
            ("rigging_quality", "Calidad de Jarcia y Cables / Rigging Quality"),
            ("sails_velas", "Estado de las Velas / Sails Condition"),
            ("mast_fore_material", "Material Palo Trinquete / Foremast Material"),
            ("mast_fore_length", "Longitud Trinquete (m) / Foremast Length (ft)"),
            ("mast_fore_dia", "Diámetro Trinquete (mm) / Foremast Diameter (in)"),
            ("mast_main_material", "Material Palo Mayor / Mainmast Material"),
            ("mast_main_length", "Longitud Palo Mayor (m) / Mainmast Length (ft)"),
            ("mast_main_dia", "Diámetro Palo Mayor (mm) / Mainmast Diameter (in)"),
            ("mast_mizzen_material", "Material Palo Mesana / Mizzenmast Material"),
            ("mast_mizzen_length", "Longitud Palo Mesana (m) / Mizzenmast Length (ft)"),
            ("mast_mizzen_dia", "Diámetro Palo Mesana (mm) / Mizzenmast Diameter (in)"),
            ("sails_full_set", "Juego Completo de Velas / Sails Full Set")
        ],
        "description": "Especificaciones de la arboladura y el velamen del buque, que servían como propulsión auxiliar y estabilización."
    },
    {
        "title": "X. EQUIPAMIENTO DE CUBIERTA / DECK EQUIPMENT",
        "fields": [
            ("anchors_no_numero_anclas", "Nº Anclas de Leva / Bower Anchors No."),
            ("anchors_weight_peso_anclas", "Peso Total Anclas (kg) / Total Anchor Weight (cwt)"),
            ("anchor_bower_1_weight", "Peso Ancla Leva 1 (kg) / Bower 1 Weight (cwt)"),
            ("anchor_bower_2_weight", "Peso Ancla Leva 2 (kg) / Bower 2 Weight (cwt)"),
            ("anchor_bower_3_weight", "Peso Ancla Leva 3 (kg) / Bower 3 Weight (cwt)"),
            ("anchor_stream_weight", "Peso Anclote (kg) / Stream Anchor Weight (cwt)"),
            ("anchor_kedge_1_weight", "Peso Ancla Espía 1 (kg) / Kedge 1 Weight (cwt)"),
            ("anchor_kedge_2_weight", "Peso Ancla Espía 2 (kg) / Kedge 2 Weight (cwt)"),
            ("windlass_type", "Tipo de Molinete / Windlass Type"),
            ("windlass_maker", "Fabricante Molinete / Windlass Maker"),
            ("windlass_condition", "Estado del Molinete / Windlass Condition"),
            ("capstan_type", "Tipo de Cabrestante / Capstan Type"),
            ("capstan_condition", "Estado del Cabrestante / Capstan Condition"),
            ("rudder_description", "Descripción del Timón / Rudder Description"),
            ("rudder_condition", "Estado del Timón / Rudder Condition"),
            ("pumps_number_type", "Nº y Tipo de Bombas / Pumps No. and Type"),
            ("pumps_condition", "Estado de Bombas / Pumps Condition"),
            ("boats_no_numero_botes", "Nº Total de Botes / Total Boats"),
            ("boats_long_boats_no", "Nº Botes de Rescate / Long Boats No."),
            ("boats_steam_launch_no", "Lanchas de Vapor / Steam Launches No.")
        ],
        "description": "Equipos de maniobra, fondeo y salvamento, esenciales para la operación segura y la respuesta ante emergencias."
    },
    {
        "title": "XI. ESCOTILLAS Y CARBONERAS / HATCHWAYS & BUNKERS",
        "fields": [
            ("engine_room_skylights_const", "Lumbreras Sala Máquinas / E.R. Skylights Construction"),
            ("engine_room_skylights_secured", "Cierre de Lumbreras / E.R. Skylights Secured"),
            ("deadlights_bad_weather", "Contraventanas / Deadlights (Bad Weather)"),
            ("coal_bunker_openings_const", "Bocas de Carbonera / Coal Bunker Openings"),
            ("coal_bunker_openings_lids", "Tapas de Carbonera / Bunker Lids Secured"),
            ("coal_bunker_openings_height", "Altura Carboneras (mm) / Bunker Height (in)"),
            ("scuppers_arrangements", "Imbornales y Amuradas / Scuppers & Bulwarks"),
            ("cargo_hatchways_formed", "Brazolas de Escotillas (mm) / Hatchways Coamings (in)"),
            ("main_hatch_size", "Escotilla Ppal. (m) / Main Hatch Size (ft)"),
            ("fore_hatch_size", "Escotilla de Proa (m) / Fore Hatch Size (ft)"),
            ("quarter_hatch_size", "Escotilla de Cuarto (m) / Quarter Hatch Size (ft)"),
            ("extraordinary_size_framed", "Refuerzos Tamaño Extra / Extraordinary Sizes"),
            ("shifting_beams_arrangement", "Baos Móviles / Shifting Beams Arrangement"),
            ("hatches_strong_efficient", "Solidez de Escotillas (mm) / Hatches Thickness (in)")
        ],
        "description": "Accesos a bodegas y espacios de combustible, fundamentales para la carga y el mantenimiento de la estabilidad."
    },
    {
        "title": "XII. CADENAS Y CABLES / CABLES & CHAINS",
        "fields": [
            ("cables_length_longitud_cadenas", "Longitud Total Cadenas (m) / Total Cables (fath)"),
            ("cable_chain_length", "Cadena Principal (m) / Main Chain (fath)"),
            ("cable_chain_size", "Calibre Cadena (mm) / Chain Size (in)"),
            ("cable_chain_test", "Prueba de Carga (Ton) / Chain Load Test (Ton)"),
            ("cable_towline_length", "Remolque Cáñamo (m) / Towline Length (fath)"),
            ("cable_towline_size", "Grosor Remolque (mm) / Towline Size (in)"),
            ("cable_hawser_length", "Calabrote (m) / Hawser Length (fath)"),
            ("cable_hawser_size", "Grosor Calabrote (mm) / Hawser Size (in)"),
            ("cable_warp_length", "Estacha (m) / Warp Length (fath)"),
            ("cable_warp_size", "Grosor Estacha (mm) / Warp Size (in)")
        ],
        "description": "Especificaciones de las cadenas de ancla y cables de remolque, vitales para el fondeo y la maniobra en puerto."
    },
    {
        "title": "XIII. MÁQUINAS Y CALDERAS / ENGINES & BOILERS",
        "fields": [
            ("engine_type_tipo_maquina", "Tipo de Máquina / Engine Type"),
            ("engine_hp_caballos_maquina", "Potencia Nominal (HP) / Nominal HP"),
            ("boilers_no_numero_calderas", "Nº de Calderas / No. of Boilers"),
            ("boilers_pressure_presion_calderas", "Presión Calderas (psi) / Boilers Pressure (psi)"),
            ("boilers_material_material_calderas", "Material de Calderas / Boilers Material"),
            ("propeller_type_tipo_helice", "Tipo de Hélice / Propeller Type")
        ],
        "description": "Corazón mecánico del S.S. Sirio, detallando su planta propulsora y la capacidad de generación de vapor."
    },
    {
        "title": "XIV. CRONOLOGÍA DE CONSTRUCCIÓN / BUILDING CHRONOLOGY",
        "fields": [
            ("special_survey_no", "Nº Inspección Especial / Special Survey No."),
            ("special_survey_date", "Fecha de Orden / Survey Order Date"),
            ("builders_yard_no", "Nº de Astillero / Builder's Yard No."),
            ("survey_1st_frame", "1ª Fase: Armazón / 1st Frame"),
            ("survey_2nd_plating", "2ª Fase: Planchaje / 2nd Plating"),
            ("survey_3rd_beams", "3ª Fase: Baos / 3rd Beams"),
            ("survey_4th_complete", "4ª Fase: Casco Completo / 4th Complete"),
            ("survey_5th_launched", "5ª Fase: Lanzamiento / 5th Launched")
        ],
        "description": "Registro temporal de los hitos clave durante la construcción del buque en los astilleros de Robert Napier."
    },
    {
        "title": "XV. FIRMAS Y FABRICANTES / MAKERS & SIGNATURES",
        "fields": [
            ("iron_quality", "Calidad del Hierro / Iron Quality"),
            ("manufacturers_trade_mark", "Marcas Fabricantes / Manufacturers Marks"),
            ("builder_signature", "Firma Constructor / Builder Signature"),
            ("surveyor_signature", "Firma Inspector / Surveyor Signature"),
            ("general_remarks_observaciones_generales", "Observaciones / General Remarks"),
            ("class_assigned_clase_asignada", "Clase Asignada / Class Assigned"),
            ("date_of_class_fecha_clase", "Fecha Clase / Date of Class")
        ],
        "description": "Validación final de la inspección, marcas de calidad de los materiales y la clasificación otorgada por Lloyd's."
    }
]
