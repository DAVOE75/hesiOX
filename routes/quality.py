"""
Rutas de control de calidad y consistencia de datos
"""
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from extensions import db
from models import ValidacionDuplicados
from utils import get_proyecto_activo

quality_bp = Blueprint('quality', __name__, url_prefix='/api/quality')

@quality_bp.route('/validar', methods=['POST'])
@login_required
def validar_duplicados():
    """
    Marca un par o grupo de registros como "validados" (no son duplicados).
    Recibe JSON: { "ids": [id1, id2, id3...] }
    """
    proyecto = get_proyecto_activo()
    if not proyecto:
        return jsonify({'success': False, 'message': 'Proyecto no activo'}), 400

    data = request.get_json(silent=True) or {}
    ids = sorted(list(set(data.get('ids', [])))) # Eliminar duplicados y ordenar

    if len(ids) < 2:
        return jsonify({'success': False, 'message': 'Se requieren al menos 2 IDs para validar'}), 400

    # Crear pares únicos de validación para todos los elementos del grupo
    # Ejemplo: si el usuario valida un grupo de 3 (A, B, C), validamos A-B, A-C, B-C
    import itertools
    count = 0
    try:
        for id1, id2 in itertools.combinations(ids, 2):
            # Verificar si ya existe
            existe = ValidacionDuplicados.query.filter_by(
                proyecto_id=proyecto.id,
                prensa_id_1=id1,
                prensa_id_2=id2
            ).first()

            if not existe:
                nueva_validacion = ValidacionDuplicados(
                    proyecto_id=proyecto.id,
                    prensa_id_1=id1,
                    prensa_id_2=id2
                )
                db.session.add(nueva_validacion)
                count += 1
        
        db.session.commit()
        return jsonify({
            'success': True, 
            'message': f'Grupo validado correctamente. {count} pares registrados.'
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@quality_bp.route('/validado', methods=['GET'])
@login_required
def obtener_validaciones():
    """Retorna lista de pares validados para el proyecto activo"""
    proyecto = get_proyecto_activo()
    if not proyecto:
        return jsonify([])
    
    validaciones = ValidacionDuplicados.query.filter_by(proyecto_id=proyecto.id).all()
    
    # Retornamos una lista de pares [min, max] para facilitar chequeo en JS
    pairs = []
    for v in validaciones:
        pairs.append([v.prensa_id_1, v.prensa_id_2])
        
    return jsonify(pairs)
