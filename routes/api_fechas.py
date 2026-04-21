from flask import Blueprint, jsonify
from extensions import db
from models import Prensa

api_fechas_bp = Blueprint('api_fechas', __name__, url_prefix='/api/analisis')

@api_fechas_bp.route('/rango_fechas', methods=['GET'])
def rango_fechas():
    proyecto_id = None
    try:
        from app import get_proyecto_activo
        proyecto = get_proyecto_activo()
        if proyecto:
            proyecto_id = proyecto.id
    except Exception:
        pass
    
    query = db.session.query(Prensa)
    if proyecto_id:
        query = query.filter(Prensa.proyecto_id == proyecto_id)
    fecha_min = db.session.query(db.func.min(Prensa.fecha_original)).scalar()
    fecha_max = db.session.query(db.func.max(Prensa.fecha_original)).scalar()
    return jsonify({
        'fecha_min': fecha_min,
        'fecha_max': fecha_max
    })
