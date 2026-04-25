"""
Rutas de gestión de artículos de prensa
Incluye: listar, crear, editar, eliminar, operaciones en lote
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session, current_app
from flask_login import login_required, current_user
from extensions import csrf, db
from datetime import datetime
from models import Prensa, Publicacion, Proyecto, GeoPlace, Hemeroteca, ImagenPrensa
from utils import (
    validar_fecha_ddmmyyyy,
    normalizar_next,
    geocode_city,
    QueryCache,
    cache,
    separar_autor
)
from sqlalchemy import String, cast, or_, func

articulos_bp = Blueprint('articulos', __name__)

# Endpoint API RESTful para eliminar artículo vía DELETE
@articulos_bp.route('/api/articulos/<int:id>/eliminar', methods=['POST'])
@login_required
@csrf.exempt
def api_eliminar_articulo(id):
    articulo = db.session.get(Prensa, id)
    if not articulo:
        return jsonify({'success': False, 'error': 'Artículo no encontrado'}), 404
    try:
        db.session.delete(articulo)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Artículo eliminado correctamente'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

def get_proyecto_activo():
    """
    Función auxiliar para obtener el proyecto activo de la sesión
    """
    from routes.proyectos import get_proyecto_activo as get_proyecto
    return get_proyecto()


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
    """Ordenar query por fecha con protección contra fechas inválidas"""
    from sqlalchemy import text
    
    orden_sql = text(f"""
        CASE
            WHEN fecha_original ~ '^[0-3]?[0-9]/[0-1]?[0-9]/[0-9]{2,4}$' THEN to_date(fecha_original, 'DD/MM/YYYY')
            WHEN fecha_original ~ '^[0-9]{4}-[0-1]?[0-9]-[0-3]?[0-9]$' THEN to_date(fecha_original, 'YYYY-MM-DD')
            ELSE NULL
        END {"DESC" if descendente else "ASC"} NULLS LAST,
        publicacion ASC
    """)
    return query.order_by(orden_sql)
