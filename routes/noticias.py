
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session, current_app, abort, send_file, Response
import json
from flask_login import login_required, current_user
from models import Prensa, ImagenPrensa, Publicacion, Proyecto, LugarNoticia, Ciudad, EdicionTipoRecurso, SQL_PRENSA_DATE, Tema, AutorPrensa, MetadataOption, VersionPrensa
from extensions import db, csrf
from utils import get_proyecto_activo, get_nlp, limpieza_profunda_ocr, clean_location_name
from cache_config import cache
from datetime import datetime
from sqlalchemy import or_, and_, cast, String, text, func
from analisis_cache import cache as analisis_cache_instance
from collections import Counter
import re
import requests
import time
import spacy
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s %(message)s')
import logging
from werkzeug.utils import secure_filename
import os

noticias_bp = Blueprint('noticias', __name__)
# nlp = spacy.load('es_core_news_md')  # MOVED TO LAZY LOAD


# --- API para autocompletar lugares de una noticia ---
@noticias_bp.route('/api/cartografia_noticia_lugares_autocomplete', methods=['GET'])
@login_required
def cartografia_noticia_lugares_autocomplete():
    """Devuelve nombres únicos de lugares con sus coordenadas para autocompletar."""
    q = (request.args.get('q') or '').strip().lower()
    # Queremos el nombre y las coordenadas. 
    # Usamos distinct en nombre para evitar muchos duplicados visuales, 
    # pero tomamos el primer par de coordenadas encontrado.
    lugares = db.session.query(
        LugarNoticia.nombre, 
        LugarNoticia.lat, 
        LugarNoticia.lon
    ).distinct(LugarNoticia.nombre).all()
    
    resultados = []
    for nombre, lat, lon in lugares:
        if not q or q in (nombre or '').lower():
            resultados.append({
                'nombre': nombre,
                'lat': lat,
                'lon': lon
            })
    return jsonify(resultados)

@noticias_bp.route('/api/search', methods=['GET'])
@login_required
def api_search():
    """Buscador simple de noticias para vincular a otros modelos."""
    q = request.args.get('q', '').strip()
    if not q:
        return jsonify({'success': True, 'results': []})
    
    proyecto_id = session.get('proyecto_activo_id')
    query = Prensa.query
    if proyecto_id:
        query = query.filter(Prensa.proyecto_id == proyecto_id)

    # Filtrar por visibilidad de la publicación
    query = query.outerjoin(Publicacion, Prensa.id_publicacion == Publicacion.id_publicacion).filter(
        or_(
            Publicacion.visible == True,
            Publicacion.id_publicacion == None
        )
    )

        
    results = query.filter(
        or_(
            Prensa.titulo.ilike(f"%{q}%"),
            Prensa.publicacion.ilike(f"%{q}%"),
            Prensa.contenido.ilike(f"%{q}%")
        )
    ).limit(50).all()
    
    data = []
    for art in results:
        data.append({
            'id': art.id,
            'titulo': art.titulo,
            'publicacion': art.publicacion,
            'fecha': art.fecha_original
        })
        
    return jsonify({'success': True, 'results': data})

@noticias_bp.route('/api/publicaciones', methods=['GET'])
@login_required
def api_publicaciones():
    """Returns all publications for the active project."""
    proyecto_id = session.get('proyecto_activo_id')
    q = request.args.get('q', '').strip()
    
    query = Publicacion.query
    if proyecto_id:
        query = query.filter(Publicacion.proyecto_id == proyecto_id)
    
    if q:
        query = query.filter(Publicacion.nombre.ilike(f"%{q}%"))
        
    publicaciones = query.order_by(Publicacion.nombre.asc()).all()
    
    return jsonify({
        'success': True,
        'results': [{
            'id': p.id_publicacion,
            'nombre': p.nombre,
            'ciudad': p.ciudad,
            'pais': p.pais_publicacion
        } for p in publicaciones]
    })

@noticias_bp.route('/api/publicacion_noticias/<int:pub_id>', methods=['GET'])
@login_required
def api_publicacion_noticias(pub_id):
    """Returns news articles for a specific publication."""
    proyecto_id = session.get('proyecto_activo_id')
    
    query = Prensa.query.filter(Prensa.id_publicacion == pub_id)
    if proyecto_id:
        query = query.filter(Prensa.proyecto_id == proyecto_id)
        
    results = query.order_by(Prensa.fecha_original.desc()).limit(100).all()
    
    data = []
    for art in results:
        data.append({
            'id': art.id,
            'titulo': art.titulo,
            'fecha': art.fecha_original
        })
        
    return jsonify({'success': True, 'results': data})

# --- API DE LIMPIEZA POTENTE PARA OCR ---
@noticias_bp.route('/api/spacy/clean2', methods=['POST'])
@login_required
def api_limpieza_potente():
    try:
        data = request.get_json()
        text_to_clean = data.get('text', '')
        if not text_to_clean:
            return jsonify({'clean_text': ''})

        # 1. Unir palabras cortadas por guiones de fin de línea (Ehin- gen -> Ehingen)
        # Soporta tildes y eñes
        text_to_clean = re.sub(r'([a-zA-ZáéíóúÁÉÍÓÚñÑ])-\s*\n\s*([a-zA-ZáéíóúÁÉÍÓÚñÑ])', r'\1\2', text_to_clean)

        # 2. Eliminar basura típica de OCR (marcas de página, WM Pl, carets)
        text_to_clean = re.sub(r'[\^\|~¬]|WM\s+Pl|por\s+España\.?\s+\d+|\d+\s+Viajes', '', text_to_clean)

        # 3. Unificar líneas rotas en un flujo continuo
        lineas = [l.strip() for l in text_to_clean.splitlines() if l.strip()]
        texto_unido = " ".join(lineas)

        # 4. Normalizar espacios y anclar puntuación
        texto_unido = re.sub(r'\s+', ' ', texto_unido)
        texto_unido = re.sub(r'\s+([.,;:])', r'\1', texto_unido)

        # 5. Crear párrafos inteligentes basados en marcadores históricos
        # Detecta "ítem" o puntos seguidos para dar estructura
        texto_unido = texto_unido.replace(" ítem", "\n\nítem")
        texto_unido = texto_unido.replace(". ", ".\n\n")

        return jsonify({'clean_text': texto_unido.strip()})
    except Exception as e:
        current_app.logger.error(f"Error en limpieza avanzada: {e}")
        return jsonify({'error': str(e)}), 500

        
# MOVED UTILS
def valores_unicos_prensa(columna, proyecto_id=None):
    cache_key = f"valores_unicos_prensa_{columna.name}_{proyecto_id}"
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        return cached_result
    query = db.session.query(columna).distinct()
    if proyecto_id and hasattr(columna.table.c, 'proyecto_id'):
        query = query.filter(columna.table.c.proyecto_id == proyecto_id)

    # Filtrar por visibilidad de la publicación si la tabla es 'prensa'
    if columna.table.name == 'prensa':
        query = query.outerjoin(Publicacion, Prensa.id_publicacion == Publicacion.id_publicacion).filter(
            or_(
                Publicacion.visible == True,
                Publicacion.id_publicacion == None
            )
        )

    valores_db = [x[0] for x in query.all() if x[0] and str(x[0]).strip()]
    unicos = {}
    for v in valores_db:
        texto = str(v).strip()
        clave = texto.lower()
        if clave not in unicos or (texto[0].isupper() and not unicos[clave][0].isupper()):
            unicos[clave] = texto
    valores_limpios = sorted(unicos.values(), key=lambda x: x.lower())
    if columna.name == "fecha_original":
        def parse_fecha(f):
            try:
                if "/" in f:
                    return datetime.strptime(f, "%d/%m/%Y")
                elif f.isdigit() and len(f) == 4:
                    return datetime(int(f), 1, 1)
            except Exception:
                return datetime.max
            return datetime.max
        valores_limpios.sort(key=parse_fecha)
    cache.set(cache_key, valores_limpios)
    return valores_limpios

def ordenar_por_fecha_prensa(query, descendente=False):
    from sqlalchemy import text
    # Enhanced for PostgreSQL to handle multiple formats: DD/MM/YYYY and YYYY-MM-DD
    orden_sql = text(f"""
        CASE
            WHEN prensa.fecha_original ~ '^[0-3]?[0-9]/[0-1]?[0-9]/[0-9]{{2,4}}$' THEN to_date(prensa.fecha_original, 'DD/MM/YYYY')
            WHEN prensa.fecha_original ~ '^[0-9]{{4}}-[0-1]?[0-9]-[0-3]?[0-9]$' THEN to_date(prensa.fecha_original, 'YYYY-MM-DD')
            ELSE NULL
        END {"DESC" if descendente else "ASC"} ,
        prensa.id {"DESC" if descendente else "ASC"}
    """)
    return query.order_by(orden_sql)

# --- Helper para datos de formulario en plantillas de noticias ---
def get_form_data_for_templates_noticias():
    idiomas = ["es", "it", "fr", "en", "pt", "ct"]
    tipos_autor = ["anónimo", "firmado", "corresponsal"]
    # Solo publicaciones del proyecto activo
    proyecto = get_proyecto_activo()
    if proyecto:
        publicaciones = [
            p.nombre for p in Publicacion.query.filter_by(proyecto_id=proyecto.id).order_by(Publicacion.nombre.asc()).all()
        ]
        # Recuperar listas auxiliares filtradas por proyecto para autocompletado
        ciudades = [r.ciudad for r in Prensa.query.with_entities(Prensa.ciudad).filter_by(proyecto_id=proyecto.id, incluido=True).distinct().order_by(Prensa.ciudad).all() if r.ciudad]
        
        # Temas: obtener y aplanar si son CSV, o mostrar distinct
        # Simplificación: distinct de la columna
        raw_temas = Prensa.query.with_entities(Prensa.temas).filter_by(proyecto_id=proyecto.id, incluido=True).distinct().all()
        temas = sorted(list(set([t.strip() for r in raw_temas if r.temas for t in r.temas.split(',') if t.strip()]))) if raw_temas else [] 

        licencias = [r.licencia for r in Prensa.query.with_entities(Prensa.licencia).filter_by(proyecto_id=proyecto.id, incluido=True).distinct().order_by(Prensa.licencia).all() if r.licencia]
        formatos = [r.formato_fuente for r in Prensa.query.with_entities(Prensa.formato_fuente).filter_by(proyecto_id=proyecto.id, incluido=True).distinct().order_by(Prensa.formato_fuente).all() if r.formato_fuente]
        paises = [r.pais_publicacion for r in Prensa.query.with_entities(Prensa.pais_publicacion).filter_by(proyecto_id=proyecto.id, incluido=True).distinct().order_by(Prensa.pais_publicacion).all() if r.pais_publicacion]
    else:
        # Si no hay proyecto activo, no devolvemos datos globales para evitar fugas
        publicaciones = []
        ciudades = []
        temas = []
        licencias = []
        formatos = []
        paises = []
    return {
        "idiomas": idiomas,
        "tipos_autor": tipos_autor,
        "publicaciones": publicaciones,
        "ciudades": ciudades,
        "temas": temas,
        "licencias": licencias,
        "formatos": formatos,
        "paises": paises,
        "opciones_genero": MetadataOption.query.filter_by(categoria='tipo_recurso').order_by(MetadataOption.orden, MetadataOption.etiqueta).all(),
        "opciones_subgenero": MetadataOption.query.filter_by(categoria='tipo_publicacion').order_by(MetadataOption.orden, MetadataOption.etiqueta).all(),
        "opciones_frecuencia": MetadataOption.query.filter_by(categoria='frecuencia').order_by(MetadataOption.orden, MetadataOption.etiqueta).all(),
    }
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session, current_app
from flask_login import login_required, current_user
from flask import abort
from models import Prensa, ImagenPrensa, Publicacion, Proyecto, LugarNoticia
from extensions import db
from utils import get_proyecto_activo
from cache_config import cache
from datetime import datetime
from sqlalchemy import or_, cast, String
from analisis_cache import cache as analisis_cache_instance
from collections import Counter
import re
import requests
import spacy
# nlp = spacy.load('es_core_news_md')  # MOVED TO LAZY LOAD
@noticias_bp.route('/api/cartografia_noticia_add_location/<int:id>/editar', methods=['POST'])
@csrf.exempt
@login_required
def editar_lugar_noticia(id):
    data = request.get_json()
    print('DEBUG editar_lugar_noticia: inicio')
    print('DEBUG editar_lugar_noticia: data recibida', data)
    nombre = data.get('nombre')
    nuevo_nombre = data.get('nuevo_nombre')
    frecuencia = data.get('frecuencia')
    en_titulo = bool(data.get('en_titulo')) if data else False
    en_contenido = bool(data.get('en_contenido')) if data else False
    print('DEBUG editar_lugar_noticia: nombre, nuevo_nombre, frecuencia, en_titulo, en_contenido', nombre, nuevo_nombre, frecuencia, en_titulo, en_contenido)
    # Validar frecuencia como entero mayor que 0
    try:
        frecuencia = int(frecuencia)
    except (TypeError, ValueError):
        frecuencia = None
    if not nombre or not nuevo_nombre or frecuencia is None or frecuencia < 1:
        print('RETURN editar_lugar_noticia: Datos incompletos o frecuencia inválida')
        return jsonify({'success': False, 'error': 'Datos incompletos o frecuencia inválida'}), 400
    lugar = LugarNoticia.query.filter_by(noticia_id=id, nombre=nombre).first()
    print('DEBUG editar_lugar_noticia: lugar encontrado', lugar)
    if not lugar:
        print('RETURN editar_lugar_noticia: Lugar no encontrado')
        return jsonify({'success': False, 'error': 'Lugar no encontrado'}), 404
    # Si el nuevo nombre ya existe en la noticia y no es el mismo registro, fusionar (sumar frecuencia y eliminar duplicado)
    if nombre != nuevo_nombre:
        existe = LugarNoticia.query.filter_by(noticia_id=id, nombre=nuevo_nombre, borrado=False).first()
        print('DEBUG editar_lugar_noticia: existe con nuevo_nombre', existe)
        if existe and existe.id != lugar.id:
            print('FUSIONANDO lugares: sumando frecuencia y eliminando duplicado')
            existe.frecuencia += frecuencia
            existe.en_titulo = en_titulo
            existe.en_contenido = en_contenido
            db.session.delete(lugar)
            db.session.commit()
            return jsonify({'success': True, 'fusion': True})
    lugar.nombre = nuevo_nombre
    lugar.frecuencia = frecuencia
    lugar.en_titulo = en_titulo
    lugar.en_contenido = en_contenido
    db.session.commit()

    # --- SYNC PROJECT-WIDE ---
    # After updating the single article's record, propagate the name change
    # to all other LugarNoticia records in the same project that share the old name.
    # This ensures Gestor de Ubicaciones and Mapa Corpus stay in sync.
    if nombre != nuevo_nombre:
        from utils import get_proyecto_activo
        proyecto = get_proyecto_activo()
        if proyecto:
            otros = LugarNoticia.query.join(Prensa).filter(
                Prensa.proyecto_id == proyecto.id,
                LugarNoticia.nombre == nombre,
                LugarNoticia.noticia_id != id  # Skip the one already updated above
            ).all()
            for o in otros:
                o.nombre = nuevo_nombre
            db.session.commit()
            print(f'[SYNC] Propagated rename "{nombre}" -> "{nuevo_nombre}" to {len(otros)} other records in project {proyecto.id}')

    print('RETURN editar_lugar_noticia: success')
    return jsonify({'success': True})
 

# --- API para borrar un lugar de la cartografía de la noticia ---

# --- API para obtener lat/lon de una ciudad por nombre ---
@noticias_bp.route('/api/ciudad_coords', methods=['GET'])
@login_required
def api_ciudad_coords():
    import unicodedata
    nombre = request.args.get('nombre')
    if not nombre:
        return jsonify({'error': 'Falta el parámetro nombre'}), 400

    def normaliza(s):
        if not s:
            return ""
        return unicodedata.normalize('NFD', s).encode('ascii', 'ignore').decode('utf-8').lower().strip()

    nombre_norm = normaliza(nombre)
    ciudades = Ciudad.query.all()
    ciudad = None
    for c in ciudades:
        if normaliza(c.name) == nombre_norm:
            ciudad = c
            break
    if not ciudad or ciudad.lat is None or ciudad.lon is None:
        return jsonify({'error': 'Ciudad no encontrada'}), 404
    return jsonify({'lat': ciudad.lat, 'lon': ciudad.lon})
@noticias_bp.route('/api/cartografia_noticia_add_location/<int:id>/borrar', methods=['POST'])
@login_required
def cartografia_noticia_borrar_location(id):
    noticia = db.session.get(Prensa, id)
    if not noticia:
        return jsonify({'success': False, 'error': 'Noticia no encontrada'}), 404
    try:
        data = request.get_json(force=True)
        nombre = data.get('nombre')
        if not nombre:
            return jsonify({'success': False, 'error': 'Nombre vacío'}), 400
        # Marcar como borrado=True en todas las noticias donde aparezca ese nombre
        lugares = LugarNoticia.query.filter_by(nombre=nombre, borrado=False).all()
        if not lugares:
            return jsonify({'success': False, 'error': 'Lugar no encontrado'}), 404
        for lugar in lugares:
            lugar.borrado = True
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
from werkzeug.utils import secure_filename
import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session, current_app
from flask_login import login_required, current_user
from models import Prensa, ImagenPrensa, Publicacion, Proyecto, LugarNoticia
from extensions import db
from utils import get_proyecto_activo
from cache_config import cache
from datetime import datetime
# IMPORTS PARA FILTROS AVANZADOS
from sqlalchemy import or_, cast, String
from analisis_cache import cache as analisis_cache_instance
from collections import Counter
import re
import requests
import spacy

# nlp = spacy.load('es_core_news_md')  # MOVED TO LAZY LOAD


# --- API para añadir manualmente una ciudad a la cartografía de la noticia ---
from extensions import csrf

@noticias_bp.route('/api/cartografia_noticia_add_location/<int:id>', methods=['POST'])
@csrf.exempt
@login_required
def cartografia_noticia_add_location(id):
    logger = logging.getLogger("cartografia_noticia")
    logger.warning(f'ENTRADA AL ENDPOINT /api/cartografia_noticia_add_location/{id}')
    logger.info(f'HEADERS: {dict(request.headers)}')
    logger.info(f'RAW DATA: {request.data}')
    logger.info(f'INICIO - request.data: {request.data}')
    noticia = db.session.get(Prensa, id)
    if not noticia:
        return jsonify({'success': False, 'error': 'Noticia no encontrada'}), 404
    try:
        data = request.get_json(force=True)
    except Exception as e:
        logger.error(f"Error al parsear JSON: {e}")
        return jsonify({'success': False, 'error': 'JSON inválido'}), 400
    logger.info('--- DEBUG add_location ---')
    logger.info(f'DATA RECIBIDA: {data}')
    raw_nombre = data.get('nombre') if data else None
    raw_busqueda = data.get('nombre_busqueda') or raw_nombre
    
    # Si parece una coordenada, no limpiar (evitar que strip('.,;') rompa el formato)
    # Usamos re.search para ser más permisivos con posibles caracteres invisibles al inicio
    is_coord_format = re.search(r'(-?\d+\.?\d*)\s*[,\s/|]\s*(-?\d+\.?\d*)', str(raw_busqueda))
    
    # DEBUG LOG
    with open('/opt/hesiox/debug_geo.log', 'a') as f:
        import datetime
        f.write(f"\n--- {datetime.datetime.now()} ---\n")
        f.write(f"ID: {id}, DATA: {data}\n")
        f.write(f"RAW_NOMBRE: {raw_nombre}, RAW_BUSQUEDA: {raw_busqueda}\n")
        f.write(f"IS_COORD: {bool(is_coord_format)}\n")

    if is_coord_format:
        nombre = clean_location_name(raw_nombre)
        nombre_busqueda = str(raw_busqueda).strip()
        logger.info(f"Formato de coordenadas detectado: {nombre_busqueda}")
    else:
        nombre = clean_location_name(raw_nombre)
        nombre_busqueda = clean_location_name(raw_busqueda)
    
    try:
        input_frecuencia = int(data.get('frecuencia', 1)) if data and data.get('frecuencia') else 1
    except (ValueError, TypeError):
        input_frecuencia = 1
        
    en_titulo = bool(data.get('en_titulo')) if data else False
    en_contenido = bool(data.get('en_contenido')) if data else False

    if not nombre:
        logger.warning('Nombre vacío o no proporcionado')
        return jsonify({'success': False, 'error': 'Nombre vacío o no proporcionado'}), 400

    # --- AUTO-CONTEO DE FRECUENCIA Y DETECCIÓN ---
    # Buscamos todas las menciones en el título y contenido para actualizar frecuencia y flags
    titulo_noticia = noticia.titulo or ""
    contenido_noticia = noticia.contenido or ""
    
    # Escapar el nombre ORIGINAL para regex y buscar de forma insensible a mayúsculas
    # El nombre original es el que está en el texto de la noticia
    safe_name = re.escape(nombre)
    matches_titulo = len(re.findall(safe_name, titulo_noticia, re.IGNORECASE))
    matches_contenido = len(re.findall(safe_name, contenido_noticia, re.IGNORECASE))
    
    frecuencia_detectada = matches_titulo + matches_contenido
    
    # Si detectamos menciones reales, priman sobre el input manual (o el 1 por defecto)
    if frecuencia_detectada > 0:
        frecuencia = frecuencia_detectada
        en_titulo = matches_titulo > 0
        en_contenido = matches_contenido > 0
    else:
        # Si no se detecta en el texto (ej. se añadió a mano algo que no está literal), usamos el input
        frecuencia = input_frecuencia

    if frecuencia < 1:
        logger.warning(f'Frecuencia resultante inválida: {frecuencia}')
        return jsonify({'success': False, 'error': 'Frecuencia inválida'}), 400
    # No permitir duplicados en la misma noticia - Búsqueda ROBUSTA (ilike)
    duplicados = LugarNoticia.query.filter(
        LugarNoticia.noticia_id == noticia.id,
        LugarNoticia.nombre.ilike(nombre),
        LugarNoticia.borrado == False
    ).all()
    
    existe = duplicados[0] if duplicados else None
    
    # Si hay más de uno (duplicados accidentales), los fusionamos ahora mismo
    if len(duplicados) > 1:
        logger.warning(f"FUSIONANDO {len(duplicados)} DUPLICADOS para '{nombre}' en noticia {noticia.id}")
        for extra in duplicados[1:]:
            existe.frecuencia += extra.frecuencia
            existe.frec_titulo += (extra.frec_titulo or 0)
            existe.frec_contenido += (extra.frec_contenido or 0)
            db.session.delete(extra)
        db.session.commit()
    try:
        logger.info(f'Geocodificando con nombre de búsqueda: {nombre_busqueda}')
        lat, lon = None, None
        tipo_lugar = 'unknown'

        # --- Detectar si el usuario pegó coordenadas directamente ---
        # Usamos re.search para mayor robustez
        coord_match = re.search(r'(-?\d+\.?\d*)\s*[,\s/|]\s*(-?\d+\.?\d*)', nombre_busqueda.replace('°', ''))
        
        if coord_match:
            try:
                lat = float(coord_match.group(1))
                lon = float(coord_match.group(2))
                logger.info(f'Coordenadas detectadas exitosamente: {lat}, {lon}')
            except (ValueError, TypeError) as e_float:
                logger.error(f"Error al convertir coordenadas a float: {e_float}")
        
        # Fallback manual si el regex falló pero is_coord_format era cierto
        if (lat is None or lon is None) and is_coord_format:
            try:
                # Intentar partir por coma si existe
                if ',' in nombre_busqueda:
                    parts = nombre_busqueda.split(',')
                    lat = float(re.findall(r'-?\d+\.?\d*', parts[0])[0])
                    lon = float(re.findall(r'-?\d+\.?\d*', parts[1])[0])
                    logger.info(f'Coordenadas extraídas por split manual: {lat}, {lon}')
            except:
                pass

        if lat is not None and lon is not None:
            # Reverse geocoding para obtener el tipo de lugar
            try:
                rev = requests.get('https://nominatim.openstreetmap.org/reverse', params={
                    'lat': lat, 'lon': lon, 'format': 'json'
                }, headers={'User-Agent': 'app-hesiox/1.0'}, timeout=10)
                rev_data = rev.json()
                tipo_lugar = rev_data.get('type', 'unknown')
            except Exception:
                pass
        else:
            try:
                resp = requests.get('https://nominatim.openstreetmap.org/search', params={
                    'q': nombre_busqueda,
                    'format': 'json',
                    'limit': 1
                }, headers={'User-Agent': 'HesiOX-App-v2/1.1'}, timeout=10)
                
                if resp.status_code == 200:
                    data_geo = resp.json()
                    logger.info(f'Respuesta Nominatim: {data_geo}')

                    if isinstance(data_geo, list) and len(data_geo) > 0:
                        lat = float(data_geo[0]['lat'])
                        lon = float(data_geo[0]['lon'])
                        tipo_lugar = data_geo[0].get('type', 'unknown')
                    else:
                        logger.warning(f'Nominatim no devolvió resultados válidos para "{nombre_busqueda}": {data_geo}')
                else:
                    logger.error(f'Nominatim error {resp.status_code}: {resp.text}')
            except Exception as e_nom:
                logger.error(f"Excepción en petición a Nominatim: {e_nom}")

            # Fallback a Gemini si Nominatim falló o no dio resultados
            if lat is None or lon is None:
                logger.info(f'Intentando geocodificación con IA Gemini para "{nombre_busqueda}"...')
                try:
                    from services.gemini_service import geocode_with_ai
                    contexto_geo = {
                        "titulo": noticia.titulo,
                        "periódico": noticia.publicacion,
                        "contenido_snippet": noticia.contenido[:5000] if noticia.contenido else "",
                        "mensaje": "DESAMBIGUACIÓN CRÍTICA: Identifica cuál de los posibles lugares con este nombre es el más probable según el texto."
                    }
                    res_ai = geocode_with_ai(nombre_busqueda, contexto_geo)
                    if res_ai and res_ai.get('found'):
                        lat = res_ai.get('lat')
                        lon = res_ai.get('lon')
                        # No sobreescribimos 'nombre' para mantener el texto original de la noticia
                        logger.info(f'Gemini desambiguó "{nombre_busqueda}" -> Coordenadas: {lat}, {lon} ({res_ai.get("explanation")})')
                except Exception as e_ai:
                    logger.error(f"Error en geocoding fallback IA: {e_ai}")



        # Si tras Nominatim e IA seguimos sin coordenadas, permitimos añadir con 0,0 para que el usuario corrija
        if lat is None or lon is None:
            # --- NUEVA LÓGICA DE UNIFICACIÓN/DESAMBIGUACIÓN (LOCAL CACHE) ---
            # Solo buscamos en el caché local si NO es un formato de coordenadas explícito
            if not is_coord_format:
                c_manual = Ciudad.query.filter(Ciudad.name.ilike(nombre_busqueda)).first()
                if c_manual and c_manual.lat is not None and c_manual.lon is not None:
                    lat, lon = c_manual.lat, c_manual.lon
                    logger.info(f'Unificación encontrada en tabla Ciudad para "{nombre_busqueda}": {lat}, {lon}')
            
            if lat is None or lon is None:
                logger.warning(f'No se pudo geocodificar "{nombre}". Añadiendo con (0,0) para corrección manual.')
                lat, lon = 0.0, 0.0

        with open('/opt/hesiox/debug_geo.log', 'a') as f:
            f.write(f"RESULT - LAT: {lat}, LON: {lon}, TIPO: {tipo_lugar}\n")
            f.write(f"EXISTE: {bool(existe)}, NOMBRE_MATCH: {nombre}\n")

        if existe:
            logger.info(f'Ya existe el lugar "{nombre}", actualizando...')
            # SOLO actualizar lat/lon si hemos encontrado algo válido (distinto de 0,0)
            # O si el usuario ha pegado coordenadas explícitamente (is_coord_format)
            if (lat != 0.0 or lon != 0.0) or is_coord_format:
                with open('/opt/hesiox/debug_geo.log', 'a') as f:
                    f.write(f"UPDATING EXISTE ID {existe.id} FROM ({existe.lat}, {existe.lon}) TO ({lat}, {lon})\n")
                logger.info(f'Actualizando coordenadas de "{nombre}" a: {lat}, {lon}')
                existe.lat = lat
                existe.lon = lon
            else:
                logger.info(f'Geocodificación fallida para "{nombre}", preservando coordenadas existentes: {existe.lat}, {existe.lon}')
            
            # Si estamos re-mapeando, actualizamos la frecuencia con el valor detectado/proporcionado
            # en lugar de sumarlo, para evitar duplicados en el conteo.
            logger.info(f'Actualizando frecuencia de {existe.frecuencia} a {frecuencia}')
            existe.frecuencia = frecuencia
            existe.tipo = 'manual'
            if 'tipo_lugar' in locals():
                existe.tipo_lugar = tipo_lugar
            existe.borrado = False
            existe.en_titulo = en_titulo
            existe.en_contenido = en_contenido
            existe.frec_titulo = matches_titulo
            existe.frec_contenido = matches_contenido
            lugar = existe
        else:
            with open('/opt/hesiox/debug_geo.log', 'a') as f:
                f.write(f"CREATING NEW LUGAR: {nombre}\n")
            nombre = nombre.strip()
            lugar = LugarNoticia(
                noticia_id=noticia.id,
                nombre=nombre,
                lat=lat,
                lon=lon,
                frecuencia=frecuencia,
                tipo='manual',
                tipo_lugar=tipo_lugar if 'tipo_lugar' in locals() else 'unknown',
                borrado=False,
                en_titulo=en_titulo,
                en_contenido=en_contenido,
                frec_titulo=matches_titulo,
                frec_contenido=matches_contenido
            )
            db.session.add(lugar)
            logger.info(f'Lugar añadido exitosamente a la noticia {noticia.id}')
        db.session.commit()
        ciudad = {
            'nombre': nombre,
            'lat': lat,
            'lon': lon,
            'frecuencia': lugar.frecuencia
        }

        # --- PERSISTENCIA EN TABLA CIUDAD (LÓGICA DE UNIFICACIÓN) ---
        # Si hemos encontrado coordenadas válidas, guardamos/actualizamos en la tabla Ciudad
        # para que futuras detecciones automáticas de este mismo nombre usen estas coordenadas.
        if lat != 0.0 or lon != 0.0:
            c_persist = Ciudad.query.filter(Ciudad.name.ilike(nombre)).first()
            if not c_persist:
                c_persist = Ciudad(name=nombre, lat=lat, lon=lon)
                db.session.add(c_persist)
            else:
                # Si ya existe pero no tiene coordenadas o las estamos corrigiendo manualmente
                c_persist.lat = lat
                c_persist.lon = lon
            
            # Marcar como verificado globalmente si se desea (opcional, por ahora solo guardamos coords)
            db.session.commit()

        estadistica = {
            'lugar': nombre,
            'frecuencia': lugar.frecuencia,
            'en_titulo': lugar.en_titulo,
            'en_contenido': lugar.en_contenido
        }
        logger.info(f'RESPUESTA JSON: ciudad={ciudad}, estadistica={estadistica}')
        return jsonify({'success': True, 'ciudad': ciudad, 'estadistica': estadistica})
    except Exception as e:
        db.session.rollback()
        import traceback
        logger.error(f'Error al añadir/actualizar lugar: {e}')
        logger.error(traceback.format_exc())
        return jsonify({'success': False, 'error': f"Excepción: {e}"}), 500

# --- API para editar manualmente una ciudad de la cartografía de la noticia ---
@noticias_bp.route('/api/cartografia_noticia_edit_location/<int:id>', methods=['POST'], endpoint='cartografia_noticia_edit_location')
@csrf.exempt
@login_required
def cartografia_noticia_edit_location(id):
    noticia = db.session.get(Prensa, id)
    if not noticia:
        return jsonify({'success': False, 'error': 'Noticia no encontrada'}), 404
    data = request.get_json()
    nombre_anterior = data.get('nombre_anterior')
    nombre = clean_location_name(data.get('nombre', '') or data.get('lugar', ''))
    frecuencia = int(data.get('frecuencia', 1))
    en_titulo = data.get('en_titulo') == 'Sí' if data else False
    en_contenido = data.get('en_contenido') == 'Sí' if data else False
    
    if not nombre:
        return jsonify({'success': False, 'error': 'El nombre de la ubicación es obligatorio'}), 400
    
    # Recuperar el lugar objeto que estamos editando
    lugar = LugarNoticia.query.filter_by(noticia_id=noticia.id, nombre=nombre_anterior, borrado=False).first()
    if not lugar:
        return jsonify({'success': False, 'error': 'Lugar original no encontrado'}), 404

    # Validar que si cambiamos el nombre, buscamos si ya existe para fusionar
    if nombre != nombre_anterior:
        # 1. FUSIONAR: Buscar si ya existe en esta noticia
        existe = LugarNoticia.query.filter_by(noticia_id=noticia.id, nombre=nombre, borrado=False).first()
        if existe and existe.id != lugar.id:
            # Fusión: sumar frecuencia al existente y borrar el antiguo
            existe.frecuencia += frecuencia
            # Combinar flags
            existe.en_titulo = existe.en_titulo or en_titulo
            existe.en_contenido = existe.en_contenido or en_contenido
            
            # Si se enviaron coordenadas nuevas explícitas, actualizamos el destino también
            if 'lat' in data and 'lon' in data and data['lat'] and data['lon']:
                try:
                    existe.lat = float(data['lat'])
                    existe.lon = float(data['lon'])
                except: pass

            db.session.delete(lugar)
            db.session.commit()
            return jsonify({'success': True, 'fusion': True})
        
        # 2. COORDINADAS: Prioridad al input manual, luego caché global Ciudad
        new_lat = None
        new_lon = None
        
        # Intentar obtener de los datos enviados (manual)
        try:
            if 'lat' in data and data['lat'] is not None and str(data['lat']).strip() != '':
                new_lat = float(data['lat'])
            if 'lon' in data and data['lon'] is not None and str(data['lon']).strip() != '':
                new_lon = float(data['lon'])
        except: pass

        if new_lat is not None and new_lon is not None:
            lugar.lat = new_lat
            lugar.lon = new_lon
            logger.info(f"Usando coordenadas manuales para {nombre}: {new_lat}, {new_lon}")
        else:
            # Si no hay manuales, buscar en tabla Ciudad (Global)
            ciudad_db = Ciudad.query.filter(Ciudad.name.ilike(nombre)).first()
            if ciudad_db and ciudad_db.lat is not None and ciudad_db.lon is not None:
                lugar.lat = ciudad_db.lat
                lugar.lon = ciudad_db.lon
                logger.info(f"Usando coordenadas de caché global para {nombre}: {lugar.lat}, {lugar.lon}")

    else:
        # Si NO cambiamos de nombre, actualizamos coordenadas si se envían
        try:
            if 'lat' in data and data['lat'] is not None and str(data['lat']).strip() != '':
                lugar.lat = float(data['lat'])
            if 'lon' in data and data['lon'] is not None and str(data['lon']).strip() != '':
                lugar.lon = float(data['lon'])
        except: pass

    # --- PERSISTENCIA GLOBAL ---
    # Si las coordenadas finales son válidas y no son (0,0), actualizamos la tabla Ciudad
    # para que este cambio sea persistente en todo el sistema.
    if lugar.lat != 0.0 or lugar.lon != 0.0:
        c_persist = Ciudad.query.filter(Ciudad.name.ilike(nombre)).first()
        if not c_persist:
            c_persist = Ciudad(name=nombre, lat=lugar.lat, lon=lugar.lon)
            db.session.add(c_persist)
        else:
            c_persist.lat = lugar.lat
            c_persist.lon = lugar.lon

    lugar.nombre = nombre
    lugar.frecuencia = frecuencia
    lugar.en_titulo = en_titulo
    lugar.en_contenido = en_contenido
    
    db.session.commit()
    return jsonify({'success': True})

# --- API para borrar manualmente una ciudad de la cartografía de la noticia ---
from extensions import csrf

@noticias_bp.route('/api/cartografia_noticia_delete_location/<int:id>', methods=['POST'], endpoint='cartografia_noticia_delete_location')
@csrf.exempt
@login_required
def cartografia_noticia_delete_location(id):
    noticia = db.session.get(Prensa, id)
    if not noticia:
        return jsonify({'success': False, 'error': 'Noticia no encontrada'}), 404
    try:
        data = request.get_json(force=True)
    except Exception as e:
        print(f"[cartografia_noticia_delete_location] Error al parsear JSON: {e}")
        return jsonify({'success': False, 'error': 'JSON inválido'}), 400
    print(f"[cartografia_noticia_delete_location] Data recibida: {data}")
    nombre = data.get('nombre') if data else None
    if not nombre:
        print("[cartografia_noticia_delete_location] Nombre no proporcionado")
        return jsonify({'success': False, 'error': 'Nombre requerido'}), 400
    lugar = LugarNoticia.query.filter_by(noticia_id=noticia.id, nombre=nombre, borrado=False).first()
    if not lugar:
        print(f"[cartografia_noticia_delete_location] Lugar '{nombre}' no encontrado para noticia {noticia.id}")
        return jsonify({'success': False, 'error': 'Lugar no encontrado'}), 404
    lugar.borrado = True
    db.session.commit()
    print(f"[cartografia_noticia_delete_location] Lugar '{nombre}' marcado como borrado (persistente) para noticia {noticia.id}")

    # --- SYNC PROJECT-WIDE ---
    # Propagate the deletion to all other records of this location in the same project.
    # This ensures it disappears from Gestor de Ubicaciones and Mapa Corpus too.
    from utils import get_proyecto_activo
    proyecto = get_proyecto_activo()
    if proyecto:
        otros = LugarNoticia.query.join(Prensa).filter(
            Prensa.proyecto_id == proyecto.id,
            LugarNoticia.nombre == nombre,
            LugarNoticia.borrado == False,
            LugarNoticia.noticia_id != noticia.id  # Skip the one already updated above
        ).all()
        for o in otros:
            o.borrado = True
        db.session.commit()
        print(f'[SYNC] Propagated deletion of "{nombre}" to {len(otros)} other records in project {proyecto.id}')

    return jsonify({'success': True})

# --- API para verificar/desverificar una ubicación ---
@noticias_bp.route('/api/verificar_ciudad', methods=['POST'])
@csrf.exempt
@login_required
def api_verificar_ciudad():
    """Toggle verification status of a city and sync with current project"""
    try:
        from utils import get_proyecto_activo
        proyecto = get_proyecto_activo()
        
        data = request.get_json()
        nombre = data.get('nombre')
        verificada = data.get('verificada', False)
        
        if not nombre:
            return jsonify({'success': False, 'error': 'Nombre de ciudad no proporcionado'}), 400
            
        ciudad = Ciudad.query.filter(Ciudad.name.ilike(nombre)).first()
        if not ciudad:
            from models import LugarNoticia
            lugar_ref = LugarNoticia.query.filter(LugarNoticia.nombre.ilike(nombre), LugarNoticia.borrado == False).first()
            lat, lon = (lugar_ref.lat, lugar_ref.lon) if lugar_ref else (0.0, 0.0)
            
            ciudad = Ciudad(name=nombre, lat=lat, lon=lon, verificada=verificada, blacklisted=False)
            db.session.add(ciudad)
        else:
            ciudad.verificada = verificada
            if verificada:
                ciudad.blacklisted = False # Si se verifica, no puede estar en lista negra
            
        # ── Sincronizar con LugarNoticia del proyecto activo ─────────────────────
        if proyecto:
            from models import LugarNoticia
            subquery = db.session.query(LugarNoticia.id).join(Prensa).filter(
                Prensa.proyecto_id == proyecto.id,
                LugarNoticia.nombre == nombre
            )
            # Decouple verification from visibility: 
            # If verified=True, ensure it's not deleted. 
            # If verified=False, keep its current deletion status (don't force it to deleted).
            update_vals = {'verificada': verificada}
            if verificada:
                update_vals['borrado'] = False

            # Fetch IDs first to avoid SQLAlchemy error with joins in update
            ids_to_update = [r[0] for r in subquery.all()]
            LugarNoticia.query.filter(LugarNoticia.id.in_(ids_to_update)).update(
                update_vals, synchronize_session=False
            )
        # ────────────────────────────────────────────────────────────────────────
            
        db.session.commit()
        return jsonify({'success': True, 'nombre': nombre, 'verificada': verificada})
    except Exception as e:
        db.session.rollback()
        print(f"[api_verificar_ciudad] Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@noticias_bp.route('/api/verificar_batch', methods=['POST'])
@csrf.exempt
@login_required
def api_verificar_batch():
    """Batch update verification status for multiple cities"""
    try:
        data = request.get_json()
        items = data.get('items', [])
        
        if not items:
            return jsonify({'success': False, 'error': 'No se proporcionaron elementos'}), 400
            
        from models import LugarNoticia
        results = []
        
        for item in items:
            nombre = item.get('nombre')
            verificada = item.get('verificada', False)
            
            if not nombre: continue
            
            ciudad = Ciudad.query.filter(Ciudad.name.ilike(nombre)).first()
            if not ciudad:
                lugar_ref = LugarNoticia.query.filter(LugarNoticia.nombre.ilike(nombre), LugarNoticia.borrado == False).first()
                lat, lon = (lugar_ref.lat, lugar_ref.lon) if lugar_ref else (0.0, 0.0)
                ciudad = Ciudad(name=nombre, lat=lat, lon=lon, verificada=verificada)
                db.session.add(ciudad)
            else:
                ciudad.verificada = verificada
            
            results.append({'nombre': nombre, 'verificada': verificada})
            
        db.session.commit()
        return jsonify({'success': True, 'processed': len(results)})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@noticias_bp.route('/api/ubicacion/<int:ubicacion_id>/verificar', methods=['POST'])
@csrf.exempt
@login_required
def verificar_ubicacion(ubicacion_id):
    """Toggle verification status of a location"""
    try:
        ubicacion = LugarNoticia.query.get(ubicacion_id)
        if not ubicacion:
            return jsonify({'success': False, 'error': 'Ubicación no encontrada'}), 404
        
        # Get verified status from request
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No se proporcionaron datos'}), 400
        
        verificada = data.get('verificada', False)
        
        # Update and save
        ubicacion.verificada = verificada
        db.session.commit()
        
        print(f"[verificar_ubicacion] Ubicación {ubicacion_id} ({ubicacion.nombre}) verificada: {verificada}")
        
        return jsonify({
            'success': True,
            'ubicacion_id': ubicacion_id,
            'verificada': verificada
        })
    except Exception as e:
        db.session.rollback()
        print(f"[verificar_ubicacion] Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@noticias_bp.route('/api/ubicacion/<int:ubicacion_id>/vincular', methods=['POST'])
@csrf.exempt
@login_required
def vincular_ubicacion(ubicacion_id):
    """Toggle vinculación status of a location occurrence in a specific noticia
    
    Ahora maneja desvinculación por ocurrencia individual:
    - Al desvincular: incrementa frecuencia_desvinculada en 1
    - Al vincular: decrementa frecuencia_desvinculada en 1  
    - Si todas las ocurrencias están desvinculadas, marca vinculada=False
    """
    try:
        ubicacion = LugarNoticia.query.get(ubicacion_id)
        if not ubicacion:
            return jsonify({'success': False, 'error': 'Ubicación no encontrada'}), 404
        
        # Get vinculada status from request
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No se proporcionaron datos'}), 400
        
        vincular = data.get('vinculada', True)
        
        # Initialize frecuencia_desvinculada if it doesn't exist (retrocompatibility)
        if not hasattr(ubicacion, 'frecuencia_desvinculada') or ubicacion.frecuencia_desvinculada is None:
            ubicacion.frecuencia_desvinculada = 0
        
        # Calculate new values
        if vincular:
            # Vincular una ocurrencia: decrementar frecuencia_desvinculada
            if ubicacion.frecuencia_desvinculada > 0:
                ubicacion.frecuencia_desvinculada -= 1
        else:
            # Desvincular una ocurrencia: incrementar frecuencia_desvinculada
            if ubicacion.frecuencia_desvinculada < ubicacion.frecuencia:
                ubicacion.frecuencia_desvinculada += 1
            else:
                return jsonify({
                    'success': False, 
                    'error': 'No hay más ocurrencias para desvincular'
                }), 400
        
        # Update vinculada status based on frecuencia_desvinculada
        # Si todas las ocurrencias están desvinculadas, marcar como desvinculada
        if ubicacion.frecuencia_desvinculada >= ubicacion.frecuencia:
            ubicacion.vinculada = False
        # Si hay al menos una ocurrencia vinculada, marcar como vinculada
        elif ubicacion.frecuencia_desvinculada < ubicacion.frecuencia:
            ubicacion.vinculada = True
        
        db.session.commit()
        
        # Calculate effective frequency
        frecuencia_efectiva = ubicacion.frecuencia - ubicacion.frecuencia_desvinculada
        
        print(f"[vincular_ubicacion] Ubicación {ubicacion_id} ({ubicacion.nombre}) - "
              f"Frecuencia total: {ubicacion.frecuencia}, Desvinculadas: {ubicacion.frecuencia_desvinculada}, "
              f"Efectiva: {frecuencia_efectiva}, Vinculada: {ubicacion.vinculada}")
        
        return jsonify({
            'success': True,
            'ubicacion_id': ubicacion_id,
            'vinculada': ubicacion.vinculada,
            'frecuencia_desvinculada': ubicacion.frecuencia_desvinculada,
            'frecuencia_efectiva': frecuencia_efectiva,
            'nombre': ubicacion.nombre
        })
    except Exception as e:
        db.session.rollback()
        print(f"[vincular_ubicacion] Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


def _core_batch_verificar(nombres, verificada, all_pro=False, proyecto=None):
    """Lógica central para verificar/desverificar ubicaciones por lote"""
    if not proyecto:
        from utils import get_proyecto_activo
        proyecto = get_proyecto_activo()
    if not proyecto:
        return False, 'No hay proyecto activo', 400
        
    from models import LugarNoticia
    # Trim all names provided
    nombres = [n.strip() for n in nombres] if nombres else []
    
    query = LugarNoticia.query.join(Prensa).filter(
        Prensa.proyecto_id == proyecto.id
    )
    
    subquery_ids = db.session.query(LugarNoticia.id).join(Prensa).filter(
        Prensa.proyecto_id == proyecto.id
    )
    
    if not all_pro:
        if not nombres:
            return False, 'Nombres requeridos si all_project es False', 400
        # Use ILIKE or ensure case consistency
        subquery_ids = subquery_ids.filter(LugarNoticia.nombre.in_(nombres))
    
    # Update LugarNoticia: 
    # Decouple verification from visibility:
    # If verified=True, ensure it's not deleted.
    # If verified=False, keep current visibility status (don't force deleted).
    update_vals = {LugarNoticia.verificada: verificada}
    if verificada:
        update_vals[LugarNoticia.borrado] = False

    # Materialize IDs to avoid SQLAlchemy error with joins in update
    ids_to_update = [r[0] for r in subquery_ids.all()]
    updated_count = LugarNoticia.query.filter(LugarNoticia.id.in_(ids_to_update)).update(update_vals, synchronize_session=False)
    
    # ── Sincronizar con tabla Ciudad para consistencia global ────────────────
    # nombres_actuales debe incluir TODOS los que se han actualizado (también los borrados)
    # si queremos que el estado de 'verificada' se refleje en la tabla global Ciudad.
    if all_pro:
        nombres_actuales = [
            r[0] for r in db.session.query(LugarNoticia.nombre).join(Prensa).filter(
                Prensa.proyecto_id == proyecto.id
            ).distinct().all()
        ]
    else:
        nombres_actuales = nombres

    for nombre in nombres_actuales:
        nombre = nombre.strip()
        ciudad = Ciudad.query.filter(Ciudad.name.ilike(nombre)).first()
        if ciudad:
            ciudad.verificada = verificada
            if verificada:  # Si se verifica, quitar de blacklist
                ciudad.blacklisted = False
            # Fix corrupted (0,0) or null if verifying
            if verificada and (ciudad.lat == 0 or ciudad.lat is None):
                lugar_ref = LugarNoticia.query.filter(LugarNoticia.nombre.ilike(nombre), LugarNoticia.lat != 0).first()
                if lugar_ref:
                    ciudad.lat, ciudad.lon = lugar_ref.lat, lugar_ref.lon
        elif verificada: # Si estamos verificando y no existe en Ciudad, crearla
            lugar_ref = LugarNoticia.query.filter(LugarNoticia.nombre.ilike(nombre), LugarNoticia.lat != 0).first()
            lat, lon = (lugar_ref.lat, lugar_ref.lon) if lugar_ref else (None, None)
            if lat is not None:
                ciudad = Ciudad(name=nombre, lat=lat, lon=lon, verificada=True, blacklisted=False)
                db.session.add(ciudad)
    # ─────────────────────────────────────────────────────────────
    
    db.session.commit()
    return True, updated_count, 200

@noticias_bp.route('/api/cartografia/gestion/batch_verificar', methods=['POST'])
@login_required
@csrf.exempt
def api_batch_verificar_ubicaciones():
    """Batch verify locations by name (unique per project)"""
    try:
        data = request.get_json() or {}
        nombres = data.get('nombres', [])
        verificada = data.get('verificada', True)
        all_pro = data.get('all_project', False)
        
        success, result, code = _core_batch_verificar(nombres, verificada, all_pro)
        if not success:
            return jsonify({'success': False, 'error': result}), code
            
        return jsonify({
            'success': True,
            'updated_count': result,
            'verificada': verificada
        })
    except Exception as e:
        db.session.rollback()
        print(f"[api_batch_verificar_ubicaciones] Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@noticias_bp.route('/api/cartografia/gestion/verificar_geo', methods=['GET'])
@login_required
def api_verificar_geo():
    """Search coordinates for a given location name using Nominatim/IA"""
    q = request.args.get('q', '').strip()
    if not q:
        return jsonify({'results': []})
        
    try:
        # 0. Check if it's already a lat/lon pair (e.g. "40.123, -3.456")
        coord_match = re.search(r'(-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)', q)
        if coord_match:
            try:
                lat = float(coord_match.group(1))
                lon = float(coord_match.group(2))
                return jsonify({'results': [{
                    'lat': lat, 
                    'lon': lon, 
                    'display_name': f"Manual ({lat}, {lon})"
                }]})
            except: pass

        # 1. Check internal Ciudad cache first
        c_internal = Ciudad.query.filter(Ciudad.name.ilike(q)).first()
        if c_internal and c_internal.lat is not None and c_internal.lon is not None:
             return jsonify({'results': [{'lat': c_internal.lat, 'lon': c_internal.lon, 'display_name': c_internal.name + " (Internal)"}]})

        # 2. External Search
        import requests
        resp = requests.get('https://nominatim.openstreetmap.org/search', params={
            'q': q, 'format': 'json', 'limit': 1
        }, headers={'User-Agent': 'app-hesiox/1.0'}, timeout=5)
        data = resp.json()
        
        results = []
        if data:
            results.append({
                'lat': float(data[0].get('lat', 0)),
                'lon': float(data[0].get('lon', 0)),
                'display_name': data[0].get('display_name', q)
            })
        
        return jsonify({'results': results})
    except Exception as e:
        print(f"[api_verificar_geo] Error: {e}")
        return jsonify({'results': []}), 500

@noticias_bp.route('/api/cartografia/gestion/batch_unverify', methods=['POST'])
@login_required
@csrf.exempt
def api_batch_unverify_ubicaciones():
    """Batch unverify locations"""
    try:
        data = request.get_json() or {}
        nombres = data.get('nombres', [])
        all_pro = data.get('all_project', False)
        
        success, result, code = _core_batch_verificar(nombres, False, all_pro)
        if not success:
            return jsonify({'success': False, 'error': result}), code
            
        return jsonify({
            'success': True,
            'updated_count': result,
            'verificada': False,
            'borrado': True
        })
    except Exception as e:
        db.session.rollback()
        print(f"[api_batch_unverify_ubicaciones] Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# --- Vista de mapa global del corpus ---
@noticias_bp.route('/mapa_corpus', methods=['GET'])
@login_required
def mapa_corpus():
    from utils import get_proyecto_activo
    proyecto = get_proyecto_activo()
    if proyecto:
        publicaciones = [p.nombre for p in Publicacion.query.filter_by(proyecto_id=proyecto.id).order_by(Publicacion.nombre.asc()).all()]
    else:
        flash("Debes seleccionar un proyecto para ver el mapa del corpus.", "warning")
        return redirect(url_for('proyectos.listar'))
    return render_template('mapa_corpus.html', publicaciones=publicaciones)


# ============================================================================
# API CRUD: CAPAS VECTORIALES GIS
# ============================================================================

@noticias_bp.route('/api/vector_layers', methods=['GET'])
@csrf.exempt
@login_required
def api_get_vector_layers():
    """Obtiene todas las capas vectoriales del proyecto activo"""
    from utils import get_proyecto_activo
    from models import VectorLayer
    
    proyecto = get_proyecto_activo()
    if not proyecto:
        return jsonify({'error': 'No hay proyecto activo'}), 400
    
    layers = VectorLayer.query.filter_by(proyecto_id=proyecto.id).order_by(VectorLayer.orden.asc(), VectorLayer.creado_en.desc()).all()
    return jsonify([layer.to_dict() for layer in layers])


@noticias_bp.route('/api/vector_layers/<int:layer_id>', methods=['GET'])
@csrf.exempt
@login_required
def api_get_vector_layer(layer_id):
    """Obtiene una capa vectorial específica"""
    from models import VectorLayer
    from utils import get_proyecto_activo
    
    proyecto = get_proyecto_activo()
    if not proyecto:
        return jsonify({'error': 'No hay proyecto activo'}), 400
    
    layer = VectorLayer.query.filter_by(id=layer_id, proyecto_id=proyecto.id).first()
    if not layer:
        return jsonify({'error': 'Capa no encontrada'}), 404
    
    return jsonify(layer.to_dict())


@noticias_bp.route('/api/vector_layers', methods=['POST'])
@csrf.exempt
@login_required
def api_create_vector_layer():
    """Crea una nueva capa vectorial"""
    from utils import get_proyecto_activo
    from models import VectorLayer
    from extensions import db
    import json
    
    proyecto = get_proyecto_activo()
    if not proyecto:
        return jsonify({'error': 'No hay proyecto activo'}), 400
    
    data = request.get_json()
    
    if not data.get('nombre'):
        return jsonify({'error': 'El nombre es obligatorio'}), 400
    
    try:
        geojson = data.get('geojson', {"type": "FeatureCollection", "features": []})
        features = geojson.get('features', [])
        
        # Calcular área y longitud inicial
        from services.geo_calculations import calculate_layer_metrics
        metrics = calculate_layer_metrics(features)
        area_total = metrics.get('area_total')
        longitud_total = metrics.get('longitud_total')
        
        layer = VectorLayer(
            proyecto_id=proyecto.id,
            nombre=data['nombre'],
            descripcion=data.get('descripcion', ''),
            tipo_geometria=data.get('tipo_geometria', 'mixed'),
            color=data.get('color', '#ff9800'),
            opacidad=data.get('opacidad', 0.7),
            grosor_linea=data.get('grosor_linea', 3),
            visible=data.get('visible', True),
            bloqueada=data.get('bloqueada', False),
            geojson_data=json.dumps(geojson),
            num_features=len(features),
            area_total=area_total,
            longitud_total=longitud_total,
            creado_por=current_user.id,
            modificado_por=current_user.id
        )
        
        db.session.add(layer)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'layer': layer.to_dict(),
            'message': f'Capa "{layer.nombre}" creada correctamente'
        }), 201
        
    except Exception as e:
        db.session.rollback()
        print(f"[api_create_vector_layer] Error: {e}")
        return jsonify({'error': str(e)}), 500


@noticias_bp.route('/api/vector_layers/<int:layer_id>', methods=['PUT'])
@csrf.exempt
@login_required
def api_update_vector_layer(layer_id):
    """Actualiza una capa vectorial existente"""
    from utils import get_proyecto_activo
    from models import VectorLayer
    from extensions import db
    import json
    
    proyecto = get_proyecto_activo()
    if not proyecto:
        return jsonify({'error': 'No hay proyecto activo'}), 400
    
    layer = VectorLayer.query.filter_by(id=layer_id, proyecto_id=proyecto.id).first()
    if not layer:
        return jsonify({'error': 'Capa no encontrada'}), 404
    
    data = request.get_json()
    
    try:
        # Actualizar campos básicos
        if 'nombre' in data:
            layer.nombre = data['nombre']
        if 'descripcion' in data:
            layer.descripcion = data['descripcion']
        if 'color' in data:
            layer.color = data['color']
        if 'opacidad' in data:
            layer.opacidad = data['opacidad']
        if 'grosor_linea' in data:
            layer.grosor_linea = data['grosor_linea']
        if 'visible' in data:
            layer.visible = data['visible']
        if 'bloqueada' in data:
            layer.bloqueada = data['bloqueada']
        if 'etiquetas_visibles' in data:
            layer.etiquetas_visibles = data['etiquetas_visibles']
        if 'snap_enabled' in data:
            layer.snap_enabled = data['snap_enabled']
        
        # Actualizar GeoJSON y recalcular métricas
        if 'geojson' in data:
            geojson = data['geojson']
            layer.geojson_data = json.dumps(geojson)
            
            # Recalcular número de features
            features = geojson.get('features', [])
            layer.num_features = len(features)
            
            # Calcular área y longitud totales si aplica
            from services.geo_calculations import calculate_layer_metrics
            metrics = calculate_layer_metrics(features)
            layer.area_total = metrics.get('area_total')
            layer.longitud_total = metrics.get('longitud_total')
        
        # Actualizar vínculos con noticias
        if 'vinculado_noticias' in data:
            layer.vinculado_noticias = json.dumps(data['vinculado_noticias'])
        
        layer.modificado_por = current_user.id
        db.session.commit()
        
        return jsonify({
            'success': True,
            'layer': layer.to_dict(),
            'message': f'Capa "{layer.nombre}" actualizada correctamente'
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"[api_update_vector_layer] Error: {e}")
        return jsonify({'error': str(e)}), 500


@noticias_bp.route('/api/vector_layers/<int:layer_id>', methods=['DELETE'])
@csrf.exempt
@login_required
def api_delete_vector_layer(layer_id):
    """Elimina una capa vectorial"""
    from utils import get_proyecto_activo
    from models import VectorLayer
    from extensions import db
    
    proyecto = get_proyecto_activo()
    if not proyecto:
        return jsonify({'error': 'No hay proyecto activo'}), 400
    
    layer = VectorLayer.query.filter_by(id=layer_id, proyecto_id=proyecto.id).first()
    if not layer:
        return jsonify({'error': 'Capa no encontrada'}), 404
    
    try:
        nombre = layer.nombre
        db.session.delete(layer)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Capa "{nombre}" eliminada correctamente'
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"[api_delete_vector_layer] Error: {e}")
        return jsonify({'error': str(e)}), 500


@noticias_bp.route('/api/vector_layers/<int:layer_id>/export', methods=['GET'])
@csrf.exempt
@login_required
def api_export_vector_layer(layer_id):
    """Exporta una capa vectorial como GeoJSON descargable"""
    from utils import get_proyecto_activo
    from models import VectorLayer
    from flask import make_response
    import json
    
    proyecto = get_proyecto_activo()
    if not proyecto:
        return jsonify({'error': 'No hay proyecto activo'}), 400
    
    layer = VectorLayer.query.filter_by(id=layer_id, proyecto_id=proyecto.id).first()
    if not layer:
        return jsonify({'error': 'Capa no encontrada'}), 404
    
    try:
        geojson = json.loads(layer.geojson_data)
        
        # Añadir metadatos adicionales
        geojson['name'] = layer.nombre
        geojson['description'] = layer.descripcion
        geojson['crs'] = {
            "type": "name",
            "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}
        }
        
        # Crear respuesta descargable
        response = make_response(json.dumps(geojson, indent=2, ensure_ascii=False))
        response.headers['Content-Type'] = 'application/geo+json; charset=utf-8'
        response.headers['Content-Disposition'] = f'attachment; filename="{layer.nombre.replace(" ", "_")}.geojson"'
        
        return response
        
    except Exception as e:
        print(f"[api_export_vector_layer] Error: {e}")
        return jsonify({'error': str(e)}), 500


@noticias_bp.route('/api/vector_layers/import', methods=['POST'])
@csrf.exempt
@login_required
def api_import_vector_layer():
    """Importa una capa vectorial desde archivo GeoJSON/KML/GPX"""
    from utils import get_proyecto_activo
    from models import VectorLayer
    from extensions import db
    import json
    
    proyecto = get_proyecto_activo()
    if not proyecto:
        return jsonify({'error': 'No hay proyecto activo'}), 400
    
    if 'file' not in request.files:
        return jsonify({'error': 'No se proporcionó archivo'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Archivo vacío'}), 400
    
    try:
        content = file.read().decode('utf-8')
        
        # Intentar parsear como GeoJSON
        geojson = json.loads(content)
        
        if geojson.get('type') != 'FeatureCollection':
            return jsonify({'error': 'El archivo debe ser un FeatureCollection válido'}), 400
        
        # Crear nueva capa con el contenido importado
        nombre = request.form.get('nombre', file.filename.rsplit('.', 1)[0])
        
        layer = VectorLayer(
            proyecto_id=proyecto.id,
            nombre=nombre,
            descripcion=request.form.get('descripcion', f'Importado desde {file.filename}'),
            tipo_geometria='mixed',
            geojson_data=json.dumps(geojson),
            color=request.form.get('color', '#ff9800'),
            num_features=len(geojson.get('features', [])),
            creado_por=current_user.id,
            modificado_por=current_user.id
        )
        
        db.session.add(layer)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'layer': layer.to_dict(),
            'message': f'Capa "{layer.nombre}" importada correctamente con {layer.num_features} elementos'
        }), 201
        
    except json.JSONDecodeError:
        return jsonify({'error': 'El archivo no es un JSON válido'}), 400
    except Exception as e:
        db.session.rollback()
        print(f"[api_import_vector_layer] Error: {e}")
        return jsonify({'error': str(e)}), 500


@noticias_bp.route('/api/vector_layers/reorder', methods=['POST'])
@csrf.exempt
@login_required
def api_reorder_vector_layers():
    """Actualiza el orden de múltiples capas vectoriales de un proyecto"""
    from utils import get_proyecto_activo
    from models import VectorLayer
    from extensions import db
    
    proyecto = get_proyecto_activo()
    if not proyecto:
        return jsonify({'error': 'No hay proyecto activo'}), 400
    
    data = request.get_json()
    order_map = data.get('order', []) # Array de {id: X, orden: Y}
    
    try:
        for item in order_map:
            layer_id = item.get('id')
            nuevo_orden = item.get('orden')
            if layer_id is not None and nuevo_orden is not None:
                VectorLayer.query.filter_by(id=layer_id, proyecto_id=proyecto.id).update(
                    {VectorLayer.orden: nuevo_orden}, synchronize_session=False
                )
        
        db.session.commit()
        return jsonify({'success': True, 'message': 'Orden de capas actualizado'})
    except Exception as e:
        db.session.rollback()
        print(f"[api_reorder_vector_layers] Error: {e}")
        return jsonify({'error': str(e)}), 500


@noticias_bp.route('/api/vector_layers/migrate', methods=['GET'])
@login_required
def api_migrate_vector_layers():
    """Migración temporal para añadir columna 'orden' si no existe"""
    if current_user.rol != 'admin':
        return jsonify({'error': 'Solo administradores'}), 403
    
    from extensions import db
    try:
        # Intentar añadir la columna usando SQL crudo para mayor seguridad en migraciones manuales
        db.session.execute(text("ALTER TABLE vector_layers ADD COLUMN IF NOT EXISTS orden INTEGER DEFAULT 0"))
        db.session.execute(text("ALTER TABLE vector_layers ADD COLUMN IF NOT EXISTS bloqueada BOOLEAN DEFAULT FALSE"))
        db.session.commit()
        return jsonify({'success': True, 'message': 'Columna "orden" verificada/añadida correctamente'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@noticias_bp.route('/api/noticias_por_publicacion', methods=['GET'])
@login_required
def api_noticias_por_publicacion():
    publicacion = request.args.get('publicacion')
    from utils import get_proyecto_activo
    proyecto = get_proyecto_activo()
    if not proyecto or not publicacion:
        return jsonify([])
    
    query = Prensa.query.filter_by(proyecto_id=proyecto.id, publicacion=publicacion, incluido=True)
    # Use the same ordering as the main news list (by date ASC, then by ID ASC)
    query = ordenar_por_fecha_prensa(query, descendente=False)
    noticias = query.all()
    
    res = [{
        'id': n.id,
        'titulo': n.titulo,
        'fecha': n.fecha_original if n.fecha_original else 'S/F'
    } for n in noticias]
    return jsonify(res)

# --- API para cartografía global del corpus ---
# Cache simple para geocodificación
_geo_cache = {}

# --- API para gestión masiva de ubicaciones (Panel Global) ---

@noticias_bp.route('/api/batch_geocoding', methods=['POST'])
@login_required
def api_batch_geocoding():
    """
    API para procesar por lotes noticias sin ubicaciones detectadas.
    Soporta modo 'base' (spaCy) y modo 'ai' (Gemini).
    """
    import logging
    app_logger = logging.getLogger('app')
    
    try:
        from utils import get_proyecto_activo, get_nlp
        proyecto = get_proyecto_activo()
        if not proyecto:
            return jsonify({'error': 'No hay proyecto activo'}), 400

        from models import LugarNoticia, Ciudad, Prensa, Publicacion
        from extensions import db
        import requests
        from collections import Counter
        import time

        data_request = request.get_json() or {}
        use_ai = data_request.get('use_ai', False)

        # Marcador específico según el tipo de procesamiento
        tag_procesado = "__PROCESSED_IA__" if use_ai else "__PROCESSED_BASE__"
        tipo_lugar = 'extraido_ai' if use_ai else 'extraido'

        # Buscamos noticias que aún no han sido procesadas POR ESTE MODO específico
        subquery = db.session.query(LugarNoticia.noticia_id).filter(
            LugarNoticia.nombre == tag_procesado
        ).distinct()

        # Si una noticia tiene lugares del tipo que buscamos, también la consideramos procesada
        subquery_tipo = db.session.query(LugarNoticia.noticia_id).filter(
            LugarNoticia.tipo == tipo_lugar
        ).distinct()
        
        # Lote de procesamiento
        limit = 3 if use_ai else 2
        noticias_pendientes = Prensa.query.filter(
            Prensa.proyecto_id == proyecto.id,
            ~Prensa.id.in_(subquery),
            ~Prensa.id.in_(subquery_tipo)
        ).limit(limit).all()

        if not noticias_pendientes:
            return jsonify({'status': 'finished', 'processed': 0, 'remaining': 0})

        if use_ai:
            from services.ai_service import AIService
            
            # ── MAPA DE MODELOS (UI value → provider, model) ──────────────────────────
            POTENCIA_MAP = {
                'flash':          ('gemini', 'gemini-2.0-flash'),
                'pro':            ('gemini', 'gemini-1.5-pro'),
                'gemini-3-flash': ('gemini', 'gemini-3-flash'),
                'gemini-3-pro':   ('gemini', 'gemini-3-pro'),
                'openai':         ('openai', 'gpt-4o'),
                'anthropic':      ('anthropic', 'claude-3-5-sonnet-20240620'),
                'llama':          ('llama', 'llama3'),
            }
            potencia = data_request.get('potencia', 'flash')
            provider, model = POTENCIA_MAP.get(potencia, ('gemini', 'gemini-2.0-flash'))
            # ───────────────────────────────────────────────────────────────────────────
            
            ai_service = AIService(provider=provider, model=model, user=current_user)
            app_logger.info(f"[BATCH-GEO] Iniciando lote IA [{potencia} → {provider}/{model}] proyecto {proyecto.id} (limit={limit})")
        else:
            nlp = get_nlp()
            if not nlp: return jsonify({'error': 'Modelo de IA base no disponible'}), 500
            app_logger.info(f"[BATCH-GEO] Iniciando lote Base (spaCy) para proyecto {proyecto.id} (limit={limit})")

        processed_this_batch = 0
        GEO_LABELS = {'LOC', 'GPE'}
        
        # ── LISTA DE EXCLUSIÓN: LOCAL (proyecto) + GLOBAL (Ciudad blacklisted) ─────────────
        excluded_loc_names = {
            r[0].strip().lower() for r in db.session.query(LugarNoticia.nombre).join(Prensa).filter(
                Prensa.proyecto_id == proyecto.id,
                LugarNoticia.borrado == True
            ).distinct().all()
        }
        # Cargar lista negra global de Ciudad (borradas por algún proyecto previo)
        blacklist_global = {
            r[0].strip().lower() for r in db.session.query(Ciudad.name).filter(
                Ciudad.blacklisted == True
            ).all()
        }
        excluded_loc_names |= blacklist_global  # unión de ambos sets
        app_logger.info(f"[BATCH-GEO] Exclusions: {len(excluded_loc_names)} nombres (proyecto={len(excluded_loc_names)-len(blacklist_global)}, global={len(blacklist_global)})")
        # ─────────────────────────────────────────────────────────────────────────────

        for noticia in noticias_pendientes:
            lugares_detectados = set()
            conteo = Counter()
            
            # Obtener lugares que ya existen para esta noticia (para evitar duplicados exactos)
            existing_loc_names = {l.nombre.strip().lower() for l in LugarNoticia.query.filter_by(noticia_id=noticia.id).all()}

            if use_ai:
                # Extracción con AIService (Multi-Proveedor)
                pub = Publicacion.query.get(noticia.id_publicacion) if noticia.id_publicacion else None
                contexto = {
                    "periódico": pub.nombre if pub else "Desconocido",
                    "año": noticia.fecha_original.year if noticia.fecha_original and hasattr(noticia.fecha_original, 'year') else None
                }
                texto_completo = noticia.titulo + "\n" + (noticia.contenido or "")
                res_ai = ai_service.extract_locations(texto_completo, contexto)
                if res_ai and 'locations' in res_ai:
                    from services.gemini_service import clean_location_name, is_valid_location_in_text
                    for loc in res_ai['locations']:
                        nombre = loc.get('normalized') or loc.get('original')
                        nombre = clean_location_name(nombre)
                        confidence = loc.get('confidence', 1.0)
                        
                        # FILTRO CRÍTICO: Si la IA no está segura o es un sustantivo común, omitir
                        if confidence < 0.6:
                            app_logger.info(f"[BATCH-GEO] Omitiendo '{nombre}' por baja confianza ({confidence})")
                            continue
                        
                        # Validar que sea una palabra completa, no parte de otra palabra
                        if not is_valid_location_in_text(nombre, texto_completo):
                            app_logger.info(f"[BATCH-GEO] Omitiendo '{nombre}' - no es palabra completa (gentilicio u otra subcadena)")
                            continue

                        if nombre and nombre.strip().lower() not in existing_loc_names and nombre.strip().lower() not in excluded_loc_names:
                            lugares_detectados.add(nombre)
                            conteo[nombre] = loc.get('importance', 1)
            else:
                # Extracción con spaCy
                from services.gemini_service import clean_location_name, is_valid_location_in_text
                texto_completo = (noticia.titulo or "") + "\n" + (noticia.contenido or "")
                doc = nlp(texto_completo)
                # Extraer, limpiar y filtrar
                raw_locs = [ent.text.strip() for ent in doc.ents if ent.label_ in GEO_LABELS and len(ent.text.strip()) > 2]
                locs_cleaned = []
                for rl in raw_locs:
                    c_loc = clean_location_name(rl)
                    if c_loc and len(c_loc) > 2 and c_loc[0].isupper():
                        # Validar que sea una palabra completa, no parte de otra palabra
                        if is_valid_location_in_text(c_loc, texto_completo):
                            # Solo añadir si no fue borrado globalmente
                            if c_loc.lower() not in excluded_loc_names:
                                locs_cleaned.append(c_loc)
                
                for loc in locs_cleaned:
                    if loc.lower() not in existing_loc_names:
                        if len(lugares_detectados) < 15: lugares_detectados.add(loc)
                conteo.update([l for l in locs_cleaned if l.lower() not in existing_loc_names])
            
            # --- DEDUPLICACIÓN DE ANIDAMIENTO ---
            if conteo:
                from services.gemini_service import merge_nested_locations
                conteo_dedup = merge_nested_locations(conteo)
                lugares_detectados = set(conteo_dedup.keys())
                conteo = Counter(conteo_dedup)

            # Procesar y geocodificar solo los nuevos
            if not lugares_detectados:
                # Añadimos el marcador de procesado incluso si no hay nada nuevo, para no re-intentar en bucle
                marca = LugarNoticia(noticia_id=noticia.id, nombre=tag_procesado, lat=0, lon=0, frecuencia=0, tipo=tipo_lugar, borrado=True)
                db.session.add(marca)
                db.session.commit()
            else:
                for lugar_nombre in lugares_detectados:
                    lugar_nombre = lugar_nombre.strip()
                    if not lugar_nombre: continue
                    
                    ciudad_db = Ciudad.query.filter_by(name=lugar_nombre).first()
                    lat, lon = None, None
                    
                    if ciudad_db and ciudad_db.lat is not None and ciudad_db.lon is not None:
                        lat, lon = ciudad_db.lat, ciudad_db.lon
                    else:
                        try:
                            # Añadimos countrycodes=es para priorizar España en proyectos del Quijote/Hispánicos
                            resp = requests.get('https://nominatim.openstreetmap.org/search', 
                                              params={'q': lugar_nombre, 'format': 'json', 'limit': 1, 'countrycodes': 'es'}, 
                                              headers={'User-Agent': 'Hesiox-Batch-Bot/1.1'}, timeout=5)
                            data_geo = resp.json()
                            if data_geo:
                                lat, lon = float(data_geo[0]['lat']), float(data_geo[0]['lon'])
                                if not ciudad_db:
                                    ciudad_db = Ciudad(name=lugar_nombre, lat=lat, lon=lon)
                                    db.session.add(ciudad_db)
                                else:
                                    ciudad_db.lat, ciudad_db.lon = lat, lon
                                db.session.commit()
                            time.sleep(1.1)
                        except Exception as e: print(f"Error geo {lugar_nombre}: {e}")
                    
                    if lat is not None and lon is not None:
                        # Doble check de seguridad por concurrencia
                        if not LugarNoticia.query.filter_by(noticia_id=noticia.id, nombre=lugar_nombre).first():
                            nuevo = LugarNoticia(noticia_id=noticia.id, nombre=lugar_nombre, lat=lat, lon=lon, frecuencia=conteo.get(lugar_nombre, 1), tipo=tipo_lugar, borrado=False)
                            db.session.add(nuevo)
                
                # Al final de una noticia con éxito, también marcamos como procesada por este modo
                marca = LugarNoticia(noticia_id=noticia.id, nombre=tag_procesado, lat=0, lon=0, frecuencia=0, tipo=tipo_lugar, borrado=True)
                db.session.add(marca)
                db.session.commit()
            
            processed_this_batch += 1
        
        # Calcular cuántas quedan (usando la misma lógica aditiva)
        remaining = Prensa.query.filter(
            Prensa.proyecto_id == proyecto.id,
            ~Prensa.id.in_(subquery),
            ~Prensa.id.in_(subquery_tipo)
        ).count()

        return jsonify({'status': 'processing', 'processed': processed_this_batch, 'remaining': remaining})

    except Exception as e:
        app_logger.exception(f"Error crítico en api_batch_geocoding: {e}")
        return jsonify({'error': str(e)}), 500

@noticias_bp.route('/api/cartografia/gestion/borrar', methods=['POST'])
@noticias_bp.route('/api/cartografia/gestion/eliminar', methods=['POST'], endpoint='gestion_eliminar_ubicacion')
@login_required
@csrf.exempt
def gestion_borrar_ubicacion():
    from utils import get_proyecto_activo
    proyecto = get_proyecto_activo()
    if not proyecto:
        return jsonify({'success': False, 'error': 'No hay proyecto activo'}), 400

    data = request.get_json()
    nombre = data.get('nombre')
    if not nombre:
        return jsonify({'success': False, 'error': 'Nombre requerido'}), 400
    
    # Marcado lógico de borrado en todas las instancias DE ESTE PROYECTO
    try:
        # Subquery para obtener los IDs de LugarNoticia vinculados a este proyecto
        subquery = db.session.query(LugarNoticia.id).join(Prensa).filter(
            Prensa.proyecto_id == proyecto.id,
            LugarNoticia.nombre == nombre,
            LugarNoticia.borrado == False
        )
        
        ids_to_update = [r[0] for r in subquery.all()]
        cnt = LugarNoticia.query.filter(LugarNoticia.id.in_(ids_to_update)).update(
            {'borrado': True, 'verificada': False}, synchronize_session=False
        )
        
        # ── LISTA NEGRA GLOBAL ──────────────────────────────────────────────────
        # Marcar en tabla Ciudad para que todo proyecto futuro omita este nombre en NER
        ciudad = Ciudad.query.filter(Ciudad.name.ilike(nombre)).first()
        if not ciudad:
            # Buscar coordenadas de referencia para crear la entrada
            lugar_ref = LugarNoticia.query.filter(
                LugarNoticia.nombre.ilike(nombre),
                LugarNoticia.lat.isnot(None)
            ).first()
            lat_ref = lugar_ref.lat if lugar_ref else 0.0
            lon_ref = lugar_ref.lon if lugar_ref else 0.0
            ciudad = Ciudad(name=nombre, lat=lat_ref, lon=lon_ref, verificada=False, blacklisted=True)
            db.session.add(ciudad)
        else:
            ciudad.blacklisted = True
            ciudad.verificada = False  # Si se borra, ya no está verificada
        # ────────────────────────────────────────────────────────────────────────
        
        db.session.commit()
        print(f"[gestion_borrar_ubicacion] '{nombre}' borrado ({cnt} instancias). Blacklisted globalmente.")
        return jsonify({'success': True, 'affected': cnt})
    except Exception as e:
        db.session.rollback()
        print(f"[gestion_borrar_ubicacion] Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@noticias_bp.route('/api/cartografia/gestion/restaurar', methods=['POST'])
@login_required
@csrf.exempt
def gestion_restaurar_ubicacion():
    from utils import get_proyecto_activo
    proyecto = get_proyecto_activo()
    if not proyecto:
        return jsonify({'success': False, 'error': 'No hay proyecto activo'}), 400

    data = request.get_json()
    nombre = data.get('nombre')
    if not nombre:
        return jsonify({'success': False, 'error': 'Nombre requerido'}), 400
    
    try:
        subquery = db.session.query(LugarNoticia.id).join(Prensa).filter(
            Prensa.proyecto_id == proyecto.id,
            LugarNoticia.nombre == nombre,
            LugarNoticia.borrado == True
        )
        
        ids_to_update = [r[0] for r in subquery.all()]
        cnt = LugarNoticia.query.filter(LugarNoticia.id.in_(ids_to_update)).update(
            {'borrado': False}, synchronize_session=False
        )
        
        # ── QUITAR DE LISTA NEGRA GLOBAL ──────────────────────────────────────
        ciudad = Ciudad.query.filter(Ciudad.name.ilike(nombre)).first()
        if ciudad:
            ciudad.blacklisted = False
        # ─────────────────────────────────────────────────────────────────────
        
        db.session.commit()
        print(f"[gestion_restaurar_ubicacion] '{nombre}' restaurado ({cnt} instancias). Quitado de blacklist.")
        return jsonify({'success': True, 'affected': cnt})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
@noticias_bp.route('/api/cartografia/gestion/limpiar_referencias', methods=['POST'])
@login_required
@csrf.exempt
def gestion_limpiar_referencias():
    from utils import get_proyecto_activo
    proyecto = get_proyecto_activo()
    if not proyecto:
        return jsonify({'success': False, 'error': 'No hay proyecto activo'}), 400

    data = request.get_json()
    nombre = data.get('nombre')
    nombres = data.get('nombres', [])
    if not nombres and nombre:
        nombres = [nombre]
    
    if not nombres:
        return jsonify({'success': False, 'error': 'Nombres requeridos'}), 400
    
    try:
        affected_count = 0
        for n_limpiar in nombres:
            # Capturar estado previo
            ref = LugarNoticia.query.join(Prensa).filter(
                Prensa.proyecto_id == proyecto.id,
                LugarNoticia.nombre.ilike(n_limpiar)
            ).order_by(LugarNoticia.verificada.desc(), LugarNoticia.lat.isnot(None).desc()).first()
            
            if not ref: continue
            
            is_v = ref.verificada
            is_b = ref.borrado
            b_lat, b_lon = ref.lat, ref.lon
            
            # Borrar todos
            subquery = db.session.query(LugarNoticia.id).join(Prensa).filter(
                Prensa.proyecto_id == proyecto.id,
                LugarNoticia.nombre.ilike(n_limpiar)
            )
            ids_to_delete = [r[0] for r in subquery.all()]
            cnt = LugarNoticia.query.filter(LugarNoticia.id.in_(ids_to_delete)).delete(synchronize_session=False)
            affected_count += cnt
            
            # Crear placeholder 0
            pn = Prensa.query.filter_by(proyecto_id=proyecto.id).first()
            if pn:
                ln = LugarNoticia(
                    noticia_id=pn.id,
                    nombre=n_limpiar,
                    lat=b_lat, lon=b_lon,
                    verificada=is_v, borrado=is_b,
                    frecuencia=0, frec_titulo=0, frec_contenido=0,
                    tipo='extraido'
                )
                db.session.add(ln)
        
        db.session.commit()
        return jsonify({'success': True, 'affected': affected_count})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

def sync_lugar_noticia(nombre, proyecto_id):
    """Auxiliar para sincronizar un lugar con todas las noticias de un proyecto."""
    # 1. Obtener coordenadas, ESTADO y FRECUENCIAS DESVINCULADAS de referencia ANTES de borrar
    # Buscamos ilike para atrapar variantes de caja (EL TOBOSO vs El Toboso)
    ref = LugarNoticia.query.join(Prensa).filter(
        Prensa.proyecto_id == proyecto_id,
        LugarNoticia.nombre.ilike(nombre)
    ).order_by(LugarNoticia.verificada.desc(), LugarNoticia.lat.isnot(None).desc()).first()
    
    base_lat, base_lon = (ref.lat, ref.lon) if ref else (0.0, 0.0)
    is_verified = ref.verificada if ref else False
    is_borrado = ref.borrado if ref else False

    # 1.5. GUARDAR MAPA DE FRECUENCIAS DESVINCULADAS antes de borrar
    # {noticia_id: frecuencia_desvinculada}
    lugares_existentes = LugarNoticia.query.join(Prensa).filter(
        Prensa.proyecto_id == proyecto_id,
        LugarNoticia.nombre.ilike(nombre)
    ).all()
    
    mapa_desvinculadas = {}
    for lg in lugares_existentes:
        if hasattr(lg, 'frecuencia_desvinculada') and lg.frecuencia_desvinculada is not None:
            mapa_desvinculadas[lg.noticia_id] = lg.frecuencia_desvinculada

    # 2. LIMPIEZA UNIFICADA (Case Insensitive): 
    # Borrar todas las variantes de caja para evitar duplicados como "El Toboso" y "EL TOBOSO"
    subquery = db.session.query(LugarNoticia.id).join(Prensa).filter(
        Prensa.proyecto_id == proyecto_id,
        LugarNoticia.nombre.ilike(nombre)
    )
    ids_to_delete = [r[0] for r in subquery.all()]
    LugarNoticia.query.filter(LugarNoticia.id.in_(ids_to_delete)).delete(synchronize_session=False)
    
    # 3. Buscar candidatos (noticias que contienen el texto)
    # Usamos búsqueda por texto plano para mayor precisión inicial
    from sqlalchemy import or_
    noticias_candidatas = Prensa.query.filter(
        Prensa.proyecto_id == proyecto_id,
        or_(
            Prensa.titulo.ilike(f"%{nombre}%"),
            Prensa.contenido.ilike(f"%{nombre}%")
        )
    ).all()
    
    import re
    # Intentamos buscar el nombre completo con límites de palabra para evitar sub-matches parciales (opcional pero recomendado)
    # Por ahora mantenemos el re.escape simple para ser consistentes con lo que el usuario espera
    safe_name = re.escape(nombre)
    actualizados = 0
    creados = 0
    
    for n in noticias_candidatas:
        titulo = n.titulo or ""
        contenido = n.contenido or ""
        
        matches_titulo = len(re.findall(safe_name, titulo, re.IGNORECASE))
        matches_contenido = len(re.findall(safe_name, contenido, re.IGNORECASE))
        
        if matches_titulo == 0 and matches_contenido == 0:
            continue
            
        ln = LugarNoticia.query.filter_by(noticia_id=n.id, nombre=nombre).first()
        
        if not ln:
            ln = LugarNoticia(
                noticia_id=n.id,
                nombre=nombre,
                lat=base_lat,
                lon=base_lon,
                tipo='extraido',
                verificada=is_verified,
                borrado=is_borrado
            )
            db.session.add(ln)
            creados += 1
        
        # Actualizar frecuencias (pero preservar desvinculadas)
        old_frec_desvinc = mapa_desvinculadas.get(n.id, 0)
        
        ln.frec_titulo = matches_titulo
        ln.frec_contenido = matches_contenido
        ln.frecuencia = matches_titulo + matches_contenido
        ln.en_titulo = matches_titulo > 0
        ln.en_contenido = matches_contenido > 0
        
        # CRÍTICO: Restaurar frecuencia_desvinculada guardada (no sobrescribir)
        # Si la nueva frecuencia es menor que las desvinculadas, ajustar
        if old_frec_desvinc > ln.frecuencia:
            ln.frecuencia_desvinculada = ln.frecuencia  # No puede haber más desvinculadas que total
        else:
            ln.frecuencia_desvinculada = old_frec_desvinc
        
        # Actualizar estado vinculada basado en desvinculadas
        ln.vinculada = ln.frecuencia_desvinculada < ln.frecuencia
        
        actualizados += 1
    
    # [NUEVO] Si no se encontraron menciones pero el lugar ya existía (especialmente si Verificado),
    # creamos UNA referencia con frecuencia 0 para que no desaparezca del listado.
    if actualizados == 0 and ref:
        # Buscamos cualquier noticia del proyecto para colgar la referencia 0
        primera_n = Prensa.query.filter_by(proyecto_id=proyecto_id).first()
        if primera_n:
            # Restaurar frecuencia_desvinculada si este lugar tenía una
            old_frec_desvinc = mapa_desvinculadas.get(primera_n.id, 0)
            
            ln = LugarNoticia(
                noticia_id=primera_n.id,
                nombre=nombre,
                lat=base_lat,
                lon=base_lon,
                tipo='extraido',
                verificada=is_verified,
                borrado=is_borrado,
                frecuencia=0,
                frec_titulo=0,
                frec_contenido=0,
                frecuencia_desvinculada=old_frec_desvinc,
                vinculada=False  # Si frecuencia es 0, está desvinculada
            )
            db.session.add(ln)
            actualizados = 1

    return actualizados, creados

@noticias_bp.route('/api/cartografia/gestion/rebuscar', methods=['POST'])
@login_required
@csrf.exempt
def api_rebuscar_ubicacion():
    data = request.get_json()
    nombre = data.get('nombre')
    if not nombre:
        return jsonify({'success': False, 'error': 'Nombre requerido'}), 400
    
    from utils import get_proyecto_activo
    proyecto = get_proyecto_activo()
    if not proyecto:
        return jsonify({'success': False, 'error': 'No hay proyecto activo'}), 400
        
    actualizados, creados = sync_lugar_noticia(nombre, proyecto.id)
    db.session.commit()
    
    return jsonify({
        'success': True, 
        'total_menciones': actualizados,
        'nuevos_registros': creados,
        'nombre': nombre
    })

@noticias_bp.route('/api/cartografia/gestion/contexto_lugar', methods=['GET'])
@login_required
def api_get_contexto_lugar():
    """
    Returns snippets of text from title and content where the location is mentioned.
    This provides 'Trazabilidad de Origen' (Geocoding Lineage) to the user.
    """
    import logging
    app_logger = logging.getLogger('app')
    
    nombre = request.args.get('nombre')
    if not nombre:
        return jsonify({'success': False, 'error': 'Nombre de ubicación requerido'}), 400
        
    from utils import get_proyecto_activo
    proyecto = get_proyecto_activo()
    if not proyecto:
        return jsonify({'success': False, 'error': 'No hay proyecto activo'}), 400
        
    try:
        # Get all active news articles where this location is mentioned
        lugares = LugarNoticia.query.join(Prensa).filter(
            Prensa.proyecto_id == proyecto.id,
            LugarNoticia.nombre.ilike(nombre),
            LugarNoticia.borrado == False
        ).options(db.joinedload(LugarNoticia.noticia)).all()
        
        snippets = []
        import re
        
        # We'll extract a window of words around the match
        WINDOW_SIZE = 60 # characters
        
        def extract_snippets(text, query):
            if not text: return []
            found_snippets = []
            # Find all occurrences, case-insensitive
            query_esc = re.escape(query)
            for match in re.finditer(query_esc, text, re.IGNORECASE):
                start = max(0, match.start() - WINDOW_SIZE)
                end = min(len(text), match.end() + WINDOW_SIZE)
                
                snippet = text[start:end]
                # Add ellipsis if we cut the text
                if start > 0: snippet = "..." + snippet
                if end < len(text): snippet = snippet + "..."
                
                # Highlight the exact match (using a custom tag or standard HTML)
                # We'll use a <mark> tag for easy styling in frontend
                highlighted = re.sub(f"({query_esc})", r"<mark class='highlight-amber'>\1</mark>", snippet, flags=re.IGNORECASE)
                found_snippets.append(highlighted)
            return found_snippets

        for lugar in lugares:
            noticia = lugar.noticia
            if not noticia: continue
            
            # Calcular frecuencia efectiva para esta ubicación específica
            frec_desvinculada = getattr(lugar, 'frecuencia_desvinculada', 0) or 0
            frec_efectiva = lugar.frecuencia - frec_desvinculada
            
            # SOLO mostrar noticias donde hay al menos 1 mención vinculada
            if frec_efectiva <= 0:
                continue
            
            # Buscar snippets siempre, especialmente para ubicaciones manuales
            # donde el nombre en el texto podría diferir del nombre canónico
            titulo_snippets = extract_snippets(noticia.titulo, nombre) if noticia.titulo else []
            contenido_snippets = extract_snippets(noticia.contenido, nombre) if noticia.contenido else []
            
            # Incluir la noticia aunque no haya snippets exactos (caso de nombres diferentes)
            # El usuario verá al menos el título y puede verificar manualmente
            snippets.append({
                'noticia_id': noticia.id,
                'lugar_id': lugar.id,
                'titulo': noticia.titulo or 'Sin título',
                'fecha': noticia.fecha_original if noticia.fecha_original else 'Sin fecha',
                'medio': noticia.publicacion or 'Medio desconocido',
                'titulo_snippets': titulo_snippets,
                'contenido_snippets': contenido_snippets,
                'frecuencia': lugar.frecuencia,
                'frecuencia_desvinculada': frec_desvinculada,
                'frecuencia_efectiva': frec_efectiva,
                'vinculada': True  # Siempre True porque filtramos las desvinculadas
            })
        
        # Sort by noticia_id (newest first as proxy for date)
        snippets.sort(key=lambda x: x.get('noticia_id', 0), reverse=True)
        
        return jsonify({
            'success': True,
            'nombre': nombre,
            'total_noticias': len(snippets),
            'snippets': snippets
        })
        
    except Exception as e:
        app_logger.error(f"[api_get_contexto_lugar] Error: {e}")
        import traceback
        app_logger.error(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500

@noticias_bp.route('/api/cartografia/gestion/rebuscar_batch', methods=['POST'])
@login_required
@csrf.exempt
def api_rebuscar_batch_ubicaciones():
    data = request.get_json()
    nombres = data.get('nombres', []) # Si vacío, podemos rebuscar TODOS los del proyecto
    
    from utils import get_proyecto_activo
    proyecto = get_proyecto_activo()
    if not proyecto:
        return jsonify({'success': False, 'error': 'No hay proyecto activo'}), 400

    if not nombres:
        # Obtener todos los nombres únicos de LugarNoticia para este proyecto
        nombres = [r[0] for r in db.session.query(LugarNoticia.nombre).join(Prensa).filter(
            Prensa.proyecto_id == proyecto.id,
            LugarNoticia.borrado == False
        ).distinct().all()]

    resumen = []
    total_creados = 0
    total_actualizados = 0

    for nombre in nombres:
        act, cre = sync_lugar_noticia(nombre, proyecto.id)
        total_actualizados += act
        total_creados += cre
        resumen.append({'nombre': nombre, 'actualizados': act, 'creados': cre})

    db.session.commit()
    return jsonify({
        'success': True, 
        'count_nombres': len(nombres),
        'total_actualizados': total_actualizados,
        'total_creados': total_creados,
        'resumen': resumen
    })

@noticias_bp.route('/api/cartografia/gestion/batch_delete', methods=['POST'])
@login_required
@csrf.exempt
def api_batch_delete_ubicaciones():
    """Batch delete locations and add to global blacklist"""
    data = request.get_json()
    nombres = data.get('nombres', [])
    if not nombres:
        return jsonify({'success': False, 'error': 'No hay nombres seleccionados'}), 400
    
    try:
        from utils import get_proyecto_activo
        proyecto = get_proyecto_activo()
        if not proyecto:
            return jsonify({'success': False, 'error': 'No hay proyecto activo'}), 400

        # Subquery para filtrar solo registros de este proyecto
        subquery = db.session.query(LugarNoticia.id).join(Prensa).filter(
            Prensa.proyecto_id == proyecto.id,
            LugarNoticia.nombre.in_(nombres),
            LugarNoticia.borrado == False
        )
        
        ids_to_delete = [r[0] for r in subquery.all()]
        cnt = LugarNoticia.query.filter(LugarNoticia.id.in_(ids_to_delete)).update(
            {'borrado': True, 'verificada': False}, synchronize_session=False
        )
        
        # ── BLACKLIST GLOBAL ────────────────────────────────────────────────────
        for nombre in nombres:
            ciudad = Ciudad.query.filter(Ciudad.name.ilike(nombre)).first()
            if not ciudad:
                lugar_ref = LugarNoticia.query.filter(LugarNoticia.nombre.ilike(nombre)).first()
                lat_ref = lugar_ref.lat if lugar_ref else 0.0
                lon_ref = lugar_ref.lon if lugar_ref else 0.0
                ciudad = Ciudad(name=nombre, lat=lat_ref, lon=lon_ref, verificada=False, blacklisted=True)
                db.session.add(ciudad)
            else:
                ciudad.blacklisted = True
                ciudad.verificada = False
        # ────────────────────────────────────────────────────────────────────────
        
        db.session.commit()
        return jsonify({'success': True, 'updated_count': cnt, 'message': f'Se han borrado {cnt} instancias correctamente.'})
    except Exception as e:
        db.session.rollback()
        print(f"[api_batch_delete_ubicaciones] Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@noticias_bp.route('/api/cartografia/gestion/batch_unlink', methods=['POST'])
@login_required
@csrf.exempt
def api_batch_unlink_ubicaciones():
    """Batch unlink locations (delete from project only, NO blacklist)"""
    data = request.get_json()
    nombres = data.get('nombres', [])
    if not nombres:
        return jsonify({'success': False, 'error': 'No hay nombres seleccionados'}), 400
    
    try:
        from utils import get_proyecto_activo
        proyecto = get_proyecto_activo()
        if not proyecto:
            return jsonify({'success': False, 'error': 'No hay proyecto activo'}), 400

        # Subquery para filtrar solo registros de este proyecto
        subquery = db.session.query(LugarNoticia.id).join(Prensa).filter(
            Prensa.proyecto_id == proyecto.id,
            LugarNoticia.nombre.in_(nombres),
            LugarNoticia.borrado == False
        )
        
        ids_to_unlink = [r[0] for r in subquery.all()]
        cnt = LugarNoticia.query.filter(LugarNoticia.id.in_(ids_to_unlink)).update(
            {'borrado': True, 'verificada': False}, synchronize_session=False
        )
        
        # A diferencia de batch_delete, AQUÍ NO TOCAMOS LA TABLA CIUDAD (Sin lista negra)
        
        db.session.commit()
        return jsonify({'success': True, 'updated_count': cnt, 'message': f'Se han desvinculado {cnt} instancias correctamente.'})
    except Exception as e:
        db.session.rollback()
        print(f"[api_batch_unlink_ubicaciones] Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
        
@noticias_bp.route('/api/cartografia/gestion/reactivar_batch', methods=['POST'])
@login_required
@csrf.exempt
def gestion_reactivar_batch_ubicaciones():
    data = request.get_json()
    nombres = data.get('nombres', [])
    if not nombres:
        return jsonify({'success': False, 'error': 'No hay nombres seleccionados'}), 400
    
    try:
        from utils import get_proyecto_activo
        proyecto = get_proyecto_activo()
        if not proyecto:
            return jsonify({'success': False, 'error': 'No hay proyecto activo'}), 400

        # Obtener ids de ubicaciones borradas del proyecto
        subquery = db.session.query(LugarNoticia.id).join(Prensa).filter(
            Prensa.proyecto_id == proyecto.id,
            LugarNoticia.nombre.in_(nombres),
            LugarNoticia.borrado == True
        )
        
        ids_to_restore = [r[0] for r in subquery.all()]
        cnt = LugarNoticia.query.filter(LugarNoticia.id.in_(ids_to_restore)).update(
            {'borrado': False}, synchronize_session=False
        )
        
        # ── QUITAR DE LISTA NEGRA GLOBAL ─────────────────────────────────────
        for nombre in nombres:
            ciudad = Ciudad.query.filter(Ciudad.name.ilike(nombre)).first()
            if ciudad:
                ciudad.blacklisted = False
        # ─────────────────────────────────────────────────────────────────────
        
        db.session.commit()
        return jsonify({'success': True, 'updated_count': cnt, 'message': f'Se han restaurado {cnt} instancias correctamente.'})
    except Exception as e:
        db.session.rollback()
        print(f"[gestion_reactivar_batch_ubicaciones] Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@noticias_bp.route('/api/cartografia/gestion/editar', methods=['POST'])
@login_required
@csrf.exempt
def gestion_editar_ubicacion():
    from utils import get_proyecto_activo
    proyecto = get_proyecto_activo()
    if not proyecto:
        return jsonify({'success': False, 'error': 'No hay proyecto activo'}), 400

    data = request.get_json()
    nombre_antiguo = data.get('nombre_antiguo')
    nombre_nuevo = data.get('nombre_nuevo')
    lat = data.get('lat')
    lon = data.get('lon')
    tipo_lugar = data.get('tipo_lugar')
    target_frecuencia = data.get('frecuencia')
    target_frec_titulo = data.get('frec_titulo')
    target_frec_contenido = data.get('frec_contenido')

    if not nombre_antiguo or not nombre_nuevo:
        return jsonify({'success': False, 'error': 'Faltan nombres'}), 400
    
    try:
        # 1. Fusionar registros si hay conflicto de nombres (SOLO en este proyecto)
        # Buscamos todos los lugares con el nombre antiguo (case insensitive) vinculados a noticias del proyecto
        lugares_viejos = LugarNoticia.query.join(Prensa).filter(
            Prensa.proyecto_id == proyecto.id,
            LugarNoticia.nombre.ilike(nombre_antiguo),
            LugarNoticia.borrado == False
        ).all()
        # DEFINIR CONFLICTO: ¿Existe ya el nombre nuevo en este proyecto?
        conflicto = None
        if nombre_antiguo != nombre_nuevo:
            conflicto = LugarNoticia.query.join(Prensa).filter(
                Prensa.proyecto_id == proyecto.id,
                LugarNoticia.nombre.ilike(nombre_nuevo),
                LugarNoticia.borrado == False
            ).first()
        
        for lv in lugares_viejos:
            # Si el nombre no cambió, solo actualizar coordenadas/frecuencia
            if nombre_antiguo == nombre_nuevo:
                if lat is not None: 
                    lv.lat = lat
                    lv.verificada = True # Marcamos como verificado al editar manual
                if lon is not None: 
                    lv.lon = lon
                    lv.verificada = True
                if tipo_lugar is not None:
                    lv.tipo_lugar = tipo_lugar
                continue
            
            if conflicto and conflicto.id != lv.id:
                # FUSIONAR: Sumar frecuencia y borrar el viejo
                print(f"[FUSIÓN] Fusionando {lv.nombre} (freq={lv.frecuencia}) con {conflicto.nombre} (freq={conflicto.frecuencia})")
                conflicto.frecuencia += lv.frecuencia
                print(f"[FUSIÓN] Nueva frecuencia de {conflicto.nombre}: {conflicto.frecuencia}")
                if lat is not None: 
                    conflicto.lat = lat
                    conflicto.verificada = True
                if lon is not None: 
                    conflicto.lon = lon
                    conflicto.verificada = True
                if tipo_lugar is not None:
                    conflicto.tipo_lugar = tipo_lugar
                db.session.delete(lv)
            else:
                # CAMBIAR NOMBRE: Simplemente actualizar
                print(f"[RENAME] Cambiando nombre de '{lv.nombre}' a '{nombre_nuevo}' (freq={lv.frecuencia})")
                lv.nombre = nombre_nuevo
                if lat is not None: 
                    lv.lat = lat
                    lv.verificada = True
                if lon is not None: 
                    lv.lon = lon
                    lv.verificada = True
                if tipo_lugar is not None:
                    lv.tipo_lugar = tipo_lugar
        
        db.session.commit()

        # 2. Buscar registros con el nuevo nombre (ya unificados)
        lugares = LugarNoticia.query.join(Prensa).filter(
            Prensa.proyecto_id == proyecto.id,
            LugarNoticia.nombre.ilike(nombre_nuevo),
            LugarNoticia.borrado == False
        ).all()

        if lugares:
            # 3. Ajustar Frecuencia Total
            if target_frecuencia is not None:
                try:
                    target_frecuencia = int(target_frecuencia)
                    current_total = sum(l.frecuencia for l in lugares)
                    diff = target_frecuencia - current_total
                    if diff != 0:
                        lugares[0].frecuencia = max(1, lugares[0].frecuencia + diff)
                except (ValueError, TypeError): pass

            # 4. Ajustar Frecuencias Título/Contenido
            if target_frec_titulo is not None:
                try:
                    target_frec_titulo = int(target_frec_titulo)
                    curr_t = sum(l.frec_titulo or 0 for l in lugares)
                    diff_t = target_frec_titulo - curr_t
                    if diff_t != 0:
                        lugares[0].frec_titulo = (lugares[0].frec_titulo or 0) + diff_t
                except (ValueError, TypeError): pass
            
            if target_frec_contenido is not None:
                try:
                    target_frec_contenido = int(target_frec_contenido)
                    curr_c = sum(l.frec_contenido or 0 for l in lugares)
                    diff_c = target_frec_contenido - curr_c
                    if diff_c != 0:
                        lugares[0].frec_contenido = (lugares[0].frec_contenido or 0) + diff_c
                except (ValueError, TypeError): pass

        db.session.commit()

        # 5. Actualizar o Crear entrada en Ciudad (referencia global)
        from sqlalchemy import func
        ciudad_vieja = Ciudad.query.filter(func.lower(Ciudad.name) == func.lower(nombre_antiguo)).first()
        ciudad_nueva = Ciudad.query.filter(func.lower(Ciudad.name) == func.lower(nombre_nuevo)).first()
        
        if ciudad_vieja:
            if ciudad_nueva and ciudad_vieja.id != ciudad_nueva.id:
                # Fusión Global: El destino ya existe. Borramos la referencia al nombre antiguo.
                print(f"[CIUDAD] Fusionando globalmente {ciudad_vieja.name} -> {ciudad_nueva.name}")
                db.session.delete(ciudad_vieja)
                if lat is not None: ciudad_nueva.lat = lat
                if lon is not None: ciudad_nueva.lon = lon
                ciudad_nueva.verificada = True
            else:
                # Renombrado simple
                ciudad_vieja.name = nombre_nuevo
                if lat is not None: ciudad_vieja.lat = lat
                if lon is not None: ciudad_vieja.lon = lon
                ciudad_vieja.verificada = True
        elif not ciudad_nueva:
            # Crear si no existe ninguna de las dos
            if lat is not None and lon is not None:
                new_city = Ciudad(name=nombre_nuevo, lat=lat, lon=lon, verificada=True)
                db.session.add(new_city)
        elif ciudad_nueva:
            # Si solo existe la nueva, actualizar sus coordenadas
            if lat is not None: ciudad_nueva.lat = lat
            if lon is not None: ciudad_nueva.lon = lon
            ciudad_nueva.verificada = True
        
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        print(f"[gestion_editar_ubicacion] Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@noticias_bp.route('/api/cartografia/gestion/cambiar-tipo-masivo', methods=['POST'])
@login_required
@csrf.exempt
def api_cambiar_tipo_masivo():
    """Cambiar el tipo_lugar de múltiples ubicaciones a la vez"""
    from utils import get_proyecto_activo
    proyecto = get_proyecto_activo()
    if not proyecto:
        return jsonify({'success': False, 'error': 'No hay proyecto activo'}), 400

    data = request.get_json()
    nombres = data.get('nombres', [])
    tipo_lugar = data.get('tipo_lugar')

    if not nombres or not tipo_lugar:
        return jsonify({'success': False, 'error': 'Faltan nombres o tipo_lugar'}), 400

    try:
        count = 0
        for nombre in nombres:
            lugares = LugarNoticia.query.join(Prensa).filter(
                Prensa.proyecto_id == proyecto.id,
                LugarNoticia.nombre.ilike(nombre),
                LugarNoticia.borrado == False
            ).all()
            
            for lugar in lugares:
                lugar.tipo_lugar = tipo_lugar
                count += 1

        db.session.commit()
        return jsonify({'success': True, 'count': count})
    except Exception as e:
        db.session.rollback()
        print(f"[api_cambiar_tipo_masivo] Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== GESTIÓN DE TIPOS DE UBICACIÓN ====================

@noticias_bp.route('/api/tipos-ubicacion/listar', methods=['GET'])
@login_required
def api_tipos_ubicacion_listar():
    """Listar todos los tipos de ubicación disponibles"""
    from models import TipoUbicacion
    try:
        incluir_inactivos = request.args.get('incluir_inactivos', 'false').lower() == 'true'
        if incluir_inactivos:
            tipos = TipoUbicacion.query.order_by(TipoUbicacion.orden, TipoUbicacion.nombre).all()
        else:
            tipos = TipoUbicacion.query.filter_by(activo=True).order_by(TipoUbicacion.orden, TipoUbicacion.nombre).all()
        
        print(f"[DEBUG_TIPOS] Tabla: {TipoUbicacion.__tablename__}. Activo=True? {not incluir_inactivos}. Encontrados: {len(tipos)}")
        for t in tipos[:3]:
            print(f"  - {t.nombre} ({t.codigo})")

        return jsonify({
            'success': True,
            'tipos': [tipo.to_dict() for tipo in tipos]
        })
    except Exception as e:
        print(f"[api_tipos_ubicacion_listar] Error Fatal: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@noticias_bp.route('/api/tipos-ubicacion/restaurar/<string:codigo>', methods=['POST'])
@login_required
@csrf.exempt
def api_tipos_ubicacion_restaurar(codigo):
    """Restaurar un tipo de ubicación desactivado por su código"""
    from models import TipoUbicacion
    tipo = TipoUbicacion.query.filter_by(codigo=codigo).first()
    if not tipo:
        return jsonify({'success': False, 'error': f'No se encontró ningún tipo con código "{codigo}"'}), 404
    if tipo.activo:
        return jsonify({'success': True, 'message': 'El tipo ya está activo', 'tipo': tipo.to_dict()})
    try:
        tipo.activo = True
        db.session.commit()
        return jsonify({'success': True, 'message': f'Tipo "{tipo.nombre}" restaurado', 'tipo': tipo.to_dict()})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@noticias_bp.route('/api/tipos-ubicacion/crear', methods=['POST'])
@login_required
@csrf.exempt
def api_tipos_ubicacion_crear():
    """Crear un nuevo tipo de ubicación"""
    from models import TipoUbicacion
    data = request.get_json()
    print(f"[api_tipos_ubicacion_crear] Payload: {data}")
    
    if not data:
        return jsonify({'success': False, 'error': 'No data provided'}), 400

    codigo = data.get('codigo', '').strip().lower()
    nombre = data.get('nombre', '').strip()
    categoria = data.get('categoria', 'Otros').strip()
    icono = data.get('icono', '').strip()
    orden = data.get('orden', 999)
    
    if not codigo or not nombre:
        return jsonify({'success': False, 'error': 'Código y nombre son obligatorios'}), 400

    
    # Verificar si ya existe (activo o no)
    existe = TipoUbicacion.query.filter_by(codigo=codigo).first()
    if existe:
        if existe.activo:
            return jsonify({'success': False, 'error': f'Ya existe un tipo activo con código "{codigo}"'}), 400
        else:
            # Reactivar el tipo desactivado con los nuevos datos
            try:
                existe.nombre = nombre
                existe.categoria = categoria
                existe.icono = icono
                existe.orden = orden
                existe.activo = True
                db.session.commit()
                return jsonify({
                    'success': True,
                    'tipo': existe.to_dict(),
                    'message': f'Tipo "{nombre}" restaurado correctamente'
                })
            except Exception as e:
                db.session.rollback()
                print(f"[api_tipos_ubicacion_crear] Error al reactivar: {e}")
                return jsonify({'success': False, 'error': str(e)}), 500
    
    try:
        nuevo_tipo = TipoUbicacion(
            codigo=codigo,
            nombre=nombre,
            categoria=categoria,
            icono=icono,
            orden=orden
        )
        db.session.add(nuevo_tipo)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'tipo': nuevo_tipo.to_dict(),
            'message': f'Tipo "{nombre}" creado correctamente'
        })
    except Exception as e:
        db.session.rollback()
        print(f"[api_tipos_ubicacion_crear] Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@noticias_bp.route('/api/tipos-ubicacion/editar/<int:tipo_id>', methods=['PUT'])
@login_required
@csrf.exempt
def api_tipos_ubicacion_editar(tipo_id):
    """Editar un tipo de ubicación existente"""
    from models import TipoUbicacion
    data = request.get_json()
    
    tipo = TipoUbicacion.query.get(tipo_id)
    if not tipo:
        return jsonify({'success': False, 'error': 'Tipo no encontrado'}), 404
    
    try:
        # Actualizar campos
        if 'codigo' in data:
            nuevo_codigo = data['codigo'].strip().lower()
            if nuevo_codigo != tipo.codigo:
                # Verificar unicidad
                existe = TipoUbicacion.query.filter_by(codigo=nuevo_codigo).first()
                if existe:
                    return jsonify({'success': False, 'error': f'El código "{nuevo_codigo}" ya está en uso'}), 400
                tipo.codigo = nuevo_codigo
        if 'nombre' in data:
            tipo.nombre = data['nombre'].strip()
        if 'categoria' in data:
            tipo.categoria = data['categoria'].strip()
        if 'icono' in data:
            tipo.icono = data['icono'].strip()
        if 'orden' in data:
            tipo.orden = data['orden']
        if 'activo' in data:
            tipo.activo = data['activo']
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'tipo': tipo.to_dict(),
            'message': f'Tipo "{tipo.nombre}" actualizado correctamente'
        })
    except Exception as e:
        db.session.rollback()
        print(f"[api_tipos_ubicacion_editar] Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@noticias_bp.route('/api/tipos-ubicacion/eliminar/<int:tipo_id>', methods=['DELETE'])
@login_required
@csrf.exempt
def api_tipos_ubicacion_eliminar(tipo_id):
    """Eliminar (desactivar) un tipo de ubicación"""
    from models import TipoUbicacion
    
    tipo = TipoUbicacion.query.get(tipo_id)
    if not tipo:
        return jsonify({'success': False, 'error': 'Tipo no encontrado'}), 404
    
    try:
        # No eliminamos físicamente, solo desactivamos
        tipo.activo = False
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Tipo "{tipo.nombre}" eliminado correctamente'
        })
    except Exception as e:
        db.session.rollback()
        print(f"[api_tipos_ubicacion_eliminar] Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@noticias_bp.route('/api/cartografia/gestion/unificar', methods=['POST'])
@login_required
@csrf.exempt
def api_unificar_duplicados():
    from utils import get_proyecto_activo
    proyecto = get_proyecto_activo()
    if not proyecto:
        return jsonify({'success': False, 'error': 'No hay proyecto activo'}), 400

    try:
        # Obtener todos los lugares activos del proyecto
        lugares_raw = LugarNoticia.query.join(Prensa).filter(
            Prensa.proyecto_id == proyecto.id,
            LugarNoticia.borrado == False
        ).all()

        # Agrupar por nombre case-insensitive
        grupos = {}
        for l in lugares_raw:
            key = l.nombre.lower().strip()
            if key not in grupos: grupos[key] = []
            grupos[key].append(l)

        unificados_count = 0
        for key, items in grupos.items():
            # Mapeo por noticia para evitar duplicados en la misma noticia
            noticias_map = {} # nid -> canon_record_for_this_news
            
            # Elegir nombre canónico (el que tenga más mayúsculas)
            items_cajas = sorted(items, key=lambda x: sum(1 for c in x.nombre if c.isupper()), reverse=True)
            canon_name = items_cajas[0].nombre

            for it in items:
                it.nombre = canon_name # Normalizar nombre
                nid = it.noticia_id
                if nid not in noticias_map:
                    noticias_map[nid] = it
                else:
                    # Fusionar con el registro ya existente para esta noticia
                    target = noticias_map[nid]
                    if target.id != it.id:
                        target.frecuencia += it.frecuencia
                        target.frec_titulo = (target.frec_titulo or 0) + (it.frec_titulo or 0)
                        target.frec_contenido = (target.frec_contenido or 0) + (it.frec_contenido or 0)
                        it.borrado = True
                        unificados_count += 1

        db.session.commit()
        return jsonify({'success': True, 'unificados': unificados_count})
    except Exception as e:
        db.session.rollback()
        print(f"[UNIFICAR] Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@noticias_bp.route('/api/cartografia/gestion/crear', methods=['POST'])
@login_required
@csrf.exempt
def gestion_crear_ubicacion():
    data = request.get_json()
    nombre = data.get('nombre')
    lat = data.get('lat')
    lon = data.get('lon')
    
    if not nombre or lat is None or lon is None:
        return jsonify({'success': False, 'error': 'Faltan datos'}), 400
    
    try:
        from utils import get_proyecto_activo
        proyecto = get_proyecto_activo()
        
        # Crear o actualizar en tabla Ciudad (referencia global)
        ciudad = Ciudad.query.filter_by(name=nombre).first()
        if ciudad:
            ciudad.lat = lat
            ciudad.lon = lon
        else:
            ciudad = Ciudad(name=nombre, lat=lat, lon=lon)
            db.session.add(ciudad)
        
        db.session.commit()
        
        # --- SINCRONIZACIÓN PROACTIVA (Alma y Corazón) ---
        # Si hay un proyecto activo, buscamos menciones de este lugar en el corpus
        # para que aparezca en el mapa inmediatamente.
        if proyecto:
            act, cre = sync_lugar_noticia(nombre, proyecto.id)
            db.session.commit()
            msg = f"Ubicación '{nombre}' guardada. Se han detectado y mapeado {cre} nuevas menciones en el proyecto '{proyecto.nombre}'."
            return jsonify({'success': True, 'message': msg, 'created': cre})
        
        return jsonify({'success': True, 'message': 'Ubicación de referencia creada globalmente.'})
    except Exception as e:
        db.session.rollback()
        print(f"[gestion_crear_ubicacion] Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500



@noticias_bp.route('/api/cartografia/ciudad/<nombre>')
@login_required
def api_get_ciudad_by_name(nombre):
    from models import Ciudad
    ciudad = Ciudad.query.filter(Ciudad.name.ilike(nombre)).first()
    if ciudad:
        return jsonify({
            'success': True,
            'nombre': ciudad.name,
            'lat': ciudad.lat,
            'lon': ciudad.lon
        })
    return jsonify({'success': False, 'error': 'Ubicación no encontrada en base de datos global'}), 404
@noticias_bp.route('/api/cartografia_corpus/embeddings', methods=['GET'])
# @login_required
def cartografia_corpus_embeddings_api():
    """
    API para visualización 3D de embeddings del corpus con Clustering.
    """
    from utils import get_proyecto_activo
    proyecto = get_proyecto_activo()
    if not proyecto:
        return jsonify({'success': False, 'error': 'No hay proyecto activo'}), 400

    limit = request.args.get('limit', default=500, type=int)
    dim = request.args.get('dim', default=3, type=int) # Default to 3D now

    # Obtener noticias con embeddings del proyecto
    noticias = Prensa.query.filter(
        Prensa.proyecto_id == proyecto.id,
        Prensa.incluido == True,
        Prensa.embedding_vector.isnot(None)
    ).limit(limit).all()

    if not noticias:
        return jsonify({'success': False, 'error': 'No hay noticias con embeddings'}), 404

    vectors = []
    metadata = []
    for n in noticias:
        if isinstance(n.embedding_vector, list) and len(n.embedding_vector) > 0:
            vectors.append(n.embedding_vector)
            metadata.append({
                'id': n.id,
                'titulo': (n.titulo[:60] + '...') if n.titulo and len(n.titulo) > 60 else (n.titulo or 'Sin título'),
                'fecha': str(n.fecha_original) if n.fecha_original else '',
                'publicacion': n.publicacion or ''
            })

    if not vectors:
        return jsonify({'success': False, 'error': 'No se encontraron vectores válidos'}), 404

    try:
        import numpy as np
        from umap import UMAP
        from sklearn.cluster import KMeans
        
        X = np.array(vectors)
        
        # 1. Reducción de dimensionalidad (3D para el efecto "Universo")
        # Aumentamos min_dist para separar más las "constelaciones" (clusters)
        reducer = UMAP(n_neighbors=25, min_dist=0.8, n_components=dim, random_state=42)
        X_embedded = reducer.fit_transform(X)

        # --- NEW: PROYECCIÓN ESFÉRICA DE BÓVEDA (Hemisferio) ---
        def to_spherical_vault(x, y, z, R=350):
            norm = np.sqrt(x**2 + y**2 + z**2) + 1e-9
            # Forzamos forma de bóveda (Hemisferio superior)
            x_norm, y_norm, z_norm = x/norm, y/norm, z/norm
            # Usamos abs(y) para la bóveda
            y_vault = abs(y_norm) 
            depth_jitter = np.random.uniform(0.9, 1.1)
            return x_norm * R * depth_jitter, y_vault * R * depth_jitter, z_norm * R * depth_jitter

        X_spherical = np.zeros_like(X_embedded)
        for i in range(len(X_embedded)):
            X_spherical[i, 0], X_spherical[i, 1], X_spherical[i, 2] = to_spherical_vault(X_embedded[i, 0], X_embedded[i, 1], X_embedded[i, 2])

        # 2. Clustering: Dinámico (Keywords) o Automático (K-Means)
        import json
        custom_clusters_json = request.args.get('custom_clusters')
        custom_clusters = None
        if custom_clusters_json:
            try:
                custom_clusters = json.loads(custom_clusters_json)
            except:
                pass

        cluster_labels = []
        n_clusters = 8 # Default
        
        if custom_clusters and len(custom_clusters) > 0:
            # --- MODO CONSTELACIONES DINÁMICAS (Orientado por el Usuario) ---
            cluster_ids = sorted(custom_clusters.keys())
            n_clusters = len(cluster_ids)
            
            for i in range(len(metadata)):
                doc_text = metadata[i]['titulo'].lower()
                best_cluster = 0
                max_score = -1
                
                for idx, c_id in enumerate(cluster_ids):
                    keywords = custom_clusters[c_id].get('keywords', [])
                    if not keywords: continue
                    # Puntuación simple por coincidencia de palabras (se puede mejorar a embeddings)
                    score = sum(1 for k in keywords if k.lower().strip() in doc_text)
                    if score > max_score:
                        max_score = score
                        best_cluster = idx
                cluster_labels.append(best_cluster)
            cluster_labels = np.array(cluster_labels)
        else:
            # --- MODO AUTOMÁTICO (K-Means) ---
            n_clusters = min(8, len(vectors))
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init='auto')
            cluster_labels = kmeans.fit_predict(X)
        
        # Preparar puntos con Dimensión 4 (Tiempo)
        points = []
        for i in range(len(metadata)):
            # Extraer timestamp para el slider temporal
            try:
                dt_str = metadata[i]['fecha']
                ts = 0
                if dt_str:
                    from datetime import datetime
                    ts = datetime.strptime(dt_str, '%Y-%m-%d').timestamp()
            except:
                ts = 0

            p = {
                'x': float(X_spherical[i, 0]),
                'y': float(X_spherical[i, 1]),
                'z': float(X_spherical[i, 2]),
                'id': metadata[i]['id'],
                'titulo': metadata[i]['titulo'],
                'fecha': metadata[i]['fecha'],
                'timestamp': ts, # Dimensión 4
                'publicacion': metadata[i]['publicacion'],
                'cluster': int(cluster_labels[i])
            }
            points.append(p)

        # 3. Metadatos de Cluster (Palabras clave y Centros)
        cluster_metadata = {}
        for c_id in range(n_clusters):
            # Obtener títulos de este cluster para "extraer" palabras (si no es custom)
            if custom_clusters:
                c_key = sorted(custom_clusters.keys())[c_id]
                top_words = custom_clusters[c_key].get('keywords', [])
            else:
                cluster_titles = [m['titulo'] for i, m in enumerate(metadata) if cluster_labels[i] == c_id]
                all_text = " ".join(cluster_titles).lower()
                import re
                clean_text = re.sub(r'[^\w\s]', '', all_text)
                all_words = clean_text.split()
                stops = {'de', 'la', 'el', 'en', 'y', 'a', 'los', 'que', 'del', 'se', 'las', 'por', 'un', 'con', 'no', 'una', 'su', 'al', 'es', 'lo', 'como', 'más', 'para'}
                words = [w for w in all_words if len(w) > 3 and w not in stops]
                top_words = [w[0] for w in Counter(words).most_common(5)]

            # Calcular Centroide en la Esfera
            c_points = X_spherical[cluster_labels == c_id]
            if len(c_points) > 0:
                centroid = np.mean(c_points, axis=0)
            else:
                centroid = [0,0,0]
            
            cluster_metadata[str(c_id)] = {
                'keywords': top_words,
                'centroid': {
                    'x': float(centroid[0]),
                    'y': float(centroid[1]),
                    'z': float(centroid[2])
                }
            }
            # Preserve custom color if provided
            if custom_clusters:
                c_key = sorted(custom_clusters.keys())[c_id]
                color = custom_clusters[c_key].get('color')
                if color:
                    cluster_metadata[str(c_id)]['color'] = color

        return jsonify({
            'success': True,
            'points': points,
            'count': len(points),
            'clusters': n_clusters,
            'cluster_metadata': cluster_metadata,
            'dim': 3,
            'mode': 'custom' if custom_clusters else 'auto'
        })

    except Exception as e:
        import traceback
        error_msg = traceback.format_exc()
        current_app.logger.error(f"Error en reducción de dimensionalidad: {error_msg}")
        return jsonify({'success': False, 'error': str(e), 'traceback': error_msg}), 500



@noticias_bp.route('/api/cartografia_corpus', methods=['GET'])
@login_required
def cartografia_corpus_api():
    """
    API optimizada: usa lugares ya guardados en LugarNoticia en lugar de 
    procesar textos con spaCy (que consume mucha memoria/tiempo).
    """
    fecha_desde = request.args.get('fecha_desde')
    fecha_hasta = request.args.get('fecha_hasta')
    publicacion = request.args.get('publicacion')
    noticia_id = request.args.get('noticia_id')
    tipo_lugar = request.args.get('tipo_lugar')
    solo_borrados = request.args.get('solo_borrados') == 'true'
    all_states = request.args.get('all_states') == 'true'
    
    from utils import get_proyecto_activo
    from models import LugarNoticia
    proyecto = get_proyecto_activo()
    
    # Construir query base de noticias
    query = Prensa.query
    if proyecto:
        query = query.filter_by(proyecto_id=proyecto.id)
    else:
        # Si no hay proyecto, no devolvemos nada para evitar fugas entre usuarios
        return {'ciudades': []}
    if fecha_desde:
        query = query.filter(text(f"{SQL_PRENSA_DATE} >= :d").params(d=fecha_desde))
    if fecha_hasta:
        query = query.filter(text(f"{SQL_PRENSA_DATE} <= :h").params(h=fecha_hasta))
    if publicacion:
        query = query.filter(Prensa.publicacion == publicacion)
    if noticia_id:
        query = query.filter(Prensa.id == noticia_id)
    
    # Filtrar solo noticias ACTIVAS (incluidas en estudio) por defecto
    # Si pedimos borrados, igual queremos ver los de noticias borradas? 
    # Generalmente borramos el LugarNoticia, no la noticia.
    query = query.filter(Prensa.incluido == True)
    
    # Obtener IDs de noticias filtradas
    noticia_ids = [n.id for n in query.with_entities(Prensa.id).all()]
    
    if not noticia_ids:
        return {'ciudades': []}
    
    # Obtener lugares guardados para estas noticias (borrado según toggle, con coordenadas)
    from sqlalchemy.orm import joinedload
    lugares_query = LugarNoticia.query.options(joinedload(LugarNoticia.noticia)).filter(
        LugarNoticia.noticia_id.in_(noticia_ids),
        LugarNoticia.lat.isnot(None),
        LugarNoticia.lon.isnot(None)
    )

    # Filtrar por Tipo de Lugar si viene en los parámetros
    if tipo_lugar and tipo_lugar != '':
        # Soporte para búsqueda exacta o contenida (pues tipo_lugar puede ser CSV)
        from sqlalchemy import or_
        lugares_query = lugares_query.filter(or_(
            LugarNoticia.tipo_lugar.ilike(f"{tipo_lugar}"),
            LugarNoticia.tipo_lugar.ilike(f"{tipo_lugar},%"),
            LugarNoticia.tipo_lugar.ilike(f"%,{tipo_lugar}"),
            LugarNoticia.tipo_lugar.ilike(f"%,{tipo_lugar},%")
        ))

    if solo_borrados:
        lugares_query = lugares_query.filter(LugarNoticia.borrado == True)
    elif all_states:
        # Gestor view: Muestra TODAS las ubicaciones del proyecto (verificadas y pendientes, vinculadas y desvinculadas)
        lugares_query = lugares_query.filter(LugarNoticia.borrado == False)
    else:
        # Map view: SOLO ubicaciones verificadas (es ubicación real) y con al menos 1 mención vinculada al proyecto
        # La vinculación se valida después por frecuencia_efectiva > 0
        lugares_query = lugares_query.filter(
            LugarNoticia.verificada == True, 
            LugarNoticia.borrado == False
        )

    # Deterministic ordering: prioritize verified entries, then by ID
    lugares_query = lugares_query.order_by(LugarNoticia.verificada.desc(), LugarNoticia.id.asc())

    lugares = lugares_query.all()
    
    # Agrupar por nombre y coordenadas
    from collections import defaultdict
    # struct: lat, lon, freq, temas: {topic: count}
    grupos = defaultdict(lambda: {
        'lat': None, 'lon': None, 'frecuencia': 0, 
        'frecuencia_total': 0,  # Total sin filtrar (para referencia)
        'frecuencia_desvinculada': 0,  # Total de desvinculadas
        'frec_titulo': 0, 'frec_contenido': 0, 
        'tipo_lugar': 'unknown',  # Clasificación geográfica
        'temas': defaultdict(int),
        'fechas_mencion': [],
        'ultima_mencion': None,
        'verified': False,
        'deleted': False,
        'blacklisted': False,
        'vinculada': True,  # Si todas las ocurrencias están desvinculadas, será False
        'noticias_list': [] # list of {id, titulo}
    })
    
    for lugar in lugares:
        key = lugar.nombre
        if grupos[key]['lat'] is None:
            grupos[key]['lat'] = lugar.lat
            grupos[key]['lon'] = lugar.lon
            # Capturar tipo_lugar (tomar el primero encontrado)
            if hasattr(lugar, 'tipo_lugar') and lugar.tipo_lugar:
                grupos[key]['tipo_lugar'] = lugar.tipo_lugar
        
        # Calcular frecuencia efectiva (restando desvinculadas)
        frec_desvinculada = getattr(lugar, 'frecuencia_desvinculada', None)
        if frec_desvinculada is None:
            frec_desvinculada = 0
        
        frec_efectiva = lugar.frecuencia - frec_desvinculada
        
        grupos[key]['frecuencia'] += frec_efectiva  # Solo cuenta las vinculadas
        grupos[key]['frecuencia_total'] += lugar.frecuencia  # Total sin filtrar
        grupos[key]['frecuencia_desvinculada'] += frec_desvinculada
        grupos[key]['frec_titulo'] += getattr(lugar, 'frec_titulo', 0)
        grupos[key]['frec_contenido'] += getattr(lugar, 'frec_contenido', 0)
        
        # Guardar la fecha más reciente de publicación para este lugar
        if lugar.noticia and lugar.noticia.fecha_original:
            current_date = grupos[key]['ultima_mencion']
            if not current_date or lugar.noticia.fecha_original > current_date:
                grupos[key]['ultima_mencion'] = lugar.noticia.fecha_original
            # Registrar fecha para el gráfico de actividad (Altair)
            grupos[key]['fechas_mencion'].append(lugar.noticia.fecha_original)
                
        # Agregar temas
        if lugar.noticia and lugar.noticia.temas:
            # Normalizar separadores (algunos usan ; otros ,)
            raw_temas = lugar.noticia.temas.replace(';', ',')
            for tema in raw_temas.split(','):
                t = tema.strip()
                if t:
                    grupos[key]['temas'][t] += 1
        
        # Guardar info de noticia (evitar duplicados en el mismo lugar)
        if lugar.noticia:
            if not any(n['id'] == lugar.noticia.id for n in grupos[key]['noticias_list']):
                grupos[key]['noticias_list'].append({
                    'id': lugar.noticia.id,
                    'titulo': lugar.noticia.titulo,
                    'publicacion': lugar.noticia.publicacion  # Agregar publicación para filtros cartográficos
                })
        
        # --- VERIFICACIÓN ---
        # Si el lugar está marcado como verificado, el grupo también
        if getattr(lugar, 'verificada', False):
            grupos[key]['verified'] = True
        if getattr(lugar, 'borrado', False):
            grupos[key]['deleted'] = True
    
    # Cruzar con tabla Ciudad para ver si son ciudades "oficiales" (mapeadas manualmente antes)
    nombres_grupos = list(grupos.keys())
    from sqlalchemy import func
    ciudades_manuales = {
        c.name.lower(): c 
        for c in Ciudad.query.filter(func.lower(Ciudad.name).in_([n.lower() for n in nombres_grupos])).all()
    }

    # Update blacklisted status from global Ciudad table
    for nombre in nombres_grupos:
        c_db = ciudades_manuales.get(nombre.lower())
        if c_db:
            grupos[nombre]['blacklisted'] = c_db.blacklisted
    
    import altair as alt
    import pandas as pd
    
    # Convertir a lista y generar Mini Gráficos (Altair Sparkline)
    ciudades = []
    
    for nombre, data in grupos.items():
        is_verified = data.get('verified', False)
        c_db = ciudades_manuales.get(nombre.lower())
        
        # Doble check con tabla Ciudad
        if c_db:
            if not is_verified and c_db.verificada:
                if c_db.lat is not None and c_db.lon is not None and c_db.lat != 0:
                    is_verified = True
                
        # --- LIGHTWEIGHT DATE AGGREGATION ---
        trends_data = []
        if data['fechas_mencion']:
            try:
                from collections import Counter
                counts = Counter()
                for f in data['fechas_mencion']:
                    try:
                        d = pd.to_datetime(f)
                        if pd.notnull(d):
                            counts[d.strftime('%Y-%m')] += 1
                    except:
                        pass
                trends_data = [{'periodo': k, 'count': v} for k, v in sorted(counts.items())]
            except Exception as e:
                current_app.logger.error(f"Error aggregating dates for {nombre}: {e}")
        
        # Validar coordenadas de Ciudad: si son (0,0) ignorar y usar las de data['lat']
        final_lat = data['lat']
        final_lon = data['lon']
        if c_db and c_db.lat is not None and c_db.lat != 0:
            final_lat = c_db.lat
            final_lon = c_db.lon

        ciudades.append({
            'nombre': nombre,
            'lat': final_lat,
            'lon': final_lon,
            'frecuencia': data['frecuencia'],  # Frecuencia EFECTIVA (solo vinculadas)
            'frecuencia_total': data['frecuencia_total'],  # Total sin filtrar
            'frecuencia_desvinculada': data['frecuencia_desvinculada'],  # Total desvinculadas
            'frec_titulo': data['frec_titulo'],
            'frec_contenido': data['frec_contenido'],
            'tipo_lugar': data.get('tipo_lugar', 'unknown'),  # Tipo geográfico
            'ultima_mencion': data['ultima_mencion'] if data['ultima_mencion'] else None,
            'trends_data': trends_data,
            'temas': dict(data['temas']),
            'verified': is_verified,
            'vinculada': data['frecuencia_desvinculada'] < data['frecuencia_total'],  # False si TODAS desvinculadas
            'deleted': data.get('deleted', False),
            'blacklisted': data.get('blacklisted', False),
            'noticias': data.get('noticias_list', [])[:50] # Limitar a 50 para no inflar el JSON
        })
    
    # --- CÁLCULO DE FLUJOS (CONNECTIONS) ---
    flows = []
    
    # 1. Obtener coordenadas de los lugares de publicación (Source)
    # Agrupamos noticias por lugar_publicacion (o ciudad de la publicación como fallback)
    from sqlalchemy import func
    
    # Origen = Prensa.lugar_publicacion OR Publicacion.ciudad
    origen_col = func.coalesce(func.nullif(Prensa.lugar_publicacion, ''), Publicacion.ciudad)
    
    origenes = db.session.query(
        origen_col, 
        func.count(Prensa.id)
    ).select_from(Prensa)\
     .outerjoin(Publicacion, Prensa.id_publicacion == Publicacion.id_publicacion)\
     .filter(Prensa.id.in_(noticia_ids))\
     .group_by(origen_col).all()
    
    # Cache coordenadas origen
    origen_coords = {}
    for nombre_origen, _ in origenes:
        if not nombre_origen: continue
        clean_name = nombre_origen.strip()
        # Intentamos buscar en tabla Ciudad (insensible a mayúsculas)
        c = Ciudad.query.filter(Ciudad.name.ilike(clean_name)).first()
        if c and c.lat and c.lon:
            origen_coords[nombre_origen] = {'lat': c.lat, 'lon': c.lon}
            
    # 2. Construir flujos
    # Traemos (origen_calculado, lugar_mencionado_nombre, lugar_mencionado_lat, lugar_mencionado_lon)
    q_flows = db.session.query(
        origen_col,
        LugarNoticia.nombre,
        LugarNoticia.lat,
        LugarNoticia.lon
    ).select_from(Prensa)\
     .join(LugarNoticia, Prensa.id == LugarNoticia.noticia_id)\
     .outerjoin(Publicacion, Prensa.id_publicacion == Publicacion.id_publicacion)\
     .filter(Prensa.id.in_(noticia_ids))\
     .filter(LugarNoticia.borrado == False)\
     .filter(LugarNoticia.lat.isnot(None))\
     .filter(LugarNoticia.lon.isnot(None))\
     .all()
     
    flow_counts = defaultdict(int)
    
    for origen_nombre, dest_nombre, dest_lat, dest_lon in q_flows:
        if not origen_nombre or origen_nombre not in origen_coords: continue
        
        # Key única para el arco
        flow_key = (origen_nombre, dest_nombre)
        flow_counts[flow_key] += 1
        
        # Guardamos datos necesarios para reconstruir si es la primera vez
        if flow_counts[flow_key] == 1:
            flow_counts[flow_key + ('data',)] = {
                'origin': origen_coords[origen_nombre],
                'dest': {'lat': dest_lat, 'lon': dest_lon},
                'origin_name': origen_nombre,
                'dest_name': dest_nombre
            }
            
    # Formatear salida
    flows = []
    for key, count in flow_counts.items():
        if isinstance(key, tuple) and len(key) == 3 and key[2] == 'data': continue # Skip data keys
        
        data = flow_counts[key + ('data',)]
        flows.append({
            'origin': data['origin'],
            'dest': data['dest'],
            'weight': count,
            'names': f"{data['origin_name']} -> {data['dest_name']}",
            'origin_name': data['origin_name']
        })

    # Calcular rango de fechas (años) global para el slider
    from sqlalchemy import func
    min_anio = db.session.query(func.min(Prensa.anio)).filter(Prensa.proyecto_id == proyecto.id, Prensa.incluido == True).scalar() or 1900
    max_anio = db.session.query(func.max(Prensa.anio)).filter(Prensa.proyecto_id == proyecto.id, Prensa.incluido == True).scalar() or 2025

    # --- CÁLCULO DE CONSTELACIONES NARRATIVAS (Agrupación por Noticia) ---
    # Esto permite conectar lugares que se mencionan juntos en la misma historia
    constellations = defaultdict(list)
    for l in lugares:
        constellations[l.noticia_id].append({
            'nombre': l.nombre,
            'lat': l.lat,
            'lon': l.lon
        })
    
    # Filtrar solo noticias con más de 1 lugar para crear conexiones
    constellation_list = []
    for nid, pts in constellations.items():
        if len(pts) > 1:
            constellation_list.append({
                'id': nid,
                'points': pts
            })

    # --- CÁLCULO DE TRAYECTORIAS NARRATIVAS (Experimental) ---
    trajectories = []
    include_trajectories = request.args.get('include_trajectories') == 'true'
    
    if include_trajectories:
        # Limitamos a un número razonable de trayectorias para no saturar el mapa
        MAX_TRAJECTORIES = 200
        
        # Consultamos noticias con sus lugares y contenido
        # Optimizamos trayendo solo lo necesario
        q_traj = db.session.query(Prensa).options(joinedload(Prensa.lugares))\
            .filter(Prensa.id.in_(noticia_ids))\
            .filter(Prensa.lugares.any())\
            .limit(MAX_TRAJECTORIES) # Limit para rendimiento
            
        docs_traj = q_traj.all()
        
        for doc in docs_traj:
            # Obtenemos lugares válidos
            valid_locs = [l for l in doc.lugares if not l.borrado and l.lat and l.lon]
            
            if len(valid_locs) < 2:
                continue
                
            # Ordenar por aparición en el texto
            # Estrategia: Buscar la primera aparición del nombre en el contenido
            # Si no tiene contenido, usar título. Si no, orden por defecto (id)
            texto_base = (doc.titulo or "") + " " + (doc.contenido or "")
            texto_lower = texto_base.lower()
            
            def get_position(loc):
                pos = texto_lower.find(loc.nombre.lower())
                if pos == -1: return 999999 # Al final si no se encuentra (raro si fue extraído)
                return pos
            
            # Ordenar
            sorted_locs = sorted(valid_locs, key=get_position)
            
            # Construir camino
            points = []
            seen_coords = set()
            for l in sorted_locs:
                # Evitar duplicados consecutivos exactos o muy cercanos podría ser útil, 
                # pero para narrativa A -> A -> B es válido (retorno).
                # Sin embargo, leaflet curve necesita puntos distintos para curvas bonitas o manejar bucles.
                # Dejamos tal cual por ahora.
                points.append({
                    'nombre': l.nombre,
                    'lat': l.lat,
                    'lon': l.lon
                })
            
            if len(points) >= 2:
                trajectories.append({
                    'doc_id': doc.id,
                    'titulo': doc.titulo,
                    'fecha': doc.fecha_original,
                    'points': points
                })

    # --- FILTRADO FINAL PARA MAPA CORPUS (NO GESTOR) ---
    # En el mapa corpus, solo mostrar ubicaciones con al menos 1 mención vinculada
    if not all_states and not solo_borrados:
        ciudades = [c for c in ciudades if c.get('frecuencia', 0) > 0]

    return {
        'ciudades': ciudades,
        'flows': flows,
        'trajectories': trajectories,
        'constellations': constellation_list,
        'meta': {
            'min_anio': int(min_anio),
            'max_anio': int(max_anio)
        }
    }


@noticias_bp.route('/cartografia/topografia-semantica')
# @login_required
def topografia_semantica_view():
    from utils import get_proyecto_activo
    from models import Publicacion
    from datetime import datetime
    from sqlalchemy import func
    
    proyecto = get_proyecto_activo()
    if not proyecto:
        flash('Seleccione un proyecto activo.', 'warning')
        return redirect(url_for('proyectos.listar'))

    try:
        publicaciones = [p[0] for p in db.session.query(Publicacion.nombre)
                         .join(Prensa, Prensa.id_publicacion == Publicacion.id_publicacion)
                         .filter(Prensa.proyecto_id == proyecto.id)
                         .distinct().order_by(Publicacion.nombre).all()]
                         
        min_date_val = db.session.query(func.min(Prensa.fecha_original)).filter(Prensa.proyecto_id == proyecto.id).scalar()
        max_date_val = db.session.query(func.max(Prensa.fecha_original)).filter(Prensa.proyecto_id == proyecto.id).scalar()
        
        import re
        def extract_year(val):
            if not val: return None
            # Buscar 4 dígitos seguidos
            match = re.search(r'\d{4}', str(val))
            return int(match.group(0)) if match else None

        # Valores por defecto para el slider
        min_year_parsed = extract_year(min_date_val)
        max_year_parsed = extract_year(max_date_val)
        
        min_year = min_year_parsed if min_year_parsed else 1900
        max_year = max_year_parsed if max_year_parsed else datetime.now().year

        return render_template('topografia_semantica.html', 
                               proyecto=proyecto,
                               publicaciones=publicaciones,
                               min_year=min_year,
                               max_year=max_year)
    except Exception as e:
        import traceback
        print(f"ERROR en topografia_semantica_view: {str(e)}")
        traceback.print_exc()
        return f"Error interno: {str(e)}", 500


@noticias_bp.route('/api/cartografia/semantica')
@login_required
def cartografia_semantica_api():
    """
    API experimental para la Topografía Semántica.
    Calcula la "elevación" de un concepto en el territorio.
    """
    concepto = request.args.get('concepto', '').strip().lower()
    proyecto_id = request.args.get('proyecto_id') or 1 # Fallback
    
    if not concepto:
        return {'points': []}


    from services.ai_service import AIService
    
    # Seleccionar proveedor y modelo según potencia
    potencia_ia = request.args.get('potencia', 'flash') 
    provider = 'gemini'
    model = 'gemini-2.0-flash'
    
    if potencia_ia == 'pro':
        model = 'gemini-2.0-flash' 
    elif potencia_ia == 'openai':
        provider = 'openai'
        model = 'gpt-4o'
    elif potencia_ia == 'anthropic':
        provider = 'anthropic'
        model = 'claude-3-5-sonnet-20240620'
    elif potencia_ia == 'llama':
        provider = 'llama'
        model = 'llama3'
    
    terminos = [concepto]
    
    # Intentar expansión con IA
    try:
        service = AIService(provider=provider, model=model, user=current_user)
        if service.is_configured():
            contexto = {
                "proyecto_id": proyecto_id, 
                "tipo": "prensa_historica",
                "instruccion": f"Genera términos específicos para '{concepto}'. NO mezcles este concepto con otros temas ajenos. Mantén la pureza semántica del término."
            }
            expansion_ai = service.expand_semantic_concept(concepto, contexto)
            if expansion_ai:
                # Normalizar a minúsculas para evitar fallos de coincidencia en Python post-SQL
                expansion_ai = [t.lower().strip() for t in expansion_ai]
                terminos.extend(expansion_ai)
    except Exception as e:
        print(f"Error AI Semantic Expansion: {e}")

    # Fallback si falla la IA o no hay resultados (Diccionario mínimo)
    if len(terminos) == 1:
        expansion_fallback = {
            'miedo': ['terror', 'pánico', 'alarma', 'susto', 'horror', 'temor'],
            'guerra': ['batalla', 'combate', 'fuego', 'tropas', 'cañones', 'sangre'],
            'progreso': ['ferrocarril', 'industria', 'comercio', 'adelanto', 'civilización'],
            'paz': ['tratado', 'armisticio', 'concordia', 'tranquilidad'],
            'enfermedad': ['cólera', 'fiebre', 'peste', 'contagio', 'muerte', 'virus']
        }
        if concepto in expansion_fallback:
            terminos.extend(expansion_fallback[concepto])

    # Deduplicar
    terminos = list(dict.fromkeys(terminos))
        
    # --- 2. Búsqueda y Puntuación ---
    from models import Prensa, LugarNoticia
    from sqlalchemy import or_, func

    # Filtros base
    fecha_desde = request.args.get('fecha_desde')
    fecha_hasta = request.args.get('fecha_hasta')
    publicacion = request.args.get('publicacion')
    noticia_id = request.args.get('noticia_id')

    # Necesitamos ID para agrupar, fecha (año) para el time-lapse y el contenido para el sentimiento
    query = db.session.query(
        LugarNoticia.lat, 
        LugarNoticia.lon, 
        LugarNoticia.frecuencia,
        Prensa.fecha_original,
        Prensa.contenido,
        Prensa.id,
        LugarNoticia.nombre
    ).join(Prensa).filter(
        Prensa.proyecto_id == proyecto_id,
        Prensa.incluido == True,
        LugarNoticia.borrado == False,
        LugarNoticia.lat.isnot(None),
        LugarNoticia.lon.isnot(None)
    )

    if fecha_desde:
        query = query.filter(text(f"{SQL_PRENSA_DATE} >= :d").params(d=fecha_desde))
    if fecha_hasta:
        query = query.filter(text(f"{SQL_PRENSA_DATE} <= :h").params(h=fecha_hasta))
    if publicacion:
        query = query.filter(Prensa.publicacion == publicacion)
    if noticia_id:
        query = query.filter(Prensa.id == noticia_id)
    
    # Construir filtro de texto (ILIKE)
    filters = [Prensa.contenido.ilike(f"%{t}%") for t in terminos]
    if filters:
        query = query.filter(or_(*filters))
        
    # Ejecutar (Límite dinámico para geosemántica)
    try:
        limit_val = int(request.args.get('limit', 2000))
    except:
        limit_val = 2000

    if limit_val > 0:
        results = query.limit(limit_val).all()
    else:
        results = query.all()
    
    # --- 3. Procesamiento (Agregación + Sentimiento Opcional) ---
    include_sentiment = request.args.get('sentiment') == 'true'
    sentiment_limit = int(request.args.get('sentiment_limit', 40))
    # Seguridad: Admitir 0 (desactivado), Máximo 100
    sentiment_limit = max(0, min(100, sentiment_limit))
    
    puntos_raw = []
    # Usar dict para analizar sentimiento solo una vez por noticia única
    noticias_unicas = {} # id -> texto
    
    for lat, lon, freq, fecha, contenido, prensa_id, nombre in results:
        year = None
        if fecha:
            if hasattr(fecha, 'year'):
                year = fecha.year
            else:
                match = re.search(r'\d{4}', str(fecha))
                if match: year = int(match.group(0))
        
        # Identificar términos que activaron este punto (huellas semánticas)
        txt = contenido.lower()
        matched = [t for t in terminos if t in txt]

        puntos_raw.append({
            'lat': lat,
            'lon': lon,
            'weight': freq,
            'year': year,
            'prensa_id': prensa_id,
            'nombre': nombre,
            'matched_terms': matched,
            'sentiment': 0 # Default neutral
        })
        
        if include_sentiment and prensa_id not in noticias_unicas:
            # Respetar el límite configurado por el usuario (o administrador)
            if len(noticias_unicas) < sentiment_limit:
                noticias_unicas[prensa_id] = contenido[:500]

    # Sentimiento por lotes si se solicita
    if include_sentiment and noticias_unicas:
        from services.gemini_service import analyze_sentiment_batch
        from utils import get_proyecto_activo
        proyecto = get_proyecto_activo()
        contexto = {"tema": proyecto.nombre if proyecto else ""}
        
        ids_ordenados = list(noticias_unicas.keys())
        textos_ordenados = [noticias_unicas[id] for id in ids_ordenados]
        
        all_scores = []
        # Procesar en bloques de 20
        for i in range(0, len(textos_ordenados), 20):
            batch = textos_ordenados[i:i+20]
            scores = analyze_sentiment_batch(batch, contexto)
            all_scores.extend(scores)
        
        # Crear mapa de id -> score
        sentiment_map = {}
        for idx, score in enumerate(all_scores):
            if idx < len(ids_ordenados):
                sentiment_map[ids_ordenados[idx]] = score
        
        # Asignar scores a los puntos
        for pt in puntos_raw:
            pid = pt['prensa_id']
            if pid in sentiment_map:
                pt['sentiment'] = sentiment_map[pid]

    return {'points': puntos_raw, 'terms': terminos}


@noticias_bp.route('/api/noticia/toggle_incluido/<int:id>', methods=['POST'])
@noticias_bp.route('/api/noticia/<int:id>/toggle_incluido', methods=['POST'])

@login_required
def toggle_incluido(id):
    """
    Activa o desactiva una noticia del estudio global.
    """
    from models import Prensa
    noticia = db.session.get(Prensa, id)
    if not noticia:
        return jsonify({'error': 'Noticia no encontrada'}), 404
    
    nuevo_estado = not noticia.incluido
    noticia.incluido = nuevo_estado
    db.session.commit()
    
    return jsonify({
        'success': True,
        'id': noticia.id,
        'incluido': noticia.incluido,
        'message': f'Noticia {"activada" if noticia.incluido else "pausada"}'
    })
    
@noticias_bp.route('/api/cartografia/semantica/interpretar', methods=['POST'])
@login_required
def interpretar_topografia_api():
    """
    API para generar una lectura interpretativa de la topografía semántica.
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No se recibieron datos JSON'}), 400
            
        concepto = data.get('concepto')
        terminos = data.get('terminos', [])
        puntos = data.get('puntos', [])
        
        if not concepto or not puntos:
            return jsonify({'error': f'Faltan datos para la interpretación (Concepto: {bool(concepto)}, Puntos: {len(puntos)})'}), 400
            
        # Crear un resumen de los puntos para el prompt
        # Guard con validación de llaves
        valid_puntos = [p for p in puntos if all(k in p for k in ('lat', 'lon', 'weight'))]
        if not valid_puntos:
            return jsonify({'error': 'Los puntos proporcionados no tienen el formato correcto (requieren lat, lon, weight)'}), 400

        puntos_ordenados = sorted(valid_puntos, key=lambda x: x.get('weight', 0), reverse=True)[:15]
        
        # --- NUEVO: Obtener evidencias narrativas (snippets) ---
        from models import Prensa
        evidencias = []
        doc_ids = [p.get('prensa_id') for p in puntos_ordenados if p.get('prensa_id')]
        
        if doc_ids:
            # Traer contenido y títulos de los documentos top
            docs = Prensa.query.filter(Prensa.id.in_(doc_ids)).all()
            doc_map = {d.id: d for d in docs}
            
            for p in puntos_ordenados:
                pid = p.get('prensa_id')
                if pid and pid in doc_map:
                    doc = doc_map[pid]
                    snippet = (doc.contenido[:500] + "...") if doc.contenido else ""
                    evidencias.append({
                        'lat': p.get('lat'),
                        'lon': p.get('lon'),
                        'titulo': doc.titulo,
                        'texto': snippet,
                        'fecha': str(doc.fecha_original) if doc.fecha_original else "S/F"
                    })

        resumen_puntos = "; ".join([f"({p.get('lat')}, {p.get('lon')}) peso {p.get('weight')}" for p in puntos_ordenados])
        
        from services.gemini_service import interpret_semantic_topography_map
        from utils import get_proyecto_activo
        
        proyecto = get_proyecto_activo()
        contexto = {
            "proyecto_nombre": proyecto.nombre if proyecto else "Desconocido",
            "proyecto_descripcion": proyecto.descripcion if proyecto else "",
            "evidencias": evidencias
        }
        
        logging.info(f"[INTERPRETAR] Solicitando interpretación para concepto: {concepto}")
        lectura = interpret_semantic_topography_map(concepto, terminos, resumen_puntos, contexto)
        
        if not lectura:
            logging.error(f"[INTERPRETAR] Gemini retornó vacío para concepto: {concepto}")
            return jsonify({'error': 'No se pudo generar la lectura IA (Gemini retornó vacío)'}), 500
            
        return jsonify({'lectura': lectura})
    except Exception as e:
        logging.exception(f"Error crítico en interpretar_topografia_api: {e}")
        return jsonify({'error': f'Error interno del servidor: {str(e)}'}), 500

@noticias_bp.route('/api/cartografia/semantica/detalles')
@login_required
def cartografia_semantica_detalles_api():
    """
    Devuelve noticias específicas para un concepto en un punto geográfico.
    Utilizado por el 'Explorador de Cumbres'.
    """
    concepto = request.args.get('concepto', '').strip()
    lat = request.args.get('lat')
    lon = request.args.get('lon')
    proyecto_id = request.args.get('proyecto_id')
    
    if not concepto or not lat or not lon:
        return jsonify({'error': 'Faltan parámetros'}), 400
        
    # Buscamos términos expandidos para ser precisos
    # (En producción esto debería estar cacheado)
    from services.ai_service import AIService
    service = AIService()
    contexto = {"proyecto_id": proyecto_id}
    
    # Soporte para conceptos combinados (A + B)
    conceptos_lista = [c.strip() for c in concepto.split('+')]
    terminos = []
    
    for c in conceptos_lista:
        terminos.append(c)
        if service.is_configured():
            try:
                ext = service.expand_semantic_concept(c, contexto)
                if ext: terminos.extend(ext)
            except:
                pass
                
    # Deduplicar
    terminos = list(dict.fromkeys(terminos))
        
    from models import Prensa, LugarNoticia
    from sqlalchemy import and_, or_
    
    # Tolerancia de coordenadas (aprox 0.2 grados ~ 22km)
    tolerance = 0.2
    lat_f = float(lat)
    lon_f = float(lon)
    
    query = db.session.query(
        Prensa.titulo, 
        Prensa.fecha_original, 
        Prensa.contenido,
        Prensa.id
    ).join(LugarNoticia).filter(
        and_(
            Prensa.proyecto_id == proyecto_id,
            LugarNoticia.lat.between(lat_f - tolerance, lat_f + tolerance),
            LugarNoticia.lon.between(lon_f - tolerance, lon_f + tolerance),
            LugarNoticia.borrado == False
        )
    )
    
    filters = [Prensa.contenido.ilike(f"%{t}%") for t in terminos]
    query = query.filter(or_(*filters))
    
    results = query.limit(10).all()
    
    import re
    noticias = []
    for t, f, c, nid in results:
        # Extraer fragmento relevante (alrededor del primer término encontrado)
        snippet = ""
        if c:
            c_low = c.lower()
            first_pos = -1
            for term in terminos:
                pos = c_low.find(term.lower())
                if pos != -1 and (first_pos == -1 or pos < first_pos):
                    first_pos = pos
            
            if first_pos != -1:
                start = max(0, first_pos - 150)
                end = min(len(c), first_pos + 150)
                snippet = c[start:end]
                if start > 0: snippet = "..." + snippet
                if end < len(c): snippet = snippet + "..."
            else:
                snippet = c[:300] + "..."

            # Resaltar términos (subrayado sutil vía CSS)
            for term in terminos:
                try:
                    pattern = re.compile(re.escape(term), re.IGNORECASE)
                    snippet = pattern.sub(lambda m: f'<span class="semantic-match">{m.group(0)}</span>', snippet)
                except:
                    pass

        noticias.append({
            'titulo': t,
            'fecha': str(f),
            'snippet': snippet,
            'url': url_for('noticias.detalle_noticia', id=nid)
        })
        
    return jsonify({'noticias': noticias, 'terminos': terminos})

@noticias_bp.route('/api/cartografia/rareza')
@login_required
def cartografia_rareza_api():
    """
    API para la Brújula de Rarezas (Detección de Anomalías).
    Identifica puntos geográficos con discurso singular.
    """
    from services.ai_service import AIService 
    from advanced_analytics import AnalisisAvanzado
    
    proyecto_id = request.args.get('proyecto_id')
    if not proyecto_id:
        from utils import get_proyecto_activo
        p = get_proyecto_activo()
        if p: proyecto_id = p.id
        
    if not proyecto_id:
        return jsonify({'anomalias': []})

    # Filtros base
    fecha_desde = request.args.get('fecha_desde')
    fecha_hasta = request.args.get('fecha_hasta')
    publicacion = request.args.get('publicacion')
    noticia_id = request.args.get('noticia_id')

    # Recuperar datos geolocalizados
    # Optimizamos trayendo solo los campos necesarios
    query = db.session.query(
        LugarNoticia.lat, 
        LugarNoticia.lon, 
        Prensa.contenido,
        Prensa.titulo
    ).join(Prensa).filter(
        Prensa.proyecto_id == proyecto_id,
        Prensa.incluido == True,
        LugarNoticia.borrado == False,
        LugarNoticia.lat.isnot(None),
        LugarNoticia.lon.isnot(None)
    )

    if fecha_desde:
        query = query.filter(text(f"{SQL_PRENSA_DATE} >= :d").params(d=fecha_desde))
    if fecha_hasta:
        query = query.filter(text(f"{SQL_PRENSA_DATE} <= :h").params(h=fecha_hasta))
    if publicacion:
        query = query.filter(Prensa.publicacion == publicacion)
    if noticia_id:
        query = query.filter(Prensa.id == noticia_id)
    
    # Límite de seguridad para análisis en tiempo real
    try:
        limit_val = int(request.args.get('limit', 3000))
        if limit_val <= 0: limit_val = 50000 # Caso "TODOS" con tope razonable
    except:
        limit_val = 3000 

    results = query.limit(limit_val).all()
    
    if not results:
        return jsonify({'anomalias': []})
        
    # Formatear para el analizador
    docs = []
    for lat, lon, content, titulo in results:
        docs.append({
            'lat': lat,
            'lon': lon,
            'contenido': content or '',
            'titulo': titulo or ''
        })
        
    # Análisis
    analisis = AnalisisAvanzado(db)
    
    # Parámetros opcionales
    top_k = int(request.args.get('top_k', 60))
    potencia_ia = request.args.get('potencia', 'flash') 
    
    # Determinar proveedor y modelo
    provider = 'gemini'
    model_name = 'gemini-2.0-flash'
    if potencia_ia == 'pro': model_name = 'gemini-2.0-flash'
    elif potencia_ia == 'gemini-3-flash': model_name = 'gemini-3-flash'
    elif potencia_ia == 'gemini-3-pro': model_name = 'gemini-3-pro'
    elif potencia_ia == 'openai': provider = 'openai'; model_name = 'gpt-4o'
    elif potencia_ia == 'anthropic': provider = 'anthropic'; model_name = 'claude-3-5-sonnet-20240620'
    elif potencia_ia == 'llama': provider = 'llama'; model_name = 'llama3'

    # Instanciamos servicio IA
    service = AIService(provider=provider, model=model_name)
    
    # Por defecto precision 3 (100m) para agrupar calles/barrios
    try:
        resultado = analisis.detectar_anomalias_geograficas(docs, precision_geo=3, top_k=top_k, ai_service=service)
    except Exception as e:
        current_app.logger.error(f"Error en Brújula de Rarezas: {e}")
        return jsonify({'error': str(e)}), 500
        
    return jsonify(resultado)

# --- API para exportar GeoJSON ---
@noticias_bp.route('/api/cartografia_corpus/export', methods=['GET'])
@login_required
def cartografia_corpus_export():
    import json
    from flask import Response
    
    # Reutilizar lógica de filtrado de cartografia_corpus_api
    fecha_desde = request.args.get('fecha_desde')
    fecha_hasta = request.args.get('fecha_hasta')
    publicacion = request.args.get('publicacion')
    
    from utils import get_proyecto_activo
    from models import LugarNoticia, Ciudad, Publicacion
    from collections import defaultdict
    proyecto = get_proyecto_activo()
    
    query = Prensa.query
    if proyecto:
        query = query.filter_by(proyecto_id=proyecto.id)
    else:
        return jsonify({'error': 'No hay proyecto activo'}), 400
        
    if fecha_desde:
        query = query.filter(text(f"{SQL_PRENSA_DATE} >= :d").params(d=fecha_desde))
    if fecha_hasta:
        query = query.filter(text(f"{SQL_PRENSA_DATE} <= :h").params(h=fecha_hasta))
    if publicacion:
        query = query.filter(Prensa.publicacion == publicacion)
    
    # Parametro tipo: 'nodes' (defecto) o 'flows'
    export_type = request.args.get('type', 'nodes')
    
    noticia_ids = [n.id for n in query.with_entities(Prensa.id).all()]
    features = []
    
    if noticia_ids:
        if export_type == 'flows':
            # Exportar Flujos (LineStrings)
            # 1. Obtener coordenadas de ciudades (Origen)
            ciudades = Ciudad.query.all()
            coord_map = {c.name.lower().strip(): (c.lat, c.lon) for c in ciudades if c.lat and c.lon}
            
            # 2. Consultar Flujos
            from models import Publicacion
            from sqlalchemy import func
            
            # Fallback origen
            origen_col = func.coalesce(func.nullif(Prensa.lugar_publicacion, ''), Publicacion.ciudad)
            
            q = db.session.query(origen_col, LugarNoticia.nombre, LugarNoticia.lat, LugarNoticia.lon)\
                .select_from(Prensa)\
                .join(LugarNoticia, Prensa.id == LugarNoticia.noticia_id)\
                .outerjoin(Publicacion, Prensa.id_publicacion == Publicacion.id_publicacion)\
                .filter(Prensa.id.in_(noticia_ids))\
                .filter(LugarNoticia.borrado == False)\
                .filter(LugarNoticia.lat.isnot(None))\
                .all()
                
            flow_counts = defaultdict(int)
            for orig, dest, d_lat, d_lon in q:
                if not orig: continue
                orig_norm = orig.lower().strip()
                if orig_norm not in coord_map: continue
                
                key = (orig, dest)
                flow_counts[key] += 1
                if flow_counts[key] == 1:
                    flow_counts[key + ('data',)] = {
                        'o_coords': coord_map[orig_norm],
                        'd_coords': (d_lat, d_lon)
                    }
            
            for key, count in flow_counts.items():
                if len(key) == 3: continue
                data = flow_counts[key + ('data',)]
                o_lat, o_lon = data['o_coords']
                d_lat, d_lon = data['d_coords']
                
                features.append({
                    "type": "Feature",
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [[o_lon, o_lat], [d_lon, d_lat]] # GeoJSON uses [Lon, Lat]
                    },
                    "properties": {
                        "source": key[0],
                        "target": key[1],
                        "weight": count
                    }
                })
                
        else:
            # Exportar Nodos (Points) - Lógica existente mejorada
            lugares = LugarNoticia.query.filter(
                LugarNoticia.noticia_id.in_(noticia_ids),
                LugarNoticia.borrado == False,
                LugarNoticia.lat.isnot(None)
            ).all()
            
            grupos = defaultdict(lambda: {'lat': None, 'lon': None, 'frecuencia': 0})
            for lugar in lugares:
                grupos[lugar.nombre]['lat'] = lugar.lat
                grupos[lugar.nombre]['lon'] = lugar.lon
                grupos[lugar.nombre]['frecuencia'] += lugar.frecuencia
                
            for nombre, data in grupos.items():
                features.append({
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [data['lon'], data['lat']]
                    },
                    "properties": {
                        "nombre": nombre,
                        "frecuencia": data['frecuencia']
                    }
                })
            
    geojson = {"type": "FeatureCollection", "features": features}
    
    filename = f"mapa_corpus_{export_type}.geojson"
    response = Response(json.dumps(geojson, indent=2), mimetype='application/json')
    response.headers['Content-Disposition'] = f'attachment; filename={filename}'
    return response

# --- Vista de detalle de noticia (ruta corta) ---
@noticias_bp.route('/noticias/<int:id>', methods=['GET'])
@login_required
def detalle_noticia_corto(id):
    """Ruta alternativa más corta para detalle de noticia"""
    return detalle_noticia(id)

# --- Vista de detalle de noticia ---
@noticias_bp.route('/noticias/detalle/<int:id>', methods=['GET'], endpoint='detalle_noticia')
@login_required
def detalle_noticia(id):
    noticia = db.session.get(Prensa, id)
    if not noticia:
        flash('Noticia no encontrada', 'danger')
        return redirect(url_for('noticias.listar'))
    
    # Calculate previous and next article IDs
    proyecto = get_proyecto_activo()
    prev_id = None
    next_id = None
    prev_id_fecha = None
    next_id_fecha = None
    
    if proyecto:
        # Get previous article (lower ID in same project)
        prev_noticia = Prensa.query.filter(
            Prensa.proyecto_id == proyecto.id,
            Prensa.id < id
        ).order_by(Prensa.id.desc()).first()
        
        # Get next article (higher ID in same project)
        next_noticia = Prensa.query.filter(
            Prensa.proyecto_id == proyecto.id,
            Prensa.id > id
        ).order_by(Prensa.id.asc()).first()
        
        if prev_noticia:
            prev_id = prev_noticia.id
        if next_noticia:
            next_id = next_noticia.id
        
        
        # Date-based navigation
        if noticia.fecha_original:
            # Get previous article by date (earlier date, or same date with lower ID)
            prev_noticia_fecha = Prensa.query.filter(
                Prensa.proyecto_id == proyecto.id,
                or_(
                    Prensa.fecha_original < noticia.fecha_original,
                    and_(
                        Prensa.fecha_original == noticia.fecha_original,
                        Prensa.id < id
                    )
                )
            ).order_by(Prensa.fecha_original.desc(), Prensa.id.desc()).first()
            
            # Get next article by date (later date, or same date with higher ID)
            next_noticia_fecha = Prensa.query.filter(
                Prensa.proyecto_id == proyecto.id,
                or_(
                    Prensa.fecha_original > noticia.fecha_original,
                    and_(
                        Prensa.fecha_original == noticia.fecha_original,
                        Prensa.id > id
                    )
                )
            ).order_by(Prensa.fecha_original.asc(), Prensa.id.asc()).first()
            
            if prev_noticia_fecha:
                prev_id_fecha = prev_noticia_fecha.id
            if next_noticia_fecha:
                next_id_fecha = next_noticia_fecha.id
    
    return render_template('detalle_noticia.html', noticia=noticia, 
                         prev_id=prev_id, next_id=next_id,
                         prev_id_fecha=prev_id_fecha, next_id_fecha=next_id_fecha)

# --- API para cartografía de la noticia ---
@noticias_bp.route('/api/cartografia_noticia/<int:id>', methods=['GET'])
@login_required
def cartografia_noticia(id):
    # Obtener noticia
    noticia = db.session.get(Prensa, id)
    if not noticia:
        print(f"[cartografia_noticia] Noticia con id {id} no encontrada")
        return jsonify({
            'idiomas': [], 'tipos_autor': [], 'publicaciones': [], 'ciudades': [],
            'estadisticas': [], 'temas': [], 'licencias': [], 'formatos': [], 'paises': []
        }), 200

    proyecto_id = noticia.proyecto_id if hasattr(noticia, 'proyecto_id') else None
    
    # 1. Metadatos básicos (Optimizado: Solo los necesarios para el proyecto)
    idiomas = valores_unicos_prensa(Prensa.idioma, proyecto_id) if proyecto_id else []
    tipos_autor = valores_unicos_prensa(Prensa.tipo_autor, proyecto_id) if proyecto_id else []
    
    # 2. Extracción de ubicaciones (NLP)
    ubicaciones_detectadas = set()
    conteo = Counter()
    
    from services.gemini_service import clean_location_name
    
    # ── LISTA NEGRA GLOBAL: cargar nombres blacklisted en Ciudad ──────────────────
    blacklist_global_ner = {
        r[0].strip().lower() for r in db.session.query(Ciudad.name).filter(
            Ciudad.blacklisted == True
        ).all()
    }
    # También excluir los borrados de este proyecto específico
    nombres_borrados_proyecto = {
        r[0].strip().lower() for r in db.session.query(LugarNoticia.nombre).filter_by(
            noticia_id=id, borrado=True
        ).all()
    }
    excludes_ner = blacklist_global_ner | nombres_borrados_proyecto
    # ─────────────────────────────────────────────────────────────────────────────
    
    nlp = get_nlp()
    if nlp:
        # Procesar contenido si existe
        if noticia.contenido and len(noticia.contenido.strip()) > 5:
            from utils import load_config
            config = load_config()
            limit = config.get('max_char_limit', 15000)
            
            doc_c = nlp(noticia.contenido[:limit]) 
            raw_locs_c = [ent.text.strip() for ent in doc_c.ents if ent.label_ in ('LOC', 'GPE') and len(ent.text.strip()) > 2]
            locs_c = [clean_location_name(l) for l in raw_locs_c if clean_location_name(l) and clean_location_name(l).lower() not in excludes_ner]
            ubicaciones_detectadas.update(locs_c)
            conteo.update(locs_c)
            
        # Procesar título
        if noticia.titulo:
            doc_t = nlp(noticia.titulo)
            raw_locs_t = [ent.text.strip() for ent in doc_t.ents if ent.label_ in ('LOC', 'GPE') and len(ent.text.strip()) > 2]
            locs_t = [clean_location_name(l) for l in raw_locs_t if clean_location_name(l) and clean_location_name(l).lower() not in excludes_ner]
            ubicaciones_detectadas.update(locs_t)
            conteo.update(locs_t)


    # --- DEDUPLICACIÓN DE ANIDAMIENTO ---
    if conteo:
        from services.gemini_service import merge_nested_locations
        conteo_dedup = merge_nested_locations(conteo)
        ubicaciones_detectadas = set(conteo_dedup.keys())
        # No sobreescribimos 'conteo' (Counter) completamente porque se usa abajo, 
        # pero actualizamos para reflejar los nombres filtrados
        conteo = Counter(conteo_dedup)

    # 3. Guardar nuevos lugares detectados (Geocodificación con caché interna)
    if ubicaciones_detectadas:
        # Obtener nombres borrados GLOBALMENTE (Solo nombres para ahorrar memoria)
        nombres_borrados = {
            r[0] for r in db.session.query(LugarNoticia.nombre).filter_by(borrado=True).distinct().all()
        }
        
        # Obtener nombres YA EXISTENTES para esta noticia
        nombres_actuales = {
            r[0] for r in db.session.query(LugarNoticia.nombre).filter_by(noticia_id=id, borrado=False).all()
        }

        geocodificados = 0
        for nombre in ubicaciones_detectadas:
            nombre = nombre.strip()
            if not nombre: continue
            
            if geocodificados >= 5:
                break
                
            if nombre in nombres_borrados or nombre in nombres_actuales:
                continue
                
            # Intentar obtener de la caché local (Tabla Ciudad)
            ciudad_db = Ciudad.query.filter_by(name=nombre).first()
            lat, lon = None, None
            tipo_geografico = 'unknown' # Para LugarNoticia.tipo_lugar
            
            if ciudad_db and ciudad_db.lat is not None:
                lat, lon = ciudad_db.lat, ciudad_db.lon
                tipo_geografico = ciudad_db.tipo_lugar or 'unknown'
            else:
                # Si no está en caché, geocodificar externamente
                try:
                    resp = requests.get('https://nominatim.openstreetmap.org/search', 
                                     params={'q': nombre, 'format': 'json', 'limit': 1},
                                     headers={'User-Agent': 'Hesiox-App/1.2'}, timeout=4)
                    data_geo = resp.json()
                    if data_geo:
                        lat, lon = float(data_geo[0]['lat']), float(data_geo[0]['lon'])
                        tipo_geografico = data_geo[0].get('type', 'unknown')
                        
                        # Guardar en Ciudad para futuras noticias
                        if not ciudad_db:
                            db.session.add(Ciudad(name=nombre, lat=lat, lon=lon, tipo_lugar=tipo_geografico))
                        else:
                            ciudad_db.lat, ciudad_db.lon = lat, lon
                            ciudad_db.tipo_lugar = tipo_geografico
                        
                        db.session.commit()
                        geocodificados += 1
                        time.sleep(1) # Respetar rate limiting
                except Exception as e:
                    print(f"[cartografia_noticia] Error geocodificando {nombre}: {e}")

            if lat is not None and lon is not None:
                nombre_clean = nombre.strip()
                nuevo = LugarNoticia(
                    noticia_id=id, nombre=nombre_clean, lat=lat, lon=lon,
                    frecuencia=conteo.get(nombre, 1), tipo='extraido', 
                    tipo_lugar=tipo_geografico, borrado=False
                )
                db.session.add(nuevo)
                db.session.commit()

    # 4. Obtener resultados finales para la UI (Agregación y Verificación)
    lugares_bd = LugarNoticia.query.filter_by(noticia_id=id, borrado=False).all()
    ciudades_map = {} # Diccionario para agregar por nombre normalizado
    
    # Obtener todas las ciudades verificadas de una vez para optimizar
    nombres_lugares = [l.nombre for l in lugares_bd]
    ciudades_verificadas_db = {
        c.name.lower(): c 
        for c in Ciudad.query.filter(Ciudad.name.in_(nombres_lugares)).all()
    }

    for l in lugares_bd:
        key = l.nombre.lower().strip()
        
        # Determinar si está verificado (usar campo verificada del modelo)
        is_verified = l.verificada if hasattr(l, 'verificada') else False
        # También considerar verificado si existe en tabla Ciudad (retrocompatibilidad)
        if not is_verified and key in ciudades_verificadas_db:
            c_db = ciudades_verificadas_db[key]
            if c_db.lat is not None and c_db.lon is not None:
                is_verified = True
        
        # Obtener vinculada status
        is_vinculada = l.vinculada if hasattr(l, 'vinculada') else True
        
        # Obtener frecuencia_desvinculada
        frec_desvinculada = l.frecuencia_desvinculada if hasattr(l, 'frecuencia_desvinculada') and l.frecuencia_desvinculada is not None else 0
        frec_efectiva = l.frecuencia - frec_desvinculada
        
        if key in ciudades_map:
            # Si ya existe, nos quedamos con la frecuencia MÁXIMA (asumimos que son duplicados redundantes)
            existente = ciudades_map[key]
            existente['id'] = l.id  # Actualizar con el último ID
            existente['frecuencia'] = max(existente['frecuencia'], l.frecuencia)
            existente['frecuencia_desvinculada'] = frec_desvinculada
            existente['frecuencia_efectiva'] = max(existente.get('frecuencia_efectiva', 0), frec_efectiva)
            existente['en_titulo'] = existente['en_titulo'] or l.en_titulo
            existente['en_contenido'] = existente['en_contenido'] or l.en_contenido
            # Mantenemos las coordenadas del último registro procesado (asumimos consistencia o última corrección)
            existente['lat'] = l.lat 
            existente['lon'] = l.lon
            # Si alguno está verificado, el agregado también (aunque la lógica de arriba ya lo cubre por nombre)
            existente['verified'] = is_verified
            # Mantener vinculada status
            existente['vinculada'] = is_vinculada
        else:
            # Nuevo item agregado
            ciudades_map[key] = {
                'id': l.id,
                'lugar': l.nombre, 
                'nombre': l.nombre, 
                'lat': l.lat, 
                'lon': l.lon, 
                'frecuencia': l.frecuencia,
                'frecuencia_desvinculada': frec_desvinculada,
                'frecuencia_efectiva': frec_efectiva,
                'en_titulo': l.en_titulo, 
                'en_contenido': l.en_contenido,
                'verified': is_verified,
                'vinculada': is_vinculada
            }

    # Convertir mapa a listas
    ciudades = list(ciudades_map.values())
    estadisticas = list(ciudades_map.values())

    # 5. Listas auxiliares (Optimizadas con DISTINCT)
    if proyecto_id:
        publicaciones = [r[0] for r in db.session.query(Publicacion.nombre).filter_by(proyecto_id=proyecto_id).order_by(Publicacion.nombre).all()]
    else:
        publicaciones = [r[0] for r in db.session.query(Publicacion.nombre).order_by(Publicacion.nombre).all()]

    # Temas, Licencias, Formatos (DISTINCT en lugar de cargar todos los objetos)
    temas_raw = db.session.query(Prensa.temas).filter(Prensa.proyecto_id == proyecto_id if proyecto_id else True).distinct().all()
    temas_set = set()
    for (t_str,) in temas_raw:
        if t_str:
            for t in t_str.split(','):
                if t.strip(): temas_set.add(t.strip())
    temas = sorted(temas_set)

    # Licencias y Formatos (DISTINCT)
    licencias = sorted(set([r[0] for r in db.session.query(Publicacion.licencia).filter(Publicacion.licencia != None).distinct().all()] + 
                          [r[0] for r in db.session.query(Prensa.licencia).filter(Prensa.licencia != None).distinct().all()] + ["CC BY 4.0"]))
    
    formatos = sorted(set([r[0] for r in db.session.query(Publicacion.formato_fuente).filter(Publicacion.formato_fuente != None).distinct().all()]))

    return jsonify({
        'idiomas': idiomas,
        'tipos_autor': tipos_autor,
        'publicaciones': publicaciones,
        'ciudades': ciudades,
        'estadisticas': estadisticas,
        'temas': temas,
        'licencias': licencias,
        'formatos': formatos,
        'paises': [] 
    })



# --- API: valores únicos filtrados para selects dependientes (AJAX avanzado) ---
@noticias_bp.route('/api/valores_filtrados', methods=['GET'])
@login_required
def api_valores_filtrados():
    """Devuelve los valores únicos posibles para cada filtro según los filtros actuales"""
    proyecto = get_proyecto_activo()
    columna_especifica = request.args.get("columna")

    if not proyecto:
        if columna_especifica:
             return jsonify([])
        return jsonify({
            "autores": [], "fechas": [], "numeros": [], "publicaciones": [], "ciudades": [], "paises": [], "temas": []
        })

    # Mapear parámetros del frontend a campos del modelo
    filtros = {}
    # Autor puede venir como 'autor' o 'nombre_autor'
    autor = request.args.get('autor', '').strip() or request.args.get('nombre_autor', '').strip()
    if autor:
        filtros['autor'] = autor
    
    for k in ["fecha_original", "publicacion", "ciudad", "pais_publicacion", "temas"]:
        v = request.args.get(k, "").strip()
        if v:
            filtros[k] = v

    from sqlalchemy import func, or_
    
    def normalizar_valor(valor):
        return (valor or '').strip().lower()

    def valores_filtrados(col, filtros_activos):
        q = Prensa.query.filter_by(proyecto_id=proyecto.id)
        
        for k, v in filtros_activos.items():
            if k == col.key:
                continue  # No filtrar por la misma columna
            
            if k == 'autor':
                # Usar hybrid_property Prensa.autor para búsqueda exacta normalizada
                q = q.filter(func.lower(func.trim(Prensa.autor)) == normalizar_valor(v))
            elif k in ["publicacion", "ciudad", "pais_publicacion", "fecha_original"]:
                q = q.filter(func.lower(func.trim(getattr(Prensa, k))) == normalizar_valor(v))
            elif k == 'temas':
                q = q.filter(getattr(Prensa, k).ilike(f"%{v}%"))
                    
        valores = [getattr(r, col.key) for r in q.all() if getattr(r, col.key)]
        valores_norm = {}
        for val in valores:
            if not val: continue
            # Formatear fechas
            if col.key == 'fecha_original' and isinstance(val, str) and len(val) == 10 and '-' in val:
                v_item = f'{val[8:10]}/{val[5:7]}/{val[0:4]}'
            else:
                v_item = val
            # Split por comas para temas
            vals_procesar = [v_item]
            if col.key == 'temas':
                vals_procesar = [t.strip() for t in v_item.split(',')]
            for v_item2 in vals_procesar:
                clave = normalizar_valor(v_item2)
                if not clave: continue
                if clave not in valores_norm:
                    valores_norm[clave] = v_item2
                elif v_item2[0].isupper() and (not valores_norm[clave] or not valores_norm[clave][0].isupper()):
                    valores_norm[clave] = v_item2
                    
        if col.key == 'fecha_original':
            from datetime import datetime
            def date_sort_key(x):
                if not isinstance(x, str): return x.lower() if isinstance(x, str) else str(x)
                f = x.strip()
                try:
                    if '-' in f:
                        parts = f.split('-')
                        if len(parts) == 3: return datetime(int(parts[0]), int(parts[1]), int(parts[2])).strftime('%Y-%m-%d')
                    if '/' in f:
                        parts = f.split('/')
                        if len(parts) == 3: return datetime(int(parts[2]), int(parts[1]), int(parts[0])).strftime('%Y-%m-%d')
                except Exception:
                    pass
                return f.lower()
            return sorted(valores_norm.values(), key=date_sort_key, reverse=True)
            
        return sorted(valores_norm.values(), key=lambda x: x.lower())

    # Función especial para autores (combina nombre y apellido)
    def valores_autores(filtros_activos):
        q = Prensa.query.filter_by(proyecto_id=proyecto.id)
        
        for k, v in filtros_activos.items():
            if k == 'autor':
                continue
            if k in ["publicacion", "ciudad", "pais_publicacion", "fecha_original"]:
                q = q.filter(func.lower(func.trim(getattr(Prensa, k))) == normalizar_valor(v))
            elif k == 'temas':
                q = q.filter(getattr(Prensa, k).ilike(f"%{v}%"))
        
        autores_set = set()
        for r in q.all():
            if r.autor:
                autores_set.add(r.autor)
        
        return sorted(list(autores_set), key=lambda x: x.lower())

    if columna_especifica:
        mapa_col = {
            "nombre_autor": Prensa.nombre_autor,
            "apellido_autor": Prensa.apellido_autor,
            "fecha_original": Prensa.fecha_original,
            "numero": Prensa.numero,
            "publicacion": Prensa.publicacion,
            "ciudad": Prensa.ciudad,
            "pais_publicacion": Prensa.pais_publicacion,
            "temas": Prensa.temas
        }
        if columna_especifica == "autor":
            return jsonify(valores_autores(filtros))
        elif columna_especifica in mapa_col:
            return jsonify(valores_filtrados(mapa_col[columna_especifica], filtros))
        else:
            return jsonify([])

    return jsonify({
        "autores": valores_autores(filtros),
        "fechas": valores_filtrados(Prensa.fecha_original, filtros),
        "numeros": valores_filtrados(Prensa.numero, filtros),
        "publicaciones": valores_filtrados(Prensa.publicacion, filtros),
        "ciudades": valores_filtrados(Prensa.ciudad, filtros),
        "paises": valores_filtrados(Prensa.pais_publicacion, filtros),
        "temas": valores_filtrados(Prensa.temas, filtros),
    })


@noticias_bp.route('/api/map-data', methods=['GET'])
@login_required
def api_map_data():
    """
    Devuelve datos para el mapa: lista de ciudades con lat/lon y conteo de noticias.
    """
    proyecto = get_proyecto_activo()
    if not proyecto:
        return jsonify([])

    from models import Ciudad, get_or_create_city_with_coords
    from utils import geocode_city # Importar funcion geocoding

    # Recuperar filtros
    filtros = {
        k: request.args.getlist(k) if len(request.args.getlist(k)) > 1 else request.args.get(k)
        for k in request.args.keys()
        if k not in ['_t']
    }
    print("[MAPA] Filtros recibidos:", filtros)
    
    query = Prensa.query.filter_by(proyecto_id=proyecto.id, incluido=True)

    if 'publicacion' in filtros:
        val = filtros['publicacion']
        print(f"[MAPA] Filtro publicación: {val}")
        if isinstance(val, list):
            query = query.filter(Prensa.publicacion.in_(val))
        elif val and val != "todas":
            query = query.filter(Prensa.publicacion == val)
        print(f"[MAPA] Resultados tras filtro publicación: {query.count()}")

    if 'ciudad' in filtros:
        val = filtros['ciudad']
        print(f"[MAPA] Filtro ciudad: {val}")
        if isinstance(val, list):
            query = query.filter(Prensa.ciudad.in_(val))
        elif val and val != "todas":
             query = query.filter(Prensa.ciudad == val)
        print(f"[MAPA] Resultados tras filtro ciudad: {query.count()}")
             
    noticias = query.all()
    ciudades_data = {} 
    
    for noticia in noticias:
        c_nombre = noticia.ciudad
        if not c_nombre: continue
        c_norm = c_nombre.strip()
        if not c_norm: continue
        
        if c_norm not in ciudades_data:
            city_obj = get_or_create_city_with_coords(db.session, c_norm)
            
            # Intento de geocodificación si faltan coordenadas o provincia
            # (Re-geocodificamos si falta provincia para rellenar el dato nuevo)
            if city_obj and (city_obj.lat is None or city_obj.lon is None or city_obj.provincia is None):
                # Solo loguear si es un caso "nuevo" o de backfill explícito para no spammeando
                print(f"[NOMINATIM] Buscando datos para: {c_norm}")
                lat, lon, addr, status, provincia = geocode_city(c_norm, country_name=noticia.pais_publicacion)
                
                # Si encontramos datos, actualizamos
                changed = False
                if lat and lon:
                    if city_obj.lat != lat or city_obj.lon != lon:
                        city_obj.lat = lat
                        city_obj.lon = lon
                        changed = True
                    
                    if provincia and city_obj.provincia != provincia:
                        city_obj.provincia = provincia
                        changed = True
                        
                    if changed:
                        db.session.commit()
                        print(f"  -> Actualizado: {lat}, {lon} ({provincia})")
                else:
                    print(f"  -> No encontrado: {status}")

            if not city_obj or not city_obj.lat or not city_obj.lon:
                ciudades_data[c_norm] = None 
                continue
                
            ciudades_data[c_norm] = {
                "name": city_obj.name,
                "lat": city_obj.lat,
                "lon": city_obj.lon,
                "count": 0,
                "publicaciones": {},
                "radius": 6
            }
        
        if ciudades_data[c_norm] is None:
            continue
            
        data = ciudades_data[c_norm]
        data["count"] += 1
        
        pub = noticia.publicacion or "Desconocido"
        data["publicaciones"][pub] = data["publicaciones"].get(pub, 0) + 1
        
    result = []
    import math
    for c_norm, data in ciudades_data.items():
        if data:
            data["radius"] = min(30, 4 + math.log(data["count"] + 1) * 3)
            result.append(data)
            
    return jsonify(result)


@noticias_bp.route('/api/map-distribution', methods=['GET'])
@login_required
def api_map_distribution():
    """
    Devuelve datos agrupados por provincia para el mapa de coropletas.
    AHORA basado en (Prensa.publicacion -> Publicacion.provincia).
    Retorna: { "Madrid": 150, "Barcelona": 80, ... }
    """
    proyecto = get_proyecto_activo()
    if not proyecto:
        return jsonify({})

    from models import Publicacion
    from sqlalchemy import func

    # Join Prensa -> Publicacion
    # Contamos noticias agrupadas por Publicacion.provincia
    query = db.session.query(
        Publicacion.provincia,
        func.count(Prensa.id)
    ).join(Publicacion, Prensa.id_publicacion == Publicacion.id_publicacion)\
     .filter(Prensa.proyecto_id == proyecto.id, Prensa.incluido == True)\
     .filter(Publicacion.provincia.isnot(None))\
     .group_by(Publicacion.provincia)

    # REPLICAR FILTROS SIMPLES
    
    # Soporte para múltiples valores (listas)
    publicaciones = request.args.getlist('publicacion')
    ciudades = request.args.getlist('ciudad')
    
    if publicaciones and 'todos' not in [p.lower() for p in publicaciones]:
         query = query.filter(Prensa.publicacion.in_(publicaciones))
         
    if ciudades and 'todos' not in [c.lower() for c in ciudades]:
         # Aquí filtramos por el nombre de ciudad en la noticia
         query = query.filter(Prensa.ciudad.in_(ciudades))

    filtros = {k: request.args.get(k) for k in request.args.keys()}
    
    if filtros.get('autor'):
         query = query.filter(Prensa.autor.ilike(f"%{filtros['autor']}%"))
    if filtros.get('temas'):
         query = query.filter(Prensa.temas.ilike(f"%{filtros['temas']}%"))

    data = query.all()
    
    # Procesar resultados a diccionario simple
    result = {}
    for prov, count in data:
        if prov:
            # Normalizar nombre para coincidir con GeoJSON
            nombre = prov.strip()
            # Agregar al acumulado (por si varias ciudades tienen misma provincia con variaciones de nombre minúsculas)
            # Aunque group_by Ciudad.provincia debería ser único si la DB está bien.
            if nombre in result:
                result[nombre] += count
            else:
                result[nombre] = count
            
    return jsonify(result)



# --- Filtrar noticias de prensa (AJAX, devuelve HTML de la tabla) ---
@noticias_bp.route('/filtrar', methods=['GET'])
@login_required
def filtrar():
    # Si la petición no es AJAX (por ejemplo, al volver atrás en el navegador), 
    # redirigimos a la vista completa de la lista con los mismos parámetros.
    if request.headers.get('X-Requested-With') != 'XMLHttpRequest' and request.args.get('ajax') != '1':
        return redirect(url_for('noticias.listar', **request.args))

    print(f"[DEBUG] /filtrar args: {request.args}")
    """Filtrar noticias de prensa y devolver tabla (HTML) y filtros (JSON)"""
    from flask import jsonify
    proyecto = get_proyecto_activo()
    if not proyecto:
        return jsonify({
            "html": "<div class='alert alert-warning'>No hay proyecto activo.</div>",
            "autores": [], "fechas": [], "numeros": [], "publicaciones": [], "ciudades": [], "temas": []
        })
    filtros = {
        k: request.args.get(k, "").strip()
        for k in [
            "autor",
            "fecha_original",
            "numero",
            "publicacion",
            "ciudad",
            "pais_publicacion",
            "temas",
            "busqueda",
            "fecha_desde",
            "fecha_hasta",
            "tipo_recurso",
            "tipo_publicacion",
            "periodicidad",
        ]
    }
    filtros["incluido"] = request.args.get("incluido", "todos")

    # Forzar fechas disponibles aunque no haya filtro activo
    fechas_disponibles = valores_unicos_prensa(Prensa.fecha_original, proyecto.id)
    if not fechas_disponibles:
        fechas_disponibles = ["(Sin fechas)"]
    page = int(request.args.get("page", 1))
    query = Prensa.query.filter_by(proyecto_id=proyecto.id)
    import unicodedata
    from sqlalchemy import or_
    def normaliza(texto):
        if not texto: return ""
        return unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('ASCII').lower().strip()
    for k, v in filtros.items():
        v = v.strip() if isinstance(v, str) else v
        if k not in ["busqueda", "incluido"] and v:
            if k == "publicacion":
                query = query.filter(getattr(Prensa, k) == v)
            elif k == "pais_publicacion":
                query = query.filter(Prensa.pais_publicacion == v)
            elif k == "ciudad":
                query = query.filter(Prensa.ciudad == v)
            elif k == "autor":
                # Filtro robusto por autores (tabla autores_prensa o legacy)
                query = query.outerjoin(AutorPrensa).filter(
                    or_(
                        Prensa.autor.ilike(f"%{v}%"),
                        AutorPrensa.apellido.ilike(f"%{v}%"),
                        AutorPrensa.nombre.ilike(f"%{v}%"),
                        db.func.concat(AutorPrensa.apellido, ", ", AutorPrensa.nombre).ilike(f"%{v}%"),
                        func.public.unaccent(Prensa.autor).ilike(func.public.unaccent(f"%{v}%"))
                    )
                )
            elif k == "fecha_original":
                # Generate all date format variants (same logic as /listar)
                formatos = {v}
                dt = None
                try:
                    if "-" in v:
                        parts = v.split('-')
                        if len(parts) == 3:
                            dt = datetime(int(parts[0]), int(parts[1]), int(parts[2]))
                    elif "/" in v:
                        parts = v.split('/')
                        if len(parts) == 3:
                            # Assume DD/MM/YYYY
                            dt = datetime(int(parts[2]), int(parts[1]), int(parts[0]))
                    
                    if dt:
                        y, m, d = dt.year, dt.month, dt.day
                        formatos.add(f"{y}-{m:02d}-{d:02d}")  # 1882-05-13
                        formatos.add(f"{y}-{m}-{d}")          # 1882-5-13
                        formatos.add(f"{d:02d}/{m:02d}/{y}")  # 13/05/1882
                        formatos.add(f"{d}/{m}/{y}")          # 13/5/1882
                        formatos.add(f"{d:02d}/{m}/{y}")      # 13/5/1882
                        formatos.add(f"{d}/{m:02d}/{y}")      # 13/05/1882
                except Exception as e:
                    print(f"Error parsing date {v}: {e}")
                
                # Apply filter with all variants
                col_limpia = db.func.lower(db.func.trim(Prensa.fecha_original))
                condiciones = [col_limpia == f.strip().lower() for f in formatos]
                condiciones.extend([Prensa.fecha_original.ilike(f"%{f}%") for f in formatos])
                query = query.filter(or_(*condiciones))
            elif k == "palabras_clave":
                v_norm = normaliza(v)
                if v_norm in [None, ""]:
                    continue
                palabras = [normaliza(p) for p in v.replace(',', ' ').split() if p.strip()]
                condiciones = []
                for palabra in palabras:
                    condiciones.append(func.lower(func.public.unaccent(Prensa.palabras_clave)).ilike(f"%{palabra}%"))
                if condiciones:
                    query = query.filter(or_(*condiciones))
            elif k == "fecha_desde":
                sql_date = "CASE WHEN prensa.fecha_original ~ '^[0-3]?[0-9]/[0-1]?[0-9]/[0-9]{2,4}$' THEN to_date(prensa.fecha_original, 'DD/MM/YYYY') WHEN prensa.fecha_original ~ '^[0-9]{4}-[0-1]?[0-9]-[0-3]?[0-9]$' THEN to_date(prensa.fecha_original, 'YYYY-MM-DD') ELSE NULL END"
                query = query.filter(text(f"{sql_date} >= :d").params(d=v))
            elif k == "fecha_hasta":
                sql_date = "CASE WHEN prensa.fecha_original ~ '^[0-3]?[0-9]/[0-1]?[0-9]/[0-9]{2,4}$' THEN to_date(prensa.fecha_original, 'DD/MM/YYYY') WHEN prensa.fecha_original ~ '^[0-9]{4}-[0-1]?[0-9]-[0-3]?[0-9]$' THEN to_date(prensa.fecha_original, 'YYYY-MM-DD') ELSE NULL END"
                query = query.filter(text(f"{sql_date} <= :h").params(h=v))
            else:
                query = query.filter(getattr(Prensa, k).ilike(f"%{v}%"))
    if filtros["busqueda"]:
        for p in filtros["busqueda"].split():
            term = f"%{p}%"
            query = query.filter(
                or_(
                    cast(Prensa.titulo, String).ilike(term),
                    cast(Prensa.contenido, String).ilike(term),
                    cast(Prensa.texto_original, String).ilike(term),
                    cast(Prensa.autor, String).ilike(term),
                    cast(Prensa.publicacion, String).ilike(term),
                    cast(Prensa.resumen, String).ilike(term),
                    cast(Prensa.palabras_clave, String).ilike(term),
                    cast(Prensa.temas, String).ilike(term),
                    cast(Prensa.notas, String).ilike(term),
                    cast(Prensa.fuente, String).ilike(term),
                )
            )
    if filtros["incluido"] == "si":
        query = query.filter(Prensa.incluido.is_(True))
    elif filtros["incluido"] == "no":
        query = query.filter(Prensa.incluido.is_(False))
    # Ordenar por fecha de menos reciente a más reciente (ascendente)
    query = ordenar_por_fecha_prensa(query, descendente=False)
    # Evitar duplicados por joins agrupando por el ID primario
    query = query.group_by(Prensa.id)
    total = query.count()
    hay_filtros = any(filtros.get(k) for k in filtros if k != 'incluido') or filtros.get('incluido') != 'todos'
    noticias_por_pagina_raw = request.args.get("noticias_por_pagina", "50").strip()
    try:
        noticias_por_pagina = int(noticias_por_pagina_raw) if noticias_por_pagina_raw else 50
    except (ValueError, TypeError):
        noticias_por_pagina = 50
    por_pagina = noticias_por_pagina
    
    # Si hay filtros aplicados, el sistema original mostraba todo (total_paginas=1)
    # pero vamos a permitir que noticias_por_pagina funcione siempre si se desea.
    # No obstante, el código original en la línea 1484 detecta hay_filtros
    # y las líneas 1487-1488 aplican paginación igualmente.
    
    registros_raw = query.offset((page - 1) * por_pagina).limit(por_pagina).all()
    total_paginas = (total // por_pagina) + (1 if total % por_pagina else 0)
    inicio = max(1, page - 2)
    fin = min(total_paginas, page + 2)
    registros = []
    print("[DEBUG] ORDEN FILTRADO:")
    for r in registros_raw:
        try:
            r.id = int(r.id)
            print(f"Fecha: {getattr(r, 'fecha_original', None)}, Publicación: {getattr(r, 'publicacion', None)}, Título: {getattr(r, 'titulo', None)}")
            registros.append(r)
        except (ValueError, TypeError):
            continue
    
    # Calcular valores únicos SOBRE LOS FILTROS ACTUALES (sin ORDER BY)
    # Crear query base solo con filtros, sin ordenamiento
    query_base = Prensa.query.filter_by(proyecto_id=proyecto.id)
    for k, v in filtros.items():
        v = v.strip() if isinstance(v, str) else v
        if k not in ["busqueda", "incluido"] and v:
            if k == "publicacion":
                query_base = query_base.filter(Prensa.publicacion == v)
            elif k == "pais_publicacion":
                query_base = query_base.filter(Prensa.pais_publicacion == v)
            elif k == "ciudad":
                query_base = query_base.filter(Prensa.ciudad == v)
            elif k == "autor":
                query_base = query_base.filter(Prensa.autor.ilike(f"%{v}%"))
            elif k == "fecha_original":
                query_base = query_base.filter(Prensa.fecha_original == v)
            elif k == "temas":
                query_base = query_base.filter(Prensa.temas.ilike(f"%{v}%"))
    if filtros["incluido"] == "si":
        query_base = query_base.filter(Prensa.incluido.is_(True))
    elif filtros["incluido"] == "no":
        query_base = query_base.filter(Prensa.incluido.is_(False))
    
    def valores_filtrados(columna):
        """Obtiene valores únicos de una columna en la query filtrada (sin ORDER BY)"""
        valores = set()
        # Usamos distinct(columna) para obtener valores únicos reales
        for r in query_base.with_entities(columna).distinct().all():
            val = r[0]
            if val and str(val).strip():
                valores.add(str(val).strip())
        return sorted(list(valores))
    
    # Valores dinámicos basados en los filtros actuales
    # Get authors in "Apellido, Nombre" format from filtered results
    autores_set = {r[0] for r in query_base.with_entities(Prensa.autor).distinct().all() if r[0]}
    autores_filtrados = sorted(list(autores_set), key=lambda x: x.lower())
    publicaciones_filtradas = valores_filtrados(Prensa.publicacion)
    ciudades_filtradas = valores_filtrados(Prensa.ciudad)
    paises_filtrados = valores_filtrados(Prensa.pais_publicacion)
    fechas_filtradas = valores_filtrados(Prensa.fecha_original)
    temas_filtrados = valores_filtrados(Prensa.temas)
    
    # Renderizar la tabla como HTML
    html = render_template(
        '_tabla.html',
        registros=registros,
        total=total,
        page=page,
        total_paginas=total_paginas,
        inicio=inicio,
        fin=fin,
        autores=autores_filtrados,
        fechas=fechas_filtradas if fechas_filtradas else ["(Sin fechas)"],
        numeros=valores_unicos_prensa(Prensa.numero, proyecto.id),
        publicaciones=publicaciones_filtradas,
        ciudades=ciudades_filtradas,
        paises=paises_filtrados,
        temas_list=temas_filtrados,
        noticias_por_pagina=noticias_por_pagina
    )
    # Devolver también los valores únicos de los filtros (dinámicos)
    return jsonify({
        "html": html,
        "autores": autores_filtrados,
        "fechas": fechas_filtradas if fechas_filtradas else ["(Sin fechas)"],
        "numeros": valores_unicos_prensa(Prensa.numero, proyecto.id),
        "publicaciones": publicaciones_filtradas,
        "ciudades": ciudades_filtradas,
        "paises": paises_filtrados,
        "temas": temas_filtrados
    })

# --- Actualizar nota de noticia de prensa ---
@noticias_bp.route("/actualizar_nota/<int:id>", methods=["POST"])
@login_required
def actualizar_nota(id):
    """Actualizar nota de una noticia de prensa vía AJAX"""
    data = request.get_json(silent=True) or {}
    nueva_nota = (data.get("nota") or "").strip()
    registro = db.session.get(Prensa, id)
    if not registro:
        return jsonify({"success": False, "message": "Registro no encontrado"}), 404

    registro.notas = nueva_nota
    db.session.commit()
    return jsonify({"success": True})

# --- VISTA STANDALONE: GESTOR DE UBICACIONES ---
@noticias_bp.route('/cartografia/gestor')
@login_required
def gestor_ubicaciones_view():
    """Vista dedicada para la gestión del corpus de ubicaciones."""
    proyecto = get_proyecto_activo()
    return render_template('gestor_ubicaciones.html', proyecto_id=proyecto.id if proyecto else None, proyecto_activo=proyecto)

# --- Listar noticias de prensa ---
@noticias_bp.route('/listar', methods=['GET'])
@login_required
def listar():
    """Listar noticias de prensa con filtros"""
    proyecto = get_proyecto_activo()
    if not proyecto:
        if Proyecto.query.count() == 0:
            flash("👋 Bienvenido! Crea tu primer proyecto para empezar.", "info")
            return redirect(url_for("proyectos.crear"))
        return redirect(url_for("proyectos.listar"))

    filtros = {
        k: request.args.get(k, "").strip()
        for k in [
            "autor",
            "fecha_original",
            "numero",
            "publicacion",
            "ciudad",
            "pais_publicacion",
            "temas",
            "busqueda",
            "palabras_clave",
            "lugar",
            "fecha_desde",
            "fecha_hasta",
            "tipo_recurso",
            "tipo_publicacion",
            "periodicidad",
        ]
    }
    # Alias: q también sirve como búsqueda
    if not filtros.get("busqueda") and request.args.get("q"):
        filtros["busqueda"] = request.args.get("q", "").strip()
    filtros["incluido"] = request.args.get("incluido", "todos")
    page = int(request.args.get("page", 1))

    query = Prensa.query.filter_by(proyecto_id=proyecto.id)
    
    # Filtrar noticias de publicaciones marcadas como no visibles
    query = query.outerjoin(Publicacion, Prensa.id_publicacion == Publicacion.id_publicacion).filter(
        or_(
            Publicacion.visible == True,
            Publicacion.id_publicacion == None
        )
    )

    
    # --- DEBUG LOGGING ---
    try:
        with open("/opt/hesiox/logs/debug_filter.log", "a") as f:
            f.write(f"\n\n--- REQUEST {datetime.now()} ---\n")
            f.write(f"ARGS: {dict(request.args)}\n")
            f.write(f"FILTROS: {filtros}\n")
    except Exception as e:
        print(f"Error writing debug log: {e}")
    # ---------------------

    print("[DEBUG] Filtros aplicados:", filtros)
    import sys
    sys.stdout.flush()
    # from sqlalchemy import or_

    for k, v in filtros.items():
        v = v.strip() if isinstance(v, str) else v
        if k not in ["busqueda", "incluido"] and v:
            if k == "lugar":
                # Filtro por LugarNoticia (mapa corpus)
                solo_vinculadas = request.args.get('solo_vinculadas', '').lower() == 'true'
                print(f"[DEBUG LUGAR] Filtrando por lugar={v}, solo_vinculadas={solo_vinculadas}")
                import sys
                sys.stdout.flush()
                
                if solo_vinculadas:
                    # Filtrar solo menciones vinculadas: donde (frecuencia - frecuencia_desvinculada) > 0
                    # Esto excluye registros donde TODAS las menciones están desvinculadas del proyecto
                    query = query.join(LugarNoticia).filter(
                        LugarNoticia.nombre == v,
                        LugarNoticia.borrado == False,
                        (LugarNoticia.frecuencia - db.func.coalesce(LugarNoticia.frecuencia_desvinculada, 0)) > 0
                    )
                    print(f"[DEBUG LUGAR] Aplicado filtro de solo_vinculadas")
                    sys.stdout.flush()
                else:
                    # Modo normal: todas las menciones (vinculadas y desvinculadas)
                    query = query.join(LugarNoticia).filter(
                        LugarNoticia.nombre == v,
                        LugarNoticia.borrado == False
                    )
                    print(f"[DEBUG LUGAR] Modo normal (todas las menciones)")
                    sys.stdout.flush()
            elif k in ["publicacion", "pais_publicacion", "ciudad"]:
                query = query.filter(getattr(Prensa, k) == v)
            elif k == "palabras_clave":
                # Filtro flexible: busca cada palabra por separado (coma o espacio) y muestra si alguna coincide (OR)
                import unicodedata
                def normaliza(texto):
                    if not texto: return ""
                    return unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('ASCII').lower().strip()
                v_norm = normaliza(v)
                if v_norm in [None, ""]:
                    continue
                # Separar por coma y espacio
                palabras = [normaliza(p) for p in v.replace(',', ' ').split() if p.strip()]
                condiciones = []
                for palabra in palabras:
                    condiciones.append(func.lower(func.public.unaccent(Prensa.palabras_clave)).ilike(f"%{palabra}%"))
                if condiciones:
                    query = query.filter(or_(*condiciones))
            elif k == "fecha_original":
                # Buscar en múltiples formatos posibles (YYYY-MM-DD, DD/MM/YYYY, D/M/YYYY)
                formatos = {v}  # Usar set para evitar duplicados
                try:
                    dt = None
                    if "-" in v:
                        dt = datetime.strptime(v, "%Y-%m-%d")
                    elif "/" in v:
                        dt = datetime.strptime(v, "%d/%m/%Y")
                    
                    if dt:
                        # Generar TODAS las variantes posibles de formato
                        y, m, d = dt.year, dt.month, dt.day
                        formatos.add(f"{y}-{m:02d}-{d:02d}")  # 2026-02-02
                        formatos.add(f"{y}-{m}-{d}")          # 2026-2-2
                        formatos.add(f"{d:02d}/{m:02d}/{y}")  # 02/02/2026
                        formatos.add(f"{d}/{m}/{y}")          # 2/2/2026
                        formatos.add(f"{d:02d}/{m}/{y}")      # 02/2/2026
                        formatos.add(f"{d}/{m:02d}/{y}")      # 2/02/2026
                except Exception:
                    pass
                
                # Usar trim para ignorar espacios invisibles y ilike para pattern matching
                # query = query.filter(or_(*[db.func.trim(Prensa.fecha_original).ilike(f) for f in formatos]))
                # Nota: SQLite/Postgres trim funciona, pero ilike con % es mejor para variaciones
                
                # Vamos a probar TRIM() == F (case insensitive) usando func.lower
                col_limpia = db.func.lower(db.func.trim(Prensa.fecha_original))
                condiciones = [col_limpia == f.strip().lower() for f in formatos]
                
                # Fallback ilike por si hay caracteres raros no-espacio
                condiciones.extend([Prensa.fecha_original.ilike(f"%{f}%") for f in formatos])

                query = query.filter(or_(*condiciones))
            elif k == "fecha_desde":
                sql_date = "CASE WHEN prensa.fecha_original ~ '^[0-3]?[0-9]/[0-1]?[0-9]/[0-9]{2,4}$' THEN to_date(prensa.fecha_original, 'DD/MM/YYYY') WHEN prensa.fecha_original ~ '^[0-9]{4}-[0-1]?[0-9]-[0-3]?[0-9]$' THEN to_date(prensa.fecha_original, 'YYYY-MM-DD') ELSE NULL END"
                query = query.filter(text(f"{sql_date} >= :d").params(d=v))
            elif k == "fecha_hasta":
                sql_date = "CASE WHEN prensa.fecha_original ~ '^[0-3]?[0-9]/[0-1]?[0-9]/[0-9]{2,4}$' THEN to_date(prensa.fecha_original, 'DD/MM/YYYY') WHEN prensa.fecha_original ~ '^[0-9]{4}-[0-1]?[0-9]-[0-3]?[0-9]$' THEN to_date(prensa.fecha_original, 'YYYY-MM-DD') ELSE NULL END"
                query = query.filter(text(f"{sql_date} <= :h").params(h=v))
            elif k == "autor":
                # Filtro robusto por autores (tabla autores_prensa o legacy)
                query = query.outerjoin(AutorPrensa).filter(
                    or_(
                        Prensa.autor.ilike(f"%{v}%"),
                        AutorPrensa.apellido.ilike(f"%{v}%"),
                        AutorPrensa.nombre.ilike(f"%{v}%"),
                        db.func.concat(AutorPrensa.apellido, ", ", AutorPrensa.nombre).ilike(f"%{v}%"),
                        func.public.unaccent(Prensa.autor).ilike(func.public.unaccent(f"%{v}%"))
                    )
                )
            else:
                query = query.filter(getattr(Prensa, k).ilike(f"%{v}%"))
    print("[DEBUG] Query SQL:", str(query.statement.compile(compile_kwargs={"literal_binds": True})))
    sys.stdout.flush()
    if filtros["busqueda"]:
        # Join con AutorPrensa para búsqueda global
        query = query.outerjoin(AutorPrensa)
        for p in filtros["busqueda"].split():
            term = f"%{p}%"
            query = query.filter(
                or_(
                    cast(Prensa.titulo, String).ilike(term),
                    cast(Prensa.contenido, String).ilike(term),
                    cast(Prensa.texto_original, String).ilike(term),
                    cast(Prensa.autor, String).ilike(term),
                    cast(Prensa.publicacion, String).ilike(term),
                    cast(Prensa.resumen, String).ilike(term),
                    cast(Prensa.palabras_clave, String).ilike(term),
                    cast(Prensa.temas, String).ilike(term),
                    cast(Prensa.notas, String).ilike(term),
                    cast(Prensa.fuente, String).ilike(term),
                    AutorPrensa.nombre.ilike(term),
                    AutorPrensa.apellido.ilike(term)
                )
            )
    if filtros["incluido"] == "si":
        query = query.filter(Prensa.incluido.is_(True))
    elif filtros["incluido"] == "no":
        query = query.filter(Prensa.incluido.is_(False))
    # Forzar ordenamiento por fecha y publicación
    query = ordenar_por_fecha_prensa(query, descendente=False)
    # Evitar duplicados por joins agrupando por el ID primario
    query = query.group_by(Prensa.id)
    total = query.count()
    hay_filtros = any(filtros.get(k) for k in filtros if k != 'incluido') or filtros.get('incluido') != 'todos'
    noticias_por_pagina_raw = request.args.get("noticias_por_pagina", "50").strip()
    try:
        noticias_por_pagina = int(noticias_por_pagina_raw) if noticias_por_pagina_raw else 50
    except (ValueError, TypeError):
        noticias_por_pagina = 50
    por_pagina = noticias_por_pagina
    registros_raw = query.offset((page - 1) * por_pagina).limit(por_pagina).all()
    total_paginas = (total // por_pagina) + (1 if total % por_pagina else 0)
    registros = []
    for r in registros_raw:
        try:
            r.id = int(r.id)
            registros.append(r)
        except (ValueError, TypeError):
            continue
    inicio = max(1, page - 2)
    fin = min(total_paginas, page + 2)
    fechas_raw = valores_unicos_prensa(Prensa.fecha_original, proyecto.id)
    def fecha_to_dt(f):
        if not isinstance(f, str): return None
        f = f.strip()
        # Intentar parseos comunes
        try:
             # ISO YYYY-MM-DD
            if '-' in f:
                parts = f.split('-')
                if len(parts) == 3:
                     return datetime(int(parts[0]), int(parts[1]), int(parts[2]))
            # Standard DD/MM/YYYY
            if '/' in f:
                parts = f.split('/')
                if len(parts) == 3:
                     # Asumir DD/MM/YYYY
                     return datetime(int(parts[2]), int(parts[1]), int(parts[0]))
        except Exception:
            pass
        return None

    # Ordenar fechas (descendente) para dropdown
    fechas_unicas = sorted(list(set([f for f in fechas_raw if fecha_to_dt(f)])), key=fecha_to_dt, reverse=True)
    
    # Formatear estéticamente para el usuario (DD/MM/YYYY)
    fechas = []
    for f in fechas_unicas:
        dt = fecha_to_dt(f)
        if dt:
             fechas.append(dt.strftime("%d/%m/%Y"))
    
    # Eliminar duplicados visuales conservando orden
    fechas = list(dict.fromkeys(fechas))
    
    # Get authors from both legacy and new tables in "Apellido, Nombre" format
    autores_set = {r[0] for r in db.session.query(Prensa.autor).filter(Prensa.proyecto_id == proyecto.id).distinct().all() if r[0]}
    
    # Usar func.concat para evitar resultados NULL si falta nombre o apellido
    autores_nuevos = db.session.query(
        db.func.concat(
            db.func.coalesce(AutorPrensa.apellido, ""), 
            ", ", 
            db.func.coalesce(AutorPrensa.nombre, "")
        )
    ).join(Prensa).filter(Prensa.proyecto_id == proyecto.id).distinct().all()
    
    for r in autores_nuevos:
        if r[0] and r[0].strip() != ",":
            autores_set.add(r[0].strip())
    
    autores = sorted(list(autores_set), key=lambda x: x.lower())
    
    resp = render_template(
        "list.html",
        registros=registros,
        proyecto=proyecto,
        total=total,
        page=page,
        total_paginas=total_paginas,
        inicio=inicio,
        fin=fin,
        autores=autores,
        fechas=fechas,
        numeros=valores_unicos_prensa(Prensa.numero, proyecto.id),
        publicaciones=valores_unicos_prensa(Prensa.publicacion, proyecto.id),
        fuentes=valores_unicos_prensa(Prensa.fuente, proyecto.id),
        ciudades=valores_unicos_prensa(Prensa.ciudad, proyecto.id),
        paises=valores_unicos_prensa(Prensa.pais_publicacion, proyecto.id),
        temas_list=sorted([t.nombre for t in Tema.query.filter_by(proyecto_id=proyecto.id).all()], key=lambda x: x.lower()),
        anios=sorted({
            d.year for d in 
            valores_unicos_prensa(Prensa.fecha_original, proyecto.id) 
            if isinstance(d, datetime) and d != datetime.max
        }, reverse=True),
        licencias_list=sorted(
            {
                *(
                    p.licencia
                    for p in Publicacion.query.filter(Publicacion.licencia.isnot(None))
                ),
                *(r.licencia for r in Prensa.query.filter(Prensa.licencia.isnot(None))),
            }
            | {"CC BY 4.0"}
        ),
        filtros=filtros,
        **filtros,
        proyecto_id=proyecto.id,
        noticias_por_pagina=noticias_por_pagina,
        lote_opciones_genero=MetadataOption.query.filter_by(categoria='tipo_recurso').order_by(MetadataOption.orden, MetadataOption.etiqueta).all(),
        lote_opciones_subgenero=MetadataOption.query.filter_by(categoria='tipo_publicacion').order_by(MetadataOption.orden, MetadataOption.etiqueta).all(),
        lote_opciones_frecuencia=MetadataOption.query.filter_by(categoria='frecuencia').order_by(MetadataOption.orden, MetadataOption.etiqueta).all()
    )
    return resp





# --- Crear noticia de prensa ---
def save_base64_image(b64_string, noticia_id):
    """Guarda una imagen en Base64 proveniente del OCR como un archivo físico y devuelve el nombre del archivo."""
    if not b64_string:
        return None
    try:
        import base64
        import uuid
        
        # Eliminar cabecera si existe (data:image/png;base64,...)
        if ',' in b64_string:
            header, data = b64_string.split(',', 1)
        else:
            data = b64_string
            
        img_data = base64.b64decode(data)
        # Generar nombre único con ID de noticia para rastreo
        filename = f"ocr_vinculado_{noticia_id}_{uuid.uuid4().hex[:6]}.png"
        upload_folder = current_app.config.get("UPLOAD_FOLDER", "static/uploads")
        
        # Asegurar que el directorio existe
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder, exist_ok=True)
            
        ruta = os.path.join(upload_folder, filename)
        
        with open(ruta, 'wb') as f:
            f.write(img_data)
            
        print(f"[DEBUG] Imagen OCR guardada correctamente: {filename}")
        return filename
    except Exception as e:
        print(f"[ERROR] Error al guardar imagen Base64 del OCR: {e}")
        return None

@noticias_bp.route("/nueva", methods=["GET", "POST"])
@login_required
def crear():
    """Crear nueva noticia de prensa"""
    return crear_noticia_view(get_proyecto_activo)

def crear_noticia_view(get_proyecto_activo_func):
    from models import AutorPrensa
    pub = None
    proyecto = get_proyecto_activo_func()
    if not proyecto:
        flash("⚠️ Debes seleccionar un proyecto antes de crear noticias", "warning")
        return redirect(url_for("proyectos.listar"))
    precargados = {key: request.args.get(key) for key in request.args}
    
    if request.method == "POST":
        # 1. GESTIÓN DE MÚLTIPLES AUTORES Y PSEUDÓNIMO
        pseudonimo = (request.form.get("pseudonimo") or "").strip()
        nombres_lista = request.form.getlist("nombre_autor[]")
        apellidos_lista = request.form.getlist("apellido_autor[]")
        tipos_lista = request.form.getlist("tipo_autor[]")
        anonimos_raw = request.form.getlist("es_anonimo_raw[]")
        
        # Para compatibilidad con columnas nombre_autor / apellido_autor originales (primer autor)
        nombre_autor_db = None
        apellido_autor_db = None
        
        # Procesamos la lista de autores
        autores_objs = []
        for i in range(len(tipos_lista)):
            nom = (nombres_lista[i] if i < len(nombres_lista) else "").strip()
            ape = (apellidos_lista[i] if i < len(apellidos_lista) else "").strip()
            tip = tipos_lista[i]
            es_anon = (i < len(anonimos_raw) and anonimos_raw[i] == "si")
            
            autores_objs.append(AutorPrensa(
                nombre=nom if not es_anon else None,
                apellido=ape if not es_anon else None,
                tipo=tip,
                es_anonimo=es_anon,
                orden=i
            ))
            
            # El primero se guarda en la tabla Prensa para compatibilidad
            if i == 0:
                nombre_autor_db = nom if not es_anon else None
                apellido_autor_db = ape if not es_anon else None

        with open("/opt/hesiox/debug_post.log", "a") as f:
            f.write(f"\n[NOTICIAS] POST Data (Nueva):\n")
            for k in request.form.keys():
                vals = request.form.getlist(k)
                f.write(f"  {k}: {vals}\n")
            f.write("-" * 30 + "\n")

    # Establecer tipo de recurso por defecto según el tipo de proyecto
    if not precargados.get("tipo_recurso"):
        if proyecto.tipo == "libros":
            precargados["tipo_recurso"] = "libro"
        elif proyecto.tipo == "hemerografia":
            precargados["tipo_recurso"] = "prensa"

    from flask import g
    g.proyecto = proyecto
    form_data = get_form_data_for_templates_noticias()
    from models import Hemeroteca, ImagenPrensa
    if proyecto:
        hemerotecas = Hemeroteca.query.filter_by(proyecto_id=proyecto.id).order_by(Hemeroteca.nombre).all()
    else:
        hemerotecas = Hemeroteca.query.order_by(Hemeroteca.nombre).all()
    if request.method == "POST":
        # DEBUG LOGGING
        import logging
        logger = logging.getLogger("noticias_crear")
        logger.info("Keys in request.form: %s", list(request.form.keys()))
        logger.info("Contenido length: %s", len(request.form.get("contenido", "")))
        logger.info("Texto original length: %s", len(request.form.get("texto_original", "")))
        
        fecha_original = (request.form.get("fecha_original") or "").strip()
        anio_str = (request.form.get("anio") or "").strip()
        tipo_recurso = (request.form.get("tipo_recurso") or "").strip()

        # --- Lógica de Fecha Automática para Libros ---
        if tipo_recurso == "libro" and anio_str.isdigit() and not fecha_original:
            fecha_original = f"01/01/{anio_str}"

        fecha_consulta = (request.form.get("fecha_consulta") or "").strip()
        nombre = (request.form.get("nombre_autor") or "").strip()
        apellido = (request.form.get("apellido_autor") or "").strip()
        es_anonimo = "anonimo" in request.form
        if es_anonimo:
            autor_final = None
        elif apellido or nombre:
            if apellido and nombre:
                autor_final = f"{apellido}, {nombre}"
            elif apellido:
                autor_final = apellido
            else:
                autor_final = nombre
        else:
            autor_final = None
        nombre_pub = (request.form.get("publicacion") or "").strip()
        pub = None
        fuente_heredada = None
        if nombre_pub:
            pub = Publicacion.query.filter_by(nombre=nombre_pub, proyecto_id=proyecto.id).first()
            if not pub:
                pub = Publicacion(nombre=nombre_pub, proyecto_id=proyecto.id)
                db.session.add(pub)
                db.session.flush()
            # Heredar campos de la publicación si están vacíos en el formulario
            campos_pub = {
                "idioma": request.form.get("idioma") or pub.idioma,
                "licencia": request.form.get("licencia") or pub.licencia or "CC BY 4.0",
                "formato_fuente": request.form.get("formato_fuente") or pub.formato_fuente,
                "pais_publicacion": request.form.get("pais_publicacion") or pub.pais_publicacion,
                "tipo_recurso": request.form.get("tipo_recurso") or pub.tipo_recurso,
                "nombre_autor": request.form.get("nombre_autor") or pub.nombre_autor,
                "apellido_autor": request.form.get("apellido_autor") or pub.apellido_autor,
                "pseudonimo": request.form.get("pseudonimo") or pub.pseudonimo,
            }
            # Heredar fuente/institución de la hemeroteca asociada a la publicación
            if pub.hemeroteca_id:
                from models import Hemeroteca
                hemeroteca = Hemeroteca.query.get(pub.hemeroteca_id)
                if hemeroteca and hemeroteca.institucion:
                    fuente_heredada = hemeroteca.institucion
        else:
            campos_pub = {
                "idioma": request.form.get("idioma"),
                "licencia": request.form.get("licencia") or "CC BY 4.0",
                "formato_fuente": request.form.get("formato_fuente"),
                "pais_publicacion": request.form.get("pais_publicacion"),
                "tipo_recurso": request.form.get("tipo_recurso"),
            }
        
        # Guardar temas como string separado por comas
        temas_val = request.form.getlist("temas")
        if not temas_val:
            temas_val = request.form.get("temas")
        if isinstance(temas_val, list):
            temas_final = ", ".join([t.strip() for t in temas_val if t.strip()])
        else:
            temas_final = (temas_val or "").strip()
        
        # Procesar contenido de texto (directo desde el formulario o desde archivo .txt subido)
        txt_file = request.files.get("archivo_texto")
        form_content = request.form.get("contenido")
        final_content = form_content
        
        if txt_file and txt_file.filename.endswith('.txt'):
            try:
                raw_data = txt_file.read()
                try:
                    final_content = raw_data.decode('utf-8')
                except UnicodeDecodeError:
                    final_content = raw_data.decode('latin-1')
                # Aplicar limpieza profunda para eliminar ruido de OCR si el TXT viene de uno
                final_content = limpieza_profunda_ocr(final_content)
                print(f"[DEBUG] Archivo .txt detectado, contenido cargado y LIMPIADO: {len(final_content)} caracteres")
            except Exception as e:
                print(f"[ERROR] Error al leer o limpiar archivo .txt: {e}")

        # Guardar todos los campos del formulario
        nuevo = Prensa(
            proyecto_id=proyecto.id,
            titulo=request.form.get("titulo"),
            publicacion=nombre_pub,
            id_publicacion=pub.id_publicacion if pub else None,
            coleccion=request.form.get("coleccion"),
            ciudad=request.form.get("ciudad"),
            fecha_original=fecha_original,
            anio=int(request.form.get("anio")) if request.form.get("anio") and str(request.form.get("anio")).isdigit() else None,
            numero=request.form.get("numero"),
            pagina_inicio=request.form.get("pagina_inicio"),
            pagina_fin=request.form.get("pagina_fin"),
            paginas=request.form.get("paginas"),
            url=request.form.get("url"),
            fecha_consulta=fecha_consulta,
            nombre_autor=nombre_autor_db or campos_pub.get("nombre_autor"),
            apellido_autor=apellido_autor_db or campos_pub.get("apellido_autor"),
            pseudonimo=pseudonimo or campos_pub.get("pseudonimo"),
            tipo_autor=request.form.get("tipo_autor") or (autores_objs[0].tipo if autores_objs else "firmado"),
            idioma=campos_pub["idioma"],
            licencia=campos_pub["licencia"],
            fuente_condiciones=request.form.get("fuente_condiciones"),
            temas=temas_final,
            notas=request.form.get("notas"),
            contenido=final_content,
            incluido=True if request.form.get("incluido") == "si" else False,
            numero_referencia=int(request.form.get("numero_referencia")) if request.form.get("numero_referencia") and str(request.form.get("numero_referencia")).isdigit() else None,
            tipo_recurso=campos_pub["tipo_recurso"],
            editor=request.form.get("editor"),
            lugar_publicacion=request.form.get("lugar_publicacion"),
            issn=request.form.get("issn"),
            volumen=request.form.get("volumen"),
            seccion=request.form.get("seccion"),
            palabras_clave=request.form.get("palabras_clave"),
            resumen=request.form.get("resumen"),
            editorial=request.form.get("editorial"),
            isbn=request.form.get("isbn"),
            doi=request.form.get("doi"),
            pais_publicacion=campos_pub["pais_publicacion"],
            formato_fuente=campos_pub["formato_fuente"],
            referencias_relacionadas=request.form.get("referencias_relacionadas"),
            archivo_pdf=request.form.get("archivo_pdf"),
            fuente=request.form.get("fuente") or fuente_heredada,
            imagen_scan=request.form.get("imagen_scan"),
            texto_original=request.form.get("texto_original"),
            descripcion_publicacion=request.form.get("descripcion_publicacion"),
            tipo_publicacion=request.form.get("tipo_publicacion"),
            periodicidad=request.form.get("periodicidad"),
            actos_totales=request.form.get("actos_totales"),
            escenas_totales=request.form.get("escenas_totales"),
            reparto_total=request.form.get("reparto_total"),
            edicion=request.form.get("edicion"),
            escenas=request.form.get("escenas"),
            reparto=request.form.get("reparto"),
        )
        db.session.add(nuevo)
        db.session.flush()  # Para obtener el ID de la noticia antes de commit

        # 2.5 GUARDAR AUTORES RELACIONADOS
        for aut in autores_objs:
            nuevo.autores.append(aut)
        # Guardar imágenes adjuntas (múltiples)
        imagenes_files = request.files.getlist("imagen_scan")
        from models import ImagenPrensa
        for file in imagenes_files:
            if file and file.filename:
                filename = secure_filename(file.filename)
                upload_folder = current_app.config.get("UPLOAD_FOLDER", "static/uploads")
                ruta = os.path.join(upload_folder, filename)
                file.save(ruta)
                nueva_img = ImagenPrensa(prensa_id=nuevo.id, filename=filename)
                db.session.add(nueva_img)

        # ── Sincronizar Temas (Modelo Tema) ──
        if temas_final:
            nombres_temas = [t.strip() for t in temas_final.split(',') if t.strip()]
            from models import Tema
            temas_objs = []
            for nt in nombres_temas:
                t_obj = Tema.query.filter_by(proyecto_id=proyecto.id, nombre=nt).first()
                if not t_obj:
                    t_obj = Tema(proyecto_id=proyecto.id, nombre=nt)
                    db.session.add(t_obj)
                    db.session.flush()
                temas_objs.append(t_obj)
            nuevo.temas_rel = temas_objs

        db.session.commit()

        # --- NUEVO: Procesar imagen vinculada del OCR (Base64) ---
        ocr_b64 = request.form.get("ocr_image_base64")
        if ocr_b64:
            filename_ocr = save_base64_image(ocr_b64, nuevo.id)
            if filename_ocr:
                nueva_img_ocr = ImagenPrensa(prensa_id=nuevo.id, filename=filename_ocr)
                db.session.add(nueva_img_ocr)
                db.session.commit()
                print(f"[OCR] Imagen vinculada persistida para noticia {nuevo.id}")

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.args.get('ajax') == '1':
            return jsonify({
                "success": True,
                "message": "Referencia guardada correctamente.",
                "id": nuevo.id
            })

        flash("✅ Noticia guardada correctamente.", "success")
        return redirect(url_for("noticias.listar", highlight_id=nuevo.id))
    next_url = None
    autores_json = "[]"
    if precargados.get("publicacion"):
        pub_obj = Publicacion.query.filter_by(nombre=precargados.get("publicacion"), proyecto_id=proyecto.id).first()
        if pub_obj and hasattr(pub_obj, 'autores') and pub_obj.autores:
            aut_list = []
            for a in pub_obj.autores:
                aut_list.append({
                    'nombre': a.nombre or '',
                    'apellido': a.apellido or '',
                    'tipo': a.tipo or 'firmado',
                    'es_anonimo': a.es_anonimo
                })
            autores_json = json.dumps(aut_list)

    return render_template(
        "new.html",
        **form_data,
        hemerotecas=hemerotecas,
        next_url=next_url,
        precargados=precargados,
        publicacion_rel=pub,
        autores_json=autores_json
    )

# --- Editar noticia de prensa ---

# --- Editar noticia de prensa ---
@noticias_bp.route("/editar/<int:id>", methods=["GET", "POST"])
@login_required
def editar(id):
    """Editar noticia existente"""
    if request.method == "POST":
        with open("/opt/hesiox/debug_post.log", "a") as f:
            f.write(f"\n[NOTICIAS] POST Data (Editar) for ID {id}:\n")
            # Log all form keys and values
            for k in request.form.keys():
                vals = request.form.getlist(k)
                f.write(f"  {k}: {vals}\n")
            f.write("-" * 30 + "\n")
    """Editar noticia de prensa existente"""
    noticia = db.session.get(Prensa, id)
    if not noticia:
        flash("Noticia no encontrada", "danger")
        return redirect(url_for("noticias.listar"))
    if request.method == "POST":
        noticia.titulo = request.form.get("titulo")
        nombre_pub = (request.form.get("publicacion") or "").strip()
        noticia.publicacion = nombre_pub
        if nombre_pub:
            pub_obj = Publicacion.query.filter_by(nombre=nombre_pub, proyecto_id=noticia.proyecto_id).first()
            if not pub_obj:
                pub_obj = Publicacion(nombre=nombre_pub, proyecto_id=noticia.proyecto_id)
                db.session.add(pub_obj)
                db.session.flush()
            noticia.id_publicacion = pub_obj.id_publicacion
        else:
            noticia.id_publicacion = None
        noticia.ciudad = request.form.get("ciudad")
        noticia.coleccion = request.form.get("coleccion")
        
        fecha_orig = (request.form.get("fecha_original") or "").strip()
        anio_val = (request.form.get("anio") or "").strip()
        tipo_rec = (request.form.get("tipo_recurso") or "").strip()

        # --- Lógica de Fecha Automática para Libros ---
        if tipo_rec == "libro" and anio_val.isdigit() and not fecha_orig:
            fecha_orig = f"01/01/{anio_val}"

        noticia.fecha_original = fecha_orig
        noticia.anio = int(anio_val) if anio_val.isdigit() else None
        noticia.numero = request.form.get("numero")
        noticia.pagina_inicio = request.form.get("pagina_inicio")
        noticia.pagina_fin = request.form.get("pagina_fin")
        noticia.paginas = request.form.get("paginas")
        noticia.url = request.form.get("url")
        noticia.fecha_consulta = request.form.get("fecha_consulta")
        # 1. GESTIÓN DE MÚLTIPLES AUTORES Y PSEUDÓNIMO
        noticia.pseudonimo = (request.form.get("pseudonimo") or "").strip()
        
        nombres_lista = request.form.getlist("nombre_autor[]")
        apellidos_lista = request.form.getlist("apellido_autor[]")
        tipos_lista = request.form.getlist("tipo_autor[]")
        anonimos_raw = request.form.getlist("es_anonimo_raw[]")

        # Limpiar autores antiguos usando la relación
        noticia.autores = []
        db.session.flush()
        
        # Procesamos la nueva lista (usamos tipos_lista como base porque siempre tiene un valor por fila)
        for i in range(len(tipos_lista)):
            nom = (nombres_lista[i] if i < len(nombres_lista) else "").strip()
            ape = (apellidos_lista[i] if i < len(apellidos_lista) else "").strip()
            tip = tipos_lista[i]
            es_anon = (i < len(anonimos_raw) and anonimos_raw[i] == "si")
            
            nuevo_aut = AutorPrensa(
                prensa_id=noticia.id,
                nombre=nom if not es_anon else None,
                apellido=ape if not es_anon else None,
                tipo=tip,
                es_anonimo=es_anon,
                orden=i
            )
            noticia.autores.append(nuevo_aut)
            
            # Sincronizar el primero para compatibilidad
            if i == 0:
                noticia.nombre_autor = nom if not es_anon else None
                noticia.apellido_autor = ape if not es_anon else None
                if es_anon:
                    noticia.autor = "Anónimo"
                else:
                    if ape and nom: noticia.autor = f"{ape}, {nom}"
                    elif ape: noticia.autor = ape
                    else: noticia.autor = nom
        
        # Recargar autores para asegurar que el flush() posterior los vea
        db.session.flush()
        noticia.tipo_autor = request.form.get("tipo_autor") or (tipos_lista[0] if tipos_lista else "firmado")
        noticia.idioma = request.form.get("idioma")
        noticia.licencia = request.form.get("licencia")
        noticia.fuente_condiciones = request.form.get("fuente_condiciones")
        # Guardar temas como string separado por comas (Choices.js puede enviar lista)
        temas_val = request.form.getlist("temas")
        if not temas_val:
            temas_val = request.form.get("temas")
        if isinstance(temas_val, list):
            temas_final = ", ".join([t.strip() for t in temas_val if t.strip()])
        else:
            temas_final = (temas_val or "").strip()
        
        noticia.temas = temas_final
        
        # ── Sincronizar Temas (Modelo Tema) ──
        nombres_temas = [t.strip() for t in temas_final.split(',') if t.strip()]
        from models import Tema
        temas_objs = []
        for nt in nombres_temas:
            t_obj = Tema.query.filter_by(proyecto_id=noticia.proyecto_id, nombre=nt).first()
            if not t_obj:
                t_obj = Tema(proyecto_id=noticia.proyecto_id, nombre=nt)
                db.session.add(t_obj)
                db.session.flush()
            temas_objs.append(t_obj)
        noticia.temas_rel = temas_objs
        noticia.notas = request.form.get("notas")
        
        # Procesar contenido de texto (directo desde el formulario o desde archivo .txt subido)
        txt_file = request.files.get("archivo_texto")
        form_content = request.form.get("contenido")
        if txt_file and txt_file.filename.endswith('.txt'):
            try:
                raw_data = txt_file.read()
                try:
                    final_content = raw_data.decode('utf-8')
                except UnicodeDecodeError:
                    final_content = raw_data.decode('latin-1')
                # Aplicar limpieza profunda
                final_content = limpieza_profunda_ocr(final_content)
                noticia.contenido = final_content
            except Exception as e:
                print(f"[ERROR] Error al leer o limpiar archivo .txt en editar: {e}")
        else:
            noticia.contenido = form_content

        incluido_val = request.form.get("incluido")
        noticia.incluido = True if incluido_val == "si" else False
        num_ref_val = request.form.get("numero_referencia")
        noticia.numero_referencia = int(num_ref_val) if num_ref_val and str(num_ref_val).isdigit() else None
        noticia.tipo_recurso = request.form.get("tipo_recurso")
        noticia.editor = request.form.get("editor")
        noticia.lugar_publicacion = request.form.get("lugar_publicacion")
        noticia.issn = request.form.get("issn")
        noticia.volumen = request.form.get("volumen")
        noticia.seccion = request.form.get("seccion")
        noticia.palabras_clave = request.form.get("palabras_clave")
        noticia.pseudonimo = request.form.get("pseudonimo")
        noticia.resumen = request.form.get("resumen")
        noticia.editorial = request.form.get("editorial")
        noticia.isbn = request.form.get("isbn")
        noticia.doi = request.form.get("doi")
        noticia.pais_publicacion = request.form.get("pais_publicacion")
        noticia.formato_fuente = request.form.get("formato_fuente")
        noticia.referencias_relacionadas = request.form.get("referencias_relacionadas")
        noticia.archivo_pdf = request.form.get("archivo_pdf")
        noticia.fuente = request.form.get("fuente")
        noticia.tipo_publicacion = request.form.get("tipo_publicacion")
        noticia.periodicidad = request.form.get("periodicidad")
        noticia.actos_totales = request.form.get("actos_totales")
        noticia.escenas_totales = request.form.get("escenas_totales")
        noticia.reparto_total = request.form.get("reparto_total")
        noticia.edicion = request.form.get("edicion")
        noticia.escenas = request.form.get("escenas")
        noticia.reparto = request.form.get("reparto")
        noticia.texto_original = request.form.get("texto_original")
        noticia.descripcion_publicacion = request.form.get("descripcion_publicacion")
        
        # --- Transcripciones PRO ---
        noticia.contenido_diplomatico = request.form.get("contenido_diplomatico")
        noticia.contenido_critico = request.form.get("contenido_critico")
        
        # Guardar imágenes adjuntas (múltiples)
        imagenes_files = request.files.getlist("imagen_scan")
        from models import ImagenPrensa
        for file in imagenes_files:
            if file and file.filename:
                filename = secure_filename(file.filename)
                upload_folder = current_app.config.get("UPLOAD_FOLDER", "static/uploads")
                ruta = os.path.join(upload_folder, filename)
                file.save(ruta)
                nueva_img = ImagenPrensa(prensa_id=noticia.id, filename=filename)
                db.session.add(nueva_img)
        db.session.commit()

        # --- NUEVO: Procesar imagen vinculada del OCR (Base64) ---
        ocr_b64 = request.form.get("ocr_image_base64")
        if ocr_b64:
            filename_ocr = save_base64_image(ocr_b64, noticia.id)
            if filename_ocr:
                nueva_img_ocr = ImagenPrensa(prensa_id=noticia.id, filename=filename_ocr)
                db.session.add(nueva_img_ocr)
                db.session.commit()
                print(f"[OCR] Imagen vinculada persistida para noticia {noticia.id}")

        # --- GESTIÓN DE VERSIONES (PRO) ---
        comentario = request.form.get("comentario_version") or "Actualización de ficha"
        version = VersionPrensa(
            prensa_id=noticia.id,
            user_id=current_user.id if current_user.is_authenticated else None,
            titulo=noticia.titulo,
            contenido=noticia.contenido,
            contenido_diplomatico=noticia.contenido_diplomatico,
            contenido_critico=noticia.contenido_critico,
            notas=noticia.notas,
            comentario_cambio=comentario
        )
        db.session.add(version)
        db.session.commit()

        # Invalidate analysis cache
        try:
            from analisis_cache import cache as analisis_cache_instance
            analisis_cache_instance.limpiar_todo()
        except:
            pass

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.args.get('ajax') == '1':
            return jsonify({
                "success": True,
                "message": "Referencia actualizada correctamente.",
                "id": noticia.id
            })

        flash("✅ Noticia actualizada correctamente.", "success")
        return redirect(url_for("noticias.listar", highlight_id=noticia.id))
    # --- LÓGICA DE NAVEGACIÓN (SWITCHER) ---
    sql_case = r"""
        CASE 
            WHEN fecha_original ~ '^\d{2}/\d{2}/\d{4}$' THEN to_date(fecha_original, 'DD/MM/YYYY')
            WHEN fecha_original ~ '^\d{4}-\d{2}-\d{2}$' THEN to_date(fecha_original, 'YYYY-MM-DD')
            WHEN fecha_original ~ '^\d{4}-\d{2}$' THEN to_date(fecha_original || '-01', 'YYYY-MM-DD')
            WHEN fecha_original ~ '^\d{4}$' THEN to_date(fecha_original || '-01-01', 'YYYY-MM-DD')
            ELSE '1900-01-01'::date
        END
    """
    
    try:
        # Obtener valor de ordenación actual
        current_date_val = db.session.execute(
            text(f"SELECT ({sql_case}) FROM prensa WHERE id = :id"),
            {'id': id}
        ).scalar()

        
        # Siguiente noticia
        sql_next = text(f"""
            SELECT id FROM prensa 
            WHERE proyecto_id = :pid 
            AND (
                ({sql_case}) > :cur_date
                OR (({sql_case}) = :cur_date AND id > :cur_id)
            )
            ORDER BY ({sql_case}) ASC, id ASC
            LIMIT 1
        """)
        noticia_next_id = db.session.execute(sql_next, {
            'pid': noticia.proyecto_id, 
            'cur_date': current_date_val, 
            'cur_id': id
        }).scalar()
        
        # Noticia anterior
        sql_prev = text(f"""
            SELECT id FROM prensa 
            WHERE proyecto_id = :pid 
            AND (
                ({sql_case}) < :cur_date
                OR (({sql_case}) = :cur_date AND id < :cur_id)
            )
            ORDER BY ({sql_case}) DESC, id DESC
            LIMIT 1
        """)
        noticia_prev_id = db.session.execute(sql_prev, {
            'pid': noticia.proyecto_id, 
            'cur_date': current_date_val, 
            'cur_id': id
        }).scalar()
        
        # Totales y posición
        total_count = db.session.query(Prensa).filter(Prensa.proyecto_id == noticia.proyecto_id).count()
        current_pos = db.session.execute(
            text(f"""
                SELECT COUNT(*) FROM prensa 
                WHERE proyecto_id = :pid 
                AND (
                    ({sql_case}) < :cur_date
                    OR (({sql_case}) = :cur_date AND id <= :cur_id)
                )
            """),
            {'pid': noticia.proyecto_id, 'cur_date': current_date_val, 'cur_id': id}
        ).scalar()
        
        nav_data = {
            'prev_id': noticia_prev_id,
            'next_id': noticia_next_id,
            'total_count': total_count,
            'current_pos': current_pos
        }
    except Exception as e:
        print(f"[ERROR] Navegación switcher: {e}")
        nav_data = {'prev_id': None, 'next_id': None, 'total_count': 0, 'current_pos': 0}

    # GET o fallback: mostrar formulario con datos actuales
    form_data = get_form_data_for_templates_noticias()
    
    return render_template(
        "editar.html",
        ref=noticia,
        **form_data,
        nav_data=nav_data,
        publicacion_rel=noticia.publicacion_rel,
        nombre_autor_val=noticia.nombre_autor,
        apellido_autor_val=noticia.apellido_autor,
        temas_sel=[t.strip() for t in (noticia.temas or "").split(",") if t.strip()],
        next_url=request.args.get("next"),
        autores_json=json.dumps([{
            'nombre': a.nombre or '',
            'apellido': a.apellido or '',
            'tipo': a.tipo or 'firmado',
            'es_anonimo': a.es_anonimo,
            'orden': a.orden
        } for a in db.session.query(AutorPrensa).filter_by(prensa_id=noticia.id).order_by(AutorPrensa.orden).all()])
    )

@noticias_bp.route('/duplicar/<int:noticia_id>', methods=['GET'], endpoint='noticia_duplicar')
@login_required
def noticia_duplicar(noticia_id):
    """Duplicar noticia de prensa y redirigir a edición del nuevo registro"""
    original = db.session.get(Prensa, noticia_id)
    if not original:
        flash('Noticia original no encontrada', 'danger')
        return redirect(url_for('noticias.listar'))

    campos = [c.name for c in Prensa.__table__.columns if c.name not in ('id', 'creado_en', 'modificado_en', 'entidades_ner')]
    datos = {campo: getattr(original, campo) for campo in campos}
    if 'titulo' in datos and datos['titulo']:
        datos['titulo'] = f"{datos['titulo']} (copia)"
    proyecto_activo = get_proyecto_activo()
    if proyecto_activo:
        datos['proyecto_id'] = proyecto_activo.id
    copia = Prensa(**datos)
    db.session.add(copia)
    db.session.flush() # Obtener id de la copia

    # Copiar autores
    for a in original.autores:
        nueva_aut = AutorPrensa(
            prensa_id=copia.id,
            nombre=a.nombre,
            apellido=a.apellido,
            tipo=a.tipo,
            es_anonimo=a.es_anonimo,
            orden=a.orden
        )
        db.session.add(nueva_aut)

    # Copiar relación con temas
    if original.temas_rel:
        copia.temas_rel = list(original.temas_rel)

    db.session.commit()
    # Invalidate analysis cache
    try: analisis_cache_instance.limpiar_todo()
    except: pass
    flash('Noticia duplicada. Ahora puedes editarla.', 'success')
    return redirect(url_for('noticias.editar', id=copia.id))

# --- Eliminar noticia de prensa ---
@noticias_bp.route('/eliminar/<int:noticia_id>', methods=['POST'], endpoint='noticia_eliminar')
@login_required
def noticia_eliminar(noticia_id):
    noticia = db.session.get(Prensa, noticia_id)
    if not noticia:
        flash('Noticia no encontrada', 'danger')
        return redirect(url_for('noticias.listar'))
    try:
        db.session.delete(noticia)
        db.session.commit()
        # Invalidate analysis cache
        try: analisis_cache_instance.limpiar_todo()
        except: pass
        flash('Noticia eliminada correctamente', 'success')
        return redirect(url_for('noticias.listar'))
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar la noticia: {str(e)}', 'danger')
        return redirect(url_for('noticias.listar'))

# --- Eliminar imagen de prensa (material adjunto) ---
@noticias_bp.route('/imagen/eliminar/<int:imagen_id>', methods=['POST'], endpoint='eliminar_imagen_prensa')
@login_required
def eliminar_imagen_prensa(imagen_id):
    current_app.logger.info(f"[ELIMINAR IMAGEN] ID={imagen_id}, Method={request.method}, User={current_user.nombre if current_user.is_authenticated else 'Anon'}")
    try:
        imagen = db.session.get(ImagenPrensa, imagen_id)
        if not imagen:
            current_app.logger.warning(f"[ELIMINAR IMAGEN] Imagen {imagen_id} no encontrada")
            flash('Imagen no encontrada', 'danger')
            return redirect(request.referrer or url_for('noticias.listar'))
        
        prensa_id = imagen.prensa_id
        filename = imagen.filename
        current_app.logger.info(f"[ELIMINAR IMAGEN] Eliminando {filename} de prensa_id={prensa_id}")
        
        # Eliminar el archivo físico del servidor
        filepath = os.path.join(current_app.root_path, 'static', 'uploads', filename)
        if os.path.exists(filepath):
            os.remove(filepath)
            current_app.logger.info(f"[ELIMINAR IMAGEN] Archivo {filepath} eliminado")
        
        # Eliminar el registro de la base de datos
        db.session.delete(imagen)
        db.session.commit()
        current_app.logger.info(f"[ELIMINAR IMAGEN] Registro BD eliminado correctamente")
        
        flash('🗑️ Imagen eliminada correctamente', 'success')
        return redirect(url_for('noticias.editar', id=prensa_id))
    except Exception as e:
        current_app.logger.error(f"[ELIMINAR IMAGEN] ERROR: {str(e)}", exc_info=True)
        db.session.rollback()
        flash(f'Error al eliminar la imagen: {str(e)}', 'danger')
        return redirect(request.referrer or url_for('noticias.listar'))


@noticias_bp.route("/api/ediciones/<tipo_recurso>", methods=["GET"])
@login_required
def get_ediciones_tipo(tipo_recurso):
    """Retorna las opciones de edición para un tipo de recurso específico desde la BD"""
    try:
        ediciones = EdicionTipoRecurso.query.filter_by(tipo_recurso=tipo_recurso).order_by(EdicionTipoRecurso.orden).all()
        return jsonify([e.to_dict() for e in ediciones])
    except Exception as e:
        print(f"[ERROR] Al obtener ediciones para {tipo_recurso}: {e}")
        return jsonify([]), 500

# --- MODO LECTOR / REVISIÓN ---
@noticias_bp.route('/noticias/lector', methods=['GET'])
@login_required
def lector():
    """Vista del Modo Lector / Revisión"""
    proyecto = get_proyecto_activo()
    if not proyecto:
        flash('Seleccione un proyecto primero', 'warning')
        return redirect(url_for('home'))
        
    return render_template('noticias/lector.html')

@noticias_bp.route('/api/noticias/simple_list', methods=['GET'])
@login_required
def api_noticias_simple_list():
    """Devuelve lista ligera de noticias para selectores (id, titulo, fecha)"""
    proyecto = get_proyecto_activo()
    if not proyecto:
        return jsonify([])
        
    publicacion = request.args.get('publicacion')
    
    query = Prensa.query.filter_by(proyecto_id=proyecto.id)
    
    if publicacion:
        query = query.filter(Prensa.publicacion == publicacion)
        
    # Ordenar por ID de menor a mayor
    query = query.order_by(Prensa.id.asc())
    
    # Proyección optimizada
    resultados = query.with_entities(Prensa.id, Prensa.titulo, Prensa.fecha_original, Prensa.numero).all()
    
    data = []
    for r in resultados:
        # fecha_original es TEXT en DB, formato YYYY-MM-DD usualmente
        fecha_str = "Sin fecha"
        if r.fecha_original:
            try:
                # Intentar parsear si es YYYY-MM-DD
                if len(r.fecha_original) >= 10 and r.fecha_original[4] == '-':
                     anio, mes, dia = r.fecha_original[:10].split('-')
                     fecha_str = f"{dia}/{mes}/{anio}"
                else:
                     fecha_str = r.fecha_original
            except:
                fecha_str = r.fecha_original

        titulo_corto = (r.titulo[:60] + '...') if r.titulo and len(r.titulo) > 60 else (r.titulo or "Sin título")
        label = f"{fecha_str} - {titulo_corto}"
        if r.numero:
            label += f" (Nº {r.numero})"
            
        data.append({
            'id': r.id,
            'label': label,
            'fecha': str(r.fecha_original) if r.fecha_original else None
        })
        
    return jsonify(data)

@noticias_bp.route('/api/noticia/contenido/<int:id>', methods=['GET'])
@login_required
def api_noticia_contenido(id):
    """Devuelve contenido completo de una noticia para el lector"""
    noticia = db.session.get(Prensa, id)
    if not noticia:
        return jsonify({'error': 'Not encontrada'}), 404
        
    # Renderizar plantilla parcial si quisiéramos, pero devolver JSON es más flexible
    # Determinar imágenes (prioridad: imagen_scan > ImagenPrensa records)
    imagenes = []
    with open('/opt/hesiox/api_debug.log', 'a') as f:
        f.write(f"\n[DEBUG API] --- Request for ID: {id} ---\n")
        f.write(f"imagen_scan: {noticia.imagen_scan}\n")
        imgs_asociadas = noticia.imagenes.all()
        f.write(f"Encontradas: {len(imgs_asociadas)}\n")
        for img in imgs_asociadas:
            url = url_for('static', filename=f'uploads/{img.filename}')
            f.write(f" - Image: {img.filename}, URL: {url}\n")
            if url not in imagenes:
                imagenes.append(url)
        
    # [FIX] Priorizar imagen_scan como primera imagen si existe
    if noticia.imagen_scan:
        url_scan = url_for('static', filename=f'uploads/{noticia.imagen_scan}')
        if url_scan not in imagenes:
            imagenes.insert(0, url_scan)
        f.write(f"Total imagenes final: {len(imagenes)}\n")

    # Determinar tipo de proyecto
    tipo_proyecto = "generico"
    if noticia.proyecto:
        tipo_proyecto = noticia.proyecto.tipo

    return jsonify({
        'id': noticia.id,
        'titulo': noticia.titulo,
        'publicacion': noticia.publicacion,
        'fecha': str(noticia.fecha_original) if noticia.fecha_original else "",
        'contenido_html': noticia.contenido, # Asumimos que es HTML seguro o se procesa en front
        'texto_puro': limpieza_profunda_ocr(noticia.contenido) if noticia.contenido else "", # Versión limpia
        'url_imagen': imagenes[0] if imagenes else None,
        'imagenes': imagenes,
        'tipo_proyecto': tipo_proyecto,
        'incluido': noticia.incluido,
        'url_detalle': url_for('noticias.detalle_noticia', id=noticia.id),
        'url_editar': url_for('noticias.editar', id=noticia.id)
    })

@noticias_bp.route('/api/publicaciones_list', methods=['GET'])
@login_required
def api_publicaciones_list():
    """Devuelve nombres de publicaciones del proyecto activo"""
    proyecto = get_proyecto_activo()
    print(f"[DEBUG] api_publicaciones_list llamado. Proyecto: {proyecto}")
    
    if not proyecto:
        print("[DEBUG] No hay proyecto activo.")
        return jsonify([])
    
    # Usar tabla Publicacion que es mucho más rápida y correcta como fuente de verdad
    publicaciones = db.session.query(Publicacion.nombre)\
        .filter_by(proyecto_id=proyecto.id)\
        .order_by(Publicacion.nombre)\
        .all()
        
    print(f"[DEBUG] Publicaciones encontradas: {len(publicaciones)}")
    return jsonify([p[0] for p in publicaciones])

@noticias_bp.route('/api/noticia/resumir/<int:id>', methods=['POST'])
@login_required
@csrf.exempt
def api_resumir_noticia(id):
    """Genera un resumen de la noticia usando Gemini"""
    noticia = db.session.get(Prensa, id)
    if not noticia:
        return jsonify({'error': 'Noticia no encontrada'}), 404
        
    texto = limpieza_profunda_ocr(noticia.contenido)
    if not texto or len(texto) < 50:
        return jsonify({'error': 'Texto insuficiente para resumir'}), 400
        
    from services.gemini_service import summarize_text_gemini
    
    try:
        resultado = summarize_text_gemini(texto)
        if not resultado:
            print(f"[ERROR] Gemini returned None for news {id}")
            return jsonify({'error': 'No se pudo generar el resumen'}), 500
            
        return jsonify(resultado)
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"[ERROR] Exception in api_resumir_noticia: {e}")
        current_app.logger.error(f"Error generando resumen: {e}")
        return jsonify({'error': str(e)}), 500

@noticias_bp.route('/api/noticia/update_content/<int:id>', methods=['POST'])
@login_required
@csrf.exempt
def api_update_noticia_content(id):
    """Actualiza rápidamente el contenido de una noticia (unificando vistas)"""
    noticia = db.session.get(Prensa, id)
    if not noticia:
        return jsonify({'error': 'Noticia no encontrada'}), 404
        
    data = request.get_json()
    nuevo_contenido = data.get('contenido')
    nuevo_titulo = data.get('titulo')
    
    if nuevo_contenido is None and nuevo_titulo is None:
        return jsonify({'error': 'No hay datos para actualizar'}), 400
        
    try:
        if nuevo_contenido is not None:
            noticia.contenido = nuevo_contenido
        if nuevo_titulo is not None:
            noticia.titulo = nuevo_titulo
            
        db.session.commit()
        
        # Invalidar caché de análisis ya que el contenido cambió
        try:
            from analisis_cache import cache as analisis_cache_instance
            analisis_cache_instance.limpiar_todo()
        except:
            pass
            
        return jsonify({
            'success': True,
            'id': noticia.id,
            'texto_puro': limpieza_profunda_ocr(noticia.contenido) if noticia.contenido else ""
        })
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error actualizando contenido noticia {id}: {e}")
        return jsonify({'error': str(e)}), 500

@noticias_bp.route('/noticia/generar_pdf_final', methods=['POST'])
@login_required
def noticia_generar_pdf_final():
    """Genera el PDF final de la noticia con los datos editados"""
    try:
        from pdf_generator import generar_pdf_noticia_simple
        from io import BytesIO

        # Recoger datos del formulario
        noticia_data = {
            'id': request.form.get('id'),
            'titulo': request.form.get('titulo'),
            'autor': request.form.get('autor'),
            'fecha_original': request.form.get('fecha_original'),
            'publicacion': request.form.get('publicacion'),
            'descripcion_publicacion': request.form.get('descripcion_publicacion'),
            'numero': request.form.get('numero'),
            'paginas': request.form.get('paginas'),
            'ciudad': request.form.get('ciudad'),
            'temas': request.form.get('temas'),
            'contenido': request.form.get('contenido'),
            'notas': request.form.get('notas')
        }

        # Generar el PDF usando el buffer
        pdf_buffer = generar_pdf_noticia_simple(noticia_data)
        
        # Nombre del archivo
        # Sanitizar título para nombre de archivo
        titulo_limpio = re.sub(r'[^\w\s-]', '', noticia_data.get('titulo', 'noticia'))[:50]
        filename = f"{titulo_limpio}_{datetime.now().strftime('%Y%m%d')}.pdf"
        
        return send_file(
            pdf_buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        current_app.logger.error(f"Error generando PDF final: {e}")
        flash(f"Error al generar PDF: {str(e)}", "danger")
        return redirect(url_for('noticias.listar'))

@noticias_bp.route("/temas/gestor", methods=["GET", "POST"])
@login_required
def gestor_temas():
    proyecto = get_proyecto_activo()
    if not proyecto:
        flash("Seleccione un proyecto para gestionar temas.", "warning")
        return redirect(url_for("proyectos.listar"))

    from models import Tema
    
    if request.method == "POST":
        accion = request.form.get("accion")
        tema_old = request.form.get("tema_old")
        
        if accion == "renombrar":
            tema_new = request.form.get("tema_new", "").strip()
            if not tema_new:
                flash("El nuevo nombre no puede estar vacío.", "danger")
            else:
                # 1. Actualizar el modelo Tema
                obj_tema = Tema.query.filter_by(proyecto_id=proyecto.id, nombre=tema_old).first()
                if obj_tema:
                    obj_tema.nombre = tema_new
                    
                    # 2. Sincronizar campo legacy en Prensa (opcional pero recomendado por ahora)
                    todas = Prensa.query.filter(Prensa.proyecto_id == proyecto.id, Prensa.temas.contains(tema_old)).all()
                    for p in todas:
                        tags = [t.strip() for t in (p.temas or "").split(",") if t.strip()]
                        if tema_old in tags:
                            new_tags = [tema_new if t == tema_old else t for t in tags]
                            final_tags = []
                            for nt in new_tags:
                                if nt not in final_tags: final_tags.append(nt)
                            p.temas = ", ".join(final_tags)
                    
                    db.session.commit()
                    flash(f"✅ Se ha renombrado '{tema_old}' a '{tema_new}'.", "success")
                else:
                    flash(f"❌ No se encontró el tema '{tema_old}'.", "danger")
        
        elif accion == "crear":
            tema_new = request.form.get("tema_new", "").strip()
            if not tema_new:
                flash("El nombre del tema no puede estar vacío.", "danger")
            else:
                # Verificar si ya existe
                existe = Tema.query.filter_by(proyecto_id=proyecto.id, nombre=tema_new).first()
                if not existe:
                    nuevo_tema = Tema(proyecto_id=proyecto.id, nombre=tema_new)
                    db.session.add(nuevo_tema)
                    db.session.commit()
                    flash(f"✨ El tema '{tema_new}' ha sido creado.", "success")
                else:
                    flash(f"⚠️ El tema '{tema_new}' ya existe.", "info")
            
        return redirect(url_for("noticias.gestor_temas"))

    # Obtener todos los temas y sus conteos usando el nuevo modelo
    temas_list = Tema.query.filter_by(proyecto_id=proyecto.id).order_by(Tema.nombre).all()
    temas_stats = []
    for t in temas_list:
        # Contar artículos asociados vía relación
        cantidad = t.articulos.count()
        temas_stats.append({"nombre": t.nombre, "cantidad": cantidad})
    
    return render_template("gestor_temas.html", temas_stats=temas_stats)


@noticias_bp.route('/api/temas', methods=['GET'], endpoint='api_get_temas')
@csrf.exempt
@login_required
def api_get_temas():
    print("[DEBUG] api_get_temas called - START")
    """Returns JSON list of all unique themes in the current project with their usage counts."""
    proyecto = get_proyecto_activo()
    print(f"[DEBUG] api_get_temas - proyecto: {proyecto}")
    if not proyecto:
        return jsonify({'error': 'No hay proyecto activo'}), 400
    
    # 1. Obtener todos los temas definidos para el proyecto (Temas persistentes)
    temas_persistentes = Tema.query.filter_by(proyecto_id=proyecto.id).order_by(Tema.nombre).all()
    
    # 2. Calcular conteo de uso en Prensa
    # OPTIMIZACIÓN: Solo traer la columna temas
    todas = Prensa.query.with_entities(Prensa.temas).filter(Prensa.proyecto_id == proyecto.id, Prensa.temas.isnot(None), Prensa.temas != '').all()
    
    conteo_uso = {}
    for p in todas:
        tags = [t.strip() for t in (p[0] or "").split(",") if t.strip()]
        for t in tags:
            conteo_uso[t] = conteo_uso.get(t, 0) + 1
            
    # También contar uso en Publicaciones (opcional, pero recomendado para completitud)
    todas_pub = Publicacion.query.with_entities(Publicacion.tema).filter(Publicacion.proyecto_id == proyecto.id, Publicacion.tema.isnot(None), Publicacion.tema != '').all()
    for p in todas_pub:
        tags = [t.strip() for t in (p[0] or "").split(",") if t.strip()]
        for t in tags:
            conteo_uso[t] = conteo_uso.get(t, 0) + (0) # No sumamos para no duplicar 'uso' si se refiere a noticias, 
                                                      # o podemos sumarlo si 'uso' es total. 
                                                      # Decidimos: 'uso' = noticias (Prensa) por ahora.
    
    # 3. Construir respuesta: Todos los temas persistentes + su conteo
    temas_stats = []
    for t in temas_persistentes:
        temas_stats.append({
            "nombre": t.nombre,
            "cantidad": conteo_uso.get(t.nombre, 0)
        })
        
    # 4. (Opcional) Temas que están en Prensa pero no en la tabla Tema (por si acaso quedaron huérfanos)
    for t_nombre, count in conteo_uso.items():
        if not any(ts["nombre"] == t_nombre for ts in temas_stats):
            temas_stats.append({
                "nombre": t_nombre,
                "cantidad": count
            })
            
    temas_stats = sorted(temas_stats, key=lambda x: x["nombre"].lower())
    print(f"[DEBUG] api_get_temas - content: {len(temas_stats)} items found")
    return jsonify(temas_stats)


@noticias_bp.route('/api/temas/renombrar', methods=['POST'], endpoint='api_renombrar_tema')
@csrf.exempt
@login_required
def api_renombrar_tema():
    print("[DEBUG] api_renombrar_tema called")
    """Bulk renames a theme in all project news items using JSON data."""
    proyecto = get_proyecto_activo()
    if not proyecto:
        return jsonify({'error': 'No hay proyecto activo'}), 400
    
    data = request.get_json()
    tema_old = data.get('tema_old')
    tema_new = (data.get('tema_new') or "").strip()
    
    if not tema_old or not tema_new:
        return jsonify({'error': 'Datos incompletos'}), 400
    
    # 1. Actualizar en la tabla Tema
    tema_obj = Tema.query.filter_by(proyecto_id=proyecto.id, nombre=tema_old).first()
    if tema_obj:
        # Check if new name exists
        existing_new = Tema.query.filter_by(proyecto_id=proyecto.id, nombre=tema_new).first()
        if existing_new:
            # Si ya existe el nuevo, borramos el viejo y las referencias apuntarán al nuevo
            db.session.delete(tema_obj)
        else:
            tema_obj.nombre = tema_new
            
    # 2. Actualizar masivamente en Prensa
    todas = Prensa.query.filter(Prensa.proyecto_id == proyecto.id, Prensa.temas.contains(tema_old)).all()
    cambios = 0
    for p in todas:
        tags = [t.strip() for t in (p.temas or "").split(",") if t.strip()]
        if tema_old in tags:
            new_tags = [tema_new if t == tema_old else t for t in tags]
            # Eliminar duplicados
            final_tags = []
            for nt in new_tags:
                if nt not in final_tags:
                    final_tags.append(nt)
            p.temas = ", ".join(final_tags)
            cambios += 1
            
    # 3. Actualizar masivamente en Publicacion
    todas_pub = Publicacion.query.filter_by(proyecto_id=proyecto.id).filter(Publicacion.tema.contains(tema_old)).all()
    for p in todas_pub:
        tags = [t.strip() for t in (p.tema or "").split(",") if t.strip()]
        if tema_old in tags:
            new_tags = [tema_new if t == tema_old else t for t in tags]
            final_tags = []
            for nt in new_tags:
                if nt not in final_tags:
                    final_tags.append(nt)
            p.tema = ", ".join(final_tags)
            cambios += 1
    
    db.session.commit()
    return jsonify({'success': True, 'cambios': cambios})


@noticias_bp.route('/api/temas/eliminar', methods=['POST'], endpoint='api_eliminar_tema')
@csrf.exempt
@login_required
def api_eliminar_tema():
    print("[DEBUG] api_eliminar_tema called")
    """Bulk removes a theme from all project news items using JSON data."""
    proyecto = get_proyecto_activo()
    if not proyecto:
        return jsonify({'error': 'No hay proyecto activo'}), 400
    
    data = request.get_json()
    tema_old = data.get('tema_old')
    
    if not tema_old:
        return jsonify({'error': 'Nombre de tema requerido'}), 400
    
    # 1. Eliminar de la tabla Tema
    tema_obj = Tema.query.filter_by(proyecto_id=proyecto.id, nombre=tema_old).first()
    if tema_obj:
        db.session.delete(tema_obj)
        
    # 2. Quitar el tag de Prensa
    todas = Prensa.query.filter(Prensa.proyecto_id == proyecto.id, Prensa.temas.contains(tema_old)).all()
    cambios = 0
    for p in todas:
        tags = [t.strip() for t in (p.temas or "").split(",") if t.strip()]
        if tema_old in tags:
            new_tags = [t for t in tags if t != tema_old]
            p.temas = ", ".join(new_tags)
            cambios += 1
            
    # 3. Quitar el tag de Publicacion
    todas_pub = Publicacion.query.filter_by(proyecto_id=proyecto.id).filter(Publicacion.tema.contains(tema_old)).all()
    for p in todas_pub:
        tags = [t.strip() for t in (p.tema or "").split(",") if t.strip()]
        if tema_old in tags:
            new_tags = [t for t in tags if t != tema_old]
            p.tema = ", ".join(new_tags)
            cambios += 1
            
    db.session.commit()
    return jsonify({'success': True, 'cambios': cambios})


@noticias_bp.route('/api/temas/crear', methods=['POST'], endpoint='api_crear_tema_v2')
@csrf.exempt
@login_required
def api_crear_tema_v2():
    """Endpoint for creating a theme via API (used by theme-manager.js)"""
    proyecto = get_proyecto_activo()
    if not proyecto:
        return jsonify({'success': False, 'error': 'No hay proyecto activo'}), 400
        
    data = request.get_json()
    tema_new = (data.get('tema_new') or "").strip()
    
    if not tema_new:
        return jsonify({'success': False, 'error': 'El nombre del tema es obligatorio'}), 400
        
    # Check if exists
    existing = Tema.query.filter_by(proyecto_id=proyecto.id, nombre=tema_new).first()
    if existing:
        return jsonify({'success': False, 'error': 'El tema ya existe'}), 400
        
    nuevo = Tema(proyecto_id=proyecto.id, nombre=tema_new)
    db.session.add(nuevo)
    db.session.commit()
    
    return jsonify({'success': True, 'nombre': tema_new})

@noticias_bp.route("/api/noticias/<int:id>/analizar-ner", methods=["POST"])
@login_required
def api_noticia_analizar_ner(id):
    """
    Analiza entidades (NER) usando el motor PROSOGRAF-IA (SpaCy + Filtros + IA).
    Mantenemos el nombre de la ruta por compatibilidad con el JS existente.
    """
    noticia = db.session.get(Prensa, id)
    if not noticia or not noticia.contenido:
        return jsonify({"success": False, "error": "Contenido no disponible o vacío"}), 400
    
    try:
        from services.prosopografia_service import ProsopografiaService
        from flask_login import current_user
        
        # Contexto para la IA
        context = {
            "noticia_id": noticia.id,
            "titulo": noticia.titulo,
            "anio": noticia.anio,
            "proyecto_id": noticia.proyecto_id
        }
        
        svc = ProsopografiaService(proyecto_id=noticia.proyecto_id, user=current_user)
        entidades = svc.analizar_completo(noticia.contenido, context=context)
        
        # Guardar en la base de datos
        noticia.entidades_ner = entidades
        db.session.commit()
        
        num_entidades = len(entidades)
        num_vinculadas = len([e for e in entidades if e.get('autor_bio_id')])
        
        return jsonify({
            "success": True,
            "message": f"PROSOGRAF-IA: Detectadas {num_entidades} entidades ({num_vinculadas} auto-vinculadas).",
            "entidades": entidades
        })
    except Exception as e:
        import traceback
        print(f"[PROSOGRAF-IA] Error: {traceback.format_exc()}")
        return jsonify({"success": False, "error": str(e)}), 500

@noticias_bp.route("/api/noticias/<int:id>/entidades/ignorar-global", methods=["POST"])
@login_required
def api_noticia_entidad_ignorar_global(id):
    """Añade una entidad al diccionario de ignoradas (aprendizaje)"""
    noticia = db.session.get(Prensa, id)
    if not noticia:
        return jsonify({"success": False, "error": "Noticia no encontrada"}), 404
        
    data = request.json
    texto = data.get('texto')
    label = data.get('label')
    
    if not texto:
        return jsonify({"success": False, "error": "Texto no proporcionado"}), 400
        
    try:
        from services.prosopografia_service import ProsopografiaService
        from flask_login import current_user
        
        svc = ProsopografiaService(proyecto_id=noticia.proyecto_id, user=current_user)
        res = svc.aprender_ignorada(texto, label)
        
        if res:
            # Eliminarla también de la noticia actual
            entidades = list(noticia.entidades_ner) if noticia.entidades_ner else []
            entidades = [e for e in entidades if not (e['texto'] == texto and e['label'] == label)]
            noticia.entidades_ner = entidades
            db.session.commit()
            
            return jsonify({"success": True, "message": f"'{texto}' añadido al diccionario de ignorados."})
        else:
            return jsonify({"success": False, "error": "Ya existe en el diccionario o error de base de datos"}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@noticias_bp.route("/api/noticias/<int:id>/entidades/vincular", methods=["POST"])
@login_required
def api_noticia_entidad_vincular(id):
    """Vincula una entidad detectada con un AutorBio"""
    noticia = db.session.get(Prensa, id)
    if not noticia:
        return jsonify({"success": False, "error": "Noticia no encontrada"}), 404
        
    data = request.json
    idx = data.get('index')
    autor_bio_id = data.get('autor_bio_id')
    
    if idx is None or not autor_bio_id:
        return jsonify({"success": False, "error": "Parámetros insuficientes"}), 400
        
    entidades = list(noticia.entidades_ner) if noticia.entidades_ner else []
    if idx >= len(entidades):
        return jsonify({"success": False, "error": "Índice fuera de rango"}), 400
        
    entidades[idx]['autor_bio_id'] = autor_bio_id
    noticia.entidades_ner = entidades
    db.session.commit()
    
    return jsonify({"success": True, "message": "Entidad vinculada correctamente"})

@noticias_bp.route("/api/noticias/<int:id>/entidades/lote", methods=["POST"])
@login_required
def api_noticia_entidades_lote(id):
    """Acciones por lote sobre entidades (eliminar o ignorar global)"""
    noticia = db.session.get(Prensa, id)
    if not noticia:
        return jsonify({"success": False, "error": "Noticia no encontrada"}), 404
        
    data = request.json
    indices = data.get('indices', [])
    accion = data.get('accion') # 'eliminar' o 'ignorar_global'
    
    if not indices or not accion:
        return jsonify({"success": False, "error": "Parámetros insuficientes"}), 400
        
    entidades = list(noticia.entidades_ner) if noticia.entidades_ner else []
    
    # Ordenar índices de mayor a menor para borrar sin alterar los anteriores
    indices_sorted = sorted([int(i) for i in indices], reverse=True)
    
    try:
        from services.prosopografia_service import ProsopografiaService
        svc = ProsopografiaService(proyecto_id=noticia.proyecto_id, user=current_user)
        
        for idx in indices_sorted:
            if idx < len(entidades):
                ent = entidades[idx]
                if accion == 'ignorar_global':
                    svc.aprender_ignorada(ent['texto'], ent.get('label'))
                
                # En ambos casos (eliminar o ignorar), quitamos de la noticia actual
                entidades.pop(idx)
                
        noticia.entidades_ner = entidades
        db.session.commit()
        
        return jsonify({
            "success": True, 
            "message": f"Acción '{accion}' aplicada a {len(indices)} entidades correctamente."
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@noticias_bp.route("/api/noticias/<int:id>/entidades/eliminar", methods=["POST"])
@login_required
def api_noticia_entidad_eliminar(id):
    """Elimina una entidad de la lista de NER"""
    noticia = db.session.get(Prensa, id)
    if not noticia:
        return jsonify({"success": False, "error": "Noticia no encontrada"}), 404
        
    data = request.json
    idx = data.get('index')
    
    if idx is None:
        return jsonify({"success": False, "error": "Índice no proporcionado"}), 400
        
    entidades = list(noticia.entidades_ner) if noticia.entidades_ner else []
    if idx >= len(entidades):
        return jsonify({"success": False, "error": "Índice fuera de rango"}), 400
        
    entidades.pop(idx)
    noticia.entidades_ner = entidades
    db.session.commit()
    
    return jsonify({"success": True, "message": "Entidad eliminada"})


@noticias_bp.route("/noticias/<int:noticia_id>/exportar-tei")
@login_required
def noticia_exportar_tei(noticia_id):
    """Genera un archivo XML en formato TEI (Text Encoding Initiative) para la noticia"""
    noticia = db.session.get(Prensa, noticia_id)
    if not noticia:
        abort(404)
        
    from xml.sax.saxutils import escape as xml_escape
    
    # Construcción básica de TEI
    tei = f'''<?xml version="1.0" encoding="UTF-8"?>
<?xml-model href="http://www.tei-c.org/release/xml/tei/custom/schema/relaxng/tei_all.rng" type="application/xml" schematypens="http://relaxng.org/ns/structure/1.0"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0">
  <teiHeader>
    <fileDesc>
      <titleStmt>
        <title>{xml_escape(noticia.titulo or 'Sin título')}</title>
        <author>{xml_escape(noticia.autor or 'Anónimo')}</author>
      </titleStmt>
      <publicationStmt>
        <publisher>Proyecto HESIOX</publisher>
        <pubPlace>{xml_escape(noticia.ciudad or 'Desconocido')}</pubPlace>
        <date when="{noticia.anio or ''}">{xml_escape(noticia.fecha_original or '')}</date>
      </publicationStmt>
      <sourceDesc>
        <bibl>
          <title level="j">{xml_escape(noticia.publicacion or '')}</title>
          <biblScope unit="page">{xml_escape(noticia.paginas or '')}</biblScope>
        </bibl>
      </sourceDesc>
    </fileDesc>
  </teiHeader>
  <text>
    <body>
      <div type="article">
        <head>{xml_escape(noticia.titulo or '')}</head>
        <p>
          {xml_escape(noticia.contenido or '')}
        </p>
      </div>
      <div type="transcription_diplomatic">
        <p>{xml_escape(noticia.contenido_diplomatico or '')}</p>
      </div>
    </body>
  </text>
</TEI>
'''
    return Response(tei, mimetype='application/xml', 
                    headers={"Content-Disposition": f"attachment;filename=noticia_{noticia_id}_tei.xml"})

@noticias_bp.route("/api/versiones/<int:version_id>")
@login_required
def api_get_version(version_id):
    """Obtiene los datos de una versión específica para su recuperación en el editor"""
    version = db.session.get(VersionPrensa, version_id)
    if not version:
        return jsonify({"success": False, "error": "Versión no encontrada"}), 404
        
    return jsonify({
        "success": True,
        "version": {
            "contenido": version.contenido,
            "contenido_diplomatico": version.contenido_diplomatico,
            "contenido_critico": version.contenido_critico,
            "titulo": version.titulo,
            "notas": version.notas
        }
    })
