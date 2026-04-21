from flask import Blueprint, request, jsonify, Response, url_for
from flask_login import login_required, current_user
from extensions import db
from models import SimulationRoute, SimulationLog, Proyecto
from datetime import datetime
import json

simulacion_bp = Blueprint('simulacion', __name__)

def get_proyecto_activo():
    """Helper to get current active project ID from session"""
    from flask import session, current_app
    proyecto_id = session.get('proyecto_activo_id')
    if not proyecto_id:
        current_app.logger.warning("[Simulador] Intento de acceso sin proyecto_activo_id en sesión")
        return None
    return Proyecto.query.get(proyecto_id)

@simulacion_bp.route('/api/simulacion/save', methods=['POST'])
@login_required
def save_route():
    try:
        data = request.json
        proyecto = get_proyecto_activo()
        if not proyecto:
            return jsonify({"success": False, "error": "No hay proyecto activo"}), 400

        route_id = data.get('id')
        nombre = data.get('nombre', 'Nueva Ruta')
        descripcion = data.get('descripcion', '')
        waypoints = json.dumps(data.get('waypoints', []))
        cronograma = json.dumps(data.get('cronograma', []))
        configuracion = json.dumps(data.get('configuracion', {}))
        vector_layer_id = data.get('vector_layer_id')

        if route_id:
            route = SimulationRoute.query.get(route_id)
            if not route or route.proyecto_id != proyecto.id:
                return jsonify({"success": False, "error": "Ruta no encontrada"}), 404
            route.nombre = nombre
            route.descripcion = descripcion
            route.waypoints = waypoints
            route.cronograma = cronograma
            route.configuracion = configuracion
            route.vector_layer_id = vector_layer_id
        else:
            route = SimulationRoute(
                proyecto_id=proyecto.id,
                nombre=nombre,
                descripcion=descripcion,
                waypoints=waypoints,
                cronograma=cronograma,
                configuracion=configuracion,
                vector_layer_id=vector_layer_id
            )
            db.session.add(route)
        
        db.session.commit()
        return jsonify({"success": True, "id": route.id})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500

@simulacion_bp.route('/api/simulacion/list', methods=['GET'])
@login_required
def list_routes():
    import traceback
    try:
        print("[DEBUG] list_routes: starting")
        proyecto = get_proyecto_activo()
        print(f"[DEBUG] list_routes: proyecto={proyecto}")
        if not proyecto:
            return jsonify({"success": False, "error": "No hay proyecto activo"}), 400
        
        print("[DEBUG] list_routes: querying SimulationRoute")
        rutas = SimulationRoute.query.filter_by(proyecto_id=proyecto.id).order_by(SimulationRoute.creado_en.desc()).all()
        print(f"[DEBUG] list_routes: found {len(rutas)} rutas")

        result_rutas = []
        for r in rutas:
            try:
                num_waypoints = len(json.loads(r.waypoints)) if r.waypoints else 0
                result_rutas.append({
                    "id": r.id,
                    "nombre": r.nombre,
                    "descripcion": r.descripcion,
                    "creado_en": r.creado_en.isoformat() if r.creado_en else None,
                    "num_waypoints": num_waypoints
                })
            except Exception as e_inner:
                print(f"[DEBUG] list_routes: error processing route {r.id}: {e_inner}")
                continue

        return jsonify({
            "success": True, 
            "rutas": result_rutas
        })
    except Exception as e:
        print(f"[ERROR] list_routes error: {e}")
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500

@simulacion_bp.route('/api/simulacion/get/<int:id>', methods=['GET'])
@login_required
def get_route(id):
    try:
        route = SimulationRoute.query.get(id)
        if not route:
            return jsonify({"success": False, "error": "Ruta no encontrada"}), 404
        
        return jsonify({
            "success": True,
            "id": route.id,
            "nombre": route.nombre,
            "descripcion": route.descripcion,
            "waypoints": json.loads(route.waypoints),
            "cronograma": json.loads(route.cronograma),
            "configuracion": json.loads(route.configuracion or '{}')
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@simulacion_bp.route('/api/simulacion/delete/<int:id>', methods=['DELETE'])
@login_required
def delete_route(id):
    try:
        route = SimulationRoute.query.get(id)
        if not route:
            return jsonify({"success": False, "error": "Ruta no encontrada"}), 404
        
        db.session.delete(route)
        db.session.commit()
        return jsonify({"success": True})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500

@simulacion_bp.route('/log', methods=['POST'])
@login_required
def log_analysis():
    try:
        data = request.json
        route_id = data.get('route_id')
        if not route_id:
            return jsonify({"success": False, "error": "ID de ruta requerido"}), 400
        
        sim_time_raw = data.get('sim_time')
        sim_time = datetime.fromtimestamp(sim_time_raw / 1000.0) if sim_time_raw else datetime.utcnow()

        log = SimulationLog(
            route_id=route_id,
            sim_time=sim_time,
            lat=data.get('lat'),
            lon=data.get('lon'),
            weather_layer_id=str(data.get('weather_layer_id')),
            analysis=data.get('analysis'),
            modifier=data.get('modifier', 1.0)
        )
        db.session.add(log)
        db.session.commit()
        return jsonify({"success": True})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500

@simulacion_bp.route('/export/geojson/<int:id>', methods=['GET'])
@login_required
def export_geojson(id):
    try:
        route = SimulationRoute.query.get(id)
        if not route:
            return "Ruta no encontrada", 404
        
        waypoints = json.loads(route.waypoints)
        features = []
        
        # Helper local para extraer coordenadas con fallback
        def get_coords(w):
            if 'coord' in w and isinstance(w['coord'], list) and len(w['coord']) >= 2:
                return w['coord'][0], w['coord'][1]
            return w.get('lng', 0), w.get('lat', 0)

        # 1. Feature de la línea
        coordinates = [list(get_coords(wp)) for wp in waypoints]
        line_feature = {
            "type": "Feature",
            "properties": {
                "name": route.nombre,
                "type": "route_line"
            },
            "geometry": {
                "type": "LineString",
                "coordinates": coordinates
            }
        }
        features.append(line_feature)
        
        # 2. Features de los puntos con metadata de tiempo
        for i, wp in enumerate(waypoints):
            lng_val, lat_val = get_coords(wp)
            features.append({
                "type": "Feature",
                "properties": {
                    "name": f"Punto {i}",
                    "timestamp": wp.get('time'),
                    "type": "waypoint"
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [lng_val, lat_val]
                }
            })
            
        geojson = {
            "type": "FeatureCollection",
            "features": features
        }
        
        return Response(
            json.dumps(geojson),
            mimetype='application/json',
            headers={'Content-Disposition': f'attachment;filename=ruta_{id}.geojson'}
        )
    except Exception as e:
        return str(e), 500

@simulacion_bp.route('/export/kml/<int:id>', methods=['GET'])
@login_required
def export_kml(id):
    try:
        route = SimulationRoute.query.get(id)
        if not route:
            return "Ruta no encontrada", 404
        
        waypoints = json.loads(route.waypoints)
        
        kml = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<kml xmlns="http://www.opengis.net/kml/2.2">',
            '  <Document>',
            f'    <name>{route.nombre}</name>',
            '    <Style id="routeStyle">',
            '      <LineStyle><color>ff0098ff</color><width>4</width></LineStyle>',
            '    </Style>',
            '    <Placemark>',
            f'      <name>Trayectoria: {route.nombre}</name>',
            '      <styleUrl>#routeStyle</styleUrl>',
            '      <LineString>',
            '        <tessellate>1</tessellate>',
            '        <coordinates>'
        ]
        
        # Helper local para extraer coordenadas con fallback
        def get_coords(w):
            if 'coord' in w and isinstance(w['coord'], list) and len(w['coord']) >= 2:
                return w['coord'][0], w['coord'][1]
            return w.get('lng', 0), w.get('lat', 0)

        coord_strings = []
        for wp in waypoints:
            ln, lt = get_coords(wp)
            coord_strings.append(f"{ln},{lt},0")
        
        kml.append(" ".join(coord_strings))
        
        kml.extend([
            '        </coordinates>',
            '      </LineString>',
            '    </Placemark>'
        ])
        
        # Añadir waypoints como puntos
        for i, wp in enumerate(waypoints):
            ln, lt = get_coords(wp)
            kml.extend([
                '    <Placemark>',
                f'      <name>Punto {i}</name>',
                f'      <description>Tiempo: {wp.get("time")}</description>',
                '      <Point>',
                f'        <coordinates>{ln},{lt},0</coordinates>',
                '      </Point>',
                '    </Placemark>'
            ])
            
        kml.extend([
            '  </Document>',
            '</kml>'
        ])
        
        return Response(
            "\n".join(kml),
            mimetype='application/vnd.google-earth.kml+xml',
            headers={'Content-Disposition': f'attachment;filename=ruta_{id}.kml'}
        )
    except Exception as e:
        return str(e), 500
@simulacion_bp.route('/api/simulacion/analyze_mc', methods=['POST'])
@simulacion_bp.route('/api/simulacion/diagnose_mc_ai', methods=['POST'])
@login_required
def analyze_mc():
    import os
    with open('/tmp/sim_debug.log', 'a') as f:
        f.write(f"{datetime.now()}: analyze_mc call detected\n")
    """
    Analiza los resultados de una simulación Monte Carlo usando el motor de IA seleccionado.
    """
    from services.ai_service import AIService
    try:
        data = request.json
        
        # Log diagnóstico para cazar el 500
        print(f"[DEBUG SIM] Petición recibida en /diagnose_mc_ai: {json.dumps(data) if data else 'NO DATA'}")
        
        if not data:
            return jsonify({"success": False, "error": "No se recibieron datos"}), 400

        # Parámetros del análisis
        results = data.get('results', {})
        potencia = data.get('potencia', 'gemini:flash') # proveedor:modelo
        scientific_mode = data.get('scientific_mode', False)
        
        # Extraer proveedor y modelo
        parts = potencia.split(':')
        provider = parts[0] if len(parts) > 0 else 'gemini'
        model = parts[1] if len(parts) > 1 else None

        # Inicializar AIService
        ai_service = AIService(provider=provider, model=model, user=current_user)
        if not ai_service.is_configured():
            return jsonify({
                "success": False, 
                "error": f"El servicio de IA ({provider}) no está configurado."
            }), 400

        # Determinar tipo de análisis
        inverse_mode = data.get('inverse_mode', False)

        # Construir el prompt
        if scientific_mode:
            atmospheric = data.get('atmospheric', {})
            atmos_str = ""
            fecha_hora_str = "N/A"
            if atmospheric:
                fecha_hora_raw = atmospheric.get('fecha_hora')
                if fecha_hora_raw:
                    try:
                        # Asegurar que es float (viene como ms desde JS)
                        ts_ms = float(fecha_hora_raw)
                        dt_impact = datetime.fromtimestamp(ts_ms / 1000.0)
                        fecha_hora_str = dt_impact.strftime("%d/%m/%Y %H:%M:%S")
                    except Exception as e:
                        print(f"[DEBUG SIM] Error convirtiendo fecha: {e}")
                        fecha_hora_str = str(fecha_hora_raw)

                atmos_str = f"""
            DETALLE DE CONDICIONES ATMOSFÉRICAS Y CRONOLÓGICAS:
            - Fecha y Hora del Impacto: {fecha_hora_str}
            - Presión Barométrica: {atmospheric.get('barometro', 'N/A')} {atmospheric.get('barometro_unit', 'hPa')}
            - Viento (Anemómetro): {atmospheric.get('anemometro', 'N/A')} {atmospheric.get('anemometro_unit', 'Knots')}
            - Escala Beaufort: Fuerza {atmospheric.get('viento_fza', 'N/A')} (Dir: {atmospheric.get('viento_dir', 'N/A')})
            - Estado del Mar (Escala Douglas): Grado {atmospheric.get('mar', 'N/A')}
            - Estado del Cielo: {atmospheric.get('cielo', 'N/A')}
            - Rango Térmico: Mín {atmospheric.get('temp_min', 'N/A')}°C / Máx {atmospheric.get('temp_max', 'N/A')}°C (Media: {atmospheric.get('temp_mean', 'N/A')}°C)
            """

            if inverse_mode:
                prompt = f"""
                Actúa como un perito forense de la Marina Civil y experto en reconstrucción de siniestros marítimos.
                Se te presentan los resultados de una simulación de Monte Carlo Inverso para reconstruir la posición inicial ($P_0$) del SS Sirio basándose en su punto de impacto conocido.
                
                DATOS DE LA RECONSTRUCCIÓN FORENSE:
                - Iteraciones totales de búsqueda: {results.get('total')}
                - Puntos de origen ($P_0$) compatibles hallados: {results.get('collisions')}
                - Probabilidad de coincidencia estocástica: {results.get('prob')}%
                {atmos_str}
                
                TAREA DE ANÁLISIS FORENSE:
                1. Evaluación de la Incertidumbre Geográfica: Analiza la dispersión de los puntos $P_0$ hallados. ¿Sugiere la simulación una zona de partida clara o hay múltiples vectores posibles?
                2. Factor Ambiental: Evalúa cómo las condiciones ({fecha_hora_str}, viento Beaufort {atmospheric.get('viento_fza', 'N/A')}, mar Douglas {atmospheric.get('mar', 'N/A')}) condicionaron la deriva y dificultaron la navegación recta.
                3. Análisis de Visibilidad: Considerando la hora ({fecha_hora_str}), determina las dificultades ópticas para situarse antes de iniciar la maniobra que llevó al desastre.
                4. Conclusión Pericial: Determina cuán cerca del Bajo de Fuera debió empezar la maniobra final y si la posición reconstruida coincide con los testimonios históricos o sugiere una negligencia en el posicionamiento estimado por la tripulación.
                
                Usa un tono técnico, pericial y extremadamente serio. Responde de forma detallada en español.
                """
            else:
                prompt = f"""
                Actúa como un perito de la Marina Civil y experto en análisis de riesgos marítimos catastróficos.
                Se te presentan los resultados de una simulación de Monte Carlo basada en una reconstrucción forense del naufragio del SS Sirio en el Bajo de Fuera.
                
                DATOS DE LA SIMULACIÓN:
                - Escenarios totales modelados: {results.get('total')}
                - Colisiones de impacto directo: {results.get('collisions')}
                - Pasos críticos en zona de peligro (<100m): {results.get('nearMisses')}
                - Probabilidad matemática de desastre: {results.get('prob')}%
                {atmos_str}
                
                TAREA DE ANÁLISIS EXHAUSTIVO:
                1. Evalúa la visibilidad y factores lumínicos: Analiza si la hora del impacto ({fecha_hora_str}) implica oscuridad total, crepúsculo o luz de día. Considera si la estación del año y la posición del sol pudieron generar reflejos cegadores sobre el mar que distorsionaran la apreciación de las distancias o la visualización de las señales del Bajo de Fuera.
                2. Evalúa cómo el viento (Beaufort) y el estado del mar (Douglas) han podido afectar al desplazamiento (leeway) y al control del buque en esta trayectoria.
                3. Analiza si la presión barométrica y el rango térmico sugieren condiciones de estabilidad atmosférica que pudieron influir en el avistamiento del faro o del bajo (ej: posibles espejismos o brumas).
                4. Determina de forma contundente si las maniobras de corrección (Tarantino) y los parámetros de navegación son suficientes para garantizar la seguridad o si el buque está irreversiblemente condenado bajo estas condiciones.
                
                Usa un tono técnico, pericial y extremadamente serio. Responde de forma detallada en español.
                """
        else:
            prompt = f"""
            Actúa como un analista de datos y experto en simulación.
            Analiza estos resultados de una simulación de Monte Carlo:
            
            - Tipo de simulación: {"Inversa/Forense" if inverse_mode else "Directa/Riesgo"}
            - Escenarios totales: {results.get('total')}
            - Coincidencias/Impactos: {results.get('collisions')}
            - Probabilidad: {results.get('prob')}%
            
            Evalúa la viabilidad de la ruta o la precisión de la reconstrucción y sugiere posibles mejoras o precauciones.
            Responde de forma concisa y profesional en español.
            """

        analysis = ai_service.generate_content(prompt, temperature=0.7)
        if not analysis:
            error_msg = ai_service.last_error or "No se pudo generar el análisis (Error desconocido)"
            return jsonify({"success": False, "error": error_msg}), 500

        return jsonify({
            "success": True,
            "analysis": analysis
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
