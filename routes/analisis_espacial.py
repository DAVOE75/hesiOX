import json
from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required, current_user
from extensions import db
from models import Prensa, Proyecto, LugarNoticia
import pandas as pd
# import geopandas as gpd
# from shapely.geometry import Point
# import numpy as np
# from scipy.spatial import ConvexHull

# Crear Blueprint
analisis_espacial_bp = Blueprint('analisis_espacial', __name__, url_prefix='/api/analisis-espacial')

@analisis_espacial_bp.route('/ui')
@login_required
def index():
    """Vista principal del módulo de Análisis Espacial Backend"""
    return render_template("analisis_espacial.html")

@analisis_espacial_bp.route('/estadisticas')
@login_required
def api_estadisticas():
    """Calcula estadísticas espaciales básicas del corpus activo"""
    try:
        import geopandas as gpd
        from shapely.geometry import Point
        from utils import get_proyecto_activo
        proyecto = get_proyecto_activo()
        if not proyecto:
            return jsonify({"success": False, "error": "No hay proyecto activo"})

        # 1. Obtener datos (Lat/Lon) de las noticias del proyecto
        # Consultamos LugarNoticia (tabla de lugares) unida a Prensa (para filtrar por proyecto)
        query = db.session.query(LugarNoticia.lat, LugarNoticia.lon).join(Prensa).filter(
            Prensa.proyecto_id == proyecto.id,
            LugarNoticia.borrado == False,
            LugarNoticia.lat.isnot(None),
            LugarNoticia.lon.isnot(None)
        ).all()

        if not query:
            return jsonify({"success": False, "error": "No hay datos geográficos en este proyecto"})

        # Convertir a DataFrame
        df = pd.DataFrame(query, columns=['lat', 'lon'])
        
        # Crear GeoDataFrame
        gdf = gpd.GeoDataFrame(
            df, geometry=gpd.points_from_xy(df.lon, df.lat), crs="EPSG:4326"
        )

        # --- CÁLCULOS ESPACIALES (Level 3) ---

        # 1. Centro Medio (Centroid)
        # Proyectamos a una proyección métrica equitativa (World Equidistant Cylindrical - EPSG:4087) para cálculos de distancia
        gdf_metric = gdf.to_crs("EPSG:4087") 
        centroid_metric = gdf_metric.geometry.unary_union.centroid
        centroid = gpd.GeoSeries([centroid_metric], crs="EPSG:4087").to_crs("EPSG:4326").iloc[0]

        # 2. Desviación Estándar (Standard Distance)
        # Distancia euclidiana promedio al centro medio
        distances = gdf_metric.distance(centroid_metric)
        std_dist_meters = distances.std()
        std_dist_km = std_dist_meters / 1000

        # 3. Convex Hull (Envolvente Convexa)
        hull_metric = gdf_metric.geometry.unary_union.convex_hull
        hull_area_sqkm = hull_metric.area / 1e6 # m2 to km2
        
        # Convertir Hull a GeoJSON para pintar en mapa
        hull_geojson = gpd.GeoSeries([hull_metric], crs="EPSG:4087").to_crs("EPSG:4326").__geo_interface__

        return jsonify({
            "success": True,
            "stats": {
                "total_points": len(df),
                "centroid": {"lat": centroid.y, "lon": centroid.x},
                "std_distance_km": round(std_dist_km, 2),
                "hull_area_sqkm": round(hull_area_sqkm, 2)
            },
            "hull_geojson": hull_geojson
        })

    except Exception as e:
        print(f"Error en estadisticas espaciales: {e}")
        return jsonify({"success": False, "error": str(e)})


@analisis_espacial_bp.route('/redes')
@login_required
def api_redes_espaciales():
    """Calcula la Red Espacial (Co-ocurrencias) y Métricas de Grafo"""
    try:
        from utils import get_proyecto_activo
        from models import Prensa, LugarNoticia
        import networkx as nx
        from collections import defaultdict
        import geopandas as gpd
        from shapely.geometry import Point
        
        proyecto = get_proyecto_activo()
        if not proyecto:
            return jsonify({"success": False, "error": "No hay proyecto activo"})

        # 1. Obtener ubicaciones agrupadas por noticia
        # Queremos saber: Noticia X -> [Madrid, Paris, Londres]
        # Esto genera aristas: Madrid-Paris, Madrid-Londres, Paris-Londres
        
        lugares = db.session.query(
            LugarNoticia.noticia_id,
            LugarNoticia.nombre,
            LugarNoticia.lat,
            LugarNoticia.lon
        ).join(Prensa).filter(
            Prensa.proyecto_id == proyecto.id,
            LugarNoticia.borrado == False,
            LugarNoticia.lat.isnot(None),
            LugarNoticia.lon.isnot(None),
            Prensa.incluido == True
        ).all()

        if not lugares:
            return jsonify({"success": False, "error": "No hay datos para redes"})

        # Agrupar por noticia
        noticias_lugares = defaultdict(list)
        loc_coords = {} # Cache de coordenadas: "Madrid" -> {lat, lon}
        
        for nid, nombre, lat, lon in lugares:
            norm_name = nombre.strip()
            noticias_lugares[nid].append(norm_name)
            if norm_name not in loc_coords:
                loc_coords[norm_name] = {'lat': lat, 'lon': lon}

        # Construir Grafo
        G = nx.Graph()
        
        # Añadir Nodos
        for name in loc_coords:
            G.add_node(name, **loc_coords[name])
            
        # Añadir Aristas (Co-ocurrencias)
        import itertools
        for nid, locs in noticias_lugares.items():
            # Eliminar duplicados en la misma noticia (Madrid, Madrid -> Madrid)
            unique_locs = sorted(list(set(locs)))
            
            if len(unique_locs) < 2: continue
            
            # Generar combinaciones pares (clique)
            for u, v in itertools.combinations(unique_locs, 2):
                if G.has_edge(u, v):
                    G[u][v]['weight'] += 1
                else:
                    G.add_edge(u, v, weight=1)
        
        # Filtrar grafo para rendimiento (eliminar nodos aislados o aristas débiles si es muy grande)
        # Por ahora lo dejamos completo, pero limitamos visualización en frontend si es necesario
        if len(G.nodes) == 0:
             return jsonify({"success": False, "error": "No se encontraron conexiones entre lugares."})

        # --- CÁLCULO DE MÉTRICAS (NetworkX) ---
        
        # 1. Grado (Importancia local)
        degree = dict(G.degree(weight='weight'))
        
        # 2. Betweenness Centrality (Puentes)
        # Costoso computacionalmente, usamos k=None (exacto) si N < 200, si no k=50 aprox
        k_val = None if len(G.nodes) < 200 else 50
        betweenness = nx.betweenness_centrality(G, weight='weight', k=k_val)
        
        # 3. Comunidades (Greedy Modularity)
        # Detecta grupos de ciudades muy conectadas entre sí
        try:
            communities = nx.community.greedy_modularity_communities(G, weight='weight')
            # Map node -> community_id
            comm_map = {}
            for idx, comm in enumerate(communities):
                for node in comm:
                    comm_map[node] = idx
        except:
            comm_map = {node: 0 for node in G.nodes} # Fallback

        # --- SERIALIZACIÓN ---
        nodes_data = []
        for n in G.nodes:
            nodes_data.append({
                "id": n,
                "lat": G.nodes[n]['lat'],
                "lon": G.nodes[n]['lon'],
                "degree": degree.get(n, 0),
                "betweenness": betweenness.get(n, 0),
                "community": comm_map.get(n, 0)
            })
            
        edges_data = []
        for u, v, data in G.edges(data=True):
            edges_data.append({
                "source": u,
                "target": v,
                "weight": data['weight']
            })
            
        # Top Bridges (Ranking)
        top_bridges = sorted(betweenness.items(), key=lambda x: x[1], reverse=True)[:5]
        top_bridges_list = [{"name": k, "score": v} for k, v in top_bridges]

        return jsonify({
            "success": True,
            "nodes": nodes_data,
            "edges": edges_data,
            "stats": {
                "num_nodes": len(G.nodes),
                "num_edges": len(G.edges),
                "bridges": top_bridges_list
            }
        })

    except Exception as e:
        print(f"Error en redes espaciales: {e}")
        return jsonify({"success": False, "error": str(e)})

@analisis_espacial_bp.route('/escala-nodos')
@login_required
def api_escala_nodos():
    """Genera una especificación Vega-Lite para la escala de magnitud de los nodos"""
    try:
        from utils import get_proyecto_activo
        import altair as alt
        proyecto = get_proyecto_activo()
        if not proyecto:
            return jsonify({"success": False, "error": "No hay proyecto activo"})

        # Obtener parámetros de filtrado espacial
        lat_min = request.args.get('lat_min', type=float)
        lat_max = request.args.get('lat_max', type=float)
        lon_min = request.args.get('lon_min', type=float)
        lon_max = request.args.get('lon_max', type=float)
        publicacion = request.args.get('publicacion')

        # Obtener frecuencias de lugares del proyecto activo
        query_base = db.session.query(
            LugarNoticia.nombre, 
            db.func.sum(LugarNoticia.frecuencia).label('total_frec')
        ).join(Prensa).filter(
            Prensa.proyecto_id == proyecto.id,
            LugarNoticia.borrado == False,
            LugarNoticia.lat.isnot(None),
            LugarNoticia.lon.isnot(None)
        )

        # Aplicar filtro de publicación si existe
        if publicacion:
            query_base = query_base.filter(Prensa.publicacion == publicacion)

        # Aplicar filtros espaciales si existen
        if lat_min is not None and lat_max is not None:
            query_base = query_base.filter(LugarNoticia.lat.between(lat_min, lat_max))
        if lon_min is not None and lon_max is not None:
            query_base = query_base.filter(LugarNoticia.lon.between(lon_min, lon_max))

        query = query_base.group_by(LugarNoticia.nombre).all()

        if not query:
            return jsonify({"success": False, "error": "No hay datos para la escala"})

        theme = request.args.get('theme', 'dark')
        accent_color = '#294a60' if theme == 'light' else '#ff9800'
        axis_color = '#444' if theme == 'light' else '#888'
        title_color = '#222' if theme == 'light' else '#aaa'
        grid_color = 'rgba(0,0,0,0.05)' if theme == 'light' else 'rgba(255,255,255,0.05)'

        df = pd.DataFrame(query, columns=['nombre', 'frecuencia'])
        
        chart = alt.Chart(df).mark_circle(color=accent_color, opacity=0.8).encode(
            x=alt.X('nombre:N', title=None, axis=None),
            y=alt.Y('frecuencia:Q', title='Menciones', 
                  axis=alt.Axis(grid=True, gridColor=grid_color, labelColor=axis_color, titleColor=title_color)),
            size=alt.Size('frecuencia:Q', title='Escala', 
                        scale=alt.Scale(range=[20, 1000]), 
                        legend=alt.Legend(titleColor=title_color, labelColor=axis_color, offset=10)),
            tooltip=['nombre', 'frecuencia']
        ).properties(
            width='container',
            height=160,
            padding={'left': 10, 'top': 20, 'right': 15, 'bottom': 20},
            background='transparent'
        ).configure_view(
            strokeWidth=0
        ).configure_axis(
            labelFontSize=9,
            titleFontSize=10
        )

        chart_dict = chart.to_dict()
        chart_dict['$schema'] = 'https://vega.github.io/schema/vega-lite/v6.json'
        return jsonify(chart_dict)
    except Exception as e:
        print(f"Error en escala altair: {e}")
        return jsonify({"success": False, "error": str(e)})


@analisis_espacial_bp.route('/weather-impact', methods=['POST'])
@login_required
def api_weather_impact():
    """
    Analiza un recorte de un mapa histórico (WMS/Raster) subido por el cliente
    usando IA Multimodal (Visión) para determinar el impacto meteorológico 
    sobre un navío en movimiento en una simulación.
    Retorna un modificador de velocidad (ej. 0.5 para -50%, 1.2 para +20%) y una justificación.
    """
    try:
        from utils import get_proyecto_activo
        proyecto = get_proyecto_activo()
        if not proyecto:
            return jsonify({"success": False, "error": "No hay proyecto activo."})
        
        data = request.json
        if not data:
            return jsonify({"success": False, "error": "No provisto payload JSON."})
            
        map_image_b64 = data.get('image_b64')
        lat = data.get('lat')
        lng = data.get('lng')
        
        if not map_image_b64:
            return jsonify({
                "success": False, 
                "error": "Se requiere la imagen recortada del mapa base (image_b64) para el análisis heurístico visual."
            })
            
        # Limpiar prefijo base64 si existe (data:image/png;base64,...)
        if ',' in map_image_b64:
            map_image_b64 = map_image_b64.split(',')[1]
            
        import base64
        import requests
        import os
        # api_key = os.getenv("GEMINI_API_KEY") 
        
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return jsonify({"success": False, "error": "La API Key de Gemini no está configurada en el backend."})
            
        # Llamada directa a Gemini v2 via REST API
        gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
        
        weather_layer_id = data.get('weather_layer_id', '')
        
        system_instructions = (
            "Eres un experto cartógrafo y meteorólogo histórico. Te daré un recorte de un mapa "
            f"{'(Capa meteorológica específica: ' + str(weather_layer_id) + ') ' if weather_layer_id else '(Mapa Base) '}"
            "del 1900 o similar. El barco que navega está situado exactamente en el CENTRO de la imagen. "
            "Tu tarea es ESCANEAR VISUALMENTE la imagen AL MÁXIMO DETALLE para no cometer ningún error. Analiza minuciosamente los colores, isobaras, frentes y toda la simbología meteorológica/marítima que veas alrededor del centro. "
            "Debes describir con extrema rigurosidad las probables condiciones de vientos (fuerza y dirección) y el estado del mar (oleaje) "
            "basado EXCLUSIVAMENTE en lo que observas en la imagen. Luego, deduce cómo afectará ese clima a la velocidad del barco de vela. "
            "Devuelve EXCLUSIVAMENTE un JSON válido con esta estructura: "
            "{\"speed_modifier\": float, \"reason\": \"string\"}. "
            "El 'speed_modifier' debe ser 1.0 (clima normal), < 1.0 (penalización) o > 1.0 (bonificación). "
            "El 'reason' debe ser una descripción detallada que incluya el estado del viento y del mar, su efecto en la navegación, y ESTRICTAMENTE EN ESPAÑOL."
        )
        
        payload = {
            "contents": [{
                "parts": [
                    {"text": system_instructions},
                    {
                        "inlineData": {
                            "mimeType": "image/jpeg",
                            "data": map_image_b64
                        }
                    }
                ]
            }],
            "generationConfig": {
                "temperature": 0.2,
                "responseMimeType": "application/json"
            }
        }
        
        response = requests.post(gemini_url, json=payload, timeout=15)
        response.raise_for_status()
        result_data = response.json()
        
        # Parse result
        try:
            text_response = result_data['candidates'][0]['content']['parts'][0]['text']
            parsed_json = json.loads(text_response)
            
            modifier = float(parsed_json.get('speed_modifier', 1.0))
            reason = str(parsed_json.get('reason', 'Clima normal identificado por IA.'))
            
            # Sanitizar rangos lógicos
            if modifier < 0.1: modifier = 0.1 # Salvo naufragio
            if modifier > 3.0: modifier = 3.0
            
            return jsonify({
                "success": True,
                "speed_modifier": modifier,
                "reason": reason,
                "coords": {"lat": lat, "lng": lng}
            })
            
        except Exception as parse_err:
            print(f"[ERROR] Parsing Gemini output in Weather Routing: {parse_err}")
            return jsonify({
                "success": False, 
                "error": "Error de la IA al parsear el mapa. Formato JSON inválido devuelto.",
                "raw_output": text_response if 'text_response' in locals() else 'None'
            })
            
    except requests.exceptions.RequestException as req_err:
        print(f"[API ERROR] Gemini Request Failed: {req_err}")
        return jsonify({"success": False, "error": f"Error de conectividad con Gemini API: {str(req_err)}"})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)})
