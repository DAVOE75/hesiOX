import re
import html
import os
import subprocess
from datetime import datetime
from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify, send_file, current_app
from flask_login import login_required, current_user
from extensions import db
from models import Hemeroteca, Publicacion, Prensa

maintenance_bp = Blueprint('maintenance', __name__)


# Redefining admin_required here to avoid circular imports with app.py
from functools import wraps

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash("Debes iniciar sesión para acceder a esta página.", "warning")
            return redirect(url_for("auth.login"))
        
        if current_user.rol != "admin":
            flash("No tienes permisos para acceder al panel de administración.", "danger")
            return redirect(url_for("dashboard"))
        
        return f(*args, **kwargs)
    return decorated_function

@maintenance_bp.route("/api/admin/restart", methods=['POST'])
@login_required
@admin_required
def api_admin_restart():
    """Reinicia el servidor tocando los archivos de entrada"""
    try:
        # Tocar passenger_wsgi.py forcea el reinicio en Passenger
        import os
        import time
        from cache_config import cache
        
        # 0. Limpiar caché de la aplicación
        try:
            cache.clear()
            print("[INFO] Caché de aplicación limpiada antes del reinicio")
        except Exception as e:
            print(f"[WARN] No se pudo limpiar la caché: {e}")
        
        # Paths a tocar
        paths = [
            os.path.join(current_app.root_path, 'passenger_wsgi.py'),
            os.path.join(current_app.root_path, 'tmp', 'restart.txt')
        ]
        
        touched = []
        for p in paths:
            if os.path.exists(p):
                # Update timestamp
                try:
                    os.utime(p, None)
                    touched.append(os.path.basename(p))
                except Exception as e:
                    print(f"[WARN] No se pudo tocar {p}: {e}")
            else:
                # Crear si no existe (caso restart.txt)
                try:
                    # Asegurar que el directorio existe
                    os.makedirs(os.path.dirname(p), exist_ok=True)
                    with open(p, 'a'):
                        os.utime(p, None)
                    touched.append(os.path.basename(p))
                except Exception as e:
                    print(f"[WARN] No se pudo crear {p}: {e}")
        
        flash(f"Servidor reiniciado correctamente. Los cambios deberían ser visibles en unos segundos.", "success")
        return redirect(url_for('admin_panel'))
        
    except Exception as e:
        flash(f"Error reiniciando servidor: {str(e)}", "danger")
        return redirect(url_for('admin_panel'))

@maintenance_bp.route("/api/admin/free-ram", methods=['POST'])
@login_required
@admin_required
def api_admin_free_ram():
    """Libera RAM del servidor (GC + Drop Caches)"""
    try:
        import gc
        import psutil
        from cache_config import cache
        
        # 1. Limpiar caché de aplicación Flask
        cache.clear()
        
        # 2. Garbage Collection de Python
        gc.collect()
        
        # 3. Intentar liberar caché del sistema
        try:
             # Sync para asegurar que datos en memoria vayan a disco antes de borrar caché
             subprocess.run(['sync'])
             # Escribir 3 en drop_caches (libera pagecache, dentries e inodes)
             with open('/proc/sys/vm/drop_caches', 'w') as f:
                 f.write('3')
        except Exception as e:
            print(f"[WARN] No se pudo hacer drop_caches: {e}")
            
        # 4. Obtener nuevas métricas
        mem = psutil.virtual_memory()
        ram_gb = mem.total / (1024**3)
        ram_usada = mem.used / (1024**3)
        ram_percent = mem.percent
        
        return jsonify({
            "success": True, 
            "message": "Memoria liberada correctamente.",
            "ram_total": f"{ram_gb:.2f}",
            "ram_used": f"{ram_usada:.2f}",
            "ram_percent": ram_percent
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

def clean_html(text):
    """
    Remove HTML tags and unescape entities.
    """
    if not text:
        return text
    
    # 1. Unescape HTML entities (&oacute; -> ó)
    text = html.unescape(text)
    
    # 2. Remove HTML tags using regex
    clean = re.compile('<.*?>')
    text = re.sub(clean, '', text)
    
    # 3. Clean extra whitespace
    text = text.strip()
    
    return text

@maintenance_bp.route("/admin/db-clean-html", methods=["POST"])
@login_required
def clean_database_html():
    """
    Rutina de mantenimiento para limpiar etiquetas HTML de campos de texto.
    """
    # Verificar seguridad (solo usuarios autorizados, idealmente admin)
    # Si tienes roles: if current_user.rol != 'admin': ...
    
    stats = {
        'hemerotecas': 0,
        'publicaciones': 0,
        'articulos': 0
    }
    
    try:
        # 1. Limpiar Hemerotecas (resumen_corpus)
        hemerotecas = Hemeroteca.query.all()
        for h in hemerotecas:
            if h.resumen_corpus and ('<' in h.resumen_corpus or '&' in h.resumen_corpus):
                old = h.resumen_corpus
                new = clean_html(old)
                if old != new:
                    h.resumen_corpus = new
                    stats['hemerotecas'] += 1
        
        # 2. Limpiar Publicaciones (descripcion)
        publicaciones = Publicacion.query.all()
        for p in publicaciones:
            if p.descripcion and ('<' in p.descripcion or '&' in p.descripcion):
                old = p.descripcion
                new = clean_html(old)
                if old != new:
                    p.descripcion = new
                    stats['publicaciones'] += 1
                    
        # 3. Limpiar Prensa (contenido, notas, resumen)
        articulos = Prensa.query.all()
        for a in articulos:
            changed = False
            
            # Contenido
            if a.contenido and ('<' in a.contenido or '&' in a.contenido):
                a.contenido = clean_html(a.contenido)
                changed = True
            
            # Notas
            if a.notas and ('<' in a.notas or '&' in a.notas):
                a.notas = clean_html(a.notas)
                changed = True

            # Resumen
            if a.resumen and ('<' in a.resumen or '&' in a.resumen):
                a.resumen = clean_html(a.resumen)
                changed = True
                
            if changed:
                stats['articulos'] += 1
                
        db.session.commit()
        
        msg = f"Limpieza completada: {stats['hemerotecas']} hemerotecas, {stats['publicaciones']} publicaciones, {stats['articulos']} artículos actualizados."
        flash(f"✅ {msg}", "success")
        
    except Exception as e:
        db.session.rollback()
        flash(f"❌ Error durante la limpieza: {str(e)}", "danger")
        
    # Redirigir de vuelta al panel de admin o home
    return redirect(url_for('admin_panel'))


@maintenance_bp.route("/admin/db-backup", methods=["POST"])
@login_required
def backup_database():
    """
    Genera un backup de la base de datos PostgreSQL y lo descarga.
    """
    # Verificar permisos (admin)
    if current_user.rol != 'admin':
        flash("❌ Acceso denegado", "danger")
        return redirect(url_for('dashboard'))

    try:
        # Obtener URL de la base de datos
        db_url = current_app.config['SQLALCHEMY_DATABASE_URI']
        
        # Parsear la URL para obtener credenciales
        from sqlalchemy.engine.url import make_url
        url = make_url(db_url)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"backup_bibliografia_{timestamp}.sql"
        
        # Usar carpeta db_backups en la raíz del proyecto
        # current_app.root_path apunta a la carpeta donde está app.py
        backup_dir = os.path.join(current_app.root_path, 'db_backups')
        os.makedirs(backup_dir, exist_ok=True)
        filepath = os.path.join(backup_dir, filename)
        
        # Configurar variables de entorno para pg_dump
        env = os.environ.copy()
        if url.password:
            env['PGPASSWORD'] = url.password
        
        # Comando pg_dump
        # Intentar obtener ruta desde variable de entorno o usar 'pg_dump' por defecto
        pg_dump_path = os.getenv('PG_DUMP_PATH', 'pg_dump')
        
        command = [
            pg_dump_path,
            '-h', url.host or 'localhost',
            '-p', str(url.port or 5432),
            '-U', url.username or 'postgres',
            '-F', 'p', # Formato plano (SQL)
            '-f', filepath,
            url.database
        ]
        
        # Ejecutar comando
        try:
            process = subprocess.run(command, env=env, capture_output=True, text=True)
            
            if process.returncode != 0:
                raise Exception(f"pg_dump error: {process.stderr}")
                
            return send_file(filepath, as_attachment=True, download_name=filename)
            
        except FileNotFoundError:
            import platform
            os_name = platform.system()
            example_path = "C:\\Program Files\\PostgreSQL\\15\\bin\\pg_dump.exe" if os_name == "Windows" else "/usr/bin/pg_dump"
            raise Exception(f"No se encontró el ejecutable 'pg_dump'. Por favor, asegúrate de que PostgreSQL está instalado y añade la ruta correcta a la variable PG_DUMP_PATH en el archivo .env (Ej: {example_path})")
            
    except Exception as e:
        current_app.logger.error(f"Error backup DB: {str(e)}")
        flash(f"❌ Error generando backup: {str(e)}", "danger")
        return redirect(url_for('admin_panel'))
@maintenance_bp.route("/admin/project-download", methods=["POST"])
@login_required
def download_project():
    """
    Comprime la carpeta del proyecto entera (excepto venv, .git, etc.) y permite descargarla.
    """
    if current_user.rol != 'admin':
        flash("❌ Acceso denegado", "danger")
        return redirect(url_for('dashboard'))

    import zipfile
    import tempfile

    try:
        # Nombre del archivo ZIP con timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        zip_filename = f"hesiox_project_full_{timestamp}.zip"
        
        # Crear un archivo temporal para el ZIP
        temp_dir = tempfile.gettempdir()
        zip_filepath = os.path.join(temp_dir, zip_filename)
        
        root_dir = current_app.root_path
        
        # Carpetas y archivos a incluir (Opt-in) para garantizar bajo peso
        include_dirs = {
            'routes', 'static', 'templates', 'scripts', 'docs',
            'services', 'migrations', 'extensions'
        }
        
        # Crear carpeta de exportación si no existe
        export_dir = os.path.join(current_app.root_path, 'exports')
        os.makedirs(export_dir, exist_ok=True)
        zip_filepath = os.path.join(export_dir, zip_filename)
        
        root_dir = current_app.root_path
        
        # Archivos top-level válidos (todo lo que es código base)
        valid_extensions = ('.py', '.md', '.txt', '.json', '.bat', '.html', '.css', '.js', '.env.example', '.env')
        exclude_specific = {'passenger_wsgi.py'} # O los que decidas no bajar

        with zipfile.ZipFile(zip_filepath, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(root_dir):
                rel_path = os.path.relpath(root, root_dir)
                
                # Excluir carpetas pesadas o no deseadas que no están en include_dirs pero walk sí ve
                if rel_path == '.':
                    dirs[:] = [d for d in dirs if d in include_dirs]
                
                # Procesar archivos
                for file in files:
                    # Evitar archivos ocultos o temporales
                    if file == '.DS_Store' or file.startswith('._') or file.endswith('.pyc'):
                        continue
                        
                    file_path = os.path.join(root, file)
                    
                    # Si es la raíz, solo archivos de código permitidos
                    if rel_path == '.':
                        if not (any(file.endswith(ext) for ext in valid_extensions) and file not in exclude_specific):
                            continue
                    
                    # Si es static/uploads, ya lo filtramos en dirs[:] si quisiéramos, 
                    # pero vamos a ser más precisos:
                    if 'static/uploads' in rel_path or 'static\\uploads' in rel_path:
                        continue
                    
                    # Agregar al zip
                    arcname = os.path.relpath(file_path, root_dir)
                    zipf.write(file_path, arcname)
                        
        return send_file(zip_filepath, as_attachment=True, download_name=zip_filename)
        
    except Exception as e:
        current_app.logger.error(f"Error zipping project: {str(e)}")
        flash(f"❌ Error generando ZIP del proyecto: {str(e)}", "danger")
        return redirect(url_for('admin_panel'))
