"""
Blueprint de Blog para HesiOX
- Rutas públicas: listado, detalle de entrada
- Rutas protegidas (login): panel admin, crear, editar, eliminar, publicar
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, abort
from flask_login import login_required, current_user
from extensions import db, csrf
from models import BlogPost, Usuario, BlogSubscription
from services.email_service import EmailService
from datetime import datetime
import re
import os
from werkzeug.utils import secure_filename

blog_bp = Blueprint('blog', __name__, url_prefix='/blog')
UPLOAD_BLOG_FOLDER = 'static/uploads/blog'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def _allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _slugify(text: str) -> str:
    """Convierte un título en un slug URL-safe."""
    import unicodedata
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')
    text = re.sub(r'[^\w\s-]', '', text).strip().lower()
    text = re.sub(r'[-\s]+', '-', text)
    return text


def _ensure_unique_slug(slug: str, exclude_id: int = None) -> str:
    """Garantiza que el slug sea único en la BD, añadiendo sufijo numérico si hace falta."""
    base_slug = slug
    counter = 1
    while True:
        q = BlogPost.query.filter_by(slug=slug)
        if exclude_id:
            q = q.filter(BlogPost.id != exclude_id)
        if not q.first():
            break
        slug = f"{base_slug}-{counter}"
        counter += 1
    return slug


# ---------------------------------------------------------------------------
# RUTAS PÚBLICAS
# ---------------------------------------------------------------------------

@blog_bp.route('/')
def lista():
    """Listado público de entradas del blog (paginado, solo publicadas)."""
    pagina = request.args.get('pagina', 1, type=int)
    categoria_filtro = request.args.get('categoria', '')
    etiqueta_filtro = request.args.get('etiqueta', '')

    q = BlogPost.query.filter_by(publicado=True)

    if categoria_filtro:
        q = q.filter_by(categoria=categoria_filtro)
    if etiqueta_filtro:
        q = q.filter(BlogPost.etiquetas.ilike(f'%{etiqueta_filtro}%'))

    q = q.order_by(BlogPost.destacado.desc(), BlogPost.publicado_en.desc())

    paginacion = q.paginate(page=pagina, per_page=9, error_out=False)
    entradas = paginacion.items

    # Categorías disponibles para filtros
    categorias = db.session.query(BlogPost.categoria).filter_by(publicado=True)\
        .distinct().order_by(BlogPost.categoria).all()
    categorias = [c[0] for c in categorias if c[0]]

    return render_template(
        'blog/lista.html',
        entradas=entradas,
        paginacion=paginacion,
        categorias=categorias,
        categoria_filtro=categoria_filtro,
        etiqueta_filtro=etiqueta_filtro,
    )


@blog_bp.route('/<slug>')
def detalle(slug):
    """Vista pública de una entrada individual del blog."""
    entrada = BlogPost.query.filter_by(slug=slug, publicado=True).first_or_404()

    # Incrementar contador de vistas
    try:
        entrada.vistas = (entrada.vistas or 0) + 1
        db.session.commit()
    except Exception:
        db.session.rollback()

    # Entradas relacionadas (misma categoría, excluida la actual)
    relacionadas = BlogPost.query.filter(
        BlogPost.publicado == True,
        BlogPost.id != entrada.id,
        BlogPost.categoria == entrada.categoria
    ).order_by(BlogPost.publicado_en.desc()).limit(3).all()

    return render_template('blog/detalle.html', entrada=entrada, relacionadas=relacionadas)


@blog_bp.route('/subscribe', methods=['POST'])
@csrf.exempt
def subscribe():
    """Registra un nuevo email para subscripción al blog."""
    email = request.form.get('email', '').strip().lower()
    
    if not email:
        return jsonify({'success': False, 'message': 'Email requerido.'}), 400
    
    # Validación básica de email
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        return jsonify({'success': False, 'message': 'Email inválido.'}), 400
        
    try:
        # Verificar si ya existe
        existing = BlogSubscription.query.filter_by(email=email).first()
        if existing:
            if existing.activo:
                return jsonify({'success': True, 'message': 'Ya estás suscrito. ¡Gracias!'})
            else:
                existing.activo = True
                db.session.commit()
                return jsonify({'success': True, 'message': '¡Re-suscrito con éxito!'})
        
        # Crear nueva suscripción
        new_sub = BlogSubscription(email=email)
        db.session.add(new_sub)
        db.session.commit()
        
        return jsonify({'success': True, 'message': '¡Te has suscrito con éxito!'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error en el servidor: {str(e)}'}), 500


# ---------------------------------------------------------------------------
# RUTAS DE ADMINISTRACIÓN (requieren login)
# ---------------------------------------------------------------------------

@blog_bp.route('/admin/')
@login_required
def admin_lista():
    """Panel interno de gestión del blog."""
    filtro = request.args.get('filtro', 'todos')

    q = BlogPost.query
    if current_user.rol != 'admin':
        q = q.filter_by(autor_id=current_user.id)

    if filtro == 'publicados':
        q = q.filter_by(publicado=True)
    elif filtro == 'borradores':
        q = q.filter_by(publicado=False)

    entradas = q.order_by(BlogPost.creado_en.desc()).all()
    
    # Conteo de suscriptores para el panel (solo si es admin)
    total_suscriptores = 0
    if current_user.rol == 'admin':
        total_suscriptores = BlogSubscription.query.count()

    return render_template(
        'blog/admin_lista.html', 
        entradas=entradas, 
        filtro=filtro,
        total_suscriptores=total_suscriptores
    )


@blog_bp.route('/admin/nueva', methods=['GET', 'POST'])
@login_required
def admin_nueva():
    """Crear una nueva entrada de blog."""
    if request.method == 'POST':
        titulo = request.form.get('titulo', '').strip()
        if not titulo:
            flash('El título es obligatorio.', 'danger')
            return redirect(url_for('blog.admin_nueva'))

        slug_base = _slugify(titulo)
        slug = _ensure_unique_slug(slug_base or f"entrada-{int(datetime.utcnow().timestamp())}")

        publicado = request.form.get('publicado') == '1'
        publicado_en = datetime.utcnow() if publicado else None

        # Buscar el usuario administrador por defecto (Administrador)
        admin_default = Usuario.query.filter_by(nombre='Administrador').first()
        autor_id = admin_default.id if admin_default else current_user.id

        entrada = BlogPost(
            titulo=titulo,
            slug=slug,
            resumen=request.form.get('resumen', '').strip() or None,
            contenido=request.form.get('contenido', ''),
            categoria=request.form.get('categoria', 'General').strip() or 'General',
            etiquetas=request.form.get('etiquetas', '').strip() or None,
            publicado=publicado,
            publicado_en=publicado_en,
            destacado='destacado' in request.form,
            autor_id=autor_id,
        )

        # Manejo de imagen de portada (Upload)
        try:
            file_portada = request.files.get('file_portada')
            if file_portada and file_portada.filename and _allowed_file(file_portada.filename):
                filename = secure_filename(f"blog_{int(datetime.utcnow().timestamp())}_{file_portada.filename}")
                upload_path = os.path.join('static', 'uploads', 'blog')
                if not os.path.exists(upload_path):
                    os.makedirs(upload_path)
                file_portada.save(os.path.join(upload_path, filename))
                entrada.imagen_portada = f"uploads/blog/{filename}"
            else:
                entrada.imagen_portada = request.form.get('imagen_portada', '').strip() or None
        except Exception as e:
            print(f"Error subiendo imagen: {e}")
            entrada.imagen_portada = request.form.get('imagen_portada', '').strip() or None

        db.session.add(entrada)
        db.session.commit()
        flash('Entrada guardada como borrador.', 'success')
        return redirect(url_for('blog.admin_editar', entrada_id=entrada.id))

    return render_template('blog/editor.html', entrada=None, accion='nueva')


@blog_bp.route('/admin/<int:entrada_id>/editar', methods=['GET', 'POST'])
@login_required
def admin_editar(entrada_id):
    """Editar una entrada existente."""
    import sys
    print(f"DEBUG: admin_editar ID={entrada_id} Method={request.method}", file=sys.stderr)
    entrada = BlogPost.query.get(entrada_id)
    if not entrada:
        abort(404)
    if current_user.rol != 'admin' and entrada.autor_id != current_user.id:
        abort(403)

    if request.method == 'POST':
        try:
            titulo = request.form.get('titulo', '').strip()
            if not titulo:
                flash('El título es obligatorio.', 'danger')
                return redirect(url_for('blog.admin_editar', entrada_id=entrada_id))

            # Solo regenerar slug si el título cambió
            nuevo_slug = request.form.get('slug', '').strip()
            if not nuevo_slug:
                nuevo_slug = _slugify(titulo)
            nuevo_slug = _ensure_unique_slug(nuevo_slug, exclude_id=entrada.id)

            entrada.titulo = titulo
            entrada.slug = nuevo_slug
            entrada.resumen = request.form.get('resumen', '').strip() or None
            entrada.contenido = request.form.get('contenido', '')
            
            # Manejo de imagen de portada
            if 'delete_portada' in request.form and request.form.get('delete_portada') == '1':
                entrada.imagen_portada = None
            
            file_portada = request.files.get('file_portada')
            if file_portada and file_portada.filename and _allowed_file(file_portada.filename):
                filename = secure_filename(f"blog_{entrada.id}_{int(datetime.utcnow().timestamp())}_{file_portada.filename}")
                upload_path = os.path.join('static', 'uploads', 'blog')
                if not os.path.exists(upload_path):
                    os.makedirs(upload_path)
                file_portada.save(os.path.join(upload_path, filename))
                entrada.imagen_portada = f"uploads/blog/{filename}"
            elif not entrada.imagen_portada: # Si no había imagen o se borró, ver si hay URL
                entrada.imagen_portada = request.form.get('imagen_portada', '').strip() or None

            entrada.categoria = request.form.get('categoria', 'General').strip() or 'General'
            entrada.etiquetas = request.form.get('etiquetas', '').strip() or None
            # Estado de publicación
            nueva_publicado = request.form.get('publicado') == '1'
            if nueva_publicado and not entrada.publicado:
                # Si se publica por primera vez o re-publica, actualizar fecha
                if not entrada.publicado_en:
                    entrada.publicado_en = datetime.utcnow()
            
            entrada.publicado = nueva_publicado
            entrada.destacado = 'destacado' in request.form
            entrada.modificado_en = datetime.utcnow()

            db.session.commit()
            flash('Entrada actualizada correctamente.', 'success')
            return redirect(url_for('blog.admin_editar', entrada_id=entrada.id))
        except Exception as e:
            db.session.rollback()
            import traceback
            error_details = traceback.format_exc()
            with open('/tmp/blog_error.log', 'a') as f:
                f.write(f"\n--- ERROR {datetime.utcnow()} ---\n{error_details}\n")
            flash(f'Error al guardar la entrada: {str(e)}', 'danger')
            return redirect(url_for('blog.admin_editar', entrada_id=entrada_id))

    return render_template('blog/editor.html', entrada=entrada, accion='editar')


@blog_bp.route('/admin/<int:entrada_id>/publicar', methods=['POST'])
@login_required
@csrf.exempt
def admin_publicar(entrada_id):
    """Alternar estado publicado/borrador de una entrada."""
    entrada = db.session.get(BlogPost, entrada_id)
    if not entrada:
        return jsonify({'success': False, 'error': 'No encontrada'}), 404
    if current_user.rol != 'admin' and entrada.autor_id != current_user.id:
        return jsonify({'success': False, 'error': 'Sin permiso'}), 403

    entrada.publicado = not entrada.publicado
    if entrada.publicado and not entrada.publicado_en:
        entrada.publicado_en = datetime.utcnow()
    db.session.commit()

    return jsonify({
        'success': True,
        'publicado': entrada.publicado,
        'label': 'Publicado' if entrada.publicado else 'Borrador',
    })


@blog_bp.route('/admin/<int:entrada_id>/notificar', methods=['POST'])
@login_required
@csrf.exempt
def admin_notificar(entrada_id):
    """Enviar notificación de nueva entrada a todos los suscriptores."""
    if current_user.rol != 'admin':
        return jsonify({'success': False, 'error': 'Solo administradores pueden enviar notificaciones'}), 403
        
    entrada = db.session.get(BlogPost, entrada_id)
    if not entrada:
        return jsonify({'success': False, 'error': 'Entrada no encontrada'}), 404
    
    if not entrada.publicado:
        return jsonify({'success': False, 'error': 'La entrada debe estar publicada para notificar'}), 404
    
    suscriptores = BlogSubscription.query.filter_by(activo=True).all()
    if not suscriptores:
        return jsonify({'success': False, 'error': 'No hay suscriptores activos'}), 400
        
    try:
        success, message = EmailService.send_newsletter(suscriptores, entrada)
        
        if success:
            entrada.notificado = True
            db.session.commit()
            return jsonify({'success': True, 'message': 'Notificación enviada correctamente'})
        else:
            # Si el servicio de correo falla por configuración, devolvemos 200 pero con el error para que el UI no se rompa
            return jsonify({'success': False, 'message': f'Error en el servicio de correo: {message}'}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error inesperado: {str(e)}'}), 200


@blog_bp.route('/admin/<int:entrada_id>/eliminar', methods=['POST'])
@login_required
@csrf.exempt
def admin_eliminar(entrada_id):
    """Eliminar definitivamente una entrada."""
    entrada = db.session.get(BlogPost, entrada_id)
    if not entrada:
        return jsonify({'success': False, 'error': 'No encontrada'}), 404
    if current_user.rol != 'admin' and entrada.autor_id != current_user.id:
        return jsonify({'success': False, 'error': 'Sin permiso'}), 403

    db.session.delete(entrada)
    db.session.commit()
    return jsonify({'success': True})


# ---------------------------------------------------------------------------
# GESTIÓN DE SUSCRIPTORES
# ---------------------------------------------------------------------------

@blog_bp.route('/admin/subscriptores')
@login_required
def admin_subscriptores():
    """Listado de suscriptores para administración."""
    if current_user.rol != 'admin':
        abort(403)
    
    subscriptores = BlogSubscription.query.order_by(BlogSubscription.creado_en.desc()).all()
    return render_template('blog/admin_subscriptores.html', subscriptores=subscriptores)


@blog_bp.route('/admin/subscriptores/<int:sub_id>/toggle', methods=['POST'])
@login_required
@csrf.exempt
def admin_subscriptor_toggle(sub_id):
    """Activar/Desactivar un suscriptor."""
    if current_user.rol != 'admin':
        return jsonify({'success': False, 'error': 'Sin permiso'}), 403
    
    sub = db.session.get(BlogSubscription, sub_id)
    if not sub:
        return jsonify({'success': False, 'error': 'No encontrado'}), 404
        
    sub.activo = not sub.activo
    db.session.commit()
    
    return jsonify({
        'success': True,
        'activo': sub.activo,
        'label': 'Activo' if sub.activo else 'Inactivo'
    })


@blog_bp.route('/admin/subscriptores/<int:sub_id>/eliminar', methods=['POST'])
@login_required
@csrf.exempt
def admin_subscriptor_eliminar(sub_id):
    """Eliminar definitivamente un suscriptor."""
    if current_user.rol != 'admin':
        return jsonify({'success': False, 'error': 'Sin permiso'}), 403
    
    sub = db.session.get(BlogSubscription, sub_id)
    if not sub:
        return jsonify({'success': False, 'error': 'No encontrado'}), 404
        
    db.session.delete(sub)
    db.session.commit()
    
    return jsonify({'success': True})
