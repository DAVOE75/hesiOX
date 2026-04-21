"""
Rutas de gestión de proyectos
Incluye: listar, crear, editar, eliminar, activar proyectos
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import login_required, current_user
from sqlalchemy import or_

from extensions import db
from models import Proyecto, Prensa, Publicacion, Hemeroteca, ProyectoCompartido, Usuario
from schemas import ProyectoSchema
from marshmallow import ValidationError
from datetime import datetime

proyectos_bp = Blueprint('proyectos', __name__, url_prefix='/proyectos')


@proyectos_bp.route("/")
@login_required
def listar():
    """Listar proyectos del usuario (propios y compartidos)"""
    # Proyectos propios del usuario
    proyectos_propios = (
        Proyecto.query.filter_by(user_id=current_user.id)
        .order_by(Proyecto.creado_en.desc())
        .all()
    )
    
    # Proyectos compartidos con el usuario (excluyendo los propios)
    proyectos_compartidos_ids = db.session.query(ProyectoCompartido.proyecto_id).join(
        Proyecto, Proyecto.id == ProyectoCompartido.proyecto_id
    ).filter(
        ProyectoCompartido.usuario_id == current_user.id,
        Proyecto.user_id != current_user.id  # Excluir proyectos donde el usuario es el dueño
    ).all()
    proyectos_compartidos_ids = [pc[0] for pc in proyectos_compartidos_ids]
    
    proyectos_compartidos = (
        Proyecto.query.filter(Proyecto.id.in_(proyectos_compartidos_ids))
        .order_by(Proyecto.creado_en.desc())
        .all()
    ) if proyectos_compartidos_ids else []
    
    proyecto_activo_id = session.get("proyecto_activo_id")
    
    proyectos_con_stats = []
    
    # Procesar proyectos propios
    for p in proyectos_propios:
        # Obtener usuarios con los que está compartido (EXCLUYENDO al propietario)
        compartidos_con = db.session.query(
            Usuario.id, Usuario.nombre, ProyectoCompartido.activo_desde
        ).join(
            ProyectoCompartido, ProyectoCompartido.usuario_id == Usuario.id
        ).filter(
            ProyectoCompartido.proyecto_id == p.id,
            ProyectoCompartido.usuario_id != p.user_id  # Excluir al propietario
        ).all()
        
        # Calcular estadísticas de embeddings
        total_docs = Prensa.query.filter_by(proyecto_id=p.id, incluido=True).count()
        docs_con_embeddings = Prensa.query.filter(
            Prensa.proyecto_id == p.id,
            Prensa.incluido == True,
            Prensa.embedding_vector.isnot(None)
        ).count()
        docs_sin_embeddings = total_docs - docs_con_embeddings
        
        proyectos_con_stats.append({
            "id": p.id,
            "nombre": p.nombre,
            "descripcion": p.descripcion,
            "tipo": p.tipo,
            "activo": p.activo,
            "creado_en": p.creado_en,
            "num_articulos": Prensa.query.filter_by(proyecto_id=p.id).count(),
            "num_publicaciones": Publicacion.query.filter_by(proyecto_id=p.id).count(),
            "num_hemerotecas": Hemeroteca.query.filter_by(proyecto_id=p.id).count(),
            "total_docs": total_docs,
            "docs_con_embeddings": docs_con_embeddings,
            "docs_sin_embeddings": docs_sin_embeddings,
            "embeddings_completo": docs_sin_embeddings == 0 and total_docs > 0,
            "es_activo": (p.id == proyecto_activo_id),
            "es_propio": True,
            "compartido_con": [{"id": u[0], "nombre": u[1], "activo": u[2] is not None} for u in compartidos_con],
            "compartido_por": None
        })
    
    # Procesar proyectos compartidos
    for p in proyectos_compartidos:
        # Obtener info del usuario que lo compartió
        compartido_info = db.session.query(
            Usuario.id, Usuario.nombre, ProyectoCompartido.compartido_en, ProyectoCompartido.activo_desde
        ).join(
            ProyectoCompartido, ProyectoCompartido.compartido_por == Usuario.id
        ).filter(
            ProyectoCompartido.proyecto_id == p.id,
            ProyectoCompartido.usuario_id == current_user.id
        ).first()
        
        # Obtener el creador del proyecto
        creador = Usuario.query.get(p.user_id)
        
        # Verificar si el creador lo tiene activo
        creador_activo = db.session.query(ProyectoCompartido.activo_desde).filter_by(
            proyecto_id=p.id, usuario_id=p.user_id
        ).first()
        
        # Calcular estadísticas de embeddings
        total_docs = Prensa.query.filter_by(proyecto_id=p.id, incluido=True).count()
        docs_con_embeddings = Prensa.query.filter(
            Prensa.proyecto_id == p.id,
            Prensa.incluido == True,
            Prensa.embedding_vector.isnot(None)
        ).count()
        docs_sin_embeddings = total_docs - docs_con_embeddings
        
        proyectos_con_stats.append({
            "id": p.id,
            "nombre": p.nombre,
            "descripcion": p.descripcion,
            "tipo": p.tipo,
            "activo": p.activo,
            "creado_en": p.creado_en,
            "num_articulos": Prensa.query.filter_by(proyecto_id=p.id).count(),
            "num_publicaciones": Publicacion.query.filter_by(proyecto_id=p.id).count(),
            "num_hemerotecas": Hemeroteca.query.filter_by(proyecto_id=p.id).count(),
            "total_docs": total_docs,
            "docs_con_embeddings": docs_con_embeddings,
            "docs_sin_embeddings": docs_sin_embeddings,
            "embeddings_completo": docs_sin_embeddings == 0 and total_docs > 0,
            "es_activo": (p.id == proyecto_activo_id),
            "es_propio": False,
            "compartido_por": {
                "id": creador.id if creador else None,
                "nombre": creador.nombre if creador else "Usuario desconocido",
                "activo": False  # Se puede agregar lógica para detectar si el creador lo tiene activo
            },
            "compartido_con": []
        })
    
    return render_template("proyectos.html", proyectos=proyectos_con_stats)


@proyectos_bp.route("/nuevo", methods=["GET", "POST"])
@login_required
def crear():
    """Crear nuevo proyecto con validación"""
    if request.method == "POST":
        schema = ProyectoSchema()
        try:
            data = schema.load(request.form)
        except ValidationError as err:
            for field, messages in err.messages.items():
                for message in messages:
                    flash(message, "danger")
            return redirect(url_for("proyectos.crear"))

        nombre = data['nombre']
        descripcion = data.get('descripcion', '')
        tipo = data.get('tipo', 'hemerografia')

        # Verificar si ya existe un proyecto con ese nombre para este usuario
        if Proyecto.query.filter_by(user_id=current_user.id, nombre=nombre).first():
            flash("Ya tienes un proyecto con ese nombre.", "warning")
            return redirect(url_for("proyectos.crear"))

        proyecto = Proyecto(
            nombre=nombre,
            descripcion=descripcion,
            tipo=tipo,
            user_id=current_user.id,
            activo=True
        )
        db.session.add(proyecto)
        db.session.commit()

        # Activar automáticamente el proyecto recién creado
        session["proyecto_activo_id"] = proyecto.id

        flash(f"Proyecto '{nombre}' creado correctamente.", "success")
        return redirect(url_for("proyectos.listar"))

    return render_template("nuevo_proyecto.html")


@proyectos_bp.route("/<int:proyecto_id>/activar", methods=["GET", "POST"])
@login_required
def activar(proyecto_id):
    """Activar un proyecto como el proyecto activo y registrar timestamp de uso"""
    proyecto = Proyecto.query.get_or_404(proyecto_id)
    
    # Verificar que el usuario tenga acceso (es propietario O está compartido con él)
    es_propietario = (proyecto.user_id == current_user.id)
    es_compartido = ProyectoCompartido.query.filter_by(
        proyecto_id=proyecto_id,
        usuario_id=current_user.id
    ).first() is not None
    
    if not es_propietario and not es_compartido:
        flash("No tienes permiso para activar este proyecto.", "danger")
        return redirect(url_for("proyectos.listar"))
    
    # Activar proyecto en sesión
    session["proyecto_activo_id"] = proyecto.id
    
    # Actualizar timestamp de uso activo (crear o actualizar)
    compartido = ProyectoCompartido.query.filter_by(
        proyecto_id=proyecto_id,
        usuario_id=current_user.id
    ).first()
    
    if compartido:
        # Si existe el registro compartido, actualizar timestamp
        compartido.activo_desde = datetime.utcnow()
    else:
        # Si es el propietario, crear/actualizar registro de uso
        # (para que otros usuarios vean que está activo)
        registro_propio = ProyectoCompartido.query.filter_by(
            proyecto_id=proyecto_id,
            usuario_id=current_user.id
        ).first()
        
        if not registro_propio and es_propietario:
            # Crear registro especial para el propietario
            registro_propio = ProyectoCompartido(
                proyecto_id=proyecto_id,
                usuario_id=current_user.id,
                compartido_por=current_user.id,  # Se marca a sí mismo como compartido_por
                activo_desde=datetime.utcnow()
            )
            db.session.add(registro_propio)
        elif registro_propio:
            registro_propio.activo_desde = datetime.utcnow()
    
    db.session.commit()
    
    flash(f"Proyecto '{proyecto.nombre}' activado.", "success")
    return redirect(url_for("proyectos.listar"))


@proyectos_bp.route("/<int:proyecto_id>/eliminar", methods=["POST"])
@login_required
def eliminar(proyecto_id):
    """Eliminar un proyecto y todos sus datos asociados"""
    proyecto = Proyecto.query.get_or_404(proyecto_id)
    
    # Verificar permisos
    if proyecto.user_id != current_user.id:
        flash("No tienes permiso para eliminar este proyecto.", "danger")
        return redirect(url_for("proyectos.listar"))
    
    # Si es el proyecto activo, limpiarlo de la sesión
    if session.get("proyecto_activo_id") == proyecto_id:
        session.pop("proyecto_activo_id", None)
    
    nombre_proyecto = proyecto.nombre
    
    # Eliminar todos los artículos del proyecto
    Prensa.query.filter_by(proyecto_id=proyecto_id).delete()
    
    # Eliminar todas las publicaciones del proyecto
    Publicacion.query.filter_by(proyecto_id=proyecto_id).delete()
    
    # Eliminar todas las hemerotecas del proyecto
    Hemeroteca.query.filter_by(proyecto_id=proyecto_id).delete()
    
    # Eliminar el proyecto
    db.session.delete(proyecto)
    db.session.commit()
    
    flash(f"Proyecto '{nombre_proyecto}' eliminado correctamente.", "success")
    return redirect(url_for("proyectos.listar"))


@proyectos_bp.route("/<int:proyecto_id>/editar", methods=["POST"])
@login_required
def editar(proyecto_id):
    """Editar un proyecto existente"""
    proyecto = Proyecto.query.get_or_404(proyecto_id)
    
    # Verificar permisos
    if proyecto.user_id != current_user.id:
        flash("No tienes permiso para editar este proyecto.", "danger")
        return redirect(url_for("proyectos.listar"))
    
    nombre = request.form.get("nombre", "").strip()
    descripcion = request.form.get("descripcion", "").strip()
    tipo = request.form.get("tipo", "hemerografia")
    
    if not nombre:
        flash("El nombre del proyecto es obligatorio.", "warning")
        return redirect(url_for("proyectos.listar"))
    
    # Verificar si ya existe otro proyecto con ese nombre para este usuario
    existing = Proyecto.query.filter_by(user_id=current_user.id, nombre=nombre).first()
    if existing and existing.id != proyecto_id:
        flash("Ya tienes un proyecto con ese nombre.", "warning")
        return redirect(url_for("proyectos.listar"))
    
    proyecto.nombre = nombre
    proyecto.descripcion = descripcion
    proyecto.tipo = tipo
    
    db.session.commit()
    flash(f"Proyecto '{nombre}' actualizado correctamente.", "success")
    return redirect(url_for("proyectos.listar"))


@proyectos_bp.route("/<int:proyecto_id>/desactivar", methods=["GET"])
@login_required
def desactivar(proyecto_id):
    """Desactivar el proyecto activo y limpiar timestamp de uso"""
    proyecto = Proyecto.query.get_or_404(proyecto_id)
    
    # Verificar que el usuario tenga acceso
    es_propietario = (proyecto.user_id == current_user.id)
    es_compartido = ProyectoCompartido.query.filter_by(
        proyecto_id=proyecto_id,
        usuario_id=current_user.id
    ).first() is not None
    
    if not es_propietario and not es_compartido:
        flash("No tienes permiso para desactivar este proyecto.", "danger")
        return redirect(url_for("proyectos.listar"))
    
    # Limpiar el proyecto activo de la sesión
    if session.get("proyecto_activo_id") == proyecto_id:
        session.pop("proyecto_activo_id", None)
        
        # Limpiar timestamp de uso activo
        compartido = ProyectoCompartido.query.filter_by(
            proyecto_id=proyecto_id,
            usuario_id=current_user.id
        ).first()
        
        if compartido:
            compartido.activo_desde = None
            db.session.commit()
        
        flash(f"Proyecto '{proyecto.nombre}' desactivado.", "info")
    
    return redirect(url_for("proyectos.listar"))


def get_proyecto_activo():
    """
    Función auxiliar para obtener el proyecto activo de la sesión
    Usada por otras rutas y context processors
    """
    proyecto_id = session.get("proyecto_activo_id")
    if proyecto_id:
        proyecto = Proyecto.query.get(proyecto_id)
        # Verificar que el proyecto existe y el usuario tiene acceso
        if proyecto and current_user.is_authenticated:
            es_propietario = (proyecto.user_id == current_user.id)
            es_compartido = ProyectoCompartido.query.filter_by(
                proyecto_id=proyecto_id,
                usuario_id=current_user.id
            ).first() is not None
            
            if es_propietario or es_compartido:
                return proyecto
    return None


# ============================================================================
# API ENDPOINTS PARA COMPARTIR PROYECTOS
# ============================================================================

@proyectos_bp.route("/api/usuarios", methods=["GET"])
@login_required
def api_listar_usuarios():
    """Obtener lista de usuarios para compartir proyectos (excluyendo al actual)"""
    usuarios = Usuario.query.filter(Usuario.id != current_user.id).all()
    
    return jsonify({
        "usuarios": [
            {
                "id": u.id,
                "nombre": u.nombre,
                "email": u.email,
                "institucion": u.institucion
            }
            for u in usuarios
        ]
    })


@proyectos_bp.route("/<int:proyecto_id>/compartir", methods=["POST"])
@login_required
def api_compartir_proyecto(proyecto_id):
    """Compartir proyecto con usuarios seleccionados"""
    proyecto = Proyecto.query.get_or_404(proyecto_id)
    
    # Solo el propietario puede compartir
    if proyecto.user_id != current_user.id:
        return jsonify({"error": "No tienes permiso para compartir este proyecto"}), 403
    
    data = request.get_json()
    usuarios_ids = data.get("usuarios_ids", [])
    
    if not usuarios_ids:
        return jsonify({"error": "Debes seleccionar al menos un usuario"}), 400
    
    # Compartir con cada usuario seleccionado
    compartidos = []
    for usuario_id in usuarios_ids:
        # Verificar que el usuario existe
        usuario = Usuario.query.get(usuario_id)
        if not usuario:
            continue
        
        # Verificar si ya está compartido
        ya_compartido = ProyectoCompartido.query.filter_by(
            proyecto_id=proyecto_id,
            usuario_id=usuario_id
        ).first()
        
        if not ya_compartido:
            nuevo_compartido = ProyectoCompartido(
                proyecto_id=proyecto_id,
                usuario_id=usuario_id,
                compartido_por=current_user.id,
                compartido_en=datetime.utcnow()
            )
            db.session.add(nuevo_compartido)
            compartidos.append(usuario.nombre)
    
    db.session.commit()
    
    if compartidos:
        return jsonify({
            "success": True,
            "mensaje": f"Proyecto compartido con: {', '.join(compartidos)}",
            "compartidos": compartidos
        })
    else:
        return jsonify({
            "success": False,
            "mensaje": "El proyecto ya estaba compartido con los usuarios seleccionados"
        })


@proyectos_bp.route("/<int:proyecto_id>/dejar-de-compartir", methods=["POST"])
@login_required
def api_dejar_compartir_proyecto(proyecto_id):
    """Dejar de compartir proyecto con un usuario específico"""
    proyecto = Proyecto.query.get_or_404(proyecto_id)
    
    # Solo el propietario puede dejar de compartir
    if proyecto.user_id != current_user.id:
        return jsonify({"error": "No tienes permiso"}), 403
    
    data = request.get_json()
    usuario_id = data.get("usuario_id")
    
    if not usuario_id:
        return jsonify({"error": "ID de usuario requerido"}), 400
    
    compartido = ProyectoCompartido.query.filter_by(
        proyecto_id=proyecto_id,
        usuario_id=usuario_id
    ).first()
    
    if compartido:
        db.session.delete(compartido)
        db.session.commit()
        return jsonify({"success": True, "mensaje": "Acceso revocado"})
    else:
        return jsonify({"success": False, "mensaje": "No se encontró el registro"}), 404


@proyectos_bp.route("/<int:proyecto_id>/dejar-de-compartir-todos", methods=["POST"])
@login_required
def api_dejar_compartir_proyecto_todos(proyecto_id):
    """Dejar de compartir proyecto con TODOS los usuarios"""
    proyecto = Proyecto.query.get_or_404(proyecto_id)
    
    # Solo el propietario puede dejar de compartir
    if proyecto.user_id != current_user.id:
        return jsonify({"error": "No tienes permiso"}), 403
    
    # Eliminar todos los registros de compartición de este proyecto
    compartidos = ProyectoCompartido.query.filter_by(proyecto_id=proyecto_id).all()
    
    if not compartidos:
        return jsonify({"success": False, "mensaje": "El proyecto no está compartido con ningún usuario"}), 404
    
    count = len(compartidos)
    for compartido in compartidos:
        db.session.delete(compartido)
    
    db.session.commit()
    
    return jsonify({
        "success": True, 
        "mensaje": f"Se revocó el acceso de {count} usuario{'s' if count > 1 else ''}"
    })


@proyectos_bp.route("/<int:proyecto_id>/compartidos", methods=["GET"])
@login_required
def api_obtener_compartidos(proyecto_id):
    """Obtener lista de usuarios con los que está compartido un proyecto"""
    proyecto = Proyecto.query.get_or_404(proyecto_id)
    
    # Solo el propietario puede ver con quién está compartido
    if proyecto.user_id != current_user.id:
        return jsonify({"error": "No tienes permiso"}), 403
    
    # Obtener usuarios compartidos (EXCLUYENDO al propietario)
    compartidos = db.session.query(
        Usuario.id, Usuario.nombre, Usuario.email, ProyectoCompartido.compartido_en, ProyectoCompartido.activo_desde
    ).join(
        ProyectoCompartido, ProyectoCompartido.usuario_id == Usuario.id
    ).filter(
        ProyectoCompartido.proyecto_id == proyecto_id,
        ProyectoCompartido.usuario_id != proyecto.user_id  # Excluir al propietario
    ).all()
    
    return jsonify({
        "compartidos": [
            {
                "id": c.id,
                "nombre": c.nombre,
                "email": c.email,
                "compartido_en": c.compartido_en.isoformat() if c.compartido_en else None,
                "activo": c.activo_desde is not None and (datetime.utcnow() - c.activo_desde).total_seconds() < 300
            }
            for c in compartidos
        ]
    })
