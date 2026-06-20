"""
Rutas para el Módulo Teatral
"""

import json
import os
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, flash, current_app
from flask_login import login_required
from models import Proyecto, Publicacion
from extensions import db

teatral_bp = Blueprint('teatral', __name__, url_prefix='/teatral')


def check_teatral_access():
    proyecto_id = session.get('proyecto_activo_id')
    if not proyecto_id:
        return False
    proyecto = db.session.get(Proyecto, proyecto_id)
    if not proyecto:
        return False
    modulos = proyecto.modulos_activados or []
    # Permitir si está activado el módulo teatral
    if 'teatral' in modulos or 'dramatico' in modulos:
        return True
    return False

@teatral_bp.route('/exportar_dossier', methods=['POST'])
@login_required
def exportar_dossier():
    current_app.logger.info(f"[DOSSIER] Iniciando exportación. User: {session.get('_user_id')}")
    if not check_teatral_access():
        return jsonify({'error': 'Acceso no autorizado al Módulo Teatral.'}), 403
    
    data = request.json.get('chart_data')
    if not data:
        return jsonify({'error': 'No se proporcionaron datos para el análisis.'}), 400
    
    from pdf_generator import generar_dossier_teatral
    from flask import send_file
    
    proyecto_id = session.get('proyecto_activo_id')
    proyecto = db.session.get(Proyecto, proyecto_id)
    proyecto_nombre = proyecto.nombre if proyecto else "PROYECTO SIRIO"
    
    try:
        pdf_buffer = generar_dossier_teatral(data, proyecto_nombre)
        return send_file(
            pdf_buffer,
            as_attachment=True,
            download_name=f"Dossier_Teatral_{proyecto_id}.pdf",
            mimetype='application/pdf'
        )
    except Exception as e:
        import traceback
        err_msg = traceback.format_exc()
        current_app.logger.error(f"Error generando dossier teatral: {err_msg}")
        return jsonify({
            'error': 'Error interno al generar el PDF.',
            'debug': err_msg
        }), 500

@teatral_bp.route('/analisis')
@login_required
def analisis():
    if not check_teatral_access():
        flash('El Módulo Teatral no está activo en este proyecto.', 'warning')
        return redirect(url_for('proyectos.listar'))
        
    proyecto_id = session.get('proyecto_activo_id')
    # Obtener obras teatrales/publicaciones
    publicaciones = Publicacion.query.filter_by(proyecto_id=proyecto_id).all()
    proyecto = db.session.get(Proyecto, proyecto_id)
    
    return render_template('teatral/analisis.html', publicaciones=publicaciones, proyecto=proyecto)

@teatral_bp.route('/atribucion')
@login_required
def atribucion():
    if not check_teatral_access():
        flash('El Módulo Teatral no está activo en este proyecto.', 'warning')
        return redirect(url_for('proyectos.listar'))
        
    proyecto_id = session.get('proyecto_activo_id')
    # Obtener obras teatrales/publicaciones
    publicaciones = Publicacion.query.filter_by(proyecto_id=proyecto_id).all()
    proyecto = db.session.get(Proyecto, proyecto_id)
    
    return render_template('teatral/atribucion.html', publicaciones=publicaciones, proyecto=proyecto)
@teatral_bp.route('/interpretar_atribucion', methods=['POST'])
@login_required
def interpretar_atribucion():
    current_app.logger.info(f"[ATRIBUCION] Petición de interpretación recibida. User: {session.get('_user_id')}")
    from flask_login import current_user
    from advanced_analytics import AnalisisAvanzado
    
    data = request.json
    delta_results = data.get('delta_results')
    model = data.get('model', 'gemini:pro')
    
    if not delta_results:
        return jsonify({'exito': False, 'error': 'Faltan resultados Delta.'}), 400
        
    analisis = AnalisisAvanzado(db)
    resultado = analisis.interpretar_atribucion(delta_results, model_config=model, current_user=current_user)
    return jsonify(resultado)
