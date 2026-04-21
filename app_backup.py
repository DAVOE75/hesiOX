import csv
import io
import json
import os
import re
from collections import Counter
from datetime import datetime
from io import BytesIO
from itertools import combinations
from urllib.parse import parse_qs, unquote, urlencode, urlparse

import networkx as nx
import numpy as np
from dotenv import load_dotenv
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
from flask_sqlalchemy import SQLAlchemy
from functools import wraps
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Importamos cast y String para solucionar el error de tipos en PostgreSQL
from sqlalchemy import String, cast, func, or_, text

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
)


# =========================================================
# CARGA DE VARIABLES DE ENTORNO
# =========================================================
load_dotenv()  # Carga el archivo .env si existe

app = Flask(__name__)

# ⚙️ CONFIGURACIÓN DE SEGURIDAD
app.secret_key = os.getenv(
    "SECRET_KEY", "bibliografia_sirio_secret_CAMBIAR_EN_PRODUCCION"
)

# ⚙️ CONFIGURACIÓN DE BASE DE DATOS POSTGRESQL
# Usa variable de entorno DATABASE_URL, con fallback a valor por defecto
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
    "DATABASE_URL", "postgresql://postgres:PASSWORD@localhost:5432/bibliografia_sirio"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# CONFIGURACIÓN DE CARPETA DE SUBIDAS (IMÁGENES)
UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", os.path.join("static", "uploads"))
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# Crear carpeta si no existe
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# =========================================================
# INICIALIZACIÓN DE EXTENSIONES
# =========================================================
from extensions import db, csrf

db.init_app(app)
csrf.init_app(app)

# NOTE: La línea 'db = SQLAlchemy(app)' que estaba aquí se movió a extensions.py
# y se inicializa con db.init_app(app) para evitar importaciones circulares

# Importar modelos DESPUÉS de inicializar db
from models import Usuario, Proyecto, Hemeroteca, Publicacion, Prensa, ImagenPrensa, GeoPlace

# 🔐 Configuración de Flask-Login
login_manager = LoginManager(app)
login_manager.login_view = "login"  # nombre de la ruta de login


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
    for v in valores_db:
        texto = str(v).strip()
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
            WHEN fecha_original ~ '^[0-3]?[0-9]/[0-1]?[0-9]/[0-9]{{2,4}}$'
            THEN (
                CASE
                    WHEN split_part(fecha_original, '/', 2)::int BETWEEN 1 AND 12
                        AND split_part(fecha_original, '/', 1)::int BETWEEN 1 AND 31
                        AND split_part(fecha_original, '/', 3)::int BETWEEN 1800 AND 2100
                    THEN to_date(fecha_original, 'DD/MM/YYYY')
                    ELSE NULL
                END
            )
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
from routes import all_blueprints

for blueprint in all_blueprints:
    app.register_blueprint(blueprint)

print("[OK] Blueprints registrados:", [bp.name for bp in all_blueprints])


# =========================================================
# RUTAS PRINCIPALES
# =========================================================
@app.route("/")
def home():
    """Página principal - redirige a dashboard si está logueado"""
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    return render_template("home.html")


@app.route("/dashboard")
@login_required
def dashboard():
    """Dashboard personalizado del usuario con estadísticas y accesos rápidos"""
    
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
    
    # Últimos artículos añadidos (últimos 5)
    ultimos_articulos = Prensa.query.join(Proyecto).filter(
        Proyecto.user_id == current_user.id
    ).order_by(Prensa.creado_en.desc()).limit(5).all()
    
    for articulo in ultimos_articulos:
        actividad_reciente.append({
            "tipo": "articulo_nuevo",
            "icono": "📄",
            "texto": f"Artículo añadido: \"{(articulo.titulo or 'Sin título')[:50]}...\"",
            "fecha": articulo.creado_en,
            "url": url_for("editar", id=articulo.id)
        })
    
    # Últimas publicaciones añadidas (últimas 3)
    ultimas_publicaciones = Publicacion.query.join(Proyecto).filter(
        Proyecto.user_id == current_user.id
    ).limit(3).all()
    
    for pub in ultimas_publicaciones:
        actividad_reciente.append({
            "tipo": "publicacion_nueva",
            "icono": "📚",
            "texto": f"Publicación: \"{(pub.nombre or 'Sin nombre')[:50]}...\"",
            "fecha": None,  # Publicacion no tiene campo de fecha
            "url": "#"  # Ajustar según tu ruta
        })
    
    # Ordenar por fecha descendente (manejar strings y None)
    def get_sort_key(item):
        fecha = item.get("fecha")
        if fecha is None:
            return ""
        if isinstance(fecha, str):
            return fecha
        return fecha.isoformat() if hasattr(fecha, 'isoformat') else str(fecha)
    
    actividad_reciente.sort(key=get_sort_key, reverse=True)
    actividad_reciente = actividad_reciente[:10]  # Solo las 10 más recientes
    
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
                         proyectos=proyectos)


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
    usuarios_recientes = Usuario.query.order_by(Usuario.creado_en.desc()).limit(5).all()
    actividad_sistema = []
    
    for u in usuarios_recientes:
        actividad_sistema.append({
            'tipo': 'Nuevo usuario',
            'fecha': u.creado_en,
            'icono': '👤',
            'descripcion': f'Usuario registrado'
        })
    
    # Últimos proyectos creados (sin ver contenido, solo fechas)
    proyectos_recientes = Proyecto.query.order_by(Proyecto.creado_en.desc()).limit(5).all()
    for p in proyectos_recientes:
        actividad_sistema.append({
            'tipo': 'Nuevo proyecto',
            'fecha': p.creado_en,
            'icono': '📁',
            'descripcion': f'Proyecto creado'
        })
    
    # Ordenar actividad por fecha
    actividad_sistema = sorted(actividad_sistema, key=lambda x: x['fecha'], reverse=True)[:10]
    
    return render_template("admin_panel.html",
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
                          # Gestión usuarios
                          usuarios=usuarios_data,
                          # Actividad
                          actividad_sistema=actividad_sistema)


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
    else:
        # Sin filtros, aplicar paginación normal
        por_pagina = 20
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

    return render_template(
        "list.html",
        registros=registros,
        proyecto=proyecto,  # Pasar proyecto al template
        total=total,
        page=page,
        total_paginas=total_paginas,
        inicio=inicio,
        fin=fin,
        autores=valores_unicos(Prensa.autor, proyecto.id),
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
    r = db.session.get(Prensa, id)
    if r:
        db.session.delete(r)
        db.session.commit()
        return jsonify({"success": True})
    return jsonify({"success": False, "message": "No encontrado"}), 404


# =========================================================
# BORRAR FICHA (VÍA FORMULARIO - REDIRECCIÓN + FLASH)
# =========================================================
@app.route("/borrar_ficha/<int:id>", methods=["POST"])
def borrar_ficha(id):
    registro = db.session.get(Prensa, id)
    if not registro:
        flash("❌ Registro no encontrado.", "danger")
    else:
        try:
            db.session.delete(registro)
            db.session.commit()
            flash("🗑️ Ficha eliminada correctamente.", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"⚠️ Error al eliminar: {e}", "warning")
    destino = normalizar_next(request.args.get("next")) or url_for("index")
    return redirect(destino)


@app.route("/actualizar_lote", methods=["POST"])
def actualizar_lote():
    data = request.get_json()
    ids = data.get("ids", [])
    updates = data.get("updates", {})

    if not ids or not updates:
        return jsonify({"success": False, "message": "Datos inválidos"}), 400

    # 1. ACTUALIZAR TABLA PRENSA (Campos normales)
    campos_prensa = [
        "tipo_recurso",
        "ciudad",
        "idioma",
        "fecha_consulta",
        "licencia",
        "formato_fuente",
        "pais_publicacion",
        "anio",
        "incluido",
        "fuente",
        "imagen_scan",
        "texto_original",
        "edicion",
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
            else:
                payload_prensa[getattr(Prensa, campo)] = val

    try:
        if payload_prensa:
            Prensa.query.filter(Prensa.id.in_(ids)).update(
                payload_prensa, synchronize_session="fetch"
            )

        # 2. ACTUALIZAR TABLA PUBLICACION (Descripción del medio)
        desc_pub = updates.get("descripcion_publicacion")
        if desc_pub:
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
                # Actualizamos la descripción en la tabla Publicacion
                Publicacion.query.filter(
                    Publicacion.id_publicacion.in_(lista_ids_pub)
                ).update(
                    {Publicacion.descripcion: desc_pub}, synchronize_session="fetch"
                )

        db.session.commit()
        flash(
            f"✅ Actualizados {len(ids)} registros y sus publicaciones asociadas.",
            "success",
        )
        return jsonify({"success": True})

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


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

        # Validar fecha_original
        valida, error_msg = validar_fecha_ddmmyyyy(fecha_original)
        if not valida:
            flash(f"⚠️ Fecha Original inválida: {error_msg}", "danger")
            # Re-render preservando datos del formulario
            idiomas = ["es", "it", "fr", "en", "pt", "ct"]
            tipos_autor = ["anónimo", "firmado", "corresponsal"]
            publicaciones = [
                p.nombre
                for p in Publicacion.query.order_by(Publicacion.nombre.asc()).all()
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
            temas = sorted(
                {
                    r.temas
                    for r in Prensa.query.filter(Prensa.temas.isnot(None))
                    if r.temas.strip()
                }
            )
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
                for p in Publicacion.query.order_by(Publicacion.nombre.asc()).all()
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
            temas = sorted(
                {
                    r.temas
                    for r in Prensa.query.filter(Prensa.temas.isnot(None))
                    if r.temas.strip()
                }
            )
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

        # 1. GESTIÓN DE AUTOR
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
            }

            for campo, valor in campos_pub.items():
                if valor and (getattr(pub, campo) is None or getattr(pub, campo) == ""):
                    setattr(pub, campo, valor)

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
            idioma=request.form.get("idioma"),
            tipo_autor=request.form.get("tipo_autor"),
            fuente_condiciones=request.form.get("fuente_condiciones"),
            temas=request.form.get("temas"),
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
        )
        db.session.add(nuevo)
        db.session.flush()  # Obtener ID del nuevo registro

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

    publicaciones = [
        p.nombre for p in Publicacion.query.order_by(Publicacion.nombre.asc()).all()
    ]
    ciudades = sorted(
        {
            *(
                p.ciudad
                for p in Publicacion.query.filter(Publicacion.ciudad.isnot(None))
            ),
            *(r.ciudad for r in Prensa.query.filter(Prensa.ciudad.isnot(None))),
        }
    )
    temas = sorted(
        {
            r.temas
            for r in Prensa.query.filter(Prensa.temas.isnot(None))
            if r.temas.strip()
        }
    )
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
# EDITAR NOTICIA / RECURSO
# =========================================================
@app.route("/editar/<int:id>", methods=["GET", "POST"])
def editar(id):
    ref = db.session.get(Prensa, id)
    if not ref:
        return abort(404)

    idiomas = ["es", "it", "fr", "en", "pt", "ct"]
    tipos_autor = ["anónimo", "firmado", "corresponsal"]

    publicaciones_lista = [
        p.nombre for p in Publicacion.query.order_by(Publicacion.nombre.asc()).all()
    ]

    if request.method == "POST":
        nombre = (request.form.get("nombre_autor") or "").strip()
        apellido = (request.form.get("apellido_autor") or "").strip()
        es_anonimo = "anonimo" in request.form

        # 🔒 CORRECCIÓN: Solo modificar autor si hay cambios explícitos
        if es_anonimo:
            ref.autor = None
        elif apellido or nombre:  # Solo actualizar si se proporcionó algún dato
            if apellido and nombre:
                ref.autor = f"{apellido}, {nombre}"
            elif apellido:
                ref.autor = apellido
            elif nombre:
                ref.autor = nombre
        # Si no se marca anónimo NI se proporciona nombre/apellido, mantener valor original

        nombre_pub = (request.form.get("publicacion") or "").strip()
        pub = None
        if nombre_pub:
            pub = Publicacion.query.filter_by(nombre=nombre_pub).first()
            if not pub:
                pub = Publicacion(nombre=nombre_pub)
                db.session.add(pub)

            campos_pub = {
                "descripcion": request.form.get("descripcion_publicacion"),
                "tipo_recurso": request.form.get("tipo_recurso"),
                "ciudad": request.form.get("ciudad"),
                "idioma": request.form.get("idioma"),
                "licencia": request.form.get("licencia"),
                "formato_fuente": request.form.get("formato_fuente"),
                "pais_publicacion": request.form.get("pais_publicacion"),
            }
            for campo, valor in campos_pub.items():
                if valor is not None:
                    setattr(pub, campo, valor)

            db.session.flush()

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
        ]
        for campo in campo_map:
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

        # Validar fecha_original
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
        pub = Publicacion.query.filter_by(nombre=ref.publicacion).first()
        if pub and pub.descripcion:
            descripcion_medio = pub.descripcion

    setattr(ref, "descripcion_publicacion", descripcion_medio)

    return render_template(
        "editar.html",
        ref=ref,
        idiomas=idiomas,
        tipos_autor=tipos_autor,
        publicaciones=publicaciones_lista,
        next_url=normalizar_next(request.args.get("next")),
        nombre_autor_val=nombre_autor_val,
        apellido_autor_val=apellido_autor_val,
    )


# =========================================================
# CONSISTENCIA DE DATOS (LA RUTA QUE FALTABA ANTES)
# =========================================================
@app.route("/consistencia")
def consistencia_datos():
    # ===== 1. DUPLICADOS EXACTOS DE CONTENIDO =====
    subquery_dups = (
        db.session.query(Prensa.contenido)
        .filter(Prensa.contenido.isnot(None), Prensa.contenido != "")
        .group_by(Prensa.contenido)
        .having(func.count(Prensa.contenido) > 1)
        .all()
    )
    duplicate_contents = [c[0] for c in subquery_dups]

    registros_duplicados_contenido = (
        db.session.query(Prensa)
        .filter(Prensa.contenido.in_(duplicate_contents))
        .order_by(Prensa.contenido, Prensa.publicacion)
        .all()
    )

    # ===== 2. DUPLICADOS INTELIGENTES (Título + Fecha + Publicación) =====
    # Analiza TODOS los registros (puede tardar varios minutos)
    todos_registros = Prensa.query.order_by(Prensa.id.desc()).all()
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
    sin_anio = Prensa.query.filter(Prensa.anio.is_(None)).all()
    sin_publicacion_enlazada = Prensa.query.filter(
        Prensa.id_publicacion.is_(None)
    ).all()

    prensa_sin_url = Prensa.query.filter(
        Prensa.tipo_recurso == "prensa", or_(Prensa.url.is_(None), Prensa.url == "")
    ).all()

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

    todos_con_fecha = Prensa.query.filter(Prensa.fecha_original.isnot(None)).all()
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

    membrete_path = os.path.join(app.static_folder, "img", "sirio_membrete1.png")
    if os.path.exists(membrete_path):
        story.append(Image(membrete_path, width=5 * cm, height=2.8 * cm))
        story.append(Spacer(1, 12))

    story.append(Paragraph(f"<b>{ref.titulo or '[Sin título]'}</b>", styles["Titulo"]))
    if ref.autor:
        story.append(Paragraph(f"<i>{ref.autor}</i>", styles["Campo"]))
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
            story.append(Paragraph(f"<b>{campo}:</b> {valor}", styles["Campo"]))

    story.append(Spacer(1, 10))

    descripcion_medio = None
    if ref.id_publicacion:
        pub = db.session.get(Publicacion, ref.id_publicacion)
        if pub and pub.descripcion:
            descripcion_medio = pub.descripcion

    if descripcion_medio:
        story.append(Paragraph("<b>Descripción del medio:</b>", styles["Campo"]))
        story.append(Paragraph(descripcion_medio, styles["Contenido"]))

    if ref.contenido:
        story.append(Paragraph("<b>Contenido / Resumen:</b>", styles["Campo"]))
        story.append(
            Paragraph(ref.contenido.replace("\n", "<br/>"), styles["Contenido"])
        )
        story.append(Spacer(1, 10))

    # [MODIFICADO] TEXTO ORIGINAL EN PDF
    if ref.texto_original:
        story.append(
            Paragraph("<b>Texto Original (Idioma Nativo):</b>", styles["Campo"])
        )
        story.append(
            Paragraph(ref.texto_original.replace("\n", "<br/>"), styles["Contenido"])
        )
        story.append(Spacer(1, 10))

    if ref.notas:
        story.append(Paragraph("<b>Notas personales:</b>", styles["Campo"]))
        story.append(Paragraph(ref.notas, styles["Contenido"]))
        story.append(Spacer(1, 10))

    story.append(Spacer(1, 20))
    fecha_actual = datetime.now().strftime("%d/%m/%Y %H:%M")
    pie = f"<i>Exportado desde el Proyecto S.S. Sirio — {fecha_actual}</i>"
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
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    story = []
    styles = getSampleStyleSheet()

    for id in ids:
        ref = db.session.get(Prensa, id)
        if ref:
            story.append(Paragraph(f"<b>{ref.titulo}</b>", styles["Title"]))
            story.append(Paragraph(ref.contenido or "", styles["BodyText"]))
            if ref.texto_original:
                story.append(Paragraph("<b>Original:</b>", styles["Heading4"]))
                story.append(Paragraph(ref.texto_original, styles["BodyText"]))
            if ref.imagen_scan:
                img_path = os.path.join(app.config["UPLOAD_FOLDER"], ref.imagen_scan)
                if os.path.exists(img_path):
                    story.append(
                        Image(
                            img_path, width=5 * cm, height=5 * cm, kind="proportional"
                        )
                    )
            story.append(PageBreak())

    doc.build(story)
    buffer.seek(0)
    return send_file(
        buffer,
        mimetype="application/pdf",
        as_attachment=True,
        download_name="dossier.pdf",
    )


# =========================================================
# EXPORTAR CSV / BIBTEX
# =========================================================
@app.route("/exportar")
def exportar():
    formato = request.args.get("formato", "csv")
    query = ordenar_por_fecha(Prensa.query, descendente=False)
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
            writer.writerow(
                [
                    r.id or "",
                    r.titulo or "",
                    r.publicacion or "",
                    r.fecha_original or "",
                    r.autor or "",
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
                ]
            )
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

            autor_bib = autor_para_bibtex(r.autor)
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
    textos = [
        r.contenido
        for r in Prensa.query.filter(
            Prensa.proyecto_id == proyecto.id, Prensa.contenido.isnot(None)
        ).all()
    ]
    texto_unido = " ".join(textos).lower()

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

    palabras = re.findall(r"\b[a-záéíóúüñ]+\b", texto_unido)
    palabras_filtradas = [p for p in palabras if p not in stopwords and len(p) > 2]

    frecuencias = Counter(palabras_filtradas).most_common(30)

    if not palabras_filtradas:
        return jsonify([])

    return jsonify(frecuencias)


@app.route("/analisis/nube")
def nube_palabras():
    proyecto = get_proyecto_activo()
    if not proyecto:
        return "Error: No hay proyecto activo", 400

    # FILTRAR POR PROYECTO
    textos = " ".join(
        [
            r.contenido
            for r in Prensa.query.filter(
                Prensa.proyecto_id == proyecto.id, Prensa.contenido.isnot(None)
            ).all()
        ]
    )
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
    palabras_filtradas = [p for p in palabras if p not in stopwords and len(p) > 2]

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
        .filter(Prensa.proyecto_id == proyecto.id)
        .group_by(Prensa.anio)
        .all()
    )
    timeline = {
        int(y): c for y, c in raw if y and str(y).isdigit() and 1800 < int(y) < 2030
    }
    years = sorted(timeline.keys())
    pubs = (
        db.session.query(Prensa.publicacion, func.count(Prensa.id))
        .filter(Prensa.proyecto_id == proyecto.id, Prensa.publicacion != "")
        .group_by(Prensa.publicacion)
        .order_by(func.count(Prensa.id).desc())
        .limit(10)
        .all()
    )
    cities = (
        db.session.query(Prensa.ciudad, func.count(Prensa.id))
        .filter(Prensa.proyecto_id == proyecto.id, Prensa.ciudad != "")
        .group_by(Prensa.ciudad)
        .order_by(func.count(Prensa.id).desc())
        .limit(10)
        .all()
    )
    langs = (
        db.session.query(Prensa.idioma, func.count(Prensa.id))
        .filter(Prensa.proyecto_id == proyecto.id)
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
        .filter(Prensa.proyecto_id == proyecto.id, Prensa.anio.isnot(None))
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
        .filter(Prensa.proyecto_id == proyecto.id)
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
        .filter(Prensa.proyecto_id == proyecto.id)
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
    return render_template("mapa.html")


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
        .filter(Prensa.proyecto_id == proyecto.id, Prensa.ciudad != None, Prensa.ciudad != '')
    
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
@login_required
def detectar_entidades():
    """Detecta automáticamente entidades usando spaCy NER"""
    proyecto = get_proyecto_activo()
    if not proyecto:
        return jsonify({"error": "No hay proyecto activo"}), 400
    
    data = request.get_json()
    tipos_nombres = data.get("tipos", {})  # {tipo1: "Personas", tipo2: "Barcos", ...}
    
    if not tipos_nombres:
        return jsonify({"error": "No se proporcionaron tipos"}), 400
    
    # Cargar modelo spaCy
    nlp = get_nlp_model()
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

    # Obtener todas las noticias del proyecto
    noticias = Prensa.query.filter_by(proyecto_id=proyecto.id).all()

    # Crear diccionario de entidad -> tipo (normalizado a minúsculas)
    entidad_tipo = {}
    for tipo_key, tipo_data in red_config.items():
                nombre = re.sub(r'\s+(de|del|y|e|la|las|los|el|von|van|da|di)\s*$', '', nombre, flags=re.IGNORECASE)
                
                # Filtros básicos
                if nombre in stopwords or len(nombre) <= 2:
                    continue
                
                # Ignorar si es solo una palabra y está al inicio de oración
                if len(nombre.split()) == 1 and oracion.strip().startswith(nombre):
                    continue
                
                # Ignorar fechas y números
                if re.search(r'\d', nombre):
                    continue
                
                # Ignorar palabras en mayúsculas completas (probablemente acrónimos o gritos)
                if nombre.isupper() and len(nombre) > 3:
                    continue
                
                candidatos[nombre]["count"] += 1
                candidatos[nombre]["contextos"].append(oracion_lower)
    
    # PASO 2: Definir keywords de contexto por tipo semántico
    keywords_persona = [
        # Títulos y roles
        'capitán', 'comandante', 'señor', 'señora', 'don', 'doña', 'doctor', 'ingeniero', 
        'pasajero', 'tripulante', 'sobreviviente', 'náufrago', 'piloto', 'marinero',
        'oficial', 'teniente', 'sargento', 'víctima', 'muerto', 'herido', 'testigo',
        # Relaciones familiares
        'familia', 'hijo', 'hija', 'padre', 'madre', 'hermano', 'hermana', 'esposa', 'esposo', 'viuda', 'viudo',
        # Verbos y acciones humanas
        'dijo', 'declaró', 'afirmó', 'manifestó', 'expresó', 'relató', 'contó', 'narró',
        'viajaba', 'embarcó', 'desembarcó', 'salvó', 'rescató', 'murió', 'falleció', 'sobrevivió'
    ]
    
    keywords_barco = [
        # Tipos de embarcación
        'vapor', 'buque', 'barco', 'navío', 'embarcación', 'nave', 's.s.', 'ss', 's/s',
        'transatlántico', 'crucero', 'fragata', 'corbeta', 'barca', 'velero', 'paquebote',
        # Eventos náuticos
        'naufragio', 'hundimiento', 'rescate', 'colisión', 'zarpó', 'arribó', 'varó', 'encalló',
        # Partes y contexto náutico
        'bordo', 'tripulación', 'mástil', 'vela', 'proa', 'popa', 'cubierta', 'casco',
        'navegaba', 'navegación', 'travesía', 'viaje', 'ruta', 'línea naviera'
    ]
    
    keywords_lugar = [
        # Tipos de lugares
        'cabo', 'puerto', 'bahía', 'ciudad', 'villa', 'pueblo', 'costa', 'mar', 'playa',
        'océano', 'isla', 'península', 'golfo', 'estrecho', 'muelle', 'puerto',
        'provincia', 'región', 'territorio', 'localidad', 'municipio', 'distrito',
        # Preposiciones de lugar
        'en', 'desde', 'hacia', 'cerca de', 'frente a', 'junto a', 'a la altura de',
        'situado', 'ubicado', 'localizado'
    ]
    
    # Prefijos comunes por tipo
    prefijos_barco = ['s.s.', 'vapor', 'buque', 'crucero', 'fragata', 'paquebote']
    prefijos_lugar = ['cabo', 'puerto', 'bahía', 'ciudad', 'villa', 'isla', 'monte', 'río']
    
    # PASO 3: Clasificar cada tipo solicitado
    for tipo_key, tipo_nombre in tipos_nombres.items():
        tipo_lower = tipo_nombre.lower()
        entidades_clasificadas = Counter()
        
        # Determinar qué tipo de entidad estamos buscando
        es_tipo_persona = any(kw in tipo_lower for kw in ['persona', 'gente', 'capitán', 'tripulante', 'pasajero', 'náufrago', 'oficial', 'marinero', 'víctima'])
        es_tipo_barco = any(kw in tipo_lower for kw in ['barco', 'buque', 'vapor', 'embarcación', 'navío', 'nave'])
        es_tipo_lugar = any(kw in tipo_lower for kw in ['lugar', 'ciudad', 'puerto', 'geografía', 'costa', 'región', 'zona', 'localidad'])
        
        # Seleccionar keywords y criterios según el tipo
        if es_tipo_persona:
            keywords_tipo = keywords_persona
            keywords_excluir = keywords_barco + keywords_lugar
            min_palabras, max_palabras = 2, 4
            requiere_contexto = True
        elif es_tipo_barco:
            keywords_tipo = keywords_barco
            keywords_excluir = keywords_persona
            min_palabras, max_palabras = 1, 5
            requiere_contexto = False
        elif es_tipo_lugar:
            keywords_tipo = keywords_lugar
            keywords_excluir = keywords_persona + keywords_barco
            min_palabras, max_palabras = 1, 4
            requiere_contexto = False
        else:
            # Tipo genérico
            keywords_tipo = tipo_nombre.lower().split()
            keywords_excluir = []
            min_palabras, max_palabras = 1, 5
            requiere_contexto = False
        
        # Clasificar cada candidato
        for nombre, info in candidatos.items():
            count = info["count"]
            contextos = info["contextos"]
            
            # Filtro de frecuencia mínima (más estricto)
            if count < 3:
                continue
            
            # Filtro de longitud de nombre
            num_palabras = len(nombre.split())
            if num_palabras < min_palabras or num_palabras > max_palabras:
                continue
            
            # Análisis de contextos
            score_tipo = 0
            score_excluir = 0
            tiene_prefijo_tipo = False
            
            nombre_lower = nombre.lower()
            
            # Verificar prefijos específicos
            if es_tipo_barco:
                tiene_prefijo_tipo = any(nombre_lower.startswith(pref) for pref in prefijos_barco)
            elif es_tipo_lugar:
                tiene_prefijo_tipo = any(nombre_lower.startswith(pref) for pref in prefijos_lugar)
            
            # Analizar cada contexto
            for ctx in contextos:
                # Contar keywords del tipo
                matches_tipo = sum(1 for kw in keywords_tipo if kw in ctx)
                score_tipo += matches_tipo
                
                # Contar keywords a excluir
                matches_excluir = sum(1 for kw in keywords_excluir if kw in ctx)
                score_excluir += matches_excluir
            
            # Calcular ratios
            ratio_tipo = score_tipo / max(len(contextos), 1)
            ratio_excluir = score_excluir / max(len(contextos), 1)
            
            # Decisión de inclusión
            incluir = False
            
            if tiene_prefijo_tipo:
                # Si tiene prefijo específico, incluir si no hay mucho contexto excluyente
                incluir = ratio_excluir < 0.5
            elif requiere_contexto:
                # Personas requieren contexto fuerte
                incluir = score_tipo >= 2 and ratio_tipo > ratio_excluir
            else:
                # Barcos y lugares: más flexible
                incluir = score_tipo > 0 and ratio_excluir < 0.3
            
            # Filtros adicionales por tipo
            if incluir:
                if es_tipo_persona:
                    # Personas: debe tener 2+ palabras (nombre + apellido)
                    if num_palabras < 2:
                        incluir = False
                    # No debe contener palabras náuticas en el nombre
                    if any(kw in nombre_lower for kw in ['vapor', 'buque', 'ss', 's.s.', 'barco']):
                        incluir = False
                
                elif es_tipo_barco:
                    # Barcos: si tiene nombre de persona (2-3 palabras sin prefijo), debe tener contexto fuerte
                    if num_palabras >= 2 and not tiene_prefijo_tipo:
                        if score_tipo < 3:
                            incluir = False
                
                elif es_tipo_lugar:
                    # Lugares: no deben ser nombres de persona típicos
                    if num_palabras == 2 and not tiene_prefijo_tipo:
                        if score_tipo < 2:
                            incluir = False
            
            if incluir:
                entidades_clasificadas[nombre] = count
        
        # Si no encontró suficientes, relajar criterios
        if len(entidades_clasificadas) < 5:
            for nombre, info in candidatos.items():
                if nombre in entidades_clasificadas:
                    continue
                    
                count = info["count"]
                if count < 2:
                    continue
                
                num_palabras = len(nombre.split())
                if num_palabras < min_palabras or num_palabras > max_palabras:
                    continue
                
                # Criterio relajado: solo evitar contexto excluyente fuerte
                contextos = info["contextos"]
                score_excluir = sum(1 for ctx in contextos for kw in keywords_excluir if kw in ctx)
                ratio_excluir = score_excluir / max(len(contextos), 1)
                
                if ratio_excluir < 0.4:
                    entidades_clasificadas[nombre] = count
        
        # Tomar top 20
        top_20 = sorted(entidades_clasificadas.items(), key=lambda x: x[1], reverse=True)[:20]
        
        resultados[tipo_key] = [
            {"nombre": nombre, "menciones": count}
            for nombre, count in top_20
        ]
    
    return jsonify({"entidades": resultados})


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

    # Obtener todas las noticias del proyecto
    noticias = Prensa.query.filter_by(proyecto_id=proyecto.id).all()

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
        .filter(Prensa.proyecto_id == proyecto.id)\
        .filter(Prensa.publicacion.isnot(None))\
        .filter(Prensa.publicacion != '')\
        .distinct()\
        .order_by(Prensa.publicacion)\
        .all()
    
    publicaciones = [p[0] for p in publicaciones_query if p[0]]
    
    # Obtener rango de fechas (min y max)
    fecha_min_query = db.session.query(db.func.min(Prensa.fecha_original))\
        .filter(Prensa.proyecto_id == proyecto.id)\
        .filter(Prensa.fecha_original.isnot(None))\
        .scalar()
    
    fecha_max_query = db.session.query(db.func.max(Prensa.fecha_original))\
        .filter(Prensa.proyecto_id == proyecto.id)\
        .filter(Prensa.fecha_original.isnot(None))\
        .scalar()
    
    return jsonify({
        "publicaciones": publicaciones,
        "fecha_min": fecha_min_query,
        "fecha_max": fecha_max_query
    })


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
    
    # Consulta base
    query = Prensa.query.filter_by(proyecto_id=proyecto.id)
    
    # Aplicar filtros
    if publicaciones_filtro:
        query = query.filter(Prensa.publicacion.in_(publicaciones_filtro))
    
    if fecha_desde:
        query = query.filter(Prensa.fecha_original >= fecha_desde)
    
    if fecha_hasta:
        query = query.filter(Prensa.fecha_original <= fecha_hasta)
    
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
        
        for entidad_original in entidad_tipo.keys():
            if entidad_original in texto_completo:
                for ent_config in red_config.values():
                    for ent in ent_config.get('entidades', []):
                        if isinstance(ent, str) and ent.lower() == entidad_original:
                            entidad_counter[ent] += texto_completo.count(entidad_original)
                            break
    
    # Crear nodos
    nodes = []
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


@app.route("/borrar_imagen_prensa/<int:id>")
def borrar_imagen_prensa(id):
    imagen = ImagenPrensa.query.get_or_404(id)
    ruta = os.path.join(app.config["UPLOAD_FOLDER"], imagen.filename)
    if os.path.exists(ruta):
        os.remove(ruta)
    db.session.delete(imagen)
    db.session.commit()
    flash("🗑️ Imagen eliminada correctamente.", "info")
    # Redirige a la edición de la noticia asociada
    return redirect(url_for("editar", id=imagen.prensa_id))


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


@app.route("/buscador_semantico")
def buscador_semantico():
    return render_template("buscador_semantico.html")


@app.route("/api/buscar_semantico")
def api_buscar_semantico():
    global vectorizer, tfidf_matrix, noticias_indices
    
    proyecto = get_proyecto_activo()
    if not proyecto:
        return jsonify({"error": "No hay proyecto activo"}), 400
    
    query = request.args.get("q", "").strip()

    # Si no hay consulta, devolvemos vacío
    if not query:
        return jsonify([])
    
    # Si el motor no cargó, intentar inicializarlo
    if vectorizer is None:
        try:
            inicializar_buscador()
        except Exception as e:
            print(f"Error inicializando buscador: {e}")
            return jsonify([])

    try:
        # 1. Convertimos la pregunta del usuario en números (vector)
        q_vec = vectorizer.transform([query])

        # 2. Calculamos similitud matemática (Coseno)
        similitudes = cosine_similarity(q_vec, tfidf_matrix).flatten()

        # 3. Ordenamos los resultados de mejor a peor
        indices_ordenados = similitudes.argsort()[::-1][:25]  # Top 25

        res = []
        for idx in indices_ordenados:
            score = similitudes[idx]
            if score < 0.01:  # Umbral más bajo para capturar más resultados
                break

            nid = noticias_indices[idx]
            n = db.session.get(Prensa, nid)

            # FILTRAR POR PROYECTO
            if n and n.proyecto_id == proyecto.id:
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
                        "fecha": n.fecha_original,
                        "publicacion": n.publicacion,
                        "ciudad": n.ciudad,
                        "score": round(score_final * 100, 1),  # Porcentaje
                        "fragmento": fragmento,
                        "url_editar": url_for("editar", id=n.id),
                    }
                )

        # Reordenar por score final
        res.sort(key=lambda x: x["score"], reverse=True)
        res = res[:20]  # Limitar a top 20

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

    datos = {
        "descripcion_publicacion": pub.descripcion,
        "tipo_recurso": pub.tipo_recurso,
        "ciudad": pub.ciudad,
        "pais_publicacion": pub.pais_publicacion,
        "idioma": pub.idioma,
        "licencia": (pub.licencia or pub.licencia_predeterminada or "CC BY 4.0"),
        "formato_fuente": pub.formato_fuente,
        "hemeroteca_nombre": nombre_hemeroteca,
        "edicion": pub.frecuencia or "",
        "institucion": institucion,
    }
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
    max_numero = db.session.query(db.func.max(Prensa.numero_referencia))\
        .filter(Prensa.proyecto_id == proyecto.id)\
        .filter(Prensa.incluido == True)\
        .scalar()
    
    siguiente_numero = (max_numero or 0) + 1
    
    return jsonify({"siguiente_numero": siguiente_numero})

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
@app.route("/publicaciones")
def lista_publicaciones():
    proyecto = get_proyecto_activo()
    if not proyecto:
        return redirect(url_for("listar_proyectos"))

    # 1. Recoger el parámetro de la URL (si existe)
    hemeroteca_id = request.args.get('hemeroteca_id')
    filtro_nombre = None

    # 2. Construir la consulta base filtrada por proyecto
    query = Publicacion.query.filter_by(proyecto_id=proyecto.id)

    # 3. Aplicar filtro de hemeroteca si viene el ID
    if hemeroteca_id:
        try:
            # Aseguramos que sea un entero para evitar errores
            hemeroteca_id = int(hemeroteca_id)
            query = query.filter_by(hemeroteca_id=hemeroteca_id)
            
            # Buscamos el nombre de la hemeroteca para mostrarlo en el título
            hemeroteca = db.session.get(Hemeroteca, hemeroteca_id)
            if hemeroteca:
                filtro_nombre = hemeroteca.nombre
        except (ValueError, TypeError):
            # Si el ID no es un número válido, ignoramos el filtro
            pass

    # 4. Ejecutar consulta con ordenación
    pubs = query.order_by(Publicacion.nombre.asc()).all()

    # Calcular estadísticas rápidas (de los resultados visibles)
    total_medios = len(pubs)
    total_noticias_vinculadas = sum(len(p.articulos) for p in pubs)

    return render_template(
        "publicaciones.html",
        publicaciones=pubs,
        total_medios=total_medios,
        total_noticias=total_noticias_vinculadas,
        filtro_activo=filtro_nombre,       # Pasamos el nombre para el aviso visual
        hemeroteca_id_activo=hemeroteca_id # Pasamos el ID por si hiciera falta
    )


@app.route("/api/publicacion/<int:id>")
def api_publicacion_get(id):
    pub = db.session.get(Publicacion, id)
    if not pub:
        return jsonify({"error": "no encontrado"}), 404
    return jsonify(
        {
            "id_publicacion": pub.id_publicacion,
            "nombre": pub.nombre,
            "ciudad": pub.ciudad,
            "pais_publicacion": pub.pais_publicacion,
            "fuente": pub.fuente,
            "formato_fuente": pub.formato_fuente,
            "descripcion": pub.descripcion,
            "idioma": pub.idioma,
            "licencia_predeterminada": pub.licencia_predeterminada,
        }
    )


@app.route("/publicacion/editar/<int:id>", methods=["GET", "POST"])
def editar_publicacion(id):
    pub = db.session.get(Publicacion, id)
    if not pub:
        return abort(404)

    if request.method == "POST":
        try:
            # Asignar valores (con .strip() cuando procede)
            nombre_val = (request.form.get("nombre") or "").strip()
            pub.nombre = nombre_val or pub.nombre

            # Sanear y asignar campos evitando guardar literales como 'None' o 'null'
            def _sanear(v):
                if v is None:
                    return None
                s = str(v).strip()
                if s == "" or s.lower() in ("none", "null"):
                    return None
                return s

            pub.ciudad = _sanear(request.form.get("ciudad"))
            pub.pais_publicacion = _sanear(request.form.get("pais"))
            pub.descripcion = _sanear(request.form.get("descripcion"))
            pub.idioma = _sanear(request.form.get("idioma"))
            pub.licencia_predeterminada = _sanear(request.form.get("licencia"))
            # Fuente y formato
            pub.fuente = _sanear(request.form.get("fuente"))
            pub.formato_fuente = _sanear(request.form.get("formato_fuente"))

            # ⬇️⬇️ NUEVO: guardar la hemeroteca seleccionada ⬇️⬇️
            h_id = request.form.get("hemeroteca_id")
            try:
                pub.hemeroteca_id = int(h_id) if h_id and h_id.strip() else None
            except ValueError:
                pub.hemeroteca_id = None
            # ⬆️⬆️ FIN BLOQUE NUEVO ⬆️⬆️

            app.logger.info(
                f"Actualizando Publicacion id={id} con datos: {dict(request.form)}"
            )
            db.session.commit()
            # Refrescar para asegurar datos sincronizados
            db.session.refresh(pub)

            # Si el usuario pidió propagar cambios a las noticias vinculadas, actualizarlas
            if "propagar" in request.form:
                try:
                    payload_prensa = {}
                    if pub.ciudad is not None:
                        payload_prensa[Prensa.ciudad] = pub.ciudad
                    if pub.pais_publicacion is not None:
                        payload_prensa[Prensa.pais_publicacion] = pub.pais_publicacion
                    if pub.fuente is not None:
                        payload_prensa[Prensa.fuente] = pub.fuente
                    if pub.formato_fuente is not None:
                        payload_prensa[Prensa.formato_fuente] = pub.formato_fuente
                    if pub.idioma is not None:
                        payload_prensa[Prensa.idioma] = pub.idioma
                    if pub.licencia_predeterminada is not None:
                        payload_prensa[Prensa.licencia] = pub.licencia_predeterminada

                    if payload_prensa:
                        app.logger.info(
                            f"Propagando a noticias vinculadas (por fila): "
                            f"{ {str(k): v for k, v in payload_prensa.items()} }"
                        )
                        # Seleccionar noticias vinculadas por id_publicacion o por nombre de publicación
                        noticias = Prensa.query.filter(
                            or_(
                                Prensa.id_publicacion == id,
                                Prensa.publicacion == pub.nombre,
                            )
                        ).all()
                        cuenta = 0
                        for noticia in noticias:
                            for attr, val in payload_prensa.items():
                                try:
                                    nombre_attr = attr.key
                                except Exception:
                                    nombre_attr = getattr(attr, "name", None) or str(
                                        attr
                                    )
                                if nombre_attr and val is not None:
                                    setattr(noticia, nombre_attr, val)
                            # Vincular explícitamente la noticia a la publicación
                            try:
                                noticia.id_publicacion = pub.id_publicacion
                                noticia.publicacion = pub.nombre
                            except Exception:
                                pass
                            cuenta += 1
                        db.session.commit()
                        db.session.expire_all()
                        app.logger.info(
                            f"Actualizadas {cuenta} noticias vinculadas para publicacion id={id} (por fila)"
                        )
                        flash(f"✅ Actualizadas {cuenta} noticias vinculadas.", "info")
                except Exception as e:
                    db.session.rollback()
                    app.logger.exception(
                        f"Error propagando cambios a noticias vinculadas para publicacion id={id}: {e}"
                    )
                    flash(
                        f"⚠️ No se pudieron propagar todos los cambios a las noticias vinculadas: {str(e)}",
                        "warning",
                    )

            flash("✅ Datos del medio actualizados.", "success")
            return redirect(url_for("lista_publicaciones"))

        except Exception as e:
            db.session.rollback()
            app.logger.exception(f"Error guardando Publicacion id={id}: {e}")
            flash(f"❌ Error al guardar: {str(e)}", "danger")
            # continuar y re-renderizar el formulario con los valores actuales

    proyecto = get_proyecto_activo()
    if proyecto:
        hemerotecas = (
            Hemeroteca.query.filter_by(proyecto_id=proyecto.id)
            .order_by(Hemeroteca.nombre)
            .all()
        )
    else:
        hemerotecas = Hemeroteca.query.order_by(Hemeroteca.nombre).all()

    return render_template("editar_publicacion.html", pub=pub, hemerotecas=hemerotecas)

    @app.route("/publicacion/editar/<int:id>", methods=["GET", "POST"])
    def editar_publicacion(id):
        pub = db.session.get(Publicacion, id)
        if not pub:
            return abort(404)

        if request.method == "POST":
            try:
                # Asignar valores (con .strip() cuando procede)
                nombre_val = (request.form.get("nombre") or "").strip()
                pub.nombre = nombre_val or pub.nombre

                # Sanear y asignar campos evitando guardar literales como 'None' o 'null'
                def _sanear(v):
                    if v is None:
                        return None
                    s = str(v).strip()
                    if s == "" or s.lower() in ("none", "null"):
                        return None
                    return s

                pub.ciudad = _sanear(request.form.get("ciudad"))
                pub.pais_publicacion = _sanear(request.form.get("pais"))
                pub.descripcion = _sanear(request.form.get("descripcion"))
                pub.idioma = _sanear(request.form.get("idioma"))
                pub.licencia_predeterminada = _sanear(request.form.get("licencia"))
                # Fuente y formato
                pub.fuente = _sanear(request.form.get("fuente"))
                pub.formato_fuente = _sanear(request.form.get("formato_fuente"))

                # ⬇️⬇️ NUEVO: guardar la hemeroteca seleccionada ⬇️⬇️
                h_id = request.form.get("hemeroteca_id")
                try:
                    pub.hemeroteca_id = int(h_id) if h_id and h_id.strip() else None
                except ValueError:
                    pub.hemeroteca_id = None
                # ⬆️⬆️ FIN BLOQUE NUEVO ⬆️⬆️

                app.logger.info(
                    f"Actualizando Publicacion id={id} con datos: {dict(request.form)}"
                )
                db.session.commit()
                # Refrescar para asegurar datos sincronizados
                db.session.refresh(pub)

                # Si el usuario pidió propagar cambios a las noticias vinculadas, actualizarlas
                if "propagar" in request.form:
                    try:
                        payload_prensa = {}
                        if pub.ciudad is not None:
                            payload_prensa[Prensa.ciudad] = pub.ciudad
                        if pub.pais_publicacion is not None:
                            payload_prensa[Prensa.pais_publicacion] = (
                                pub.pais_publicacion
                            )
                        if pub.fuente is not None:
                            payload_prensa[Prensa.fuente] = pub.fuente
                        if pub.formato_fuente is not None:
                            payload_prensa[Prensa.formato_fuente] = pub.formato_fuente
                        if pub.idioma is not None:
                            payload_prensa[Prensa.idioma] = pub.idioma
                        if pub.licencia_predeterminada is not None:
                            payload_prensa[Prensa.licencia] = (
                                pub.licencia_predeterminada
                            )

                        if payload_prensa:
                            app.logger.info(
                                f"Propagando a noticias vinculadas (por fila): "
                                f"{ {str(k): v for k, v in payload_prensa.items()} }"
                            )
                            # Seleccionar noticias vinculadas por id_publicacion o por nombre de publicación
                            noticias = Prensa.query.filter(
                                or_(
                                    Prensa.id_publicacion == id,
                                    Prensa.publicacion == pub.nombre,
                                )
                            ).all()
                            cuenta = 0
                            for noticia in noticias:
                                for attr, val in payload_prensa.items():
                                    try:
                                        nombre_attr = attr.key
                                    except Exception:
                                        nombre_attr = getattr(
                                            attr, "name", None
                                        ) or str(attr)
                                    if nombre_attr and val is not None:
                                        setattr(noticia, nombre_attr, val)
                                # Vincular explícitamente la noticia a la publicación
                                try:
                                    noticia.id_publicacion = pub.id_publicacion
                                    noticia.publicacion = pub.nombre
                                except Exception:
                                    pass
                                cuenta += 1
                            db.session.commit()
                            db.session.expire_all()
                            app.logger.info(
                                f"Actualizadas {cuenta} noticias vinculadas para publicacion id={id} (por fila)"
                            )
                            flash(
                                f"✅ Actualizadas {cuenta} noticias vinculadas.", "info"
                            )
                    except Exception as e:
                        db.session.rollback()
                        app.logger.exception(
                            f"Error propagando cambios a noticias vinculadas para publicacion id={id}: {e}"
                        )
                        flash(
                            f"⚠️ No se pudieron propagar todos los cambios a las noticias vinculadas: {str(e)}",
                            "warning",
                        )

                flash("✅ Datos del medio actualizados.", "success")
                return redirect(url_for("lista_publicaciones"))

            except Exception as e:
                db.session.rollback()
                app.logger.exception(f"Error guardando Publicacion id={id}: {e}")
                flash(f"❌ Error al guardar: {str(e)}", "danger")
                # continuar y re-renderizar el formulario con los valores actuales

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
            "editar_publicacion.html", pub=pub, hemerotecas=hemerotecas
        )


# [NUEVO] CREAR NUEVA PUBLICACIÓN
@app.route("/publicacion/nueva", methods=["GET", "POST"])
def nueva_publicacion():
    if request.method == "POST":
        nombre = request.form.get("nombre").strip()

        # Evitar duplicados
        if Publicacion.query.filter_by(nombre=nombre).first():
            flash(f"⚠️ El medio '{nombre}' ya existe.", "warning")
            return redirect(url_for("nueva_publicacion"))

        hemeroteca_id = request.form.get("hemeroteca_id")
        nueva = Publicacion(
            proyecto_id=get_proyecto_activo().id,
            nombre=nombre,
            ciudad=request.form.get("ciudad"),
            pais_publicacion=request.form.get("pais"),
            descripcion=request.form.get("descripcion"),
            idioma=request.form.get("idioma"),
            licencia_predeterminada=request.form.get("licencia"),
            fuente=request.form.get("fuente"),
            formato_fuente=request.form.get("formato_fuente"),
            hemeroteca_id=int(hemeroteca_id)
            if hemeroteca_id and hemeroteca_id.strip()
            else None,
        )
        db.session.add(nueva)
        db.session.commit()
        # Después de crear la publicación, asociar y propagar a noticias que ya referencian ese nombre
        try:
            pub_id = nueva.id_publicacion
            payload_prensa = {}
            if nueva.ciudad:
                payload_prensa[Prensa.ciudad] = nueva.ciudad
            if nueva.pais_publicacion:
                payload_prensa[Prensa.pais_publicacion] = nueva.pais_publicacion
            if nueva.fuente:
                payload_prensa[Prensa.fuente] = nueva.fuente
            if nueva.formato_fuente:
                payload_prensa[Prensa.formato_fuente] = nueva.formato_fuente
            if nueva.idioma:
                payload_prensa[Prensa.idioma] = nueva.idioma
            if nueva.licencia_predeterminada:
                payload_prensa[Prensa.licencia] = nueva.licencia_predeterminada

            # Buscar noticias cuyo texto 'publicacion' coincida con el nombre
            noticias = Prensa.query.filter(Prensa.publicacion == nombre).all()
            cuenta = 0
            for noticia in noticias:
                # Establecer id_publicacion y actualizar campos
                noticia.id_publicacion = pub_id
                noticia.publicacion = nombre
                for attr, val in payload_prensa.items():
                    try:
                        key = attr.key
                    except Exception:
                        key = getattr(attr, "name", None) or str(attr)
                    if key and val is not None:
                        setattr(noticia, key, val)
                cuenta += 1
            if cuenta:
                db.session.commit()
                db.session.expire_all()
                flash(
                    f"✅ Medio '{nombre}' creado con éxito. Asociadas y actualizadas {cuenta} noticias existentes.",
                    "success",
                )
            else:
                flash(f"✅ Medio '{nombre}' creado con éxito.", "success")
        except Exception as e:
            db.session.rollback()
            app.logger.exception(
                f"Error propagando creación de publicacion '{nombre}': {e}"
            )
            flash(
                f"✅ Medio '{nombre}' creado, pero no se pudieron asociar noticias existentes: {str(e)}",
                "warning",
            )
        return redirect(url_for("lista_publicaciones"))

    proyecto = get_proyecto_activo()
    if proyecto:
        hemerotecas = (
            Hemeroteca.query.filter_by(proyecto_id=proyecto.id)
            .order_by(Hemeroteca.nombre)
            .all()
        )
    else:
        hemerotecas = Hemeroteca.query.order_by(Hemeroteca.nombre).all()

    return render_template("nueva_publicacion.html", hemerotecas=hemerotecas)


# [NUEVO] BORRAR PUBLICACIÓN
@app.route("/publicacion/borrar/<int:id>")
def borrar_publicacion(id):
    pub = db.session.get(Publicacion, id)
    if pub:
        # Paso de seguridad: Desvincular noticias antes de borrar
        # para que no se borren las noticias en cascada (o den error)
        noticias_afectadas = Prensa.query.filter_by(id_publicacion=id).all()
        for n in noticias_afectadas:
            n.id_publicacion = None  # Las dejamos "huerfanas" pero vivas

        nombre = pub.nombre
        db.session.delete(pub)
        db.session.commit()
        flash(
            f"🗑️ Medio '{nombre}' eliminado. {len(noticias_afectadas)} noticias desvinculadas.",
            "success",
        )
    return redirect(url_for("lista_publicaciones"))


# =========================================================
# RUTAS - GESTIÓN DE HEMEROTECAS
# =========================================================


@app.route("/hemerotecas")
def lista_hemerotecas():
    """Listado de hemerotecas con filtrado por proyecto"""
    proyecto_actual = get_proyecto_activo()

    if proyecto_actual:
        hemerotecas = (
            Hemeroteca.query.filter_by(proyecto_id=proyecto_actual.id)
            .order_by(Hemeroteca.pais, Hemeroteca.nombre)
            .all()
        )
    else:
        hemerotecas = Hemeroteca.query.order_by(
            Hemeroteca.pais, Hemeroteca.nombre
        ).all()

    # Contar publicaciones por hemeroteca
    stats = {}
    for h in hemerotecas:
        stats[h.id] = Publicacion.query.filter_by(hemeroteca_id=h.id).count()

    return render_template(
        "hemerotecas.html",
        hemerotecas=hemerotecas,
        stats=stats,
        total_hemerotecas=len(hemerotecas),
    )


@app.route("/hemeroteca/nueva", methods=["GET", "POST"])
def nueva_hemeroteca():
    """Crear nueva hemeroteca"""
    proyecto_actual = get_proyecto_activo()

    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        pais = request.form.get("pais", "").strip()
        provincia = request.form.get("provincia", "").strip()
        ciudad = request.form.get("ciudad", "").strip()
        institucion = request.form.get("institucion", "").strip()
        resumen_corpus = request.form.get("resumen_corpus", "").strip()
        url = request.form.get("url", "").strip()

        if not nombre:
            flash("❌ El nombre de la hemeroteca es obligatorio", "danger")
            return redirect(url_for("nueva_hemeroteca"))

        try:
            nueva_hem = Hemeroteca(
                proyecto_id=proyecto_actual.id if proyecto_actual else None,
                nombre=nombre,
                institucion=institucion,
                pais=pais,
                provincia=provincia,
                ciudad=ciudad,
                resumen_corpus=resumen_corpus,
                url=url,
            )
            db.session.add(nueva_hem)
            db.session.commit()
            flash(f'✅ Hemeroteca "{nombre}" creada con éxito', "success")
            return redirect(url_for("lista_hemerotecas"))
        except Exception as e:
            db.session.rollback()
            flash(f"❌ Error al crear hemeroteca: {str(e)}", "danger")
            app.logger.exception(f"Error creando hemeroteca: {e}")

    return render_template("hemeroteca_form.html", hemeroteca=None, accion="nueva")


@app.route("/hemeroteca/editar/<int:id>", methods=["GET", "POST"])
def editar_hemeroteca(id):
    """Editar hemeroteca existente"""
    hemeroteca = db.session.get(Hemeroteca, id)
    if not hemeroteca:
        flash("❌ Hemeroteca no encontrada", "danger")
        return redirect(url_for("lista_hemerotecas"))

    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()

        if not nombre:
            flash("❌ El nombre de la hemeroteca es obligatorio", "danger")
            return render_template(
                "hemeroteca_form.html", hemeroteca=hemeroteca, accion="editar"
            )

        try:
            hemeroteca.nombre = nombre
            hemeroteca.institucion = request.form.get("institucion", "").strip()
            hemeroteca.pais = request.form.get("pais", "").strip()
            hemeroteca.provincia = request.form.get("provincia", "").strip()
            hemeroteca.ciudad = request.form.get("ciudad", "").strip()
            hemeroteca.resumen_corpus = request.form.get("resumen_corpus", "").strip()
            hemeroteca.url = request.form.get("url", "").strip()
            hemeroteca.modificado_en = datetime.utcnow()

            db.session.commit()
            flash(f'✅ Hemeroteca "{nombre}" actualizada con éxito', "success")
            return redirect(url_for("lista_hemerotecas"))
        except Exception as e:
            db.session.rollback()
            flash(f"❌ Error al actualizar hemeroteca: {str(e)}", "danger")
            app.logger.exception(f"Error actualizando hemeroteca: {e}")

    return render_template(
        "hemeroteca_form.html", hemeroteca=hemeroteca, accion="editar"
    )


@app.route("/hemeroteca/borrar/<int:id>")
def borrar_hemeroteca(id):
    """Eliminar hemeroteca (desvincula publicaciones)"""
    hemeroteca = db.session.get(Hemeroteca, id)
    if hemeroteca:
        # Desvincular publicaciones
        publicaciones_afectadas = Publicacion.query.filter_by(hemeroteca_id=id).all()
        for pub in publicaciones_afectadas:
            pub.hemeroteca_id = None

        nombre = hemeroteca.nombre
        db.session.delete(hemeroteca)
        db.session.commit()
        flash(
            f'🗑️ Hemeroteca "{nombre}" eliminada. {len(publicaciones_afectadas)} publicaciones desvinculadas.',
            "success",
        )

    return redirect(url_for("lista_hemerotecas"))


@app.route("/hemeroteca/migrar/<int:id>", methods=["GET", "POST"])
def migrar_hemeroteca(id):
    """Migrar hemeroteca a otro proyecto"""
    hemeroteca = db.session.get(Hemeroteca, id)
    if not hemeroteca:
        flash("❌ Hemeroteca no encontrada", "danger")
        return redirect(url_for("lista_hemerotecas"))

    # Obtener todos los proyectos excepto el actual
    proyectos_disponibles = (
        Proyecto.query.filter(Proyecto.id != hemeroteca.proyecto_id)
        .order_by(Proyecto.nombre)
        .all()
    )

    if request.method == "POST":
        nuevo_proyecto_id = request.form.get("proyecto_id")

        if not nuevo_proyecto_id:
            flash("❌ Debes seleccionar un proyecto destino", "danger")
            return render_template(
                "migrar_hemeroteca.html",
                hemeroteca=hemeroteca,
                proyectos=proyectos_disponibles,
            )

        try:
            proyecto_destino = db.session.get(Proyecto, int(nuevo_proyecto_id))
            proyecto_origen = (
                db.session.get(Proyecto, hemeroteca.proyecto_id)
                if hemeroteca.proyecto_id
                else None
            )

            # Contar publicaciones afectadas
            publicaciones_afectadas = Publicacion.query.filter_by(
                hemeroteca_id=id
            ).count()

            # Migrar hemeroteca
            hemeroteca.proyecto_id = int(nuevo_proyecto_id)
            db.session.commit()

            flash(
                f'✅ Hemeroteca "{hemeroteca.nombre}" migrada a proyecto "{proyecto_destino.nombre}". {publicaciones_afectadas} publicaciones vinculadas se mantienen.',
                "success",
            )
            return redirect(url_for("lista_hemerotecas"))

        except Exception as e:
            db.session.rollback()
            flash(f"❌ Error al migrar hemeroteca: {str(e)}", "danger")
            app.logger.exception(f"Error migrando hemeroteca: {e}")

    return render_template(
        "migrar_hemeroteca.html", hemeroteca=hemeroteca, proyectos=proyectos_disponibles
    )


# =========================================================
# API ENDPOINTS - GESTIÓN DE REFERENCIAS BIBLIOGRÁFICAS
# =========================================================

@app.route("/api/validar_numero_referencia")
def api_validar_numero_referencia():
    """Valida si un número de referencia ya está en uso"""
    try:
        numero = request.args.get("numero", type=int)
        exclude_id = request.args.get("exclude_id", type=int)

        if not numero:
            return jsonify({"en_uso": False})

        # Buscar si el número ya existe
        query = db.session.query(Prensa).filter(
            Prensa.numero_referencia == numero, Prensa.incluido == True
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
    try:
        referencias = (
            Prensa.query.filter(
                Prensa.numero_referencia == numero, Prensa.incluido == True
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


# =========================================================
# VISTA DE BIBLIOGRAFÍA
# =========================================================


@app.route("/bibliografia")
def bibliografia():
    """Vista de bibliografía completa ordenada por número de referencia"""
    try:
        # Obtener todas las referencias incluidas con número asignado
        referencias = (
            Prensa.query.filter(
                Prensa.incluido == True, Prensa.numero_referencia.isnot(None)
            )
            .order_by(Prensa.numero_referencia.asc(), Prensa.fecha_original.asc())
            .all()
        )

        # Agrupar por número de referencia
        referencias_agrupadas = {}
        for ref in referencias:
            num = ref.numero_referencia
            if num not in referencias_agrupadas:
                referencias_agrupadas[num] = []
            referencias_agrupadas[num].append(ref)

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
    try:
        formato = request.args.get("formato", "bibtex")

        referencias = (
            Prensa.query.filter(
                Prensa.incluido == True, Prensa.numero_referencia.isnot(None)
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
# Carga lazy del modelo de spaCy (se carga solo cuando se necesita)
_nlp_model = None


def get_nlp_model():
    """Carga el modelo de spaCy de forma lazy"""
    global _nlp_model
    if _nlp_model is None:
        try:
            import spacy

            _nlp_model = spacy.load("es_core_news_md")
        except Exception as e:
            print(f"Error cargando modelo spaCy: {e}")
            _nlp_model = False
    return _nlp_model


@app.route("/api/analyze-text", methods=["POST"])
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
        nlp = get_nlp_model()
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

        # Obtener todos los contenidos no vacíos
        referencias = (
            Prensa.query.filter(Prensa.contenido.isnot(None), Prensa.contenido != "")
            .limit(1000)
            .all()
        )  # Limitar para rendimiento

        if not referencias:
            return jsonify({"error": "No hay contenidos para analizar"}), 404

        # === ESTADÍSTICAS GENERALES ===
        total_refs = Prensa.query.count()
        with_content = Prensa.query.filter(
            Prensa.contenido.isnot(None), Prensa.contenido != ""
        ).count()
        content_percentage = (
            round((with_content / total_refs * 100), 1) if total_refs > 0 else 0
        )

        # Concatenar todos los textos
        corpus_text = " ".join([ref.contenido[:500] for ref in referencias])

        # === WORD CLOUD DATA ===
        word_freq = {}
        try:
            from sklearn.feature_extraction.text import CountVectorizer

            # Stopwords personalizadas para español - periodismo
            if custom_stopwords:
                # Usar stopwords del usuario
                stopwords_es = set(
                    w.strip().lower() for w in custom_stopwords.split(",") if w.strip()
                )
            else:
                # Usar stopwords predeterminadas (sin palabras clave del proyecto)
                stopwords_es = {
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
                    "sino",
                    "aquel",
                    "aquella",
                    "aquellos",
                    "aquellas",
                    "sido",
                    "siendo",
                }

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
            stopwords_es = stopwords_es - palabras_clave_proyecto

            vectorizer = CountVectorizer(
                max_features=300,
                ngram_range=(1, 2),
                min_df=1,
                stop_words=list(stopwords_es),
                token_pattern=r"\b[a-záéíóúüñ]{2,}\b",
            )

            texts = [ref.contenido[:500] for ref in referencias if ref.contenido]
            if texts:
                count_matrix = vectorizer.fit_transform(texts)
                feature_names = vectorizer.get_feature_names_out()
                counts = count_matrix.sum(axis=0).A1

                word_freq = {
                    feature_names[i]: int(counts[i]) for i in range(len(feature_names))
                }
        except Exception as e:
            print(f"Error generando word cloud: {e}")

        # === ENTITY NETWORK ===
        entity_network = {"nodes": [], "links": []}

        nlp = get_nlp_model()
        if nlp:
            all_entities = []
            for ref in referencias[:30]:  # Primeras 30 referencias
                if not ref.contenido:
                    continue
                doc = nlp(ref.contenido[:1000])
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
                if not ref.contenido:
                    continue
                doc = nlp(ref.contenido[:1000])
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

        # Crear usuario
        usuario = Usuario(nombre=nombre, email=email)
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
        return redirect(next_page or url_for("home"))

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
    """Pantalla principal de selección de proyectos del usuario actual"""
    # Solo proyectos del usuario autenticado
    proyectos = (
        Proyecto.query.filter_by(user_id=current_user.id)
        .order_by(Proyecto.creado_en.desc())
        .all()
    )

    # Obtener proyecto activo de la sesión
    proyecto_activo_id = session.get("proyecto_activo_id")

    # Calcular estadísticas para cada proyecto
    proyectos_con_stats = []
    for p in proyectos:
        proyectos_con_stats.append(
            {
                "id": p.id,
                "nombre": p.nombre,
                "descripcion": p.descripcion,
                "tipo": p.tipo,
                "activo": p.activo,
                "creado_en": p.creado_en,
                "num_articulos": Prensa.query.filter_by(proyecto_id=p.id).count(),
                "num_publicaciones": Publicacion.query.filter_by(
                    proyecto_id=p.id
                ).count(),
                "es_activo": p.id == proyecto_activo_id,
            }
        )

    return render_template("proyectos.html", proyectos=proyectos_con_stats)


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
            f'📌 Proyecto "{proyecto.nombre}" desactivado. No hay proyecto activo actualmente.',
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
    
    # Parsear JSON fields
    if articulo.get('autores'):
        articulo['autores'] = json.loads(articulo['autores'])
    if articulo.get('palabras_clave'):
        articulo['palabras_clave'] = json.loads(articulo['palabras_clave'])
    if articulo.get('keywords'):
        articulo['keywords'] = json.loads(articulo['keywords'])
    if articulo.get('contenido_json'):
        articulo['contenido_json'] = json.loads(articulo['contenido_json'])
    
    return render_template('articulo_editor.html', 
                         proyecto=proyecto, 
                         articulo=articulo)


@app.route("/api/articulos/guardar", methods=['POST'])
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
                'proyecto_id': datos['proyectoId'],
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
                   numero_referencia, incluido
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
        'incluido': getattr(n, 'incluido', False)
    } for n in noticias])


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
        """)
        
        db.session.execute(query, {
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
        
        nuevo_id = db.session.execute(text("SELECT last_insert_rowid()")).scalar()
        
        flash("Artículo duplicado correctamente", "success")
        return redirect(url_for('articulo_editar', articulo_id=nuevo_id))
    
    except Exception as e:
        db.session.rollback()
        flash(f"Error al duplicar artículo: {str(e)}", "danger")
        return redirect(url_for('articulos_lista', proyecto_id=original.proyecto_id))


def calcular_palabras_totales(secciones):
    """Calcular total de palabras en todas las secciones"""
    total = 0
    for seccion in secciones:
        contenido_html = seccion.get('contenido_html', '')
        # Quitar HTML tags y contar palabras
        texto_plano = re.sub(r'<[^>]+>', '', contenido_html)
        palabras = len([p for p in texto_plano.split() if p.strip()])
        total += palabras
    return total


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
        from pdf_generator import generar_pdf_articulo
        
        # Obtener datos (mismo código que exportar_pdf pero sin as_attachment)
        articulo_data = db.session.execute(
            text("SELECT * FROM articulos_cientificos WHERE id = :id"),
            {'id': articulo_id}
        ).fetchone()
        
        if not articulo_data or articulo_data.user_id != current_user.id:
            return abort(403)
        
        articulo = dict(articulo_data._mapping)
        articulo['autores'] = json.loads(articulo.get('autores', '[]'))
        articulo['palabras_clave'] = json.loads(articulo.get('palabras_clave', '[]'))
        articulo['keywords'] = json.loads(articulo.get('keywords', '[]'))
        articulo['contenido_json'] = json.loads(articulo.get('contenido_json', '{}'))
        
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
        return f"Error: {str(e)}", 500


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
    
    articulo = dict(articulo_data._mapping)
    
    # Obtener coautores actuales
    coautores_ids = json.loads(articulo.get('coautores', '[]'))
    coautores = []
    for user_id in coautores_ids:
        user = Usuario.query.get(user_id)
        if user:
            coautores.append(user)
    
    # Obtener comentarios de revisión
    comentarios = json.loads(articulo.get('comentarios_revision', '[]'))
    
    return render_template('articulo_colaboradores.html',
                         articulo=articulo,
                         coautores=coautores,
                         comentarios=comentarios)


@app.route("/api/articulos/<int:articulo_id>/agregar-colaborador", methods=['POST'])
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
