"""
Rutas API para Análisis Avanzados
Proyecto Sirio
"""

from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from extensions import db, csrf
from models import (
    Prensa, Publicacion, Hemeroteca, get_or_create_city_with_coords, 
    Ciudad, SemanticConcept, SQL_PRENSA_DATE
)
from advanced_analytics import AnalisisAvanzado
from analisis_cache import cache
from utils import formatear_fecha_para_ui
from sqlalchemy import or_, text
import re
import sys
import json
from analisis_innovador import AnalisisInnovador

# Blueprint
analisis_bp = Blueprint('analisis_avanzado', __name__, url_prefix='/api/analisis')

# Endpoint para recargar caché
@analisis_bp.route('/recargar_cache', methods=['POST'])
@csrf.exempt
@login_required
def recargar_cache():
    """Limpia toda la caché de análisis avanzado"""
    try:
        cache.limpiar_todo()
        return jsonify({'exito': True, 'mensaje': 'Caché de análisis avanzado recargada correctamente.'})
    except Exception as e:
        return jsonify({'exito': False, 'error': str(e)}), 500

@analisis_bp.route('/reuso-detalle', methods=['POST'])
@csrf.exempt
@login_required
def reuso_detalle():
    """Obtiene el contenido de dos documentos para comparación de reuso"""
    try:
        data = request.get_json() or {}
        id1 = data.get('id1')
        id2 = data.get('id2')
        
        if not id1 or not id2:
            return jsonify({'exito': False, 'error': 'Se requieren IDs de ambos documentos'}), 400
            
        doc1 = db.session.get(Prensa, id1)
        doc2 = db.session.get(Prensa, id2)
        
        if not doc1 or not doc2:
            return jsonify({'exito': False, 'error': 'No se encontró uno de los documentos'}), 404
            
        pub1 = Publicacion.query.get(doc1.id_publicacion) if doc1.id_publicacion else None
        pub2 = Publicacion.query.get(doc2.id_publicacion) if doc2.id_publicacion else None
        
        # Helper function to safely format dates (handles both string and datetime)
        def format_fecha(fecha):
            if not fecha:
                return None
            if isinstance(fecha, str):
                return fecha  # Already a string, return as-is
            # If it's a datetime object, format it
            return fecha.strftime('%Y-%m-%d')
        
        return jsonify({
            'exito': True,
            'doc1': {
                'titulo': doc1.titulo,
                'contenido': doc1.contenido,
                'publicacion': pub1.nombre if pub1 else 'Desconocido',
                'fecha': format_fecha(doc1.fecha_original)
            },
            'doc2': {
                'titulo': doc2.titulo,
                'contenido': doc2.contenido,
                'publicacion': pub2.nombre if pub2 else 'Desconocido',
                'fecha': format_fecha(doc2.fecha_original)
            }
        })
    except Exception as e:
        return jsonify({'exito': False, 'error': str(e)}), 500


# Instanciar clase de análisis
analisis = AnalisisAvanzado(db)
innovador = AnalisisInnovador()

@analisis_bp.route('/dramatico/autor', methods=['POST'])
@csrf.exempt
@login_required
def dramatico_autor():
    """Obtiene biografía, foto y datos de estreno de una publicación"""
    try:
        data = request.get_json() or {}
        obra_nombre = data.get('obra')
        
        if not obra_nombre:
            return jsonify({'exito': False, 'error': 'Se requiere el nombre de la obra'}), 400
            
        from app import get_proyecto_activo
        proyecto = get_proyecto_activo()
        proyecto_id = proyecto.id if proyecto else None
        
        pub_query = Publicacion.query.filter_by(nombre=obra_nombre)
        if proyecto_id:
            pub_query = pub_query.filter_by(proyecto_id=proyecto_id)
        pub = pub_query.first()
        
        if not pub:
            return jsonify({'exito': False, 'error': 'No se encontró la publicación/obra'}), 404
            
        # Extraer datos de estreno de una noticia cualquiera
        noticia = Prensa.query.filter_by(id_publicacion=pub.id_publicacion).filter(
            or_(Prensa.fecha_original != None, Prensa.lugar_publicacion != None)
        ).first()
        
        fecha_estreno = ""
        teatro_estreno = ""
        
        if noticia:
            fecha_estreno = noticia.fecha_original or ""
            teatro_estreno = noticia.lugar_publicacion or ""
            
        nombre_autor = pub.nombre_autor or (noticia.nombre_autor if noticia else "")
        apellido_autor = pub.apellido_autor or (noticia.apellido_autor if noticia else "")
        
        from models import AutorBio
        bio = None
        if nombre_autor and apellido_autor:
            bio = AutorBio.query.filter_by(nombre=nombre_autor, apellido=apellido_autor).first()
        elif apellido_autor:
            bio = AutorBio.query.filter_by(apellido=apellido_autor).first()
        elif nombre_autor:
            bio = AutorBio.query.filter_by(nombre=nombre_autor).first()
            
        biografia_texto = ""
        foto_path = ""
        

        if bio:
            biografia_texto = bio.bibliografia or bio.estilo or ""
            foto_path = bio.foto or ""
            if foto_path and not foto_path.startswith('/') and not foto_path.startswith('http'):
                foto_path = f"/static/uploads/autores/{foto_path}"

            
        return jsonify({
            'exito': True,
            'nombre_autor': f"{nombre_autor} {apellido_autor}".strip() or "Autor Desconocido",
            'fecha_estreno': fecha_estreno,
            'teatro_estreno': teatro_estreno,
            'biografia': biografia_texto,
            'foto': foto_path
        })
    except Exception as e:
        return jsonify({'exito': False, 'error': str(e)}), 500


@analisis_bp.route('/analitica-hd')
@login_required
def analisis_hd():
    """Vista principal de análisis novedosos de humanidades digitales"""
    from app import get_proyecto_activo
    
    proyecto = get_proyecto_activo()
    if not proyecto:
        flash("No hay proyecto activo", "warning")
        return redirect(url_for("index"))
    
    # Obtener hemerotecas del proyecto
    hemerotecas = Hemeroteca.query.filter_by(proyecto_id=proyecto.id).all()
    
    # Obtener publicaciones del proyecto
    publicaciones = Publicacion.query.filter_by(proyecto_id=proyecto.id).all()
    
    # Obtener temas únicos
    temas = db.session.query(Prensa.temas)\
        .filter(Prensa.proyecto_id == proyecto.id, Prensa.incluido == True)\
        .filter(Prensa.temas.isnot(None))\
        .filter(Prensa.temas != '')\
        .distinct().all()
    temas = sorted([t[0] for t in temas if t[0]])

    # Obtener países únicos
    paises = db.session.query(Prensa.pais_publicacion)\
        .filter(Prensa.proyecto_id == proyecto.id, Prensa.incluido == True)\
        .filter(Prensa.pais_publicacion.isnot(None))\
        .distinct().all()
    paises = sorted([p[0] for p in paises if p[0]])
    
    return render_template("analisis_hd.html", 
                         hemerotecas=hemerotecas, 
                         publicaciones=publicaciones,
                         temas=temas,
                         paises=paises,
                         proyecto=proyecto)

def extraer_filtros(data):
    """Extrae filtros del request JSON"""
    from app import get_proyecto_activo
    proyecto = get_proyecto_activo()
    
    # Configurar perfil de análisis según el proyecto
    if proyecto and hasattr(proyecto, 'perfil_analisis'):
        analisis.set_perfil_analisis(proyecto.perfil_analisis or 'contenido')
    else:
        analisis.set_perfil_analisis('contenido')  # Default
    
    # Convertir a int si es posible para consistencia de caché
    pub_id = data.get('publicacion_id')
    try:
        if pub_id and str(pub_id).strip() != '':
            pub_id = int(pub_id)
        else:
            pub_id = None
    except:
        pub_id = None

    return {
        'proyecto_id': proyecto.id if proyecto else None,
        'tema': data.get('tema'),
        'publicacion_id': pub_id,
        'pais': data.get('pais'),
        'fecha_desde': data.get('fecha_desde'),
        'fecha_hasta': data.get('fecha_hasta'),
        'eje_x': data.get('eje_x', 'fecha'),  # Nuevo filtro: 'fecha' o 'secuencia'
        'documentos_ids': data.get('documentos_ids', []), # IDs específicos a analizar
        'limite': int(data.get('limite', 300))  # Límite por defecto: 300 (0 = todos)
    }


def obtener_publicaciones_filtradas(proyecto_id=None, tema=None, 
                                    publicacion_id=None, pais=None,
                                    fecha_desde=None, fecha_hasta=None, 
                                    documentos_ids=None, limit=None, **kwargs):
    """Obtiene publicaciones con filtros opcionales"""
    print(f"[DEBUG] Filtrando documentos - Proyecto: {proyecto_id}, Pub: {publicacion_id}, Docs: {len(documentos_ids or [])}")
    query = Prensa.query.filter(Prensa.incluido == True)
    
    if not proyecto_id:
        return []

    if proyecto_id:
        query = query.filter_by(proyecto_id=proyecto_id)
    
    # Filtro por IDs específicos (prioritario si se proporciona)
    if documentos_ids:
        query = query.filter(Prensa.id.in_(documentos_ids))
        # Si se filtran por IDs específicos, el orden debe ser el de los IDs o por ID asc
        return query.order_by(Prensa.id.asc()).all()

    # Filtro por tema (directamente en Prensa)
    if tema:
        query = query.filter(Prensa.temas == tema)
    
    # Filtro por publicación específica
    if publicacion_id is not None and str(publicacion_id) != '':
        try:
            publicacion_id = int(publicacion_id)
            query = query.filter_by(id_publicacion=publicacion_id)
        except (ValueError, TypeError):
            pass
    
    # Filtro por país
    if pais:
        query = query.filter_by(pais_publicacion=pais)
    
    from sqlalchemy import func
    # Filtrar por fechas si se especifican, usando lógica robusta para formatos mixtos (DD/MM/YYYY y YYYY-MM-DD)
    params = {}
    if fecha_desde:
        query = query.filter(text(f"({SQL_PRENSA_DATE}) >= :f_desde"))
        params['f_desde'] = fecha_desde
    if fecha_hasta:
        query = query.filter(text(f"({SQL_PRENSA_DATE}) <= :f_hasta"))
        params['f_hasta'] = fecha_hasta
    
    if params:
        query = query.params(**params)
    # Solo incluir registros marcados como incluidos - DESHABILITADO para analizar todo
    # query = query.filter_by(incluido=True)
    # Ordenar por fecha descendente para obtener los más recientes
    query = query.order_by(Prensa.fecha_original.desc())
    
    # Aplicar límite si se especifica (0 = sin límite)
    if limit and limit > 0:
        query = query.limit(limit)
    
    return query.all()


def publicacion_to_dict(pub):
    """Convierte objeto Prensa a diccionario y asegura coordenadas de ciudad"""
    # Extraer fecha del campo fecha_original (puede ser texto)
    fecha = None
    if pub.fecha_original:
        try:
            from datetime import datetime
            import re
            # Intentar parsear diferentes formatos de fecha comunes
            for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y', '%Y/%m/%d']:
                try:
                    fecha = datetime.strptime(pub.fecha_original, fmt).strftime('%Y-%m-%d')
                    break
                except:
                    continue
            
            # Si no coincide con formatos estándar, intentar extraer el primer bloque de 4 dígitos (Año)
            if not fecha:
                year_match = re.search(r'(\d{4})', pub.fecha_original)
                if year_match:
                    fecha = year_match.group(1)  # Solo el año como fallback mínimo
                else:
                    fecha = pub.fecha_original  # Usar como está
        except:
            fecha = pub.fecha_original

    # --- NUEVO: asegurar coordenadas de ciudad ---
    ciudad_nombre = pub.ciudad or ''
    pais = pub.pais_publicacion or None
    if ciudad_nombre:
        get_or_create_city_with_coords(db.session, ciudad_nombre, country=pais)

    # Obtener nombre real de la publicación desde la relación
    pub_nombre = pub.publicacion or ''
    if hasattr(pub, 'publicacion_rel') and pub.publicacion_rel:
        pub_nombre = pub.publicacion_rel.nombre
        
    return {
        'id': pub.id,
        'publicacion_id': pub.id_publicacion,
        'titulo': pub.titulo or '',
        'contenido': pub.contenido or '',
        'fecha': fecha,
        'publicacion': pub_nombre,
        'ciudad': pub.ciudad or '',
        'pais': pub.pais_publicacion or '',
        'autor': pub.nombre_autor or '',
        'tipo': pub.tipo_recurso or '',
        'seccion': pub.seccion or '',
        'volumen': pub.volumen or '',
        'palabras_clave': pub.palabras_clave or '',
        'reparto_total': getattr(pub, 'reparto_total', '') or '',
        'actos_totales': getattr(pub, 'actos_totales', '') or '',
        'escenas_totales': getattr(pub, 'escenas_totales', '') or '',
        'actos': pub.seccion or '',
        'escenas': pub.volumen or ''
    }



@analisis_bp.route('/lista-documentos', methods=['POST'])
@csrf.exempt
@login_required
def lista_documentos():
    """Retorna una lista simple de IDs y títulos para el selector secuencial"""
    try:
        data = request.get_json() or {}
        filtros = extraer_filtros(data)
        
        # Obtenemos publicaciones usando los filtros actuales (sin limite para el selector)
        # pero limitado a un número razonable para el select (e.g. 1000)
        publicaciones_db = obtener_publicaciones_filtradas(**filtros, limit=1000)
        
        resultados = [{
            'id': p.id,
            'titulo': f"{p.titulo[:50]}..." if p.titulo else f"Documento {p.id}"
        } for p in publicaciones_db]
        
        # Ordenar por ID para que en el select aparezcan en orden secuencial
        resultados.sort(key=lambda x: x['id'])
        
        return jsonify({
            'exito': True,
            'documentos': resultados
        })
    except Exception as e:
        return jsonify({'exito': False, 'error': str(e)}), 500


# ============================================
# ENDPOINTS DE ANÁLISIS
# ============================================

@analisis_bp.route('/sentimiento-temporal', methods=['POST'])
@csrf.exempt
@login_required
def sentimiento_temporal():
    """Análisis de sentimiento a lo largo del tiempo"""
    try:
        data = request.get_json() or {}
        filtros = extraer_filtros(data)
        
        # Intentar obtener de caché
        resultado_cache = cache.obtener('sentimiento', filtros)
        if resultado_cache:
            return jsonify(resultado_cache)
        
        # Si no hay caché, calcular
        limite = filtros.pop('limite', 300)
        eje_x = filtros.pop('eje_x', 'fecha')
        
        publicaciones_db = obtener_publicaciones_filtradas(**filtros, limit=limite if (limite and limite > 0) else None)
        publicaciones = [publicacion_to_dict(p) for p in publicaciones_db]
        
        # Re-inyectar eje_x para la llamada al método
        resultado = analisis.analisis_sentimiento_temporal(publicaciones, eje_x=eje_x)
        
        # Restaurar filtros para caché
        filtros['eje_x'] = eje_x
        filtros['limite'] = limite
        
        # Guardar en caché
        cache.guardar('sentimiento', filtros, resultado, limite=limite, eje_x=eje_x)
        
        return jsonify(resultado)
    
    except Exception as e:
        return jsonify({'exito': False, 'error': str(e)}), 500


@analisis_bp.route('/topic-modeling', methods=['POST'])
@csrf.exempt
@login_required
def topic_modeling():
    """Topic modeling con LDA"""
    try:
        data = request.get_json() or {}
        filtros = extraer_filtros(data)
        n_topics = data.get('n_topics', 5)
        n_words = data.get('n_words', 10)
        
        # Intentar obtener de caché
        resultado_cache = cache.obtener('topics', filtros, n_topics=n_topics, n_words=n_words)
        if resultado_cache:
            return jsonify(resultado_cache)
        
        # Si no hay caché, calcular
        limite = filtros.pop('limite', 300)
        publicaciones_db = obtener_publicaciones_filtradas(**filtros, limit=limite if (limite and limite > 0) else None)
        publicaciones = [publicacion_to_dict(p) for p in publicaciones_db]
        
        resultado = analisis.topic_modeling_lda(publicaciones, n_topics=n_topics, n_words=n_words)
        
        # Guardar en caché
        cache.guardar('topics', filtros, resultado, n_topics=n_topics, n_words=n_words, limite=limite)
        
        return jsonify(resultado)
    
    except Exception as e:
        return jsonify({'exito': False, 'error': str(e)}), 500


@analisis_bp.route('/coocurrencia-entidades', methods=['POST'])
@csrf.exempt
@login_required
def coocurrencia_entidades():
    """Análisis de coocurrencia de entidades"""
    try:
        data = request.get_json() or {}
        filtros = extraer_filtros(data)
        min_coocurrencias = data.get('min_coocurrencias', 2)
        
        # Intentar obtener de caché
        resultado_cache = cache.obtener('entidades', filtros, min_coocurrencias=min_coocurrencias)
        if resultado_cache:
            return jsonify(resultado_cache)
        
        # Si no hay caché, calcular
        limite = filtros.pop('limite', 300)
        publicaciones_db = obtener_publicaciones_filtradas(**filtros, limit=limite if (limite and limite > 0) else None)
        publicaciones = [publicacion_to_dict(p) for p in publicaciones_db]
        
        resultado = analisis.analisis_coocurrencia_entidades(publicaciones, min_coocurrencias)
        
        # Guardar en caché
        cache.guardar('entidades', filtros, resultado, min_coocurrencias=min_coocurrencias, limite=limite)
        
        return jsonify(resultado)
    
    except Exception as e:
        return jsonify({'exito': False, 'error': str(e)}), 500


@analisis_bp.route('/estilometrico', methods=['POST'])
@csrf.exempt
@login_required
def analisis_estilometrico_route():
    """Análisis estilométrico del corpus"""
    try:
        data = request.get_json() or {}
        filtros = extraer_filtros(data)
        
        # Intentar obtener de caché
        resultado_cache = cache.obtener('estilometrico', filtros)
        if resultado_cache:
            return jsonify(resultado_cache)
        
        # Si no hay caché, calcular
        limite = filtros.pop('limite', 300)
        publicaciones_db = obtener_publicaciones_filtradas(**filtros, limit=limite if (limite and limite > 0) else None)
        publicaciones = [publicacion_to_dict(p) for p in publicaciones_db]
        
        resultado = analisis.analisis_estilometrico(publicaciones)
        
        # Guardar en caché
        cache.guardar('estilometrico', filtros, resultado, limite=limite)
        
        return jsonify(resultado)
    
    except Exception as e:
        return jsonify({'exito': False, 'error': str(e)}), 500


@analisis_bp.route('/atribucion', methods=['POST'])
@csrf.exempt
@login_required
def analisis_atribucion_route():
    """Análisis de atribución de autoría y comparativa estilométrica"""
    try:
        data = request.get_json() or {}
        filtros = extraer_filtros(data)
        
        # Intentar obtener de caché
        resultado_cache = cache.obtener('atribucion', filtros)
        if resultado_cache:
            return jsonify(resultado_cache)
        
        # Si no hay caché, calcular
        limite = filtros.pop('limite', 300)
        publicaciones_db = obtener_publicaciones_filtradas(**filtros, limit=limite if (limite and limite > 0) else None)
        publicaciones = [publicacion_to_dict(p) for p in publicaciones_db]
        
        resultado = analisis.atribucion_autoria(publicaciones)
        
        # Guardar en caché
        cache.guardar('atribucion', filtros, resultado, limite=limite)
        
        return jsonify(resultado)
    
    except Exception as e:
        return jsonify({'exito': False, 'error': str(e)}), 500


@analisis_bp.route('/ngramas', methods=['POST'])
@csrf.exempt
@login_required
def ngramas():
    """Análisis de n-gramas frecuentes"""
    try:
        data = request.get_json() or {}
        filtros = extraer_filtros(data)
        n = data.get('n', 2)  # 2=bigramas, 3=trigramas
        top_k = data.get('top_k', 20)
        
        # Intentar obtener de caché
        resultado_cache = cache.obtener('ngramas', filtros, n=n, top_k=top_k)
        if resultado_cache:
            return jsonify(resultado_cache)
        
        # Si no hay caché, calcular
        limite = filtros.pop('limite', 300)
        publicaciones_db = obtener_publicaciones_filtradas(**filtros, limit=limite if (limite and limite > 0) else None)
        publicaciones = [publicacion_to_dict(p) for p in publicaciones_db]
        
        resultado = analisis.analisis_ngramas(publicaciones, n, top_k)
        
        # Guardar en caché
        cache.guardar('ngramas', filtros, resultado, n=n, top_k=top_k, limite=limite)
        
        return jsonify(resultado)
    
    except Exception as e:
        return jsonify({'exito': False, 'error': str(e)}), 500


@analisis_bp.route('/clustering', methods=['POST'])
@csrf.exempt
@login_required
def clustering():
    """Clustering de documentos similares"""
    try:
        data = request.get_json() or {}
        filtros = extraer_filtros(data)
        n_clusters = data.get('n_clusters', 5)
        metodo = data.get('metodo', 'kmeans')
        
        # Intentar obtener de caché
        resultado_cache = cache.obtener('clustering', filtros, n_clusters=n_clusters, metodo=metodo)
        if resultado_cache:
            return jsonify(resultado_cache)
        
        # Si no hay caché, calcular
        limite = filtros.pop('limite', 300)
        publicaciones_db = obtener_publicaciones_filtradas(**filtros, limit=limite if (limite and limite > 0) else None)
        publicaciones = [publicacion_to_dict(p) for p in publicaciones_db]
        
        resultado = analisis.clustering_documentos(publicaciones, n_clusters, metodo)
        
        # Guardar en caché
        cache.guardar('clustering', filtros, resultado, n_clusters=n_clusters, metodo=metodo, limite=limite)
        
        return jsonify(resultado)
    
    except Exception as e:
        return jsonify({'exito': False, 'error': str(e)}), 500


@analisis_bp.route('/regex-search', methods=['POST'])
@csrf.exempt
@login_required
def regex_search():
    """Búsqueda avanzada usando expresiones regulares (PostgreSQL ~*)"""
    try:
        data = request.get_json() or {}
        filtros_base = extraer_filtros(data)
        pattern = data.get('pattern', '')
        campos = data.get('campos', ['contenido', 'titulo'])
        
        # Parámetros de IA
        usar_ia = data.get('usar_ia', False)
        modelo_ia = data.get('modelo_ia', 'gemini-1.5-flash')
        temperatura = float(data.get('temperatura', 0.3))
        
        if not pattern:
            return jsonify({'exito': False, 'error': 'Patrón REGEX no proporcionado'}), 400

        # Validar REGEX antes de enviarla a la base de datos
        try:
            re.compile(pattern)
        except re.error as e:
            return jsonify({'exito': False, 'error': f'Sintaxis REGEX inválida: {str(e)}'}), 400

        # Obtener publicaciones filtradas por criterios base
        limite = int(data.get('limite', 500))
        query = db.session.query(Prensa).filter(Prensa.incluido == True)
        
        if filtros_base.get('proyecto_id'):
            query = query.filter_by(proyecto_id=filtros_base['proyecto_id'])
        if filtros_base.get('publicacion_id'):
            query = query.filter_by(id_publicacion=filtros_base['publicacion_id'])
        if filtros_base.get('pais'):
            query = query.filter_by(pais_publicacion=filtros_base['pais'])
        if filtros_base.get('fecha_desde'):
            query = query.filter(text(f"({SQL_PRENSA_DATE}) >= :f_desde")).params(f_desde=filtros_base['fecha_desde'])
        if filtros_base.get('fecha_hasta'):
            query = query.filter(text(f"({SQL_PRENSA_DATE}) <= :f_hasta")).params(f_hasta=filtros_base['fecha_hasta'])

        # Aplicar operadores REGEX de PostgreSQL (~* para case-insensitive)
        condiciones_regex = []
        for campo in campos:
            if hasattr(Prensa, campo):
                # Usar text() para inyectar el operador nativo de PostgreSQL de forma segura
                condiciones_regex.append(getattr(Prensa, campo).op('~*')(pattern))
        
        if condiciones_regex:
            query = query.filter(or_(*condiciones_regex))

        query = query.order_by(Prensa.fecha_original.desc()).limit(limite)
        resultados_db = query.all()

        vistos = set()
        resultados = []
        
        # Función para extraer snippets
        def get_snippet(texto, pat):
            if not texto: return ""
            m = re.search(pat, texto, re.IGNORECASE)
            if not m: return texto[:150] + "..."
            start = max(0, m.start() - 75)
            end = min(len(texto), m.end() + 75)
            snippet = texto[start:end]
            if start > 0: snippet = "..." + snippet
            if end < len(texto): snippet = snippet + "..."
            return snippet

        for r in resultados_db:
            if r.id in vistos: continue
            vistos.add(r.id)
            
            # Determinar qué campo coincidió para el snippet
            snippet = ""
            for campo in campos:
                val = getattr(r, campo, "")
                if val and re.search(pattern, val, re.IGNORECASE):
                    snippet = get_snippet(val, pattern)
                    break
            
            resultados.append({
                'id': r.id,
                'titulo': r.titulo or 'Sin título',
                'fecha': formatear_fecha_para_ui(r.fecha_original),
                'publicacion': r.publicacion,
                'snippet': snippet,
                'url': f"/noticias/lector?id={r.id}"
            })

        # Análisis con IA si está activado
        analisis_ia = None
        if usar_ia and len(resultados) > 0:
            try:
                from services.ai_service import AIService
                ai_service = AIService(current_user)
                
                # Tomar muestra de snippets para análisis (máx 20 para no saturar)
                muestra_snippets = [r['snippet'] for r in resultados[:20] if r['snippet']]
                snippets_texto = "\n\n---\n\n".join(muestra_snippets[:10])
                
                prompt = f"""Analiza los siguientes fragmentos de documentos encontrados con el patrón regex "{pattern}":

{snippets_texto}

Genera un resumen analítico breve (máximo 150 palabras) que incluya:
1. Patrones temáticos comunes
2. Contextos de uso predominantes
3. Insights o hallazgos relevantes

Responde en formato conciso y profesional."""

                respuesta = ai_service.generar_texto(
                    prompt=prompt,
                    model=modelo_ia,
                    temperature=temperatura,
                    max_tokens=300
                )
                analisis_ia = respuesta.strip()
                print(f"[IA] Análisis generado: {analisis_ia[:100]}...")
            except Exception as e:
                print(f"[IA] Error generando análisis: {e}")
                analisis_ia = None

        respuesta = {
            'exito': True,
            'total': len(resultados),
            'resultados': resultados
        }
        
        if analisis_ia:
            respuesta['analisis_ia'] = analisis_ia
        
        return jsonify(respuesta)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'exito': False, 'error': str(e)}), 500


@analisis_bp.route('/similares/<int:id_documento>', methods=['POST'])
@csrf.exempt
@login_required
def documentos_similares(id_documento):
    """Encuentra documentos similares a uno dado"""
    try:
        data = request.get_json() or {}
        proyecto_id = data.get('proyecto_id')
        top_k = data.get('top_k', 5)
        
        publicaciones_db = obtener_publicaciones_filtradas(
            proyecto_id=proyecto_id,
            limit=1000
        )
        
        publicaciones = [publicacion_to_dict(p) for p in publicaciones_db]
        
        resultado = analisis.documentos_similares(id_documento, publicaciones, top_k)
        
        return jsonify(resultado)
    
    except Exception as e:
        return jsonify({'exito': False, 'error': str(e)}), 500


@analisis_bp.route('/dramatico', methods=['POST'])
@csrf.exempt
@login_required
def analisis_dramatico_route():
    """Análisis específico para obras teatrales (Red de personajes, tensión)"""
    try:
        data = request.get_json() or {}
        print(f"\n[DEBUG] === ANALISIS DRAMATICO REQUEST ===")
        print(f"[DEBUG] data keys: {list(data.keys())}")
        print(f"[DEBUG] generar_ia in request: {data.get('generar_ia')}")
        
        filtros = extraer_filtros(data)

        # Extraer alias manuales
        manual_aliases = data.get('manual_aliases', {})
        print(f"[DEBUG] Dramático - Aliases recibidos: {len(manual_aliases)}")

        # Determinar nombre del filtro para UI
        filtro_nombre = None
        if filtros.get('publicacion_id'):
            from models import Publicacion
            pub_obj = Publicacion.query.get(filtros['publicacion_id'])
            if pub_obj:
                filtro_nombre = pub_obj.nombre
        elif len(filtros.get('documentos_ids', [])) > 0:
            filtro_nombre = f"{len(filtros['documentos_ids'])} documentos seleccionados"

        # Consultar caché incluyendo los alias y el LÍMITE en la clave (si no se pide refrescar)
        refresh = data.get('refresh', False)
        limite = filtros.get('limite', 300) # Mantener para la caché
        
        resultado_cache = None
        if not refresh:
            # IMPORTANTE: Pasar 'limite' para que la clave coincida con el guardado
            resultado_cache = cache.obtener('dramatico', filtros, manual_aliases=manual_aliases, limite=limite)
        
        if resultado_cache:
            # Si se solicita generar IA pero el caché no la tiene, ignoramos el caché para forzar la generación
            if data.get('generar_ia', False) and not resultado_cache.get('analisis_ia'):
                print("[DEBUG] Cache HIT but NO AI report found. Forcing recalculation to generate AI.")
                resultado_cache = None
            
        if resultado_cache:
            # Determinamos si hay filtrado activo para podar de nuevo por si el caché es antiguo
            filtrado_activo = (filtros.get('publicacion_id') is not None) or (len(filtros.get('documentos_ids', [])) > 0)
            
            # --- PODA DE EMERGENCIA (Fuerza bruta sobre caché antiguo) ---
            if 'reparto_detalle' in resultado_cache:
                # Filtrar reparto_detalle: Eliminar 0 palabras siempre
                resultado_cache['reparto_detalle'] = [d for d in resultado_cache['reparto_detalle'] if (d.get('palabras', 0) > 0)]
                nombres_validos = [d['nombre'] for d in resultado_cache['reparto_detalle']]
                
                # Filtrar nodos del grafo
                if 'nodos' in resultado_cache:
                    resultado_cache['nodos'] = [n for n in resultado_cache['nodos'] if n['id'] in nombres_validos]
            
            # REQUISITO: El informe IA NUNCA se envía si no se pide, aunque esté en caché
            if not data.get('generar_ia', False):
                print("[DEBUG] Cache HIT, but NO generar_ia detected. Force nullifying analisis_ia.")
                resultado_cache['analisis_ia'] = None
            else:
                print(f"[DEBUG] Cache HIT with generar_ia=True. AI analysis length: {len(resultado_cache.get('analisis_ia', '')) if resultado_cache.get('analisis_ia') else 0}")
                
            resp = jsonify(resultado_cache)
            resp.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            return resp
                
        # Si no hay caché, calcular
        limite = filtros.pop('limite', 300)
        publicaciones_db = obtener_publicaciones_filtradas(**filtros, limit=limite if (limite and limite > 0) else None)
        publicaciones = [publicacion_to_dict(p) for p in publicaciones_db]

        # Determinar si hay filtrado activo para purgar personajes vacíos
        filtrado_activo = (filtros.get('publicacion_id') is not None) or (len(filtros.get('documentos_ids', [])) > 0)
        
        resultado = analisis.analisis_dramatico(publicaciones, manual_aliases=manual_aliases, filtrado_activo=filtrado_activo)
        
        # IA INSIGHTS: Análisis hermenéutico de la obra (SOLO SI SE SOLICITA)
        generar_ia = data.get('generar_ia', False) or data.get('generar_informe', False)
        modelo_solicitado = data.get('modelo', 'gemini-1.5-flash')
        print(f"[DEBUG] Dramático - Generar IA solicitado: {generar_ia} | Modelo: {modelo_solicitado}")
        
        if generar_ia and len(publicaciones) > 0:
            try:
                from services.ai_service import AIService
                # Mapeo de conveniencia para modelos que vienen del frontend
                # (Opcional, AIService ya mapea algunos, pero aseguramos compatibilidad)
                ai_service = AIService(model=modelo_solicitado, user=current_user)

                
                # Consolidar muestra para la IA
                muestras = []
                for p in publicaciones[:3]:
                    muestras.append(f"OBRA: {p['titulo']}\nCONTENIDO:\n{p['contenido'][:4000]}...")
                
                texto_ia = "\n\n---\n\n".join(muestras)
                
                prompt = f"""Actúa como un crítico teatral y analista literario experto. 
Analiza los siguientes fragmentos de obras teatrales:

{texto_ia}

Genera un informe narratológico de ALTA COMPLEJIDAD que incluya:
1. **Conflicto y Poder**: Motor dramático y jerarquía discursiva.
2. **Espectro Táctico**: Deconstrucción de las intenciones predominantes (Persuadir vs Atacar).
3. **Anatomía del Clímax**: Análisis de los puntos de giro basados en la curva de tensión.
4. **Sincronía Afectiva**: Interpretación de los vínculos de 'Entrainment' entre el reparto.
5. **Hermenéutica Teatral**: Significado profundo y temas universales detectados.

Responde en formato Markdown estructurado, profesional y académico, usando iconos teatrales 🎭✨."""

                resultado['analisis_ia'] = ai_service.generate_content(
                    prompt=prompt,
                    temperature=0.4
                )
                print(f"[DEBUG] IA generada con éxito: {len(resultado['analisis_ia'])} caracteres")
            except Exception as e:
                print(f"[IA ERROR] {e}")
                resultado['analisis_ia'] = "_No se pudo generar el análisis de IA para esta obra._"
        else:
            # No se solicitó IA o no hay documentos - Asegurar NULL
            resultado['analisis_ia'] = None

        # Guardar en caché con la clave que incluye los alias
        resultado['filtro_nombre'] = filtro_nombre
        cache.guardar('dramatico', filtros, resultado, manual_aliases=manual_aliases, limite=limite)
        
        print(f"[DEBUG] Final Response AI field present: {resultado.get('analisis_ia') is not None}")
        resp = jsonify(resultado)
        resp.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        return resp
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'exito': False, 'error': str(e)}), 500


@analisis_bp.route('/dashboard', methods=['POST'])
@csrf.exempt
@login_required
def dashboard_completo():
    """Genera un dashboard completo con múltiples análisis"""
    try:
        data = request.get_json() or {}
        filtros = extraer_filtros(data)
        
        print(f"[DEBUG] Dashboard - filtros: {filtros}")
        
        # Intentar obtener de caché
        resultado_cache = cache.obtener('dashboard', filtros)
        if resultado_cache:
            print(f"[CACHE HIT] Dashboard cargado desde caché")
            return jsonify(resultado_cache)
        
        # Si no hay caché, calcular
        limite = filtros.pop('limite', 300)
        # BUGFIX: permitir analizar más de 300 si el usuario lo pide (limite=0 o >300)
        publicaciones_db = obtener_publicaciones_filtradas(**filtros, limit=limite if (limite and limite > 0) else None)
        
        print(f"[DEBUG] Dashboard - publicaciones encontradas: {len(publicaciones_db)}")
        
        if len(publicaciones_db) == 0:
            return jsonify({
                'exito': False, 
                'error': 'No hay publicaciones disponibles. Por favor, añade algunos documentos primero.'
            }), 400
        
        publicaciones = [publicacion_to_dict(p) for p in publicaciones_db]
        
        print(f"[DEBUG] Dashboard - iniciando análisis de {len(publicaciones)} documentos...")
        
        # Ejecutar múltiples análisis con manejo de errores individual
        resultado = {
            'exito': True,
            'total_documentos': len(publicaciones)
        }
        
        # Sentimiento (procesar todos)
        try:
            # Extraer eje_x de filtros si existe, default a 'fecha'
            eje_x = filtros.get('eje_x', 'fecha')
            theme = data.get('theme', 'dark')
            
            sent_temporal = analisis.analisis_sentimiento_temporal(publicaciones, eje_x=eje_x)
            resultado['sentimiento'] = sent_temporal
            
            # Generar también el Arco Narrativo (siempre por secuencia para el arco)
            if sent_temporal.get('exito'):
                # Si el análisis temporal ya fue por secuencia, usamos sus datos individuales
                # Si no, pedimos uno por secuencia para el arco
                if sent_temporal.get('tipo_eje') == 'secuencia':
                    datos_arco = sent_temporal.get('datos_individuales', [])
                else:
                    res_secuencia = analisis.analisis_sentimiento_temporal(publicaciones, eje_x='secuencia')
                    datos_arco = res_secuencia.get('datos_individuales', [])
                
                # Importar AnalisisInnovador localmente si no está disponible globalmente
                from analisis_innovador import AnalisisInnovador
                innovador = AnalisisInnovador()
                resultado['arco_sentimiento'] = innovador.generar_arco_sentimiento(datos_arco, theme=theme)
        except Exception as e:
            print(f"[ERROR] Sentimiento/Arco: {e}")
            import traceback
            traceback.print_exc()
            resultado['sentimiento'] = {'exito': False, 'error': str(e)}
        
        # Topics (necesita al menos 5 docs)
        try:
            if len(publicaciones) >= 5:
                resultado['topics'] = analisis.topic_modeling_lda(publicaciones, n_topics=min(5, len(publicaciones)//2), n_words=8)
            else:
                resultado['topics'] = {'exito': False, 'error': 'Se necesitan al menos 5 documentos para topic modeling'}
        except Exception as e:
            print(f"[ERROR] Topics: {e}")
            resultado['topics'] = {'exito': False, 'error': str(e)}
        
        # N-gramas
        try:
            resultado['ngramas'] = analisis.analisis_ngramas(publicaciones, n=2, top_k=15)
        except Exception as e:
            print(f"[ERROR] N-gramas: {e}")
            resultado['ngramas'] = {'exito': False, 'error': str(e)}
        
        # Estilometría (procesar todos)
        try:
            resultado['estilometria'] = analisis.analisis_estilometrico(publicaciones)
        except Exception as e:
            print(f"[ERROR] Estilometría: {e}")
            resultado['estilometria'] = {'exito': False, 'error': str(e)}
        
        print(f"[DEBUG] Dashboard - análisis completados")
        
        # Guardar en caché
        cache.guardar('dashboard', filtros, resultado, limite=limite)
        
        return jsonify(resultado)
    
    except Exception as e:
        print(f"[ERROR] Dashboard general: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'exito': False, 'error': str(e)}), 500

@analisis_bp.route('/distribucion-temporal', methods=['GET'])
@login_required
def distribucion_temporal():
    """Distribución temporal del corpus - por años (referencias) o por días (palabras)"""
    try:
        tipo = request.args.get('tipo', 'referencias')
        inicio = request.args.get('inicio')
        fin = request.args.get('fin')
        palabras = request.args.get('palabras', '')
        palabras = [p.strip().lower() for p in palabras.split(',') if p.strip()] if palabras else []

        # Filtrar por proyecto activo
        from utils import get_proyecto_activo
        proyecto = get_proyecto_activo()
        
        limite = request.args.get('limit', '300')
        try:
            limite = int(limite)
        except (ValueError, TypeError):
            limite = 300

        query = Prensa.query.filter(Prensa.incluido == True)
        if proyecto:
            query = query.filter_by(proyecto_id=proyecto.id)
        else:
            return jsonify({"success": False, "error": "No hay proyecto activo. Selecciona un proyecto."})
        if inicio:
            query = query.filter(Prensa.fecha_original >= inicio)
        if fin:
            query = query.filter(Prensa.fecha_original <= fin)
        
        if limite > 0:
            referencias = query.limit(limite).all()
        else:
            referencias = query.all()

        if tipo == 'referencias':
            # Eje X: años presentes en el corpus filtrado
            anios = sorted(set([r.anio for r in referencias if r.anio]))
            labels = [str(a) for a in anios]
            # Serie: número de referencias por año
            conteo = {str(a): 0 for a in anios}
            for r in referencias:
                if r.anio:
                    conteo[str(r.anio)] += 1
            series = [conteo[str(a)] for a in anios]
            return jsonify({"success": True, "labels": labels, "series": series, "agrupacion": "anio"})

        elif tipo == 'palabras' and palabras:
            # Eje X: fechas (días) presentes en el corpus filtrado
            # fecha_original es un string en formato YYYY-MM-DD
            fechas_raw = sorted(set([str(r.fecha_original)[:10] for r in referencias if r.fecha_original]))
            # Convertir a DD/MM/AAAA
            def format_fecha(fecha):
                if fecha and len(fecha) == 10 and fecha[4] == '-' and fecha[7] == '-':
                    return f"{fecha[8:10]}/{fecha[5:7]}/{fecha[0:4]}"
                return fecha
            labels = [format_fecha(f) for f in fechas_raw]
            
            # Serie: frecuencia de cada palabra por día
            series = []
            colores = ['#ff9800', '#03a9f4', '#4caf50', '#e91e63', '#9c27b0', '#ffc107', '#009688', '#f44336', '#607d8b', '#8bc34a']
            for idx, palabra in enumerate(palabras):
                conteo = {format_fecha(f): 0 for f in fechas_raw}
                for r in referencias:
                    if not r.fecha_original:
                        continue
                    fecha_str = format_fecha(str(r.fecha_original)[:10])
                    texto = ((r.contenido or '') + ' ' + (r.titulo or '')).lower()
                    if palabra in texto:
                        conteo[fecha_str] += texto.count(palabra)
                series.append({
                    "label": palabra,
                    "data": [conteo[f] for f in labels],
                    "color": colores[idx % len(colores)]
                })
            return jsonify({"success": True, "labels": labels, "series": series, "agrupacion": "dia"})

        else:
            return jsonify({"success": False, "error": "Tipo o palabras no válidas"})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)})
# ============================================
# ENDPOINTS EXPERIMENTALES DH (NOVEDOSOS)
# ============================================

@analisis_bp.route('/keyness', methods=['POST'])
@csrf.exempt
@login_required
def keyness_analisis():
    """Análisis de Keyness (palabras clave contrastales)"""
    try:
        data = request.get_json() or {}
        filtros = extraer_filtros(data)
        eje = data.get('eje', 'publicacion')
        
        # Intentar obtener de caché
        resultado_cache = cache.obtener('keyness', filtros, eje=eje)
        if resultado_cache:
            return jsonify(resultado_cache)
        
        limite = filtros.pop('limite', 300)
        publicaciones_db = obtener_publicaciones_filtradas(**filtros, limit=limite)
        publicaciones = [publicacion_to_dict(p) for p in publicaciones_db]
        
        resultado = analisis.analisis_keyness(publicaciones, eje=eje)
        
        # Guardar en caché
        cache.guardar('keyness', filtros, resultado, eje=eje, limite=limite)
        
        return jsonify(resultado)
    except Exception as e:
        return jsonify({'exito': False, 'error': str(e)}), 500

@analisis_bp.route('/reuso-textual', methods=['POST'])
@csrf.exempt
@login_required
def reuso_textual_analisis():
    """Detección de fragmentos replicados (noticias virales)"""
    try:
        data = request.get_json() or {}
        filtros = extraer_filtros(data)
        
        # Intentar obtener de caché
        resultado_cache = cache.obtener('reuso', filtros)
        if resultado_cache:
            return jsonify(resultado_cache)
        
        limite = filtros.pop('limite', 500) # Más límite para reuso
        publicaciones_db = obtener_publicaciones_filtradas(**filtros, limit=limite)
        publicaciones = [publicacion_to_dict(p) for p in publicaciones_db]
        
        resultado = analisis.deteccion_reuso_textual(publicaciones)
        
        # Guardar en caché
        cache.guardar('reuso', filtros, resultado, limite=limite)
        
        return jsonify(resultado)
    except Exception as e:
        return jsonify({'exito': False, 'error': str(e)}), 500

# ============================================
# ENDPOINTS BIBLIOTECA DE CONCEPTOS
# ============================================

@analisis_bp.route('/conceptos', methods=['GET'])
@login_required
def get_conceptos():
    try:
        from app import get_proyecto_activo
        proyecto = get_proyecto_activo()
        
        # Obtener conceptos del proyecto o globales
        query = SemanticConcept.query
        if proyecto:
            query = query.filter(or_(SemanticConcept.proyecto_id == proyecto.id, SemanticConcept.proyecto_id == None))
        else:
            query = query.filter(SemanticConcept.proyecto_id == None)
            
        conceptos = query.order_by(SemanticConcept.tema.asc(), SemanticConcept.concepto.asc()).all()
        
        return jsonify({
            'exito': True,
            'conceptos': [{
                'id': c.id,
                'tema': c.tema,
                'concepto': c.concepto,
                'proyecto_id': c.proyecto_id
            } for c in conceptos]
        })
    except Exception as e:
        return jsonify({'exito': False, 'error': str(e)}), 500

@analisis_bp.route('/conceptos', methods=['POST'])
@csrf.exempt
@login_required
def create_concepto():
    try:
        data = request.get_json() or {}
        tema = data.get('tema')
        concepto_text = data.get('concepto')
        
        if not tema or not concepto_text:
            return jsonify({'exito': False, 'error': 'Tema y concepto son requeridos'}), 400
            
        from app import get_proyecto_activo
        proyecto = get_proyecto_activo()
        
        nuevo_concepto = SemanticConcept(
            tema=tema,
            concepto=concepto_text,
            proyecto_id=proyecto.id if proyecto else None
        )
        db.session.add(nuevo_concepto)
        db.session.commit()
        
        return jsonify({'exito': True, 'id': nuevo_concepto.id})
    except Exception as e:
        db.session.rollback()
        return jsonify({'exito': False, 'error': str(e)}), 500

@analisis_bp.route('/conceptos/<int:id>', methods=['PUT'])
@csrf.exempt
@login_required
def update_concepto(id):
    try:
        data = request.get_json() or {}
        tema = data.get('tema')
        concepto_text = data.get('concepto')
        
        concepto_obj = db.session.get(SemanticConcept, id)
        if not concepto_obj:
            return jsonify({'exito': False, 'error': 'Concepto no encontrado'}), 404
            
        if tema:
            concepto_obj.tema = tema
        if concepto_text:
            concepto_obj.concepto = concepto_text
            
        db.session.commit()
        return jsonify({'exito': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'exito': False, 'error': str(e)}), 500

@analisis_bp.route('/conceptos/<int:id>', methods=['DELETE'])
@csrf.exempt
@login_required
def delete_concepto(id):
    try:
        concepto_obj = db.session.get(SemanticConcept, id)
        if not concepto_obj:
            return jsonify({'exito': False, 'error': 'Concepto no encontrado'}), 404
            
        db.session.delete(concepto_obj)
        db.session.commit()
        return jsonify({'exito': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'exito': False, 'error': str(e)}), 500

@analisis_bp.route('/geosemantica', methods=['POST'])
@csrf.exempt
@login_required
def geosemantica_analisis():
    """Mapeo geográfico de tópicos del discurso"""
    try:
        data = request.get_json() or {}
        filtros = extraer_filtros(data)
        
        # Intentar obtener de caché
        resultado_cache = cache.obtener('geosemantica', filtros)
        if resultado_cache:
            return jsonify(resultado_cache)
        
        limite = filtros.pop('limite', 300)
        publicaciones_db = obtener_publicaciones_filtradas(**filtros, limit=limite)
        publicaciones = [publicacion_to_dict(p) for p in publicaciones_db]
        
        resultado = analisis.mapas_geosemanticos(publicaciones)
        
        # Guardar en caché
        cache.guardar('geosemantica', filtros, resultado, limite=limite)
        
        return jsonify(resultado)
    except Exception as e:
        return jsonify({'exito': False, 'error': str(e)}), 500

@analisis_bp.route('/ngramas', methods=['POST'])
@csrf.exempt
@login_required
def ngramas_analisis():
    """Análisis de n-gramas más frecuentes (patrones de palabras)"""
    try:
        data = request.get_json() or {}
        filtros = extraer_filtros(data)
        n = int(data.get('n', 2))
        
        # Intentar obtener de caché
        resultado_cache = cache.obtener('ngramas', filtros, n=n)
        if resultado_cache:
            return jsonify(resultado_cache)
        
        limite = filtros.pop('limite', 300)
        publicaciones_db = obtener_publicaciones_filtradas(**filtros, limit=limite)
        publicaciones = [publicacion_to_dict(p) for p in publicaciones_db]
        
        resultado = analisis.analisis_ngramas(publicaciones, n=n)
        
        # Guardar en caché
        cache.guardar('ngramas', filtros, resultado, n=n, limite=limite)
        
        return jsonify(resultado)
    except Exception as e:
        return jsonify({'exito': False, 'error': str(e)}), 500

@analisis_bp.route('/semantic-shift', methods=['POST'])
@csrf.exempt
@login_required
def semantic_shift_analisis():
    """Estudio del cambio semántico de conceptos clave"""
    try:
        data = request.get_json() or {}
        filtros = extraer_filtros(data)
        palabra = data.get('palabra', '')
        
        if not palabra:
            return jsonify({'exito': False, 'error': 'Debes especificar una palabra para analizar su evolución.'})
            
        # Intentar obtener de caché
        resultado_cache = cache.obtener('shift', filtros, palabra=palabra)
        if resultado_cache:
            return jsonify(resultado_cache)
        
        limite = filtros.pop('limite', 500)
        publicaciones_db = obtener_publicaciones_filtradas(**filtros, limit=limite)
        publicaciones = [publicacion_to_dict(p) for p in publicaciones_db]
        
        resultado = analisis.semantic_shift_analysis(publicaciones, palabra)
        
        # Guardar en caché
        cache.guardar('shift', filtros, resultado, palabra=palabra, limite=limite)
        
        return jsonify(resultado)
    except Exception as e:
        return jsonify({'exito': False, 'error': str(e)}), 500

@analisis_bp.route('/comunidades', methods=['POST'])
@csrf.exempt
@login_required
def comunidades_analisis():
    """Detección de comunidades y agentes influyentes"""
    try:
        data = request.get_json() or {}
        filtros = extraer_filtros(data)
        
        # Intentar obtener de caché
        resultado_cache = cache.obtener('comunidades', filtros)
        if resultado_cache:
            return jsonify(resultado_cache)
        
        limite = filtros.pop('limite', 300)
        publicaciones_db = obtener_publicaciones_filtradas(**filtros, limit=limite)
        publicaciones = [publicacion_to_dict(p) for p in publicaciones_db]
        
        resultado = analisis.analisis_comunidades_agentes(publicaciones)
        
        # Guardar en caché
        cache.guardar('comunidades', filtros, resultado, limite=limite)
        
        return jsonify(resultado)
    except Exception as e:
        return jsonify({'exito': False, 'error': str(e)}), 500

@analisis_bp.route('/retorica', methods=['POST'])
@csrf.exempt
@login_required
def analisis_retorica_route():
    """Análisis de recursos retóricos (ironía, metáforas bélicas, lenguaje emocional)"""
    try:
        data = request.get_json() or {}
        filtros = extraer_filtros(data)
        
        # Intentar obtener de caché
        resultado_cache = cache.obtener('retorica', filtros)
        if resultado_cache:
            return jsonify(resultado_cache)
        
        limite = filtros.pop('limite', 300)
        publicaciones_db = obtener_publicaciones_filtradas(**filtros, limit=limite)
        publicaciones = [publicacion_to_dict(p) for p in publicaciones_db]
        
        # Extraer eje_x
        eje_x = filtros.get('eje_x', 'fecha')
        resultado = analisis.analisis_retorica(publicaciones, eje_x=eje_x)
        
        # Guardar en caché
        cache.guardar('retorica', filtros, resultado, limite=limite)

        
        return jsonify(resultado)
    except Exception as e:
        return jsonify({'exito': False, 'error': str(e)}), 500

@analisis_bp.route('/periodistico', methods=['POST'])
@csrf.exempt
@login_required
def analisis_periodistico_route():
    """Análisis periodístico integral (modalidad, polarización, sensacionalismo, agencia, propaganda)"""
    try:
        data = request.get_json() or {}
        filtros = extraer_filtros(data)
        
        # Intentar obtener de caché
        resultado_cache = cache.obtener('periodistico', filtros)
        if resultado_cache:
            return jsonify(resultado_cache)
        
        limite = filtros.pop('limite', 300)
        publicaciones_db = obtener_publicaciones_filtradas(**filtros, limit=limite)
        publicaciones = [publicacion_to_dict(p) for p in publicaciones_db]
        
        # Extraer eje_x
        eje_x = filtros.get('eje_x', 'fecha')
        resultado = analisis.analisis_periodistico(publicaciones, eje_x=eje_x)
        
        # Guardar en caché
        cache.guardar('periodistico', filtros, resultado, limite=limite)

        
        return jsonify(resultado)
    except Exception as e:
        return jsonify({'exito': False, 'error': str(e)}), 500

# --- ANÁLISIS INNOVADOR ---

@analisis_bp.route('/innovador/semantico', methods=['POST'])
@csrf.exempt
@login_required
def analisis_semantico():
    """Análisis de cambio semántico diacrónico sobre el corpus filtrado"""
    try:
        data = request.get_json() or {}
        filtros = extraer_filtros(data)
        
        limite = filtros.pop('limite', 300)
        publicaciones_db = obtener_publicaciones_filtradas(**filtros, limit=limite if (limite and limite > 0) else None)
        publicaciones = [publicacion_to_dict(p) for p in publicaciones_db]
        
        # Invocamos al motor real de análisis semántico con soporte para términos personalizados y granularidad
        conceptos_raw = data.get('conceptos', '')
        granularidad = data.get('granularidad') # Opcional: 'dia', 'mes', 'anio'
        
        custom_terms = None
        if conceptos_raw:
            custom_terms = [c.strip() for c in conceptos_raw.split(',') if c.strip()]
            
        resultado = innovador.generar_analisis_semantico(publicaciones, custom_terms=custom_terms, granularidad=granularidad)
        
        return jsonify(resultado)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'exito': False, 'error': str(e)}), 500

@analisis_bp.route('/innovador/intertextualidad', methods=['POST'])
@csrf.exempt
@login_required
def analisis_intertextualidad():
    """Análisis de red de intertextualidad y recirculación de textos"""
    try:
        data = request.get_json() or {}
        filtros = extraer_filtros(data)
        
        limite = filtros.pop('limite', 100)
        publicaciones_db = obtener_publicaciones_filtradas(**filtros, limit=limite)
        publicaciones = [publicacion_to_dict(p) for p in publicaciones_db]
        
        resultado = innovador.generar_intertextualidad_real(publicaciones)
        return jsonify(resultado)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'exito': False, 'error': str(e)}), 500

@analisis_bp.route('/innovador/interpretar_intertextualidad', methods=['POST'])
@csrf.exempt
@login_required
def interpretar_intertextualidad_ia():
    try:
        from services.ai_service import AIService
        data = request.get_json() or {}
        chart_data = data.get('chart_data', {})
        modelo_ia = data.get('modelo', 'gemini-1.5-pro')
        
        prompt = (
            "Actúa como un experto en análisis de redes y sociología de la comunicación. "
            "A continuación te presento los nodos (documentos) y enlaces (similitud léxica > 12%) de una red de intertextualidad:\n"
            f"{str(chart_data)}\n\n"
            "Realiza una interpretación analítica breve (2-3 párrafos en Markdown) sobre la 'Circulación' de textos. "
            "Analiza si hay clústeres de documentos muy interconectados (recirculación intensa), qué sugiere eso sobre "
            "la homogeneidad del discurso en ese periodo y cómo se distribuye la influencia temática según los enlaces."
        )
            
        from flask_login import current_user
        # Usar AIService con fallback automático
        ai_service = AIService(model=modelo_ia, user=current_user)
        respuesta = ai_service.generate_content(prompt, temperature=0.7, auto_fallback=True)
        
        if respuesta and isinstance(respuesta, str):
            return jsonify({'exito': True, 'interpretacion': respuesta})
        else:
            error_msg = ai_service.last_error or "Error de comunicación con IA"
            print(f"[Análisis Geográfico] Fallo IA: {error_msg}", file=sys.stderr)
            return jsonify({'exito': False, 'error': error_msg}), 500
    except Exception as e:
        return jsonify({'exito': False, 'error': str(e)}), 500

@analisis_bp.route('/innovador/emociones', methods=['POST'])
@csrf.exempt
@login_required
def analisis_emociones():
    """Análisis de emociones de Plutchik sobre documentos filtrados"""
    try:
        data = request.get_json() or {}
        filtros = extraer_filtros(data)
        
        # Intentar obtener de caché
        resultado_cache = cache.obtener('emociones', filtros)
        if resultado_cache:
            return jsonify(resultado_cache)
            
        limite = filtros.pop('limite', 300)
        publicaciones_db = obtener_publicaciones_filtradas(**filtros, limit=limite if (limite and limite > 0) else None)
        publicaciones = [publicacion_to_dict(p) for p in publicaciones_db]
        
        # Realizamos el análisis real a través del lexicón de Plutchik
        granularidad = data.get('granularidad')
        resultado = innovador.generar_emociones_plutchik(publicaciones, granularidad=granularidad)
        
        # Guardar en caché
        cache.guardar('emociones', filtros, resultado, limite=limite)
        
        return jsonify(resultado)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'exito': False, 'error': str(e)}), 500

@analisis_bp.route('/innovador/interpretar_emociones', methods=['POST'])
@csrf.exempt
@login_required
def interpretar_emociones_ia():
    try:
        from services.ai_service import AIService
        data = request.get_json() or {}
        chart_type = data.get('chart_type', 'radar')
        chart_data = data.get('chart_data', {})
        modelo_ia = data.get('modelo', 'gemini-1.5-pro')
        
        if chart_type == 'radar':
            prompt = (
                "Actúa como un experto lingüista y psico-historiador especializado en humanidades digitales. "
                "A continuación te presento un conteo de palabras extraído de un corpus con las 8 emociones básicas de Plutchik:\n"
                f"{str(chart_data)}\n\n"
                "Realiza una hermenéutica analítica breve (2-3 párrafos formatados en Markdown básico sin títulos grandes) "
                "interpretando la huella emocional, identificando las emociones predominantes, la posible polarización discursiva "
                "o el equilibrio del mismo."
            )
        else:
            prompt = (
                "Actúa como un experto lingüista y psico-historiador especializado en humanidades digitales. "
                "A continuación te presento la evolución temporal de las 8 emociones básicas de Plutchik de un corpus, "
                "donde 'labels' corresponde al eje temporal en formato mensual/anual y el resto son las series:\n"
                f"{str(chart_data)}\n\n"
                "Realiza un análisis diacrónico breve (2-3 párrafos formatados en Markdown básico sin títulos grandes) "
                "destacando los hitos temporales más prominentes, cruces narrativos relevantes (cuando una emoción sobrepasa a otra de forma súbita) "
                "y la volatilidad a lo largo del tiempo."
            )
            
        from flask_login import current_user
        # Usar AIService con fallback automático
        ai_service = AIService(model=modelo_ia, user=current_user)
        respuesta = ai_service.generate_content(prompt, temperature=0.7, auto_fallback=True)
        
        if respuesta and isinstance(respuesta, str):
            return jsonify({'exito': True, 'interpretacion': respuesta})
        else:
            error_msg = ai_service.last_error or "Error de comunicación con IA"
            print(f"[Análisis Emociones] Fallo IA: {error_msg}", file=sys.stderr)
            return jsonify({'exito': False, 'error': error_msg}), 500

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'exito': False, 'error': str(e)}), 500


@analisis_bp.route('/innovador/interpretar_semantica', methods=['POST'])
@csrf.exempt
@login_required
def interpretar_semantica_ia():
    """Interpretación IA de los resultados del análisis semántico diacrónico"""
    try:
        from services.ai_service import AIService
        data = request.get_json() or {}
        chart_data = data.get('chart_data', {})
        modelo_ia = data.get('modelo', 'gemini-1.5-pro')
        
        prompt = (
            "Actúa como un experto en lingüística computacional y análisis semántico diacrónico. "
            "A continuación te presento los datos de evolución de los términos con mayor desplazamiento léxico en un corpus "
            "(frecuencia relativa por cada 1000 palabras en cada periodo):\n"
            f"{str(chart_data)}\n\n"
            "Realiza una interpretación analítica breve (2-3 párrafos formatados en Markdown básico sin títulos grandes) "
            "donde analices cómo la deriva en el uso de estos conceptos refleja posibles cambios ideológicos, "
            "temáticos o sociales en el contexto histórico del corpus. Identifica si hay términos que crecen "
            "mientras otros decrecen y qué sugiere eso sobre la evolución del régimen discursivo."
        )
            
        from flask_login import current_user
        # Usar AIService con fallback automático
        ai_service = AIService(model=modelo_ia, user=current_user)
        respuesta = ai_service.generate_content(prompt, temperature=0.7, auto_fallback=True)
        
        if respuesta and isinstance(respuesta, str):
            return jsonify({'exito': True, 'interpretacion': respuesta})
        else:
            error_msg = ai_service.last_error or "Error de comunicación con IA"
            print(f"[Análisis Semántico] Fallo IA: {error_msg}", file=sys.stderr)
            return jsonify({'exito': False, 'error': error_msg}), 500

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'exito': False, 'error': str(e)}), 500


@analisis_bp.route('/innovador/sirio_chat', methods=['POST'])
@login_required
def analisis_sirio_chat():
    # Placeholder para Sirio Chat
    return jsonify({
        'exito': True,
        'mensaje': 'Modulo de IA Semántica en desarrollo',
        'data': {}
    })

@analisis_bp.route('/innovador/sesgos', methods=['POST'])
@csrf.exempt
@login_required
def analisis_sesgos():
    """Análisis de sesgos discursivos (Género, Clase, Geofocalización)"""
    try:
        data = request.get_json() or {}
        filtros = extraer_filtros(data)
        
        limite = filtros.pop('limite', 300)
        publicaciones_db = obtener_publicaciones_filtradas(**filtros, limit=limite)
        publicaciones = [publicacion_to_dict(p) for p in publicaciones_db]
        
        resultado = innovador.generar_analisis_sesgos(publicaciones)
        return jsonify(resultado)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'exito': False, 'error': str(e)}), 500

@analisis_bp.route('/innovador/interpretar_sesgos', methods=['POST'])
@csrf.exempt
@login_required
def interpretar_sesgos_ia():
    try:
        from services.ai_service import AIService
        data = request.get_json() or {}
        chart_data = data.get('chart_data', {})
        modelo_ia = data.get('modelo', 'gemini-1.5-pro')
        
        prompt = (
            "Actúa como un experto en análisis crítico del discurso y estudios de género/sociales. "
            "A continuación te presento los resultados de un análisis de sesgos (conteo de términos por categorías) en un corpus:\n"
            f"{str(chart_data)}\n\n"
            "Realiza una interpretación crítica y pedagógica breve (2-3 párrafos en Markdown). "
            "Analiza las asimetrías detectadas (ej. Masculino vs Femenino, Elites vs Popular, Local vs Global). "
            "¿Qué nos dice esto sobre el punto de vista dominante del corpus y qué voces o realidades parecen estar marginadas o invisibilizadas?"
        )
            
        from flask_login import current_user
        # Usar AIService con fallback automático
        ai_service = AIService(model=modelo_ia, user=current_user)
        respuesta = ai_service.generate_content(prompt, temperature=0.7, auto_fallback=True)
        
        if respuesta and isinstance(respuesta, str):
            return jsonify({'exito': True, 'interpretacion': respuesta})
        else:
            error_msg = ai_service.last_error or "Error de comunicación con IA"
            print(f"[Gráficos Innovadores] Fallo IA: {error_msg}", file=sys.stderr)
            return jsonify({'exito': False, 'error': error_msg}), 500
    except Exception as e:
        return jsonify({'exito': False, 'error': str(e)}), 500

@analisis_bp.route('/dramatico/subtexto', methods=['POST'])
@csrf.exempt
@login_required
def analisis_subtexto_ia():
    """Analiza el subtexto y las intenciones dramáticas usando IA"""
    try:
        from services.ai_service import AIService
        data = request.get_json() or {}
        filtros = extraer_filtros(data)
        manual_aliases = data.get('manual_aliases', {})
        modelo_ia = data.get('modelo', 'gemini-1.5-pro')
        
        # Obtener documentos
        limite = filtros.pop('limite', 300)
        publicaciones_db = obtener_publicaciones_filtradas(**filtros, limit=limite if (limite and limite > 0) else None)
        
        if not publicaciones_db:
            return jsonify({'exito': False, 'error': 'No hay documentos para analizar'}), 400
            
        # Extraer una muestra representativa de diálogos
        # Para no saturar el prompt, tomamos fragmentos de los personajes principales
        reparto_muestra = {}
        for pub in publicaciones_db[:5]: # Máximo 5 documentos para contexto
            contenido = pub.contenido or ""
            # Limpieza básica
            texto = re.sub(r'<[^>]*?>', '', contenido)
            # Intentar detectar diálogos (NOMBRE: texto)
            lineas = texto.split('\n')
            for linea in lineas:
                match = re.match(r'^\s*([A-ZÁÉÍÓÚÑ ]+)\s*[:\.]\s*(.*)', linea)
                if match:
                    personaje = match.group(1).strip().upper()
                    # Ignorar acotaciones y nombres cortos
                    if len(personaje) > 2 and personaje not in ['ACTO', 'ESCENA', 'FIN']:
                        if personaje not in reparto_muestra:
                            reparto_muestra[personaje] = []
                        if len(reparto_muestra[personaje]) < 15: # Máximo 15 intervenciones por personaje
                            reparto_muestra[personaje].append(match.group(2).strip()[:200])

        # Consolidar data para el prompt
        dialogos_data = ""
        for p, d in reparto_muestra.items():
            dialogos_data += f"\nPERSONAJE: {p}\n"
            dialogos_data += "\n".join([f"- {i}" for i in d]) + "\n"

        if not dialogos_data:
            return jsonify({'exito': False, 'error': 'No se detectaron diálogos claros para el análisis de subtexto'}), 400

        prompt = f"""Actúa como un analista literario y experto en dramaturgia profesional. 
Analiza los siguientes diálogos de una obra teatral y clasifica las "Acciones Dramáticas" (tácticas) de cada personaje según su subtexto.

CATEGORÍAS DE ACCIÓN:
1. Persuadir/Convencer
2. Atacar/Confrontar
3. Seducir/Cortejar
4. Suplicar/Rogar
5. Defender/Justificar
6. Evadir/Huir
7. Manipular/Engañar
8. Informar/Exponer
9. Reflexionar/Dudar

DATOS DE DIÁLOGOS:
{dialogos_data}

Responde ÚNICAMENTE con un objeto JSON válido con el siguiente formato (sin bloques de código markdown, solo el JSON):
{{
  "personajes": {{
    "NOMBRE_PERSONAJE": {{
      "tacticas": {{ "Persuadir/Convencer": 30, "Atacar/Confrontar": 10, ... }},
      "resumen_estrategico": "Breve descripción de su meta",
      "evolucion": "Cómo cambia su táctica"
    }}
  }},
  "conflicto_dominante": "Choque de intenciones principal",
  "clima_escenico": "Tono general del subtexto",
  "evolucion_temporal": [
    {{ "acto": "I", "tactica": "Persuadir", "valor": 40 }},
    {{ "acto": "I", "tactica": "Atacar", "valor": 20 }},
    {{ "acto": "II", "tactica": "Manipular", "valor": 60 }},
    ...
  ]
}}
"""
        ai_service = AIService(model=modelo_ia, user=current_user)
        respuesta_raw = ai_service.generate_content(prompt, temperature=0.3)
        
        # Limpiar respuesta por si la IA añade markdown
        if "```json" in respuesta_raw:
            respuesta_raw = respuesta_raw.split("```json")[1].split("```")[0].strip()
        elif "```" in respuesta_raw:
            respuesta_raw = respuesta_raw.split("```")[1].split("```")[0].strip()
            
        try:
            resultado_ia = json.loads(respuesta_raw)
            
            # Generar Streamgraph si hay datos de evolución
            streamgraph_spec = None
            if resultado_ia.get('evolucion_temporal'):
                innovador = AnalisisInnovador()
                tema = request.args.get('theme', 'dark') # O usar cookie
                streamgraph_spec = innovador.generar_streamgraph_tactico(resultado_ia['evolucion_temporal'], theme=tema)
            
            resultado_ia['streamgraph_spec'] = streamgraph_spec
            return jsonify({'exito': True, 'analisis': resultado_ia})
        except Exception as e:
            print(f"[SUBTEXTO ERROR] Fallo al parsear JSON: {e}\nRespuesta: {respuesta_raw}")
            return jsonify({'exito': False, 'error': 'La IA no devolvió un formato válido', 'raw': respuesta_raw}), 500

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'exito': False, 'error': str(e)}), 500

@analisis_bp.route('/ping', methods=['GET'])
def ping_analisis():
    return jsonify({'mensaje': 'Blueprint analisis_avanzado activo'}), 200

@analisis_bp.route('/dramatico/interpretar', methods=['POST'])
@csrf.exempt
@login_required
def interpretar_dramatico_seccion():
    try:
        from services.ai_service import AIService
        data = request.get_json() or {}
        seccion = data.get('seccion', 'general')
        chart_data = data.get('chart_data', {})
        modelo_ia = data.get('modelo', 'gemini-1.5-pro')
        
        prompts = {
            'protagonismo': (
                "Actúa como un experto en teoría dramática y análisis literario. "
                "A continuación te presento los datos de 'Distribución de Protagonismo' (personaje y volumen de palabras) de una obra teatral:\n"
                f"{str(chart_data)}\n\n"
                "Realiza un análisis pormenorizado sobre la jerarquía discursiva. "
                "¿Quién domina la acción? ¿Hay personajes secundarios con un volumen sorprendentemente alto? "
                "¿Qué sugiere esto sobre la estructura de poder en la obra?"
            ),
            'reparto': (
                "Actúa como un experto en dramaturgia. Analiza este 'Desglose Analítico por Personaje' que incluye vocabulario dominante e intervenciones:\n"
                f"{str(chart_data)}\n\n"
                "Interpreta la caracterización de los personajes principales basándote en sus términos más frecuentes. "
                "¿Qué temas o rasgos psicológicos se desprenden de su léxico? "
                "Analiza la relación entre el número de intervenciones y la riqueza de su vocabulario."
            ),
            'tension': (
                "Actúa como un crítico teatral experto. Analiza la 'Cronología de la Tensión Dramática' (sentimiento bloque a bloque):\n"
                f"{str(chart_data)}\n\n"
                "Identifica los puntos de inflexión (clímax y anticlímax). "
                "¿Cómo evoluciona el flujo emocional de la obra? ¿Hay sorpresas o cambios bruscos de tono? "
                "Explica cómo esta curva de sentimiento estructura la experiencia del espectador."
            ),
            'interacciones': (
                "Actúa como un sociólogo de la literatura. Analiza esta 'Matriz de Interacciones' (co-ocurrencias entre personajes):\n"
                f"{str(chart_data)}\n\n"
                "Identifica los núcleos de poder y las redes de influencia. "
                "¿Qué personajes actúan como puentes? ¿Hay grupos aislados? "
                "¿Qué nos dice el mapa de calor sobre las relaciones sociales y el conflicto central?"
            ),
            'presencia': (
                "Actúa como un director de escena experto. Analiza esta 'Matriz de Presencia' (quién está en qué escena/acto):\n"
                f"{str(chart_data)}\n\n"
                "Interpreta el ritmo de la obra y la gestión del espacio. "
                "¿Hay escenas corales o predominan los diálogos íntimos? "
                "Analiza la estrategia de entradas y salidas y cómo afecta a la dinámica de la obra."
            ),
            'trayectoria': (
                "Actúa como un psicólogo y crítico teatral. Analiza la 'Trayectoria Emocional por Personaje' (arco de sentimiento de los protagonistas):\n"
                f"{str(chart_data)}\n\n"
                "Comenta las diferencias entre los arcos emocionales de los distintos personajes. "
                "¿Quién tiene la trayectoria más estable? ¿Quién sufre los cambios más erráticos? "
                "Explica cómo estas trayectorias individuales revelan los conflictos internos y la evolución de los personajes a lo largo de la pieza."
            ),
            'tactica_flujo': (
                "Actúa como un analista de tácticas dramáticas. Analiza el 'Flujo Táctico' de la obra (evolución de intenciones comunicativas):\n"
                f"{str(chart_data.get('metricas_avanzadas', {}).get('flujo_tactico', []))}\n\n"
                "Identifica las tácticas dominantes en cada acto (Atacar, Persuadir, Seducir, Manipular, Informar). "
                "¿Cómo cambia el 'juego de poder' a lo largo de la obra? ¿Hay una transición de la persuasión a la confrontación abierta? "
                "Explica qué revela este flujo táctico sobre la estrategia narrativa del autor."
            ),
            'ritmo': (
                "Actúa como un analista de ritmo teatral. Analiza las métricas de 'Ritmo Dramático' y sentimiento de 'Acotaciones':\n"
                f"{str(chart_data.get('metricas_avanzadas', {}).get('ritmo_bloques', []))}\n\n"
                "Interpreta la relación entre la velocidad de la acción (intervenciones) y el tono del autor (acotaciones). "
                "¿Hay momentos de estancamiento rítmico con alta carga emocional? ¿Cómo gestiona el autor el 'tempo' de la obra?"
            ),
            'sincronia': (
                "Actúa como un analista de dinámicas relacionales. Analiza la 'Sincronía Emocional' (Entrainment) entre personajes:\n"
                f"{str(chart_data.get('metricas_avanzadas', {}).get('sincronia_pares', []))}\n\n"
                "Identifica las parejas de personajes con mayor sintonía afectiva y aquellos con mayor disonancia. "
                "¿Qué sugiere esto sobre sus vínculos sociales? ¿Quiénes están 'en la misma onda' y quiénes están en conflicto irreconciliable?"
            )
        }
        
        prompt = prompts.get(seccion, "Analiza estos resultados de análisis dramático y proporciona una interpretación académica: " + str(chart_data))
            
        from flask_login import current_user
        # Usar AIService con el modelo solicitado y fallback automático
        import sys
        print(f"[Análisis Dramático] Iniciando interpretación con modelo {modelo_ia}...", file=sys.stderr)
        ai_service = AIService(model=modelo_ia, user=current_user)
        respuesta = ai_service.generate_content(prompt, temperature=0.7, auto_fallback=True)
        
        return jsonify({
            'exito': True,
            'interpretacion': respuesta
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'exito': False, 'error': str(e)})
def analisis_literario():
    """Endpoint para análisis literario profundo (Altair)"""
    try:
        data = request.get_json() or {}
        publicaciones_data = _obtener_publicaciones_filtradas(data)
        theme = data.get('theme', 'dark')
        
        if not publicaciones_data:
            return jsonify({'exito': False, 'error': 'No hay documentos para analizar'})
            
        # 1. Dispersión Léxica
        chart_dispersion = innovador.generar_dispersion_lexica(publicaciones_data, theme=theme)
        
        # 2. Arco de Sentimiento
        # Reutilizar el cálculo de sentimiento del Análisis Avanzado
        res_sentimiento = analisis.analisis_sentimiento_temporal(publicaciones_data, eje_x='secuencia')
        chart_arco = innovador.generar_arco_sentimiento(res_sentimiento.get('datos_individuales', []), theme=theme)
        
        # 3. Heatmap Estilístico
        res_estilo = analisis.analisis_estilometrico(publicaciones_data)
        chart_heatmap = innovador.generar_heatmap_estilistico(res_estilo.get('documentos', []), theme=theme)
        
        return jsonify({
            'exito': True,
            'charts': {
                'dispersion': chart_dispersion,
                'arco_sentimiento': chart_arco,
                'heatmap_estilo': chart_heatmap
            }
        })
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return jsonify({'exito': False, 'error': str(e)}), 500

def _obtener_publicaciones_filtradas(filtros):
    """Copia simplificada de la lógica de filtrado (debería centralizarse)"""
    from app import get_proyecto_activo
    proyecto = get_proyecto_activo()
    if not proyecto: return []
    
    query = Prensa.query.filter_by(proyecto_id=proyecto.id)
    
    # Aplicar filtros
    if filtros.get('tema'):
        query = query.filter(Prensa.tema == filtros['tema'])
    if filtros.get('publicacion_id'):
        query = query.filter(Prensa.id_publicacion == filtros['publicacion_id'])
    if filtros.get('pais'):
        query = query.filter(Prensa.pais_hemeroteca == filtros['pais'])
    if filtros.get('fecha_desde'):
        query = query.filter(Prensa.fecha_original >= filtros['fecha_desde'])
    if filtros.get('fecha_hasta'):
        query = query.filter(Prensa.fecha_original <= filtros['fecha_hasta'])
    
    # Límite
    limite = int(filtros.get('limite', 300))
    if limite > 0:
        query = query.limit(limite)
    
    pubs = query.all()
    
    return [{
        'id': p.id,
        'titulo': p.titulo,
        'contenido': p.contenido,
        'fecha': formatear_fecha_para_ui(p.fecha_original) if getattr(p, 'fecha_original', None) else None,
        'publicacion': p.id_publicacion
    } for p in pubs]


# ============================================
# CORPUS CHAT - RAG (Retrieval Augmented Generation)
# ============================================

@analisis_bp.route('/innovador/corpus_chat', methods=['POST'])
@csrf.exempt
@login_required
def corpus_chat():
    """
    Chat IA con el corpus usando RAG (Retrieval Augmented Generation)
    """
    import sys
    import logging
    import traceback
    
    # Usar el logger de la aplicación en lugar de configurar uno nuevo en pleno request
    logger = current_app.logger
    
    try:
        logger.info("=" * 40)
        logger.info("CORPUS_CHAT: Nueva solicitud recibida")
        
        # Obtener datos del request
        try:
            data = request.get_json() or {}
        except Exception as e:
            logger.error(f"Error parseando JSON: {e}")
            return jsonify({'exito': False, 'error': 'Formato JSON inválido'}), 400
            
        pregunta = data.get('pregunta', '').strip()
        modelo_ia = data.get('modelo', 'gemini-1.5-flash')
        temperatura = float(data.get('temperatura', 0.3))
        num_documentos = int(data.get('num_documentos', 5))
        
        if not pregunta:
            return jsonify({'exito': False, 'error': 'No se proporcionó ninguna pregunta'}), 400
        
        # Imports necesarios (dentro para evitar circulares)
        from services.embedding_service import EmbeddingService
        from services.ai_service import AIService
        from app import get_proyecto_activo
        from models import Proyecto, Prensa
        from flask import session
        
        # Obtener proyecto activo
        proyecto = get_proyecto_activo()
        
        if not proyecto:
            # Fallback a proyecto del usuario si no hay uno activo en sesión
            proyecto = Proyecto.query.filter_by(user_id=current_user.id).first()
            if not proyecto:
                # Fallback final a compartidos
                from models import ProyectoCompartido
                compartido = ProyectoCompartido.query.filter_by(usuario_id=current_user.id).first()
                if compartido:
                    proyecto = compartido.proyecto
            
            if not proyecto:
                return jsonify({'exito': False, 'error': 'No tienes ningún proyecto disponible.'}), 400
            
            # Autoselect
            session["proyecto_activo_id"] = proyecto.id
        
        logger.info(f"Corpus Chat - Proyecto: {proyecto.nombre} | Pregunta: {pregunta[:50]}...")
        
        # 1. Inicializar servicio de embeddings
        logger.info("[CORPUS_CHAT] Inicializando servicio de embeddings...")
        embedding_service = EmbeddingService(user=current_user)
        
        # 2. Buscar documentos con embeddings y aplicar filtros
        logger.info(f"[CORPUS_CHAT] Buscando documentos filtrados para proyecto ID {proyecto.id}...")
        
        # Extraer filtros del request (reutilizando la lógica centralizada)
        filtros = extraer_filtros(data)
        
        query = db.session.query(Prensa).filter(
            Prensa.proyecto_id == proyecto.id,
            Prensa.embedding_vector.isnot(None),
            Prensa.incluido == True
        )
        
        # Aplicar filtros adicionales si existen
        if filtros.get('tema'):
            query = query.filter(Prensa.temas == filtros['tema'])
        
        if filtros.get('publicacion_id'):
            try:
                pub_id = int(filtros['publicacion_id'])
                query = query.filter(Prensa.id_publicacion == pub_id)
            except (ValueError, TypeError):
                pass
                
        if filtros.get('pais'):
            query = query.filter(Prensa.pais_publicacion == filtros['pais'])
            
        if filtros.get('fecha_desde'):
            query = query.filter(text(f"({SQL_PRENSA_DATE}) >= :f_desde")).params(f_desde=filtros['fecha_desde'])
            
        if filtros.get('fecha_hasta'):
            query = query.filter(text(f"({SQL_PRENSA_DATE}) <= :f_hasta")).params(f_hasta=filtros['fecha_hasta'])

        documentos_candidatos = query.limit(2000).all()
        
        if not documentos_candidatos:
            return jsonify({
                'exito': False, 
                'error': 'No se encontraron documentos con embeddings que coincidan con los filtros seleccionados.',
                'ayuda': 'Prueba a relajar los filtros (fechas, temas, etc.) o asegúrate de haber generado los embeddings para este proyecto.'
            }), 404
        
        # 3. Detectar dimensión y modelo
        actual_dim = 0
        for doc in documentos_candidatos[:20]:
            emb = doc.embedding_vector
            if emb is None: continue
            
            # Robustez: Si es un string (JSON), lo cargamos
            if isinstance(emb, str):
                try:
                    import json
                    emb = json.loads(emb)
                except: continue
                
            actual_dim = len(emb) if isinstance(emb, (list, tuple)) else 0
            if actual_dim > 0:
                break
        
        if actual_dim == 0:
            return jsonify({'exito': False, 'error': 'Formato de embedding inválido en la base de datos (dimensión 0). Por favor, regenera los embeddings para este proyecto.'}), 500
            
        target_model = embedding_service.detect_model_from_dimension(actual_dim)
        if not target_model:
            # Fallback inteligente basado en dimensiones conocidas
            if actual_dim == 768: target_model = 'google'
            elif actual_dim == 1536: target_model = 'openai-small'
            elif actual_dim == 3072: target_model = 'openai-large'
            else: target_model = 'openai-small' # Fallback final
            
        logger.info(f"[CORPUS_CHAT] Dimensión detectada: {actual_dim}, Modelo: {target_model}")
            
        # 4. Generar embedding de la pregunta
        logger.info("[CORPUS_CHAT] Generando embedding de la pregunta...")
        query_embedding = None
        fallback_mode = None
        
        try:
            query_embedding = embedding_service.generate_query_embedding(pregunta, model=target_model)
        except Exception as api_err:
            error_msg = str(api_err)
            if "insufficient_quota" in error_msg.lower() or "quota" in error_msg.lower() or "429" in error_msg:
                # FALLBACK A BÚSQUEDA POR PALABRAS CLAVE
                logger.warning(f"[CORPUS_CHAT] Quota excedida para {target_model}. Iniciando fallback por palabras clave.")
                fallback_mode = "keyword"
            else:
                # Otros errores de API
                return jsonify({
                    'exito': False, 
                    'error': f'Error al generar embedding con {target_model}: {error_msg}'
                }), 500
        
        if not query_embedding and not fallback_mode:
            logger.warning(f"[CORPUS_CHAT] No se pudo generar query_embedding para {target_model}")
            return jsonify({'exito': False, 'error': f'La IA no pudo generar un vector para esta pregunta ({target_model})'}), 500
        
        # 5. Búsqueda y Top-K
        doc_scores = []
        
        if fallback_mode == "keyword":
            # Búsqueda tradicional por palabras clave (Emergencia)
            palabras = [p.strip() for p in pregunta.split() if len(p.strip()) > 3]
            if not palabras: 
                palabras = [p.strip() for p in pregunta.split() if p.strip()]
            
            # Construir filtros ILIKE (limitamos a las primeras 5 palabras para rendimiento)
            condiciones_texto = []
            for p in palabras[:5]:
                condiciones_texto.append(Prensa.contenido.ilike(f"%{p}%"))
                condiciones_texto.append(Prensa.titulo.ilike(f"%{p}%"))
            
            if condiciones_texto:
                # Re-ejecutar el query filtrado pero sin obligar a tener embedding
                query_fallback = db.session.query(Prensa).filter(
                    Prensa.proyecto_id == proyecto.id,
                    Prensa.incluido == True
                )
                
                # Aplicar los mismos filtros de metadatos
                if filtros.get('tema'): query_fallback = query_fallback.filter(Prensa.temas == filtros['tema'])
                if filtros.get('publicacion_id'):
                    try: query_fallback = query_fallback.filter(Prensa.id_publicacion == int(filtros['publicacion_id']))
                    except: pass
                if filtros.get('pais'): query_fallback = query_fallback.filter(Prensa.pais_publicacion == filtros['pais'])
                if filtros.get('fecha_desde'): query_fallback = query_fallback.filter(text(f"({SQL_PRENSA_DATE}) >= :f_desde")).params(f_desde=filtros['fecha_desde'])
                if filtros.get('fecha_hasta'): query_fallback = query_fallback.filter(text(f"({SQL_PRENSA_DATE}) <= :f_hasta")).params(f_hasta=filtros['fecha_hasta'])
                
                docs_encontrados = query_fallback.filter(or_(*condiciones_texto)).limit(num_documentos).all()
                doc_scores = [(d, 0.5) for d in docs_encontrados] # Score ficticio
        else:
            # Flujo normal: Similitud Coseno
            logger.info(f"[CORPUS_CHAT] Filtrando {len(documentos_candidatos)} candidatos...")
            documentos = []
            doc_embeddings = []
            for doc in documentos_candidatos:
                d_vec = doc.embedding_vector
                if d_vec is None: continue
                
                if isinstance(d_vec, str):
                    try:
                        import json
                        d_vec = json.loads(d_vec)
                    except: continue
                    
                if isinstance(d_vec, (list, tuple)) and len(d_vec) == len(query_embedding):
                    documentos.append(doc)
                    doc_embeddings.append(d_vec)
            
            if not documentos:
                return jsonify({'exito': False, 'error': 'No se encontraron documentos compatibles con la configuración de IA actual.'}), 422
            
            similitudes = embedding_service.batch_cosine_similarity(query_embedding, doc_embeddings)
            doc_scores = sorted(zip(documentos, similitudes), key=lambda x: x[1], reverse=True)[:num_documentos]
        
        if not doc_scores:
            return jsonify({'exito': False, 'error': 'No se encontraron documentos relevantes para tu pregunta con los filtros actuales.'}), 404
            
        # 6. Preparar contexto
        contexto_docs = []
        for doc, score in doc_scores:
            limit = 50000
            contenido = doc.contenido[:limit] if doc.contenido else ""
            contexto_docs.append(f"[ID: {doc.id}] {doc.titulo}\nCONTENIDO: {contenido}\n---")
        
        contexto_texto = "\n".join(contexto_docs)
        
        # 7. Generar respuesta con LLM
        prompt = f"""Responde la pregunta basándote en los documentos del corpus:
PREGUNTA: {pregunta}
DOCUMENTOS:
{contexto_texto}
Instrucciones: Cita por ID, sé conciso y fiel a los textos. Si no encuentras la respuesta, dilo."""
        
        logger.info(f"[CORPUS_CHAT] Generando respuesta con LLM ({modelo_ia})...")
        
        # Detectar proveedor basado en el nombre del modelo
        provider = 'gemini'
        if 'gpt' in modelo_ia.lower(): provider = 'openai'
        elif 'claude' in modelo_ia.lower(): provider = 'anthropic'
        
        ai_service = AIService(provider=provider, model=modelo_ia, user=current_user)
        # auto_fallback=True ya está por defecto en AIService.generate_content
        respuesta_ia = ai_service.generate_content(prompt, temperature=temperatura)
        
        if not respuesta_ia:
            logger.error("[CORPUS_CHAT] La IA no devolvió respuesta")
            return jsonify({'exito': False, 'error': 'La IA no pudo generar una respuesta.'}), 500
        
        logger.info("[CORPUS_CHAT] Respuesta generada con éxito")
        
        # 8. Respuesta final
        return jsonify({
            'exito': True,
            'respuesta': respuesta_ia.strip(),
            'fallback_mode': fallback_mode,
            'documentos_usados': [{
                'id': doc.id,
                'titulo': doc.titulo or "Sin título",
                'fecha': formatear_fecha_para_ui(doc.fecha_original),
                'similitud': round(score * 100, 1) if fallback_mode != 'keyword' else None,
                'url': f"/noticias/lector?id={doc.id}"
            } for doc, score in doc_scores],
            'metadata': {
                'modelo_ia': modelo_ia,
                'modelo_embedding': target_model if fallback_mode != 'keyword' else 'keyword_search'
            }
        })
        
    except Exception as e:
        logger.error(f"CORPUS_CHAT CRITICAL ERROR: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'exito': False, 'error': f"Error interno: {str(e)}"}), 500
