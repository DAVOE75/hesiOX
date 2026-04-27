# --- Habilitar PyMySQL como MySQLdb para SQLAlchemy ---
# Reload trigger
import pymysql
pymysql.install_as_MySQLdb()
# =========================================================
# FRECUENCIA NORMALIZADA (después de /analisis/frecuencia)
# =========================================================
import csv
import io
import json
import os
import re
from collections import Counter
from datetime import datetime
import time
import ast
from io import BytesIO
from itertools import combinations
from urllib.parse import parse_qs, unquote, urlencode, urlparse
from xml.sax.saxutils import escape as xml_escape

import networkx as nx
import numpy as np
from dotenv import load_dotenv

# =========================================================
# CARGA DE VARIABLES DE ENTORNO
# =========================================================
load_dotenv()  # Carga el archivo .env si existe

# Verificación de variables críticas
if not os.getenv("GEMINI_API_KEY"):
    print("[WARNING] GEMINI_API_KEY no detectada en el entorno.")
else:
    print("[DEBUG] GEMINI_API_KEY cargada correctamente.")

from flask import (
    Flask,
    Response,
    abort,
    flash,
    jsonify,
    make_response,
    redirect,
    render_template,
    request,
    send_file,
    send_from_directory,
    session,
    url_for,
)
from flask_login import (
    LoginManager,
    UserMixin,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from extensions import db, login_manager
from functools import wraps
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Importamos cast y String para solucionar el error de tipos en PostgreSQL
from sqlalchemy import String, Integer, cast, func, or_, and_, text

# 🔐 NUEVOS IMPORTS PARA USUARIOS Y LOGIN
from werkzeug.security import check_password_hash, generate_password_hash

# Importación para subida segura de archivos
from werkzeug.utils import secure_filename

# Asegúrate de haber instalado esta librería: pip install wordcloud
from wordcloud import WordCloud

# 🚀 IMPORTAR UTILIDADES OPTIMIZADAS
from utils import (
    QueryCache,
    cache,
    validar_fecha_ddmmyyyy,
    normalizar_texto,
    normalizar_next,
    levenshtein_distance,
    similitud_titulos,
    fechas_similares,
    separar_autor,
    capitalizar_palabra,
    formatear_autor_por_estilo,
    try_parse_fecha_ddmmyyyy,
    fecha_en_estilo,
    construir_paginas,
    STOPWORDS_ES,
    filtrar_palabras_significativas,
    formatear_fecha_para_ui,
    get_nlp,
)


# load_dotenv()  # Movido al inicio por orden de carga y visibilidad


app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB limit for layer uploads
app.config['TEMPLATES_AUTO_RELOAD'] = True  # Forzar recarga de templates
app.jinja_env.auto_reload = True
app.jinja_env.cache = None  # Deshabilitar caché de Jinja2 completamente (era {})

# ⚙️ CONFIGURACIÓN DE SEGURIDAD Y SESIÓN
app.config['WTF_CSRF_TIME_LIMIT'] = None                 # Eliminar límite de tiempo para CSRF
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'           # Mejorar estabilidad de cookies
if not os.getenv("FLASK_ENV") == "development":
    app.config['SESSION_COOKIE_SECURE'] = True          # Solo en producción (HTTPS)

# Redirecciones retrocompatibles para rutas antiguas del listado de noticias.
@app.route('/noticias/listar')
def redirect_noticias_listar():
    return redirect(url_for('noticias.listar', **request.args), code=302)

@app.route('/listados')
def redirect_listados():
    # Redirige a la ruta real del listado manteniendo los parámetros
    args = request.query_string.decode()
    # Mapea parámetros antiguos a los nuevos si es necesario
    # fecha -> fecha_original, keyword -> palabras_clave
    from urllib.parse import parse_qs, urlencode
    params = parse_qs(args)
    new_params = {}
    if 'fecha' in params:
        new_params['fecha_original'] = params['fecha'][0]
    if 'keyword' in params:
        new_params['palabras_clave'] = params['keyword'][0]
    # Añade otros parámetros si existen
    for k, v in params.items():
        if k not in ['fecha', 'keyword']:
            new_params[k] = v[0]
    url = url_for('noticias.listar')
    if new_params:
        url += '?' + urlencode(new_params)
    return redirect(url, code=302)

# Importar configuración de caché y inicializarla justo después de crear la app
from cache_config import cache, init_cache
init_cache(app)

# ⚙️ CONFIGURACIÓN DE SEGURIDAD
app.secret_key = os.getenv(
    "SECRET_KEY", "bibliografia_sirio_secret_CAMBIAR_EN_PRODUCCION"
)

# ⚙️ CONFIGURACIÓN DE BASE DE DATOS POSTGRESQL
# Usa variable de entorno DATABASE_URL, con fallback a valor por defecto

# --- CONFIGURACIÓN DE BASE DE DATOS POSTGRESQL Y POOL ---
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
    "DATABASE_URL", "postgresql://postgres:PASSWORD@localhost:5432/bibliografia_sirio"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
# Aumenta el tamaño del pool y el overflow para evitar TimeoutError
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_size": 20,
    "max_overflow": 30,
    "pool_timeout": 30,
    "pool_pre_ping": True,
}

# CONFIGURACIÓN DE CARPETA DE SUBIDAS (IMÁGENES)
UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", os.path.join("static", "uploads"))
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp", "txt", "pdf"}
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# Crear carpeta si no existe
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# =========================================================
# ENDPOINT: TOP 100 PALABRAS CLAVE PARA SUGERENCIAS (multi-select)
# =========================================================

@app.route("/api/keywords/top100")
def api_keywords_top100():
    try:
        from sqlalchemy import and_
        # Leer fechas de la query string
        inicio = request.args.get('inicio')
        fin = request.args.get('fin')
        palabras = []
        # Leer parámetro 'fields' (por defecto: contenido y titulo)
        fields_raw = request.args.get('fields', 'contenido,titulo')
        fields = [f.strip() for f in fields_raw.split(',') if f.strip() in ('contenido', 'titulo')]
        if not fields:
            fields = ['contenido', 'titulo']

        # Filtrar por proyecto activo
        from app import get_proyecto_activo
        proyecto = get_proyecto_activo()
        filtros = []
        if proyecto:
            filtros.append(Prensa.proyecto_id == proyecto.id)
        if inicio:
            filtros.append(Prensa.fecha >= inicio)
        if fin:
            filtros.append(Prensa.fecha <= fin)

        # 1. Palabras clave explícitas
        query_palabras = Prensa.query.with_entities(Prensa.palabras_clave)
        if filtros:
            query_palabras = query_palabras.filter(and_(*filtros))
        for ref in query_palabras.filter(Prensa.palabras_clave != None).all():
            if ref[0]:
                palabras += [p.strip().lower() for p in ref[0].split(',') if p.strip()]

        # 2. Palabras más frecuentes de los campos seleccionados
        query_textos = Prensa.query
        if filtros:
            query_textos = query_textos.filter(and_(*filtros))
        textos = []
        for ref in query_textos.limit(1000).all():
            texto = ' '.join([(getattr(ref, f, '') or '') for f in fields])
            textos.append(texto)
        print(f"[DEBUG] Textos procesados para top keywords (fields={fields}): {len(textos)}")
        from sklearn.feature_extraction.text import CountVectorizer
        from utils import STOPWORDS_ES
        vectorizer = CountVectorizer(max_features=100, stop_words=list(STOPWORDS_ES), token_pattern=r"\b[a-záéíóúüñ]{3,}\b")
        if textos:
            X = vectorizer.fit_transform(textos)
            palabras_frecuentes = vectorizer.get_feature_names_out()
            # Obtener frecuencias reales
            freqs = X.sum(axis=0).A1
            palabras_con_frecuencia = list(zip(palabras_frecuentes, freqs))
            palabras_con_frecuencia.sort(key=lambda x: x[1], reverse=True)
            palabras_ordenadas = [p for p, f in palabras_con_frecuencia]
            print(f"[DEBUG] Palabras frecuentes extraídas (orden real): {palabras_ordenadas}")
            palabras += palabras_ordenadas
        # Quitar duplicados y limpiar, pero mantener el orden de frecuencia
        palabras = [p for p in palabras if len(p) > 2]
        palabras = list(dict.fromkeys(palabras))
        print(f"[DEBUG] Palabras finales para selector: {palabras[:30]}")
        return jsonify({"success": True, "keywords": palabras[:100]})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


# =========================================================
# ENDPOINT LEGACY DESHABILITADO: DISTRIBUCIÓN TEMPORAL AVANZADA (referencias/keywords)
# =========================================================
# @app.route("/api/distribucion-temporal")
# def api_distribucion_temporal():
#     try:
#         tipo = request.args.get('tipo', 'referencias')
#         inicio = request.args.get('inicio')
#         fin = request.args.get('fin')
#         palabras = request.args.get('palabras', '')
#         palabras = [p.strip().lower() for p in palabras.split(',') if p.strip()] if palabras else []
#
#         # Filtrar por fechas
#         query = Prensa.query
#         if inicio:
#             query = query.filter(Prensa.fecha_original >= inicio)
#         if fin:
#             query = query.filter(Prensa.fecha_original <= fin)
#         referencias = query.all()
#
#         # Eje X: años presentes en el corpus filtrado
#         anios = sorted(set([r.anio for r in referencias if r.anio]))
#         labels = [str(a) for a in anios]
#
#         if tipo == 'referencias':
#             # Serie: número de referencias por año
#             conteo = {str(a): 0 for a in anios}
#             for r in referencias:
#                 if r.anio:
#                     conteo[str(r.anio)] += 1
#             series = [conteo[str(a)] for a in anios]
#             return jsonify({"success": True, "labels": labels, "series": series})
#
#         elif tipo == 'palabras' and palabras:
#             # Serie: frecuencia de cada palabra por año
#             series = []
#             colores = ['#ff9800', '#03a9f4', '#4caf50', '#e91e63', '#9c27b0', '#ffc107', '#009688', '#f44336', '#607d8b', '#8bc34a']
#             for idx, palabra in enumerate(palabras):
#                 conteo = {str(a): 0 for a in anios}
#                 for r in referencias:
#                     texto = ((r.contenido or '') + ' ' + (r.titulo or '')).lower()
#                     if r.anio and palabra in texto:
#                         conteo[str(r.anio)] += texto.count(palabra)
#                 series.append({
#                     "label": palabra,
#                     "data": [conteo[str(a)] for a in anios],
#                     "color": colores[idx % len(colores)]
#                 })
#             return jsonify({"success": True, "labels": labels, "series": series})
#
#         else:
#             return jsonify({"success": False, "error": "Tipo o palabras no válidas"})
#     except Exception as e:
#         return jsonify({"success": False, "error": str(e)})

# =========================================================
# INICIALIZACIÓN DE EXTENSIONES
# =========================================================
from extensions import db, csrf

db.init_app(app)

csrf.init_app(app)

# Inicializar Flask-Migrate para habilitar comandos flask db
from flask_migrate import Migrate
migrate = Migrate(app, db)

# Eximir CSRF para todas las rutas que empiecen por /api/
@app.before_request
def eximir_csrf_api():
    if request.path.startswith('/api/') or request.path.startswith('/pasajeros/api/') or request.path.startswith('/barco/api/'):
        setattr(request, '_disable_csrf', True)

## La instancia de db se importa desde extensions.py
# y se inicializa con db.init_app(app) para evitar importaciones circulares

# Importar modelos DESPUÉS de inicializar db


from models import (
    Usuario, Proyecto, Hemeroteca, Publicacion, Prensa, 
    ImagenPrensa, GeoPlace, ServicioIDE, VectorLayer, SQL_PRENSA_DATE,
    BlogPost, BlogSubscription, AutorBio, Ciudad, MetadataOption
)

# 🔐 Configuración de Flask-Login
login_manager.init_app(app)
login_manager.login_view = "login"  # nombre de la ruta de login

# Handler para peticiones no autorizadas: devolver JSON en APIs, redirect en vistas
@login_manager.unauthorized_handler
def unauthorized():
    # Si es una petición a una API (comienza con /api/), devolver JSON
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Autenticación requerida', 'authenticated': False}), 401
    # Si es una vista normal, redirigir a login
    return redirect(url_for('login'))


# =========================================================
# FILTROS PERSONALIZADOS DE JINJA
# =========================================================
@app.template_filter('from_json')
def from_json_filter(value):
    """Parsear JSON string a objeto Python"""
    if not value:
        return []
    try:
        return json.loads(value)
    except:
        return []


@app.template_filter('country_flag')
def country_flag_filter(country_name):
    """Convierte nombre de país a código ISO de 2 letras para flag-icon-css"""
    from utils import get_country_code
    return get_country_code(country_name)


@login_manager.user_loader
def load_user(user_id):
    """Función que carga un usuario desde su ID almacenado en la sesión"""
    # No necesitamos import, Usuario ya está definido en este archivo
    return db.session.get(Usuario, int(user_id))


# =========================================================
# DECORADORES DE SEGURIDAD
# =========================================================


def admin_required(f):
    """
    Decorador que restringe el acceso solo a usuarios administradores.
    
    Uso:
        @app.route('/admin')
        @login_required
        @admin_required
        def admin_panel():
            ...
    
    Nota: Este decorador DEBE usarse DESPUÉS de @login_required
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash("Debes iniciar sesión para acceder a esta página.", "warning")
            return redirect(url_for("login"))
        
        if current_user.rol != "admin":
            flash("No tienes permisos para acceder al panel de administración.", "danger")
            return redirect(url_for("dashboard"))
        
        return f(*args, **kwargs)
    
    return decorated_function


# =========================================================
# FUNCIONES AUXILIARES
# =========================================================


# Función auxiliar para validar imágenes
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# Función auxiliar para validar imágenes
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# =========================================================
# =========================================================
# MODELOS DE DATOS
# =========================================================
# Los modelos ahora están definidos en models.py para evitar importaciones circulares
# Ya fueron importados anteriormente con: from models import ...
#
# Las clases originales (Usuario, Proyecto, Hemeroteca, Publicacion, Prensa, ImagenPrensa)
# han sido comentadas para evitar duplicaciones.


# FUNCIONES AUXILIARES ESPECÍFICAS DE LA APLICACIÓN
# =========================================================
def valores_unicos(columna, proyecto_id=None):
    """
    Obtiene valores únicos de una columna con normalización y ordenamiento.
    Opcionalmente filtra por proyecto.
    OPTIMIZACIÓN: Usa caché para consultas frecuentes
    """
    # Generar clave de caché
    cache_key = f"valores_unicos_{columna.name}_{proyecto_id}"
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        return cached_result
    
    # Construir query con filtro opcional de proyecto
    query = db.session.query(columna).distinct()
    if proyecto_id and hasattr(columna.table.c, 'proyecto_id'):
        query = query.filter(columna.table.c.proyecto_id == proyecto_id)
    
    valores_db = [
        x[0]
        for x in query.all()
        if x[0] and str(x[0]).strip()
    ]
    
    unicos = {}
    is_temas = (columna.name == "temas")
    
    for v in valores_db:
        texto_raw = str(v).strip()
        if is_temas:
            # Separar por comas para temas
            sub_partes = [p.strip() for p in texto_raw.split(',') if p.strip()]
        else:
            sub_partes = [texto_raw]
            
        for texto in sub_partes:
            clave = texto.lower()
            if clave not in unicos or (
                texto[0].isupper() and not unicos[clave][0].isupper()
            ):
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
    
    # Guardar en caché
    cache.set(cache_key, valores_limpios)
    return valores_limpios


def ordenar_por_fecha(query, descendente=False):
    # Protección contra fechas inválidas en BD (ej: 15/13/1908)
    # Usa split_part para extraer día/mes/año y validar ANTES de to_date
    orden_sql = text(f"""
                CASE
                    WHEN fecha_original ~ '^[0-3]?[0-9]/[0-1]?[0-9]/[0-9]{2,4}$' THEN to_date(fecha_original, 'DD/MM/YYYY')
                    WHEN fecha_original ~ '^[0-9]{4}-[0-1]?[0-9]-[0-3]?[0-9]$' THEN to_date(fecha_original, 'YYYY-MM-DD')
                    ELSE NULL
                END {"DESC" if descendente else "ASC"} NULLS LAST,
        publicacion ASC
    """)
    return query.order_by(orden_sql)


# =========================================================
# CONTEXT PROCESSOR: VARIABLES GLOBALES EN TEMPLATES
# =========================================================
@app.context_processor
def inject_proyecto_activo():
    """Inyecta el proyecto activo en todos los templates"""
    proyecto = get_proyecto_activo()
    return dict(proyecto_activo=proyecto)


# =========================================================
# REGISTRO DE BLUEPRINTS (MODULOS SEPARADOS)
# =========================================================

# Importar blueprints justo antes de registrarlos para evitar importación circular
from routes import all_blueprints
for blueprint in all_blueprints:
    app.register_blueprint(blueprint)
    print(f"[DEBUG] Blueprint registrado: {blueprint.name} (url_prefix={getattr(blueprint, 'url_prefix', None)})")
print("[OK] Blueprints registrados:", [bp.name for bp in all_blueprints])

# Mostrar todas las rutas registradas
with app.app_context():
    print("[DEBUG] Rutas registradas:")
    for rule in app.url_map.iter_rules():
        print(f"  {rule.methods} {rule}")





@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static', 'img'),
                               'hesiox_logo2.png', mimetype='image/vnd.microsoft.icon')


@app.route("/")
def home():
    """Página principal - redirige a dashboard si está logueado"""
    if current_user.is_authenticated:
        return redirect(url_for("auth.perfil"))
    return render_template("home.html")


@app.route("/manual")
@login_required
def manual():
    """Vista del Manual de Usuario (La Biblia de HesiOX)"""
    # Temporarily changed pdf_mode to True for AG diagnostic
    return render_template("manual.html", pdf_mode=False)


@app.route("/manual/pdf")
@login_required
def manual_pdf():
    """Generar PDF de La Biblia de HesiOX usando WeasyPrint"""
    from weasyprint import HTML
    
    # Renderizar HTML con modo PDF activado
    html_content = render_template("manual.html", pdf_mode=True)
    
    try:
        # Generar PDF usando WeasyPrint (soporta CSS @page y contadores)
        pdf = HTML(string=html_content).write_pdf()
        
        response = make_response(pdf)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'inline; filename=Hesiox_Biblia_v4.1.0_A4.pdf'
        return response
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error generando PDF (WeasyPrint): {e}\n{error_details}")
        return f"Error generando PDF: {str(e)}", 500


@app.route("/guia-contenido")
@login_required
def guia_contenido():
    """Vista de la Guía de Uso de Contenido"""
    return render_template("content_guide.html")


@app.route("/dashboard")
@login_required
def dashboard():
    """Dashboard personalizado del usuario con estadísticas y accesos rápidos"""
    from utils import load_config
    system_config = load_config()
    
    # Obtener proyectos del usuario
    proyectos = Proyecto.query.filter_by(user_id=current_user.id).all()
    total_proyectos = len(proyectos)
    
    # Proyecto activo
    proyecto_activo = get_proyecto_activo()
    proyecto_activo_nombre = proyecto_activo.nombre if proyecto_activo else "Ninguno"
    
    # Estadísticas generales (todos los proyectos del usuario)
    total_articulos = 0
    total_publicaciones = 0
    articulos_esta_semana = 0
    
    for proyecto in proyectos:
        # Contar artículos de prensa
        articulos = Prensa.query.filter_by(proyecto_id=proyecto.id).all()
        total_articulos += len(articulos)
        
        # Contar publicaciones académicas
        publicaciones = Publicacion.query.filter_by(proyecto_id=proyecto.id).count()
        total_publicaciones += publicaciones
    
    # Artículos de esta semana (simplificado - últimos 7)
    articulos_esta_semana = min(7, total_articulos)
    
    # Actividad reciente (últimas 10 acciones del usuario)
    actividad_reciente = []
    
    # 1. Obtener actividad de la base de datos (Últimos artículos añadidos)
    try:
        ultimos_articulos = Prensa.query.join(Proyecto).filter(
            Proyecto.user_id == current_user.id
        ).order_by(Prensa.creado_en.desc()).limit(5).all()
        
        for articulo in ultimos_articulos:
            actividad_reciente.append({
                "tipo": "articulo_nuevo",
                "icono": "fa-file-lines",
                "texto": f"Noticia añadida: \"{(articulo.titulo or 'Sin título')[:50]}...\"",
                "fecha": articulo.creado_en or datetime(1970, 1, 1),
                "url": url_for("noticias.editar", id=articulo.id)
            })
    except Exception as e:
        print(f"[ERROR] No se pudo obtener artículos recientes: {e}")

    # 2. Leer logs de seguridad (últimas 50 líneas)
    try:
        log_path = os.path.join(app.root_path, 'logs', 'security.log')
        if os.path.exists(log_path):
            with open(log_path, 'r', encoding='utf-8') as f:
                # Leer últimas líneas de forma eficiente
                content = f.readlines()
                for line in content[-50:]:
                    if current_user.email in line and "Login exitoso" in line:
                        # Formato esperado: 2026-02-09 12:20:07 - security - INFO - [ip] - Mensaje
                        parts = line.split(' - ')
                        if len(parts) >= 5:
                            timestamp_str = parts[0]
                            # Intentar parsear fecha
                            try:
                                dt = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                            except:
                                continue
                                
                            # Mapear mensajes a iconos y textos amigables
                            icon = "fa-right-to-bracket"
                            text_msg = "Inicio de sesión"
                            
                            actividad_reciente.append({
                                "tipo": "login",
                                "icono": icon,
                                "texto": text_msg,
                                "fecha": dt,
                                "url": "#"
                            })
    except Exception as e:
        print(f"[ERROR] No se pudo leer el log de seguridad: {e}")
        
    # 3. Entradas manuales de refinamiento de sistema
    actividad_reciente.append({
        "tipo": "sistema",
        "icono": "fa-wand-magic-sparkles",
        "texto": "Refinamiento de interfaz: Controles NLP y Modo Claro.",
        "fecha": datetime.now(),
        "url": url_for("analisis_avanzado.analisis_hd")
    })
    
    actividad_reciente.append({
        "tipo": "sistema",
        "icono": "fa-shield-halved",
        "texto": "Módulo de Seguridad: Auditoría de accesos completada.",
        "fecha": datetime.now(),
        "url": "#"
    })

    actividad_reciente.append({
        "tipo": "sistema",
        "icono": "fa-bolt",
        "texto": "Optimización de motor: Indexación de documentos acelerada.",
        "fecha": datetime.now(),
        "url": "#"
    })
        
    # Función auxiliar para normalizar fechas para el sort
    def normalizar_fecha_actividad(v):
        try:
            if not v:
                return datetime(1970, 1, 1)
            if isinstance(v, datetime):
                return v
            if isinstance(v, str):
                # Intentar varios formatos comunes
                for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M:%S.%f', '%d/%m/%Y %H:%M:%S', '%Y-%m-%d'):
                    try:
                        return datetime.strptime(v, fmt)
                    except:
                        continue
            # Si es date pero no datetime
            if hasattr(v, 'year') and not hasattr(v, 'hour'):
                return datetime.combine(v, datetime.min.time())
        except Exception as e:
            # Silencio en producción o log a archivo
            pass
        return datetime(1970, 1, 1)

    # Normalizar todas las fechas primero
    for item in actividad_reciente:
        item['fecha'] = normalizar_fecha_actividad(item.get('fecha'))

    # Ordenar por fecha descendente
    try:
        actividad_reciente.sort(key=lambda x: x['fecha'], reverse=True)
    except Exception:
        # Último recurso: no ordenar
        pass
    
    # Limitar a 12 items
    actividad_reciente = actividad_reciente[:12]
    
    # Estadísticas rápidas del proyecto activo
    stats_proyecto_activo = None
    if proyecto_activo:
        articulos_proyecto = Prensa.query.filter_by(proyecto_id=proyecto_activo.id).count()
        publicaciones_proyecto = Publicacion.query.filter_by(proyecto_id=proyecto_activo.id).count()
        hemerotecas_proyecto = Hemeroteca.query.filter_by(proyecto_id=proyecto_activo.id).count()
        
        stats_proyecto_activo = {
            "articulos": articulos_proyecto,
            "publicaciones": publicaciones_proyecto,
            "hemerotecas": hemerotecas_proyecto
        }
    
    # Top 5 publicaciones más citadas (del proyecto activo)
    top_periodicos = []
    if proyecto_activo:
        from sqlalchemy import func
        top_periodicos = db.session.query(
            Prensa.publicacion,
            func.count(Prensa.id).label('total')
        ).filter(
            Prensa.proyecto_id == proyecto_activo.id,
            Prensa.publicacion.isnot(None),
            Prensa.publicacion != ''
        ).group_by(Prensa.publicacion).order_by(func.count(Prensa.id).desc()).limit(5).all()
    
    return render_template("dashboard.html",
                         total_proyectos=total_proyectos,
                         total_articulos=total_articulos,
                         total_publicaciones=total_publicaciones,
                         articulos_esta_semana=articulos_esta_semana,
                         proyecto_activo_nombre=proyecto_activo_nombre,
                         actividad_reciente=actividad_reciente,
                         stats_proyecto_activo=stats_proyecto_activo,
                         top_periodicos=top_periodicos,
                         proyectos=proyectos,
                         proyecto_id=proyecto_activo.id if proyecto_activo else None,
                         system_config=system_config)

@app.route('/api/admin/config', methods=['POST'])
@login_required
def api_admin_config():
    """Endpoint para actualizar configuración del sistema"""
    from utils import save_config
    if request.method == 'POST':
        try:
            data = request.json
            new_config = {}
            
            if 'spacy_model' in data:
                if data['spacy_model'] in ['es_core_news_sm', 'es_core_news_md', 'es_core_news_lg']:
                    new_config['spacy_model'] = data['spacy_model']
            
            if 'max_char_limit' in data:
                try:
                    limit = int(data['max_char_limit'])
                    if 1000 <= limit <= 100000:
                        new_config['max_char_limit'] = limit
                except ValueError:
                    pass
                    
            if new_config:
                if save_config(new_config):
                    return jsonify({'success': True, 'message': 'Configuración actualizada correctamente.'})
                else:
                    return jsonify({'success': False, 'error': 'Error guardando archivo de configuración.'}), 500
            else:
                 return jsonify({'success': False, 'error': 'No se enviaron datos válidos.'}), 400
                 
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    return jsonify({'success': False, 'error': 'Método no permitido'}), 405





@app.route("/admin")
@login_required
@admin_required
def admin_panel():
    """
    Panel de Administración Técnica
    
    Enfocado en mantenimiento del sistema SIN acceso a contenidos académicos.
    Respeta la privacidad de la investigación.
    """
    import psutil
    import platform
    from datetime import timedelta
    
    # ===== ESTADÍSTICAS GLOBALES (ANÓNIMAS) =====
    total_usuarios = Usuario.query.count()
    total_proyectos = Proyecto.query.count()
    total_articulos = Prensa.query.count()
    total_publicaciones = Publicacion.query.count()
    total_hemerotecas = Hemeroteca.query.count()
    
    # ===== MONITOREO DEL SISTEMA =====
    # Uso de disco
    disk = psutil.disk_usage('/')
    disk_total_gb = disk.total / (1024**3)
    disk_usado_gb = disk.used / (1024**3)
    disk_libre_gb = disk.free / (1024**3)
    disk_porcentaje = disk.percent
    
    # Calcular tamaño de uploads/ (PDFs, imágenes OCR)
    uploads_path = os.path.join(app.config['UPLOAD_FOLDER'])
    uploads_size_mb = 0
    if os.path.exists(uploads_path):
        for dirpath, dirnames, filenames in os.walk(uploads_path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                if os.path.exists(fp):
                    uploads_size_mb += os.path.getsize(fp)
        uploads_size_mb = uploads_size_mb / (1024**2)  # Convertir a MB
    
    # Tamaño de la base de datos (estimación por recuento de registros)
    db_stats = {
        'articulos': total_articulos,
        'publicaciones': total_publicaciones,
        'proyectos': total_proyectos,
        'hemerotecas': total_hemerotecas,
        'usuarios': total_usuarios
    }
    
    # RAM y CPU
    memoria = psutil.virtual_memory()
    ram_total_gb = memoria.total / (1024**3)
    ram_usado_gb = memoria.used / (1024**3)
    ram_porcentaje = memoria.percent
    cpu_porcentaje = psutil.cpu_percent(interval=1)
    
    # Uptime del sistema
    boot_time = datetime.fromtimestamp(psutil.boot_time())
    uptime = datetime.now() - boot_time
    uptime_str = f"{uptime.days}d {uptime.seconds//3600}h {(uptime.seconds//60)%60}m"
    
    # Info del sistema
    sistema_info = {
        'os': platform.system(),
        'version': platform.version(),
        'python': platform.python_version(),
        'procesador': platform.processor()
    }
    
    # ===== GESTIÓN DE USUARIOS (SOLO DATOS BÁSICOS) =====
    usuarios_lista = Usuario.query.order_by(Usuario.creado_en.desc()).all()
    usuarios_data = []
    for u in usuarios_lista:
        # Contar proyectos del usuario (sin ver contenido)
        num_proyectos = Proyecto.query.filter_by(user_id=u.id).count()
        
        usuarios_data.append({
            'id': u.id,
            'nombre': u.nombre,
            'email': u.email,
            'creado_en': u.creado_en,
            'rol': u.rol,
            'activo': u.activo,
            'num_proyectos': num_proyectos
        })
    
    # ===== ACTIVIDAD RECIENTE DEL SISTEMA (ANÓNIMA) =====
    # Últimos usuarios registrados (solo fechas, sin datos personales)
    usuarios_recientes = Usuario.query.order_by(Usuario.creado_en.desc()).limit(4).all()
    actividad_sistema = []
    
    for u in usuarios_recientes:
        actividad_sistema.append({
            'tipo': 'Nuevo usuario',
            'fecha': u.creado_en,
            'icono': '👤',
            'descripcion': f'Usuario registrado'
        })
    
    # Últimos proyectos creados (sin ver contenido, solo fechas)
    proyectos_recientes = Proyecto.query.order_by(Proyecto.creado_en.desc()).limit(4).all()
    for p in proyectos_recientes:
        actividad_sistema.append({
            'tipo': 'Nuevo proyecto',
            'fecha': p.creado_en,
            'icono': '📁',
            'descripcion': f'Proyecto creado'
        })
    
    # Ordenar por fecha descendente y limitar a 8 items
    actividad_sistema = sorted(actividad_sistema, key=lambda x: x['fecha'], reverse=True)[:8]
    
    # ===== GESTIÓN DE BACKUPS =====
    ultimo_backup = None
    backup_dir = os.path.join(app.root_path, 'db_backups')
    if os.path.exists(backup_dir):
        files = [os.path.join(backup_dir, f) for f in os.listdir(backup_dir) if f.endswith('.sql')]
        if files:
            latest_file = max(files, key=os.path.getmtime)
            ultimo_backup = datetime.fromtimestamp(os.path.getmtime(latest_file))
    
    # ===== GESTIÓN DE PROYECTOS =====
    proyectos_lista = Proyecto.query.order_by(Proyecto.creado_en.desc()).all()
    
    # ===== UBICACIONES PENDIENTES =====
    geo_pendientes = GeoPlace.query.filter(GeoPlace.status.in_(['PENDING', 'NOT_FOUND'])).order_by(GeoPlace.created_at.desc()).all()
    
    # ===== GESTIÓN DE IDE (WMS/WMTS) =====
    ide_servicios = ServicioIDE.query.order_by(ServicioIDE.pais, ServicioIDE.nombre).all()
    
    # ===== ESTADÍSTICAS DE EMBEDDINGS =====
    total_docs_global = Prensa.query.filter_by(incluido=True).count()
    docs_con_embeddings_global = Prensa.query.filter(
        Prensa.incluido == True,
        Prensa.embedding_vector.isnot(None)
    ).count()
    docs_sin_embeddings_global = total_docs_global - docs_con_embeddings_global
    porcentaje_embeddings_global = (docs_con_embeddings_global / total_docs_global * 100) if total_docs_global > 0 else 0
    # ===== ESTADÍSTICAS DEL BLOG =====
    total_blog_posts = BlogPost.query.count()
    blog_publicados = BlogPost.query.filter_by(publicado=True).count()
    blog_borradores = total_blog_posts - blog_publicados
    blog_vistas = db.session.query(func.sum(BlogPost.vistas)).scalar() or 0
    
    blog_stats = {
        'total': total_blog_posts,
        'publicados': blog_publicados,
        'borradores': blog_borradores,
        'vistas': blog_vistas
    }
    
    return render_template("admin_panel.html",
                          blog_stats=blog_stats,
                          # Estadísticas globales
                          total_usuarios=total_usuarios,
                          total_proyectos=total_proyectos,
                          total_articulos=total_articulos,
                          total_publicaciones=total_publicaciones,
                          total_hemerotecas=total_hemerotecas,
                          # Monitoreo sistema
                          disk_total_gb=round(disk_total_gb, 2),
                          disk_usado_gb=round(disk_usado_gb, 2),
                          disk_libre_gb=round(disk_libre_gb, 2),
                          disk_porcentaje=disk_porcentaje,
                          uploads_size_mb=round(uploads_size_mb, 2),
                          ram_total_gb=round(ram_total_gb, 2),
                          ram_usado_gb=round(ram_usado_gb, 2),
                          ram_porcentaje=ram_porcentaje,
                          cpu_porcentaje=cpu_porcentaje,
                          uptime=uptime_str,
                          sistema_info=sistema_info,
                          db_stats=db_stats,
                          ultimo_backup=ultimo_backup,
                          # Gestión usuarios
                          usuarios=usuarios_data,
                          # Gestión proyectos
                          proyectos_lista=proyectos_lista,
                          # Ubicaciones pendientes
                          geo_pendientes=geo_pendientes,
                          # Actividad
                          actividad_sistema=actividad_sistema,
                          # Gestión IDE
                          ide_servicios=ide_servicios,
                          # Estadísticas embeddings
                          total_docs_global=total_docs_global,
                          docs_con_embeddings_global=docs_con_embeddings_global,
                          docs_sin_embeddings_global=docs_sin_embeddings_global,
                          porcentaje_embeddings_global=porcentaje_embeddings_global)


@app.route("/admin/usuario/<int:user_id>/toggle", methods=["POST"])
@login_required
@admin_required
def admin_toggle_usuario(user_id):
    """Activar/desactivar cuenta de usuario (suspensión técnica)"""
    usuario = Usuario.query.get_or_404(user_id)
    
    # No permitir desactivar al propio admin
    if usuario.id == current_user.id:
        flash("No puedes desactivar tu propia cuenta.", "warning")
        return redirect(url_for("admin_panel"))
    
    usuario.activo = not usuario.activo
    db.session.commit()
    
    estado = "activada" if usuario.activo else "desactivada"
    flash(f"Cuenta de {usuario.nombre} {estado} correctamente.", "success")
    return redirect(url_for("admin_panel"))


@app.route("/admin/usuario/<int:user_id>/rol", methods=["POST"])
@login_required
@admin_required
def admin_cambiar_rol(user_id):
    """Cambiar rol de usuario (admin/user)"""
    usuario = Usuario.query.get_or_404(user_id)
    
    # No permitir cambiar el propio rol
    if usuario.id == current_user.id:
        flash("No puedes cambiar tu propio rol.", "warning")
        return redirect(url_for("admin_panel"))
    
    nuevo_rol = request.form.get("rol")
    if nuevo_rol not in ["admin", "user"]:
        flash("Rol inválido.", "danger")
        return redirect(url_for("admin_panel"))
    
    usuario.rol = nuevo_rol
    db.session.commit()
    
    flash(f"Rol de {usuario.nombre} actualizado a '{nuevo_rol}'.", "success")
    return redirect(url_for("admin_panel"))


@app.route("/admin/usuario/<int:user_id>/delete", methods=["POST"])
@login_required
@admin_required
def admin_delete_usuario(user_id):
    """Eliminar usuario permanentemente"""
    usuario = Usuario.query.get_or_404(user_id)
    
    # No permitir eliminar la propia cuenta
    if usuario.id == current_user.id:
        flash("No puedes eliminar tu propia cuenta.", "warning")
        return redirect(url_for("admin_panel"))
    
    nombre_usuario = usuario.nombre
    
    try:
        # Eliminar usuario (las referencias en cascada se manejan en el modelo)
        db.session.delete(usuario)
        db.session.commit()
        flash(f"Usuario '{nombre_usuario}' eliminado permanentemente.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error al eliminar usuario: {str(e)}", "danger")
    
    return redirect(url_for("admin_panel"))


@app.route("/admin/ide/<int:ide_id>/update", methods=["POST"])
@login_required
@admin_required
def admin_ide_update(ide_id):
    """Actualizar campos de un servicio IDE"""
    srv = ServicioIDE.query.get_or_404(ide_id)
    
    try:
        srv.nombre = request.form.get("nombre", srv.nombre)
        srv.tipo = request.form.get("tipo", srv.tipo)
        srv.url = request.form.get("url", srv.url)
        srv.capas = request.form.get("capas", srv.capas)
        srv.formato = request.form.get("formato", srv.formato)
        srv.attribution = request.form.get("attribution", srv.attribution)
        srv.pais = request.form.get("pais", srv.pais)
        srv.categoria = request.form.get("categoria", srv.categoria)
        
        opacidad = request.form.get("opacidad")
        if opacidad:
            srv.opacidad = float(opacidad)
            
        db.session.commit()
        flash(f"Servicio IDE '{srv.nombre}' actualizado correctamente.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error al actualizar servicio IDE: {str(e)}", "danger")
        
    return redirect(url_for("admin_panel"))


@app.route("/admin/ide/<int:ide_id>/delete", methods=["POST"])
@login_required
@admin_required
def admin_ide_delete(ide_id):
    """Eliminar servicio IDE del catálogo global"""
    srv = ServicioIDE.query.get_or_404(ide_id)
    nombre = srv.nombre
    
    try:
        db.session.delete(srv)
        db.session.commit()
        flash(f"Servicio IDE '{nombre}' eliminado correctamente.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error al eliminar servicio IDE: {str(e)}", "danger")
        
    return redirect(url_for("admin_panel"))


@app.route("/admin/ide/add", methods=["POST"])
@login_required
@admin_required
def admin_ide_add():
    """Añadir nuevo servicio IDE al catálogo global"""
    try:
        nombre = request.form.get("nombre")
        tipo = request.form.get("tipo", "WMS")
        url = request.form.get("url")
        
        if not nombre or not url:
            flash("Nombre y URL son obligatorios.", "warning")
            return redirect(url_for("admin_panel"))
            
        srv = ServicioIDE(
            nombre=nombre,
            tipo=tipo,
            url=url,
            capas=request.form.get("capas"),
            formato=request.form.get("formato", "image/png"),
            attribution=request.form.get("attribution"),
            pais=request.form.get("pais"),
            categoria=request.form.get("categoria"),
            opacidad=float(request.form.get("opacidad", 0.85)),
            creado_por=current_user.id
        )
        
        db.session.add(srv)
        db.session.commit()
        flash(f"Servicio IDE '{nombre}' añadido correctamente.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error al añadir servicio IDE: {str(e)}", "danger")
        
    return redirect(url_for("admin_panel"))


@app.route("/admin/proyecto/<int:proyecto_id>/delete", methods=["POST"])
@login_required
@admin_required
def admin_delete_proyecto(proyecto_id):
    """Eliminar proyecto y todos sus datos asociados permanentemente"""
    proyecto = Proyecto.query.get_or_404(proyecto_id)
    nombre = proyecto.nombre
    
    try:
        # La eliminación en cascada debería estar configurada en los modelos
        db.session.delete(proyecto)
        db.session.commit()
        flash(f"Proyecto '{nombre}' y todos sus datos asociados eliminados.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error al eliminar proyecto: {str(e)}", "danger")
        
    return redirect(url_for("admin_panel"))


@app.route("/admin/geo/<int:geo_id>/update", methods=["POST"])
@login_required
@admin_required
def admin_geo_update(geo_id):
    """Actualizar coordenadas de una ubicación y marcar como válida"""
    geo = GeoPlace.query.get_or_404(geo_id)
    
    try:
        lat = request.form.get("lat")
        lon = request.form.get("lon")
        
        if lat and lon:
            geo.lat = float(lat)
            geo.lon = float(lon)
            geo.status = "VALID"
            db.session.commit()
            flash(f"Ubicación '{geo.place_raw}' actualizada y validada.", "success")
        else:
            flash("Latitud y Longitud son obligatorias.", "warning")
            
    except Exception as e:
        db.session.rollback()
        flash(f"Error al actualizar ubicación: {str(e)}", "danger")
        
    return redirect(url_for("admin_panel"))


@app.route("/admin/generar-embeddings", methods=["POST"])
@login_required
@admin_required
def admin_generar_embeddings():
    """Generar embeddings para todos los proyectos (global)"""
    import threading
    from services.embedding_service import EmbeddingService
    
    modelo = request.form.get("modelo", "openai-small")
    batch_size = int(request.form.get("batch_size", 50))
    limite = request.form.get("limite")
    limite = int(limite) if limite else None
    
    # Contar noticias pendientes
    total_pendientes = db.session.query(func.count(Prensa.id)).filter(
        Prensa.incluido == True,
        Prensa.embedding_vector.is_(None)
    ).scalar()
    
    if total_pendientes == 0:
        flash("✅ No hay noticias pendientes. Todas tienen embeddings.", "info")
        return redirect(url_for("admin_panel"))
    
    # Iniciar proceso en background
    def proceso_embeddings():
        with app.app_context():
            try:
                from generar_embeddings import generar_embeddings_batch
                generar_embeddings_batch(
                    proyecto_id=None,  # Todos los proyectos
                    modelo=modelo,
                    batch_size=batch_size,
                    limite=limite,
                    interactive=False
                )
            except Exception as e:
                print(f"Error generando embeddings: {e}")
    
    thread = threading.Thread(target=proceso_embeddings)
    thread.daemon = True
    thread.start()
    
    total_a_procesar = min(total_pendientes, limite) if limite else total_pendientes
    flash(f"🚀 Generación de embeddings iniciada para {total_a_procesar} documentos. El proceso se ejecuta en segundo plano.", "success")
    flash(f"📊 Modelo: {modelo} | Batch: {batch_size}", "info")
    
    return redirect(url_for("admin_panel"))


@app.route("/proyecto/<int:proyecto_id>/generar-embeddings", methods=["POST"])
@login_required
def proyecto_generar_embeddings(proyecto_id):
    """Generar embeddings para un proyecto específico"""
    import threading
    from services.embedding_service import EmbeddingService
    
    proyecto = Proyecto.query.get_or_404(proyecto_id)
    
    # Verificar permisos
    if proyecto.user_id != current_user.id and not current_user.es_admin():
        flash("No tienes permisos para generar embeddings en este proyecto.", "danger")
        return redirect(url_for("proyectos.listar"))
    
    modelo = request.form.get("modelo", "openai-small")
    batch_size = int(request.form.get("batch_size", 50))
    limite = request.form.get("limite")
    limite = int(limite) if limite else None
    
    # Contar noticias pendientes del proyecto
    total_pendientes = db.session.query(func.count(Prensa.id)).filter(
        Prensa.proyecto_id == proyecto_id,
        Prensa.incluido == True,
        Prensa.embedding_vector.is_(None)
    ).scalar()
    
    if total_pendientes == 0:
        flash(f"✅ No hay noticias pendientes en '{proyecto.nombre}'. Todas tienen embeddings.", "info")
        return redirect(url_for("proyectos.listar"))
    
    # Iniciar proceso en background
    def proceso_embeddings():
        with app.app_context():
            try:
                from generar_embeddings import generar_embeddings_batch
                generar_embeddings_batch(
                    proyecto_id=proyecto_id,
                    modelo=modelo,
                    batch_size=batch_size,
                    limite=limite,
                    interactive=False
                )
            except Exception as e:
                print(f"Error generando embeddings: {e}")
    
    thread = threading.Thread(target=proceso_embeddings)
    thread.daemon = True
    thread.start()
    
    total_a_procesar = min(total_pendientes, limite) if limite else total_pendientes
    flash(f"🚀 Generación de embeddings iniciada para {total_a_procesar} documentos del proyecto '{proyecto.nombre}'.", "success")
    flash(f"📊 Modelo: {modelo} | Batch: {batch_size}", "info")
    
    return redirect(url_for("proyectos.listar"))


@app.route("/api/embeddings/progress/<prog_id>")
@login_required
def api_embeddings_progress(prog_id):
    """Retorna el progreso de generación de embeddings desde el archivo temporal"""
    import json
    path = f"/tmp/embedding_progress_{prog_id}.json"
    
    if not os.path.exists(path):
        # Fallback: if 'global' is requested, try to find any active progress for the current project
        if prog_id == 'global':
            from utils import get_proyecto_activo
            proyecto = get_proyecto_activo()
            if proyecto:
                path_proyecto = f"/tmp/embedding_progress_{proyecto.id}.json"
                if os.path.exists(path_proyecto):
                    path = path_proyecto
        
        # If still not found, return idle
        if not os.path.exists(path):
            return jsonify({
                "status": "idle",
                "porcentaje": 0,
                "procesados": 0,
                "total": 0,
                "errores": 0
            })
        
    try:
        with open(path, "r") as f:
            data = json.load(f)
        
        # SI el proceso ha terminado, verificar cuánto tiempo hace
        if data.get('status') == 'completed':
            actualizado_en_str = data.get('actualizado_en')
            if actualizado_en_str:
                from datetime import datetime, timezone
                try:
                    # Intentar parsear con y sin microsegundos
                    try:
                        dt_actualizado = datetime.fromisoformat(actualizado_en_str)
                    except ValueError:
                        # Fallback por si acaso
                        dt_actualizado = datetime.strptime(actualizado_en_str, "%Y-%m-%dT%H:%M:%S.%f")
                    
                    # Asegurar que ambos sean aware de UTC
                    now = datetime.now(timezone.utc)
                    if dt_actualizado.tzinfo is None:
                        dt_actualizado = dt_actualizado.replace(tzinfo=timezone.utc)
                    
                    diff = (now - dt_actualizado).total_seconds()
                    
                    # Si tiene más de 60 segundos de antigüedad, lo consideramos irrelevante para la UI
                    if diff > 60:
                        return jsonify({
                            "status": "idle",
                            "porcentaje": 100,
                            "procesados": data.get('procesados', 0),
                            "total": data.get('total', 0),
                            "stale": True
                        })
                except Exception as e:
                    print(f"[DEBUG] Error parseando fecha de progreso: {e}")
        
        return jsonify(data)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/informacion")
def informacion():
    """Página de información sobre hesiOX"""
    return render_template("informacion.html")


@app.route("/ayuda")
def ayuda():
    """Página de ayuda y preguntas frecuentes"""
    return render_template("ayuda.html")


@app.route("/manual")
def manual_usuario():
    """Renderiza el manual de usuario en HTML desde Markdown"""
    try:
        manual_path = os.path.join(os.path.dirname(__file__), 'docs', 'MANUAL_USUARIO.md')
        with open(manual_path, 'r', encoding='utf-8') as f:
            markdown_content = f.read()
        
        # Reemplazar emojis por iconos SVG antes de convertir a HTML
        emoji_replacements = {
            '📘': '<svg width="18" height="18" fill="currentColor" viewBox="0 0 16 16" style="vertical-align: text-bottom;"><path d="M1 2.828c.885-.37 2.154-.769 3.388-.893 1.33-.134 2.458.063 3.112.752v9.746c-.935-.53-2.12-.603-3.213-.493-1.18.12-2.37.461-3.287.811V2.828zm7.5-.141c.654-.689 1.782-.886 3.112-.752 1.234.124 2.503.523 3.388.893v9.923c-.918-.35-2.107-.692-3.287-.81-1.094-.111-2.278-.039-3.213.492V2.687zM8 1.783C7.015.936 5.587.81 4.287.94c-1.514.153-3.042.672-3.994 1.105A.5.5 0 0 0 0 2.5v11a.5.5 0 0 0 .707.455c.882-.4 2.303-.881 3.68-1.02 1.409-.142 2.59.087 3.223.877a.5.5 0 0 0 .78 0c.633-.79 1.814-1.019 3.222-.877 1.378.139 2.8.62 3.681 1.02A.5.5 0 0 0 16 13.5v-11a.5.5 0 0 0-.293-.455c-.952-.433-2.48-.952-3.994-1.105C10.413.809 8.985.936 8 1.783z"/></svg>',
            '📑': '<svg width="18" height="18" fill="currentColor" viewBox="0 0 16 16" style="vertical-align: text-bottom;"><path fill-rule="evenodd" d="M14 4.5V11h-1V4.5h-2A1.5 1.5 0 0 1 9.5 3V1H4a1 1 0 0 0-1 1v9H2V2a2 2 0 0 1 2-2h5.5L14 4.5ZM3 12.5a.5.5 0 0 1 .5-.5h9a.5.5 0 0 1 0 1h-9a.5.5 0 0 1-.5-.5zm0 2a.5.5 0 0 1 .5-.5h9a.5.5 0 0 1 0 1h-9a.5.5 0 0 1-.5-.5z"/></svg>',
            '🎯': '<svg width="18" height="18" fill="currentColor" viewBox="0 0 16 16" style="vertical-align: text-bottom;"><path d="M8 15A7 7 0 1 1 8 1a7 7 0 0 1 0 14zm0 1A8 8 0 1 0 8 0a8 8 0 0 0 0 16z"/><path d="M8 13A5 5 0 1 1 8 3a5 5 0 0 1 0 10zm0 1A6 6 0 1 0 8 2a6 6 0 0 0 0 12z"/><path d="M8 11a3 3 0 1 1 0-6 3 3 0 0 1 0 6zm0 1a4 4 0 1 0 0-8 4 4 0 0 0 0 8z"/><path d="M9.5 8a1.5 1.5 0 1 1-3 0 1.5 1.5 0 0 1 3 0z"/></svg>',
            '🚀': '<svg width="18" height="18" fill="currentColor" viewBox="0 0 16 16" style="vertical-align: text-bottom;"><path d="M9.752 6.193c.599.6 1.73.437 2.528-.362.798-.799.96-1.932.362-2.531-.599-.6-1.73-.438-2.528.361-.798.8-.96 1.933-.362 2.532Z"/><path d="M15.811 3.312c-.363 1.534-1.334 3.626-3.64 6.218l-.24 2.408a2.56 2.56 0 0 1-.732 1.526L8.817 15.85a.51.51 0 0 1-.867-.434l.27-1.899c.04-.28-.013-.593-.131-.956a9.42 9.42 0 0 0-.249-.657l-.082-.202c-.815-.197-1.578-.662-2.191-1.277-.614-.615-1.079-1.379-1.275-2.195l-.203-.083a9.556 9.556 0 0 0-.655-.248c-.363-.119-.675-.172-.955-.132l-1.896.27A.51.51 0 0 1 .15 7.17l2.382-2.386c.41-.41.947-.67 1.524-.734h.006l2.4-.238C9.005 1.55 11.087.582 12.623.208c.89-.217 1.59-.232 2.08-.188.244.023.435.06.57.093.067.017.12.033.16.045.184.06.279.13.351.295l.029.073a3.475 3.475 0 0 1 .157.721c.055.485.051 1.178-.159 2.065Zm-4.828 7.475.04-.04-.107 1.081a1.536 1.536 0 0 1-.44.913l-1.298 1.3.054-.38c.072-.506-.034-.993-.172-1.418a8.548 8.548 0 0 0-.164-.45c.738-.065 1.462-.38 2.087-1.006ZM5.205 5c-.625.626-.94 1.351-1.004 2.09a8.497 8.497 0 0 0-.45-.164c-.424-.138-.91-.244-1.416-.172l-.38.054 1.3-1.3c.245-.246.566-.401.91-.44l1.08-.107-.04.039Zm9.406-3.961c-.38-.034-.967-.027-1.746.163-1.558.38-3.917 1.496-6.937 4.521-.62.62-.799 1.34-.687 2.051.107.676.483 1.362 1.048 1.928.564.565 1.25.941 1.924 1.049.71.112 1.429-.067 2.048-.688 3.079-3.083 4.192-5.444 4.556-6.987.183-.771.18-1.345.138-1.713a2.835 2.835 0 0 0-.045-.283 3.078 3.078 0 0 0-.3-.041Z"/></svg>',
            '🔐': '<svg width="18" height="18" fill="currentColor" viewBox="0 0 16 16" style="vertical-align: text-bottom;"><path d="M8 1a2 2 0 0 1 2 2v4H6V3a2 2 0 0 1 2-2zm3 6V3a3 3 0 0 0-6 0v4a2 2 0 0 0-2 2v5a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2z"/></svg>',
            '📁': '<svg width="18" height="18" fill="currentColor" viewBox="0 0 16 16" style="vertical-align: text-bottom;"><path d="M.54 3.87.5 3a2 2 0 0 1 2-2h3.672a2 2 0 0 1 1.414.586l.828.828A2 2 0 0 0 9.828 3h3.982a2 2 0 0 1 1.992 2.181l-.637 7A2 2 0 0 1 13.174 14H2.826a2 2 0 0 1-1.991-1.819l-.637-7a1.99 1.99 0 0 1 .342-1.31zM2.19 4a1 1 0 0 0-.996 1.09l.637 7a1 1 0 0 0 .995.91h10.348a1 1 0 0 0 .995-.91l.637-7A1 1 0 0 0 13.81 4H2.19z"/></svg>',
            '📂': '<svg width="18" height="18" fill="currentColor" viewBox="0 0 16 16" style="vertical-align: text-bottom;"><path d="M1 3.5A1.5 1.5 0 0 1 2.5 2h2.764c.958 0 1.76.56 2.311 1.184C7.985 3.648 8.48 4 9 4h4.5A1.5 1.5 0 0 1 15 5.5v.64c.57.265.94.876.856 1.546l-.64 5.124A2.5 2.5 0 0 1 12.733 15H3.266a2.5 2.5 0 0 1-2.481-2.19l-.64-5.124A1.5 1.5 0 0 1 1 6.14V3.5zM2 6h12v-.5a.5.5 0 0 0-.5-.5H9c-.964 0-1.71-.629-2.174-1.154C6.374 3.334 5.82 3 5.264 3H2.5a.5.5 0 0 0-.5.5V6zm-.367 1a.5.5 0 0 0-.496.562l.64 5.124A1.5 1.5 0 0 0 3.266 14h9.468a1.5 1.5 0 0 0 1.489-1.314l.64-5.124A.5.5 0 0 0 14.367 7H1.633z"/></svg>',
            '🗄️': '<svg width="18" height="18" fill="currentColor" viewBox="0 0 16 16" style="vertical-align: text-bottom;"><path d="M6 0a.5.5 0 0 1 .5.5V3h3V.5a.5.5 0 0 1 1 0V3h1a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h1V.5A.5.5 0 0 1 6 0zM4 4a1 1 0 0 0-1 1v1h10V5a1 1 0 0 0-1-1H4zm9 3H3v7a1 1 0 0 0 1 1h8a1 1 0 0 0 1-1V7z"/></svg>',
            '📸': '<svg width="18" height="18" fill="currentColor" viewBox="0 0 16 16" style="vertical-align: text-bottom;"><path d="M15 12a1 1 0 0 1-1 1H2a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1h1.172a3 3 0 0 0 2.12-.879l.83-.828A1 1 0 0 1 6.827 3h2.344a1 1 0 0 1 .707.293l.828.828A3 3 0 0 0 12.828 5H14a1 1 0 0 1 1 1v6zM2 4a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V6a2 2 0 0 0-2-2h-1.172a2 2 0 0 1-1.414-.586l-.828-.828A2 2 0 0 0 9.172 2H6.828a2 2 0 0 0-1.414.586l-.828.828A2 2 0 0 1 3.172 4H2z"/><path d="M8 11a2.5 2.5 0 1 1 0-5 2.5 2.5 0 0 1 0 5zm0 1a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7zM3 6.5a.5.5 0 1 1-1 0 .5.5 0 0 1 1 0z"/></svg>',
            '🔍': '<svg width="18" height="18" fill="currentColor" viewBox="0 0 16 16" style="vertical-align: text-bottom;"><path d="M11.742 10.344a6.5 6.5 0 1 0-1.397 1.398h-.001c.03.04.062.078.098.115l3.85 3.85a1 1 0 0 0 1.415-1.414l-3.85-3.85a1.007 1.007 0 0 0-.115-.1zM12 6.5a5.5 5.5 0 1 1-11 0 5.5 5.5 0 0 1 11 0z"/></svg>',
            '🧠': '<svg width="18" height="18" fill="currentColor" viewBox="0 0 16 16" style="vertical-align: text-bottom;"><path d="M4.406 1.342A5.53 5.53 0 0 1 8 0c2.69 0 4.923 2 5.166 4.579C14.758 4.804 16 6.137 16 7.773 16 9.569 14.502 11 12.687 11H10a.5.5 0 0 1 0-1h2.688C13.979 10 15 8.988 15 7.773c0-1.216-1.02-2.228-2.313-2.228h-.5v-.5C12.188 2.825 10.328 1 8 1a4.53 4.53 0 0 0-2.941 1.1c-.757.652-1.153 1.438-1.153 2.055v.448l-.445.049C2.064 4.805 1 5.952 1 7.318 1 8.785 2.23 10 3.781 10H6a.5.5 0 0 1 0 1H3.781C1.708 11 0 9.366 0 7.318c0-1.763 1.266-3.223 2.942-3.593.143-.863.698-1.723 1.464-2.383z"/><path d="M7.646 15.854a.5.5 0 0 0 .708 0l3-3a.5.5 0 0 0-.708-.708L8.5 14.293V5.5a.5.5 0 0 0-1 0v8.793l-2.146-2.147a.5.5 0 0 0-.708.708l3 3z"/></svg>',
            '🏷️': '<svg width="18" height="18" fill="currentColor" viewBox="0 0 16 16" style="vertical-align: text-bottom;"><path d="M2 2a1 1 0 0 1 1-1h4.586a1 1 0 0 1 .707.293l7 7a1 1 0 0 1 0 1.414l-4.586 4.586a1 1 0 0 1-1.414 0l-7-7A1 1 0 0 1 2 6.586V2zm3.5 4a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3z"/></svg>',
            '📊': '<svg width="18" height="18" fill="currentColor" viewBox="0 0 16 16" style="vertical-align: text-bottom;"><path d="M4 11H2v3h2v-3zm5-4H7v7h2V7zm5-5v12h-2V2h2zm-2-1a1 1 0 0 0-1 1v12a1 1 0 0 0 1 1h2a1 1 0 0 0 1-1V2a1 1 0 0 0-1-1h-2zM6 7a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v7a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1V7zm-5 4a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v3a1 1 0 0 1-1 1H2a1 1 0 0 1-1-1v-3z"/></svg>',
            '🔬': '<svg width="18" height="18" fill="currentColor" viewBox="0 0 16 16" style="vertical-align: text-bottom;"><path d="M8.5 5.034v1.1l.953-.55.5.867L9 7l.953.55-.5.866-.953-.55v1.1h-1v-1.1l-.953.55-.5-.866L7 7l-.953-.55.5-.866.953.55v-1.1h1ZM13.25 9a.25.25 0 0 0-.25.25v.5c0 .138.112.25.25.25h.5a.25.25 0 0 0 .25-.25v-.5a.25.25 0 0 0-.25-.25h-.5ZM13 11.25a.25.25 0 0 1 .25-.25h.5a.25.25 0 0 1 .25.25v.5a.25.25 0 0 1-.25.25h-.5a.25.25 0 0 1-.25-.25v-.5Zm.25 1.75a.25.25 0 0 0-.25.25v.5c0 .138.112.25.25.25h.5a.25.25 0 0 0 .25-.25v-.5a.25.25 0 0 0-.25-.25h-.5Zm-11-4a.25.25 0 0 0-.25.25v.5c0 .138.112.25.25.25h.5A.25.25 0 0 0 3 9.75v-.5A.25.25 0 0 0 2.75 9h-.5Zm0 2a.25.25 0 0 0-.25.25v.5c0 .138.112.25.25.25h.5a.25.25 0 0 0 .25-.25v-.5a.25.25 0 0 0-.25-.25h-.5ZM2 13.25a.25.25 0 0 1 .25-.25h.5a.25.25 0 0 1 .25.25v.5a.25.25 0 0 1-.25.25h-.5a.25.25 0 0 1-.25-.25v-.5Z"/><path d="M5 1a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v7.268a2 2 0 0 1 .854 1.369l.853 3.415A1 1 0 0 1 11.74 14H4.26a1 1 0 0 1-.967-1.242l.853-3.415A2 2 0 0 1 5 8.268V1Zm1 0v7.268a1 1 0 0 0 .725.962l.149.037.853 3.415a.002.002 0 0 0 .002.002h6.538a.002.002 0 0 0 .002-.002l.853-3.415a1 1 0 0 0 .725-.962V1H6Z"/></svg>',
            '🗺️': '<svg width="18" height="18" fill="currentColor" viewBox="0 0 16 16" style="vertical-align: text-bottom;"><path fill-rule="evenodd" d="M15.817.113A.5.5 0 0 1 16 .5v14a.5.5 0 0 1-.402.49l-5 1a.502.502 0 0 1-.196 0L5.5 15.01l-4.902.98A.5.5 0 0 1 0 15.5v-14a.5.5 0 0 1 .402-.49l5-1a.5.5 0 0 1 .196 0L10.5.99l4.902-.98a.5.5 0 0 1 .415.103zM10 1.91l-4-.8v12.98l4 .8V1.91zm1 12.98 4-.8V1.11l-4 .8v12.98zm-6-.8V1.11l-4 .8v12.98l4-.8z"/></svg>',
            '💾': '<svg width="18" height="18" fill="currentColor" viewBox="0 0 16 16" style="vertical-align: text-bottom;"><path d="M2 1a1 1 0 0 0-1 1v12a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V2a1 1 0 0 0-1-1H9.5a1 1 0 0 0-1 1v7.293l2.646-2.647a.5.5 0 0 1 .708.708l-3.5 3.5a.5.5 0 0 1-.708 0l-3.5-3.5a.5.5 0 1 1 .708-.708L7.5 9.293V2a2 2 0 0 1 2-2H14a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2V2a2 2 0 0 1 2-2h2.5a.5.5 0 0 1 0 1H2z"/></svg>',
            '📚': '<svg width="18" height="18" fill="currentColor" viewBox="0 0 16 16" style="vertical-align: text-bottom;"><path d="M1 2.828c.885-.37 2.154-.769 3.388-.893 1.33-.134 2.458.063 3.112.752v9.746c-.935-.53-2.12-.603-3.213-.493-1.18.12-2.37.461-3.287.811V2.828zm7.5-.141c.654-.689 1.782-.886 3.112-.752 1.234.124 2.503.523 3.388.893v9.923c-.918-.35-2.107-.692-3.287-.81-1.094-.111-2.278-.039-3.213.492V2.687zM8 1.783C7.015.936 5.587.81 4.287.94c-1.514.153-3.042.672-3.994 1.105A.5.5 0 0 0 0 2.5v11a.5.5 0 0 0 .707.455c.882-.4 2.303-.881 3.68-1.02 1.409-.142 2.59.087 3.223.877a.5.5 0 0 0 .78 0c.633-.79 1.814-1.019 3.222-.877 1.378.139 2.8.62 3.681 1.02A.5.5 0 0 0 16 13.5v-11a.5.5 0 0 0-.293-.455c-.952-.433-2.48-.952-3.994-1.105C10.413.809 8.985.936 8 1.783z"/></svg>',
            '🎨': '<svg width="18" height="18" fill="currentColor" viewBox="0 0 16 16" style="vertical-align: text-bottom;"><path d="M12.433 10.07C14.133 10.585 16 11.15 16 8a8 8 0 1 0-8 8c1.996 0 1.826-1.504 1.649-3.08-.124-1.101-.252-2.237.351-2.92.465-.527 1.42-.237 2.433.07zM8 5a1.5 1.5 0 1 1 0-3 1.5 1.5 0 0 1 0 3zm4.5 3a1.5 1.5 0 1 1 0-3 1.5 1.5 0 0 1 0 3zM5 6.5a1.5 1.5 0 1 1-3 0 1.5 1.5 0 0 1 3 0zm.5 6.5a1.5 1.5 0 1 1 0-3 1.5 1.5 0 0 1 0 3z"/></svg>',
            '⌨️': '<svg width="18" height="18" fill="currentColor" viewBox="0 0 16 16" style="vertical-align: text-bottom;"><path d="M14 5a1 1 0 0 1 1 1v5a1 1 0 0 1-1 1H2a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1h12zM2 4a2 2 0 0 0-2 2v5a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V6a2 2 0 0 0-2-2H2z"/><path d="M13 10.25a.25.25 0 0 1 .25-.25h.5a.25.25 0 0 1 .25.25v.5a.25.25 0 0 1-.25.25h-.5a.25.25 0 0 1-.25-.25v-.5zm0-2a.25.25 0 0 1 .25-.25h.5a.25.25 0 0 1 .25.25v.5a.25.25 0 0 1-.25.25h-.5a.25.25 0 0 1-.25-.25v-.5zm-5 0A.25.25 0 0 1 8.25 8h.5a.25.25 0 0 1 .25.25v.5a.25.25 0 0 1-.25.25h-.5A.25.25 0 0 1 8 8.75v-.5zm2 0a.25.25 0 0 1 .25-.25h1.5a.25.25 0 0 1 .25.25v.5a.25.25 0 0 1-.25.25h-1.5a.25.25 0 0 1-.25-.25v-.5zm1 2a.25.25 0 0 1 .25-.25h.5a.25.25 0 0 1 .25.25v.5a.25.25 0 0 1-.25.25h-.5a.25.25 0 0 1-.25-.25v-.5zm-5-2A.25.25 0 0 1 6.25 8h.5a.25.25 0 0 1 .25.25v.5a.25.25 0 0 1-.25.25h-.5A.25.25 0 0 1 6 8.75v-.5zm-2 0A.25.25 0 0 1 4.25 8h.5a.25.25 0 0 1 .25.25v.5a.25.25 0 0 1-.25.25h-.5A.25.25 0 0 1 4 8.75v-.5zm-2 0A.25.25 0 0 1 2.25 8h.5a.25.25 0 0 1 .25.25v.5a.25.25 0 0 1-.25.25h-.5A.25.25 0 0 1 2 8.75v-.5zm11-2a.25.25 0 0 1 .25-.25h.5a.25.25 0 0 1 .25.25v.5a.25.25 0 0 1-.25.25h-.5a.25.25 0 0 1-.25-.25v-.5zm-2 0a.25.25 0 0 1 .25-.25h.5a.25.25 0 0 1 .25.25v.5a.25.25 0 0 1-.25.25h-.5a.25.25 0 0 1-.25-.25v-.5zm-2 0A.25.25 0 0 1 9.25 6h.5a.25.25 0 0 1 .25.25v.5a.25.25 0 0 1-.25.25h-.5A.25.25 0 0 1 9 6.75v-.5zm-2 0A.25.25 0 0 1 7.25 6h.5a.25.25 0 0 1 .25.25v.5a.25.25 0 0 1-.25.25h-.5A.25.25 0 0 1 7 6.75v-.5zm-2 0A.25.25 0 0 1 5.25 6h.5a.25.25 0 0 1 .25.25v.5a.25.25 0 0 1-.25.25h-.5A.25.25 0 0 1 5 6.75v-.5zm-3 0A.25.25 0 0 1 2.25 6h1.5a.25.25 0 0 1 .25.25v.5a.25.25 0 0 1-.25.25h-1.5A.25.25 0 0 1 2 6.75v-.5zm0 4a.25.25 0 0 1 .25-.25h.5a.25.25 0 0 1 .25.25v.5a.25.25 0 0 1-.25.25h-.5a.25.25 0 0 1-.25-.25v-.5zm2 0a.25.25 0 0 1 .25-.25h5.5a.25.25 0 0 1 .25.25v.5a.25.25 0 0 1-.25.25h-5.5a.25.25 0 0 1-.25-.25v-.5z"/></svg>',
            '🔧': '<svg width="18" height="18" fill="currentColor" viewBox="0 0 16 16" style="vertical-align: text-bottom;"><path d="M.102 2.223A3.004 3.004 0 0 0 3.78 5.897l6.341 6.252A3.003 3.003 0 0 0 13 16a3 3 0 1 0-.851-5.878L5.897 3.781A3.004 3.004 0 0 0 2.223.1l2.141 2.142L4 4l-1.757.364L.102 2.223zm13.37 9.019.528.026.287.445.445.287.026.529L15 13l-.242.471-.026.529-.445.287-.287.445-.529.026L13 15l-.471-.242-.529-.026-.287-.445-.445-.287-.026-.529L11 13l.242-.471.026-.529.445-.287.287-.445.529-.026L13 11l.471.242z"/></svg>',
            '⚠️': '<svg width="18" height="18" fill="currentColor" viewBox="0 0 16 16" style="vertical-align: text-bottom;"><path d="M8.982 1.566a1.13 1.13 0 0 0-1.96 0L.165 13.233c-.457.778.091 1.767.98 1.767h13.713c.889 0 1.438-.99.98-1.767L8.982 1.566zM8 5c.535 0 .954.462.9.995l-.35 3.507a.552.552 0 0 1-1.1 0L7.1 5.995A.905.905 0 0 1 8 5zm.002 6a1 1 0 1 1 0 2 1 1 0 0 1 0-2z"/></svg>',
            '✅': '<svg width="18" height="18" fill="currentColor" viewBox="0 0 16 16" style="vertical-align: text-bottom;"><path d="M12.736 3.97a.733.733 0 0 1 1.047 0c.286.289.29.756.01 1.05L7.88 12.01a.733.733 0 0 1-1.065.02L3.217 8.384a.757.757 0 0 1 0-1.06.733.733 0 0 1 1.047 0l3.052 3.093 5.4-6.425a.247.247 0 0 1 .02-.022Z"/></svg>',
            '💡': '<svg width="18" height="18" fill="currentColor" viewBox="0 0 16 16" style="vertical-align: text-bottom;"><path d="M8 16a2 2 0 0 0 2-2H6a2 2 0 0 0 2 2zm.995-14.901a1 1 0 1 0-1.99 0A5.002 5.002 0 0 0 3 6c0 1.098-.5 6-2 7h14c-1.5-1-2-5.902-2-7 0-2.42-1.72-4.44-4.005-4.901z"/></svg>',
            '📄': '<svg width="18" height="18" fill="currentColor" viewBox="0 0 16 16" style="vertical-align: text-bottom;"><path d="M14 4.5V14a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V2a2 2 0 0 1 2-2h5.5L14 4.5zm-3 0A1.5 1.5 0 0 1 9.5 3V1H4a1 1 0 0 0-1 1v12a1 1 0 0 0 1 1h8a1 1 0 0 0 1-1V4.5h-2z"/></svg>',
        }
        
        for emoji, svg in emoji_replacements.items():
            markdown_content = markdown_content.replace(emoji, svg)
        
        # Convertir markdown a HTML
        try:
            import markdown
            html_content = markdown.markdown(markdown_content, extensions=['extra', 'codehilite', 'toc'])
        except ImportError:
            # Si markdown no está instalado, mostrar texto plano
            html_content = f"<pre>{markdown_content}</pre>"
        
        return render_template("manual_viewer.html", content=html_content)
    except Exception as e:
        flash(f"Error al cargar el manual: {str(e)}", "danger")
        return redirect(url_for('ayuda'))


@app.route("/biblioteca", methods=["GET"])
def index():
    # Verificar proyecto activo
    proyecto = get_proyecto_activo()
    if not proyecto:
        # Si no hay proyectos, redirigir a crear uno
        if Proyecto.query.count() == 0:
            flash("👋 Bienvenido! Crea tu primer proyecto para empezar.", "info")
            return redirect(url_for("crear_proyecto"))
        # Si hay proyectos pero ninguno activo, mostrar selector
        return redirect(url_for("listar_proyectos"))

    filtros = {
        k: request.args.get(k, "").strip()
        for k in [
            "autor",
            "fecha_original",
            "numero",
            "publicacion",
            "ciudad",
            "temas",
            "busqueda",
        ]
    }
    filtros["incluido"] = request.args.get("incluido", "todos")
    page = int(request.args.get("page", 1))

    # FILTRAR POR PROYECTO ACTIVO
    query = Prensa.query.filter_by(proyecto_id=proyecto.id)

    for k, v in filtros.items():
        if k not in ["busqueda", "incluido"] and v:
            query = query.filter(getattr(Prensa, k).ilike(f"%{v}%"))

    if filtros["busqueda"]:
        for p in filtros["busqueda"].split():
            term = f"%{p}%"
            query = query.filter(
                or_(
                    cast(Prensa.titulo, String).ilike(term),
                    cast(Prensa.contenido, String).ilike(term),
                    cast(Prensa.texto_original, String).ilike(
                        term
                    ),  # Buscar en original
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

    query = ordenar_por_fecha(query, descendente=False)

    total = query.count()
    
    # Verificar si hay filtros aplicados (excepto página)
    hay_filtros = any(filtros.get(k) for k in filtros if k != 'incluido') or filtros.get('incluido') != 'todos'
    
    # Si hay filtros, mostrar todos los resultados sin paginación
    if hay_filtros:
        registros_raw = query.all()
        total_paginas = 1
        page = 1
        noticias_por_pagina = request.args.get('noticias_por_pagina', 20, type=int)
    else:
        # Sin filtros, aplicar paginación normal
        noticias_por_pagina = request.args.get('noticias_por_pagina', 20, type=int)
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

    # Si la petición es AJAX (fetch), devolver JSON con el valor actual
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
        html = render_template(
            "_tabla.html",
            registros=registros,
            proyecto=proyecto,
            total=total,
            page=page,
            total_paginas=total_paginas,
            inicio=inicio,
            fin=fin,
            autores=valores_unicos(Prensa.nombre_autor, proyecto.id),
            fechas=valores_unicos(Prensa.fecha_original, proyecto.id),
            numeros=valores_unicos(Prensa.numero, proyecto.id),
            publicaciones=valores_unicos(Prensa.publicacion, proyecto.id),
            ciudades=valores_unicos(Prensa.ciudad, proyecto.id),
            temas_list=valores_unicos(Prensa.temas, proyecto.id),
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
            **filtros,
            noticias_por_pagina=noticias_por_pagina,
        )
        return jsonify({
            "html": html,
            "autores": valores_unicos(Prensa.nombre_autor, proyecto.id),
            "publicaciones": valores_unicos(Prensa.publicacion, proyecto.id),
            "fechas": valores_unicos(Prensa.fecha_original, proyecto.id),
            "ciudades": valores_unicos(Prensa.ciudad, proyecto.id),
            "temas": valores_unicos(Prensa.temas, proyecto.id),
            "noticias_por_pagina": noticias_por_pagina
        })
    else:
        # Obtener opciones de metadatos dinámicas
        opciones_genero = MetadataOption.query.filter_by(categoria='tipo_recurso').order_by(MetadataOption.orden, MetadataOption.etiqueta).all()
        opciones_subgenero = MetadataOption.query.filter_by(categoria='tipo_publicacion').order_by(MetadataOption.orden, MetadataOption.etiqueta).all()
        opciones_frecuencia = MetadataOption.query.filter_by(categoria='frecuencia').order_by(MetadataOption.orden, MetadataOption.etiqueta).all()

        return render_template(
            "list.html",
            opciones_genero=opciones_genero,
            opciones_subgenero=opciones_subgenero,
            opciones_frecuencia=opciones_frecuencia,
            registros=registros,
            proyecto=proyecto,  # Pasar proyecto al template
            total=total,
            page=page,
            total_paginas=total_paginas,
            inicio=inicio,
            fin=fin,
            autores=valores_unicos(Prensa.nombre_autor, proyecto.id),
            fechas=valores_unicos(Prensa.fecha_original, proyecto.id),
            numeros=valores_unicos(Prensa.numero, proyecto.id),
            publicaciones=valores_unicos(Prensa.publicacion, proyecto.id),
            ciudades=valores_unicos(Prensa.ciudad, proyecto.id),
            temas_list=valores_unicos(Prensa.temas, proyecto.id),
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
            **filtros,
            noticias_por_pagina=noticias_por_pagina,
        )


# ====================================================================
# 🚫 RUTA OBSOLETA - Ahora se usa la ruta /filtrar del blueprint articulos_bp
# ====================================================================
@app.route("/filtrar_old")
def filtrar():
    filtros = {
        k: request.args.get(k, "").strip()
        for k in [
            "autor",
            "fecha_original",
            "numero",
            "publicacion",
            "ciudad",
            "temas",
            "busqueda",
        ]
    }
    filtros["incluido"] = request.args.get("incluido", "todos")
    page = int(request.args.get("page", 1))
    orden = request.args.get("orden", "asc")
    sin_paginacion = request.args.get("sin_paginacion", "0") == "1"

    # Filtrar por proyecto activo
    proyecto = get_proyecto_activo()
    if proyecto:
        query = Prensa.query.filter_by(proyecto_id=proyecto.id)
    else:
        query = Prensa.query
    
    for k, v in filtros.items():
        if k not in ["busqueda", "incluido"] and v:
            query = query.filter(getattr(Prensa, k).ilike(f"%{v}%"))

    if filtros["busqueda"]:
        for p in filtros["busqueda"].split():
            term = f"%{p}%"
            query = query.filter(
                or_(
                    cast(Prensa.titulo, String).ilike(term),
                    cast(Prensa.contenido, String).ilike(term),
                    cast(Prensa.texto_original, String).ilike(term),
                    cast(Prensa.temas, String).ilike(term),
                    cast(Prensa.notas, String).ilike(term),
                    cast(Prensa.fuente, String).ilike(term),
                )
            )

    if filtros["incluido"] == "si":
        query = query.filter(Prensa.incluido.is_(True))
    elif filtros["incluido"] == "no":
        query = query.filter(Prensa.incluido.is_(False))

    query = ordenar_por_fecha(query, descendente=(orden == "desc"))
    
    # Verificar si hay filtros aplicados o se solicita sin paginación
    hay_filtros = any(filtros.get(k) for k in filtros if k != 'incluido') or filtros.get('incluido') != 'todos'
    
    # Si hay filtros o se solicita sin paginación, mostrar todos los resultados
    if hay_filtros or sin_paginacion:
        registros = query.all()
        total = len(registros)
        total_paginas = 1
        page = 1
    else:
        # Sin filtros, aplicar paginación normal
        pagination = query.paginate(page=page, per_page=20, error_out=False)
        registros = pagination.items
        total = pagination.total
        total_paginas = pagination.pages

    return render_template(
        "_tabla.html",
        registros=registros,
        total=total,
        page=page,
        total_paginas=total_paginas,
        inicio=max(1, page - 2),
        fin=min(total_paginas, page + 2),
        orden=orden,
    )


# ====================================================================
# 🚫 RUTA OBSOLETA - Ahora se usa /api/valores_filtrados del blueprint articulos_bp
# ====================================================================
@app.route("/api/valores_filtrados_old")
def api_valores_filtrados():
    proyecto = get_proyecto_activo()
    if not proyecto:
        return jsonify({"error": "No hay proyecto activo"}), 400

    # Si piden una columna específica, devolver solo esa
    columna = request.args.get("columna")
    if columna:
        query = Prensa.query.filter_by(proyecto_id=proyecto.id)
        
        if columna == "publicacion":
            valores = sorted({r.publicacion for r in query if r.publicacion})
        elif columna == "autor":
            valores = sorted({r.autor for r in query if r.autor})
        elif columna == "ciudad":
            valores = sorted({r.ciudad for r in query if r.ciudad})
        elif columna == "temas":
            valores = sorted({r.temas for r in query if r.temas})
        elif columna == "fecha_original":
            fechas_raw = {r.fecha_original for r in query if r.fecha_original}
            def parse_fecha(f):
                try:
                    if "/" in f:
                        return datetime.strptime(f, "%d/%m/%Y")
                    elif f.isdigit() and len(f) == 4:
                        return datetime(int(f), 1, 1)
                except Exception:
                    return datetime.max
                return datetime.max
            valores = sorted(fechas_raw, key=parse_fecha)
        else:
            return jsonify({"error": f"Columna '{columna}' no válida"}), 400
        
        response = jsonify(valores)
        response.headers["Content-Type"] = "application/json"
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        return response

    # Si no piden columna específica, devolver todo (para compatibilidad)
    # Obtener todos los filtros posibles
    publicacion = request.args.get("publicacion")
    autor = request.args.get("autor")
    ciudad = request.args.get("ciudad")
    fecha_original = request.args.get("fecha_original")
    temas = request.args.get("temas")
    
    query = Prensa.query.filter_by(proyecto_id=proyecto.id)
    
    # Aplicar filtros si están presentes
    if publicacion:
        query = query.filter(Prensa.publicacion == publicacion)
    if autor:
        query = query.filter(Prensa.autor == autor)
    if ciudad:
        query = query.filter(Prensa.ciudad == ciudad)
    if fecha_original:
        query = query.filter(Prensa.fecha_original == fecha_original)
    if temas:
        query = query.filter(Prensa.temas == temas)

    # Obtener valores únicos de los resultados filtrados
    autores = sorted({r.autor for r in query if r.autor})
    publicaciones = sorted({r.publicacion for r in query if r.publicacion})
    ciudades = sorted({r.ciudad for r in query if r.ciudad})
    temas_list = sorted({r.temas for r in query if r.temas})
    
    # Ordenar fechas cronológicamente
    fechas_raw = {r.fecha_original for r in query if r.fecha_original}
    def parse_fecha(f):
        try:
            if "/" in f:
                return datetime.strptime(f, "%d/%m/%Y")
            elif f.isdigit() and len(f) == 4:
                return datetime(int(f), 1, 1)
        except Exception:
            return datetime.max
        return datetime.max
    fechas = sorted(fechas_raw, key=parse_fecha)

    return jsonify(
        {
            "autores": autores,
            "fechas": fechas,
            "ciudades": ciudades,
            "temas": temas_list,
            "publicaciones": publicaciones
        }
    )


# =========================================================
# GESTIÓN: NUEVA / EDITAR / BORRAR
# =========================================================
@app.route("/actualizar_nota/<int:id>", methods=["POST"])
def actualizar_nota(id):
    data = request.get_json(silent=True) or {}
    nueva_nota = (data.get("nota") or "").strip()
    registro = db.session.get(Prensa, id)
    if not registro:
        return jsonify({"success": False, "message": "Registro no encontrado"}), 404

    registro.notas = nueva_nota
    db.session.commit()
    return jsonify({"success": True})


@app.route("/borrar/<int:id>", methods=["POST"])
def borrar(id):
    from sqlalchemy import text
    try:
        result = db.session.execute(
            text("DELETE FROM articulos_cientificos WHERE id = :id"),
            {'id': id}
        )
        db.session.commit()
        return jsonify({"success": True, "rowcount": result.rowcount})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


# =========================================================
# BORRAR FICHA (VÍA FORMULARIO - REDIRECCIÓN + FLASH)
# =========================================================
@app.route("/borrar_articulo_cientifico/<int:id>", methods=["POST"])
@csrf.exempt
def borrar_articulo_cientifico(id):
    from sqlalchemy import text
    try:
        result = db.session.execute(
            text("DELETE FROM articulos_cientificos WHERE id = :id"),
            {'id': id}
        )
        db.session.commit()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
            # Petición AJAX/fetch
            if result.rowcount > 0:
                return jsonify({"success": True})
            else:
                return jsonify({"success": False, "message": "Artículo científico no encontrado."}), 404
        else:
            # Petición tradicional (formulario)
            if result.rowcount > 0:
                flash("🗑️ Artículo científico eliminado correctamente.", "success")
            else:
                flash("❌ Artículo científico no encontrado.", "danger")
    except Exception as e:
        db.session.rollback()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
            return jsonify({"success": False, "message": str(e)}), 500
        else:
            flash(f"⚠️ Error al eliminar artículo científico: {e}", "warning")
    destino = normalizar_next(request.args.get("next")) or url_for("index")
    return redirect(destino)


@app.route("/actualizar_lote", methods=["POST"])
@csrf.exempt
def actualizar_lote():
    data = request.get_json()
    ids_raw = data.get("ids", [])
    updates = data.get("updates", {})
    
    with open("/opt/hesiox/debug_batch.log", "a") as f:
        f.write(f"\n--- {datetime.now()} ---\n")
        f.write(f"IDs Raw: {ids_raw}\n")
        f.write(f"Updates: {updates}\n")

    # Asegurar que los IDs sean enteros para evitar problemas con PostgreSQL
    ids = []
    for id_val in ids_raw:
        try:
            ids.append(int(id_val))
        except (ValueError, TypeError):
            continue

    if not ids or not updates:
        return jsonify({"success": False, "message": "Datos inválidos"}), 400

    # 1. ACTUALIZAR TABLA PRENSA (Campos normales)
    campos_prensa = [
        "publicacion",
        "tipo_recurso",
        "ciudad",
        "idioma",
        "fecha_consulta",
        "numero",
        "licencia",
        "formato_fuente",
        "pais_publicacion",
        "anio",
        "incluido",
        "fuente",
        "imagen_scan",
        "texto_original",
        "edicion",
        "fecha_original",
        "editorial",
        "nombre_autor",
        "apellido_autor",
        "temas",
        "es_referencia",
        "numero_referencia",
        "lugar_publicacion",
        "seccion",
        "volumen",
        "palabras_clave",
        "pseudonimo",
        "tipo_publicacion",
        "periodicidad",
        "pagina_inicio",
        "pagina_fin",
        "actos_totales",
        "escenas_totales",
        "reparto_total",
        "escenas",
        "reparto",
    ]

    payload_prensa = {}
    for campo in campos_prensa:
        val = updates.get(campo)
        if val is not None and val != "":
            if campo == "incluido":
                payload_prensa[Prensa.incluido] = val.lower() == "si"
            elif campo == "anio":
                try:
                    payload_prensa[Prensa.anio] = int(val)
                except:
                    pass
            elif campo == "edicion":
                payload_prensa[Prensa.edicion] = val
            elif campo == "es_referencia":
                payload_prensa[Prensa.es_referencia] = val.lower() == "si"
            elif campo == "numero_referencia":
                try:
                    payload_prensa[Prensa.numero_referencia] = int(val)
                except:
                    pass
            elif campo == "publicacion":
                payload_prensa[Prensa.publicacion] = val
                # Sincronizar id_publicacion
                primero = db.session.get(Prensa, ids[0])
                if primero:
                    pub = Publicacion.query.filter_by(nombre=val, proyecto_id=primero.proyecto_id).first()
                    if pub:
                        payload_prensa[Prensa.id_publicacion] = pub.id_publicacion
            else:
                payload_prensa[campo] = val

    # --- Lógica de Fecha Automática para Libros ---
    # Si el recurso es o pasa a ser 'libro' y tenemos un año pero NO una fecha exacta,
    # le ponemos el 01/01 por defecto para que sea analizable.
    final_tipo = updates.get("tipo_recurso")
    final_anio = updates.get("anio")
    final_fecha = updates.get("fecha_original")

    if not final_fecha:
        # Si no viene en updates, buscamos el valor actual (si aplica)
        # pero en batch update, si no viene en 'updates' es que no se cambia.
        # Sin embargo, si el usuario nos da un año nuevo para un lote de libros,
        # queremos que se genere la fecha.
        if (final_tipo == "libro") and final_anio and str(final_anio).isdigit():
            payload_prensa[Prensa.fecha_original] = f"01/01/{final_anio}"
        elif final_anio and str(final_anio).isdigit():
            # Si no cambian el tipo pero ya es libro (asumimos por proyecto o selección)
            # Para mayor seguridad, solo aplicamos si es explícitamente libro en el lote o ya lo era
            # En batch update es complejo saberlo para cada uno sin iterar, 
            # pero el usuario pide que si es libro y marcamos año, se aplique.
            if updates.get("tipo_recurso") == "libro":
                payload_prensa[Prensa.fecha_original] = f"01/01/{final_anio}"

    try:
        updated_count = 0
        if payload_prensa:
            with open("/opt/hesiox/debug_batch.log", "a") as f:
                f.write(f"Payload Prensa: {payload_prensa}\n")
            updated_count = db.session.query(Prensa).filter(Prensa.id.in_(ids)).update(
                payload_prensa, synchronize_session=False
            )
            
            # 1.1 ACTUALIZAR RELACIÓN AutorPrensa (para el nuevo sistema de autoría)
            # Solo si se han proporcionado datos de autor
            nombre_batch = updates.get("nombre_autor")
            apellido_batch = updates.get("apellido_autor")
            
            if nombre_batch or apellido_batch:
                # Nota: Para evitar inconsistencias en el lote, borramos autores previos
                # y creamos un único autor principal para cada registro del lote.
                from models import AutorPrensa
                
                # Borrar autores previos para estos registros
                db.session.query(AutorPrensa).filter(AutorPrensa.prensa_id.in_(ids)).delete(synchronize_session=False)
                
                # Crear nuevos autores
                for n_id in ids:
                    nuevo_aut = AutorPrensa(
                        prensa_id=n_id,
                        nombre=nombre_batch or "",
                        apellido=apellido_batch or "",
                        tipo="firmado",
                        es_anonimo=False,
                        orden=0
                    )
                    db.session.add(nuevo_aut)
            
            with open("/opt/hesiox/debug_batch.log", "a") as f:
                f.write(f"Updated Count: {updated_count}\n")

        # 2. ACTUALIZAR TABLA PUBLICACION (Descripción, Tipo y Periodicidad del medio)
        desc_pub = updates.get("descripcion_publicacion")
        tipo_pub = updates.get("tipo_publicacion")
        peri_pub = updates.get("periodicidad")

        if desc_pub or tipo_pub or peri_pub:
            # Buscamos los IDs de publicación asociados a las noticias seleccionadas
            ids_pubs_asociados = (
                db.session.query(Prensa.id_publicacion)
                .filter(Prensa.id.in_(ids))
                .distinct()
                .all()
            )

            # Extraemos la lista de IDs limpia
            lista_ids_pub = [r[0] for r in ids_pubs_asociados if r[0] is not None]

            if lista_ids_pub:
                updates_pub = {}
                if desc_pub:
                    updates_pub[Publicacion.descripcion] = desc_pub
                if tipo_pub:
                    updates_pub[Publicacion.tipo_publicacion] = tipo_pub
                if peri_pub:
                    updates_pub[Publicacion.periodicidad] = peri_pub

                if updates_pub:
                    # Actualizamos la tabla Publicacion
                    Publicacion.query.filter(
                        Publicacion.id_publicacion.in_(lista_ids_pub)
                    ).update(updates_pub, synchronize_session="fetch")

        db.session.commit()
        flash(
            f"✅ Actualizados {updated_count} registros de prensa y sus publicaciones asociadas.",
            "success",
        )
        return jsonify({"success": True})

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/autor/bio/editar/<int:id>")
@login_required
def editar_autor_bio_page(id):
    autor = AutorBio.query.get_or_404(id)
    # Solo permitir editar si es del proyecto actual o es admin
    if autor.proyecto_id != session.get('proyecto_id') and current_user.rol != 'admin':
        flash("No tienes permiso para editar este autor en este proyecto.", "warning")
        return redirect(url_for("lista_autores"))
    
    return render_template("autor_bio_editor.html", autor=autor)

@app.route("/autor/bio/get", methods=["GET"])
@login_required
def get_autor_bio():
    nombre = request.args.get("nombre", "").strip()
    apellido = request.args.get("apellido", "").strip()
    
    if not nombre and not apellido:
        return jsonify({"status": "not_found", "message": "Parámetros vacíos"}), 200
        
    proyecto_activo = get_proyecto_activo()
    
    # Robustez: Si el nombre contiene una coma y el apellido está vacío, intentar dividirlos
    # Esto ayuda cuando el frontend envía "Apellido, Nombre" en un solo campo
    if nombre and "," in nombre and not apellido:
        partes = nombre.split(",", 1)
        apellido = partes[0].strip()
        nombre = partes[1].strip()
        
    user_project_ids = [p.id for p in current_user.proyectos]
    query = AutorBio.query.filter(AutorBio.proyecto_id.in_(user_project_ids))
    
    # Búsqueda por nombre y apellido
    autor = query.filter(
        AutorBio.nombre.ilike(f"%{nombre}%"),
        AutorBio.apellido.ilike(f"%{apellido}%")
    ).first()
    
    # Fallback si no encuentra combinación exacta, buscar seudónimo
    if not autor:
        autor = query.filter(
            or_(
                AutorBio.seudonimo.ilike(f"%{nombre}%"),
                AutorBio.seudonimo.ilike(f"%{apellido}%")
            )
        ).first()
    
    if autor:
        return jsonify({"status": "success", "bio": autor.to_dict()})
    return jsonify({"status": "not_found"})

@app.route("/autor/bio/ia_expand", methods=["POST"])
@login_required
def ia_expand_bio():
    from services.ai_service import AIService
    
    nombre = request.json.get("nombre")
    apellido = request.json.get("apellido")
    current_bio = request.json.get("bio_data", {})
    
    prompt = f"""
    Eres un experto en investigación biográfica y prosopografía. Tu tarea es completar TODOS los campos de una ficha técnica para el autor: {nombre} {apellido}.
    
    INSTRUCCIONES:
    1. Busca y genera información verídica y detallada para cada punto.
    2. Si el autor es una figura histórica conocida, rellena todos los campos con precisión.
    3. Para fechas, usa estrictamente el formato DD/MM/AAAA.
    4. Para campos de texto largo (trayectoria, estilo, impacto), sé descriptivo y analítico (mínimo 3-4 líneas).
    5. NO dejes campos vacíos. Si el dato es totalmente desconocido, usa el contexto histórico para inferir el dato más probable o deja una nota breve.
    
    ESTRUCTURA DE RESPUESTA (Responde EXCLUSIVAMENTE con este objeto JSON):
    {{
        "seudonimo": "Nombre literario o alias conocidos",
        "lugar_nacimiento": "Ciudad, Región, País",
        "fecha_nacimiento": "DD/MM/AAAA",
        "lugar_defuncion": "Ciudad, País",
        "fecha_defuncion": "DD/MM/AAAA",
        "nacionalidad": "Nacionalidad principal",
        "formacion_academica": "Resumen detallado de su educación, formación y trayectoria vital temprana",
        "ocupaciones_secundarias": "Otras profesiones o cargos desempeñados",
        "movimiento_literario": "Escuelas o movimientos literarios vinculados",
        "influencias": "Autores o corrientes que marcaron su pensamiento",
        "generos_literarios": "Lista de géneros practicados",
        "tematicas_recurrentes": "Análisis de sus temas constantes",
        "obras_principales": "Bibliografía fundamental con años de publicación",
        "estilo": "Análisis técnico de su lenguaje, recursos y tono literario",
        "premios": "Menciones, premios y honores recibidos",
        "impacto": "Trascendencia en la literatura universal y legado",
        "bibliografia": "Libros de referencia sobre el autor",
        "citas": "Frases célebres representativas",
        "enlaces": "Sitios web de referencia o archivos"
    }}
    """
    
    ai = AIService(provider='gemini', model='1.5-pro', user=current_user)
    try:
        raw_response = ai.generate_content(prompt, temperature=0.1)
        # Log para depuración en el servidor
        print(f"[HesiOX IA] Respuesta de {nombre} {apellido}: {raw_response[:200]}...")
        data = ai._extract_json_from_text(raw_response)
        if data:
            return jsonify({"status": "success", "expanded": data})
        return jsonify({"status": "error", "message": "No se pudo estructurar la respuesta de la IA"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route("/autor/bio/save", methods=["POST"])
@login_required
def save_autor_bio():
    try:
        # Soporte para FormData (multipart/form-data)
        data = request.form
        proyecto_activo = get_proyecto_activo()
        
        nombre = (data.get("nombre") or data.get("bio_nombre", "")).strip()
        apellido = (data.get("apellido") or data.get("bio_apellido", "")).strip()
        
        # Robustez: Si el nombre tiene coma y el apellido está vacío, dividir
        if nombre and "," in nombre and not apellido:
            partes = nombre.split(",", 1)
            apellido = partes[0].strip()
            nombre = partes[1].strip()
            
        if not nombre and not apellido:
            return jsonify({"status": "error", "message": "Nombre o Apellido son obligatorios"}), 400
            
        autor_id = data.get("autor_id") or data.get("bio_autor_id")
        
        if autor_id:
            autor = AutorBio.query.get(autor_id)
        else:
            autor = AutorBio.query.filter_by(
                nombre=nombre, 
                apellido=apellido,
                proyecto_id=proyecto_activo.id if proyecto_activo else None
            ).first()
        
        if not autor:
            autor = AutorBio(
                nombre=nombre, 
                apellido=apellido,
                proyecto_id=proyecto_activo.id if proyecto_activo else None
            )
            db.session.add(autor)
            db.session.flush() # Para tener el ID
            
        # Actualizar campos de texto
        for key in data.keys():
            # Mapear nombres de campos del modal a campos del modelo si es necesario
            model_key = key.replace('bio_', '')
            if hasattr(autor, model_key) and model_key not in ['id', 'proyecto_id', 'creado_en', 'foto']:
                setattr(autor, model_key, data.get(key))
                
        # Manejar subida de Retrato/Foto
        if 'foto_file' in request.files:
            file = request.files['foto_file']
            if file and file.filename:
                import time
                from werkzeug.utils import secure_filename
                filename = secure_filename(f"autor_{autor.id}_{int(time.time())}_{file.filename}")
                upload_folder = app.config.get('UPLOAD_FOLDER', 'static/uploads')
                upload_path = os.path.join(upload_folder, 'autores')
                os.makedirs(upload_path, exist_ok=True)
                file.save(os.path.join(upload_path, filename))
                autor.foto = filename
                
        db.session.commit()
        return jsonify({"status": "success", "success": True, "id": autor.id})
    except Exception as e:
        db.session.rollback()
        import traceback
        traceback.print_exc()
        app.logger.error(f"Error al guardar biografía de autor: {str(e)}")
        return jsonify({"status": "error", "success": False, "message": str(e)}), 500

@app.route("/autores")
@login_required
def lista_autores():
    proyecto = get_proyecto_activo()
    if not proyecto:
        flash("⚠️ Selecciona un proyecto primero", "warning")
        return redirect(url_for("proyectos.listar"))
    
    q = request.args.get('q', '').strip()
    siglo = request.args.get('siglo', '').strip()
    
    # Base query: SOLO autores de este proyecto para el listado principal
    query = AutorBio.query.filter_by(proyecto_id=proyecto.id)

    if q:
        query = query.filter(
            or_(
                AutorBio.nombre.ilike(f"%{q}%"),
                AutorBio.apellido.ilike(f"%{q}%"),
                AutorBio.seudonimo.ilike(f"%{q}%")
            )
        )
    
    if siglo:
        try:
            s_num = int(siglo)
            start_year = (s_num - 1) * 100 + 1
            end_year = s_num * 100
            
            # Extraemos el año (último segmento separado por '/' o el texto completo si no hay '/')
            # PostgreSQL: reverse(split_part(reverse(campo), '/', 1))
            year_part = func.reverse(func.split_part(func.reverse(AutorBio.fecha_nacimiento), '/', 1))
            
            # Filtramos por rango numérico (cast a Integer para PostgreSQL)
            # Primero nos aseguramos de que sea numérico para evitar errores de cast
            query = query.filter(year_part.op('~')('^[0-9]+$'))
            query = query.filter(cast(year_part, Integer).between(start_year, end_year))
        except Exception as e:
            app.logger.error(f"Error al filtrar por siglo {siglo}: {e}")
            pass

    autores = query.order_by(AutorBio.apellido, AutorBio.nombre).all()
    return render_template("autores_lista.html", autores=autores, q=q, siglo=siglo, proyecto=proyecto)

@app.route("/autor/nuevo")
@login_required
def nuevo_autor_page():
    proyecto = get_proyecto_activo()
    if not proyecto:
        flash("⚠️ Selecciona un proyecto primero", "warning")
        return redirect(url_for("proyectos.listar"))
    return render_template("autor_nuevo.html", proyecto=proyecto)

@app.route("/autor/bio/delete/<int:id>", methods=["POST"])
@login_required
def delete_autor_bio(id):
    try:
        autor = AutorBio.query.get_or_404(id)
        proyecto_activo = get_proyecto_activo()
        if autor.proyecto_id != proyecto_activo.id:
             return jsonify({"success": False, "message": "No tienes permiso para eliminar este autor"}), 403
             
        db.session.delete(autor)
        db.session.commit()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route("/autores/repositorio")
@login_required
def repositorio_global_autores():
    proyecto_actual = get_proyecto_activo()
    q = request.args.get('q', '').strip()
    
    # Obtener IDs de todos los proyectos del usuario
    proyecto_ids = [p.id for p in current_user.proyectos]
    
    # Base query: Todos los autores de otros proyectos + Universales, excluyendo los del proyecto actual
    query = AutorBio.query.filter(or_(AutorBio.proyecto_id.in_(proyecto_ids), AutorBio.proyecto_id == None))
    query = query.filter(or_(AutorBio.proyecto_id != proyecto_actual.id, AutorBio.proyecto_id == None))
    
    if q:
        query = query.filter(
            or_(
                AutorBio.nombre.ilike(f"%{q}%"),
                AutorBio.apellido.ilike(f"%{q}%"),
                AutorBio.seudonimo.ilike(f"%{q}%")
            )
        )
    
    all_autores = query.order_by(AutorBio.apellido, AutorBio.nombre).all()
    
    # Lógica de desduplicación inteligente: si existe una versión con proyecto y una universal, preferir la de proyecto
    autores_dict = {}
    for a in all_autores:
        key = (a.nombre, a.apellido, a.seudonimo)
        if key not in autores_dict:
            autores_dict[key] = a
        else:
            if autores_dict[key].proyecto_id is None and a.proyecto_id is not None:
                autores_dict[key] = a
                
    autores = sorted(autores_dict.values(), key=lambda x: (x.apellido or '', x.nombre or ''))
    total_globales = len(autores)
    
    # Obtener nombres de autores ya presentes en el proyecto actual para marcarlos en la UI
    autores_locales = AutorBio.query.filter_by(proyecto_id=proyecto_actual.id).all()
    nombres_locales = {f"{a.nombre}|{a.apellido}" for a in autores_locales}
    
    return render_template("repositorio_autores.html", 
                           autores=autores, 
                           total_globales=total_globales, 
                           q=q, 
                           proyecto=proyecto_actual,
                           nombres_locales=nombres_locales)

@app.route("/autor/importar/<int:id>", methods=["POST"])
@login_required
def importar_autor_bio(id):
    proyecto_actual = get_proyecto_activo()
    if not proyecto_actual:
        flash("Selecciona un proyecto primero", "warning")
        return redirect(url_for('proyectos.listar'))
        
    autor_original = AutorBio.query.get_or_404(id)
    
    # Verificar que el autor original pertenece a uno de los proyectos del usuario, es Universal o el usuario es Admin
    if current_user.rol != 'admin':
        user_p_ids = [p.id for p in current_user.proyectos]
        if autor_original.proyecto_id is not None and autor_original.proyecto_id not in user_p_ids:
            flash("No tienes permiso para importar este autor", "danger")
            return redirect(url_for('repositorio_global_autores'))
        
    # Crear copia
    nuevo_autor = AutorBio()
    # Copiar campos manualmente para evitar problemas con relaciones/IDs
    exclude = ['id', 'proyecto_id', 'created_at', 'updated_at', 'proyecto']
    for column in autor_original.__table__.columns:
        if column.name not in exclude:
            setattr(nuevo_autor, column.name, getattr(autor_original, column.name))
    
    nuevo_autor.proyecto_id = proyecto_actual.id
    
    try:
        db.session.add(nuevo_autor)
        db.session.commit()
        flash(f"✅ Autor '{nuevo_autor.nombre} {nuevo_autor.apellido}' importado correctamente", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"❌ Error al importar: {str(e)}", "danger")
        
    return redirect(url_for('lista_autores'))
        
@app.route("/autor/importar/masivo", methods=["POST"])
@login_required
def importar_autor_bio_masivo():
    proyecto_actual = get_proyecto_activo()
    if not proyecto_actual:
        return jsonify({"status": "error", "message": "Selecciona un proyecto primero"}), 400
        
    data = request.get_json()
    ids = data.get('ids', [])
    
    if not ids:
        return jsonify({"status": "error", "message": "No se han seleccionado autores"}), 400
        
    exito = 0
    errores = 0
    
    # Obtener IDs de proyectos del usuario para validación
    user_project_ids = [p.id for p in current_user.proyectos]
    
    for autor_id in ids:
        try:
            autor_original = AutorBio.query.get(autor_id)
            if not autor_original:
                errores += 1
                continue
            
            # Verificar permiso (pertenece a sus proyectos, es Universal o es Admin)
            if current_user.rol != 'admin':
                user_project_ids = [p.id for p in current_user.proyectos]
                if autor_original.proyecto_id is not None and autor_original.proyecto_id not in user_project_ids:
                    errores += 1
                    continue
                
            # Evitar duplicados en el mismo proyecto (basado en nombre/apellido/seudonimo)
            # Podríamos ser más estrictos, pero por ahora permitimos si el usuario lo pide
            
            # Crear copia
            nuevo_autor = AutorBio()
            exclude = ['id', 'proyecto_id', 'created_at', 'updated_at', 'proyecto']
            for column in autor_original.__table__.columns:
                if column.name not in exclude:
                    setattr(nuevo_autor, column.name, getattr(autor_original, column.name))
            
            nuevo_autor.proyecto_id = proyecto_actual.id
            db.session.add(nuevo_autor)
            exito += 1
        except:
            errores += 1
            
    try:
        db.session.commit()
        return jsonify({
            "status": "success", 
            "message": f"Se han importado {exito} autores correctamente. {f'Errores: {errores}' if errores else ''}"
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500

    return redirect(url_for('lista_autores'))

@app.route("/nueva", methods=["GET", "POST"])
def nueva():
    # Verificar proyecto activo
    proyecto = get_proyecto_activo()
    if not proyecto:
        flash("⚠️ Debes seleccionar un proyecto antes de crear artículos", "warning")
        return redirect(url_for("listar_proyectos"))

    precargados = {key: request.args.get(key) for key in request.args}

    if request.method == "POST":
        # =============================
        # VALIDACIÓN SERVIDOR FECHA
        # =============================
        fecha_original = (request.form.get("fecha_original") or "").strip()
        fecha_consulta = (request.form.get("fecha_consulta") or "").strip()

        # Validar fecha_original (relajado para libros: permite Mes/Año)
        if request.form.get("tipo_recurso") == "libro":
            valida, error_msg = True, None
        else:
            valida, error_msg = validar_fecha_ddmmyyyy(fecha_original)
            
        if not valida:
            flash(f"⚠️ Fecha Original inválida: {error_msg}", "danger")
            # Re-render preservando datos del formulario
            idiomas = ["es", "it", "fr", "en", "pt", "ct"]
            tipos_autor = ["anónimo", "firmado", "corresponsal"]
            publicaciones = [
                p.nombre
                for p in Publicacion.query.filter_by(proyecto_id=proyecto.id).order_by(Publicacion.nombre.asc()).all()
            ]
            ciudades = sorted(
                {
                    *(
                        p.ciudad
                        for p in Publicacion.query.filter(
                            Publicacion.ciudad.isnot(None)
                        )
                    ),
                    *(r.ciudad for r in Prensa.query.filter(Prensa.ciudad.isnot(None))),
                }
            )
            temas = valores_unicos(Prensa.temas, proyecto.id)
            licencias = sorted(
                {
                    *(
                        p.licencia
                        for p in Publicacion.query.filter(
                            Publicacion.licencia.isnot(None)
                        )
                    ),
                    *(
                        r.licencia
                        for r in Prensa.query.filter(Prensa.licencia.isnot(None))
                    ),
                }
                | {"CC BY 4.0"}
            )
            formatos = sorted(
                {
                    *(
                        p.formato_fuente
                        for p in Publicacion.query.filter(
                            Publicacion.formato_fuente.isnot(None)
                        )
                    ),
                    *(
                        r.formato_fuente
                        for r in Prensa.query.filter(Prensa.formato_fuente.isnot(None))
                    ),
                }
            )
            paises = sorted(
                {
                    *(
                        p.pais_publicacion
                        for p in Publicacion.query.filter(
                            Publicacion.pais_publicacion.isnot(None)
                        )
                    ),
                    *(
                        r.pais_publicacion
                        for r in Prensa.query.filter(
                            Prensa.pais_publicacion.isnot(None)
                        )
                    ),
                }
            )
            next_url = normalizar_next(request.args.get("next"))
            precargados_form = {
                k: (request.form.get(k) or "") for k in request.form.keys()
            }
            return render_template(
                "new.html",
                idiomas=idiomas,
                tipos_autor=tipos_autor,
                publicaciones=publicaciones,
                ciudades=ciudades,
                temas=temas,
                licencias=licencias,
                formatos=formatos,
                paises=paises,
                next_url=next_url,
                precargados=precargados_form,
            )

        # Validar fecha_consulta
        valida, error_msg = validar_fecha_ddmmyyyy(fecha_consulta)
        if not valida:
            flash(f"⚠️ Fecha Consulta inválida: {error_msg}", "danger")
            # Re-render con los mismos datos
            idiomas = ["es", "it", "fr", "en", "pt", "ct"]
            tipos_autor = ["anónimo", "firmado", "corresponsal"]
            publicaciones = [
                p.nombre
                for p in Publicacion.query.filter_by(proyecto_id=proyecto.id).order_by(Publicacion.nombre.asc()).all()
            ]
            ciudades = sorted(
                {
                    *(
                        p.ciudad
                        for p in Publicacion.query.filter(
                            Publicacion.ciudad.isnot(None)
                        )
                    ),
                    *(r.ciudad for r in Prensa.query.filter(Prensa.ciudad.isnot(None))),
                }
            )
            temas = valores_unicos(Prensa.temas, proyecto.id)
            licencias = sorted(
                {
                    *(
                        p.licencia
                        for p in Publicacion.query.filter(
                            Publicacion.licencia.isnot(None)
                        )
                    ),
                    *(
                        r.licencia
                        for r in Prensa.query.filter(Prensa.licencia.isnot(None))
                    ),
                }
                | {"CC BY 4.0"}
            )
            formatos = sorted(
                {
                    *(
                        p.formato_fuente
                        for p in Publicacion.query.filter(
                            Publicacion.formato_fuente.isnot(None)
                        )
                    ),
                    *(
                        r.formato_fuente
                        for r in Prensa.query.filter(Prensa.formato_fuente.isnot(None))
                    ),
                }
            )
            paises = sorted(
                {
                    *(
                        p.pais_publicacion
                        for p in Publicacion.query.filter(
                            Publicacion.pais_publicacion.isnot(None)
                        )
                    ),
                    *(
                        r.pais_publicacion
                        for r in Prensa.query.filter(
                            Prensa.pais_publicacion.isnot(None)
                        )
                    ),
                }
            )
            next_url = normalizar_next(request.args.get("next"))
            precargados_form = {
                k: (request.form.get(k) or "") for k in request.form.keys()
            }
            return render_template(
                "new.html",
                idiomas=idiomas,
                tipos_autor=tipos_autor,
                publicaciones=publicaciones,
                ciudades=ciudades,
                temas=temas,
                licencias=licencias,
                formatos=formatos,
                paises=paises,
                next_url=next_url,
                precargados=precargados_form,
            )

        # 1. GESTIÓN DE MÚLTIPLES AUTORES Y PSEUDÓNIMO
        pseudonimo = (request.form.get("pseudonimo") or "").strip()
        nombres_lista = request.form.getlist("nombre_autor[]")
        apellidos_lista = request.form.getlist("apellido_autor[]")
        tipos_lista = request.form.getlist("tipo_autor[]")
        # El checkbox solo envía 'on' si está marcado. Para una lista de checkboxes dinámicos,
        # es más fiable usar un patrón de IDs o procesar por índice.
        # En el JS, 'anonimo_autor[]' se envía por cada fila.
        anonimos_raw = request.form.getlist("anonimo_autor[]")
        
        # Para compatibilidad con columnas nombre_autor / apellido_autor originales (primer autor)
        nombre_autor_db = None
        apellido_autor_db = None
        autor_final = None
        
        # Procesamos la lista de autores
        autores_objs = []
        for i in range(len(nombres_lista)):
            nom = (nombres_lista[i] or "").strip()
            ape = (apellidos_lista[i] or "").strip()
            tip = tipos_lista[i] if i < len(tipos_lista) else "firmado"
            # Un truco para los checkboxes en listas de Flask: 
            # Si el checkbox no está marcado, no se envía nada en getlist.
            # Pero en nuestro JS, podemos asegurar que se envíe algo o inferir.
            # Alternativa: el JS marca anónimo si el check está activo.
            es_anon = (i < len(anonimos_raw) and anonimos_raw[i] == "on")
            
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
                if es_anon:
                    autor_final = "Anónimo"
                else:
                    if ape and nom: autor_final = f"{ape}, {nom}"
                    elif ape: autor_final = ape
                    else: autor_final = nom

        # 2. GESTIÓN DE PUBLICACIÓN (MEDIO)
        nombre_pub = (request.form.get("publicacion") or "").strip()
        pub = None

        if nombre_pub:
            # Buscar publicación existente o crear nueva
            pub = Publicacion.query.filter_by(
                nombre=nombre_pub, proyecto_id=proyecto.id
            ).first()
            if not pub:
                pub = Publicacion(nombre=nombre_pub, proyecto_id=proyecto.id)
                db.session.add(pub)
                db.session.flush()  # Obtener ID sin hacer commit completo

            # Actualizar campos de la publicación solo si hay datos
            campos_pub = {
                "descripcion": request.form.get("descripcion_publicacion"),
                "tipo_recurso": request.form.get("tipo_recurso"),
                "ciudad": request.form.get("ciudad"),
                "idioma": request.form.get("idioma"),
                "licencia": request.form.get("licencia") or "CC BY 4.0",
                "formato_fuente": request.form.get("formato_fuente"),
                "pais_publicacion": request.form.get("pais_publicacion"),
                "editorial": request.form.get("editorial"),
            }

            for campo, valor in campos_pub.items():
                if valor and (getattr(pub, campo) is None or getattr(pub, campo) == ""):
                    setattr(pub, campo, valor)

            # HERENCIA DE AUTORÍA: Si no se enviaron autores en el form, heredar de la publicación
            form_has_authors = any(n.strip() or a.strip() for n, a in zip(nombres_lista, apellidos_lista))
            if not form_has_authors and pub and pub.autores:
                autores_objs = []
                for i, aut_pub in enumerate(pub.autores):
                    autores_objs.append(AutorPrensa(
                        nombre=aut_pub.nombre,
                        apellido=aut_pub.apellido,
                        tipo=aut_pub.tipo,
                        es_anonimo=aut_pub.es_anonimo,
                        orden=aut_pub.orden
                    ))
                    if i == 0:
                        nombre_autor_db = aut_pub.nombre
                        apellido_autor_db = aut_pub.apellido
                        if aut_pub.es_anonimo:
                            autor_final = "Anónimo"
                        else:
                            if aut_pub.apellido and aut_pub.nombre: autor_final = f"{aut_pub.apellido}, {aut_pub.nombre}"
                            elif aut_pub.apellido: autor_final = aut_pub.apellido
                            else: autor_final = aut_pub.nombre

        nuevo = Prensa(
            proyecto_id=proyecto.id,  # ASIGNAR PROYECTO ACTIVO
            titulo=request.form.get("titulo"),
            publicacion=nombre_pub,
            id_publicacion=pub.id_publicacion if pub else None,
            ciudad=request.form.get("ciudad"),
            fecha_original=fecha_original,
            anio=request.form.get("anio") or None,
            numero=request.form.get("numero"),
            edicion=request.form.get("edicion"),
            pagina_inicio=request.form.get("pagina_inicio"),
            pagina_fin=request.form.get("pagina_fin"),
            paginas=request.form.get("paginas"),
            url=request.form.get("url"),
            fecha_consulta=fecha_consulta,
            autor=autor_final,
            nombre_autor=nombre_autor_db,
            apellido_autor=apellido_autor_db,
            pseudonimo=pseudonimo,
            idioma=request.form.get("idioma"),
            tipo_autor=request.form.get("tipo_autor") or (autores_objs[0].tipo if autores_objs else "firmado"),
            fuente_condiciones=request.form.get("fuente_condiciones"),
            temas=", ".join(request.form.getlist("temas")),
            notas=request.form.get("notas"),
            contenido=request.form.get("contenido"),
            texto_original=request.form.get("texto_original"),  # [NUEVO]
            licencia=request.form.get("licencia") or "CC BY 4.0",
            incluido=(request.form.get("incluido") == "si"),
            numero_referencia=int(request.form.get("numero_referencia"))
            if request.form.get("numero_referencia")
            and request.form.get("numero_referencia").strip().isdigit()
            else None,
            tipo_recurso=request.form.get("tipo_recurso"),
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
            pais_publicacion=request.form.get("pais_publicacion"),
            formato_fuente=request.form.get("formato_fuente"),
            fuente=request.form.get("fuente"),
            referencias_relacionadas=request.form.get("referencias_relacionadas"),
            archivo_pdf=request.form.get("archivo_pdf"),
            imagen_scan=None,  # Este campo queda obsoleto
            es_referencia=(request.form.get("es_referencia") == "si"),
            # Campos teatrales
            actos_totales=request.form.get("actos_totales"),
            escenas_totales=request.form.get("escenas_totales"),
            reparto_total=request.form.get("reparto_total"),
            escenas=request.form.get("escenas"),
            reparto=request.form.get("reparto"),
        )
        db.session.add(nuevo)
        db.session.flush()  # Obtener ID del nuevo registro

        # 2.5 GUARDAR AUTORES RELACIONADOS
        for aut in autores_objs:
            aut.prensa_id = nuevo.id
            db.session.add(aut)

        # 3. GUARDAR MÚLTIPLES IMÁGENES
        imagenes = request.files.getlist("imagen_scan")
        for imagen in imagenes:
            if imagen and allowed_file(imagen.filename):
                nombre_imagen = secure_filename(
                    f"{datetime.now().timestamp()}_{imagen.filename}"
                )
                imagen.save(os.path.join(app.config["UPLOAD_FOLDER"], nombre_imagen))
                nueva_imagen = ImagenPrensa(prensa_id=nuevo.id, filename=nombre_imagen)
                db.session.add(nueva_imagen)
        db.session.commit()
        flash("✅ Referencia añadida correctamente.", "success")

        next_raw = request.args.get("next")
        destino = normalizar_next(next_raw) or url_for("index")
        return redirect(destino)

    idiomas = ["es", "it", "fr", "en", "pt", "ct"]
    tipos_autor = ["anónimo", "firmado", "corresponsal"]

    if proyecto:
        publicaciones = [
            p.nombre for p in Publicacion.query.filter_by(proyecto_id=proyecto.id).order_by(Publicacion.nombre.asc()).all()
        ]
    else:
        publicaciones = []
    ciudades = sorted(
        {
            *(
                p.ciudad
                for p in Publicacion.query.filter(Publicacion.ciudad.isnot(None))
            ),
            *(r.ciudad for r in Prensa.query.filter(Prensa.ciudad.isnot(None))),
        }
    )
    temas = valores_unicos(Prensa.temas, proyecto.id)
    licencias = sorted(
        {
            *(
                p.licencia
                for p in Publicacion.query.filter(Publicacion.licencia.isnot(None))
            ),
            *(r.licencia for r in Prensa.query.filter(Prensa.licencia.isnot(None))),
        }
        | {"CC BY 4.0"}
    )
    formatos = sorted(
        {
            *(
                p.formato_fuente
                for p in Publicacion.query.filter(
                    Publicacion.formato_fuente.isnot(None)
                )
            ),
            *(
                r.formato_fuente
                for r in Prensa.query.filter(Prensa.formato_fuente.isnot(None))
            ),
        }
    )
    paises = sorted(
        {
            *(
                p.pais_publicacion
                for p in Publicacion.query.filter(
                    Publicacion.pais_publicacion.isnot(None)
                )
            ),
            *(
                r.pais_publicacion
                for r in Prensa.query.filter(Prensa.pais_publicacion.isnot(None))
            ),
        }
    )

    next_url = normalizar_next(request.args.get("next"))

    # Obtener hemerotecas del proyecto actual
    proyecto = get_proyecto_activo()
    if proyecto:
        hemerotecas = (
            Hemeroteca.query.filter_by(proyecto_id=proyecto.id)
            .order_by(Hemeroteca.nombre)
            .all()
        )
    else:
        hemerotecas = Hemeroteca.query.order_by(Hemeroteca.nombre).all()

    return render_template(
        "new.html",
        idiomas=idiomas,
        tipos_autor=tipos_autor,
        publicaciones=publicaciones,
        ciudades=ciudades,
        temas=temas,
        licencias=licencias,
        formatos=formatos,
        paises=paises,
        hemerotecas=hemerotecas,
        next_url=next_url,
        precargados=precargados,
    )


# =========================================================
# API PARA HERENCIA DE DATOS TEATRALES
# =========================================================
@app.route("/api/publicacion/details/<nombre>")
@login_required
def api_publicacion_details(nombre):
    proyecto = get_proyecto_activo()
    if not proyecto:
        return jsonify({"error": "No hay proyecto activo"}), 400
    
    pub = Publicacion.query.filter_by(nombre=nombre, proyecto_id=proyecto.id).first()
    if not pub:
        return jsonify({"error": "Publicación no encontrada"}), 404
    
    return jsonify({
        "actos_totales": pub.actos_totales or "",
        "escenas_totales": pub.escenas_totales or "",
        "reparto_total": pub.reparto_total or "",
        "tipo_recurso": pub.tipo_recurso or "",
        "tipo_publicacion": pub.tipo_publicacion or "",
        "periodicidad": pub.frecuencia or pub.periodicidad or "",
        "lugar_publicacion": pub.lugar_publicacion or "",
        "licencia": pub.licencia or ""
    })


# =========================================================
# EDITAR NOTICIA / RECURSO
# =========================================================
@app.route("/editar/<int:id>", methods=["GET", "POST"])
def editar(id):
    ref = db.session.get(Prensa, id)
    if not ref:
        return abort(404)

    idiomas = ["es", "it", "fr", "en", "pt", "ct"]
    tipos_autor = ["anónimo", "firmado", "corresponsal"]

    proyecto = get_proyecto_activo()
    publicaciones_lista = []
    if proyecto:
        publicaciones_lista = [
            p.nombre for p in Publicacion.query.filter_by(proyecto_id=proyecto.id).order_by(Publicacion.nombre.asc()).all()
        ]

    if request.method == "POST":
        # 1. GESTIÓN DE MÚLTIPLES AUTORES Y PSEUDÓNIMO
        ref.pseudonimo = (request.form.get("pseudonimo") or "").strip()
        
        nombres_lista = request.form.getlist("nombre_autor[]")
        apellidos_lista = request.form.getlist("apellido_autor[]")
        tipos_lista = request.form.getlist("tipo_autor[]")
        anonimos_raw = request.form.getlist("anonimo_autor[]")

        # Limpiar autores antiguos
        for aut_old in ref.autores:
            db.session.delete(aut_old)
        
        # Procesamos la nueva lista
        for i in range(len(nombres_lista)):
            nom = (nombres_lista[i] or "").strip()
            ape = (apellidos_lista[i] or "").strip()
            tip = tipos_lista[i] if i < len(tipos_lista) else "firmado"
            es_anon = (i < len(anonimos_raw) and anonimos_raw[i] == "on")
            
            nuevo_aut = AutorPrensa(
                prensa_id=ref.id,
                nombre=nom if not es_anon else None,
                apellido=ape if not es_anon else None,
                tipo=tip,
                es_anonimo=es_anon,
                orden=i
            )
            db.session.add(nuevo_aut)
            
            # Sincronizar el primero para compatibilidad
            if i == 0:
                ref.nombre_autor = nom if not es_anon else None
                ref.apellido_autor = ape if not es_anon else None
                if es_anon:
                    ref.autor = "Anónimo"
                else:
                    if ape and nom: ref.autor = f"{ape}, {nom}"
                    elif ape: ref.autor = ape
                    else: ref.autor = nom

        nombre_pub = (request.form.get("publicacion") or "").strip()
        pub = None
        if nombre_pub:
            pub = Publicacion.query.filter_by(nombre=nombre_pub, proyecto_id=proyecto.id).first()
            if not pub:
                pub = Publicacion(nombre=nombre_pub, proyecto_id=proyecto.id)
                db.session.add(pub)

            campos_pub = {
                "descripcion": request.form.get("descripcion_publicacion"),
                "tipo_recurso": request.form.get("tipo_recurso"),
                "ciudad": request.form.get("ciudad"),
                "idioma": request.form.get("idioma"),
                "licencia": request.form.get("licencia"),
                "formato_fuente": request.form.get("formato_fuente"),
                "pais_publicacion": request.form.get("pais_publicacion"),
                "editorial": request.form.get("editorial"),
                "actos_totales": request.form.get("actos_totales"),
                "escenas_totales": request.form.get("escenas_totales"),
                "reparto_total": request.form.get("reparto_total"),
                "tipo_publicacion": request.form.get("tipo_publicacion"),
                "periodicidad": request.form.get("periodicidad"),
                "lugar_publicacion": request.form.get("lugar_publicacion"),
            }
            for campo, valor in campos_pub.items():
                if valor is not None:
                    setattr(pub, campo, valor)

            db.session.flush()

            # HERENCIA DE AUTORÍA EN EDICIÓN: Si no se enviaron autores en el form, heredar de la publicación
            form_has_authors = any(n.strip() or a.strip() for n, a in zip(nombres_lista, apellidos_lista))
            if not form_has_authors and pub and pub.autores:
                # Limpiar lo que se haya procesado antes (que estarían vacíos según form_has_authors)
                for aut_added in ref.autores:
                    db.session.delete(aut_added)
                
                for i, aut_pub in enumerate(pub.autores):
                    nuevo_aut = AutorPrensa(
                        prensa_id=ref.id,
                        nombre=aut_pub.nombre,
                        apellido=aut_pub.apellido,
                        tipo=aut_pub.tipo,
                        es_anonimo=aut_pub.es_anonimo,
                        orden=aut_pub.orden
                    )
                    db.session.add(nuevo_aut)
                    if i == 0:
                        ref.nombre_autor = aut_pub.nombre
                        ref.apellido_autor = aut_pub.apellido
                        if aut_pub.es_anonimo:
                            ref.autor = "Anónimo"
                        else:
                            if aut_pub.apellido and aut_pub.nombre: ref.autor = f"{aut_pub.apellido}, {aut_pub.nombre}"
                            elif aut_pub.apellido: ref.autor = aut_pub.apellido
                            else: ref.autor = aut_pub.nombre

        # Asignar campos principales de la noticia desde el formulario
        campo_map = [
            "titulo",
            "fecha_original",
            "numero",
            "pagina_inicio",
            "pagina_fin",
            "paginas",
            "url",
            "fecha_consulta",
            "idioma",
            "licencia",
            "temas",
            "notas",
            "contenido",
            "texto_original",
            "edicion",
            "ciudad",
            "pais_publicacion",
            "fuente",
            "formato_fuente",
            "tipo_recurso",
            "editorial",
            "isbn",
            "issn",
            "volumen",
            "doi",
            "lugar_publicacion",
            "seccion",
            "palabras_clave",
            "pseudonimo",
            "actos_totales",
            "escenas_totales",
            "reparto_total",
            "escenas",
            "reparto",
            "tipo_publicacion",
            "periodicidad",
        ]
        for campo in campo_map:
            if campo == "temas":
                valor = ", ".join(request.form.getlist("temas"))
            else:
                valor = request.form.get(campo)
                
            if valor is not None:
                setattr(ref, campo, valor)

        # Año (int)
        anio_val = request.form.get("anio")
        if anio_val:
            try:
                ref.anio = int(anio_val)
            except ValueError:
                ref.anio = None

        # 🔒 VALIDACIÓN DE FECHAS (fecha_original y fecha_consulta)
        fecha_original = (request.form.get("fecha_original") or "").strip()
        fecha_consulta = (request.form.get("fecha_consulta") or "").strip()

        # Validar fecha_original (relajado para libros: permite Mes/Año)
        if request.form.get("tipo_recurso") == "libro":
            valida, error_msg = True, None
        else:
            valida, error_msg = validar_fecha_ddmmyyyy(fecha_original)
            
        if not valida:
            flash(f"⚠️ Fecha Original inválida: {error_msg}", "danger")
            return render_template(
                "editar.html",
                ref=ref,
                idiomas=idiomas,
                tipos_autor=tipos_autor,
                publicaciones=publicaciones_lista,
                next_url=normalizar_next(request.args.get("next")),
                nombre_autor_val=nombre,
                apellido_autor_val=apellido,
            )

        # Validar fecha_consulta
        valida, error_msg = validar_fecha_ddmmyyyy(fecha_consulta)
        if not valida:
            flash(f"⚠️ Fecha Consulta inválida: {error_msg}", "danger")
            return render_template(
                "editar.html",
                ref=ref,
                idiomas=idiomas,
                tipos_autor=tipos_autor,
                publicaciones=publicaciones_lista,
                next_url=normalizar_next(request.args.get("next")),
                nombre_autor_val=nombre,
                apellido_autor_val=apellido,
            )

        # Incluido (checkbox)
        ref.incluido = (request.form.get("incluido") == "si") or (
            "incluido" in request.form and request.form.get("incluido") is None
        )

        # Número de referencia bibliográfica (condicional)
        numero_ref_str = request.form.get("numero_referencia", "").strip()
        ref.numero_referencia = (
            int(numero_ref_str) if numero_ref_str and numero_ref_str.isdigit() else None
        )

        # Asociación a publicación
        ref.publicacion = nombre_pub
        ref.id_publicacion = pub.id_publicacion if pub else None

        # [MODIFICADO] Guardar es_referencia
        ref.es_referencia = (request.form.get("es_referencia") == "si")

        # [MODIFICADO] GESTIÓN DE IMAGEN EN EDITAR
        imagenes = request.files.getlist("imagen_scan")
        for imagen in imagenes:
            if imagen and allowed_file(imagen.filename):
                nombre_imagen = secure_filename(
                    f"{id}_{datetime.now().timestamp()}_{imagen.filename}"
                )
                imagen.save(os.path.join(app.config["UPLOAD_FOLDER"], nombre_imagen))
                nueva_imagen = ImagenPrensa(prensa_id=ref.id, filename=nombre_imagen)
                db.session.add(nueva_imagen)

        db.session.commit()
        flash("💾 Cambios guardados correctamente.", "info")

        next_raw = request.args.get("next")
        destino = normalizar_next(next_raw) or url_for("index")
        return redirect(destino)

    # Recuperar nombre y apellido desde los nuevos campos si existen, si no, usar separación antigua
    if ref.nombre_autor is not None or ref.apellido_autor is not None:
        nombre_autor_val = ref.nombre_autor or ""
        apellido_autor_val = ref.apellido_autor or ""
    else:
        autor_guardado = (ref.autor or "").strip()
        nombre_autor_val, apellido_autor_val = "", ""
        if autor_guardado:
            n, a = separar_autor(autor_guardado)
            nombre_autor_val, apellido_autor_val = n, a

    descripcion_medio = None
    if ref.id_publicacion:
        pub = db.session.get(Publicacion, ref.id_publicacion)
        if pub:
            db.session.refresh(pub)  # ¡CORRECCIÓN! Refresca el objeto desde la BD
        if pub and pub.descripcion:
            descripcion_medio = pub.descripcion
    elif ref.publicacion:
        pub = Publicacion.query.filter_by(nombre=ref.publicacion, proyecto_id=ref.proyecto_id).first()
        if pub and pub.descripcion:
            descripcion_medio = pub.descripcion

    setattr(ref, "descripcion_publicacion", descripcion_medio)

    temas_all = valores_unicos(Prensa.temas, proyecto.id)
    temas_sel = [t.strip() for t in (ref.temas or "").split(",") if t.strip()]

    autores_data = []
    for a in ref.autores:
        n_clean = (a.nombre or "").strip()
        a_clean = (a.apellido or "").strip()
        
        # Búsqueda robusta en AutorBio (ignorar espacios y mayúsculas)
        bio = AutorBio.query.filter(
            func.trim(AutorBio.nombre).ilike(n_clean),
            func.trim(AutorBio.apellido).ilike(a_clean),
            AutorBio.proyecto_id == proyecto.id
        ).first()
        
        autores_data.append({
            'nombre': a.nombre or '',
            'apellido': a.apellido or '',
            'tipo': a.tipo or 'firmado',
            'es_anonimo': a.es_anonimo,
            'pseudonimo': bio.seudonimo if bio else ''
        })
    autores_json = json.dumps(autores_data)

    return render_template(
        "editar.html",
        ref=ref,
        idiomas=idiomas,
        tipos_autor=tipos_autor,
        publicaciones=publicaciones_lista,
        temas=temas_all,
        temas_sel=temas_sel,
        next_url=normalizar_next(request.args.get("next")),
        nombre_autor_val=nombre_autor_val,
        apellido_autor_val=apellido_autor_val,
        autores_json=autores_json
    )



# =========================================================
# CONSISTENCIA DE DATOS (LA RUTA QUE FALTABA ANTES)
# =========================================================
@app.route("/consistencia")
def consistencia_datos():
    from utils import get_proyecto_activo
    proyecto = get_proyecto_activo()
    if not proyecto:
        flash("Debes seleccionar un proyecto para verificar la consistencia de datos.", "warning")
        return redirect(url_for('proyectos.listar'))

    # ===== 1. DUPLICADOS EXACTOS DE CONTENIDO =====
    subquery_dups = (
        db.session.query(Prensa.contenido)
        .filter(Prensa.contenido.isnot(None), Prensa.contenido != "")
        .filter(Prensa.proyecto_id == proyecto.id)
        .group_by(Prensa.contenido)
        .having(func.count(Prensa.contenido) > 1)
        .all()
    )
    duplicate_contents = [c[0] for c in subquery_dups]

    registros_duplicados_contenido = (
        db.session.query(Prensa)
        .filter(Prensa.contenido.in_(duplicate_contents))
        .filter(Prensa.proyecto_id == proyecto.id)
        .order_by(Prensa.contenido, Prensa.publicacion)
        .all()
    )

    # ===== 2. DUPLICADOS INTELIGENTES (Título + Fecha + Publicación) =====
    # Analiza TODOS los registros (puede tardar varios minutos)
    todos_registros = Prensa.query.filter_by(proyecto_id=proyecto.id).order_by(Prensa.id.desc()).all()
    grupos_duplicados = []
    procesados = set()

    # Agrupar por publicación primero para optimizar
    from collections import defaultdict

    por_publicacion = defaultdict(list)
    for reg in todos_registros:
        if reg.publicacion:
            por_publicacion[reg.publicacion.strip().lower()].append(reg)

    # Comparar registros de la misma publicación
    for publicacion, registros_pub in por_publicacion.items():
        if len(registros_pub) < 2:
            continue

        for i, reg1 in enumerate(registros_pub):
            if reg1.id in procesados:
                continue

            grupo_actual = [reg1]

            for reg2 in registros_pub[i + 1 :]:
                if reg2.id in procesados:
                    continue

                # Criterios de similitud
                titulo_similar = similitud_titulos(
                    reg1.titulo, reg2.titulo, umbral=0.85
                )
                fecha_similar = fechas_similares(
                    reg1.fecha_original, reg2.fecha_original, tolerancia_dias=1
                )

                # SOLO es duplicado si AMBOS: título similar Y fecha similar
                # (Si tienen fechas distintas, NO son duplicados aunque el título sea similar)
                if titulo_similar and fecha_similar:
                    grupo_actual.append(reg2)
                    procesados.add(reg2.id)

            # Si encontramos al menos un duplicado, añadir grupo
            if len(grupo_actual) > 1:
                grupos_duplicados.append(grupo_actual)
                procesados.add(reg1.id)

    # ===== 3. OTROS CHECKS DE CALIDAD =====
    sin_anio = Prensa.query.filter(Prensa.anio.is_(None)).filter(Prensa.proyecto_id == proyecto.id).all()
    sin_publicacion_enlazada = Prensa.query.filter(
        Prensa.id_publicacion.is_(None)
    ).filter(Prensa.proyecto_id == proyecto.id).all()

    prensa_sin_url = Prensa.query.filter(
        Prensa.tipo_recurso == "prensa", or_(Prensa.url.is_(None), Prensa.url == "")
    ).filter(Prensa.proyecto_id == proyecto.id).all()

    # FECHAS INVÁLIDAS (mes > 12, día > 31, etc.)
    import re as _re_val

    def _fecha_invalida(f):
        if not f:
            return False
        m = _re_val.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})$", f.strip())
        if not m:
            return True  # Formato incorrecto
        d, mth, y = map(int, m.groups())
        if not (1 <= mth <= 12):
            return True
        if not (1800 <= y <= 2100):
            return True
        dias_mes = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        if (y % 4 == 0 and y % 100 != 0) or (y % 400 == 0):
            dias_mes[1] = 29
        if not (1 <= d <= dias_mes[mth - 1]):
            return True
        return False

    todos_con_fecha = Prensa.query.filter(Prensa.fecha_original.isnot(None)).filter(Prensa.proyecto_id == proyecto.id).all()
    fechas_invalidas = [r for r in todos_con_fecha if _fecha_invalida(r.fecha_original)]

    return render_template(
        "consistencia.html",
        registros_duplicados_contenido=registros_duplicados_contenido,
        grupos_duplicados_inteligentes=grupos_duplicados,
        sin_anio=sin_anio,
        sin_publicacion_enlazada=sin_publicacion_enlazada,
        prensa_sin_url=prensa_sin_url,
        fechas_invalidas=fechas_invalidas,
        total_duplicados_contenido=len(duplicate_contents),
        total_grupos_inteligentes=len(grupos_duplicados),
    )


# =========================================================
# VER CITA BIBLIOGRÁFICA
# =========================================================
@app.route("/cita/<int:id>")
def ver_cita(id):
    """Muestra la vista previa de la cita bibliográfica de una referencia."""
    ref = db.session.get(Prensa, id)
    if not ref:
        return abort(404)
    
    # La plantilla cita.html maneja el formateo con citation-generator.js
    return render_template('cita.html', ref=ref)


# =========================================================
# IMPRIMIR / EXPORTAR PDF
# =========================================================
def _strip_html(value):
    """Elimina etiquetas HTML del texto de forma robusta para el PDF."""
    if not value:
        return ""
    # Reemplazar etiquetas de bloque (apertura y cierre) por saltos de línea
    value = re.sub(r'</?(p|br|div|h[1-6]|li|tr|blockquote)[^>]*>', '\n', value, flags=re.IGNORECASE)
    # Eliminar el resto de etiquetas (como <span>, <a>, <img>, etc.)
    clean = re.compile('<[^>]*>')
    value = re.sub(clean, '', value)
    # Colapsar múltiples saltos de línea (máximo 2 para párrafos)
    value = re.sub(r'\n\s*\n+', '\n\n', value)
    return value.strip()

def _safe_text(value):
    """Escapa texto dinámico para evitar errores del parser XML de ReportLab."""
    from xml.sax.saxutils import escape as xml_escape
    return xml_escape(str(value or ""), {'"': "&quot;", "'": "&#39;"})

def _safe_text_with_breaks(value):
    # Primero quitamos HTML, luego escapamos para XML y finalmente preservamos saltos de línea
    text = _strip_html(value)
    return _safe_text(text).replace("\n", "<br/>")

@app.route("/imprimir/<int:id>")
def imprimir_pdf(id):
    ref = db.session.get(Prensa, id)
    if not ref:
        return abort(404)

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="Titulo", fontSize=14, leading=16, spaceAfter=10, alignment=TA_CENTER
        )
    )
    styles.add(
        ParagraphStyle(
            name="Campo", fontSize=10, leading=12, spaceAfter=4, alignment=TA_JUSTIFY
        )
    )
    styles.add(
        ParagraphStyle(
            name="Contenido",
            fontSize=10,
            leading=14,
            spaceBefore=8,
            alignment=TA_JUSTIFY,
        )
    )
    styles.add(
        ParagraphStyle(name="Pie", fontSize=8, alignment=TA_RIGHT, textColor="gray")
    )

    story = []

    membrete_path = os.path.join(app.static_folder, "img", "hesiox_cabecera.png")
    if os.path.exists(membrete_path):
        # Ajustamos el tamaño para que se vea bien como cabecera (más ancho, menos alto)
        story.append(Image(membrete_path, width=7 * cm, height=2.5 * cm))
        story.append(Spacer(1, 12))

    story.append(Paragraph(f"<b>{_safe_text(ref.titulo or '[Sin título]')}</b>", styles["Titulo"]))
    if ref.autor:
        story.append(Paragraph(f"<i>{_safe_text(ref.autor)}</i>", styles["Campo"]))
    story.append(Spacer(1, 10))

    # [MODIFICADO] Insertar Imagen en PDF Individual
    if ref.imagen_scan:
        img_path = os.path.join(app.config["UPLOAD_FOLDER"], ref.imagen_scan)
        if os.path.exists(img_path):
            story.append(
                Image(img_path, width=10 * cm, height=10 * cm, kind="proportional")
            )
            story.append(Spacer(1, 10))

    paginas = ""
    if ref.pagina_inicio and ref.pagina_fin:
        paginas = f"{ref.pagina_inicio}–{ref.pagina_fin}"
    elif ref.pagina_inicio:
        paginas = ref.pagina_inicio
    elif ref.paginas:
        paginas = ref.paginas

    campos = [
        ("Publicación", ref.publicacion or ""),
        ("Tipo de recurso", ref.tipo_recurso or ""),
        ("Ciudad", ref.ciudad or ""),
        ("País", ref.pais_publicacion or ""),
        ("Fecha original", ref.fecha_original or ""),
        ("Idioma", ref.idioma or ""),
        ("Número", ref.numero or ""),
        ("Páginas", paginas or ""),
        ("Licencia", ref.licencia or ""),
        ("Fuente (Institución)", ref.fuente or ""),
        ("Formato Fuente", ref.formato_fuente or ""),
        ("Temas", ref.temas or ""),
        ("URL", ref.url or ""),
        ("Fecha de consulta", ref.fecha_consulta or ""),
    ]

    for campo, valor in campos:
        if valor:
            story.append(Paragraph(f"<b>{_safe_text(campo)}:</b> {_safe_text(valor)}", styles["Campo"]))

    story.append(Spacer(1, 10))

    descripcion_medio = None
    if ref.id_publicacion:
        pub = db.session.get(Publicacion, ref.id_publicacion)
        if pub and pub.descripcion:
            descripcion_medio = pub.descripcion

    if descripcion_medio:
        story.append(Paragraph("<b>Descripción del medio:</b>", styles["Campo"]))
        story.append(Paragraph(_safe_text_with_breaks(descripcion_medio), styles["Contenido"]))

    if ref.contenido:
        story.append(Paragraph("<b>Contenido / Resumen:</b>", styles["Campo"]))
        story.append(Paragraph(_safe_text_with_breaks(ref.contenido), styles["Contenido"]))
        story.append(Spacer(1, 10))

    # [MODIFICADO] TEXTO ORIGINAL EN PDF
    if ref.texto_original:
        story.append(
            Paragraph("<b>Texto Original (Idioma Nativo):</b>", styles["Campo"])
        )
        story.append(Paragraph(_safe_text_with_breaks(ref.texto_original), styles["Contenido"]))
        story.append(Spacer(1, 10))

    if ref.notas:
        story.append(Paragraph("<b>Notas personales:</b>", styles["Campo"]))
        story.append(Paragraph(_safe_text_with_breaks(ref.notas), styles["Contenido"]))
        story.append(Spacer(1, 10))

    story.append(Spacer(1, 20))
    fecha_actual = datetime.now().strftime("%d/%m/%Y %H:%M")
    pie = f"<i>Exportado desde el Proyecto HESIOX — {fecha_actual}</i>"
    story.append(Paragraph(pie, styles["Pie"]))

    doc.build(story)
    buffer.seek(0)

    return send_file(
        buffer,
        mimetype="application/pdf",
        as_attachment=False,
        download_name=f"Referencia_{ref.id}.pdf",
    )


@app.route("/imprimir_lote", methods=["POST"])
def imprimir_lote():
    ids = request.json.get("ids", [])
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )
    story = []
    styles = getSampleStyleSheet()
    
    # Estilos personalizados
    styles.add(ParagraphStyle(name='TituloLote', parent=styles['Heading1'], fontSize=16, spaceAfter=12))
    styles.add(ParagraphStyle(name='ContenidoLote', parent=styles['Normal'], fontSize=10, leading=14, alignment=TA_JUSTIFY))



    for idx, id in enumerate(ids):
        ref = db.session.get(Prensa, id)
        if ref:
            # Logo HesiOX en cada inicio de noticia del lote
            logo_path = os.path.join(app.static_folder, "img", "hesiox_cabecera.png")
            if os.path.exists(logo_path):
                story.append(Image(logo_path, width=7 * cm, height=2.5 * cm))
                story.append(Spacer(1, 0.5 * cm))
            
            story.append(Paragraph(_safe_text(ref.titulo), styles["TituloLote"]))
            
            if ref.contenido:
                story.append(Paragraph(_safe_text_with_breaks(ref.contenido), styles["ContenidoLote"]))
            
            if ref.texto_original:
                story.append(Paragraph("<b>Texto Original:</b>", styles["Heading4"]))
                story.append(Paragraph(_safe_text_with_breaks(ref.texto_original), styles["ContenidoLote"]))
                
            if ref.imagen_scan:
                img_path = os.path.join(app.config["UPLOAD_FOLDER"], ref.imagen_scan)
                if os.path.exists(img_path):
                    story.append(Spacer(1, 0.5 * cm))
                    story.append(Image(img_path, width=10 * cm, height=10 * cm, kind="proportional"))
            
            if idx < len(ids) - 1:
                story.append(PageBreak())

    doc.build(story)
    buffer.seek(0)
    return send_file(
        buffer,
        mimetype="application/pdf",
        as_attachment=True,
        download_name="dossier_hesiox.pdf",
    )


# =========================================================
# EXPORTAR CSV / BIBTEX
# =========================================================
@app.route("/exportar")
@login_required
def exportar():
    formato = request.args.get("formato", "csv")
    ids_raw = request.args.get("ids")
    
    # Obtener proyecto activo para seguridad
    from app import get_proyecto_activo
    proyecto = get_proyecto_activo()
    if not proyecto:
        flash("Debes seleccionar un proyecto.", "warning")
        return redirect(url_for("dashboard"))

    query = Prensa.query.filter_by(proyecto_id=proyecto.id)
    
    # --- Aplicar Filtros Sincronizados con la Tabla ---
    filtros = {
        k: request.args.get(k, "").strip()
        for k in [
            "autor", "fecha_original", "numero", "publicacion",
            "ciudad", "pais_publicacion", "temas", "busqueda",
            "fecha_desde", "fecha_hasta"
        ]
    }
    filtros["incluido"] = request.args.get("incluido", "todos")

    if ids_raw:
        try:
            ids = [int(x) for x in ids_raw.split(",") if x.strip()]
            if ids:
                query = query.filter(Prensa.id.in_(ids))
        except ValueError:
            pass
    else:
        # Solo aplicar filtros si no se exportan IDs específicos
        for k, v in filtros.items():
            if not v or k in ["busqueda", "incluido"]:
                continue
            
            if k == "publicacion":
                query = query.filter(Prensa.publicacion == v)
            elif k == "pais_publicacion":
                query = query.filter(Prensa.pais_publicacion == v)
            elif k == "ciudad":
                query = query.filter(Prensa.ciudad == v)
            elif k == "autor":
                query = query.filter(or_(Prensa.nombre_autor.ilike(f"%{v}%"), Prensa.apellido_autor.ilike(f"%{v}%")))
            elif k == "fecha_original":
                # Lógica de fechas (simplificada pero compatible con los formatos de /filtrar)
                query = query.filter(Prensa.fecha_original.ilike(f"%{v}%"))
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
                query = query.filter(or_(
                    cast(Prensa.titulo, String).ilike(term),
                    cast(Prensa.contenido, String).ilike(term),
                    cast(Prensa.texto_original, String).ilike(term),
                    cast(Prensa.nombre_autor, String).ilike(term),
                    cast(Prensa.publicacion, String).ilike(term),
                    cast(Prensa.resumen, String).ilike(term),
                    cast(Prensa.palabras_clave, String).ilike(term),
                    cast(Prensa.temas, String).ilike(term),
                    cast(Prensa.notas, String).ilike(term)
                ))

        if filtros["incluido"] == "si":
            query = query.filter(Prensa.incluido.is_(True))
        elif filtros["incluido"] == "no":
            query = query.filter(Prensa.incluido.is_(False))

    query = ordenar_por_fecha(query, descendente=False)
    resultados = query.all()

    def autor_para_bibtex(autor_raw):
        n, a = separar_autor(autor_raw or "")
        nom = " ".join(capitalizar_palabra(x) for x in n.split()) if n else ""
        ape = capitalizar_palabra(a)
        if ape and nom:
            return f"{ape}, {nom}"
        elif ape:
            return ape
        elif nom:
            return nom
        else:
            return "Anónimo"

    def extraer_anio(fecha_texto):
        _, solo_anio = try_parse_fecha_ddmmyyyy(fecha_texto or "")
        if solo_anio:
            return str(solo_anio)
        m = re.search(r"(\d{4})", fecha_texto or "")
        return m.group(1) if m else "s.f."

    if formato == "json_sirio":
        export_data = []
        for r in resultados:
            # Noticia data
            noticia_dict = {c.name: getattr(r, c.name) for c in r.__table__.columns}
            # Remove project/user specific IDs that might clash
            for k in ['id', 'proyecto_id', 'id_publicacion', 'creado_en', 'actualizado_en']:
                noticia_dict.pop(k, None)
            
            # Publicacion data
            pub_dict = None
            hem_dict = None
            if r.publicacion_rel:
                pub = r.publicacion_rel
                pub_dict = {c.name: getattr(pub, c.name) for c in pub.__table__.columns}
                for k in ['id_publicacion', 'proyecto_id', 'hemeroteca_id', 'creado_en', 'actualizado_en']:
                    pub_dict.pop(k, None)
                    
                if pub.hemeroteca_rel:
                    hem = pub.hemeroteca_rel
                    hem_dict = {c.name: getattr(hem, c.name) for c in hem.__table__.columns}
                    for k in ['id', 'proyecto_id', 'creado_en', 'actualizado_en']:
                        hem_dict.pop(k, None)
            
            export_data.append({
                "noticia": noticia_dict,
                "publicacion": pub_dict,
                "hemeroteca": hem_dict
            })
            
        return Response(
            json.dumps(export_data, indent=2, default=str),
            mimetype="application/json",
            headers={"Content-Disposition": "attachment; filename=export_sirio.json"},
        )

    elif formato == "csv_sirio":
        output = io.StringIO()
        writer = csv.writer(output, delimiter=",", quoting=csv.QUOTE_ALL)
        
        # Comprehensive header with ABSOLUTELY ALL metadata
        header = [
            # Hemeroteca
            "Hem_Nombre", "Hem_Institucion", "Hem_Pais", "Hem_Provincia", "Hem_Ciudad", "Hem_URL", "Hem_ResumenCorpus",
            # Publicacion
            "Pub_Nombre", "Pub_Ciudad", "Pub_Provincia", "Pub_Pais", "Pub_Idioma", "Pub_Licencia", "Pub_URL", 
            "Pub_Tipo", "Pub_Frecuencia", "Pub_Fuente",
            # Prensa (Noticia)
            "Noticia_Titulo", "Noticia_Fecha", "Noticia_Anio", "Noticia_Autor_Nom", "Noticia_Autor_Ape", 
            "Noticia_Autor_Tipo", "Noticia_Ciudad", "Noticia_Pais", "Noticia_Numero", "Noticia_Edicion",
            "Noticia_PaginaInicio", "Noticia_PaginaFin", "Noticia_PaginasTotales", "Noticia_TipoRecurso",
            "Noticia_Idioma", "Noticia_Temas", "Noticia_PalabrasClave", "Noticia_Resumen", "Noticia_URL", 
            "Noticia_FechaConsulta", "Noticia_Licencia", "Noticia_Notas", "Noticia_Contenido",
            "Noticia_ISSN", "Noticia_ISBN", "Noticia_DOI", "Noticia_Volumen", "Noticia_Seccion",
            "Noticia_Editorial", "Noticia_Editor", "Noticia_LugarPub", "Noticia_Fuente", 
            "Noticia_NombreInvestigador", "Noticia_UniversidadInvestigador",
            "Noticia_FuenteCondiciones", "Noticia_NumeroReferencia", "Noticia_FormatoFuente",
            "Noticia_ReferenciasRelacionadas", "Noticia_ArchivoPDF", "Noticia_ImagenScan",
            "Noticia_TextoOriginal", "Noticia_DescripcionPub", "Noticia_Incluido"
        ]
        writer.writerow(header)
        
        for r in resultados:
            pub = r.publicacion_rel
            hem = pub.hemeroteca_rel if pub else None
            
            row = [
                # Hemeroteca
                hem.nombre if hem else "", hem.institucion if hem else "", hem.pais if hem else "", 
                hem.provincia if hem else "", hem.ciudad if hem else "", hem.url if hem else "", 
                hem.resumen_corpus if hem else "",
                # Publicacion
                pub.nombre if pub else r.publicacion, pub.ciudad if pub else r.ciudad, 
                pub.provincia if pub else "", pub.pais_publicacion if pub else r.pais_publicacion, 
                pub.idioma if pub else "", pub.licencia if pub else r.licencia, pub.url_publi if pub else "", 
                pub.tipo_recurso if pub else r.tipo_recurso, pub.frecuencia if pub else "", pub.fuente if pub else r.fuente,
                # Prensa (Noticia)
                r.titulo or "", r.fecha_original or "", r.anio or "", r.nombre_autor or "", r.apellido_autor or "",
                r.tipo_autor or "", r.ciudad or "", r.pais_publicacion or (pub.pais_publicacion if pub else ""),
                r.numero or "", r.edicion or "", r.pagina_inicio or "", r.pagina_fin or "", r.paginas or "", 
                r.tipo_recurso or (pub.tipo_recurso if pub else ""), r.idioma or (pub.idioma if pub else ""), 
                r.temas or "", r.palabras_clave or "", r.resumen or "", r.url or "", r.fecha_consulta or "", 
                r.licencia or "", r.notas or "", (r.contenido or "").replace("\n", " "),
                r.issn or "", r.isbn or "", r.doi or "", r.volumen or "", r.seccion or "",
                r.editorial or "", r.editor or "", r.lugar_publicacion or "", r.fuente or "",
                r.nombre_investigador or "", r.universidad_investigador or "",
                r.fuente_condiciones or "", str(r.numero_referencia or ""), r.formato_fuente or "",
                r.referencias_relacionadas or "", r.archivo_pdf or "", r.imagen_scan or "",
                r.texto_original or "", r.descripcion_publicacion or "", "1" if r.incluido else "0"
            ]
            writer.writerow(row)
            
        output.seek(0)
        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment; filename=export_sirio.csv"},
        )

    elif formato == "txt":
        output = io.StringIO()
        for r in resultados:
            if r.id is None:
                continue
            titulo = r.titulo or "[Sin título]"
            contenido = r.contenido or ""
            output.write(f"Título: {titulo}\n")
            output.write(f"Contenido:\n{contenido}\n")
            output.write("\n" + "="*40 + "\n\n")
        output.seek(0)
        return Response(
            output.getvalue(),
            mimetype="text/plain",
            headers={
                "Content-Disposition": "attachment; filename=noticias.txt"
            },
        )

    if formato == "csv":
        output = io.StringIO()
        writer = csv.writer(output, delimiter=",", quoting=csv.QUOTE_ALL)
        # [MODIFICADO] Añadidas columnas Imagen y Texto Original
        writer.writerow(
            [
                "ID",
                "Título",
                "Publicación",
                "Fecha",
                "Autor",
                "Número",
                "Ciudad",
                "País_publicacion",
                "Idioma",
                "Tipo_recurso",
                "Formato_fuente",
                "Incluido",
                "Temas",
                "Notas",
                "URL",
                "Fecha_consulta",
                "Archivo_PDF",
                "Referencias_relacionadas",
                "Páginas",
                "ISSN",
                "ISBN",
                "DOI",
                "Editorial",
                "Lugar_publicacion",
                "Volumen",
                "Seccion",
                "Palabras_clave",
                "Resumen",
                "Licencia",
                "Descripcion_publicacion",
                "Fuente",
                "Contenido",
                "Imagen",
                "Texto_Original",
                "Hem_Provincia",
                "Hem_ResumenCorpus",
                "Pub_Provincia",
                "Pub_Frecuencia",
                "Pub_Fuente",
            ]
        )
        for r in resultados:
            try:
                if r.id is None:
                    continue
                r.id = int(r.id)
            except ValueError:
                continue

            desc_pub = r.publicacion_rel.descripcion if r.publicacion_rel else ""
            # Soporte para Prensa: autor puede ser nombre_autor + apellido_autor
            if hasattr(r, 'autor'):
                autor = r.autor or ""
            else:
                nombre = getattr(r, 'nombre_autor', None) or ""
                apellido = getattr(r, 'apellido_autor', None) or ""
                autor = f"{apellido}, {nombre}".strip(', ') if (nombre or apellido) else ""
            writer.writerow([
                r.id or "",
                r.titulo or "",
                r.publicacion or "",
                r.fecha_original or "",
                autor,
                r.numero or "",
                r.ciudad or "",
                r.pais_publicacion or "",
                r.idioma or "",
                r.tipo_recurso or "",
                r.formato_fuente or "",
                "sí" if r.incluido else "no",
                r.temas or "",
                (r.notas or "").replace("\n", " ").strip(),
                r.url or "",
                r.fecha_consulta or "",
                r.archivo_pdf or "",
                r.referencias_relacionadas or "",
                r.paginas or "",
                r.issn or "",
                r.isbn or "",
                r.doi or "",
                r.editorial or "",
                r.lugar_publicacion or "",
                r.volumen or "",
                r.seccion or "",
                r.palabras_clave or "",
                (r.resumen or "").replace("\n", " ").strip(),
                r.licencia or "",
                (desc_pub or "").replace("\n", " ").strip(),
                r.fuente or "",
                r.contenido or "",
                r.imagen_scan or "",
                r.texto_original or "",
                hem.provincia if hem else "",
                hem.resumen_corpus if hem else "",
                pub.provincia if pub else "",
                pub.frecuencia if pub else "",
                pub.fuente if pub else "",
            ])
        output.seek(0)
        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={
                "Content-Disposition": "attachment; filename=bibliografia_completa.csv"
            },
        )

    elif formato == "bib":
        entries = []
        for r in resultados:
            try:
                if r.id is None:
                    continue
                r.id = int(r.id)
            except ValueError:
                continue

            # Soporte para Prensa: autor puede ser nombre_autor + apellido_autor
            if hasattr(r, 'autor'):
                autor_raw = r.autor or ""
            else:
                nombre = getattr(r, 'nombre_autor', None) or ""
                apellido = getattr(r, 'apellido_autor', None) or ""
                autor_raw = f"{apellido}, {nombre}".strip(', ') if (nombre or apellido) else ""
            autor_bib = autor_para_bibtex(autor_raw)
            anyo_bib = extraer_anio(r.fecha_original)
            desc_pub = r.publicacion_rel.descripcion if r.publicacion_rel else ""
            clave_base = ""
            if "," in autor_bib:
                clave_base = autor_bib.split(",")[0]
            else:
                partes = autor_bib.split()
                clave_base = partes[0] if partes else "Anonimo"
            key = f"{clave_base}_{anyo_bib}"

            entry = f"@article{{{key},\n"
            entry += f" \ttitle = {{{r.titulo or '[Sin título]'}}},\n"
            entry += f" \tauthor = {{{autor_bib}}},\n"
            if r.publicacion:
                entry += f" \tjournal = {{{r.publicacion}}},\n"
            if r.editorial:
                entry += f" \tpublisher = {{{r.editorial}}},\n"
            if r.lugar_publicacion:
                entry += f" \taddress = {{{r.lugar_publicacion}}},\n"
            entry += f" \tyear = {{{anyo_bib}}},\n"
            if r.volumen:
                entry += f" \tvolume = {{{r.volumen}}},\n"
            if r.numero:
                entry += f" \tnumber = {{{r.numero}}},\n"
            if r.isbn:
                entry += f" \tisbn = {{{r.isbn}}},\n"
            if r.issn:
                entry += f" \tissn = {{{r.issn}}},\n"
            if r.doi:
                entry += f" \tdoi = {{{r.doi}}},\n"
            if r.pagina_inicio or r.pagina_fin:
                entry += f" \tpages = {{{(r.pagina_inicio or '')}-{(r.pagina_fin or '')}}},\n"
            if r.url:
                entry += f" \turl = {{{r.url}}},\n"
            if r.fecha_consulta:
                entry += f" \tnote = {{Consultado el {r.fecha_consulta}}},\n"
            if r.pais_publicacion:
                entry += f" \tlocation = {{{r.pais_publicacion}}},\n"
            if r.formato_fuente:
                entry += f" \thowpublished = {{{r.formato_fuente}}},\n"
            if r.archivo_pdf:
                entry += f" \tfile = {{{r.archivo_pdf}}},\n"
            if r.referencias_relacionadas:
                entry += f" \trelated = {{{r.referencias_relacionadas}}},\n"
            if desc_pub:
                entry += f" \tnote = {{{(desc_pub or '').replace('{', '').replace('}', '')}}},\n"
            entry += "}\n\n"
            entries.append(entry)

        return Response(
            "".join(entries),
            mimetype="text/plain",
            headers={"Content-Disposition": "attachment; filename=bibliografia.bib"},
        )

    elif formato == 'xml_sirio':
        # XML Sirio (full fidelity)
        import xml.etree.ElementTree as ET
        root = ET.Element("BibliotecaSirio")
        root.set("proyecto", proyecto.nombre)
        root.set("fecha_exportacion", datetime.now().isoformat())

        for r in resultados:
            pub = r.publicacion_rel
            hem = pub.hemeroteca_rel if pub else None
            
            noticia_el = ET.SubElement(root, "Noticia")
            noticia_el.set("id", str(r.id))
            
            # Hemeroteca
            hem_el = ET.SubElement(noticia_el, "Hemeroteca")
            ET.SubElement(hem_el, "Nombre").text = hem.nombre if hem else ""
            ET.SubElement(hem_el, "Institucion").text = hem.institucion if hem else ""
            ET.SubElement(hem_el, "Pais").text = hem.pais if hem else ""
            ET.SubElement(hem_el, "Provincia").text = hem.provincia if hem else ""
            ET.SubElement(hem_el, "Ciudad").text = hem.ciudad if hem else ""
            ET.SubElement(hem_el, "URL").text = hem.url if hem else ""
            ET.SubElement(hem_el, "ResumenCorpus").text = hem.resumen_corpus if hem else ""
            
            # Publicacion
            pub_el = ET.SubElement(noticia_el, "Publicacion")
            ET.SubElement(pub_el, "Nombre").text = pub.nombre if pub else r.publicacion
            ET.SubElement(pub_el, "Ciudad").text = pub.ciudad if pub else r.ciudad
            ET.SubElement(pub_el, "Provincia").text = pub.provincia if pub else ""
            ET.SubElement(pub_el, "Pais").text = pub.pais_publicacion if pub else r.pais_publicacion
            ET.SubElement(pub_el, "Idioma").text = pub.idioma if pub else ""
            ET.SubElement(pub_el, "Licencia").text = pub.licencia if pub else r.licencia
            ET.SubElement(pub_el, "URL").text = pub.url_publi if pub else ""
            ET.SubElement(pub_el, "Tipo").text = pub.tipo_recurso if pub else r.tipo_recurso
            ET.SubElement(pub_el, "Frecuencia").text = pub.frecuencia if pub else ""
            ET.SubElement(pub_el, "Fuente").text = pub.fuente if pub else r.fuente
            
            # Metadata Prensa
            meta_el = ET.SubElement(noticia_el, "Metadatos")
            ET.SubElement(meta_el, "Titulo").text = r.titulo or ""
            ET.SubElement(meta_el, "FechaOriginal").text = r.fecha_original or ""
            ET.SubElement(meta_el, "Anio").text = str(r.anio or "")
            ET.SubElement(meta_el, "AutorNombre").text = r.nombre_autor or ""
            ET.SubElement(meta_el, "AutorApellido").text = r.apellido_autor or ""
            ET.SubElement(meta_el, "AutorTipo").text = r.tipo_autor or ""
            ET.SubElement(meta_el, "Numero").text = r.numero or ""
            ET.SubElement(meta_el, "Edicion").text = r.edicion or ""
            ET.SubElement(meta_el, "PaginaInicio").text = r.pagina_inicio or ""
            ET.SubElement(meta_el, "PaginaFin").text = r.pagina_fin or ""
            ET.SubElement(meta_el, "PaginasTotales").text = r.paginas or ""
            ET.SubElement(meta_el, "CiudadPrensa").text = r.ciudad or ""
            ET.SubElement(meta_el, "PaisPrensa").text = r.pais_publicacion or ""
            ET.SubElement(meta_el, "Temas").text = r.temas or ""
            ET.SubElement(meta_el, "PalabrasClave").text = r.palabras_clave or ""
            ET.SubElement(meta_el, "IdiomaPrensa").text = r.idioma or ""
            ET.SubElement(meta_el, "TipoRecurso").text = r.tipo_recurso or ""
            ET.SubElement(meta_el, "URLPrensa").text = r.url or ""
            ET.SubElement(meta_el, "FechaConsulta").text = r.fecha_consulta or ""
            ET.SubElement(meta_el, "ISSN").text = r.issn or ""
            ET.SubElement(meta_el, "ISBN").text = r.isbn or ""
            ET.SubElement(meta_el, "DOI").text = r.doi or ""
            ET.SubElement(meta_el, "Volumen").text = r.volumen or ""
            ET.SubElement(meta_el, "Seccion").text = r.seccion or ""
            ET.SubElement(meta_el, "Editorial").text = r.editorial or ""
            ET.SubElement(meta_el, "Editor").text = r.editor or ""
            ET.SubElement(meta_el, "LugarPub").text = r.lugar_publicacion or ""
            ET.SubElement(meta_el, "Fuente").text = r.fuente or ""
            ET.SubElement(meta_el, "Resumen").text = r.resumen or ""
            ET.SubElement(meta_el, "LicenciaPrensa").text = r.licencia or ""
            ET.SubElement(meta_el, "Notas").text = r.notas or ""
            ET.SubElement(meta_el, "FuenteCondiciones").text = r.fuente_condiciones or ""
            ET.SubElement(meta_el, "NumeroReferencia").text = str(r.numero_referencia or "")
            ET.SubElement(meta_el, "FormatoFuente").text = r.formato_fuente or ""
            ET.SubElement(meta_el, "ReferenciaRelacionada").text = r.referencias_relacionadas or ""
            ET.SubElement(meta_el, "ArchivoPDF").text = r.archivo_pdf or ""
            ET.SubElement(meta_el, "ImagenScan").text = r.imagen_scan or ""
            ET.SubElement(meta_el, "TextoOriginal").text = r.texto_original or ""
            ET.SubElement(meta_el, "DescripcionPublicacion").text = r.descripcion_publicacion or ""
            ET.SubElement(meta_el, "NombreInvestigador").text = r.nombre_investigador or ""
            ET.SubElement(meta_el, "UniversidadInvestigador").text = r.universidad_investigador or ""
            ET.SubElement(meta_el, "Incluido").text = "1" if r.incluido else "0"
            
            # Contenido
            ET.SubElement(noticia_el, "Contenido").text = r.contenido or ""

        xml_data = ET.tostring(root, encoding="unicode", method="xml")
        response = Response(xml_data, mimetype="application/xml")
        response.headers["Content-Disposition"] = "attachment; filename=export_sirio.xml"
        return response

    elif formato == "xml":
        import xml.etree.ElementTree as ET
        root = ET.Element("bibliografia")
        for r in resultados:
            if r.id is None:
                continue
            item = ET.SubElement(root, "registro")
            ET.SubElement(item, "ID").text = str(r.id or "")
            ET.SubElement(item, "Titulo").text = r.titulo or ""
            ET.SubElement(item, "Publicacion").text = r.publicacion or ""
            ET.SubElement(item, "Fecha").text = r.fecha_original or ""
            # Autor: soporte Prensa y Publicacion
            if hasattr(r, 'autor'):
                autor = r.autor or ""
            else:
                nombre = getattr(r, 'nombre_autor', None) or ""
                apellido = getattr(r, 'apellido_autor', None) or ""
                autor = f"{apellido}, {nombre}".strip(', ') if (nombre or apellido) else ""
            ET.SubElement(item, "Autor").text = autor
            ET.SubElement(item, "Numero").text = r.numero or ""
            ET.SubElement(item, "Ciudad").text = r.ciudad or ""
            ET.SubElement(item, "Pais_publicacion").text = r.pais_publicacion or ""
            ET.SubElement(item, "Idioma").text = r.idioma or ""
            ET.SubElement(item, "Tipo_recurso").text = r.tipo_recurso or ""
            ET.SubElement(item, "Formato_fuente").text = r.formato_fuente or ""
            ET.SubElement(item, "Incluido").text = "sí" if r.incluido else "no"
            ET.SubElement(item, "Temas").text = r.temas or ""
            ET.SubElement(item, "Notas").text = (r.notas or "").replace("\n", " ").strip()
            ET.SubElement(item, "URL").text = r.url or ""
            ET.SubElement(item, "Fecha_consulta").text = r.fecha_consulta or ""
            ET.SubElement(item, "Archivo_PDF").text = r.archivo_pdf or ""
            ET.SubElement(item, "Referencias_relacionadas").text = r.referencias_relacionadas or ""
            ET.SubElement(item, "Paginas").text = r.paginas or ""
            ET.SubElement(item, "ISSN").text = r.issn or ""
            ET.SubElement(item, "ISBN").text = r.isbn or ""
            ET.SubElement(item, "DOI").text = r.doi or ""
            ET.SubElement(item, "Editorial").text = r.editorial or ""
            ET.SubElement(item, "Lugar_publicacion").text = r.lugar_publicacion or ""
            ET.SubElement(item, "Volumen").text = r.volumen or ""
            ET.SubElement(item, "Seccion").text = r.seccion or ""
            ET.SubElement(item, "Palabras_clave").text = r.palabras_clave or ""
            ET.SubElement(item, "Resumen").text = (r.resumen or "").replace("\n", " ").strip()
            ET.SubElement(item, "Licencia").text = r.licencia or ""
            desc_pub = r.publicacion_rel.descripcion if r.publicacion_rel else ""
            ET.SubElement(item, "Descripcion_publicacion").text = (desc_pub or "").replace("\n", " ").strip()
            ET.SubElement(item, "Fuente").text = r.fuente or ""
            ET.SubElement(item, "Contenido").text = r.contenido or ""
            ET.SubElement(item, "Imagen").text = r.imagen_scan or ""
            ET.SubElement(item, "Texto_Original").text = r.texto_original or ""
            ET.SubElement(item, "Hem_Provincia").text = hem.provincia if hem else ""
            ET.SubElement(item, "Hem_ResumenCorpus").text = hem.resumen_corpus if hem else ""
            ET.SubElement(item, "Pub_Provincia").text = pub.provincia if pub else ""
            ET.SubElement(item, "Pub_Frecuencia").text = pub.frecuencia if pub else ""
            ET.SubElement(item, "Pub_Fuente").text = pub.fuente if pub else ""
        xml_str = ET.tostring(root, encoding="utf-8", method="xml")
        return Response(
            xml_str,
            mimetype="application/xml",
            headers={
                "Content-Disposition": "attachment; filename=bibliografia.xml"
            },
        )
        entries = []
        for r in resultados:
            try:
                if r.id is None:
                    continue
                r.id = int(r.id)
            except ValueError:
                continue

            # Soporte para Prensa: autor puede ser nombre_autor + apellido_autor
            if hasattr(r, 'autor'):
                autor_raw = r.autor or ""
            else:
                nombre = getattr(r, 'nombre_autor', None) or ""
                apellido = getattr(r, 'apellido_autor', None) or ""
                autor_raw = f"{apellido}, {nombre}".strip(', ') if (nombre or apellido) else ""
            autor_bib = autor_para_bibtex(autor_raw)
            anyo_bib = extraer_anio(r.fecha_original)
            desc_pub = r.publicacion_rel.descripcion if r.publicacion_rel else ""
            clave_base = ""
            if "," in autor_bib:
                clave_base = autor_bib.split(",")[0]
            else:
                partes = autor_bib.split()
                clave_base = partes[0] if partes else "Anonimo"
            key = f"{clave_base}_{anyo_bib}"

            entry = f"@article{{{key},\n"
            entry += f" \ttitle = {{{r.titulo or '[Sin título]'}}},\n"
            entry += f" \tauthor = {{{autor_bib}}},\n"
            if r.publicacion:
                entry += f" \tjournal = {{{r.publicacion}}},\n"
            if r.editorial:
                entry += f" \tpublisher = {{{r.editorial}}},\n"
            if r.lugar_publicacion:
                entry += f" \taddress = {{{r.lugar_publicacion}}},\n"
            entry += f" \tyear = {{{anyo_bib}}},\n"
            if r.volumen:
                entry += f" \tvolume = {{{r.volumen}}},\n"
            if r.numero:
                entry += f" \tnumber = {{{r.numero}}},\n"
            if r.isbn:
                entry += f" \tisbn = {{{r.isbn}}},\n"
            if r.issn:
                entry += f" \tissn = {{{r.issn}}},\n"
            if r.doi:
                entry += f" \tdoi = {{{r.doi}}},\n"
            if r.pagina_inicio or r.pagina_fin:
                entry += f" \tpages = {{{(r.pagina_inicio or '')}-{(r.pagina_fin or '')}}},\n"
            if r.url:
                entry += f" \turl = {{{r.url}}},\n"
            if r.fecha_consulta:
                entry += f" \tnote = {{Consultado el {r.fecha_consulta}}},\n"
            if r.pais_publicacion:
                entry += f" \tlocation = {{{r.pais_publicacion}}},\n"
            if r.formato_fuente:
                entry += f" \thowpublished = {{{r.formato_fuente}}},\n"
            if r.archivo_pdf:
                entry += f" \tfile = {{{r.archivo_pdf}}},\n"
            if r.referencias_relacionadas:
                entry += f" \trelated = {{{r.referencias_relacionadas}}},\n"
            if desc_pub:
                entry += f" \tnote = {{{(desc_pub or '').replace('{', '').replace('}', '')}}},\n"
            entry += "}\n\n"
            entries.append(entry)

        return Response(
            "".join(entries),
            mimetype="text/plain",
            headers={"Content-Disposition": "attachment; filename=bibliografia.bib"},
        )

    return Response("Formato no soportado", status=400)


@app.route("/importar_datos", methods=["POST"])
@login_required
def importar_datos():
    if "file" not in request.files:
        return jsonify({"success": False, "error": "No hay archivo"}), 400
    
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"success": False, "error": "Archivo vacío"}), 400

    from app import get_proyecto_activo
    proyecto = get_proyecto_activo()
    if not proyecto:
        return jsonify({"success": False, "error": "No hay proyecto activo"}), 400

    filename = secure_filename(file.filename).lower()
    raw_content = file.read()
    
    # Intentar decodificar con distintos encodings
    content = None
    for enc in ["utf-8-sig", "utf-8", "latin-1", "iso-8859-1"]:
        try:
            content = raw_content.decode(enc)
            break
        except:
            continue
    
    if content is None:
        return jsonify({"success": False, "error": "No se pudo decodificar el archivo"}), 400

    rows = []
    errors = []
    count = 0

    try:
        if filename.endswith(".json"):
            try:
                data = json.loads(content)
                if isinstance(data, list): rows = data
                elif isinstance(data, dict):
                    if "noticias" in data: rows = data["noticias"]
                    else: rows = [data]
            except Exception as e:
                return jsonify({"success": False, "error": f"Error JSON: {str(e)}"}), 400

        elif filename.endswith(".csv"):
            f = io.StringIO(content)
            reader = csv.DictReader(f)
            rows = list(reader)

        elif filename.endswith(".xml"):
            import xml.etree.ElementTree as ET
            try:
                root = ET.fromstring(content)
                if root.tag == "BibliotecaSirio":
                    for notizia_el in root.findall("Noticia"):
                        row = {}
                        hem = notizia_el.find("Hemeroteca")
                        if hem is not None:
                            row["Hem_Nombre"] = hem.findtext("Nombre")
                            row["Hem_Institucion"] = hem.findtext("Institucion")
                            row["Hem_Pais"] = hem.findtext("Pais")
                            row["Hem_Ciudad"] = hem.findtext("Ciudad")
                            row["Hem_URL"] = hem.findtext("URL")
                        
                        pub = notizia_el.find("Publicacion")
                        if pub is not None:
                            row["Pub_Nombre"] = pub.findtext("Nombre")
                            row["Pub_Ciudad"] = pub.findtext("Ciudad")
                            row["Pub_Pais"] = pub.findtext("Pais")
                            row["Pub_Idioma"] = pub.findtext("Idioma")
                            row["Pub_Licencia"] = pub.findtext("Licencia")
                            row["Pub_URL"] = pub.findtext("URL")
                            row["Pub_Tipo"] = pub.findtext("Tipo")
                        
                        meta = notizia_el.find("Metadatos")
                        if meta is not None:
                            for m_el in meta:
                                row[f"Noticia_{m_el.tag}"] = m_el.text
                            # Fallbacks for specific tags if needed
                            row["Noticia_Titulo"] = meta.findtext("Titulo")
                            row["Noticia_Fecha"] = meta.findtext("FechaOriginal")
                            row["Noticia_PaginaInicio"] = meta.findtext("PaginaInicio")
                            row["Noticia_PaginaFin"] = meta.findtext("PaginaFin")
                            row["Noticia_PaginasTotales"] = meta.findtext("PaginasTotales")
                            row["Noticia_Ciudad"] = meta.findtext("CiudadPrensa")
                            row["Noticia_Pais"] = meta.findtext("PaisPrensa")
                            row["Noticia_Idioma"] = meta.findtext("IdiomaPrensa")
                            row["Noticia_Tipo"] = meta.findtext("TipoRecurso")
                            row["Noticia_URL"] = meta.findtext("URLPrensa")
                            row["Noticia_LicenciaPrensa"] = meta.findtext("LicenciaPrensa")
                            row["Noticia_DescripcionPub"] = meta.findtext("DescripcionPublicacion")
                            row["Noticia_ReferenciaRelacionada"] = meta.findtext("ReferenciaRelacionada")

                        row["Noticia_Contenido"] = notizia_el.findtext("Contenido")
                        rows.append(row)
                else:
                    # Genérico
                    for item in root.findall(".//noticia") or root.findall(".//item") or root.findall(".//record"):
                        row = {child.tag.lower(): child.text for child in item}
                        rows.append(row)
            except Exception as e:
                return jsonify({"success": False, "error": f"Error XML: {str(e)}"}), 400

        # Procesar filas
        for row in rows:
            try:
                # Normalizar keys para manejar acentos y mayúsculas
                def normalize_key(k):
                    import unicodedata
                    k = k.lower().strip()
                    k = "".join(c for c in unicodedata.normalize('NFD', k) if unicodedata.category(c) != 'Mn')
                    return k

                norm_row = {normalize_key(k): v for k, v in row.items() if k}
                
                # Diferenciar si es formato "noticia" anidado (JSON Sirio) o plano
                if "noticia" in row and isinstance(row["noticia"], dict):
                    # Formato JSON Sirio anidado
                    n_data = row["noticia"]
                    p_data = row.get("publicacion") or {}
                    h_data = row.get("hemeroteca") or {}
                    
                    # Resolve Hemeroteca
                    hem_id = None
                    if h_data.get("nombre"):
                        hem = Hemeroteca.query.filter_by(nombre=h_data["nombre"], proyecto_id=proyecto.id).first()
                        if not hem:
                            hem = Hemeroteca(proyecto_id=proyecto.id, **h_data)
                            db.session.add(hem)
                            db.session.flush()
                        hem_id = hem.id
                    
                    # Resolve Publicacion
                    pub_id = None
                    if p_data.get("nombre"):
                        pub = Publicacion.query.filter_by(nombre=p_data["nombre"], proyecto_id=proyecto.id).first()
                        if not pub:
                            pub = Publicacion(proyecto_id=proyecto.id, hemeroteca_id=hem_id, **p_data)
                            db.session.add(pub)
                            db.session.flush()
                        pub_id = pub.id_publicacion
                    
                    noticia = Prensa(proyecto_id=proyecto.id, id_publicacion=pub_id, **n_data)
                    if not noticia.publicacion and p_data.get("nombre"):
                        noticia.publicacion = p_data["nombre"]
                else:
                    # Formato Plano (CSV / XML / Plano JSON)
                    is_sirio = any(k.startswith(("hem_", "pub_", "noticia_")) for k in norm_row.keys())
                    
                    if is_sirio:
                        # Resolve Hemeroteca
                        hem_id = None
                        if norm_row.get("hem_nombre"):
                            hem = Hemeroteca.query.filter_by(nombre=norm_row["hem_nombre"], proyecto_id=proyecto.id).first()
                            if not hem:
                                hem = Hemeroteca(
                                    proyecto_id=proyecto.id,
                                    nombre=norm_row["hem_nombre"],
                                    institucion=norm_row.get("hem_institucion"),
                                    pais=norm_row.get("hem_pais"),
                                    ciudad=norm_row.get("hem_ciudad"),
                                    url=norm_row.get("hem_url")
                                )
                                db.session.add(hem)
                                db.session.flush()
                            hem_id = hem.id
                        
                        # Resolve Publicacion
                        pub_id = None
                        pub_nombre = norm_row.get("pub_nombre") or norm_row.get("publicacion")
                        if pub_nombre:
                            pub = Publicacion.query.filter_by(nombre=pub_nombre, proyecto_id=proyecto.id).first()
                            if not pub:
                                pub = Publicacion(
                                    proyecto_id=proyecto.id,
                                    hemeroteca_id=hem_id,
                                    nombre=pub_nombre,
                                    ciudad=norm_row.get("pub_ciudad"),
                                    pais_publicacion=norm_row.get("pub_pais"),
                                    idioma=norm_row.get("pub_idioma"),
                                    licencia=norm_row.get("pub_licencia", "CC BY 4.0"),
                                    url_publi=norm_row.get("pub_url"),
                                    tipo_recurso=norm_row.get("pub_tipo")
                                )
                                db.session.add(pub)
                                db.session.flush()
                            pub_id = pub.id_publicacion
                        
                        # Noticia
                        n_fecha = norm_row.get("noticia_fecha") or norm_row.get("noticia_fechaoriginal")
                        n_anio = norm_row.get("noticia_anio")
                        if n_fecha and not n_anio:
                            try:
                                if "-" in n_fecha: n_anio = int(n_fecha.split("-")[0])
                                elif "/" in n_fecha: n_anio = int(n_fecha.split("/")[-1])
                                elif len(n_fecha) == 4 and n_fecha.isdigit(): n_anio = int(n_fecha)
                            except: pass

                        noticia = Prensa(
                            proyecto_id=proyecto.id,
                            id_publicacion=pub_id,
                            publicacion=pub_nombre,
                            titulo=norm_row.get("noticia_titulo"),
                            fecha_original=n_fecha,
                            anio=int(n_anio) if n_anio and str(n_anio).isdigit() else None,
                            nombre_autor=norm_row.get("noticia_autornombre") or norm_row.get("noticia_autor_nom"),
                            apellido_autor=norm_row.get("noticia_autorapellido") or norm_row.get("noticia_autor_ape") or norm_row.get("noticia_autor"),
                            tipo_autor=norm_row.get("noticia_autortipo") or norm_row.get("noticia_autor_tipo"),
                            ciudad=norm_row.get("noticia_ciudadprensa") or norm_row.get("noticia_ciudad"),
                            pais_publicacion=norm_row.get("noticia_paisprensa") or norm_row.get("noticia_pais") or norm_row.get("pub_pais"),
                            numero=norm_row.get("noticia_numero"),
                            edicion=norm_row.get("noticia_edicion"),
                            pagina_inicio=norm_row.get("noticia_paginainicio") or norm_row.get("noticia_paginas"),
                            pagina_fin=norm_row.get("noticia_paginafin"),
                            paginas=norm_row.get("noticia_paginastotales") or norm_row.get("noticia_paginas"),
                            temas=norm_row.get("noticia_temas"),
                            palabras_clave=norm_row.get("noticia_palabrasclave"),
                            resumen=norm_row.get("noticia_resumen"),
                            tipo_recurso=norm_row.get("noticia_tiporecurso") or norm_row.get("noticia_tipo") or norm_row.get("pub_tipo"),
                            idioma=norm_row.get("noticia_idiomaprensa") or norm_row.get("noticia_idioma") or norm_row.get("pub_idioma"),
                            url=norm_row.get("noticia_urlprensa") or norm_row.get("noticia_url"),
                            fecha_consulta=norm_row.get("noticia_fechaconsulta"),
                            licencia=norm_row.get("noticia_licencia") or norm_row.get("noticia_licenciaprensa") or norm_row.get("pub_licencia"),
                            notas=norm_row.get("noticia_notas"),
                            contenido=norm_row.get("noticia_contenido"),
                            issn=norm_row.get("noticia_issn"),
                            isbn=norm_row.get("noticia_isbn"),
                            doi=norm_row.get("noticia_doi"),
                            volumen=norm_row.get("noticia_volumen"),
                            seccion=norm_row.get("noticia_seccion"),
                            editorial=norm_row.get("noticia_editorial"),
                            editor=norm_row.get("noticia_editor"),
                            lugar_publicacion=norm_row.get("noticia_lugarpub"),
                            fuente=norm_row.get("noticia_fuente"),
                            nombre_investigador=norm_row.get("noticia_nombreinvestigador"),
                            universidad_investigador=norm_row.get("noticia_universidadinvestigador"),
                            referencias_relacionadas=norm_row.get("noticia_referenciarelacionada"),
                            archivo_pdf=norm_row.get("noticia_archivopdf"),
                            imagen_scan=norm_row.get("noticia_imagenscan"),
                            texto_original=norm_row.get("noticia_textooriginal"),
                            descripcion_publicacion=norm_row.get("noticia_descripcionpub") or norm_row.get("noticia_descripcionpublicacion"),
                            fuente_condiciones=norm_row.get("noticia_fuentecondiciones"),
                            numero_referencia=int(norm_row["noticia_numeroreferencia"]) if norm_row.get("noticia_numeroreferencia") and str(norm_row["noticia_numeroreferencia"]).isdigit() else None,
                            formato_fuente=norm_row.get("noticia_formatofuente"),
                            incluido=norm_row.get("noticia_incluido") in ["1", 1, True, "True"]
                        )
                    else:
                        # No Sirio (Genérico / Legacy)
                        f_val = norm_row.get("fecha")
                        a_val = norm_row.get("anio")
                        if f_val and not a_val:
                            try:
                                if "-" in f_val: a_val = int(f_val.split("-")[0])
                                elif "/" in f_val: a_val = int(f_val.split("/")[-1])
                                elif len(f_val) == 4 and f_val.isdigit(): a_val = int(f_val)
                            except: pass
                        
                        # Extraer autor
                        a_nom = norm_row.get("nombre_autor") or norm_row.get("nombre")
                        a_ape = norm_row.get("autor") or norm_row.get("apellido_autor") or norm_row.get("apellido")
                        if not a_nom and a_ape and "," in str(a_ape):
                            parts = a_ape.split(",")
                            a_ape = parts[0].strip()
                            a_nom = parts[1].strip()

                        noticia = Prensa(
                            proyecto_id=proyecto.id,
                            titulo=norm_row.get("titulo"),
                            publicacion=norm_row.get("publicacion"),
                            contenido=norm_row.get("contenido"),
                            fecha_original=f_val,
                            anio=a_val,
                            nombre_autor=a_nom,
                            apellido_autor=a_ape,
                            numero=norm_row.get("numero") or norm_row.get("num"),
                            pagina_inicio=norm_row.get("pagina") or norm_row.get("pag"),
                            paginas=norm_row.get("paginas"),
                            ciudad=norm_row.get("ciudad"),
                            pais_publicacion=norm_row.get("pais_publicacion") or norm_row.get("pais"),
                            tipo_recurso=norm_row.get("tipo_recurso") or norm_row.get("tipo"),
                            idioma=norm_row.get("idioma"),
                            temas=norm_row.get("temas"),
                            url=norm_row.get("url")
                        )
                
                db.session.add(noticia)
                count += 1
            except Exception as e:
                errors.append(f"Error procesando registro: {str(e)}")
                continue

        db.session.commit()
        return jsonify({
            "success": True, 
            "message": f"Se han importado {count} registros correctamente.",
            "errors": errors
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": f"Error general: {str(e)}"}), 500


# =========================================================
# HUMANIDADES DIGITALES — ANÁLISIS DE TEXTO
# =========================================================
@app.route("/analisis")
def analisis():
    """Vista unificada de análisis NLP + estadísticas"""
    return render_template("analisis.html")


@app.route("/analisis/frecuencia")
def frecuencia_palabras():
    proyecto = get_proyecto_activo()
    if not proyecto:
        return jsonify({"error": "No hay proyecto activo"}), 400

    # FILTRAR POR PROYECTO
    fields = request.args.get("fields", "contenido,titulo").split(",")
    fields = [f for f in fields if f in ("contenido", "titulo")]
    if not fields:
        fields = ["contenido"]

    limite = request.args.get('limit', '300')
    try:
        limite = int(limite)
    except (ValueError, TypeError):
        limite = 300

    q_base = Prensa.query.filter(Prensa.proyecto_id == proyecto.id, Prensa.incluido == True)
    if limite > 0:
        referencias = q_base.limit(limite).all()
    else:
        referencias = q_base.all()

    textos = [
        " ".join([getattr(r, f, "") for f in fields if getattr(r, f, None)])
        for r in referencias
    ]
    texto_unido = " ".join(textos).lower()

    stopwords = {
        "de", "la", "que", "el", "en", "y", "a", "los", "del", "se", "las", "por", "un", "para", "con", "no", "una", "su", "al", "lo", "como", "más", "pero", "sus", "le", "ya", "o", "fue", "este", "ha", "sí", "porque", "esta", "son", "entre", "cuando", "muy", "sin", "sobre", "también", "me", "hasta", "hay", "donde", "han", "quien", "desde", "todo", "nos", "durante", "todos", "uno", "les", "ni", "contra", "otros", "ese", "eso", "ante", "ellos", "e", "esto", "mí", "antes", "algunos", "qué", "unos", "yo", "otro", "otras", "otra", "él", "tanto", "esa", "estos", "mucho", "quienes", "nada", "muchos", "cual", "poco", "ella", "estar", "estas", "algunas", "algo", "nosotros", "mi", "mis", "tú", "te", "ti", "tu", "tus", "ellas", "nosotras", "vosotros", "vosotras", "os", "mío", "mía", "míos", "mías", "tuyo", "tuya", "tuyos", "tuyas", "suyo", "suya", "suyos", "suyas", "nuestro", "nuestra", "nuestros", "nuestras", "vuestro", "vuestra", "vuestros", "vuestras", "esos", "esas", "estoy", "estás", "está", "estamos", "estáis", "están", "esté", "estén", "estaba", "estaban", "he", "has", "han", "hace", "hacía", "hacen", "hacer", "cada", "ser", "haber", "era", "eras", "eran", "soy", "es", "sea", "sean", "según", "sin", "sino", "si", "del", "al", "aquel", "aquella", "aquellos", "aquellas",
    }

    palabras = re.findall(r"\b[a-záéíóúüñ]+\b", texto_unido)
    palabras_filtradas = [p for p in palabras if p not in stopwords and len(p) > 2]

    frecuencias = Counter(palabras_filtradas).most_common(120)

    if not palabras_filtradas:
        return jsonify([])

    return jsonify(frecuencias)


# =========================================================
# FRECUENCIA NORMALIZADA (después de /analisis/frecuencia)
# =========================================================
@app.route("/analisis/frecuencia_normalizada")
def frecuencia_normalizada():
    proyecto = get_proyecto_activo()
    if not proyecto:
        return jsonify({"error": "No hay proyecto activo"}), 400

    fields = request.args.get("fields", "contenido,titulo").split(",")
    fields = [f for f in fields if f in ("contenido", "titulo")]
    if not fields:
        fields = ["contenido"]

    limite = request.args.get('limit', '300')
    try:
        limite = int(limite)
    except (ValueError, TypeError):
        limite = 300

    q_base = Prensa.query.filter(Prensa.proyecto_id == proyecto.id, Prensa.incluido == True)
    if limite > 0:
        referencias = q_base.limit(limite).all()
    else:
        referencias = q_base.all()

    textos = [
        " ".join([getattr(r, f, "") for f in fields if getattr(r, f, None)])
        for r in referencias
    ]
    texto_unido = " ".join(textos).lower()

    stopwords = {
        "de", "la", "que", "el", "en", "y", "a", "los", "del", "se", "las", "por", "un", "para", "con", "no", "una", "su", "al", "lo", "como", "más", "pero", "sus", "le", "ya", "o", "fue", "este", "ha", "sí"
    }

    palabras = re.findall(r"\b[a-záéíóúüñ]+\b", texto_unido)
    palabras_filtradas = [p for p in palabras if p not in stopwords and len(p) > 2]

    total_palabras = len(palabras_filtradas)
    if total_palabras == 0:
        return jsonify([])

    conteo = Counter(palabras_filtradas)
    normalizadas = [
        (palabra, int(freq * 1_000_000 / total_palabras))
        for palabra, freq in conteo.items()
    ]
    normalizadas.sort(key=lambda x: x[1], reverse=True)
    top120 = normalizadas[:120]
    return jsonify(top120)


@app.route("/analisis/nube")
def nube_palabras():
    proyecto = get_proyecto_activo()
    if not proyecto:
        return "Error: No hay proyecto activo", 400

    limite = request.args.get('limit', '300')
    try:
        limite = int(limite)
    except (ValueError, TypeError):
        limite = 300

    q_base = Prensa.query.filter(Prensa.proyecto_id == proyecto.id, Prensa.incluido == True, Prensa.contenido.isnot(None))
    if limite > 0:
        referencias = q_base.limit(limite).all()
    else:
        referencias = q_base.all()

    textos = " ".join([r.contenido for r in referencias])
    textos = textos.lower()

    stopwords = {
        "de",
        "la",
        "que",
        "el",
        "en",
        "y",
        "a",
        "los",
        "del",
        "se",
        "las",
        "por",
        "un",
        "para",
        "con",
        "no",
        "una",
        "su",
        "al",
        "lo",
        "como",
        "más",
        "pero",
        "sus",
        "le",
        "ya",
        "o",
        "fue",
        "este",
        "ha",
        "sí",
        "porque",
        "esta",
        "son",
        "entre",
        "cuando",
        "muy",
        "sin",
        "sobre",
        "también",
        "me",
        "hasta",
        "hay",
        "donde",
        "han",
        "quien",
        "desde",
        "todo",
        "nos",
        "durante",
        "todos",
        "uno",
        "les",
        "ni",
        "contra",
        "otros",
        "ese",
        "eso",
        "ante",
        "ellos",
        "e",
        "esto",
        "mí",
        "antes",
        "algunos",
        "qué",
        "unos",
        "yo",
        "otro",
        "otras",
        "otra",
        "él",
        "tanto",
        "esa",
        "estos",
        "mucho",
        "quienes",
        "nada",
        "muchos",
        "cual",
        "poco",
        "ella",
        "estar",
        "estas",
        "algunas",
        "algo",
        "nosotros",
        "mi",
        "mis",
        "tú",
        "te",
        "ti",
        "tu",
        "tus",
        "ellas",
        "nosotras",
        "vosotros",
        "vosotras",
        "os",
        "mío",
        "mía",
        "míos",
        "mías",
        "tuyo",
        "tuya",
        "tuyos",
        "tuyas",
        "suyo",
        "suya",
        "suyos",
        "suyas",
        "nuestro",
        "nuestra",
        "nuestros",
        "nuestras",
        "vuestro",
        "vuestra",
        "vuestros",
        "vuestras",
        "esos",
        "esas",
        "estoy",
        "estás",
        "está",
        "estamos",
        "estáis",
        "están",
        "esté",
        "estén",
        "estaba",
        "estaban",
        "he",
        "has",
        "han",
        "hace",
        "hacía",
        "hacen",
        "hacer",
        "cada",
        "ser",
        "haber",
        "era",
        "eras",
        "eran",
        "soy",
        "es",
        "sea",
        "sean",
        "según",
        "sin",
        "sino",
        "si",
        "del",
        "al",
        "aquel",
        "aquella",
        "aquellos",
        "aquellas",
    }

    palabras = re.findall(r"\b[a-záéíóúüñ]+\b", textos)
    # Normalizar stopwords y palabras antes de comparar
    stopwords_norm = set(normalizar_texto(sw) for sw in stopwords)
    palabras_filtradas = [p for p in palabras if normalizar_texto(p) not in stopwords_norm and len(p) > 2]

    if not palabras_filtradas:
        nube = WordCloud(
            width=800, height=400, background_color="black", colormap="cividis"
        ).generate("No hay suficientes palabras para el análisis.")
    else:
        nube = WordCloud(
            width=800, height=400, background_color="black", colormap="cividis"
        ).generate(" ".join(palabras_filtradas))

    img = BytesIO()
    nube.to_image().save(img, format="PNG")
    img.seek(0)
    return send_file(img, mimetype="image/png")


# =========================================================
# 📊 MÓDULO DE ESTADÍSTICAS
# =========================================================
@app.route("/estadisticas")
def estadisticas():
    proyecto = get_proyecto_activo()
    if not proyecto:
        return redirect(url_for("listar_proyectos"))

    # FILTRAR POR PROYECTO
    query_base = Prensa.query.filter_by(proyecto_id=proyecto.id)
    total = query_base.count()
    medios = (
        db.session.query(func.count(func.distinct(Prensa.publicacion)))
        .filter(Prensa.proyecto_id == proyecto.id)
        .scalar()
    )
    ciudades = (
        db.session.query(func.count(func.distinct(Prensa.ciudad)))
        .filter(Prensa.proyecto_id == proyecto.id)
        .scalar()
    )
    min_anio = (
        db.session.query(func.min(Prensa.anio))
        .filter(Prensa.proyecto_id == proyecto.id)
        .scalar()
    )
    max_anio = (
        db.session.query(func.max(Prensa.anio))
        .filter(Prensa.proyecto_id == proyecto.id)
        .scalar()
    )
    rango = f"{min_anio} - {max_anio}" if min_anio else "Desc."
    return render_template(
        "estadisticas.html", total=total, medios=medios, ciudades=ciudades, rango=rango
    )


@app.route("/api/stats-data")
def stats_data():
    proyecto = get_proyecto_activo()
    if not proyecto:
        return jsonify({"error": "No hay proyecto activo"}), 400

    # FILTRAR POR PROYECTO
    raw = (
        db.session.query(Prensa.anio, func.count(Prensa.id))
        .filter(Prensa.proyecto_id == proyecto.id, Prensa.incluido == True)
        .group_by(Prensa.anio)
        .all()
    )
    timeline = {
        int(y): c for y, c in raw if y and str(y).isdigit() and 1800 < int(y) < 2030
    }
    years = sorted(timeline.keys())
    pubs = (
        db.session.query(Prensa.publicacion, func.count(Prensa.id))
        .filter(Prensa.proyecto_id == proyecto.id, Prensa.publicacion != "", Prensa.incluido == True)
        .group_by(Prensa.publicacion)
        .order_by(func.count(Prensa.id).desc())
        .limit(10)
        .all()
    )
    cities = (
        db.session.query(Prensa.ciudad, func.count(Prensa.id))
        .filter(Prensa.proyecto_id == proyecto.id, Prensa.ciudad != "", Prensa.incluido == True)
        .group_by(Prensa.ciudad)
        .order_by(func.count(Prensa.id).desc())
        .limit(10)
        .all()
    )
    langs = (
        db.session.query(Prensa.idioma, func.count(Prensa.id))
        .filter(Prensa.proyecto_id == proyecto.id, Prensa.incluido == True)
        .group_by(Prensa.idioma)
        .all()
    )

    return jsonify(
        {
            "timeline": {
                "labels": [str(y) for y in years],
                "data": [timeline[y] for y in years],
            },
            "publicaciones": {
                "labels": [p[0] for p in pubs],
                "data": [p[1] for p in pubs],
            },
            "ciudades": {
                "labels": [c[0] for c in cities],
                "data": [c[1] for c in cities],
            },
            "idiomas": {
                "labels": [l[0] or "?" for l in langs],
                "data": [l[1] for l in langs],
            },
        }
    )


# =========================================================
# API de Estadísticas para visualizaciones mejoradas
# =========================================================
@app.route("/api/stats/por-fecha")
def stats_por_fecha():
    """Distribución de noticias por año"""
    proyecto = get_proyecto_activo()
    if not proyecto:
        return jsonify({"error": "No hay proyecto activo"}), 400

    raw = (
        db.session.query(Prensa.anio, func.count(Prensa.id))
        .filter(Prensa.proyecto_id == proyecto.id, Prensa.incluido == True, Prensa.anio.isnot(None))
        .group_by(Prensa.anio)
        .order_by(Prensa.anio)
        .all()
    )

    data = [
        {"anio": int(y), "count": c}
        for y, c in raw
        if y and str(y).isdigit() and 1800 < int(y) < 2030
    ]

    response = jsonify(data)
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


@app.route("/api/stats/por-publicacion")
def stats_por_publicacion():
    """Distribución por publicación"""
    proyecto = get_proyecto_activo()
    if not proyecto:
        return jsonify({"error": "No hay proyecto activo"}), 400

    raw = (
        db.session.query(Prensa.publicacion, func.count(Prensa.id))
        .filter(Prensa.proyecto_id == proyecto.id, Prensa.incluido == True)
        .filter(Prensa.publicacion.isnot(None))
        .filter(Prensa.publicacion != "")
        .group_by(Prensa.publicacion)
        .order_by(func.count(Prensa.id).desc())
        .limit(15)
        .all()
    )

    data = [{"publicacion": p, "count": c} for p, c in raw]

    response = jsonify(data)
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


@app.route("/api/stats/por-ciudad")
def stats_por_ciudad():
    """Distribución por ciudad"""
    proyecto = get_proyecto_activo()
    if not proyecto:
        return jsonify({"error": "No hay proyecto activo"}), 400

    raw = (
        db.session.query(Prensa.ciudad, func.count(Prensa.id))
        .filter(Prensa.proyecto_id == proyecto.id, Prensa.incluido == True)
        .filter(Prensa.ciudad.isnot(None))
        .filter(Prensa.ciudad != "")
        .group_by(Prensa.ciudad)
        .order_by(func.count(Prensa.id).desc())
        .limit(15)
        .all()
    )

    data = [{"ciudad": c, "count": cnt} for c, cnt in raw]

    response = jsonify(data)
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


# =========================================================
# DICCIONARIO DE COORDENADAS (Ordenado y sin duplicados)
# =========================================================
ciudades_coords = {
    # --- CIUDADES ESPECÍFICAS DEL SIRIO ---
    "Aguilas": [37.4063, -1.5823],
    "Águilas": [37.4063, -1.5823],
    "Alcoi": [38.6987, -0.4736],
    "Alcoy": [38.6987, -0.4736],
    "Cabo de Palos": [37.6321, -0.6907],
    "Cartagena": [37.6257, -0.9966],
    "Cieza": [38.2392, -1.4189],
    "Eivissa": [38.9067, 1.4206],
    "Ibiza": [38.9067, 1.4206],
    "Mahón": [39.8896, 4.2604],
    "Mahon": [39.8896, 4.2604],
    "Manresa": [41.7281, 1.8239],
    "Orihuela": [38.0855, -0.9470],
    "Reus": [41.1561, 1.1069],
    "Santa Pola": [38.1925, -0.5550],
    "Sóller": [39.7671, 2.7152],
    "Soller": [39.7671, 2.7152],
    "Torrevieja": [37.9787, -0.6822],
    "Tortosa": [40.8121, 0.5233],
    "Vilanova i la Geltrú": [41.2214, 1.7241],
    # --- CAPITALES DE ESPAÑA ---
    "A Coruña": [43.3623, -8.4115],
    "Alacant": [38.3452, -0.4810],
    "Albacete": [38.9943, -1.8585],
    "Alicante": [38.3452, -0.4810],
    "Almería": [36.8340, -2.4637],
    "Almeria": [36.8340, -2.4637],
    "Ávila": [40.6565, -4.6813],
    "Avila": [40.6565, -4.6813],
    "Badajoz": [38.8794, -6.9706],
    "Barcelona": [41.3851, 2.1734],
    "Bilbao": [43.2630, -2.9350],
    "Burgos": [42.3439, -3.6969],
    "Cáceres": [39.4753, -6.3723],
    "Cádiz": [36.5271, -6.2886],
    "Castellón": [39.9864, -0.0513],
    "Castellón de la Plana": [39.9864, -0.0513],
    "Ceuta": [35.8894, -5.3213],
    "Ciudad Real": [38.9848, -3.9274],
    "Córdoba": [37.8882, -4.7794],
    "Cordoba": [37.8882, -4.7794],
    "Cuenca": [40.0704, -2.1374],
    "Donostia": [43.3183, -1.9812],
    "Elche": [38.2669, -0.6983],
    "Gerona": [41.9794, 2.8214],
    "Gijón": [43.5322, -5.6611],
    "Gijon": [43.5322, -5.6611],
    "Girona": [41.9794, 2.8214],
    "Granada": [37.1773, -3.5986],
    "Guadalajara": [40.6328, -3.1602],
    "Huelva": [37.2614, -6.9447],
    "Huesca": [42.1362, -0.4087],
    "Jaén": [37.7796, -3.7849],
    "La Coruña": [43.3623, -8.4115],
    "Las Palmas": [28.1235, -15.4363],
    "Las Palmas de Gran Canaria": [28.1235, -15.4363],
    "León": [42.5987, -5.5671],
    "Lérida": [41.6176, 0.6200],
    "Lleida": [41.6176, 0.6200],
    "Logroño": [42.4625, -2.4450],
    "Lugo": [43.0097, -7.5568],
    "Madrid": [40.4168, -3.7038],
    "Málaga": [36.7212, -4.4217],
    "Malaga": [36.7212, -4.4217],
    "Melilla": [35.2923, -2.9381],
    "Murcia": [37.9922, -1.1307],
    "Orense": [42.3358, -7.8639],
    "Ourense": [42.3358, -7.8639],
    "Oviedo": [43.3619, -5.8494],
    "Palencia": [42.0095, -4.5286],
    "Palma": [39.5696, 2.6502],
    "Palma de Mallorca": [39.5696, 2.6502],
    "Pamplona": [42.8125, -1.6458],
    "Pontevedra": [42.4320, -8.6443],
    "Salamanca": [40.9701, -5.6635],
    "San Sebastián": [43.3183, -1.9812],
    "Santa Cruz de Tenerife": [28.4636, -16.2518],
    "Santander": [43.4623, -3.8099],
    "Segovia": [40.9429, -4.1088],
    "Sevilla": [37.3891, -5.9845],
    "Soria": [41.7640, -2.4735],
    "Tarragona": [41.1189, 1.2445],
    "Tenerife": [28.4636, -16.2518],
    "Teruel": [40.3456, -1.1065],
    "Toledo": [39.8628, -4.0273],
    "Valencia": [39.4699, -0.3763],
    "Valladolid": [41.6523, -4.7245],
    "Vigo": [42.2406, -8.7207],
    "Vitoria": [42.8467, -2.6716],
    "Vitoria-Gasteiz": [42.8467, -2.6716],
    "Zamora": [41.5038, -5.7438],
    "Zaragoza": [41.6488, -0.8891],
    # --- CAPITALES y CIUDADES DE ITALIA ---
    "Acerra": [40.9439, 14.3707],
    "Acireale": [37.6126, 15.1659],
    "Acqui": [44.6761, 8.4686],
    "Acqui Terme": [44.6761, 8.4686],
    "Afragola": [40.9206, 14.3070],
    "Agrigento": [37.3107, 13.5766],
    "Alba": [44.6960, 8.0360],
    "Alessandria": [44.9092, 8.6108],
    "Altamura": [40.8288, 16.5528],
    "Ancona": [43.6158, 13.5189],
    "Andria": [41.2310, 16.2969],
    "Anzio": [41.4467, 12.6270],
    "Aosta": [45.7376, 7.3130],
    "Aprilia": [41.5947, 12.6526],
    "Arezzo": [43.4631, 11.8780],
    "Ascoli Piceno": [42.8550, 13.5754],
    "Asti": [44.9008, 8.2068],
    "Avellino": [40.9140, 14.7953],
    "Aversa": [40.9729, 14.2066],
    "Bagheria": [38.0786, 13.5121],
    "Bari": [41.1171, 16.8719],
    "Barletta": [41.3196, 16.2782],
    "Battipaglia": [40.6075, 14.9850],
    "Benevento": [41.1296, 14.7826],
    "Bérgamo": [45.6983, 9.6773],
    "Bergamo": [45.6983, 9.6773],
    "Bisceglie": [41.2407, 16.5020],
    "Bitonto": [41.1091, 16.6921],
    "Bolonia": [44.4949, 11.3426],
    "Bolzano": [46.4983, 11.3548],
    "Brescia": [45.5416, 10.2118],
    "Brindisi": [40.6327, 17.9418],
    "Busto Arsizio": [45.6122, 8.8516],
    "Cagliari": [39.2238, 9.1217],
    "Caltanissetta": [37.4889, 14.0626],
    "Campobasso": [41.5603, 14.6627],
    "Carpi": [44.7842, 10.8848],
    "Carrara": [44.0793, 10.0961],
    "Caserta": [41.0831, 14.3343],
    "Casoria": [40.9017, 14.2933],
    "Castellammare di Stabia": [40.7009, 14.4809],
    "Catania": [37.5079, 15.0830],
    "Catanzaro": [38.9098, 16.5877],
    "Cava de' Tirreni": [40.7015, 14.7076],
    "Cerignola": [41.2657, 15.8936],
    "Cesena": [44.1391, 12.2432],
    "Chieti": [42.3511, 14.1675],
    "Chioggia": [45.2198, 12.2791],
    "Cinisello Balsamo": [45.5568, 9.2202],
    "Civitavecchia": [42.0924, 11.7954],
    "Collegno": [45.0778, 7.5747],
    "Como": [45.8081, 9.0852],
    "Cosenza": [39.3030, 16.2526],
    "Cremona": [45.1332, 10.0245],
    "Crotone": [39.0808, 17.1274],
    "Cuneo": [44.3896, 7.5479],
    "Ercolano": [40.8063, 14.3466],
    "Faenza": [44.2896, 11.8774],
    "Fano": [43.8447, 13.0195],
    "Ferrara": [44.8381, 11.6198],
    "Firenze": [43.7696, 11.2558],
    "Fiumicino": [41.7675, 12.2333],
    "Florencia": [43.7696, 11.2558],
    "Foggia": [41.4622, 15.5446],
    "Foligno": [42.9565, 12.7032],
    "Forlì": [44.2225, 12.0407],
    "Gallarate": [45.6606, 8.7921],
    "Gela": [37.0664, 14.2504],
    "Génova": [44.4056, 8.9463],
    "Genova": [44.4056, 8.9463],
    "Giugliano in Campania": [40.9266, 14.1966],
    "Grosseto": [42.7606, 11.1108],
    "Guidonia Montecelio": [41.9957, 12.7229],
    "Imola": [44.3604, 11.7119],
    "L'Aquila": [42.3498, 13.3995],
    "La Spezia": [44.1025, 9.8241],
    "Lamezia Terme": [38.9541, 16.1824],
    "Latina": [41.4676, 12.9037],
    "Lecce": [40.3515, 18.1750],
    "Legnano": [45.5949, 8.9177],
    "Livorno": [43.5485, 10.3106],
    "Lucca": [43.8429, 10.5027],
    "Manfredonia": [41.6280, 15.9147],
    "Mantova": [45.1564, 10.7914],
    "Mantua": [45.1564, 10.7914],
    "Marsala": [37.7981, 12.4370],
    "Massa": [44.0208, 10.1128],
    "Matera": [40.6638, 16.6061],
    "Mazara del Vallo": [37.6511, 12.5897],
    "Messina": [38.1938, 15.5540],
    "Milan": [45.4642, 9.1900],
    "Milán": [45.4642, 9.1900],
    "Módena": [44.6471, 10.9252],
    "Modena": [44.6471, 10.9252],
    "Modica": [36.8585, 14.7608],
    "Molfetta": [41.2007, 16.5967],
    "Moncalieri": [44.9991, 7.6846],
    "Montesilvano": [42.5137, 14.1502],
    "Monza": [45.5845, 9.2744],
    "Napoles": [40.8518, 14.2681],
    "Nápoles": [40.8518, 14.2681],
    "Novara": [45.4469, 8.6200],
    "Olbia": [40.9237, 9.4963],
    "Padova": [45.4064, 11.8768],
    "Padua": [45.4064, 11.8768],
    "Palermo": [38.1157, 13.3615],
    "Parma": [44.8015, 10.3279],
    "Pavía": [45.1847, 9.1582],
    "Pavia": [45.1847, 9.1582],
    "Perugia": [43.1107, 12.3908],
    "Pesaro": [43.9125, 12.9155],
    "Pésaro": [43.9125, 12.9155],
    "Pescara": [42.4618, 14.2161],
    "Piacenza": [45.0526, 9.6930],
    "Pisa": [43.7228, 10.4017],
    "Pistoia": [43.9308, 10.9061],
    "Pomezia": [41.6696, 12.5014],
    "Pordenone": [45.9627, 12.6560],
    "Portici": [40.8188, 14.3381],
    "Potenza": [40.6404, 15.8056],
    "Pozzuoli": [40.8224, 14.1222],
    "Prato": [43.8777, 11.1022],
    "Quartu Sant'Elena": [39.2363, 9.1906],
    "Ragusa": [36.9262, 14.7254],
    "Ravenna": [44.4184, 12.2035],
    "Reggio Calabria": [38.1144, 15.6504],
    "Reggio Emilia": [44.6990, 10.6300],
    "Rho": [45.5299, 9.0405],
    "Rimini": [44.0678, 12.5695],
    "Rímini": [44.0678, 12.5695],
    "Roma": [41.9028, 12.4964],
    "Rovigo": [45.0711, 11.7900],
    "Salerno": [40.6824, 14.7681],
    "San Severo": [41.6898, 15.3789],
    "Sanremo": [43.8160, 7.7760],
    "Sassari": [40.7259, 8.5557],
    "Scafati": [40.7542, 14.5258],
    "Scandicci": [43.7539, 11.1769],
    "Sesto San Giovanni": [45.5360, 9.2308],
    "Siena": [43.3188, 11.3308],
    "Siracusa": [37.0755, 15.2866],
    "Taranto": [40.4644, 17.2470],
    "Tarento": [40.4644, 17.2470],
    "Teramo": [42.6589, 13.7039],
    "Terni": [42.5636, 12.6408],
    "Tívoli": [41.9634, 12.7968],
    "Torre del Greco": [40.7856, 14.3643],
    "Trani": [41.2727, 16.4155],
    "Trapani": [38.0174, 12.5151],
    "Trento": [46.0748, 11.1217],
    "Treviso": [45.6669, 12.2430],
    "Trieste": [45.6495, 13.7768],
    "Turin": [45.0703, 7.6869],
    "Turín": [45.0703, 7.6869],
    "Udine": [46.0637, 13.2446],
    "Varese": [45.8206, 8.8251],
    "Velletri": [41.6867, 12.7770],
    "Venecia": [45.4408, 12.3155],
    "Venezia": [45.4408, 12.3155],
    "Verona": [45.4384, 10.9916],
    "Viareggio": [43.8668, 10.2504],
    "Vicenza": [45.5455, 11.5354],
    "Vigevano": [45.3170, 8.8549],
    "Viterbo": [42.4207, 12.1077],
    "Vittoria": [36.9496, 14.5306],
    # --- INTERNACIONALES ---
    "Buenos Aires": [-34.6037, -58.3816],
    "Glasgow": [55.8642, -4.2518],
    "La Habana": [23.1136, -82.3666],
    "Lisboa": [38.7223, -9.1393],
    "Londres": [51.5074, -0.1278],
    "Marseille": [43.2965, 5.3698],
    "Marsella": [43.2965, 5.3698],
    "Montevideo": [-34.9011, -56.1645],
    "Nueva York": [40.7128, -74.0060],
    "París": [48.8566, 2.3522],
    "Rio de Janeiro": [-22.9068, -43.1729],
    "Río de Janeiro": [-22.9068, -43.1729],
    "Rosario": [-32.9468, -60.6393],
    "Santos": [-23.9618, -46.3322],
    "Sao Paulo": [-23.5505, -46.6333],
    "São Paulo": [-23.5505, -46.6333],
    "Viena": [48.2082, 16.3738],
}


@app.route("/mapa")
def mapa():
    proyecto = get_proyecto_activo()
    return render_template("mapa.html", proyecto_id=proyecto.id if proyecto else None)


@app.route("/api/map-data")
def map_api():
    proyecto = get_proyecto_activo()
    if not proyecto:
        return jsonify({"error": "No hay proyecto activo"}), 400
    
    # Filtrar por publicaciones y ciudades (múltiples valores)
    publicaciones_filtro = request.args.getlist('publicacion')
    ciudades_filtro = request.args.getlist('ciudad')
    
    # Debug: verificar total de registros
    total_prensa = Prensa.query.filter(Prensa.proyecto_id == proyecto.id).count()
    print(f"DEBUG: Total registros Prensa: {total_prensa}")
    
    query = db.session.query(Prensa.ciudad, func.count(Prensa.id))\
        .filter(Prensa.proyecto_id == proyecto.id, Prensa.incluido == True, Prensa.ciudad != None, Prensa.ciudad != '')
    
    if publicaciones_filtro:
        query = query.filter(Prensa.publicacion.in_(publicaciones_filtro))
        print(f"DEBUG: Filtro publicaciones: {publicaciones_filtro}")
    
    if ciudades_filtro:
        query = query.filter(Prensa.ciudad.in_(ciudades_filtro))
        print(f"DEBUG: Filtro ciudades: {ciudades_filtro}")
    
    results = query.group_by(Prensa.ciudad).all()
    print(f"DEBUG: Ciudades encontradas: {len(results)}")
    
    # Obtener desglose por publicación para cada ciudad
    marcadores = []
    for ciudad, cuenta in results:
        if not ciudad:
            continue

        ciudad_limpia = ciudad.strip()
        coords = ciudades_coords.get(ciudad_limpia)
        
        if not coords:
            print(f"DEBUG: No hay coordenadas para: {ciudad_limpia}")
            continue

        # Obtener desglose de publicaciones para esta ciudad
        pubs_query = db.session.query(Prensa.publicacion, func.count(Prensa.id))\
            .filter(Prensa.proyecto_id == proyecto.id, Prensa.ciudad == ciudad)
        
        if publicaciones_filtro:
            pubs_query = pubs_query.filter(Prensa.publicacion.in_(publicaciones_filtro))
        
        pubs_desglose = pubs_query.group_by(Prensa.publicacion).all()
        publicaciones_dict = {pub: count for pub, count in pubs_desglose if pub}
        
        marcadores.append(
            {
                "name": ciudad_limpia,
                "lat": coords[0],
                "lon": coords[1],
                "count": cuenta,
                "radius": 5 + (cuenta**0.5) * 2,
                "publicaciones": publicaciones_dict
            }
        )
    
    print(f"DEBUG: Marcadores generados: {len(marcadores)}")
    response = jsonify(marcadores)
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


@app.route("/mapa_autores")
@login_required
def mapa_autores():
    proyecto = get_proyecto_activo()
    
    # Obtener listas para filtros
    nacionalidades = db.session.query(AutorBio.nacionalidad).distinct().all()
    nacionalidades = sorted([n[0] for n in nacionalidades if n[0]])
    
    from models import AutorPrensa
    publicaciones_query = db.session.query(Prensa.publicacion).join(AutorPrensa, Prensa.id == AutorPrensa.prensa_id).distinct().all()
    publicaciones = sorted([p[0] for p in publicaciones_query if p[0]])
    
    return render_template("mapa_autores.html", 
                         proyecto=proyecto, 
                         nacionalidades=nacionalidades, 
                         publicaciones=publicaciones)



@app.route("/api/autores/map-data")
@login_required
def api_autores_map_data():
    proyecto_activo = get_proyecto_activo()

    def normalizar_texto(valor):
        import unicodedata
        texto = ' '.join((valor or '').split()).strip().casefold()
        return ''.join(
            c for c in unicodedata.normalize('NFKD', texto)
            if not unicodedata.combining(c)
        )

    # Obtener parámetros de filtro
    nacionalidad = request.args.get('nacionalidad')
    ciudad_filtro = request.args.get('ciudad')
    siglo = request.args.get('siglo')
    publicacion = request.args.get('publicacion')
    
    # Query base
    query = AutorBio.query
    
    # Filtro por nacionalidad
    if nacionalidad:
        query = query.filter(AutorBio.nacionalidad.ilike(f"%{nacionalidad}%"))
        
    # Filtro por ciudad (lugar de nacimiento)
    if ciudad_filtro:
        query = query.filter(AutorBio.lugar_nacimiento.ilike(f"%{ciudad_filtro}%"))
        
    # Filtro por siglo
    if siglo:
        try:
            s_num = int(siglo)
            start_year = (s_num - 1) * 100 + 1
            end_year = s_num * 100
            year_part = func.reverse(func.split_part(func.reverse(AutorBio.fecha_nacimiento), '/', 1))
            query = query.filter(year_part.op('~')('^[0-9]+$'))
            query = query.filter(cast(year_part, Integer).between(start_year, end_year))
        except:
            pass
            
    # Filtro por publicación
    if publicacion:
        from models import AutorPrensa
        # Join explícito por nombre/apellido ya que no hay FK directa
        query = query.join(AutorPrensa, (AutorBio.nombre == AutorPrensa.nombre) & (AutorBio.apellido == AutorPrensa.apellido)) \
                     .join(Prensa, Prensa.id == AutorPrensa.prensa_id) \
                     .filter(Prensa.publicacion == publicacion).distinct()
    
    # Obtener autores con lugar de nacimiento
    autores = query.filter(AutorBio.lugar_nacimiento.isnot(None), AutorBio.lugar_nacimiento != '').all()
    
    from collections import defaultdict
    from models import AutorPrensa

    # Obtener proyectos accesibles para el usuario
    user_proyectos = [p.id for p in current_user.proyectos]
    
    # Pre-obtener todas las publicaciones de los autores en los proyectos del usuario
    all_pubs = db.session.query(AutorPrensa.nombre, AutorPrensa.apellido, Prensa.publicacion) \
                 .join(Prensa, Prensa.id == AutorPrensa.prensa_id) \
                 .filter(Prensa.proyecto_id.in_(user_proyectos)) \
                 .distinct().all()
    
    author_pubs_map = defaultdict(list)
    for nom, ape, pub in all_pubs:
        if pub:
            author_pubs_map[(nom, ape)].append(pub)

    autores_proyecto_activo = set()
    if proyecto_activo:
        autores_locales = AutorBio.query.filter_by(proyecto_id=proyecto_activo.id).all()
        autores_proyecto_activo = {
            (normalizar_texto(a.nombre), normalizar_texto(a.apellido))
            for a in autores_locales
        }

    marcadores = []
    autores_vistos = set()
    ciudades_cache = {} 
    
    for a in autores:
        # Evitar duplicados visuales en el mapa
        auth_key = f"{a.nombre}|{a.apellido}|{a.lugar_nacimiento}".lower()
        if auth_key in autores_vistos:
            continue
        autores_vistos.add(auth_key)
        lugar = a.lugar_nacimiento.strip()
        nombre_ciudad = lugar.split(',')[0].strip()
        
        coords = None
        if nombre_ciudad in ciudades_cache:
            coords = ciudades_cache[nombre_ciudad]
        else:
            coords = ciudades_coords.get(nombre_ciudad)
            if not coords:
                c_obj = Ciudad.query.filter(Ciudad.name.ilike(nombre_ciudad)).first()
                if c_obj and c_obj.lat and c_obj.lon:
                    coords = [c_obj.lat, c_obj.lon]
            
            if coords:
                ciudades_cache[nombre_ciudad] = coords

        if coords:
            publicaciones = author_pubs_map.get((a.nombre, a.apellido), [])
            clave_nombre = (normalizar_texto(a.nombre), normalizar_texto(a.apellido))
            clave_invertida = (normalizar_texto(a.apellido), normalizar_texto(a.nombre))
            es_local = False
            if proyecto_activo:
                es_local = (
                    a.proyecto_id == proyecto_activo.id or
                    clave_nombre in autores_proyecto_activo or
                    clave_invertida in autores_proyecto_activo
                )
            
            marcadores.append({
                "id": a.id,
                "nombre": a.nombre,
                "apellido": a.apellido,
                "seudonimo": a.seudonimo,
                "proyecto_id": a.proyecto_id,
                "es_proyecto_activo": es_local,
                "lugar_nacimiento": a.lugar_nacimiento,
                "fechas_vida": a.fechas_vida,
                "foto": url_for('static', filename='uploads/autores/' + a.foto) if a.foto else None,
                "lat": coords[0],
                "lon": coords[1],
                "publicaciones": sorted(list(set(publicaciones)))
            })
            
    return jsonify(marcadores)


# =========================================================
# ⏳ LÍNEA DE TIEMPO
# =========================================================
@app.route("/timeline")
def timeline():
    return render_template("timeline.html")


@app.route("/api/timeline-data")
def timeline_api():
    proyecto = get_proyecto_activo()
    if not proyecto:
        return jsonify({"error": "No hay proyecto activo"}), 400
    
    noticias = Prensa.query.filter(
        Prensa.proyecto_id == proyecto.id,
        Prensa.incluido == True,
        Prensa.fecha_original != None
    ).all()
    items = []
    for n in noticias:
        dt, _ = try_parse_fecha_ddmmyyyy(n.fecha_original)
        if dt:
            clase = "pub-otros"
            pub_lower = (n.publicacion or "").lower()
            if "eco" in pub_lower:
                clase = "pub-el"
            elif "lavoro" in pub_lower:
                clase = "pub-il"
            elif "diario" in pub_lower:
                clase = "pub-diario"

            items.append(
                {
                    "id": n.id,
                    "content": f"<b>{n.publicacion}</b><br>{(n.titulo or '')[:30]}...",
                    "start": dt.strftime("%Y-%m-%d"),
                    "className": clase,
                    "titulo_completo": n.titulo,
                    "url_editar": url_for("editar", id=n.id),
                }
            )

    response = jsonify(items)
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


@app.route("/api/noticia/<int:id>")
def noticia_api(id):
    """API para obtener detalles de una noticia específica"""
    noticia = db.session.get(Prensa, id)
    if not noticia:
        return jsonify({"error": "Noticia no encontrada"}), 404

    return jsonify(
        {
            "id": noticia.id,
            "titulo": noticia.titulo,
            "contenido": noticia.contenido,
            "publicacion": noticia.publicacion,
            "ciudad": noticia.ciudad,
            "fecha_original": noticia.fecha_original,
            "autor": noticia.autor,
            "tipo_recurso": noticia.tipo_recurso,
        }
    )


# =========================================================
# REDES (SNA)
# =========================================================
@app.route("/redes")
def redes():
    return render_template("redes.html")


@app.route("/analisis-avanzado")
@login_required
def analisis_avanzado():
    """Vista principal de análisis avanzados de humanidades digitales"""
    from models import Hemeroteca, Publicacion, Prensa
    
    proyecto = get_proyecto_activo()
    if not proyecto:
        flash("No hay proyecto activo", "warning")
        return redirect(url_for("index"))
    
    # Obtener hemerotecas del proyecto
    hemerotecas = Hemeroteca.query.filter_by(proyecto_id=proyecto.id).all()
    
    # Obtener publicaciones del proyecto
    publicaciones = Publicacion.query.filter_by(proyecto_id=proyecto.id).all()
    
    # Obtener temas únicos de las noticias del proyecto (Prensa.temas)
    temas = db.session.query(Prensa.temas)\
        .filter(Prensa.proyecto_id == proyecto.id, Prensa.incluido == True)\
        .filter(Prensa.temas.isnot(None))\
        .filter(Prensa.temas != '')\
        .distinct()\
        .all()
    temas = sorted([t[0] for t in temas if t[0]])

    # Obtener países únicos de las noticias del proyecto
    paises = db.session.query(Prensa.pais_publicacion)\
        .filter(Prensa.proyecto_id == proyecto.id, Prensa.incluido == True)\
        .filter(Prensa.pais_publicacion.isnot(None))\
        .distinct()\
        .all()
    paises = sorted([p[0] for p in paises if p[0]])
    
    return render_template("analisis_avanzado.html", 
                         hemerotecas=hemerotecas, 
                         publicaciones=publicaciones,
                         temas=temas,
                         paises=paises,
                         proyecto=proyecto)


@app.route("/analisis-innovador")
@login_required
def analisis_innovador():
    """Vista de Análisis Innovadores de humanidades digitales"""
    from models import Hemeroteca, Publicacion, Prensa
    
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
        .distinct()\
        .all()
    temas = sorted([t[0] for t in temas if t[0]])

    # Obtener países únicos
    paises = db.session.query(Prensa.pais_publicacion)\
        .filter(Prensa.proyecto_id == proyecto.id, Prensa.incluido == True)\
        .filter(Prensa.pais_publicacion.isnot(None))\
        .distinct()\
        .all()
    paises = sorted([p[0] for p in paises if p[0]])
    
    return render_template("analisis_innovador.html", 
                         hemerotecas=hemerotecas, 
                         publicaciones=publicaciones,
                         temas=temas,
                         paises=paises,
                         proyecto=proyecto)


@app.route("/analisis/regex-lab")
@login_required
def regex_lab():
    """Vista del Laboratorio REGEX"""
    from models import Hemeroteca, Publicacion, Prensa
    
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
        .distinct()\
        .all()
    temas = sorted([t[0] for t in temas if t[0]])

    # Obtener países únicos
    paises = db.session.query(Prensa.pais_publicacion)\
        .filter(Prensa.proyecto_id == proyecto.id, Prensa.incluido == True)\
        .filter(Prensa.pais_publicacion.isnot(None))\
        .distinct()\
        .all()
    paises = sorted([p[0] for p in paises if p[0]])
    
    return render_template("regex_lab.html", 
                         hemerotecas=hemerotecas, 
                         publicaciones=publicaciones,
                         temas=temas,
                         paises=paises,
                         proyecto=proyecto)


@app.route("/config-red")
@login_required
def config_red():
    """Página de configuración de tipos de nodos de red"""
    proyecto = get_proyecto_activo()
    if not proyecto:
        flash("No hay proyecto activo", "warning")
        return redirect(url_for("index"))
    return render_template("config_red_v3.html", proyecto=proyecto)


@app.route("/api/config-red", methods=["GET", "POST"])
@login_required
def api_config_red():
    """API para obtener/guardar configuración de red"""
    proyecto = get_proyecto_activo()
    if not proyecto:
        return jsonify({"error": "No hay proyecto activo"}), 400
    
    if request.method == "GET":
        # Devolver configuración actual
        import json
        try:
            config = json.loads(proyecto.red_tipos or '{}')
        except:
            config = {}
        return jsonify({"tipos": config})
    
    elif request.method == "POST":
        # Guardar nueva configuración
        import json
        data = request.get_json()
        tipos = data.get("tipos", {})
        
        # Validar estructura
        if not isinstance(tipos, dict):
            return jsonify({"error": "Formato inválido"}), 400
        
        # Guardar en proyecto
        proyecto.red_tipos = json.dumps(tipos)
        db.session.commit()
        
        return jsonify({"success": True})


@app.route("/api/detectar-entidades", methods=["POST"])
@csrf.exempt
def detectar_entidades():
    """Detecta automáticamente entidades usando spaCy NER"""
    try:
        # Verificar autenticación para API
        if not current_user.is_authenticated:
            return jsonify({"error": "No autenticado"}), 401
        
        proyecto = get_proyecto_activo()
        if not proyecto:
            return jsonify({"error": "No hay proyecto activo"}), 400
        
        data = request.get_json()
        if not data:
            return jsonify({"error": "No se recibió JSON válido"}), 400
            
        tipos_nombres = data.get("tipos", {})  # {tipo1: "Personas", tipo2: "Barcos", ...}
        
        if not tipos_nombres:
            return jsonify({"error": "No se proporcionaron tipos"}), 400
    
        # Cargar modelo spaCy (centralizado en utils.py)
        nlp = get_nlp()
        if not nlp:
            return jsonify({"error": "Modelo spaCy no disponible. Ejecuta: python -m spacy download es_core_news_md"}), 500
        
        # Obtener noticias del proyecto
        noticias = Prensa.query.filter_by(proyecto_id=proyecto.id).limit(1000).all()
        
        from collections import Counter, defaultdict
        
        resultados = {}
        
        # Mapeo de tipos de usuario a categorías spaCy
        # PER = Personas, LOC = Lugares, ORG = Organizaciones, MISC = Miscelánea
        tipo_a_spacy = {}
        
        for tipo_key, tipo_nombre in tipos_nombres.items():
            tipo_lower = tipo_nombre.lower()
            
            # Determinar qué categoría spaCy usar según el nombre del tipo
            if any(kw in tipo_lower for kw in ['persona', 'gente', 'capitán', 'tripulante', 'pasajero', 'náufrago', 'oficial', 'marinero', 'víctima', 'nombre']):
                tipo_a_spacy[tipo_key] = ['PER']
            elif any(kw in tipo_lower for kw in ['lugar', 'ciudad', 'puerto', 'geografía', 'costa', 'región', 'zona', 'localidad', 'país']):
                tipo_a_spacy[tipo_key] = ['LOC']
            elif any(kw in tipo_lower for kw in ['organización', 'institución', 'empresa', 'compañía', 'gobierno', 'partido']):
                tipo_a_spacy[tipo_key] = ['ORG']
            elif any(kw in tipo_lower for kw in ['barco', 'buque', 'vapor', 'embarcación', 'navío', 'nave']):
                # Barcos son MISC en spaCy, pero necesitamos detección especial
                tipo_a_spacy[tipo_key] = ['MISC', 'barcos']
            else:
                # Tipo genérico: usar todas las categorías
                tipo_a_spacy[tipo_key] = ['PER', 'LOC', 'ORG', 'MISC']
        
        # Procesar textos con spaCy
        entidades_por_tipo = defaultdict(Counter)
        
        # Keywords para barcos (detección especial)
        keywords_barco = ['vapor', 'buque', 's.s.', 'ss', 's/s', 'transatlántico', 'crucero', 
                         'fragata', 'paquebote', 'naufragio', 'hundimiento', 'zarpó', 'arribó', 
                         'bordo', 'tripulación', 'navío', 'embarcación']
        
        for noticia in noticias:
            # Combinar texto
            texto = ""
            if noticia.contenido:
                texto += noticia.contenido + " "
            if noticia.titulo:
                texto += noticia.titulo + " "
            if noticia.resumen:
                texto += noticia.resumen + " "
            
            if len(texto.strip()) < 10:
                continue
            
            # Procesar con spaCy (limitar a 10000 chars para performance)
            doc = nlp(texto[:10000])
            
            # Extraer entidades nombradas
            for ent in doc.ents:
                texto_entidad = ent.text.strip()
                label_spacy = ent.label_
                
                # Filtros básicos
                if len(texto_entidad) <= 2:
                    continue
                
                # Filtrar stopwords comunes
                stopwords = ['El', 'La', 'Los', 'Las', 'Un', 'Una', 'De', 'Muy', 'Más', 'Menos']
                if texto_entidad in stopwords:
                    continue
                
                # Asignar a tipos de usuario según mapeo
                for tipo_key, categorias_spacy in tipo_a_spacy.items():
                    if 'barcos' in categorias_spacy:
                        # Detección especial para barcos
                        oracion_contexto = ent.sent.text.lower() if ent.sent else ""
                        
                        # Es barco si:
                        # 1. Contiene prefijo náutico en el nombre
                        # 2. Aparece en contexto náutico
                        tiene_prefijo = any(pref in texto_entidad.lower() for pref in ['s.s.', 'vapor', 'buque'])
                        tiene_contexto_nautico = any(kw in oracion_contexto for kw in keywords_barco)
                        
                        if tiene_prefijo or (label_spacy == 'MISC' and tiene_contexto_nautico):
                            entidades_por_tipo[tipo_key][texto_entidad] += 1
                    
                    elif label_spacy in categorias_spacy:
                        # Filtros adicionales por tipo
                        if label_spacy == 'PER':
                            # Personas: al menos 2 palabras (nombre + apellido)
                            if len(texto_entidad.split()) >= 2:
                                entidades_por_tipo[tipo_key][texto_entidad] += 1
                        
                        elif label_spacy == 'LOC':
                            # Lugares: aceptar todo
                            entidades_por_tipo[tipo_key][texto_entidad] += 1
                        
                        elif label_spacy == 'ORG':
                            # Organizaciones: al menos 2 palabras
                            if len(texto_entidad.split()) >= 2:
                                entidades_por_tipo[tipo_key][texto_entidad] += 1
                        
                        else:
                            # MISC y otros
                            entidades_por_tipo[tipo_key][texto_entidad] += 1
        
        # Preparar resultados: Top 20 por tipo
        for tipo_key in tipos_nombres.keys():
            if tipo_key in entidades_por_tipo:
                # Filtrar por frecuencia mínima de 2
                entidades_filtradas = {
                    nombre: count 
                    for nombre, count in entidades_por_tipo[tipo_key].items() 
                    if count >= 2
                }
                
                # Ordenar por frecuencia y tomar top 20
                top_20 = sorted(entidades_filtradas.items(), key=lambda x: x[1], reverse=True)[:20]
                
                resultados[tipo_key] = [
                    {"nombre": nombre, "menciones": count}
                    for nombre, count in top_20
                ]
            else:
                resultados[tipo_key] = []
        
        return jsonify({"entidades": resultados})
    except Exception as e:
        print(f"[ERROR] detectar_entidades (processing): {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Error en detección: {str(e)}"}), 500


@app.route("/api/network-data")
def network_data():
    # Obtener proyecto activo
    proyecto = get_proyecto_activo()
    if not proyecto:
        return jsonify({"error": "No hay proyecto activo"}), 400

    # Cargar configuración de tipos de red del proyecto
    import json
    import re
    try:
        red_config = json.loads(proyecto.red_tipos or '{}')
    except:
        red_config = {}
    
    # Si no hay configuración, usar valores por defecto
    if not red_config:
        red_config = {
            "tipo1": {"nombre": "Principales", "color": "#ff9800", "forma": "dot", "entidades": []},
            "tipo2": {"nombre": "Secundarios", "color": "#03a9f4", "forma": "dot", "entidades": []},
            "tipo3": {"nombre": "Lugares", "color": "#4a7c2f", "forma": "square", "entidades": []}
        }

    # Obtener todas las noticias del proyecto que están INCLUIDAS
    noticias = Prensa.query.filter_by(proyecto_id=proyecto.id, incluido=True).all()

    # Crear diccionario de entidad -> tipo (normalizado a minúsculas)
    entidad_tipo = {}
    for tipo_key, tipo_data in red_config.items():
        for entidad in tipo_data.get('entidades', []):
            entidad_nombre = entidad if isinstance(entidad, str) else entidad.get('nombre', '')
            if entidad_nombre:
                entidad_norm = entidad_nombre.strip().lower()
                entidad_tipo[entidad_norm] = tipo_key

    # Si no hay entidades configuradas, buscar en el contenido de las noticias
    if not entidad_tipo:
        # Extraer nombres propios del contenido usando regex simple
        from collections import Counter
        
        nombres_encontrados = Counter()
        
        for n in noticias[:200]:  # Limitar a 200 noticias para performance
            texto = ""
            if n.contenido:
                texto += " " + n.contenido
            if n.titulo:
                texto += " " + n.titulo
            if n.resumen:
                texto += " " + n.resumen
            
            # Buscar nombres propios (palabras que empiezan con mayúscula)
            # Patrón: palabra con mayúscula seguida opcionalmente de más palabras
            patrones = re.findall(r'\b([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+){0,3})\b', texto)
            
            for patron in patrones:
                # Filtrar palabras comunes que no son nombres
                if patron not in ['El', 'La', 'Los', 'Las', 'Un', 'Una', 'De', 'Del', 'Al', 'En', 'Con', 'Por', 'Para', 'Desde', 'Hasta']:
                    nombres_encontrados[patron] += 1
        
        # Crear configuración temporal con los top nombres
        top_nombres = [n for n, c in nombres_encontrados.most_common(30) if c >= 3]
        
        for nombre in top_nombres:
            entidad_tipo[nombre.lower()] = "tipo1"  # Todos como tipo1 por defecto

    # Contar apariciones de cada entidad en palabras clave, temas Y contenido
    from collections import Counter
    entidad_counter = Counter()
    
    for n in noticias:
        textos = []
        
        # Buscar en palabras_clave
        if n.palabras_clave:
            textos.append(n.palabras_clave)
        
        # Buscar en temas
        if n.temas:
            textos.append(n.temas)
        
        # Buscar en contenido
        if n.contenido:
            textos.append(n.contenido)
        
        if n.titulo:
            textos.append(n.titulo)
            
        if n.resumen:
            textos.append(n.resumen)
        
        # Buscar cada entidad en los textos
        texto_completo = " ".join(textos).lower()
        
        for entidad_original in entidad_tipo.keys():
            # Contar menciones (case insensitive)
            if entidad_original in texto_completo:
                # Buscar la variante original para mostrar
                for ent_config in red_config.values():
                    for ent in ent_config.get('entidades', []):
                        if isinstance(ent, str) and ent.lower() == entidad_original:
                            entidad_counter[ent] += texto_completo.count(entidad_original)
                            break

    # Crear nodos con grupos según configuración
    nodes = []
    for entidad, count in entidad_counter.items():
        if count >= 2:  # Mínimo 2 menciones
            tipo_key = entidad_tipo.get(entidad.lower())
            if tipo_key and tipo_key in red_config:
                nodes.append({
                    "id": entidad,
                    "label": entidad,
                    "group": tipo_key,
                    "value": 8 + (count ** 0.5) * 2
                })

    # Crear enlaces basados en co-ocurrencia en documentos
    edges = []
    edge_counts = Counter()
    
    for n in noticias:
        # Obtener todas las entidades mencionadas en esta noticia
        texto = ""
        if n.contenido:
            texto += " " + n.contenido
        if n.titulo:
            texto += " " + n.titulo
        if n.resumen:
            texto += " " + n.resumen
        if n.palabras_clave:
            texto += " " + n.palabras_clave
        if n.temas:
            texto += " " + n.temas
        
        texto_lower = texto.lower()
        
        # Encontrar qué entidades aparecen en este documento
        entidades_en_doc = set()
        for entidad in entidad_counter.keys():
            if entidad.lower() in texto_lower:
                entidades_en_doc.add(entidad)
        
        # Crear enlaces entre todas las combinaciones
        entidades_list = list(entidades_en_doc)
        for i in range(len(entidades_list)):
            for j in range(i + 1, len(entidades_list)):
                pair = tuple(sorted([entidades_list[i], entidades_list[j]]))
                edge_counts[pair] += 1
    
    # Convertir a formato de edges con peso
    for (source, target), weight in edge_counts.items():
        if weight >= 1:
            edges.append({"from": source, "to": target, "value": weight})
    
    # Incluir configuración de tipos en la respuesta
    response = jsonify({"nodes": nodes, "edges": edges, "tipos": red_config})
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


@app.route("/api/redes/filtros")
def api_redes_filtros():
    """Endpoint para obtener opciones de filtros (publicaciones y rango de fechas)"""
    proyecto = get_proyecto_activo()
    if not proyecto:
        return jsonify({"error": "No hay proyecto activo"}), 400
    
    # Obtener todas las publicaciones únicas del proyecto
    publicaciones_query = db.session.query(Prensa.publicacion)\
        .filter(Prensa.proyecto_id == proyecto.id, Prensa.incluido == True)\
        .filter(Prensa.publicacion.isnot(None))\
        .filter(Prensa.publicacion != '')\
        .distinct()\
        .order_by(Prensa.publicacion)\
        .all()
    
    publicaciones = [p[0] for p in publicaciones_query if p[0]]
    
    # Obtener rango de fechas (min y max) de forma cronológica
    # Como las fechas son 'DD/MM/YYYY' en texto, no podemos usar min() directamente
    todas_fechas = db.session.query(Prensa.fecha_original)\
        .filter(Prensa.proyecto_id == proyecto.id, Prensa.incluido == True)\
        .filter(Prensa.fecha_original.isnot(None))\
        .filter(Prensa.fecha_original != '')\
        .all()
    
    fecha_min_query = None
    fecha_max_query = None
    
    if todas_fechas:
        fechas_validas = []
        for f in todas_fechas:
            try:
                # Intentar parsear DD/MM/YYYY
                dt = datetime.strptime(f[0].strip(), "%d/%m/%Y")
                fechas_validas.append(dt)
            except:
                continue
        
        if fechas_validas:
            fecha_min_query = min(fechas_validas).strftime("%d/%m/%Y")
            fecha_max_query = max(fechas_validas).strftime("%d/%m/%Y")
    
    return jsonify({
        "publicaciones": publicaciones,
        "fecha_min": fecha_min_query,
        "fecha_max": fecha_max_query
    })


@app.route("/api/redes/node_docs")
def api_redes_node_docs():
    """Endpoint para obtener noticias que mencionan una entidad específica"""
    proyecto = get_proyecto_activo()
    if not proyecto:
        return jsonify({"error": "No hay proyecto activo"}), 400
    
    entidad_id = request.args.get('id', '')
    if not entidad_id:
        return jsonify([])
    
    # Buscar noticias que contengan la entidad
    entidad_lower = entidad_id.lower()
    noticias = Prensa.query.filter_by(proyecto_id=proyecto.id, incluido=True).limit(1000).all()
    
    resultados = []
    for n in noticias:
        texto_completo = ""
        if n.contenido:
            texto_completo += n.contenido + " "
        if n.titulo:
            texto_completo += n.titulo + " "
        if n.resumen:
            texto_completo += n.resumen + " "
        if n.palabras_clave:
            texto_completo += n.palabras_clave + " "
        if n.temas:
            texto_completo += n.temas + " "
        
        if entidad_lower in texto_completo.lower():
            resultados.append({
                "id": n.id,
                "titulo": n.titulo or "Sin título",
                "fecha": n.fecha_original or "",
                "publicacion": n.publicacion or "",
                "url_editar": url_for('editar', id=n.id)
            })
    
    return jsonify(resultados[:50])  # Limitar a 50 resultados


@app.route("/api/redes")
def api_redes():
    """Endpoint para generar datos de red con filtros"""
    proyecto = get_proyecto_activo()
    if not proyecto:
        return jsonify({"error": "No hay proyecto activo"}), 400
    
    # Cargar configuración de tipos de red
    import json
    try:
        red_config = json.loads(proyecto.red_tipos or '{}')
    except:
        red_config = {}
    
    print(f"[DEBUG] red_config: {red_config}")
    
    if not red_config:
        red_config = {
            "tipo1": {"nombre": "Principales", "color": "#ff9800", "forma": "dot", "entidades": []},
            "tipo2": {"nombre": "Secundarios", "color": "#03a9f4", "forma": "dot", "entidades": []},
            "tipo3": {"nombre": "Lugares", "color": "#4a7c2f", "forma": "square", "entidades": []}
        }
    
    # Obtener filtros
    publicaciones_filtro = request.args.getlist('publicacion')
    fecha_desde = request.args.get('fecha_desde')
    fecha_hasta = request.args.get('fecha_hasta')
    min_edge = int(request.args.get('min_edge', 1))
    min_node = int(request.args.get('min_node', 2))
    max_docs = int(request.args.get('max_docs', 5000))
    
    # Consulta base (Filtrar solo noticias ACTIVAS)
    query = Prensa.query.filter_by(proyecto_id=proyecto.id, incluido=True)
    
    # Aplicar filtros
    if publicaciones_filtro:
        query = query.filter(Prensa.publicacion.in_(publicaciones_filtro))
    
    if fecha_desde:
        from models import SQL_PRENSA_DATE
        from sqlalchemy import text
        query = query.filter(text(f"{SQL_PRENSA_DATE} >= :d").params(d=fecha_desde))
    
    if fecha_hasta:
        from models import SQL_PRENSA_DATE
        from sqlalchemy import text
        query = query.filter(text(f"{SQL_PRENSA_DATE} <= :h").params(h=fecha_hasta))
    
    # Limitar resultados
    noticias = query.limit(max_docs).all()
    
    # Crear diccionario de entidad -> tipo
    entidad_tipo = {}
    for tipo_key, tipo_data in red_config.items():
        for entidad in tipo_data.get('entidades', []):
            entidad_nombre = entidad if isinstance(entidad, str) else entidad.get('nombre', '')
            if entidad_nombre:
                entidad_norm = entidad_nombre.strip().lower()
                entidad_tipo[entidad_norm] = tipo_key
    
    print(f"[DEBUG] Entidades configuradas: {list(entidad_tipo.keys())[:10]}")
    print(f"[DEBUG] Total entidades: {len(entidad_tipo)}")
    print(f"[DEBUG] Total noticias: {len(noticias)}")
    
    # Contar apariciones de entidades
    from collections import Counter
    entidad_counter = Counter()
    
    for n in noticias:
        textos = []
        if n.palabras_clave:
            textos.append(n.palabras_clave)
        if n.temas:
            textos.append(n.temas)
        if n.contenido:
            textos.append(n.contenido)
        if n.titulo:
            textos.append(n.titulo)
        if n.resumen:
            textos.append(n.resumen)
        
        texto_completo = " ".join(textos).lower()
        
        # Buscar cada entidad configurada en el texto
        for tipo_key, tipo_data in red_config.items():
            for entidad in tipo_data.get('entidades', []):
                nombre = entidad.get('nombre', '') if isinstance(entidad, dict) else entidad
                if nombre:
                    nombre_lower = nombre.lower()
                    count = texto_completo.count(nombre_lower)
                    if count > 0:
                        entidad_counter[nombre] += count
                    
                    # Buscar también por alias
                    if isinstance(entidad, dict):
                        for alias in entidad.get('alias', []):
                            if alias:
                                alias_lower = alias.lower()
                                count_alias = texto_completo.count(alias_lower)
                                if count_alias > 0:
                                    entidad_counter[nombre] += count_alias
    
    # Crear nodos
    nodes = []
    print(f"[DEBUG] Entidad counter: {dict(list(entidad_counter.items())[:5])}")
    print(f"[DEBUG] Min node threshold: {min_node}")
    
    for entidad, count in entidad_counter.items():
        if count >= min_node:
            tipo_key = entidad_tipo.get(entidad.lower())
            if tipo_key and tipo_key in red_config:
                nodes.append({
                    "id": entidad,
                    "label": entidad,
                    "group": tipo_key,
                    "value": 8 + (count ** 0.5) * 2
                })
    
    print(f"[DEBUG] Nodos creados: {len(nodes)}")
    
    # Crear enlaces por co-ocurrencia
    edges = []
    edge_counts = Counter()
    
    for n in noticias:
        texto = ""
        if n.contenido:
            texto += " " + n.contenido
        if n.titulo:
            texto += " " + n.titulo
        if n.resumen:
            texto += " " + n.resumen
        if n.palabras_clave:
            texto += " " + n.palabras_clave
        if n.temas:
            texto += " " + n.temas
        
        texto_lower = texto.lower()
        
        entidades_en_doc = set()
        for entidad in entidad_counter.keys():
            if entidad.lower() in texto_lower:
                entidades_en_doc.add(entidad)
        
        entidades_list = list(entidades_en_doc)
        for i in range(len(entidades_list)):
            for j in range(i + 1, len(entidades_list)):
                pair = tuple(sorted([entidades_list[i], entidades_list[j]]))
                edge_counts[pair] += 1
    
    for (source, target), weight in edge_counts.items():
        if weight >= min_edge:
            edges.append({"from": source, "to": target, "value": weight})
    
    response = jsonify({
        "nodes": nodes,
        "edges": edges,
        "tipos": red_config,
        "meta": {"docs": len(noticias)}
    })
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


@app.route("/exportar_gephi")
def exportar_gephi():
    proyecto = get_proyecto_activo()
    if not proyecto:
        flash("No hay proyecto activo", "warning")
        return redirect(url_for('index'))
    
    actores = {
        "Capitán Piccone": ["piccone", "piconne"],
        "Sirio": ["sirio"],
        "Lola Millanes": ["millanes"],
        "Obispo": ["obispo"],
    }
    G = nx.Graph()
    for actor in actores.keys():
        G.add_node(actor, label=actor)

    noticias = (
        db.session.query(Prensa.contenido)
        .filter(
            Prensa.proyecto_id == proyecto.id,
            Prensa.contenido != None
        )
        .limit(50)
        .all()
    )
    for nota in noticias:
        txt = nota.contenido.lower()
        encontrados = [k for k, v in actores.items() if any(x in txt for x in v)]
        if len(encontrados) > 1:
            for u, v in combinations(sorted(encontrados), 2):
                if G.has_edge(u, v):
                    G[u][v]["weight"] += 1
                else:
                    G.add_edge(u, v, weight=1)

    buffer = BytesIO()
    nx.write_gexf(G, buffer)
    buffer.seek(0)
    return send_file(
        buffer, mimetype="application/xml", as_attachment=True, download_name="red.gexf"
    )


# =========================================================
# FUNCIONES AUXILIARES RIGUROSAS
# =========================================================
def ordenar_por_fecha(query, descendente=False):
    orden_sql = text(
        f"CASE WHEN fecha_original ~ '^[0-3]?[0-9]/[0-1]?[0-9]/[0-9]{{2,4}}$' THEN to_date(fecha_original, 'DD/MM/YYYY') ELSE NULL END {'DESC' if descendente else 'ASC'} NULLS LAST, publicacion ASC"
    )
    return query.order_by(orden_sql)


def normalizar_next(next_raw):
    if not next_raw:
        return None
    parsed = urlparse(unquote(next_raw))
    if not parsed.path.startswith("/"):
        return "/"
    if parsed.path.startswith("/filtrar"):
        safe_path = "/"
    else:
        safe_path = parsed.path
    qs = urlencode(parse_qs(parsed.query), doseq=True)
    return f"{safe_path}?{qs}" if qs else safe_path


# Gestión de Autores
def separar_autor(autor_raw):
    if (
        not autor_raw
        or autor_raw.lower() == "anónimo"
        or autor_raw.lower() == "anonimo"
    ):
        return ("", "")
    autor_raw = autor_raw.strip()
    # Si tiene coma "Apellido, Nombre"
    if "," in autor_raw:
        partes = [p.strip() for p in autor_raw.split(",")]
        return (partes[1], partes[0]) if len(partes) >= 2 else ("", autor_raw)
    # Si es "Nombre Apellido"
    pedazos = autor_raw.split()
    if len(pedazos) > 1:
        return (" ".join(pedazos[:-1]), pedazos[-1])
    return ("", autor_raw)


def capitalizar(w):
    return w[0].upper() + w[1:].lower() if w else ""


def formatear_autor(nombre, apellido, estilo):
    # Lógica estricta de autores
    if not apellido:
        return ""  # Sin autor

    ape = capitalizar(apellido)
    nom = " ".join(capitalizar(x) for x in nombre.split()) if nombre else ""
    inicial = nom[0] + "." if nom else ""

    if estilo == "apa":
        return f"{ape}, {inicial}"  # Pérez, J.
    if estilo == "mla" or estilo == "chicago":
        return f"{ape}, {nom}"  # Pérez, Juan
    if estilo == "une":
        return f"{ape.upper()}, {nom}"  # PÉREZ, Juan
    if estilo == "ieee":
        return f"{inicial} {ape}"  # J. Pérez
    if estilo == "cse":
        return f"{ape} {inicial.replace('.', '')}"  # Pérez J

    return f"{ape}, {nom}" if nom else ape


# Gestión de Fechas Estricta
def parse_fecha_rigurosa(fecha_str):
    if not fecha_str:
        return None
    fecha_str = fecha_str.strip()
    # Intento DD/MM/YYYY
    try:
        return datetime.strptime(fecha_str, "%d/%m/%Y")
    except:
        pass
    # Intento YYYY-MM-DD
    try:
        return datetime.strptime(fecha_str, "%Y-%m-%d")
    except:
        return None


def formatear_fecha(dt, estilo):
    if not dt:
        return "s.f."
    meses = [
        "",
        "enero",
        "febrero",
        "marzo",
        "abril",
        "mayo",
        "junio",
        "julio",
        "agosto",
        "septiembre",
        "octubre",
        "noviembre",
        "diciembre",
    ]
    meses_abrev = [
        "",
        "ene.",
        "feb.",
        "mar.",
        "abr.",
        "mayo",
        "jun.",
        "jul.",
        "ago.",
        "sept.",
        "oct.",
        "nov.",
        "dic.",
    ]

    d, m, y = dt.day, dt.month, dt.year

    if estilo == "apa":
        return f"({y}, {d} de {meses[m]})"  # (1906, 4 de agosto)
    if estilo == "mla":
        return f"{d} {meses_abrev[m]} {y}"  # 4 ago. 1906
    if estilo == "chicago":
        return f"{meses[m]} {d}, {y}"  # Agosto 4, 1906
    if estilo == "une":
        return f"{d} de {meses[m]} de {y}"
    if estilo == "ieee":
        return f"{meses_abrev[m]} {d}, {y}"
    if estilo == "iso":
        return f"{y}-{m:02d}-{d:02d}"

    return f"{d}/{m:02d}/{y}"


# =========================================================
# RUTA DE CITAS PROFESIONAL
# =========================================================
@app.route("/citar/<int:id>")
def citar(id):
    """
    Genera cita bibliográfica usando CitationGenerator de JavaScript.
    El backend solo pasa los datos a la plantilla.
    """
    ref = db.session.get(Prensa, id)
    if not ref:
        return abort(404)

    return render_template("cita.html", ref=ref)


# =========================================================
# [NUEVO] RUTA GALERÍA
# =========================================================
@app.route("/galeria")
def galeria():
    noticias = Prensa.query.filter(
        Prensa.imagen_scan != None, Prensa.imagen_scan != ""
    ).all()
    return render_template("galeria.html", noticias=noticias)


# Elimina la foto
@app.route("/borrar_imagen/<int:id>")
def borrar_imagen(id):
    noticia = db.session.get(Prensa, id)

    if noticia and noticia.imagen_scan:
        # 1. Borrar el archivo físico del disco
        try:
            ruta_archivo = os.path.join(
                app.config["UPLOAD_FOLDER"], noticia.imagen_scan
            )
            if os.path.exists(ruta_archivo):
                os.remove(ruta_archivo)
        except Exception as e:
            print(f"Error borrando archivo: {e}")

        # 2. Borrar el nombre en la base de datos
        noticia.imagen_scan = None
        db.session.commit()
        flash("🗑️ Imagen eliminada correctamente.", "success")

    # Volvemos a la página de editar
    return redirect(url_for("editar", id=id))


# =========================================================
# =========================================================
# 🧠 CONFIGURACIÓN DEL BUSCADOR SEMÁNTICO
# =========================================================
import unicodedata

vectorizer = None
tfidf_matrix = None
noticias_indices = []


def normalizar_texto(texto):
    """Elimina acentos y normaliza texto para mejores coincidencias"""
    if not texto:
        return ""
    # Eliminar acentos usando unicodedata
    texto = "".join(
        c
        for c in unicodedata.normalize("NFD", texto)
        if unicodedata.category(c) != "Mn"
    )
    return texto.lower().strip()


def extraer_fragmento_inteligente(contenido, query, max_chars=300):
    """Extrae el fragmento más relevante usando ventana deslizante"""
    if not contenido:
        return ""

    # Normalizar para búsqueda
    contenido_norm = normalizar_texto(contenido)
    palabras_query = [p for p in normalizar_texto(query).split() if len(p) > 2]

    if not palabras_query:
        return contenido[:max_chars] + ("..." if len(contenido) > max_chars else "")

    # Buscar ventana con más coincidencias
    mejor_pos = 0
    max_coincidencias = 0

    for i in range(0, max(1, len(contenido) - max_chars), 50):
        ventana = contenido_norm[i : i + max_chars]
        coincidencias = sum(1 for p in palabras_query if p in ventana)
        if coincidencias > max_coincidencias:
            max_coincidencias = coincidencias
            mejor_pos = i

    # Extraer fragmento
    fragmento = contenido[mejor_pos : mejor_pos + max_chars]
    if mejor_pos > 0:
        fragmento = "..." + fragmento
    if mejor_pos + max_chars < len(contenido):
        fragmento = fragmento + "..."

    return fragmento.strip()


def inicializar_buscador():
    global vectorizer, tfidf_matrix, noticias_indices
    print("[BUSCADOR] Entrenando motor de búsqueda semántico...")
    with app.app_context():
        # Cargamos solo lo necesario: ID, Título y Contenido
        noticias = (
            db.session.query(Prensa.id, Prensa.titulo, Prensa.contenido)
            .filter(Prensa.contenido != None)
            .all()
        )

        if not noticias:
            print("[AVISO] No hay noticias para indexar.")
            return

        # Creamos el "corpus" - título duplicado para darle más peso
        corpus = [
            f"{(n.titulo or '')} {(n.titulo or '')} {(n.contenido or '')}"
            for n in noticias
        ]
        noticias_indices = [n.id for n in noticias]

        # Entrenamos el modelo TF-IDF con parámetros optimizados
        vectorizer = TfidfVectorizer(
            min_df=1,
            max_df=0.85,
            ngram_range=(1, 2),  # Unigramas y bigramas
            stop_words=None,
            strip_accents="unicode",
        )
        try:
            tfidf_matrix = vectorizer.fit_transform(corpus)
            print(f"[OK] Motor listo: {len(noticias)} documentos indexados.")
        except Exception as e:
            print(f"[ERROR] Error entrenando buscador: {e}")


# =========================================================
# INICIALIZACIÓN AUTOMÁTICA DEL BUSCADOR
# =========================================================
# Inicializar el buscador semántico cuando se importa el módulo
# Esto garantiza que funcione tanto en desarrollo como en producción
# try:
#     with app.app_context():
#         if vectorizer is None:
#             print("[STARTUP] Inicializando buscador semántico...")
#             inicializar_buscador()
# except Exception as e:
#     print(f"[ERROR] No se pudo inicializar el buscador semántico: {e}")
    import traceback
    traceback.print_exc()


@app.route("/buscador_semantico")
@login_required
def buscador_semantico():
    from models import Publicacion, Prensa
    proyecto = get_proyecto_activo()
    if not proyecto:
        flash("Debes seleccionar un proyecto activo.", "warning")
        return redirect(url_for("dashboard"))
    
    # Obtener publicaciones y países para los filtros
    publicaciones = Publicacion.query.filter_by(proyecto_id=proyecto.id).order_by(Publicacion.nombre).all()
    paises = [p[0] for p in db.session.query(Prensa.pais_publicacion).filter_by(proyecto_id=proyecto.id).distinct().all() if p[0]]
    
    return render_template("buscador_semantico.html", 
                         publicaciones=publicaciones, 
                         paises=paises)


@app.route("/api/buscar_semantico")
@login_required
def api_buscar_semantico():
    global vectorizer, tfidf_matrix, noticias_indices
    
    proyecto = get_proyecto_activo()
    if not proyecto:
        return jsonify({"error": "No hay proyecto activo. Selecciona un proyecto primero."}), 400
    
    query = request.args.get("q", "").strip()

    # Si no hay consulta, devolvemos vacío
    if not query:
        return jsonify([])
    
    # Parámetros de IA
    usar_ia = request.args.get("usar_ia", "0") == "1"
    modelo_ia = request.args.get("modelo_ia", "gemini-1.5-flash")
    temperatura = float(request.args.get("temperatura", "0.3"))
    limite = int(request.args.get("limite", "50"))
    
    # Obtener parámetros de filtro
    publicacion_id = request.args.get("publicacion_id")
    pais = request.args.get("pais")
    fecha_desde = request.args.get("fecha_desde")
    fecha_hasta = request.args.get("fecha_hasta")

    # ========================================================================
    # MODO DEEP LEARNING: Búsqueda por Embeddings Semánticos
    # ========================================================================
    if usar_ia:
        try:
            from services.embedding_service import EmbeddingService
            
            # Usar siempre el modelo de embeddings disponible en la BD (google)
            # El modelo_ia seleccionado es para generación de texto, no afecta embeddings
            embedding_model = 'google'  # Todos los embeddings están con Google Gemini
            
            embedding_service = EmbeddingService(user=current_user, default_model=embedding_model)
            
            # Generar embedding del query
            print(f"[EMBEDDING] Generando embedding para query: '{query}' con modelo {embedding_model}")
            query_embedding = embedding_service.generate_query_embedding(query, model=embedding_model)
            
            if not query_embedding:
                raise Exception("No se pudo generar el embedding del query")
            
            # Buscar documentos con embeddings en la base de datos
            query_db = db.session.query(Prensa).filter(
                Prensa.incluido == True,
                Prensa.proyecto_id == proyecto.id,
                Prensa.embedding_vector.isnot(None)  # Solo documentos con embeddings
            )
            
            # Aplicar filtros adicionales
            if publicacion_id:
                query_db = query_db.filter(Prensa.id_publicacion == publicacion_id)
            if pais:
                query_db = query_db.filter(Prensa.pais_publicacion == pais)
            params_date = {}
            if fecha_desde:
                query_db = query_db.filter(text(f"({SQL_PRENSA_DATE}) >= :f_desde"))
                params_date['f_desde'] = fecha_desde
            if fecha_hasta:
                query_db = query_db.filter(text(f"({SQL_PRENSA_DATE}) <= :f_hasta"))
                params_date['f_hasta'] = fecha_hasta
            
            if params_date:
                query_db = query_db.params(**params_date)
            
            # Obtener todos los documentos candidatos
            documentos = query_db.limit(2000).all()  # Límite razonable para cálculo
            
            if not documentos:
                return jsonify([])
            
            print(f"[EMBEDDING] Calculando similitud para {len(documentos)} documentos")
            
            # Calcular similitudes
            doc_embeddings = [doc.embedding_vector for doc in documentos]
            similitudes = embedding_service.batch_cosine_similarity(query_embedding, doc_embeddings)
            
            # Combinar documentos con sus scores
            doc_scores = list(zip(documentos, similitudes))
            
            # Ordenar por similitud descendente
            doc_scores.sort(key=lambda x: x[1], reverse=True)
            
            # Tomar top resultados
            doc_scores = doc_scores[:limite]
            
            # Construir respuesta
            res = []
            for doc, score in doc_scores:
                if score < 0.5:  # Umbral mínimo de similitud semántica
                    continue
                
                fragmento = extraer_fragmento_inteligente(
                    doc.contenido, query, max_chars=300
                )
                
                res.append({
                    "id": doc.id,
                    "titulo": doc.titulo or "Sin título",
                    "fecha": formatear_fecha_para_ui(doc.fecha_original),
                    "publicacion": doc.publicacion,
                    "ciudad": doc.ciudad,
                    "score": round(score * 100, 1),  # Porcentaje
                    "fragmento": fragmento,
                    "url_editar": url_for("noticias.lector") + f"?id={doc.id}",
                    "metodo": "embedding"  # Indicar que se usó embedding
                })
            
            print(f"[EMBEDDING] Resultados encontrados: {len(res)}")
            return jsonify(res)
            
        except Exception as e:
            print(f"[EMBEDDING] Error en búsqueda por embeddings: {e}")
            import traceback
            traceback.print_exc()
            # Fallback a TF-IDF si falla embeddings
            print("[EMBEDDING] Fallback a TF-IDF")
    
    # ========================================================================
    # MODO TRADICIONAL: Búsqueda TF-IDF (fallback)
    # ========================================================================
    # Si el motor no cargó, intentar inicializarlo
    if vectorizer is None:
        try:
            inicializar_buscador()
        except Exception as e:
            print(f"Error inicializando buscador: {e}")
            return jsonify({"error": "El buscador semántico no está disponible"}), 503

    # Expansión semántica con IA si está activada (solo para TF-IDF)
    query_expandida = query
    if usar_ia:
        try:
            from services.ai_service import AIService
            ai_service = AIService(current_user)
            prompt = f"""Eres un asistente que expande consultas de búsqueda para mejorar los resultados.

Consulta original: "{query}"

Genera una versión expandida que incluya:
- Sinónimos relevantes
- Términos relacionados conceptualmente
- Variaciones lingüísticas

Responde SOLO con la consulta expandida, sin explicaciones. Máximo 100 palabras."""

            respuesta = ai_service.generar_texto(
                prompt=prompt,
                model=modelo_ia,
                temperature=temperatura,
                max_tokens=150
            )
            query_expandida = respuesta.strip()
            print(f"[IA] Query expandida: {query_expandida}")
        except Exception as e:
            print(f"[IA] Error expandiendo query: {e}")
            # Continuar con la query original si falla

    try:
        # 1. Convertimos la pregunta del usuario en números (vector)
        # Si hay expansión IA, usamos la query expandida, sino la original
        query_busqueda = query_expandida if usar_ia else query
        q_vec = vectorizer.transform([query_busqueda])

        # 2. Calculamos similitud matemática (Coseno)
        similitudes = cosine_similarity(q_vec, tfidf_matrix).flatten()

        # 3. Ordenamos los resultados de mejor a peor
        # Usar el límite del frontend
        indices_ordenados = similitudes.argsort()[::-1][:min(limite * 10, 1000)]  # Candidatos para filtrar

        # Debug logging
        print(f"[BUSCAR_SEMANTICO] Query: '{query}', Proyecto ID: {proyecto.id}")
        if usar_ia:
            print(f"[BUSCAR_SEMANTICO] Query expandida: '{query_expandida}'")
        print(f"[BUSCAR_SEMANTICO] Top score: {similitudes[indices_ordenados[0]]:.4f}")

        # Obtener parámetros de filtro
        publicacion_id = request.args.get("publicacion_id")
        pais = request.args.get("pais")
        fecha_desde = request.args.get("fecha_desde")
        fecha_hasta = request.args.get("fecha_hasta")

        res = []
        candidatos_revisados = 0
        for idx in indices_ordenados:
            score = similitudes[idx]
            if score < 0.01:  # Umbral ajustado: 1% es suficiente para TF-IDF
                break

            nid = noticias_indices[idx]
            n = db.session.get(Prensa, nid)
            candidatos_revisados += 1

            # FILTRAR POR PROYECTO
            if n and n.proyecto_id == proyecto.id:
                # Aplicar filtros adicionales
                if publicacion_id and str(n.publicacion_id) != publicacion_id:
                    continue
                if pais and n.pais_publicacion != pais:
                    continue
                
                # Filtro de fecha
                if n.fecha_original:
                    try:
                        dt_n = parse_fecha_rigurosa(n.fecha_original)
                        if dt_n:
                            dt_n = dt_n.date()
                            if fecha_desde:
                                d = datetime.strptime(fecha_desde, "%Y-%m-%d").date()
                                if dt_n < d: continue
                            if fecha_hasta:
                                h = datetime.strptime(fecha_hasta, "%Y-%m-%d").date()
                                if dt_n > h: continue
                    except Exception as e:
                        print(f"Error parseando fecha: {e}")
                        pass
                elif fecha_desde or fecha_hasta:
                    # Si hay filtro de fecha pero la noticia no tiene fecha, la saltamos?
                    # Opcionalmente permitir. Por ahora saltamos si no cumple.
                    continue

                if len(res) >= limite: # Limitar según el parámetro del frontend
                    break
                # Extracción inteligente de fragmento
                fragmento = extraer_fragmento_inteligente(
                    n.contenido, query, max_chars=300
                )

                # Boost si la query aparece en el título
                score_boost = 1.0
                if normalizar_texto(query) in normalizar_texto(n.titulo or ""):
                    score_boost = 1.3

                score_final = score * score_boost

                res.append(
                    {
                        "id": n.id,
                        "titulo": n.titulo or "Sin título",
                        "fecha": formatear_fecha_para_ui(n.fecha_original),
                        "publicacion": n.publicacion,
                        "ciudad": n.ciudad,
                        "score": round(score_final * 100, 1),  # Porcentaje
                        "fragmento": fragmento,
                        "url_editar": url_for("noticias.lector") + f"?id={n.id}",
                    }
                )

        # Reordenar por score final
        res.sort(key=lambda x: x["score"], reverse=True)
        # Ya no limitamos aquí, respetamos el límite aplicado antes

        print(f"[BUSCAR_SEMANTICO] Candidatos revisados: {candidatos_revisados}, Resultados encontrados: {len(res)}")
        
        return jsonify(res)

    except Exception as e:
        print(f"Error en búsqueda: {e}")
        return jsonify([])


# =========================================================
# API: obtener datos de una publicación existente
# =========================================================
@app.route("/api/publicacion_info/<nombre>")
def api_publicacion_info(nombre):
    proyecto = get_proyecto_activo()
    if not proyecto:
        return jsonify({"error": "No hay proyecto activo"}), 400

    pub = Publicacion.query.filter_by(nombre=nombre, proyecto_id=proyecto.id).first()
    if not pub:
        return jsonify({}), 404

    # Obtener hemeroteca si está vinculada
    hem = None
    nombre_hemeroteca = ""
    institucion = ""
    
    if pub.hemeroteca_id:
        hem = db.session.get(Hemeroteca, pub.hemeroteca_id)
        if hem:
            nombre_hemeroteca = hem.nombre
            institucion = hem.institucion or ""
    
    # Priorizar el campo fuente de la publicación, si no existe usar la institución de la hemeroteca
    fuente_final = pub.fuente if pub.fuente else institucion

    datos = {
        "descripcion_publicacion": pub.descripcion,
        "tipo_recurso": pub.tipo_recurso,
        "tipo_publicacion": pub.tipo_publicacion,
        "periodicidad": pub.periodicidad,
        "ciudad": pub.ciudad,
        "pais_publicacion": pub.pais_publicacion,
        "idioma": pub.idioma,
        "licencia": (pub.licencia or pub.licencia_predeterminada or "CC BY 4.0"),
        "formato_fuente": pub.formato_fuente,
        "hemeroteca_nombre": nombre_hemeroteca,
        "edicion": pub.frecuencia or "",
        "institucion": fuente_final,
        # Nuevos campos teatrales
        "actos_totales": pub.actos_totales or "",
        "escenas_totales": pub.escenas_totales or "",
        "reparto_total": pub.reparto_total or "",
        "pseudonimo": getattr(pub, 'pseudonimo', ''),
        "coleccion": getattr(pub, 'coleccion', ''),
        "autores": []
    }
    
    # Enriquecer autores con sus pseudónimos desde AutorBio
    for a in (pub.autores if hasattr(pub, 'autores') else []):
        n_clean = (a.nombre or "").strip()
        a_clean = (a.apellido or "").strip()
        
        # Búsqueda robusta en AutorBio (ignorar espacios y mayúsculas)
        bio = AutorBio.query.filter(
            func.trim(AutorBio.nombre).ilike(n_clean),
            func.trim(AutorBio.apellido).ilike(a_clean),
            AutorBio.proyecto_id == proyecto.id
        ).first()
        
        datos["autores"].append({
            "nombre": a.nombre,
            "apellido": a.apellido,
            "tipo": a.tipo,
            "es_anonimo": a.es_anonimo,
            "pseudonimo": bio.seudonimo if bio else ""
        })
        
    return jsonify(datos)

# =========================================================
# API: Obtener siguiente número de referencia disponible
# =========================================================
@app.route("/api/siguiente_numero_referencia")
def api_siguiente_numero_referencia():
    """Devuelve el siguiente número de referencia bibliográfica disponible"""
    proyecto = get_proyecto_activo()
    if not proyecto:
        return jsonify({"error": "No hay proyecto activo"}), 400
    
    # Obtener el máximo número de referencia actual del modelo Prensa
    max_numero_query = db.session.query(func.max(Prensa.numero_referencia))\
        .filter(Prensa.proyecto_id == proyecto.id)\
        .filter(Prensa.es_referencia == True)\
        .scalar()
    
    max_numero = max_numero_query if max_numero_query is not None else 0
    
    total_referencias = db.session.query(Prensa).filter(
        Prensa.proyecto_id == proyecto.id, Prensa.es_referencia == True
    ).count()

    siguiente_numero = max_numero + 1

    return jsonify({
        "siguiente_numero": siguiente_numero,
        "total_referencias": total_referencias,
        "status": "success"
    })

# =========================================================
# API: Autocompletar inteligente con sugerencias
# =========================================================
@app.route("/api/autocomplete/<field>")
def api_autocomplete(field):
    """Devuelve sugerencias para autocompletar basadas en registros previos"""
    proyecto = get_proyecto_activo()
    if not proyecto:
        return jsonify([]), 200

    query = request.args.get("q", "").lower()
    limit = int(request.args.get("limit", 10))

    if field == "publicacion":
        # Obtener publicaciones únicas ordenadas por frecuencia de uso
        results = (
            db.session.query(Prensa.publicacion, func.count(Prensa.id).label("count"))
            .filter(Prensa.proyecto_id == proyecto.id)
            .filter(Prensa.publicacion.isnot(None), Prensa.publicacion != "")
            .group_by(Prensa.publicacion)
            .order_by(func.count(Prensa.id).desc())
            .limit(limit)
            .all()
        )

        suggestions = [
            {"value": r.publicacion, "count": r.count}
            for r in results
            if query in r.publicacion.lower()
        ]

    elif field == "ciudad":
        results = (
            db.session.query(Prensa.ciudad, func.count(Prensa.id).label("count"))
            .filter(Prensa.proyecto_id == proyecto.id)
            .filter(Prensa.ciudad.isnot(None), Prensa.ciudad != "")
            .group_by(Prensa.ciudad)
            .order_by(func.count(Prensa.id).desc())
            .limit(limit)
            .all()
        )

        suggestions = [
            {"value": r.ciudad, "count": r.count}
            for r in results
            if query in r.ciudad.lower()
        ]

    elif field == "autor":
        results = (
            db.session.query(Prensa.autor, func.count(Prensa.id).label("count"))
            .filter(Prensa.proyecto_id == proyecto.id)
            .filter(
                Prensa.autor.isnot(None), Prensa.autor != "", Prensa.autor != "Anónimo"
            )
            .group_by(Prensa.autor)
            .order_by(func.count(Prensa.id).desc())
            .limit(limit)
            .all()
        )

        suggestions = [
            {"value": r.autor, "count": r.count}
            for r in results
            if query in r.autor.lower()
        ]

    elif field == "autores_bio":
        # Búsqueda en la base de datos central de autores (AutorBio)
        raw_results = (
            db.session.query(AutorBio)
            .filter(
                or_(
                    AutorBio.nombre.ilike(f"%{query}%"),
                    AutorBio.apellido.ilike(f"%{query}%"),
                    AutorBio.seudonimo.ilike(f"%{query}%")
                )
            )
            .all()
        )
        
        processed = {}
        target_project_id = str(proyecto.id) if proyecto else "NONE"
        
        for r in raw_results:
            nombre_norm = (r.nombre or "").strip().lower()
            apellido_norm = (r.apellido or "").strip().lower()
            key = (nombre_norm, apellido_norm)
            
            r_project_id = str(r.proyecto_id) if r.proyecto_id else "NONE"
            
            # Lógica de prioridad:
            if key not in processed:
                processed[key] = r
            else:
                existing = processed[key]
                ex_project_id = str(existing.proyecto_id) if existing.proyecto_id else "NONE"
                
                # Prioridad 1: Mi proyecto actual
                if r_project_id == target_project_id:
                    processed[key] = r
                # Prioridad 2: Global (si el que hay es de otro proyecto)
                elif r_project_id == "NONE" and ex_project_id != target_project_id:
                    processed[key] = r
        
        suggestions = []
        final_list = sorted(processed.values(), key=lambda x: (x.apellido or "").lower())
        
        for r in final_list[:limit]:
            r_pid = str(r.proyecto_id) if r.proyecto_id else "NONE"
            if r_pid == target_project_id:
                label = "Este proyecto"
            elif r_pid == "NONE":
                label = "Global"
            else:
                label = "Repositorio"
            
            suggestions.append({
                "value": f"{r.apellido}, {r.nombre}" if r.apellido else r.nombre,
                "nombre": r.nombre,
                "apellido": r.apellido,
                "pseudonimo": r.seudonimo,
                "origen": label
            })

    elif field == "temas":
        # Obtener todos los temas, separar por comas y contar
        all_temas = (
            db.session.query(Prensa.temas)
            .filter(Prensa.proyecto_id == proyecto.id)
            .filter(Prensa.temas.isnot(None), Prensa.temas != "")
            .all()
        )

        tema_count = Counter()
        for (temas_str,) in all_temas:
            for tema in temas_str.split(","):
                tema = tema.strip()
                if tema:
                    tema_count[tema] += 1

        suggestions = [
            {"value": tema, "count": count}
            for tema, count in tema_count.most_common(limit)
            if query in tema.lower()
        ]
    else:
        suggestions = []

    return jsonify(suggestions)


# =========================================================



# API: Obtener último registro creado
# =========================================================
@app.route("/api/ultimo_registro")
def api_ultimo_registro():
    """Devuelve los datos del último registro creado para facilitar duplicación"""
    proyecto = get_proyecto_activo()
    if not proyecto:
        return jsonify({}), 404

    ultimo = Prensa.query.filter_by(proyecto_id=proyecto.id).order_by(Prensa.id.desc()).first()

    if not ultimo:
        return jsonify({}), 404

    # Devolver solo campos reutilizables (no título ni contenido)
    datos = {
        "publicacion": ultimo.publicacion or "",
        "ciudad": ultimo.ciudad or "",
        "pais_publicacion": ultimo.pais_publicacion or "",
        "idioma": ultimo.idioma or "",
        "tipo_recurso": ultimo.tipo_recurso or "prensa",
        "fuente": ultimo.fuente or "",
        "formato_fuente": ultimo.formato_fuente or "",
        "licencia": ultimo.licencia or "CC BY 4.0",
        "edicion": ultimo.edicion or "",
        "anio": ultimo.anio or "",
    }

    return jsonify(datos)


# =========================================================
# RUTA PARA VER IMÁGENES ASOCIADAS A UNA NOTICIA
# =========================================================
@app.route("/ver_imagenes_prensa/<int:id>")
def ver_imagenes_prensa(id):
    ref = db.session.get(Prensa, id)
    if not ref:
        return abort(404)
    imagenes = ref.imagenes.order_by(ImagenPrensa.fecha_subida.asc()).all()
    return render_template("ver_imagenes_prensa.html", ref=ref, imagenes=imagenes)


# =========================================================
# 📰 GESTIÓN DE PUBLICACIONES (MEDIOS MAESTROS)
# =========================================================
# @app.route("/publicaciones")
# def lista_publicaciones():
#     proyecto = get_proyecto_activo()
#     if not proyecto:
#         return redirect(url_for("listar_proyectos"))
# 
#     # 1. Recoger el parámetro de la URL (si existe)
#     hemeroteca_id = request.args.get('hemeroteca_id')
#     filtro_nombre = None
# 
#     # 2. Construir la consulta base filtrada por proyecto
#     query = Publicacion.query.filter_by(proyecto_id=proyecto.id)
# 
#     # 3. Aplicar filtro de hemeroteca si viene el ID
#     if hemeroteca_id:
#         try:
#             # Aseguramos que sea un entero para evitar errores
#             hemeroteca_id = int(hemeroteca_id)
#             query = query.filter_by(hemeroteca_id=hemeroteca_id)
#             
#             # Buscamos el nombre de la hemeroteca para mostrarlo en el título
#             hemeroteca = db.session.get(Hemeroteca, hemeroteca_id)
#             if hemeroteca:
#                 filtro_nombre = hemeroteca.nombre
#         except (ValueError, TypeError):
#             # Si el ID no es un número válido, ignoramos el filtro
#             pass
# 
#     # 4. Ejecutar consulta con ordenación
#     pubs = query.order_by(Publicacion.nombre.asc()).all()
# 
#     # Calcular estadísticas rápidas (de los resultados visibles)
#     total_medios = len(pubs)
#     total_noticias_vinculadas = sum(len(p.articulos) for p in pubs)
# 
#     return render_template(
#         "publicaciones.html",
#         publicaciones=pubs,
#         total_medios=total_medios,
#         total_noticias=total_noticias_vinculadas,
#         filtro_activo=filtro_nombre,       # Pasamos el nombre para el aviso visual
#         hemeroteca_id_activo=hemeroteca_id # Pasamos el ID por si hiciera falta
#     )


# @app.route("/api/publicacion/<int:id>")
# def api_publicacion_get(id):
#     pub = db.session.get(Publicacion, id)
#     if not pub:
#         return jsonify({"error": "no encontrado"}), 404
#     return jsonify(
#         {
#             "id_publicacion": pub.id_publicacion,
#             "nombre": pub.nombre,
#             "ciudad": pub.ciudad,
#             "pais_publicacion": pub.pais_publicacion,
#             "fuente": pub.fuente,
#             "formato_fuente": pub.formato_fuente,
#             "descripcion": pub.descripcion,
#             "idioma": pub.idioma,
#             "licencia_predeterminada": pub.licencia_predeterminada,
#         }
#     )


# @app.route("/publicacion/editar/<int:id>", methods=["GET", "POST"])
# def editar_publicacion(id):
#     pub = db.session.get(Publicacion, id)
#     if not pub:
#         return abort(404)
# 
#     if request.method == "POST":
#         try:
#             # Asignar valores (con .strip() cuando procede)
#             nombre_val = (request.form.get("nombre") or "").strip()
#             pub.nombre = nombre_val or pub.nombre
# 
#             # Sanear y asignar campos evitando guardar literales como 'None' o 'null'
#             def _sanear(v):
#                 if v is None:
#                     return None
#                 s = str(v).strip()
#                 if s == "" or s.lower() in ("none", "null"):
#                     return None
#                 return s
# 
#             pub.ciudad = _sanear(request.form.get("ciudad"))
#             pub.pais_publicacion = _sanear(request.form.get("pais"))
#             pub.descripcion = _sanear(request.form.get("descripcion"))
#             pub.idioma = _sanear(request.form.get("idioma"))
#             pub.licencia_predeterminada = _sanear(request.form.get("licencia"))
#             # Fuente y formato
#             pub.fuente = _sanear(request.form.get("fuente"))
#             pub.formato_fuente = _sanear(request.form.get("formato_fuente"))
# 
#             # ⬇️⬇️ NUEVO: guardar la hemeroteca seleccionada ⬇️⬇️
#             h_id = request.form.get("hemeroteca_id")
#             try:
#                 pub.hemeroteca_id = int(h_id) if h_id and h_id.strip() else None
#             except ValueError:
#                 pub.hemeroteca_id = None
#             # ⬆️⬆️ FIN BLOQUE NUEVO ⬆️⬆️
# 
#             app.logger.info(
#                 f"Actualizando Publicacion id={id} with data: {dict(request.form)}"
#             )
#             db.session.commit()
#             # Refrescar para asegurar datos sincronizados
#             db.session.refresh(pub)
# 
#             # Si el usuario pidió propagar cambios a las noticias vinculadas, actualizarlas
#             if "propagar" in request.form:
#                 try:
#                     payload_prensa = {}
#                     if pub.ciudad is not None:
#                         payload_prensa[Prensa.ciudad] = pub.ciudad
#                     if pub.pais_publicacion is not None:
#                         payload_prensa[Prensa.pais_publicacion] = pub.pais_publicacion
#                     if pub.fuente is not None:
#                         payload_prensa[Prensa.fuente] = pub.fuente
#                     if pub.formato_fuente is not None:
#                         payload_prensa[Prensa.formato_fuente] = pub.formato_fuente
#                     if pub.idioma is not None:
#                         payload_prensa[Prensa.idioma] = pub.idioma
#                     if pub.licencia_predeterminada is not None:
#                         payload_prensa[Prensa.licencia] = pub.licencia_predeterminada
# 
#                     if payload_prensa:
#                         app.logger.info(
#                             f"Propagando a noticias vinculadas (por fila): "
#                             f"{ {str(k): v for k, v in payload_prensa.items()} }"
#                         )
#                         # Seleccionar noticias vinculadas por id_publicacion o por nombre de publicación
#                         noticias = Prensa.query.filter(
#                             or_(
#                                 Prensa.id_publicacion == id,
#                                 Prensa.publicacion == pub.nombre,
#                             )
#                         ).all()
#                         cuenta = 0
#                         for noticia in noticias:
#                             for attr, val in payload_prensa.items():
#                                 try:
#                                     nombre_attr = attr.key
#                                 except Exception:
#                                     nombre_attr = getattr(attr, "name", None) or str(
#                                         attr
#                                     )
#                                 if nombre_attr and val is not None:
#                                     setattr(noticia, nombre_attr, val)
#                             # Vincular explícitamente la noticia a la publicación
#                             try:
#                                 noticia.id_publicacion = pub.id_publicacion
#                                 noticia.publicacion = pub.nombre
#                             except Exception:
#                                 pass
#                             cuenta += 1
#                         db.session.commit()
#                         db.session.expire_all()
#                         app.logger.info(
#                             f"Actualizadas {cuenta} noticias vinculadas para publicacion id={id} (por fila)"
#                         )
#                         flash(f"✅ Actualizadas {cuenta} noticias vinculadas.", "info")
#                 except Exception as e:
#                     db.session.rollback()
#                     app.logger.exception(
#                         f"Error propagando cambios a noticias vinculadas para publicacion id={id}: {e}"
#                     )
#                     flash(
#                         f"⚠️ No se pudieron propagar todos los cambios a las noticias vinculadas: {str(e)}",
#                         "warning",
#                     )
# 
#             flash("✅ Datos del medio actualizados.", "success")
#             return redirect(url_for("hemerotecas.lista_publicaciones"))
# 
#         except Exception as e:
#             db.session.rollback()
#             app.logger.exception(f"Error guardando Publicacion id={id}: {e}")
#             flash(f"❌ Error al guardar: {str(e)}", "danger")
#             # continuar y re-renderizar el formulario con los valores actuales
# 
#     proyecto = get_proyecto_activo()
#     if proyecto:
#         hemerotecas = (
#             Hemeroteca.query.filter_by(proyecto_id=proyecto.id)
#             .order_by(Hemeroteca.nombre)
#             .all()
#         )
#     else:
#         hemerotecas = Hemeroteca.query.order_by(Hemeroteca.nombre).all()
# 
#     return render_template("editar_publicacion.html", pub=pub, hemerotecas=hemerotecas)

#     @app.route("/publicacion/editar/<int:id>", methods=["GET", "POST"])
#     def editar_publicacion(id):
#         pub = db.session.get(Publicacion, id)
#         if not pub:
#             return abort(404)
# 
#         if request.method == "POST":
#             try:
#                 # Asignar valores (con .strip() cuando procede)
#                 nombre_val = (request.form.get("nombre") or "").strip()
#                 pub.nombre = nombre_val or pub.nombre
# 
#                 # Sanear y asignar campos evitando guardar literales como 'None' o 'null'
#                 def _sanear(v):
#                     if v is None:
#                         return None
#                     s = str(v).strip()
#                     if s == "" or s.lower() in ("none", "null"):
#                         return None
#                     return s
# 
#                 pub.ciudad = _sanear(request.form.get("ciudad"))
#                 pub.pais_publicacion = _sanear(request.form.get("pais"))
#                 pub.descripcion = _sanear(request.form.get("descripcion"))
#                 pub.idioma = _sanear(request.form.get("idioma"))
#                 pub.licencia_predeterminada = _sanear(request.form.get("licencia"))
#                 # Fuente y formato
#                 pub.fuente = _sanear(request.form.get("fuente"))
#                 pub.formato_fuente = _sanear(request.form.get("formato_fuente"))
# 
#                 # ⬇️⬇️ NUEVO: guardar la hemeroteca seleccionada ⬇️⬇️
#                 h_id = request.form.get("hemeroteca_id")
#                 try:
#                     pub.hemeroteca_id = int(h_id) if h_id and h_id.strip() else None
#                 except ValueError:
#                     pub.hemeroteca_id = None
#                 # ⬆️⬆️ FIN BLOQUE NUEVO ⬆️⬆️
# 
#                 app.logger.info(
#                     f"Actualizando Publicacion id={id} with data: {dict(request.form)}"
#                 )
#                 db.session.commit()
#                 # Refrescar para asegurar datos sincronizados
#                 db.session.refresh(pub)
# 
#                 # Si el usuario pidió propagar cambios a las noticias vinculadas, actualizarlas
#                 if "propagar" in request.form:
#                     try:
#                         payload_prensa = {}
#                         if pub.ciudad is not None:
#                             payload_prensa[Prensa.ciudad] = pub.ciudad
#                         if pub.pais_publicacion is not None:
#                             payload_prensa[Prensa.pais_publicacion] = (
#                                 pub.pais_publicacion
#                             )
#                         if pub.fuente is not None:
#                             payload_prensa[Prensa.fuente] = pub.fuente
#                         if pub.formato_fuente is not None:
#                             payload_prensa[Prensa.formato_fuente] = pub.formato_fuente
#                         if pub.idioma is not None:
#                             payload_prensa[Prensa.idioma] = pub.idioma
#                         if pub.licencia_predeterminada is not None:
#                             payload_prensa[Prensa.licencia] = (
#                                 pub.licencia_predeterminada
#                             )
# 
#                         if payload_prensa:
#                             app.logger.info(
#                                 f"Propagando a noticias vinculadas (por fila): "
#                                 f"{ {str(k): v for k, v in payload_prensa.items()} }"
#                             )
#                             # Seleccionar noticias vinculadas por id_publicacion o por nombre de publicación
#                             noticias = Prensa.query.filter(
#                                 or_(
#                                     Prensa.id_publicacion == id,
#                                     Prensa.publicacion == pub.nombre,
#                                 )
#                             ).all()
#                             cuenta = 0
#                             for noticia in noticias:
#                                 for attr, val in payload_prensa.items():
#                                     try:
#                                         nombre_attr = attr.key
#                                     except Exception:
#                                         nombre_attr = getattr(
#                                             attr, "name", None
#                                         ) or str(attr)
#                                     if nombre_attr and val is not None:
#                                         setattr(noticia, nombre_attr, val)
#                                 # Vincular explícitamente la noticia a la publicación
#                                 try:
#                                     noticia.id_publicacion = pub.id_publicacion
#                                     noticia.publicacion = pub.nombre
#                                 except Exception:
#                                     pass
#                                 cuenta += 1
#                             db.session.commit()
#                             db.session.expire_all()
#                             app.logger.info(
#                                 f"Actualizadas {cuenta} noticias vinculadas for publicacion id={id} (por fila)"
#                             )
#                             flash(
#                                 f"✅ Actualizadas {cuenta} noticias vinculadas.", "info"
#                             )
#                     except Exception as e:
#                         db.session.rollback()
#                         app.logger.exception(
#                             f"Error propagando cambios a noticias vinculadas for publicacion id={id}: {e}"
#                         )
#                         flash(
#                             f"⚠️ No se pudieron propagar todos los cambios a las noticias vinculadas: {str(e)}",
#                             "warning",
#                         )
# 
#                 flash("✅ Datos del medio actualizados.", "success")
#                 return redirect(url_for("hemerotecas.lista_publicaciones"))
# 
#             except Exception as e:
#                 db.session.rollback()
#                 app.logger.exception(f"Error guardando Publicacion id={id}: {e}")
#                 flash(f"❌ Error al guardar: {str(e)}", "danger")
#                 # continuar y re-renderizar el formulario con los valores actuales
# 
#         proyecto = get_proyecto_activo()
#         if proyecto:
#             hemerotecas = (
#                 Hemeroteca.query.filter_by(proyecto_id=proyecto.id)
#                 .order_by(Hemeroteca.nombre)
#                 .all()
#             )
#         else:
#             hemerotecas = Hemeroteca.query.order_by(Hemeroteca.nombre).all()
# 
#         return render_template(
#             "editar_publicacion.html", pub=pub, hemerotecas=hemerotecas
#         )


# [NUEVO] CREAR NUEVA PUBLICACIÓN
# @app.route("/publicacion/nueva", methods=["GET", "POST"])
# def nueva_publicacion():
#     if request.method == "POST":
#         nombre = request.form.get("nombre").strip()
# 
#         # Evitar duplicados
#         proyecto = get_proyecto_activo()
#         if proyecto and Publicacion.query.filter_by(nombre=nombre, proyecto_id=proyecto.id).first():
#             flash(f"⚠️ El medio '{nombre}' ya existe.", "warning")
#             return redirect(url_for("hemerotecas.nueva_publicacion"))
# 
#         hemeroteca_id = request.form.get("hemeroteca_id")
#         nueva = Publicacion(
#             proyecto_id=get_proyecto_activo().id,
#             nombre=nombre,
#             ciudad=request.form.get("ciudad"),
#             pais_publicacion=request.form.get("pais"),
#             descripcion=request.form.get("descripcion"),
#             idioma=request.form.get("idioma"),
#             licencia_predeterminada=request.form.get("licencia"),
#             fuente=request.form.get("fuente"),
#             formato_fuente=request.form.get("formato_fuente"),
#             hemeroteca_id=int(hemeroteca_id)
#             if hemeroteca_id and hemeroteca_id.strip()
#             else None,
#         )
#         db.session.add(nueva)
#         db.session.commit()
#         # Después de crear la publicación, asociar y propagar a noticias que ya referencian ese nombre
#         try:
#             pub_id = nueva.id_publicacion
#             payload_prensa = {}
#             if nueva.ciudad:
#                 payload_prensa[Prensa.ciudad] = nueva.ciudad
#             if nueva.pais_publicacion:
#                 payload_prensa[Prensa.pais_publicacion] = nueva.pais_publicacion
#             if nueva.fuente:
#                 payload_prensa[Prensa.fuente] = nueva.fuente
#             if nueva.formato_fuente:
#                 payload_prensa[Prensa.formato_fuente] = nueva.formato_fuente
#             if nueva.idioma:
#                 payload_prensa[Prensa.idioma] = nueva.idioma
#             if nueva.licencia_predeterminada:
#                 payload_prensa[Prensa.licencia] = nueva.licencia_predeterminada
# 
#             # Buscar noticias cuyo texto 'publicacion' coincida con el nombre
#             noticias = Prensa.query.filter(Prensa.publicacion == nombre).all()
#             cuenta = 0
#             for noticia in noticias:
#                 # Establecer id_publicacion y actualizar campos
#                 noticia.id_publicacion = pub_id
#                 noticia.publicacion = nombre
#                 for attr, val in payload_prensa.items():
#                     try:
#                         key = attr.key
#                     except Exception:
#                         key = getattr(attr, "name", None) or str(attr)
#                     if key and val is not None:
#                         setattr(noticia, key, val)
#                 cuenta += 1
#             if cuenta:
#                 db.session.commit()
#                 db.session.expire_all()
#                 flash(
#                     f"✅ Medio '{nombre}' creado con éxito. Asociadas y actualizadas {cuenta} noticias existentes.",
#                     "success",
#                 )
#             else:
#                 flash(f"✅ Medio '{nombre}' creado con éxito.", "success")
#         except Exception as e:
#             db.session.rollback()
#             app.logger.exception(
#                 f"Error propagando creación de publicacion '{nombre}': {e}"
#             )
#             flash(
#                 f"✅ Medio '{nombre}' creado, pero no se pudieron asociar noticias existentes: {str(e)}",
#                 "warning",
#             )
#         return redirect(url_for("lista_publicaciones"))
# 
#     proyecto = get_proyecto_activo()
#     if proyecto:
#         hemerotecas = (
#             Hemeroteca.query.filter_by(proyecto_id=proyecto.id)
#             .order_by(Hemeroteca.nombre)
#             .all()
#         )
#     else:
#         hemerotecas = Hemeroteca.query.order_by(Hemeroteca.nombre).all()
# 
#     return render_template("nueva_publicacion.html", hemerotecas=hemerotecas)


# [NUEVO] BORRAR PUBLICACIÓN
# @app.route("/publicacion/borrar/<int:id>")
# def borrar_publicacion(id):
#     pub = db.session.get(Publicacion, id)
#     if pub:
#         # Paso de seguridad: Desvincular noticias antes de borrar
#         # para que no se borren las noticias en cascada (o den error)
#         noticias_afectadas = Prensa.query.filter_by(id_publicacion=id).all()
#         for n in noticias_afectadas:
#             n.id_publicacion = None  # Las dejamos "huerfanas" pero vivas
# 
#         nombre = pub.nombre
#         db.session.delete(pub)
#         db.session.commit()
#         flash(
#             f"🗑️ Medio '{nombre}' eliminado. {len(noticias_afectadas)} noticias desvinculadas.",
#             "success",
#         )
#     return redirect(url_for("hemerotecas.lista_publicaciones"))


# =========================================================
# RUTAS - GESTIÓN DE HEMEROTECAS
# =========================================================


# @app.route("/hemerotecas")
# def lista_hemerotecas():
#     """Listado de hemerotecas con filtrado por proyecto"""
#     proyecto_actual = get_proyecto_activo()
# 
#     if proyecto_actual:
#         hemerotecas = (
#             Hemeroteca.query.filter_by(proyecto_id=proyecto_actual.id)
#             .order_by(Hemeroteca.pais, Hemeroteca.nombre)
#             .all()
#         )
#     else:
#         hemerotecas = Hemeroteca.query.order_by(
#             Hemeroteca.pais, Hemeroteca.nombre
#         ).all()
# 
#     # Contar publicaciones por hemeroteca
#     stats = {}
#     for h in hemerotecas:
#         stats[h.id] = Publicacion.query.filter_by(hemeroteca_id=h.id).count()
# 
#     return render_template(
#         "hemerotecas.html",
#         hemerotecas=hemerotecas,
#         stats=stats,
#         total_hemerotecas=len(hemerotecas),
#     )


# @app.route("/hemeroteca/nueva", methods=["GET", "POST"])
# def nueva_hemeroteca():
#     """Crear nueva hemeroteca"""
#     proyecto_actual = get_proyecto_activo()
# 
#     if request.method == "POST":
#         nombre = request.form.get("nombre", "").strip()
#         pais = request.form.get("pais", "").strip()
#         provincia = request.form.get("provincia", "").strip()
#         ciudad = request.form.get("ciudad", "").strip()
#         institucion = request.form.get("institucion", "").strip()
#         resumen_corpus = request.form.get("resumen_corpus", "").strip()
#         url = request.form.get("url", "").strip()
# 


# @app.route("/hemeroteca/borrar/<int:id>")
# def borrar_hemeroteca(id):
#     """Eliminar hemeroteca (desvincula publicaciones)"""
#     hemeroteca = db.session.get(Hemeroteca, id)
#     if hemeroteca:
#         # Desvincular publicaciones
#         publicaciones_afectadas = Publicacion.query.filter_by(hemeroteca_id=id).all()
#         for pub in publicaciones_afectadas:
#             pub.hemeroteca_id = None
# 
#         nombre = hemeroteca.nombre
#         db.session.delete(hemeroteca)
#         db.session.commit()
#         flash(
#             f'🗑️ Hemeroteca "{nombre}" eliminada. {len(publicaciones_afectadas)} publicaciones desvinculadas.',
#             "success",
#         )
# 
#     return redirect(url_for("hemerotecas.hemerotecas"))


# @app.route("/hemeroteca/migrar/<int:id>", methods=["GET", "POST"])
# def migrar_hemeroteca(id):
#     """Migrar hemeroteca a otro proyecto"""
#     hemeroteca = db.session.get(Hemeroteca, id)
#     if not hemeroteca:
#         flash("❌ Hemeroteca no encontrada", "danger")
#         return redirect(url_for("hemerotecas.hemerotecas"))
# 
#     # Obtener todos los proyectos excepto el actual
#     proyectos_disponibles = (
#         Proyecto.query.filter(Proyecto.id != hemeroteca.proyecto_id)
#         .order_by(Proyecto.nombre)
#         .all()
#     )
# 
#     if request.method == "POST":
#         nuevo_proyecto_id = request.form.get("proyecto_id")
# 
#         if not nuevo_proyecto_id:
#             flash("❌ Debes seleccionar un proyecto destino", "danger")
#             return render_template(
#                 "migrar_hemeroteca.html",
#                 hemeroteca=hemeroteca,
#                 proyectos=proyectos_disponibles,
#             )
# 
#         try:
#             proyecto_destino = db.session.get(Proyecto, int(nuevo_proyecto_id))
#             proyecto_origen = (
#                 db.session.get(Proyecto, hemeroteca.proyecto_id)
#                 if hemeroteca.proyecto_id
#                 else None
#             )
# 
#             # Contar publicaciones afectadas
#             publicaciones_afectadas = Publicacion.query.filter_by(
#                 hemeroteca_id=id
#             ).count()
# 
#             # Migrar hemeroteca
#             hemeroteca.proyecto_id = int(nuevo_proyecto_id)
#             db.session.commit()
# 
#             flash(
#                 f'✅ Hemeroteca "{hemeroteca.nombre}" migrada a proyecto "{proyecto_destino.nombre}". {publicaciones_afectadas} publicaciones vinculadas se mantienen.',
#                 "success",
#             )
#             return redirect(url_for("hemerotecas.hemerotecas"))
# 
#         except Exception as e:
#             db.session.rollback()
#             flash(f"❌ Error al migrar hemeroteca: {str(e)}", "danger")
#             app.logger.exception(f"Error migrando hemeroteca: {e}")
# 
#     return render_template(
#         "migrar_hemeroteca.html", hemeroteca=hemeroteca, proyectos=proyectos_disponibles
#     )


# =========================================================
# API ENDPOINTS - GESTIÓN DE REFERENCIAS BIBLIOGRÁFICAS
# =========================================================

@app.route("/api/validar_numero_referencia")
def api_validar_numero_referencia():
    """Valida si un número de referencia ya está en uso"""
    proyecto = get_proyecto_activo()
    if not proyecto:
        return jsonify({"en_uso": False})

    try:
        numero = request.args.get("numero", type=int)
        exclude_id = request.args.get("exclude_id", type=int)

        if not numero:
            return jsonify({"en_uso": False})

        # Buscar si el número ya existe en el proyecto activo
        query = db.session.query(Prensa).filter(
            Prensa.proyecto_id == proyecto.id,
            Prensa.numero_referencia == numero,
            db.or_(Prensa.es_referencia == True, Prensa.numero_referencia.isnot(None))
        )

        # Excluir el registro actual en caso de edición
        if exclude_id:
            query = query.filter(Prensa.id != exclude_id)

        registro = query.first()

        if registro:
            return jsonify(
                {
                    "en_uso": True,
                    "id": registro.id,
                    "titulo": registro.titulo or "(Sin título)",
                    "publicacion": registro.publicacion or "",
                    "fecha": registro.fecha_original or "",
                }
            )
        else:
            return jsonify({"en_uso": False})

    except Exception as e:
        app.logger.error(f"Error en api_validar_numero_referencia: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/referencias_por_numero/<int:numero>")
def api_referencias_por_numero(numero):
    """Obtiene todas las referencias que usan un número bibliográfico específico"""
    proyecto = get_proyecto_activo()
    if not proyecto:
        return jsonify({"error": "No hay proyecto activo"}), 400

    try:
        referencias = (
            Prensa.query.filter(
                Prensa.proyecto_id == proyecto.id,
                Prensa.numero_referencia == numero
            )
            .order_by(Prensa.fecha_original.desc())
            .all()
        )

        return jsonify(
            {
                "numero": numero,
                "total": len(referencias),
                "referencias": [
                    {
                        "id": ref.id,
                        "titulo": ref.titulo or "(Sin título)",
                        "publicacion": ref.publicacion or "",
                        "fecha": ref.fecha_original or "",
                        "autor": ref.autor or "Anónimo",
                        "url": url_for("editar", id=ref.id),
                    }
                    for ref in referencias
                ],
            }
        )
    except Exception as e:
        app.logger.error(f"Error en api_referencias_por_numero: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/bibliografia/eliminar", methods=["POST"])
@csrf.exempt
def eliminar_de_bibliografia():
    """Elimina las referencias dadas de la bibliografía (resetea es_referencia y numero_referencia)"""
    proyecto = get_proyecto_activo()
    if not proyecto:
        return jsonify({"success": False, "error": "No hay proyecto activo"}), 400

    try:
        data = request.json
        ids = data.get("ids", [])
        if not ids:
            return jsonify({"success": False, "error": "No IDs provided"}), 400
        
        for ref_id in ids:
            ref = Prensa.query.get(ref_id)
            if ref and ref.proyecto_id == proyecto.id:
                ref.es_referencia = False
                ref.numero_referencia = None
        
        db.session.commit()
        return jsonify({"success": True})
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error al eliminar de bibliografía: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/bibliografia/editar", methods=["POST"])
@csrf.exempt
def editar_referencia_bibliografica():
    """Actualiza propiedades rápidas de una referencia (número y tipo)"""
    proyecto = get_proyecto_activo()
    if not proyecto:
        return jsonify({"success": False, "error": "No hay proyecto activo"}), 400

    try:
        data = request.json
        ref_id = data.get("id")
        nuevo_numero = data.get("numero_referencia")
        nuevo_tipo = data.get("tipo_recurso")
        
        if not ref_id:
            return jsonify({"success": False, "error": "ID no proporcionado"}), 400
            
        ref = Prensa.query.get(ref_id)
        if not ref or ref.proyecto_id != proyecto.id:
            return jsonify({"success": False, "error": "Referencia no encontrada"}), 404
            
        if nuevo_numero is not None and str(nuevo_numero).strip() != "":
            try:
                ref.numero_referencia = int(nuevo_numero)
            except ValueError:
                return jsonify({"success": False, "error": "Número inválido"}), 400
        else:
            ref.numero_referencia = None
            
        if nuevo_tipo is not None:
            ref.tipo_recurso = nuevo_tipo
            
        # Si se le pone número, nos aseguramos de que es_referencia = True
        if ref.numero_referencia is not None:
            ref.es_referencia = True
            
        db.session.commit()
        return jsonify({"success": True})
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error al editar referencia: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# =========================================================
# VISTA DE BIBLIOGRAFÍA
# =========================================================


@app.route("/bibliografia")
def bibliografia():
    """Vista de bibliografía completa ordenada por número de referencia"""
    proyecto = get_proyecto_activo()
    if not proyecto:
        flash("Debes seleccionar un proyecto activo", "warning")
        return redirect(url_for("listar_proyectos"))

    try:
        # Obtener todas las referencias incluidas con número asignado
        referencias = (
            Prensa.query.filter(
                Prensa.proyecto_id == proyecto.id,
                db.or_(
                    Prensa.es_referencia == True, Prensa.numero_referencia.isnot(None)
                )
            )
            .order_by(Prensa.numero_referencia.asc(), Prensa.fecha_original.asc())
            .all()
        )
        app.logger.info(f"BIBLIOGRAFIA (Proyecto {proyecto.id}): Encontradas {len(referencias)} referencias.")

        # Agrupar por número de referencia
        referencias_agrupadas = {}
        for ref in referencias:
            if ref.numero_referencia is not None:
                num = ref.numero_referencia
                if num not in referencias_agrupadas:
                    referencias_agrupadas[num] = []
                referencias_agrupadas[num].append(ref)
            else:
                # Cada item sin número va en su propia "agrupación" ficticia para que no se combinen
                num = 999999 + ref.id
                referencias_agrupadas[num] = [ref]

        # Estadísticas
        total_numeros = len(referencias_agrupadas)
        total_articulos = len(referencias)
        numeros_multiples = sum(
            1 for refs in referencias_agrupadas.values() if len(refs) > 1
        )

        # Obtener formato de cita preferido (por defecto Chicago)
        formato = request.args.get("formato", "chicago")

        return render_template(
            "bibliografia.html",
            referencias_agrupadas=referencias_agrupadas,
            total_numeros=total_numeros,
            total_articulos=total_articulos,
            numeros_multiples=numeros_multiples,
            formato=formato,
        )
    except Exception as e:
        app.logger.error(f"Error en bibliografía: {e}")
        flash(f"Error al cargar bibliografía: {str(e)}", "danger")
        return redirect(url_for("index"))


@app.route("/bibliografia/exportar")
def bibliografia_exportar():
    """Exporta la bibliografía en diferentes formatos"""
    proyecto = get_proyecto_activo()
    if not proyecto:
        flash("Debes seleccionar un proyecto activo", "warning")
        return redirect(url_for("listar_proyectos"))

    try:
        formato = request.args.get("formato", "bibtex")

        referencias = (
            Prensa.query.filter(
                Prensa.proyecto_id == proyecto.id,
                db.or_(
                    Prensa.es_referencia == True, Prensa.numero_referencia.isnot(None)
                )
            )
            .order_by(Prensa.numero_referencia.asc())
            .all()
        )

        if formato == "bibtex":
            contenido = generar_bibtex(referencias)
            mimetype = "application/x-bibtex"
            extension = "bib"
        elif formato == "ris":
            contenido = generar_ris(referencias)
            mimetype = "application/x-research-info-systems"
            extension = "ris"
        elif formato == "txt":
            contenido = generar_bibliografia_txt(
                referencias, request.args.get("estilo", "chicago")
            )
            mimetype = "text/plain"
            extension = "txt"
        else:
            flash("Formato no soportado", "danger")
            return redirect(url_for("bibliografia"))

        response = make_response(contenido)
        response.headers["Content-Type"] = f"{mimetype}; charset=utf-8"
        response.headers["Content-Disposition"] = (
            f"attachment; filename=bibliografia_sirio.{extension}"
        )

        return response

    except Exception as e:
        app.logger.error(f"Error al exportar bibliografía: {e}")
        flash(f"Error al exportar: {str(e)}", "danger")
        return redirect(url_for("bibliografia"))


# =========================================================
# FUNCIONES AUXILIARES - GENERACIÓN DE FORMATOS
# =========================================================


def generar_bibtex(referencias):
    """Genera archivo BibTeX"""
    lineas = []
    lineas.append("% Bibliografía del estudio del S.S. Sirio")
    lineas.append("% Generado automáticamente\n")

    for ref in referencias:
        entry_type = "article" if ref.publicacion else "misc"
        key = f"sirio{ref.numero_referencia:03d}"

        lineas.append(f"@{entry_type}{{{key},")

        if ref.titulo:
            lineas.append(f"  title = {{{ref.titulo}}},")
        if ref.autor:
            lineas.append(f"  author = {{{ref.autor}}},")
        if ref.publicacion:
            lineas.append(f"  journal = {{{ref.publicacion}}},")
        if ref.anio:
            lineas.append(f"  year = {{{ref.anio}}},")
        if ref.fecha_original:
            lineas.append(f"  date = {{{ref.fecha_original}}},")
        if ref.pagina_inicio:
            if ref.pagina_fin:
                lineas.append(f"  pages = {{{ref.pagina_inicio}--{ref.pagina_fin}}},")
            else:
                lineas.append(f"  pages = {{{ref.pagina_inicio}}},")
        if ref.url:
            lineas.append(f"  url = {{{ref.url}}},")
        if ref.fecha_consulta:
            lineas.append(f"  urldate = {{{ref.fecha_consulta}}},")
        if ref.idioma:
            lineas.append(f"  language = {{{ref.idioma}}},")

        lineas.append(f"  note = {{Número de referencia: [{ref.numero_referencia}]}}")
        lineas.append("}\n")

    return "\n".join(lineas)


def generar_ris(referencias):
    """Genera archivo RIS (Reference Manager)"""
    lineas = []

    for ref in referencias:
        lineas.append("TY  - JOUR" if ref.publicacion else "TY  - GEN")

        if ref.titulo:
            lineas.append(f"TI  - {ref.titulo}")
        if ref.autor:
            # RIS espera autores en formato: Apellido, Nombre
            lineas.append(f"AU  - {ref.autor}")
        if ref.publicacion:
            lineas.append(f"JO  - {ref.publicacion}")
        if ref.anio:
            lineas.append(f"PY  - {ref.anio}")
        if ref.fecha_original:
            lineas.append(f"DA  - {ref.fecha_original}")
        if ref.pagina_inicio:
            lineas.append(f"SP  - {ref.pagina_inicio}")
        if ref.pagina_fin:
            lineas.append(f"EP  - {ref.pagina_fin}")
        if ref.url:
            lineas.append(f"UR  - {ref.url}")
        if ref.idioma:
            lineas.append(f"LA  - {ref.idioma}")

        lineas.append(f"N1  - Número de referencia: [{ref.numero_referencia}]")
        lineas.append("ER  - \n")

    return "\n".join(lineas)


def generar_bibliografia_txt(referencias, estilo="chicago"):
    """Genera bibliografía en formato texto plano"""
    lineas = []
    lineas.append("=" * 80)
    lineas.append("BIBLIOGRAFÍA - ESTUDIO DEL NAUFRAGIO DEL S.S. SIRIO (1906)")
    lineas.append("=" * 80)
    lineas.append("")

    for ref in referencias:
        # Formato Chicago (default)
        partes = []

        # [Número]
        partes.append(f"[{ref.numero_referencia}]")

        # Autor
        if ref.autor:
            if ref.tipo_autor == "anónimo":
                partes.append("Anónimo.")
            else:
                partes.append(f"{ref.autor}.")
        else:
            partes.append("Anónimo.")

        # Título
        if ref.titulo:
            partes.append(f'"{ref.titulo}."')

        # Publicación
        if ref.publicacion:
            partes.append(f"*{ref.publicacion}*")

        # Fecha
        if ref.fecha_original:
            partes.append(f"({ref.fecha_original})")
        elif ref.anio:
            partes.append(f"({ref.anio})")

        # Páginas
        if ref.pagina_inicio:
            if ref.pagina_fin:
                partes.append(f"pp. {ref.pagina_inicio}-{ref.pagina_fin}.")
            else:
                partes.append(f"p. {ref.pagina_inicio}.")

        # URL
        if ref.url:
            partes.append(f"Disponible en: {ref.url}")
            if ref.fecha_consulta:
                partes.append(f"(consultado {ref.fecha_consulta}).")

        lineas.append(" ".join(partes))
        lineas.append("")

    lineas.append("=" * 80)
    lineas.append(f"Total de referencias: {len(referencias)}")
    lineas.append("=" * 80)

    return "\n".join(lineas)


# =========================================================
# 🤖 ANÁLISIS NLP CON SPACY
# =========================================================
# Note: redundant _nlp_model and get_nlp_model removed. 
# Using centralized get_nlp() from utils.py which respects dashboard config.


@app.route("/api/analyze-text", methods=["POST"])
@csrf.exempt
def analyze_text():
    """
    Analiza texto con NLP: Named Entities, Sentiment, Keywords
    POST body: {"text": "contenido a analizar", "ref_id": 123 (opcional)}
    """
    try:
        data = request.get_json()
        text = data.get("text", "")

        if not text or len(text.strip()) < 10:
            return jsonify({"error": "Texto demasiado corto para analizar"}), 400

        # === 1. NAMED ENTITY RECOGNITION (spaCy) ===
        nlp = get_nlp()
        entities = []

        if nlp:
            doc = nlp(text[:5000])  # Limitar a 5000 chars para rendimiento

            # Agrupar entidades por tipo
            entities_by_type = {}
            for ent in doc.ents:
                label = ent.label_
                if label not in entities_by_type:
                    entities_by_type[label] = []
                entities_by_type[label].append(
                    {"text": ent.text, "start": ent.start_char, "end": ent.end_char}
                )

            # Convertir a lista con conteos
            for label, ents in entities_by_type.items():
                entities.append(
                    {
                        "type": label,
                        "count": len(ents),
                        "items": ents[:10],  # Máximo 10 ejemplos
                    }
                )

        # === 2. SENTIMENT ANALYSIS (textblob) ===
        sentiment = {"polarity": 0, "subjectivity": 0, "label": "neutral"}

        try:
            from textblob import TextBlob

            blob = TextBlob(text[:2000])  # Limitar para rendimiento
            sentiment["polarity"] = round(blob.sentiment.polarity, 3)
            sentiment["subjectivity"] = round(blob.sentiment.subjectivity, 3)

            # Clasificar sentimiento
            if sentiment["polarity"] > 0.1:
                sentiment["label"] = "positive"
            elif sentiment["polarity"] < -0.1:
                sentiment["label"] = "negative"
            else:
                sentiment["label"] = "neutral"
        except Exception as e:
            print(f"Error en sentiment analysis: {e}")

        # === 3. KEYWORDS EXTRACTION (TF-IDF) ===
        keywords = []

        try:
            from sklearn.feature_extraction.text import TfidfVectorizer

            # Crear vectorizador con parámetros para español
            vectorizer = TfidfVectorizer(
                max_features=15,
                stop_words=None,  # spaCy ya maneja stopwords
                ngram_range=(1, 2),  # Unigramas y bigramas
                min_df=1,
            )

            # Necesitamos al menos 2 documentos para TF-IDF, usamos el texto dividido
            sentences = text.split(".")[:20]  # Primeras 20 frases
            if len(sentences) >= 2:
                tfidf_matrix = vectorizer.fit_transform(sentences)
                feature_names = vectorizer.get_feature_names_out()

                # Calcular scores promedio
                scores = tfidf_matrix.mean(axis=0).A1
                top_indices = scores.argsort()[-10:][::-1]

                keywords = [
                    {"word": feature_names[i], "score": round(float(scores[i]), 3)}
                    for i in top_indices
                    if scores[i] > 0
                ]
        except Exception as e:
            print(f"Error en keyword extraction: {e}")

        # === 4. ESTADÍSTICAS BÁSICAS ===
        stats = {
            "char_count": len(text),
            "word_count": len(text.split()),
            "sentence_count": len([s for s in text.split(".") if s.strip()]),
        }

        return jsonify(
            {
                "success": True,
                "entities": entities,
                "sentiment": sentiment,
                "keywords": keywords,
                "stats": stats,
            }
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/corpus-analysis")
def corpus_analysis():
    """
    Analiza todo el corpus de contenidos para generar estadísticas globales
    """
    try:
        # Obtener stopwords personalizadas del parámetro query
        custom_stopwords = request.args.get("stopwords", "")

        # Obtener campos seleccionados
        fields = request.args.get("fields", "contenido,titulo").split(",")
        fields = [f for f in fields if f in ("contenido", "titulo")]
        if not fields:
            fields = ["contenido"]

        limite = request.args.get('limit', '1000')
        try:
             limite = int(limite)
        except (ValueError, TypeError):
             limite = 1000

        from app import get_proyecto_activo
        proyecto = get_proyecto_activo()
        query = Prensa.query
        if proyecto:
            query = query.filter(Prensa.proyecto_id == proyecto.id, Prensa.incluido == True)
        else:
            query = query.filter(Prensa.incluido == True)
        
        if limite > 0:
            referencias = query.limit(limite).all()
        else:
            referencias = query.all()
        referencias = [ref for ref in referencias if any(getattr(ref, f, None) for f in fields)]
        if not referencias:
            return jsonify({"error": "No hay contenidos para analizar"}), 404

        # === ESTADÍSTICAS GENERALES ===
        total_refs = query.count()
        with_content = query.filter(Prensa.contenido.isnot(None), Prensa.contenido != "").count()
        content_percentage = (
            round((with_content / total_refs * 100), 1) if total_refs > 0 else 0
        )

        corpus_text = " ".join([
            " ".join([getattr(ref, f, "")[:500] for f in fields if getattr(ref, f, None)])
            for ref in referencias
        ])

        # === WORD CLOUD DATA ===
        word_freq = {}
        try:
            from sklearn.feature_extraction.text import CountVectorizer

            # Stopwords personalizadas para español - periodismo
            if custom_stopwords:
                # Usar stopwords del usuario (normalizadas)
                stopwords_es = set(
                    normalizar_texto(w) for w in custom_stopwords.split(",") if w.strip()
                )
            else:
                # Usar stopwords predeterminadas (normalizadas, sin palabras clave del proyecto)
                stopwords_es = set([
                    normalizar_texto(sw) for sw in [
                        "de", "la", "que", "el", "en", "y", "a", "los", "del", "se", "las",
                        "por", "un", "para", "con", "no", "una", "su", "al", "lo", "como", "más", "pero", "sus", "le", "ya", "o", "fue", "este", "ha", "sí", "porque", "esta", "son", "entre", "cuando", "muy", "sin", "sobre", "también", "me", "hasta", "hay", "donde", "han", "quien", "desde", "todo", "nos", "durante", "todos", "uno", "les", "ni", "contra", "otros", "ese", "eso", "ante", "ellos", "e", "esto", "mí", "antes", "algunos", "qué", "unos", "yo", "otro", "otras", "otra", "él", "tanto", "esa", "estos", "mucho", "quienes", "nada", "muchos", "cual", "poco", "ella", "estar", "estas", "algunas", "algo", "nosotros", "mi", "mis", "tú", "te", "ti", "tu", "tus", "ellas", "nosotras", "vosotros", "vosotras", "os", "mío", "mía", "míos", "mías", "tuyo", "tuya", "tuyos", "tuyas", "suyo", "suya", "suyos", "suyas", "nuestro", "nuestra", "nuestros", "nuestras", "vuestro", "vuestra", "vuestros", "vuestras", "esos", "esas", "estoy", "estás", "está", "estamos", "estáis", "están", "esté", "estén", "estaba", "estaban", "he", "has", "han", "hace", "hacía", "hacen", "hacer", "cada", "ser", "haber", "era", "eras", "eran", "soy", "es", "sea", "sean", "según", "sino", "aquel", "aquella", "aquellos", "aquellas", "sido", "siendo"
                    ]
                ])

            # NUNCA filtrar estas palabras clave del proyecto (whitelist)
            palabras_clave_proyecto = {
                "sirio",
                "vapor",
                "naufragio",
                "náufrago",
                "náufragos",
                "génova",
                "cartagena",
            }
            # Normalizar también las palabras clave del proyecto
            palabras_clave_proyecto_norm = set(normalizar_texto(w) for w in palabras_clave_proyecto)
            stopwords_es = stopwords_es - palabras_clave_proyecto_norm

            vectorizer = CountVectorizer(
                max_features=300,
                ngram_range=(1, 2),
                min_df=1,
                stop_words=list(stopwords_es),
                token_pattern=r"\b[a-záéíóúüñ]{2,}\b",
            )

            texts = [
                " ".join([getattr(ref, f, "")[:500] for f in fields if getattr(ref, f, None)])
                for ref in referencias
            ]
            if texts:
                count_matrix = vectorizer.fit_transform(texts)
                feature_names = vectorizer.get_feature_names_out()
                counts = count_matrix.sum(axis=0).A1

                # Normalizar cada palabra generada y filtrar stopwords tras vectorizer
                word_freq = {}
                for i in range(len(feature_names)):
                    palabra = feature_names[i]
                    palabra_norm = normalizar_texto(palabra)
                    if palabra_norm not in stopwords_es:
                        word_freq[palabra] = int(counts[i])
        except Exception as e:
            print(f"Error generando word cloud: {e}")

        # === ENTITY NETWORK ===
        entity_network = {"nodes": [], "links": []}

        nlp = get_nlp()
        if nlp:
            all_entities = []
            for ref in referencias[:30]:  # Primeras 30 referencias
                texto = " ".join([getattr(ref, f, "")[:1000] for f in fields if getattr(ref, f, None)])
                if not texto:
                    continue
                doc = nlp(texto)
                all_entities.extend(
                    [
                        {"text": ent.text, "label": ent.label_, "ref_id": ref.id}
                        for ent in doc.ents
                        if ent.label_
                        in [
                            "PER",
                            "LOC",
                            "ORG",
                        ]  # Solo personas, lugares, organizaciones
                    ]
                )

            # Crear nodos (entidades únicas)
            unique_entities = {}
            for ent in all_entities:
                key = (ent["text"], ent["label"])
                if key not in unique_entities:
                    unique_entities[key] = {
                        "id": len(unique_entities),
                        "name": ent["text"],
                        "type": ent["label"],
                        "count": 1,
                        "refs": [ent["ref_id"]],
                    }
                else:
                    unique_entities[key]["count"] += 1
                    if ent["ref_id"] not in unique_entities[key]["refs"]:
                        unique_entities[key]["refs"].append(ent["ref_id"])

            entity_network["nodes"] = list(unique_entities.values())

            # Crear enlaces (co-ocurrencias en mismo documento)
            from itertools import combinations

            for ref in referencias[:30]:
                texto = " ".join([getattr(ref, f, "")[:1000] for f in fields if getattr(ref, f, None)])
                if not texto:
                    continue
                doc = nlp(texto)
                ref_entities = [
                    (ent.text, ent.label_)
                    for ent in doc.ents
                    if ent.label_ in ["PER", "LOC", "ORG"]
                ]

                # Crear enlaces entre todas las parejas
                for e1, e2 in combinations(set(ref_entities), 2):
                    if e1 in unique_entities and e2 in unique_entities:
                        entity_network["links"].append(
                            {
                                "source": unique_entities[e1]["id"],
                                "target": unique_entities[e2]["id"],
                                "ref_id": ref.id,
                            }
                        )

        return jsonify(
            {
                "success": True,
                "total_docs": len(referencias),
                "word_cloud": word_freq,
                "entity_network": entity_network,
                "stats": {
                    "total_refs": total_refs,
                    "with_content": with_content,
                    "content_percentage": content_percentage,
                },
            }
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# =========================================================
# 🤖 CORRECCIÓN DE OCR CON IA (CLAUDE SONNET 4.5)
# =========================================================


@app.route("/api/ocr/corregir", methods=["POST"])
@csrf.exempt
def corregir_ocr_con_ia():
    """
    Mejora los metadatos extraídos por OCR usando Claude API

    Recibe:
    - texto_ocr: texto completo extraído por Tesseract
    - metadatos_raw: metadatos detectados por regex (pueden tener errores)

    Retorna:
    - metadatos corregidos y refinados con IA
    - lista de correcciones realizadas
    - nivel de confianza mejorado
    """
    try:
        # Obtener API key de variables de entorno
        api_key = os.getenv("ANTHROPIC_API_KEY")

        if not api_key or api_key == "tu_api_key_aqui":
            return jsonify(
                {
                    "error": "API key de Anthropic no configurada",
                    "mensaje": "Por favor, añade ANTHROPIC_API_KEY en el archivo .env",
                }
            ), 400

        # Obtener datos del request
        data = request.get_json()
        texto_ocr = data.get("texto", "")
        metadatos_raw = data.get("metadatos", {})

        if not texto_ocr:
            return jsonify({"error": "No se proporcionó texto OCR"}), 400

        # Importar librería de Anthropic
        try:
            import anthropic
        except ImportError:
            return jsonify(
                {
                    "error": "Librería anthropic no instalada",
                    "mensaje": "Ejecuta: pip install anthropic",
                }
            ), 500

        # Crear cliente de Claude
        client = anthropic.Anthropic(api_key=api_key)

        # Construir prompt para Claude
        prompt = f"""Eres un experto en hemerografía histórica española e italiana (período 1800-2000).
Analiza este texto extraído por OCR de una noticia de prensa histórica y corrige los metadatos.

TEXTO OCR EXTRAÍDO:
{texto_ocr[:2000]}

METADATOS DETECTADOS (pueden contener errores de OCR):
{json.dumps(metadatos_raw, indent=2, ensure_ascii=False)}

INSTRUCCIONES CRÍTICAS:
1. Corrige errores comunes de OCR:
   - Confusiones: rn→m, l→I, O→0, cl→d, vv→w
   - Espacios mal colocados
   - Puntuación incorrecta

2. FECHAS:
   - Normaliza a formato DD/MM/YYYY
   - Detecta fechas escritas ("4 de agosto de 1906" → "04/08/1906")
   - Si solo hay año, úsalo en campo "anio"

3. AUTORES:
   - Formato estricto: "APELLIDO, Nombre"
   - Si detectas "Por: Juan Pérez" → "PÉREZ, Juan"
   - Si es anónimo, deja vacío

4. TÍTULO:
   - Identifica el titular principal (suele estar en mayúsculas o al inicio)
   - Máximo 200 caracteres
   - Elimina ruido (números de página, fechas repetidas)

5. PUBLICACIÓN:
   - Nombres completos: "El Eco de Asturias", "Il Lavoro", etc.
   - Normaliza variantes ("Eco Asturias" → "El Eco de Asturias")

6. CIUDAD:
   - Detecta ciudad de publicación o mención principal
   - Formato: "Oviedo", "Gijón", "Buenos Aires"

7. PÁGINAS:
   - Si detectas "p. 3" o "pág. 5-7", extrae números
   - pagina_inicio y pagina_fin

RESPONDE SOLO CON JSON VÁLIDO (sin comentarios, sin markdown):
{{
  "titulo": "título corregido",
  "autor": "APELLIDO, Nombre o vacío",
  "fecha_original": "DD/MM/YYYY o vacío",
  "anio": año numérico o null,
  "publicacion": "nombre completo",
  "ciudad": "ciudad o vacío",
  "pagina_inicio": número o null,
  "pagina_fin": número o null,
  "confianza": 0-100 (tu nivel de confianza en estas correcciones),
  "correcciones": ["lista de correcciones importantes que realizaste"],
  "advertencias": ["avisos sobre datos dudosos o faltantes"]
}}"""

        # Llamar a Claude API
        print("[IA] Enviando request a Claude Sonnet 4.5...")

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            temperature=0.3,  # Baja temperatura para respuestas más precisas
            messages=[{"role": "user", "content": prompt}],
        )

        # Extraer respuesta de Claude
        respuesta_texto = response.content[0].text.strip()

        # Intentar parsear JSON (Claude a veces añade ```json```)
        if "```json" in respuesta_texto:
            respuesta_texto = (
                respuesta_texto.split("```json")[1].split("```")[0].strip()
            )
        elif "```" in respuesta_texto:
            respuesta_texto = respuesta_texto.split("```")[1].split("```")[0].strip()

        metadatos_corregidos = json.loads(respuesta_texto)

        print(
            f"[IA] ✓ Corrección completada. Confianza: {metadatos_corregidos.get('confianza', 0)}%"
        )

        return jsonify(
            {
                "success": True,
                "metadatos": metadatos_corregidos,
                "metadatos_originales": metadatos_raw,
                "tokens_usados": response.usage.input_tokens
                + response.usage.output_tokens,
            }
        )

    except json.JSONDecodeError as e:
        print(f"[IA] Error parseando JSON: {e}")
        print(f"Respuesta de Claude: {respuesta_texto}")
        return jsonify(
            {
                "error": "Error al parsear respuesta de IA",
                "detalle": str(e),
                "respuesta_raw": respuesta_texto[:500],
            }
        ), 500

    except Exception as e:
        print(f"[IA] Error en corrección OCR: {e}")
        return jsonify({"error": "Error al procesar con IA", "detalle": str(e)}), 500


# =========================================================
# 👤 RUTAS: AUTENTICACIÓN DE USUARIOS
# =========================================================


@app.route("/registro", methods=["GET", "POST"])
def registro():
    """Registro de un nuevo usuario"""
    if current_user.is_authenticated:
        return redirect(url_for("home"))

    if request.method == "POST":
        nombre = (request.form.get("nombre") or "").strip()
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        password2 = request.form.get("password2") or ""

        # Validaciones básicas
        if not nombre or not email or not password:
            flash("Todos los campos son obligatorios.", "warning")
            return redirect(url_for("registro"))

        if password != password2:
            flash("Las contraseñas no coinciden.", "warning")
            return redirect(url_for("registro"))

        # ¿Ya existe ese correo?
        if Usuario.query.filter_by(email=email).first():
            flash("Ya existe un usuario con ese correo.", "error")
            return redirect(url_for("registro"))

        # Crear usuario con imágenes por defecto del admin
        usuario = Usuario(
            nombre=nombre, 
            email=email,
            foto_perfil='img/avatars/admin_avatar.png',
            fondo_perfil='img/backgrounds/admin_banner.png'
        )
        usuario.set_password(password)
        db.session.add(usuario)
        db.session.commit()

        flash("Cuenta creada correctamente. Ya puedes iniciar sesión.", "success")
        return redirect(url_for("login"))

    return render_template("registro.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Inicio de sesión"""
    if current_user.is_authenticated:
        return redirect(url_for("home"))

    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""

        usuario = Usuario.query.filter_by(email=email).first()

        if usuario is None or not usuario.check_password(password):
            flash("Correo o contraseña incorrectos.", "danger")
            return redirect(url_for("login"))

        # Iniciar sesión
        login_user(usuario)
        flash(f"Bienvenido/a, {usuario.nombre}.", "success")

        # Si venía redirigido desde @login_required
        next_page = request.args.get("next")
        response = make_response(redirect(next_page or url_for("home")))
        response.set_cookie('force_dark_mode', '1', max_age=3600)  # Forzar modo oscuro en cliente
        return response

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    """Cerrar sesión del usuario actual"""
    # Limpiar proyecto activo de la sesión
    session.pop("proyecto_activo_id", None)
    logout_user()
    flash("Sesión cerrada.", "info")
    return redirect(url_for("home"))


# =========================================================
# 🗂️ RUTAS: GESTIÓN DE PROYECTOS
# =========================================================


@app.route("/proyectos")
@login_required
def listar_proyectos():
    """Redirigir a la ruta del blueprint de proyectos"""
    return redirect(url_for("proyectos.listar"))


@app.route("/biblioteca/proyecto/<int:proyecto_id>")
@login_required
def biblioteca_proyecto(proyecto_id):
    """Activar un proyecto por su ID y redirigir a la vista principal de la biblioteca."""
    proyecto = Proyecto.query.filter_by(id=proyecto_id, user_id=current_user.id).first()
    if not proyecto:
        flash("Proyecto no encontrado o no tienes permisos.", "error")
        return redirect(url_for("listar_proyectos"))

    # Marcar proyecto como activo en sesión
    session["proyecto_activo_id"] = proyecto.id
    flash(f"Proyecto activo: {proyecto.nombre}", "info")
    return redirect(url_for("index"))


@app.route("/proyecto/nuevo", methods=["GET", "POST"])
@login_required
def crear_proyecto():
    """Crear un nuevo proyecto para el usuario actual"""
    if request.method == "POST":
        nombre = (request.form.get("nombre") or "").strip()
        descripcion = (request.form.get("descripcion") or "").strip()
        tipo = request.form.get("tipo", "hemerografia")
        perfil_analisis = request.form.get("perfil_analisis", "contenido")

        if not nombre:
            flash("El nombre del proyecto es obligatorio", "error")
            return redirect(url_for("crear_proyecto"))

        # Verificar que no exista otro proyecto con ese nombre PARA ESTE USUARIO
        if Proyecto.query.filter_by(nombre=nombre, user_id=current_user.id).first():
            flash(f'Ya tienes un proyecto con el nombre "{nombre}"', "error")
            return redirect(url_for("crear_proyecto"))

        # Crear proyecto
        nuevo_proyecto = Proyecto(
            nombre=nombre,
            descripcion=descripcion,
            tipo=tipo,
            perfil_analisis=perfil_analisis,
            activo=True,
            user_id=current_user.id,
        )

        db.session.add(nuevo_proyecto)
        db.session.commit()

        # Activar automáticamente el nuevo proyecto
        session["proyecto_activo_id"] = nuevo_proyecto.id

        flash(f'✅ Proyecto "{nombre}" creado correctamente', "success")
        return redirect(url_for("index"))

    return render_template("nuevo_proyecto.html")


@app.route("/proyecto/<int:id>/activar")
@login_required
def activar_proyecto(id):
    """Cambiar el proyecto activo del usuario actual"""
    proyecto = Proyecto.query.filter_by(id=id, user_id=current_user.id).first_or_404()

    session["proyecto_activo_id"] = proyecto.id
    flash(f"📂 Proyecto activo: {proyecto.nombre}", "info")
    return redirect(request.referrer or url_for("index"))


@app.route("/proyecto/desactivar/<int:id>")
@login_required
def desactivar_proyecto(id):
    """Desactivar el proyecto activo (quitarlo de la sesión) para este usuario"""
    proyecto = Proyecto.query.filter_by(id=id, user_id=current_user.id).first_or_404()

    proyecto_activo_id = session.get("proyecto_activo_id")
    if proyecto_activo_id == proyecto.id:
        session.pop("proyecto_activo_id", None)
        flash(
            f'📌 Proyecto "{proyecto.nombre|upper}" desactivado. No hay proyecto activo actualmente.',
            "info",
        )
    else:
        flash("Este proyecto no estaba marcado como activo.", "warning")

    return redirect(request.referrer or url_for("listar_proyectos"))


@app.route("/proyecto/<int:id>/editar", methods=["POST"])
@login_required
def editar_proyecto(id):
    """Editar un proyecto existente perteneciente al usuario actual"""
    proyecto = Proyecto.query.filter_by(id=id, user_id=current_user.id).first_or_404()

    nombre = (request.form.get("nombre") or "").strip()
    descripcion = (request.form.get("descripcion") or "").strip()
    tipo = request.form.get("tipo", "hemerografia")

    if not nombre:
        flash("El nombre del proyecto es obligatorio", "error")
        return redirect(url_for("listar_proyectos"))

    # Verificar que no exista otro proyecto del mismo usuario con el mismo nombre
    proyecto_existente = Proyecto.query.filter_by(
        nombre=nombre, user_id=current_user.id
    ).first()
    if proyecto_existente and proyecto_existente.id != id:
        flash(f'Ya existe otro proyecto con el nombre "{nombre}"', "error")
        return redirect(url_for("listar_proyectos"))

    # Actualizar datos
    proyecto.nombre = nombre
    proyecto.descripcion = descripcion
    proyecto.tipo = tipo

    db.session.commit()

    flash(f'✅ Proyecto "{nombre}" actualizado correctamente', "success")
    return redirect(url_for("listar_proyectos"))


@app.route("/proyecto/<int:id>/eliminar", methods=["POST"])
@login_required
def eliminar_proyecto(id):
    """Eliminar un proyecto (con confirmación) del usuario actual"""
    proyecto = Proyecto.query.filter_by(id=id, user_id=current_user.id).first_or_404()

    # Verificar que no sea el único proyecto de ESTE usuario
    if Proyecto.query.filter_by(user_id=current_user.id).count() == 1:
        flash("❌ No puedes eliminar tu único proyecto", "error")
        return redirect(url_for("listar_proyectos"))

    # Verificar que no sea el proyecto activo
    if session.get("proyecto_activo_id") == id:
        flash(
            "❌ No puedes eliminar el proyecto activo. Activa otro proyecto primero.",
            "error",
        )
        return redirect(url_for("listar_proyectos"))

    nombre = proyecto.nombre
    num_articulos = Prensa.query.filter_by(proyecto_id=id).count()
    num_publicaciones = Publicacion.query.filter_by(proyecto_id=id).count()

    # Eliminar proyecto (cascade eliminará artículos y publicaciones)
    db.session.delete(proyecto)
    db.session.commit()

    flash(
        f'🗑️ Proyecto "{nombre}" eliminado ({num_articulos} artículos, {num_publicaciones} publicaciones)',
        "warning",
    )
    return redirect(url_for("listar_proyectos"))


# =========================================================
# FUNCIÓN AUXILIAR: OBTENER PROYECTO ACTIVO
# =========================================================


def get_proyecto_activo():
    """Obtiene el proyecto activo de la sesión; si no existe, devuelve None"""
    proyecto_id = session.get("proyecto_activo_id")

    if proyecto_id:
        proyecto = Proyecto.query.get(proyecto_id)
        if proyecto:
            return proyecto

    # No seleccionar uno automáticamente
    return None


# =========================================================
# RUTA DE TEST PARA DEBUG
# =========================================================
@app.route("/test-proyecto")
def test_proyecto():
    proyecto = get_proyecto_activo()
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
        <meta http-equiv="Pragma" content="no-cache">
        <meta http-equiv="Expires" content="0">
        <title>TEST PROYECTO</title>
    </head>
    <body style="margin:0; padding:40px; background:#000; color:#0f0; font-family:monospace; font-size:20px;">
        <h1 style="color:#ff0; background:#f00; padding:20px;">🔥 TEST PROYECTO 🔥</h1>
        <p>Proyecto activo: <strong style="color:#fff; font-size:30px;">{proyecto.nombre if proyecto else "NONE"}</strong></p>
        <p>ID: {proyecto.id if proyecto else "N/A"}</p>
        <p>Tipo: {proyecto.tipo if proyecto else "N/A"}</p>
        <hr style="border-color:#0f0;">
        <p>Session proyecto_id: {session.get("proyecto_activo_id", "NO SET")}</p>
        <p>Total proyectos en DB: {Proyecto.query.count()}</p>
        <hr style="border-color:#0f0;">
        <a href="/" style="color:#0ff; font-size:24px;">← Volver al inicio</a>
    </body>
    </html>
    """
    response = make_response(html)
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


# =========================================================
# 📚 SISTEMA DE ARTÍCULOS CIENTÍFICOS
# =========================================================

@app.route("/articulos/<int:proyecto_id>")
@login_required
def articulos_lista(proyecto_id):
    """Lista de artículos científicos del proyecto"""
    proyecto = Proyecto.query.get_or_404(proyecto_id)
    
    # Verificar acceso
    if proyecto.user_id != current_user.id:
        flash("No tienes acceso a este proyecto", "danger")
        return redirect(url_for("home"))
    
    # Obtener filtros
    estado_filtro = request.args.get('estado', 'todos')
    
    # Query base
    query = text("""
        SELECT id, titulo, subtitulo, autores, estado, version, 
               palabras_totales, created_at, updated_at, fecha_publicacion
        FROM articulos_cientificos 
        WHERE proyecto_id = :proyecto_id AND user_id = :user_id
    """)
    
    params = {'proyecto_id': proyecto_id, 'user_id': current_user.id}
    
    if estado_filtro != 'todos':
        query = text("""
            SELECT id, titulo, subtitulo, autores, estado, version, 
                   palabras_totales, created_at, updated_at, fecha_publicacion
            FROM articulos_cientificos 
            WHERE proyecto_id = :proyecto_id AND user_id = :user_id AND estado = :estado
        """)
        params['estado'] = estado_filtro
    
    articulos = db.session.execute(query, params).fetchall()
    
    return render_template('articulos_lista.html', 
                         proyecto=proyecto, 
                         articulos=articulos,
                         estado_filtro=estado_filtro)


@app.route("/articulos/nuevo/<int:proyecto_id>")
@login_required
def articulo_nuevo(proyecto_id):
    """Crear nuevo artículo científico"""
    proyecto = Proyecto.query.get_or_404(proyecto_id)
    
    if proyecto.user_id != current_user.id:
        flash("No tienes acceso a este proyecto", "danger")
        return redirect(url_for("home"))
    
    # Obtener plantillas disponibles
    plantillas = db.session.execute(
        text("SELECT id, nombre, tipo_articulo, descripcion FROM plantillas_secciones")
    ).fetchall()
    
    return render_template('articulo_editor.html', 
                         proyecto=proyecto, 
                         articulo=None,
                         plantillas=plantillas)


@app.route("/articulos/editar/<int:articulo_id>")
@login_required
def articulo_editar(articulo_id):
    """Editar artículo existente"""
    articulo_data = db.session.execute(
        text("SELECT * FROM articulos_cientificos WHERE id = :id"),
        {'id': articulo_id}
    ).fetchone()
    
    if not articulo_data:
        flash("Artículo no encontrado", "danger")
        return redirect(url_for("home"))
    
    proyecto = Proyecto.query.get(articulo_data.proyecto_id)
    
    if articulo_data.user_id != current_user.id:
        flash("No tienes acceso a este artículo", "danger")
        return redirect(url_for("home"))
    
    # Convertir Row a diccionario
    articulo = dict(articulo_data._mapping)
    
    # Función auxiliar para parseo robusto (JSON o literal Python)
    def parse_json_robust(data):
        if not data:
            return None
        try:
            return json.loads(data)
        except (json.JSONDecodeError, TypeError):
            try:
                # Fallback para datos guardados erróneamente con comillas simples (formato literal Python)
                return ast.literal_eval(data)
            except Exception:
                return data

    # Parsear JSON fields
    articulo['autores'] = parse_json_robust(articulo.get('autores'))
    articulo['palabras_clave'] = parse_json_robust(articulo.get('palabras_clave'))
    articulo['keywords'] = parse_json_robust(articulo.get('keywords'))
    articulo['contenido_json'] = parse_json_robust(articulo.get('contenido_json'))
    
    return render_template('articulo_editor.html', 
                         proyecto=proyecto, 
                         articulo=articulo)


@app.route("/api/articulos/guardar", methods=['POST'])
@csrf.exempt
@login_required
def api_articulo_guardar():
    """Guardar artículo (crear o actualizar)"""
    try:
        datos = request.get_json()
        
        # Validar datos mínimos
        if not datos.get('titulo'):
            return jsonify({'error': 'El título es obligatorio'}), 400
        
        # Preparar datos para BD
        autores_json = json.dumps(datos.get('autores', []))
        palabras_clave_json = json.dumps(datos.get('palabras_clave', []))
        keywords_json = json.dumps(datos.get('keywords', []))
        contenido_json = json.dumps(datos.get('secciones', []))
        referencias_list = datos.get('referencias', []) or []
        proyecto_id = datos.get('proyectoId') or datos.get('proyecto_id')
        
        # Calcular estadísticas
        palabras_totales = calcular_palabras_totales(datos.get('secciones', []))
        paginas_estimadas = max(1, palabras_totales // 300)  # ~300 palabras por página
        
        if datos.get('id'):
            # ACTUALIZAR artículo existente
            query = text("""
                UPDATE articulos_cientificos 
                SET titulo = :titulo,
                    subtitulo = :subtitulo,
                    autores = :autores,
                    resumen_es = :resumen_es,
                    abstract_en = :abstract_en,
                    palabras_clave = :palabras_clave,
                    keywords = :keywords,
                    contenido_json = :contenido_json,
                    palabras_totales = :palabras_totales,
                    paginas_estimadas = :paginas_estimadas,
                    estilo_citas = :estilo_citas,
                    plantilla = :plantilla,
                    ultimo_autoguardado = CURRENT_TIMESTAMP
                WHERE id = :id AND user_id = :user_id
            """)
            
            db.session.execute(query, {
                'id': datos['id'],
                'user_id': current_user.id,
                'titulo': datos['titulo'],
                'subtitulo': datos.get('subtitulo', ''),
                'autores': autores_json,
                'resumen_es': datos.get('resumen_es', ''),
                'abstract_en': datos.get('abstract_en', ''),
                'palabras_clave': palabras_clave_json,
                'keywords': keywords_json,
                'contenido_json': contenido_json,
                'palabras_totales': palabras_totales,
                'paginas_estimadas': paginas_estimadas,
                'estilo_citas': datos.get('estilo_citas', 'chicago'),
                'plantilla': datos.get('plantilla', 'janus')
            })
            db.session.commit()

            # Actualizar referencias vinculadas: eliminar anteriores e insertar nuevas
            try:
                db.session.execute(
                    text("DELETE FROM articulos_referencias WHERE articulo_id = :id"),
                    {'id': datos['id']}
                )
                orden = 1
                for noticia_id in referencias_list:
                    db.session.execute(
                        text("INSERT INTO articulos_referencias (articulo_id, noticia_id, orden_aparicion) VALUES (:articulo_id, :noticia_id, :orden)"),
                        {'articulo_id': datos['id'], 'noticia_id': noticia_id, 'orden': orden}
                    )
                    orden += 1
                db.session.commit()
            except Exception:
                db.session.rollback()
            
            return jsonify({
                'success': True,
                'id': datos['id'],
                'mensaje': 'Artículo actualizado correctamente'
            })
        
        else:
            # CREAR nuevo artículo
            query = text("""
                INSERT INTO articulos_cientificos 
                (user_id, proyecto_id, titulo, subtitulo, autores, resumen_es, 
                 abstract_en, palabras_clave, keywords, contenido_json, 
                 palabras_totales, paginas_estimadas, estilo_citas, plantilla, estado)
                VALUES 
                (:user_id, :proyecto_id, :titulo, :subtitulo, :autores, :resumen_es,
                 :abstract_en, :palabras_clave, :keywords, :contenido_json,
                 :palabras_totales, :paginas_estimadas, :estilo_citas, :plantilla, 'borrador')
            """)
            
            # CREAR artículo y obtener id
            # Usar RETURNING id para compatibilidad con Postgres
            insert_query = text("""
                INSERT INTO articulos_cientificos 
                (user_id, proyecto_id, titulo, subtitulo, autores, resumen_es, 
                 abstract_en, palabras_clave, keywords, contenido_json, 
                 palabras_totales, paginas_estimadas, estilo_citas, plantilla, estado)
                VALUES 
                (:user_id, :proyecto_id, :titulo, :subtitulo, :autores, :resumen_es,
                 :abstract_en, :palabras_clave, :keywords, :contenido_json,
                 :palabras_totales, :paginas_estimadas, :estilo_citas, :plantilla, 'borrador')
                RETURNING id
            """)

            result = db.session.execute(insert_query, {
                'user_id': current_user.id,
                'proyecto_id': proyecto_id,
                'titulo': datos['titulo'],
                'subtitulo': datos.get('subtitulo', ''),
                'autores': autores_json,
                'resumen_es': datos.get('resumen_es', ''),
                'abstract_en': datos.get('abstract_en', ''),
                'palabras_clave': palabras_clave_json,
                'keywords': keywords_json,
                'contenido_json': contenido_json,
                'palabras_totales': palabras_totales,
                'paginas_estimadas': paginas_estimadas,
                'estilo_citas': datos.get('estilo_citas', 'chicago'),
                'plantilla': datos.get('plantilla', 'janus')
            })
            db.session.commit()
            # Obtener el ID insertado (RETURNING)
            try:
                nuevo_id = result.fetchone()[0]
            except Exception:
                nuevo_id = None

            # Insertar referencias vinculadas
            try:
                orden = 1
                for noticia_id in referencias_list:
                    db.session.execute(
                        text("INSERT INTO articulos_referencias (articulo_id, noticia_id, orden_aparicion) VALUES (:articulo_id, :noticia_id, :orden)"),
                        {'articulo_id': nuevo_id, 'noticia_id': noticia_id, 'orden': orden}
                    )
                    orden += 1
                db.session.commit()
            except Exception:
                db.session.rollback()

            return jsonify({
                'success': True,
                'id': nuevo_id,
                'mensaje': 'Artículo creado correctamente'
            })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@app.route("/api/articulos/<int:articulo_id>/cambiar-estado", methods=['POST'])
@csrf.exempt
@login_required
def api_articulo_cambiar_estado(articulo_id):
    """Cambiar estado del artículo (borrador, revision, finalizado, publicado)"""
    try:
        datos = request.get_json()
        nuevo_estado = datos.get('estado')
        
        if nuevo_estado not in ['borrador', 'revision', 'finalizado', 'publicado']:
            return jsonify({'error': 'Estado no válido'}), 400
        
        # Verificar propiedad
        articulo = db.session.execute(
            text("SELECT user_id FROM articulos_cientificos WHERE id = :id"),
            {'id': articulo_id}
        ).fetchone()
        
        if not articulo or articulo.user_id != current_user.id:
            return jsonify({'error': 'No autorizado'}), 403
        
        # Actualizar estado
        query = text("""
            UPDATE articulos_cientificos 
            SET estado = :estado,
                fecha_publicacion = CASE WHEN :estado = 'publicado' THEN CURRENT_DATE ELSE fecha_publicacion END
            WHERE id = :id
        """)
        
        db.session.execute(query, {'id': articulo_id, 'estado': nuevo_estado})
        db.session.commit()
        
        return jsonify({'success': True, 'estado': nuevo_estado})
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@app.route("/api/articulos/<int:articulo_id>/eliminar", methods=['DELETE'])
@login_required
def api_articulo_eliminar(articulo_id):
    """Eliminar artículo"""
    try:
        # Verificar propiedad
        articulo = db.session.execute(
            text("SELECT user_id FROM articulos_cientificos WHERE id = :id"),
            {'id': articulo_id}
        ).fetchone()
        
        if not articulo or articulo.user_id != current_user.id:
            return jsonify({'error': 'No autorizado'}), 403
        
        # Eliminar (CASCADE eliminará referencias y versiones)
        db.session.execute(
            text("DELETE FROM articulos_cientificos WHERE id = :id"),
            {'id': articulo_id}
        )
        db.session.commit()
        
        return jsonify({'success': True})
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@app.route("/api/proyectos/<int:proyecto_id>/noticias")
@login_required
def api_proyecto_noticias(proyecto_id):
    """Obtener todas las noticias del proyecto para referencias"""
    proyecto = Proyecto.query.get_or_404(proyecto_id)
    
    if proyecto.user_id != current_user.id:
        return jsonify({'error': 'No autorizado'}), 403
    
    # Nota: la tabla 'noticias' puede no existir en esta base; usamos la tabla 'prensa'
    # Solo devolver referencias marcadas como incluidas en el estudio
    noticias = db.session.execute(
        text("""
            SELECT id, titulo, publicacion as medio, fecha_original as fecha, autor, url,
                   numero_referencia, incluido, es_referencia
            FROM prensa
            WHERE proyecto_id = :proyecto_id AND incluido = true
            ORDER BY fecha_original DESC
        """),
        {'proyecto_id': proyecto_id}
    ).fetchall()

    return jsonify([{
        'id': n.id,
        'titulo': n.titulo,
        'medio': n.medio,
        'fecha': n.fecha,
        'autor': n.autor,
        'url': n.url,
        'numero_referencia': getattr(n, 'numero_referencia', None),
        'incluido': n.incluido,
        'es_referencia': n.es_referencia
    } for n in noticias])


@app.route("/api/proyectos/<int:proyecto_id>/referencias")
@login_required
def api_proyecto_referencias(proyecto_id):
    """Obtener todas las referencias del proyecto ordenadas por número bibliográfico"""
    try:
        with open("/tmp/error_referencias.log", "a") as f:
            f.write(f"\n--- API Call for project {proyecto_id} at {datetime.now()} ---\n")
            f.write(f"User: {current_user}\n")
            if current_user.is_authenticated:
                f.write(f"User ID: {current_user.id}\n")
            
        proyecto = Proyecto.query.get_or_404(proyecto_id)
        if proyecto.user_id != current_user.id:
            with open("/tmp/error_referencias.log", "a") as f:
                f.write(f"Access Denied: Project Owner {proyecto.user_id} vs Current User {current_user.id}\n")
            return jsonify({'error': 'No autorizado'}), 403

        referencias = Prensa.query.filter(
            Prensa.proyecto_id == proyecto_id,
            db.or_(
                Prensa.es_referencia == True,
                Prensa.numero_referencia.isnot(None)
            )
        ).order_by(
            Prensa.numero_referencia.asc(), 
            Prensa.fecha_original.asc()
        ).all()

        with open("/tmp/error_referencias.log", "a") as f:
            f.write(f"Found {len(referencias)} records\n")

        data = []
        for r in referencias:
            try:
                item = {
                    'id': r.id,
                    'titulo': r.titulo or "(Sin título)",
                    'medio': r.publicacion or "",
                    'fecha': r.fecha_original or "",
                    'autor': r.autor or "Anónimo",
                    'url': r.url or "",
                    'numero_referencia': r.numero_referencia
                }
                data.append(item)
            except Exception as e_inner:
                with open("/tmp/error_referencias.log", "a") as f:
                    f.write(f"Error processing record ID {r.id}: {str(e_inner)}\n")
                raise e_inner

        with open("/tmp/error_referencias.log", "a") as f:
            f.write(f"Returning {len(data)} items\n")
            
        return jsonify(data)
    except Exception as e:
        import traceback
        with open("/tmp/error_referencias.log", "a") as f:
            f.write(f"\n--- ERROR at {datetime.now()} ---\n")
            f.write(str(e) + "\n")
            f.write(traceback.format_exc() + "\n")
        return jsonify({'error': str(e)}), 500


@app.route("/articulos/<int:articulo_id>/duplicar")
@login_required
def articulo_duplicar(articulo_id):
    """Duplicar artículo existente"""
    try:
        # Obtener artículo original
        original = db.session.execute(
            text("SELECT * FROM articulos_cientificos WHERE id = :id"),
            {'id': articulo_id}
        ).fetchone()
        
        if not original or original.user_id != current_user.id:
            flash("No tienes acceso a este artículo", "danger")
            return redirect(url_for("home"))
        
        # Crear copia
        query = text("""
            INSERT INTO articulos_cientificos 
            (user_id, proyecto_id, titulo, subtitulo, autores, instituciones,
             resumen_es, abstract_en, palabras_clave, keywords, contenido_json,
             estado, plantilla, estilo_citas, idioma_principal)
            VALUES 
            (:user_id, :proyecto_id, :titulo, :subtitulo, :autores, :instituciones,
             :resumen_es, :abstract_en, :palabras_clave, :keywords, :contenido_json,
             'borrador', :plantilla, :estilo_citas, :idioma_principal)
            RETURNING id
        """)
        result = db.session.execute(query, {
            'user_id': current_user.id,
            'proyecto_id': original.proyecto_id,
            'titulo': f"[COPIA] {original.titulo}",
            'subtitulo': original.subtitulo,
            'autores': original.autores,
            'instituciones': original.instituciones,
            'resumen_es': original.resumen_es,
            'abstract_en': original.abstract_en,
            'palabras_clave': original.palabras_clave,
            'keywords': original.keywords,
            'contenido_json': original.contenido_json,
            'plantilla': original.plantilla,
            'estilo_citas': original.estilo_citas,
            'idioma_principal': original.idioma_principal
        })
        db.session.commit()
        nuevo_id = result.scalar()
        flash("Artículo duplicado correctamente", "success")
        return redirect(url_for('articulo_editar', articulo_id=nuevo_id))
    
    except Exception as e:
        db.session.rollback()
        flash(f"Error al duplicar artículo: {str(e)}", "danger")
        return redirect(url_for('articulos_lista', proyecto_id=original.proyecto_id))


def calcular_palabras_totales(secciones):
    """Calcular total de palabras en todas las secciones, manejando tanto listas como diccionarios"""
    total = 0
    if not secciones:
        return 0
        
    # Si es un diccionario (el nuevo formato del editor)
    if isinstance(secciones, dict):
        for contenido_html in secciones.values():
            if contenido_html:
                # Quitar HTML tags y contar palabras
                texto_plano = re.sub(r'<[^>]+>', '', str(contenido_html))
                palabras = len([p for p in texto_plano.split() if p.strip()])
                total += palabras
                
    # Si es una lista (formato antiguo o de otros módulos)
    elif isinstance(secciones, list):
        for seccion in secciones:
            contenido_html = ''
            if isinstance(seccion, dict):
                contenido_html = seccion.get('contenido_html', '') or seccion.get('contenido', '')
            else:
                contenido_html = str(seccion)
                
            if contenido_html:
                texto_plano = re.sub(r'<[^>]+>', '', contenido_html)
                palabras = len([p for p in texto_plano.split() if p.strip()])
                total += palabras
        
    return total


# =========================================================
# 📄 EXPORTACIÓN DE NOTICIAS A PDF
# =========================================================
@app.route("/noticias/<int:noticia_id>/pdf")
@login_required
def noticia_exportar_pdf(noticia_id):
    """Generar y descargar PDF de una noticia de prensa"""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
        from reportlab.lib import colors
        from io import BytesIO
        
        # Obtener la noticia
        noticia = Prensa.query.get_or_404(noticia_id)
        
        # Verificar que pertenece al proyecto del usuario
        if noticia.proyecto_id not in [p.id for p in current_user.proyectos]:
            flash("No tienes acceso a esta noticia", "danger")
            return redirect(url_for("home"))
        
        # Crear buffer para PDF
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm
        )
        
        # Estilos
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(
            name='TituloNoticia',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=12,
            textColor=colors.HexColor('#1a1a1a'),
            alignment=TA_CENTER
        ))
        styles.add(ParagraphStyle(
            name='MetaDatos',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#666666'),
            spaceAfter=6
        ))
        styles.add(ParagraphStyle(
            name='Contenido',
            parent=styles['Normal'],
            fontSize=11,
            leading=16,
            alignment=TA_JUSTIFY,
            spaceAfter=12
        ))
        styles.add(ParagraphStyle(
            name='Seccion',
            parent=styles['Heading2'],
            fontSize=12,
            spaceBefore=12,
            spaceAfter=6,
            textColor=colors.HexColor('#ff9800')
        ))
        
        story = []

        # Logo HesiOX
        logo_path = os.path.join(app.root_path, "static", "img", "hesiox_logo2.png")
        if os.path.exists(logo_path):
            story.append(Image(logo_path, width=4*cm, height=5.5*cm))
            story.append(Spacer(1, 0.5*cm))
        
        # Título
        titulo = noticia.titulo or "Sin título"
        story.append(Paragraph(_safe_text(titulo), styles['TituloNoticia']))
        story.append(Spacer(1, 0.5*cm))
        
        # Metadatos en tabla
        meta_data = []
        if noticia.publicacion:
            meta_data.append(['Publicación:', _safe_text(noticia.publicacion)])
        if noticia.fecha_original:
            meta_data.append(['Fecha:', _safe_text(noticia.fecha_original)])
        if noticia.ciudad:
            meta_data.append(['Ciudad:', _safe_text(noticia.ciudad)])
        if noticia.pais_publicacion:
            meta_data.append(['País:', _safe_text(noticia.pais_publicacion)])
        if noticia.nombre_autor or noticia.apellido_autor:
            autor = f"{noticia.nombre_autor or ''} {noticia.apellido_autor or ''}".strip()
            meta_data.append(['Autor:', _safe_text(autor)])
        if noticia.seccion:
            meta_data.append(['Sección:', _safe_text(noticia.seccion)])
        if noticia.pagina_inicio:
            paginas = str(noticia.pagina_inicio)
            if noticia.pagina_fin:
                paginas += f"-{noticia.pagina_fin}"
            meta_data.append(['Páginas:', _safe_text(paginas)])
        
        if meta_data:
            meta_table = Table(meta_data, colWidths=[3*cm, 13*cm])
            meta_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#666666')),
                ('TEXTCOLOR', (1, 0), (1, -1), colors.HexColor('#333333')),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ]))
            story.append(meta_table)
            story.append(Spacer(1, 0.5*cm))
        
        # Línea separadora
        story.append(Paragraph('<hr/>', styles['Normal']))
        story.append(Spacer(1, 0.3*cm))
        
        # Contenido principal
        if noticia.contenido:
            story.append(Paragraph("Contenido", styles['Seccion']))
            story.append(Paragraph(_safe_text_with_breaks(noticia.contenido), styles['Contenido']))
        
        # Texto original (si existe)
        if noticia.texto_original:
            story.append(Spacer(1, 0.5*cm))
            story.append(Paragraph("Texto Original", styles['Seccion']))
            story.append(Paragraph(_safe_text_with_breaks(noticia.texto_original), styles['Contenido']))
        
        # Resumen (si existe)
        if noticia.resumen:
            story.append(Spacer(1, 0.5*cm))
            story.append(Paragraph("Resumen", styles['Seccion']))
            story.append(Paragraph(_safe_text_with_breaks(noticia.resumen), styles['Contenido']))
        
        # Notas (si existen)
        if noticia.notas:
            story.append(Spacer(1, 0.5*cm))
            story.append(Paragraph("Notas", styles['Seccion']))
            story.append(Paragraph(_safe_text_with_breaks(noticia.notas), styles['Contenido']))
        
        # Palabras clave
        if noticia.palabras_clave:
            story.append(Spacer(1, 0.5*cm))
            story.append(Paragraph("Palabras clave", styles['Seccion']))
            story.append(Paragraph(_safe_text_with_breaks(noticia.palabras_clave), styles['Contenido']))
        
        # URL de la fuente
        if noticia.url:
            story.append(Spacer(1, 0.5*cm))
            story.append(Paragraph("Fuente", styles['Seccion']))
            story.append(Paragraph(f'<link href="{noticia.url}">{noticia.url}</link>', styles['MetaDatos']))
        
        # Generar PDF
        doc.build(story)
        buffer.seek(0)
        
        # Nombre del archivo
        titulo_limpio = re.sub(r'[^\w\s-]', '', titulo)[:40]
        filename = f"noticia_{titulo_limpio}_{datetime.now().strftime('%Y%m%d')}.pdf"
        
        return send_file(
            buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        flash(f"Error al generar PDF: {str(e)}", "danger")
        return redirect(url_for('noticias.listar_noticias'))


# =========================================================
# 📄 EXPORTACIÓN DE ARTÍCULOS A PDF
# =========================================================
@app.route("/articulos/<int:articulo_id>/pdf")
@login_required
def articulo_exportar_pdf(articulo_id):
    """Generar y descargar PDF del artículo"""
    try:
        from pdf_generator import generar_pdf_articulo
        
        # Obtener datos del artículo
        articulo_data = db.session.execute(
            text("SELECT * FROM articulos_cientificos WHERE id = :id"),
            {'id': articulo_id}
        ).fetchone()
        
        if not articulo_data or articulo_data.user_id != current_user.id:
            flash("No tienes acceso a este artículo", "danger")
            return redirect(url_for("home"))
        
        # Convertir a diccionario y parsear JSON
        articulo = dict(articulo_data._mapping)
        articulo['autores'] = json.loads(articulo.get('autores', '[]'))
        articulo['palabras_clave'] = json.loads(articulo.get('palabras_clave', '[]'))
        articulo['keywords'] = json.loads(articulo.get('keywords', '[]'))
        articulo['contenido_json'] = json.loads(articulo.get('contenido_json', '{}'))
        
        # Obtener referencias vinculadas
        referencias_ids = db.session.execute(
            text("""
                SELECT DISTINCT noticia_id 
                FROM articulos_referencias 
                WHERE articulo_id = :id
                ORDER BY orden_aparicion
            """),
            {'id': articulo_id}
        ).fetchall()
        
        noticias_referencias = []
        for ref_id in referencias_ids:
            noticia = db.session.execute(
                text("SELECT * FROM noticias WHERE id = :id"),
                {'id': ref_id.noticia_id}
            ).fetchone()
            if noticia:
                noticias_referencias.append(dict(noticia._mapping))
        
        # Generar PDF
        plantilla = articulo.get('plantilla', 'janus')
        pdf_buffer = generar_pdf_articulo(articulo, noticias_referencias, plantilla)
        
        # Crear nombre de archivo
        titulo_limpio = re.sub(r'[^\w\s-]', '', articulo['titulo'])[:50]
        filename = f"{titulo_limpio}_{datetime.now().strftime('%Y%m%d')}.pdf"
        
        return send_file(
            pdf_buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )
    
    except Exception as e:
        flash(f"Error al generar PDF: {str(e)}", "danger")
        return redirect(url_for('articulo_editar', articulo_id=articulo_id))


@app.route("/articulos/<int:articulo_id>/preview")
@login_required
def articulo_preview_pdf(articulo_id):
    """Vista previa del PDF en el navegador"""
    try:
        from flask import current_app, abort
        from pdf_generator import generar_pdf_articulo
        
        # Obtener datos (mismo código que exportar_pdf pero sin as_attachment)
        articulo_data = db.session.execute(
            text("SELECT * FROM articulos_cientificos WHERE id = :id"),
            {'id': articulo_id}
        ).fetchone()
        
        if not articulo_data:
            return abort(404, "Artículo no encontrado")
        
        
        # Mapear la tupla a un dict usando los nombres de columna
        columnas = [
            'id', 'user_id', 'proyecto_id', 'titulo', 'subtitulo', 'autores', 'coautores', 'fecha', 'resumen',
            'abstract', 'palabras_clave', 'keywords', 'contenido_json', 'estado', 'publicacion_id', 'es_publico',
            'es_destacado', 'plantilla', 'formato_cita', 'idioma', 'doi', 'issn', 'isbn', 'url', 'archivo', 'imagen',
            'fecha_creacion', 'fecha_modificacion', 'fecha_revision', 'fecha_publicacion'
        ]
        
        # Convertir articulo_data a diccionario de manera segura
        articulo = None
        if hasattr(articulo_data, '_mapping'):
            # SQLAlchemy Row object con _mapping
            articulo = dict(articulo_data._mapping)
        elif isinstance(articulo_data, dict):
            # Ya es un diccionario
            articulo = articulo_data
        elif isinstance(articulo_data, (tuple, list)):
            # Es una tupla o lista, mapear a columnas
            articulo = dict(zip(columnas, articulo_data))
        else:
            return f"Error: El resultado de la consulta no es un artículo válido. Tipo: {type(articulo_data)}", 500
        

        # AHORA verificar user_id con el artículo ya convertido a dict
        if articulo.get('user_id') != current_user.id:
            return abort(403, "No tiene permiso para ver este artículo")

        def ensure_json(val, default):
            if isinstance(val, (list, dict)):
                return val
            try:
                return json.loads(val) if val else default
            except Exception:
                return default

        # Ahora ya podemos usar .get() de manera segura
        articulo['autores'] = ensure_json(articulo.get('autores', '[]'), [])
        articulo['palabras_clave'] = ensure_json(articulo.get('palabras_clave', '[]'), [])
        articulo['keywords'] = ensure_json(articulo.get('keywords', '[]'), [])
        
        # Manejo especial para contenido_json: asegurar que sea un dict con 'secciones'
        contenido_raw = ensure_json(articulo.get('contenido_json', '{}'), {})
        if isinstance(contenido_raw, list):
            # Si es una lista, envolverla en la estructura esperada
            articulo['contenido_json'] = {'secciones': contenido_raw}
        elif isinstance(contenido_raw, dict):
            # Si es un dict pero no tiene 'secciones', asumimos que ES la lista de secciones
            if 'secciones' not in contenido_raw and contenido_raw:
                articulo['contenido_json'] = {'secciones': [contenido_raw]}
            else:
                articulo['contenido_json'] = contenido_raw
        else:
            articulo['contenido_json'] = {'secciones': []}
        
        referencias_ids = db.session.execute(
            text("SELECT DISTINCT noticia_id FROM articulos_referencias WHERE articulo_id = :id"),
            {'id': articulo_id}
        ).fetchall()
        
        noticias_referencias = []
        for ref_id in referencias_ids:
            noticia = db.session.execute(
                text("SELECT * FROM noticias WHERE id = :id"),
                {'id': ref_id.noticia_id}
            ).fetchone()
            if noticia:
                noticias_referencias.append(dict(noticia._mapping))
        
        
        plantilla = articulo.get('plantilla', 'janus')
        pdf_buffer = generar_pdf_articulo(articulo, noticias_referencias, plantilla)
        
        return send_file(
            pdf_buffer,
            mimetype='application/pdf',
            as_attachment=False
        )
    
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        current_app.logger.error(f"Error en preview de artículo {articulo_id}: {str(e)}")
        current_app.logger.error(f"Traceback completo:\n{error_trace}")
        return f"Error al generar vista previa: {str(e)}<br><br><pre>{error_trace}</pre>", 500


# =========================================================
# 🖼️ GESTIÓN DE FIGURAS Y TABLAS
# =========================================================
@app.route("/articulos/<int:articulo_id>/figuras")
@login_required
def articulo_figuras(articulo_id):
    """Gestión de figuras, tablas y gráficos del artículo"""
    articulo_data = db.session.execute(
        text("SELECT * FROM articulos_cientificos WHERE id = :id"),
        {'id': articulo_id}
    ).fetchone()
    
    if not articulo_data or articulo_data.user_id != current_user.id:
        flash("No tienes acceso a este artículo", "danger")
        return redirect(url_for("home"))
    
    articulo = dict(articulo_data._mapping)
    
    # Obtener figuras del artículo
    figuras = db.session.execute(
        text("""
            SELECT * FROM articulos_figuras 
            WHERE articulo_id = :id 
            ORDER BY tipo, numero
        """),
        {'id': articulo_id}
    ).fetchall()
    
    figuras_list = [dict(f._mapping) for f in figuras]
    
    return render_template('articulo_figuras.html', 
                         articulo=articulo, 
                         figuras=figuras_list)


@app.route("/api/articulos/figuras/subir", methods=['POST'])
@csrf.exempt
@login_required
def api_figura_subir():
    """Subir nueva figura/tabla al artículo"""
    try:
        articulo_id = request.form.get('articulo_id')
        
        # Verificar acceso
        articulo = db.session.execute(
            text("SELECT user_id FROM articulos_cientificos WHERE id = :id"),
            {'id': articulo_id}
        ).fetchone()
        
        if not articulo or articulo.user_id != current_user.id:
            return jsonify({'error': 'No autorizado'}), 403
        
        # Procesar archivo
        if 'archivo' not in request.files:
            return jsonify({'error': 'No se recibió archivo'}), 400
        
        archivo = request.files['archivo']
        if archivo.filename == '':
            return jsonify({'error': 'Archivo vacío'}), 400
        
        if archivo and allowed_file(archivo.filename):
            # Guardar archivo
            filename = f"figura_{articulo_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{archivo.filename}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            archivo.save(filepath)
            
            # Obtener siguiente número para este tipo
            tipo = request.form.get('tipo', 'figura')
            ultimo_numero = db.session.execute(
                text("""
                    SELECT MAX(numero) as max_num 
                    FROM articulos_figuras 
                    WHERE articulo_id = :id AND tipo = :tipo
                """),
                {'id': articulo_id, 'tipo': tipo}
            ).fetchone()
            
            siguiente_numero = (ultimo_numero.max_num or 0) + 1
            
            # Insertar en BD
            query = text("""
                INSERT INTO articulos_figuras 
                (articulo_id, tipo, numero, titulo, descripcion, archivo_ruta, creditos)
                VALUES 
                (:articulo_id, :tipo, :numero, :titulo, :descripcion, :archivo_ruta, :creditos)
            """)
            
            db.session.execute(query, {
                'articulo_id': articulo_id,
                'tipo': tipo,
                'numero': siguiente_numero,
                'titulo': request.form.get('titulo', ''),
                'descripcion': request.form.get('descripcion', ''),
                'archivo_ruta': url_for('static', filename=f'uploads/{filename}'),
                'creditos': request.form.get('creditos', '')
            })
            db.session.commit()
            
            return jsonify({
                'success': True,
                'mensaje': f'{tipo.capitalize()} {siguiente_numero} agregada correctamente'
            })
        
        return jsonify({'error': 'Tipo de archivo no permitido'}), 400
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@app.route("/api/articulos/figuras/<int:figura_id>/eliminar", methods=['DELETE'])
@login_required
def api_figura_eliminar(figura_id):
    """Eliminar figura del artículo"""
    try:
        # Verificar propiedad a través del artículo
        figura = db.session.execute(
            text("""
                SELECT f.*, a.user_id 
                FROM articulos_figuras f
                JOIN articulos_cientificos a ON f.articulo_id = a.id
                WHERE f.id = :id
            """),
            {'id': figura_id}
        ).fetchone()
        
        if not figura or figura.user_id != current_user.id:
            return jsonify({'error': 'No autorizado'}), 403
        
        # Eliminar archivo físico
        if figura.archivo_ruta:
            try:
                filepath = figura.archivo_ruta.replace('/static/', '')
                full_path = os.path.join('static', filepath)
                if os.path.exists(full_path):
                    os.remove(full_path)
            except:
                pass
        
        # Eliminar de BD
        db.session.execute(
            text("DELETE FROM articulos_figuras WHERE id = :id"),
            {'id': figura_id}
        )
        db.session.commit()
        
        return jsonify({'success': True})
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# =========================================================
# 🤝 SISTEMA DE COLABORACIÓN EN ARTÍCULOS
# =========================================================
@app.route("/articulos/<int:articulo_id>/colaboradores")
@login_required
def articulo_colaboradores(articulo_id):
    """Gestión de colaboradores del artículo"""
    articulo_data = db.session.execute(
        text("SELECT * FROM articulos_cientificos WHERE id = :id"),
        {'id': articulo_id}
    ).fetchone()
    
    if not articulo_data or articulo_data.user_id != current_user.id:
        flash("Solo el autor principal puede gestionar colaboradores", "danger")
        return redirect(url_for("home"))
    
    # 1. Recuperamos el objeto Proyecto usando el ID guardado en el artículo (ESTO FALTABA)
    proyecto = Proyecto.query.get(articulo_data.proyecto_id)

    articulo = dict(articulo_data._mapping)
    
    # Obtener coautores actuales (Manejo de NULL corregido)
    coautores_ids = json.loads(articulo.get('coautores') or '[]')
    
    coautores = []
    for user_id in coautores_ids:
        user = Usuario.query.get(user_id)
        if user:
            coautores.append(user)
    
    # Obtener comentarios de revisión (Manejo de NULL corregido)
    comentarios = json.loads(articulo.get('comentarios_revision') or '[]')
    
    return render_template('articulo_colaboradores.html',
                         articulo=articulo,
                         proyecto=proyecto,  # 2. Enviamos la variable 'proyecto' a la plantilla
                         coautores=coautores,
                         comentarios=comentarios)
@app.route("/api/articulos/<int:articulo_id>/agregar-colaborador", methods=['POST'])
@csrf.exempt
@login_required
def api_agregar_colaborador(articulo_id):
    """Agregar colaborador al artículo"""
    try:
        datos = request.get_json()
        email_colaborador = datos.get('email')
        
        # Verificar que el usuario actual es el autor
        articulo = db.session.execute(
            text("SELECT user_id, coautores FROM articulos_cientificos WHERE id = :id"),
            {'id': articulo_id}
        ).fetchone()
        
        if not articulo or articulo.user_id != current_user.id:
            return jsonify({'error': 'No autorizado'}), 403
        
        # Buscar usuario por email
        colaborador = Usuario.query.filter_by(email=email_colaborador).first()
        if not colaborador:
            return jsonify({'error': 'Usuario no encontrado'}), 404
        
        # Agregar a lista de coautores
        coautores = json.loads(articulo.coautores) if articulo.coautores else []
        if colaborador.id not in coautores:
            coautores.append(colaborador.id)
            
            db.session.execute(
                text("UPDATE articulos_cientificos SET coautores = :coautores WHERE id = :id"),
                {'id': articulo_id, 'coautores': json.dumps(coautores)}
            )
            db.session.commit()
            
            return jsonify({
                'success': True,
                'mensaje': f'{colaborador.username} agregado como colaborador'
            })
        
        return jsonify({'error': 'Ya es colaborador'}), 400
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@app.route("/api/articulos/<int:articulo_id>/comentario", methods=['POST'])
@csrf.exempt
@login_required
def api_agregar_comentario(articulo_id):
    """Agregar comentario de revisión al artículo"""
    try:
        datos = request.get_json()
        texto = datos.get('texto')
        seccion = datos.get('seccion', 'general')
        
        # Verificar acceso (autor o coautor)
        articulo = db.session.execute(
            text("SELECT user_id, coautores, comentarios_revision FROM articulos_cientificos WHERE id = :id"),
            {'id': articulo_id}
        ).fetchone()
        
        if not articulo:
            return jsonify({'error': 'Artículo no encontrado'}), 404
        
        coautores = json.loads(articulo.coautores) if articulo.coautores else []
        if articulo.user_id != current_user.id and current_user.id not in coautores:
            return jsonify({'error': 'No autorizado'}), 403
        
        # Agregar comentario
        comentarios = json.loads(articulo.comentarios_revision) if articulo.comentarios_revision else []
        nuevo_comentario = {
            'id': len(comentarios) + 1,
            'user_id': current_user.id,
            'username': current_user.username,
            'texto': texto,
            'seccion': seccion,
            'fecha': datetime.now().isoformat(),
            'resuelto': False
        }
        comentarios.append(nuevo_comentario)
        
        db.session.execute(
            text("UPDATE articulos_cientificos SET comentarios_revision = :comentarios WHERE id = :id"),
            {'id': articulo_id, 'comentarios': json.dumps(comentarios)}
        )
        db.session.commit()
        
        return jsonify({'success': True, 'comentario': nuevo_comentario})
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# =========================================================
# MAIN
# =========================================================
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        inicializar_buscador()
    app.run(debug=True)