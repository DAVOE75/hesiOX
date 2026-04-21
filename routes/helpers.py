"""
Helpers reutilizables para rutas de hesiOX
Funciones comunes para validación, obtención de proyectos, etc.
"""
from flask import session, flash, abort, request
from flask_login import current_user
from marshmallow import ValidationError

from extensions import db
from models import Proyecto


def get_proyecto_activo_or_404():
    """
    Obtiene el proyecto activo de la sesión o aborta con 404
    
    Returns:
        Proyecto: Proyecto activo del usuario
    
    Raises:
        404: Si no hay proyecto activo o no existe
        403: Si el proyecto no pertenece al usuario actual
    """
    proyecto_id = session.get('proyecto_activo_id')
    
    if not proyecto_id:
        flash("⚠️ Debes activar un proyecto primero", "warning")
        abort(404)
    
    proyecto = Proyecto.query.get_or_404(proyecto_id)
    
    # Verificar que el proyecto pertenece al usuario actual
    if proyecto.user_id != current_user.id:
        flash("❌ No tienes acceso a este proyecto", "danger")
        abort(403)
    
    return proyecto


def validate_and_flash(schema, data, partial=False):
    """
    Valida datos con un schema Marshmallow y muestra errores como flash messages
    
    Args:
        schema: Instancia del schema Marshmallow
        data: Datos a validar (dict o FormData)
        partial: Si True, permite validación parcial (campos opcionales)
    
    Returns:
        dict | None: Datos validados si éxito, None si hay errores
    """
    try:
        return schema.load(data, partial=partial)
    except ValidationError as err:
        for field, messages in err.messages.items():
            for message in messages:
                flash(f"{field}: {message}", "danger")
        return None


def get_client_ip():
    """
    Obtiene la IP real del cliente considerando proxies
    
    Returns:
        str: Dirección IP del cliente
    """
    if request.headers.get('X-Forwarded-For'):
        # Si hay proxy, tomar la primera IP
        ip = request.headers.get('X-Forwarded-For').split(',')[0].strip()
    else:
        ip = request.remote_addr or '127.0.0.1'
    
    return ip


def paginate_query(query, page=1, per_page=25):
    """
    Pagina una query de SQLAlchemy
    
    Args:
        query: Query de SQLAlchemy
        page: Número de página (1-indexed)
        per_page: Resultados por página
    
    Returns:
        tuple: (items, total, total_pages, page)
    """
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    
    return (
        pagination.items,
        pagination.total,
        pagination.pages,
        page
    )


def safe_commit(flash_success=None, flash_error=None):
    """
    Intenta hacer commit a la base de datos con manejo de errores
    
    Args:
        flash_success: Mensaje flash de éxito (opcional)
        flash_error: Mensaje flash de error (opcional)
    
    Returns:
        bool: True si commit exitoso, False si hubo error
    """
    try:
        db.session.commit()
        if flash_success:
            flash(flash_success, "success")
        return True
    except Exception as e:
        db.session.rollback()
        if flash_error:
            flash(f"{flash_error}: {str(e)}", "danger")
        else:
            flash(f"Error al guardar cambios: {str(e)}", "danger")
        return False


def require_proyecto_activo(f):
    """
    Decorador que requiere un proyecto activo
    
    Uso:
        @app.route('/ruta')
        @login_required
        @require_proyecto_activo
        def mi_ruta():
            proyecto = get_proyecto_activo_or_404()
            ...
    """
    from functools import wraps
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        get_proyecto_activo_or_404()
        return f(*args, **kwargs)
    
    return decorated_function


def build_filter_query(model, filters, proyecto_id=None):
    """
    Construye una query con filtros dinámicos
    
    Args:
        model: Modelo de SQLAlchemy
        filters: Dict con filtros {campo: valor}
        proyecto_id: ID del proyecto para filtrar (opcional)
    
    Returns:
        Query: Query de SQLAlchemy con filtros aplicados
    """
    query = model.query
    
    # Filtrar por proyecto si se proporciona
    if proyecto_id and hasattr(model, 'proyecto_id'):
        query = query.filter_by(proyecto_id=proyecto_id)
    
    # Aplicar filtros dinámicos
    for field, value in filters.items():
        if value and hasattr(model, field):
            column = getattr(model, field)
            query = query.filter(column.ilike(f"%{value}%"))
    
    return query
