"""
Rutas de autenticación
Incluye: login, logout, registro
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_user, logout_user, current_user, login_required
from datetime import datetime

from extensions import db
from models import Usuario, ServicioIDE
from limiter import limiter
from security_logger import log_login_attempt, log_logout, log_registration
from schemas import LoginSchema, RegistroSchema
from marshmallow import ValidationError

auth_bp = Blueprint('auth', __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("20 per minute")  # Aumentado de 5 a 20 para desarrollo
def login():
    """Inicio de sesión con validación y logging"""
    if current_user.is_authenticated:
        return redirect(url_for("auth.perfil"))

    if request.method == "POST":
        # Validar datos de entrada
        schema = LoginSchema()
        try:
            data = schema.load(request.form)
        except ValidationError as err:
            for field, messages in err.messages.items():
                for message in messages:
                    flash(message, "danger")
            return redirect(url_for("auth.login"))

        email = data['email'].strip().lower()
        password = data['password']
        ip_address = request.remote_addr
        user_agent = request.headers.get('User-Agent')

        usuario = Usuario.query.filter_by(email=email).first()

        if usuario is None or not usuario.check_password(password):
            log_login_attempt(email, False, ip_address, user_agent)
            flash("Correo o contraseña incorrectos.", "danger")
            return redirect(url_for("auth.login"))

        log_login_attempt(email, True, ip_address, user_agent)
        login_user(usuario)
        session['force_sidebar_collapse'] = True
        flash(f"Bienvenido/a, {usuario.nombre}.", "success")

        next_page = request.args.get("next")
        if next_page:
            return redirect(next_page)
        
        # New users (no projects) go to Profile; returning users go to Projects
        if usuario.proyectos:
            return redirect(url_for("proyectos.listar"))
        
        return redirect(url_for("auth.perfil"))

    return render_template("login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    """Cerrar sesión con logging"""
    email = current_user.email
    ip_address = request.remote_addr
    
    log_logout(email, ip_address)
    session.pop("proyecto_activo_id", None)
    logout_user()
    flash("Sesión cerrada.", "info")
    return redirect(url_for("home"))


@auth_bp.route("/registro", methods=["GET", "POST"])
@limiter.limit("3 per hour")
def registro():
    """Registro de usuario con validación"""
    if current_user.is_authenticated:
        return redirect(url_for("auth.perfil"))

    if request.method == "POST":
        schema = RegistroSchema()
        try:
            # Crear copia mutable para manejar compatibilidad con versiones cacheadas del frontend
            form_data = request.form.copy()
            if 'password2' in form_data and 'password_confirm' not in form_data:
                form_data['password_confirm'] = form_data['password2']
            
            data = schema.load(form_data)
        except ValidationError as err:
            for field, messages in err.messages.items():
                for message in messages:
                    flash(message, "danger")
            return redirect(url_for("auth.registro"))

        nombre = data['nombre'].strip()
        email = data['email'].strip().lower()
        password = data['password']
        ip_address = request.remote_addr

        if Usuario.query.filter_by(email=email).first():
            log_registration(email, False, ip_address, "Email ya existe")
            flash("Este email ya está registrado.", "warning")
            return redirect(url_for("auth.registro"))

        usuario = Usuario(nombre=nombre, email=email, rol="user")
        usuario.set_password(password)
        db.session.add(usuario)
        db.session.commit()

        log_registration(email, True, ip_address)
        flash("Cuenta creada correctamente. Ya puedes iniciar sesión.", "success")
        return redirect(url_for("auth.login"))

    # GET request: mostrar formulario de registro
    return render_template("registro.html")


@auth_bp.route("/perfil", methods=["GET", "POST"])
@login_required
def perfil():
    """Gestión de perfil y API Keys personales"""
    import os
    from werkzeug.utils import secure_filename
    from flask import current_app

    if request.method == "POST":
        # Manejo de Foto de Perfil
        if 'foto_perfil' in request.files:
            file = request.files['foto_perfil']
            if file and file.filename != '':
                try:
                    # Asegurar carpeta de perfiles
                    perfiles_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'perfiles')
                    os.makedirs(perfiles_dir, exist_ok=True)
                    
                    ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else 'jpg'
                    filename = secure_filename(f"user_{current_user.id}_{int(datetime.now().timestamp())}.{ext}")
                    file_path = os.path.join(perfiles_dir, filename)
                    file.save(file_path)
                    
                    # Guardar ruta relativa
                    current_user.foto_perfil = f"uploads/perfiles/{filename}"
                except Exception as e:
                    flash(f"Error al subir la foto: {str(e)}", "danger")

        # Datos Personales
        current_user.nombre = request.form.get("nombre", current_user.nombre).strip()
        current_user.institucion = request.form.get("institucion", "").strip()
        current_user.orcid = request.form.get("orcid", "").strip()
        current_user.telefono = request.form.get("telefono", "").strip()

        # Cambio de Contraseña
        old_password = request.form.get("old_password")
        new_password = request.form.get("new_password")
        confirm_password = request.form.get("confirm_password")

        if old_password and new_password:
            if not current_user.check_password(old_password):
                flash("La contraseña actual es incorrecta.", "danger")
            elif new_password != confirm_password:
                flash("La nueva contraseña y su confirmación no coinciden.", "danger")
            else:
                current_user.set_password(new_password)
                flash("Contraseña actualizada correctamente.", "success")

        # API Keys
        current_user.api_key_gemini = request.form.get("api_key_gemini", "").strip()
        current_user.api_key_openai = request.form.get("api_key_openai", "").strip()
        current_user.api_key_anthropic = request.form.get("api_key_anthropic", "").strip()
        
        # Flags de activación
        current_user.ai_gemini_active = 'ai_gemini_active' in request.form
        current_user.ai_openai_active = 'ai_openai_active' in request.form
        current_user.ai_anthropic_active = 'ai_anthropic_active' in request.form
        
        db.session.commit()
        flash("Perfil actualizado correctamente.", "success")
        return redirect(url_for("auth.perfil"))
        
    return render_template("perfil.html")


# ─── API: Catálogo Global IDE (compartido) ───────────────────────────────────

@auth_bp.route("/api/ide/catalogo", methods=["GET"])
@login_required
def get_ide_catalogo():
    """Devuelve el catálogo global de servicios WMS/WMTS compartido."""
    from flask import jsonify
    servicios = ServicioIDE.query.order_by(ServicioIDE.pais, ServicioIDE.nombre).all()
    return jsonify({"success": True, "data": [s.to_dict() for s in servicios]})


@auth_bp.route("/api/ide/catalogo", methods=["POST"])
@login_required
def add_ide_catalogo():
    """Añade un servicio nuevo al catálogo global (si no existe ya)."""
    from flask import jsonify, request as req
    data = req.get_json(force=True) or {}
    url = (data.get('url') or '').strip()
    svc_type = data.get('type', 'WMS').upper()
    capas = (data.get('layers') or '').strip() or None
    if not url:
        return jsonify({'success': False, 'error': 'URL requerida'}), 400
    # Consistent check: only URL and Type to avoid duplication across different layer selections
    existing = ServicioIDE.query.filter_by(url=url, tipo=svc_type).first()
    if existing:
        return jsonify({'success': True, 'id': existing.id, 'already_exists': True})
    srv = ServicioIDE(
        nombre=(data.get('name') or url).strip(),
        tipo=svc_type,
        url=url,
        capas=capas,
        formato=data.get('format', 'image/png'),
        attribution=data.get('attribution', ''),
        pais=data.get('country', ''),
        categoria=data.get('category', ''),
        opacidad=float(data.get('opacity', 0.85)),
        creado_por=current_user.id,
    )
    db.session.add(srv)
    db.session.commit()
    return jsonify({'success': True, 'id': srv.id}), 201


# ─── API: IDE Personal WMS/WMTS ──────────────────────────────────────────────

@auth_bp.route("/api/user/wms-favoritos", methods=["GET"])
@login_required
def get_wms_favoritos():
    """Returns the authenticated user's WMS/WMTS IDE favorites list."""
    import json
    try:
        favs = json.loads(current_user.wms_favoritos or '[]')
    except Exception:
        favs = []
    from flask import jsonify
    return jsonify(favs)


@auth_bp.route("/api/user/wms-favoritos", methods=["POST"])
@login_required
def add_wms_favorito():
    """Adds a WMS/WMTS service to the user's IDE favorites.
    Also registers the service in the shared global catalog if not already present.
    """
    import json, uuid
    from flask import jsonify, request as req
    data = req.get_json(force=True) or {}

    # Required fields
    url = (data.get('url') or '').strip()
    name = (data.get('name') or url or 'Sin nombre').strip()
    svc_type = data.get('type', 'WMS').upper()  # 'WMS' | 'WMTS'
    capas = (data.get('layers') or '').strip() or None

    if not url:
        return jsonify({'success': False, 'error': 'URL requerida'}), 400

    try:
        favs = json.loads(current_user.wms_favoritos or '[]')
    except Exception:
        favs = []

    # Avoid duplicating same URL+type in favorites
    if any(f.get('url') == url and f.get('type') == svc_type for f in favs):
        return jsonify({'success': False, 'error': 'Servicio ya en favoritos'}), 409

    # ── Register in global catalog if new ────────────────────────────────────
    # We only check URL and Type to avoid duplicating the service if the user chooses different layers
    existing_global = ServicioIDE.query.filter_by(url=url, tipo=svc_type).first()
    if not existing_global:
        srv = ServicioIDE(
            nombre=name,
            tipo=svc_type,
            url=url,
            capas=capas,
            formato=data.get('format', 'image/png'),
            attribution=data.get('attribution', ''),
            pais=data.get('country', ''),
            categoria=data.get('category', ''),
            opacidad=float(data.get('opacity', 0.85)),
            creado_por=current_user.id,
        )
        db.session.add(srv)
    # ─────────────────────────────────────────────────────────────────────────

    entry = {
        'id': str(uuid.uuid4()),
        'name': name,
        'type': svc_type,
        'url': url,
        'layers': capas or '',
        'format': data.get('format', 'image/png'),
        'attribution': data.get('attribution', ''),
        'opacity': float(data.get('opacity', 0.85)),
        'zIndex': int(data.get('zIndex', 10)),
        'country': data.get('country', ''),
        'category': data.get('category', ''),
        'active': bool(data.get('active', True)),
    }
    favs.append(entry)
    current_user.wms_favoritos = json.dumps(favs, ensure_ascii=False)
    db.session.commit()
    return jsonify({'success': True, 'id': entry['id']})


@auth_bp.route("/api/user/wms-favoritos/<fav_id>", methods=["DELETE"])
@login_required
def delete_wms_favorito(fav_id):
    """Removes a WMS/WMTS service from the user's IDE favorites."""
    import json
    from flask import jsonify
    try:
        favs = json.loads(current_user.wms_favoritos or '[]')
    except Exception:
        favs = []
    original_len = len(favs)
    favs = [f for f in favs if f.get('id') != fav_id]
    if len(favs) == original_len:
        return jsonify({'success': False, 'error': 'Favorito no encontrado'}), 404
    current_user.wms_favoritos = json.dumps(favs, ensure_ascii=False)
    db.session.commit()
    return jsonify({'success': True})


@auth_bp.route("/api/user/wms-favoritos/<fav_id>", methods=["PATCH"])
@login_required
def patch_wms_favorito(fav_id):
    """Toggles active flag or updates a single field on a favorite."""
    import json
    from flask import jsonify, request as req
    data = req.get_json(force=True) or {}
    try:
        favs = json.loads(current_user.wms_favoritos or '[]')
    except Exception:
        return jsonify({'success': False, 'error': 'Error interno'}), 500
    for f in favs:
        if f.get('id') == fav_id:
            for key in ('active', 'name', 'opacity', 'zIndex', 'url', 'type', 'layers', 'country', 'attribution'):
                if key in data:
                    val = data[key]
                    if key == 'type' and isinstance(val, str):
                        val = val.upper()
                    f[key] = val
            break
    else:
        return jsonify({'success': False, 'error': 'No encontrado'}), 404
    current_user.wms_favoritos = json.dumps(favs, ensure_ascii=False)
    db.session.commit()
    return jsonify({'success': True})

# ─────────────────────────────────────────────────────────────────────────────
