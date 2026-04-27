from flask import Blueprint, jsonify, request
from extensions import db
from models import MetadataOption
from flask_login import login_required

metadata_api = Blueprint('metadata_api', __name__)

@metadata_api.route('/api/metadata/<categoria>', methods=['GET'])
@login_required
def get_metadata_options(categoria):
    """Obtiene todas las opciones de una categoría específica."""
    options = MetadataOption.query.filter_by(categoria=categoria).order_by(MetadataOption.orden, MetadataOption.etiqueta).all()
    return jsonify([opt.to_dict() for opt in options])

@metadata_api.route('/api/metadata/grouped/<categoria>/<grupo>', methods=['GET'])
@login_required
def get_metadata_grouped(categoria, grupo):
    """Obtiene opciones filtradas por categoría y grupo (ej: subgéneros de un género)."""
    options = MetadataOption.query.filter_by(categoria=categoria, grupo=grupo).order_by(MetadataOption.orden, MetadataOption.etiqueta).all()
    # Si no hay resultados para el grupo, intentar buscar sin grupo o devolver vacío según convenga
    return jsonify([opt.to_dict() for opt in options])

@metadata_api.route('/api/metadata/<categoria>', methods=['POST'])
@login_required
def create_metadata_option(categoria):
    """Crea una nueva opción de metadato."""
    data = request.get_json()
    
    if not data or not data.get('etiqueta'):
        return jsonify({'error': 'La etiqueta es obligatoria'}), 400
    
    # Generar valor automático si no se proporciona (slugify simple)
    valor = data.get('valor') or data.get('etiqueta').lower().replace(' ', '_')
    
    new_option = MetadataOption(
        categoria=categoria,
        valor=valor,
        etiqueta=data.get('etiqueta'),
        grupo=data.get('grupo'),
        orden=data.get('orden', 0)
    )
    
    db.session.add(new_option)
    db.session.commit()
    
    return jsonify(new_option.to_dict()), 201

@metadata_api.route('/api/metadata/option/<int:id>', methods=['PUT'])
@login_required
def update_metadata_option(id):
    """Actualiza una opción existente."""
    option = MetadataOption.query.get_or_404(id)
    data = request.get_json()
    
    if 'etiqueta' in data:
        option.etiqueta = data['etiqueta']
    if 'valor' in data:
        option.valor = data['valor']
    if 'grupo' in data:
        option.grupo = data['grupo']
    if 'orden' in data:
        option.orden = data['orden']
        
    db.session.commit()
    return jsonify(option.to_dict())

@metadata_api.route('/api/metadata/option/<int:id>', methods=['DELETE'])
@login_required
def delete_metadata_option(id):
    """Elimina una opción."""
    option = MetadataOption.query.get_or_404(id)
    db.session.delete(option)
    db.session.commit()
    return jsonify({'message': 'Opción eliminada correctamente'})
