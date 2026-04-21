from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, current_app
from flask_login import login_required, current_user
from models import db, SirioFicha, SirioPuntoInteractivo, Proyecto, LloydsFicha, MotoresFicha
from extensions import csrf
from .utils_lloyds import LLOYDS_SECTIONS
from .utils_motores import MOTORES_SECTIONS
from services.ai_service import AIService
from functools import wraps
from datetime import datetime
import json

barco_bp = Blueprint('barco', __name__, url_prefix='/barco')

def check_sirio_access(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # El menu "El Barco" solo es para el Proyecto 1 (Sirio)
        try:
            proyecto_id_raw = request.args.get('proyecto_id')
            if proyecto_id_raw:
                proyecto_id = int(proyecto_id_raw)
            else:
                proyecto_id = 1
                
            if proyecto_id != 1:
                flash("Este módulo solo está disponible para el proyecto S.S. Sirio.", "warning")
                return redirect(url_for('index'))
        except (ValueError, TypeError):
            # Si el ID es inválido, asumimos Sirio (1) por defecto si estamos en estas rutas
            pass
            
        return f(*args, **kwargs)
    return decorated_function

@barco_bp.route('/ficha')
@login_required
@check_sirio_access
def ficha():
    ficha_data = SirioFicha.query.first()
    lloyds = LloydsFicha.query.first()
    lloyds_dict = {c.name: getattr(lloyds, c.name) for c in lloyds.__table__.columns} if lloyds else {}
    return render_template('barco/ficha.html', ficha=ficha_data, lloyds=lloyds_dict, lloyds_sections=LLOYDS_SECTIONS)

@barco_bp.route('/plano')
@login_required
@check_sirio_access
def plano():
    puntos_db = SirioPuntoInteractivo.query.all()
    puntos_dict = [{
        'id': p.id,
        'nombre': p.nombre,
        'categoria': p.categoria,
        'descripcion': p.descripcion,
        'x': p.x,
        'y': p.y,
        'coordenadas': p.coordenadas,
        'icono': p.icono
    } for p in puntos_db]
    return render_template('barco/plano.html', puntos=puntos_dict)

@barco_bp.route('/admin')
@login_required
@check_sirio_access
def admin():
    ficha_data = SirioFicha.query.first()
    lloyds = LloydsFicha.query.first()
    lloyds_dict = {c.name: getattr(lloyds, c.name) for c in lloyds.__table__.columns} if lloyds else {}
    
    motores = MotoresFicha.query.first()
    motores_dict = {c.name: getattr(motores, c.name) for c in motores.__table__.columns} if motores else {}
    
    puntos = SirioPuntoInteractivo.query.all()
    return render_template('barco/admin_barco.html', 
                          ficha=ficha_data, 
                          lloyds=lloyds_dict, 
                          lloyds_sections=LLOYDS_SECTIONS,
                          motores=motores_dict,
                          motores_sections=MOTORES_SECTIONS,
                          puntos=puntos)

@barco_bp.route('/api/puntos', methods=['GET', 'POST'])
@csrf.exempt
@login_required
def api_puntos():
    if request.method == 'GET':
        puntos = SirioPuntoInteractivo.query.order_by(SirioPuntoInteractivo.id.asc()).all()
        return jsonify([{
            'id': p.id,
            'nombre': p.nombre,
            'categoria': p.categoria,
            'descripcion': p.descripcion,
            'x': p.x,
            'y': p.y,
            'coordenadas': p.coordenadas,
            'icono': p.icono
        } for p in puntos])
    
    data = request.json
    nuevo_punto = SirioPuntoInteractivo(
        nombre=data.get('nombre'),
        categoria=data.get('categoria'),
        descripcion=data.get('descripcion'),
        x=data.get('x'),
        y=data.get('y'),
        coordenadas=data.get('coordenadas'),
        icono=data.get('icono', 'fa-circle-info')
    )
    db.session.add(nuevo_punto)
    db.session.commit()
    return jsonify({'id': nuevo_punto.id, 'status': 'success'})

@barco_bp.route('/api/puntos/<int:id>', methods=['PUT', 'DELETE'])
@csrf.exempt
@login_required
def api_punto_detail(id):
    punto = SirioPuntoInteractivo.query.get_or_404(id)
    if request.method == 'DELETE':
        print(f"DEBUG: Deleting point {id}")
        db.session.delete(punto)
        db.session.commit()
        return jsonify({'status': 'deleted'})
    
    data = request.json
    punto.nombre = data.get('nombre', punto.nombre)
    punto.categoria = data.get('categoria', punto.categoria)
    punto.descripcion = data.get('descripcion', punto.descripcion)
    punto.x = data.get('x', punto.x)
    punto.y = data.get('y', punto.y)
    punto.coordenadas = data.get('coordenadas', punto.coordenadas)
    punto.icono = data.get('icono', punto.icono)
    db.session.commit()
    return jsonify({'status': 'updated'})

@barco_bp.route('/api/ficha', methods=['POST'])
@csrf.exempt
@login_required
def api_update_ficha():
    ficha_data = SirioFicha.query.first()
    if not ficha_data:
        ficha_data = SirioFicha()
        db.session.add(ficha_data)
    
    data = request.json
    # Actualizar los grupos JSON según lo que venga del frontend
    if 'datos_generales' in data: ficha_data.datos_generales = data['datos_generales']
    if 'datos_estructura' in data: ficha_data.datos_estructura = data['datos_estructura']
    if 'datos_planchaje' in data: ficha_data.datos_planchaje = data['datos_planchaje']
    if 'datos_fijaciones' in data: ficha_data.datos_fijaciones = data['datos_fijaciones']
    if 'datos_equipamiento' in data: ficha_data.datos_equipamiento = data['datos_equipamiento']
    if 'datos_inspecciones' in data: ficha_data.datos_inspecciones = data['datos_inspecciones']
    
    db.session.commit()
    return jsonify({'status': 'success'})

@barco_bp.route('/api/ficha_lloyds', methods=['POST'])
@csrf.exempt
@login_required
def api_update_lloyds():
    lloyds_data = LloydsFicha.query.first()
    if not lloyds_data:
        lloyds_data = LloydsFicha()
        db.session.add(lloyds_data)
    
    data = request.json
    # Solo procesamos los campos que existen en el modelo
    for field, value in data.items():
        if hasattr(lloyds_data, field) and field != 'id':
            setattr(lloyds_data, field, value)
    
    db.session.commit()
    return jsonify({'status': 'success'})

@barco_bp.route('/api/analizar_seccion', methods=['POST'])
@login_required
def api_analizar_seccion():
    """
    Analiza una sección técnica de la ficha Lloyd's usando IA.
    """
    try:
        data = request.json
        section_id = data.get('section_id')
        model_type = data.get('model', 'flash') 
        context_base = data.get('context', '') # El texto histórico manual como referencia
        
        section_def = None
        if section_id == 'all':
            section_def = {
                'title': 'S.S. SIRIO - INFORME GLOBAL',
                'fields': []
            }
            # Agregamos todos los campos de todas las secciones
            for s in LLOYDS_SECTIONS:
                if 'fields' in s:
                    section_def['fields'].extend(s['fields'])
        else:
            for idx, s in enumerate(LLOYDS_SECTIONS):
                # Los IDs son 1-indexed (loop.index en Jinja)
                if str(idx + 1) == str(section_id):
                    section_def = s
                    break
        
        if not section_def:
            return jsonify({'error': 'Sección no encontrada'}), 404
            
        # Obtener los datos reales de la ficha para esta sección
        lloyds = LloydsFicha.query.first()
        if not lloyds:
            return jsonify({'error': 'No hay datos de ficha disponibles'}), 404
            
        # Construir un string con los datos reales de los campos de esta sección
        section_data_str = ""
        for field_name, label in section_def['fields']:
            val = getattr(lloyds, field_name, "N/A")
            section_data_str += f"- {label}: {val}\n"

        # Configurar AIService
        provider = 'gemini'
        model_name = 'gemini-2.0-flash'
        if model_type == 'pro': model_name = 'gemini-2.0-flash'
        elif model_type == 'gemini-3-flash': model_name = 'gemini-3-flash'
        elif model_type == 'gemini-3-pro': model_name = 'gemini-3-pro'
        elif model_type == 'openai': provider = 'openai'; model_name = 'gpt-4o'
        elif model_type == 'anthropic': provider = 'anthropic'; model_name = 'claude-3-5-sonnet-20240620'
        elif model_type == 'llama': provider = 'llama'; model_name = 'llama3'

        ai = AIService(provider=provider, model=model_name, user=current_user)
        
        if section_id == 'all':
            prompt = f"""
            Como Inspector Jefe de Lloyd's Register y experto en arqueología naval, proporciona un INFORME TÉCNICO GLOBAL y EXHAUSTIVO sobre el buque S.S. Sirio basado en su inspección de 1883.

            DATOS TÉCNICOS COMPLETOS:
            {section_data_str}

            REGLAS CRÍTICAS:
            1. Resume las características principales que hacían de este buque una pieza relevante de la ingeniería de la época.
            2. Analiza su estructura, potencia y equipamiento de forma integrada.
            3. Ve DIRECTO al análisis. Sin introducciones ceremoniosas.
            4. USA HTML limpio (p, strong, ul, li). NO uses bloques de código con triple comilla (```).
            5. Idioma: ESPAÑOL. Tono: Académico, sobrio y técnico.
            """
        else:
            prompt = f"""
            Como experto analista de Lloyd's Register, proporciona un informe técnico e histórico SOBRE la sección "{section_def['title']}" del buque S.S. Sirio.

            DATOS TÉCNICOS DE LA SECCIÓN:
            {section_data_str}

            CONTEXTO ORIGINAL:
            {context_base}

            REGLAS CRÍTICAS:
            1. NO asumas roles explícitamente ni uses frases como "Como historiador..." o "Desde mi posición...".
            2. Ve DIRECTO al análisis de los datos. Sin introducciones.
            3. Explica el significado técnico y comercial de estos números para la navegación de 1883 de forma profesional y sobria.
            4. ILUSTRACIONES TÉCNICAS: Tienes permitido (y se recomienda) incluir imágenes de las piezas técnicas si las mencionas.
               USA ESTA SINTAXIS EXACTA: <img src="/static/img/tech/ARCHIVO.png" class="tech-img"> <span class="tech-caption">Título de la Imagen</span>
               ARCHIVOS DISPONIBLES: quilla.png, roda.png, codaste.png, cuadernas.png, varengas.png, planchaje.png.
            5. USA HTML limpio (p, strong, ul, li). NO uses bloques de código con triple comilla (```).
            6. Idioma: ESPAÑOL. Tono: Académico y ejecutivo.
            """
        
        analisis = ai.generate_content(prompt, temperature=0.7)
        
        if not analisis:
            return jsonify({'error': 'La IA no pudo generar el análisis. Verifique la configuración del modelo.'}), 500
            
        return jsonify({
            'analisis': analisis,
            'modelo_usado': model_name
        })

    except Exception as e:
        current_app.logger.error(f"Error en api_analizar_seccion: {str(e)}")
        return jsonify({'error': str(e)}), 500


# =============================================================================
# RUTAS DE MOTORES (Report on Machinery 1883)
# =============================================================================

@barco_bp.route('/motores')
@login_required
@check_sirio_access
def ficha_motores():
    """Ficha técnica de los motores del S.S. Sirio."""
    motores = MotoresFicha.query.first()
    motores_dict = {c.name: getattr(motores, c.name) for c in motores.__table__.columns} if motores else {}
    return render_template('barco/ficha_motores.html', motores=motores_dict, motores_sections=MOTORES_SECTIONS)


@barco_bp.route('/admin/motores')
@login_required
@check_sirio_access
def admin_motores():
    """Redirige al nuevo panel consolidado con el tab de motores activo."""
    return redirect(url_for('barco.admin', _anchor='motores-tab'))


@barco_bp.route('/api/motores', methods=['POST'])
@csrf.exempt
@login_required
def api_update_motores():
    """Actualiza la ficha técnica de motores."""
    motores_data = MotoresFicha.query.first()
    if not motores_data:
        motores_data = MotoresFicha()
        db.session.add(motores_data)

    data = request.json
    for field, value in data.items():
        if hasattr(motores_data, field) and field not in ('id', 'ultima_actualizacion'):
            setattr(motores_data, field, value)

    db.session.commit()
    return jsonify({'status': 'success'})


@barco_bp.route('/api/analizar_motores', methods=['POST'])
@login_required
def api_analizar_motores():
    """
    Analiza una sección de la ficha de motores usando IA.
    """
    try:
        data = request.json
        section_id = data.get('section_id')
        model_type = data.get('model', 'flash')
        context_base = data.get('context', '')

        section_def = None
        if section_id == 'all':
            section_def = {'title': 'S.S. SIRIO - INFORME GLOBAL DE MAQUINARIA', 'fields': []}
            for s in MOTORES_SECTIONS:
                if 'fields' in s:
                    section_def['fields'].extend(s['fields'])
        else:
            for idx, s in enumerate(MOTORES_SECTIONS):
                if str(idx + 1) == str(section_id):
                    section_def = s
                    break

        if not section_def:
            return jsonify({'error': 'Sección no encontrada'}), 404

        motores = MotoresFicha.query.first()
        if not motores:
            return jsonify({'error': 'No hay datos de motores disponibles'}), 404

        section_data_str = ""
        for field_name, label in section_def['fields']:
            val = getattr(motores, field_name, 'N/A')
            section_data_str += f"- {label}: {val}\n"

        provider = 'gemini'
        model_name = 'gemini-2.0-flash'
        if model_type == 'pro': model_name = 'gemini-2.0-flash'
        elif model_type == 'openai': provider = 'openai'; model_name = 'gpt-4o'
        elif model_type == 'anthropic': provider = 'anthropic'; model_name = 'claude-3-5-sonnet-20240620'
        elif model_type == 'llama': provider = 'llama'; model_name = 'llama3'

        ai = AIService(provider=provider, model=model_name, user=current_user)

        if section_id == 'all':
            prompt = f"""
            Como Ingeniero Jefe de Lloyd's Register y experto en arqueología industrial naval, proporciona un INFORME TÉCNICO GLOBAL y EXHAUSTIVO sobre la maquinaria del S.S. Sirio basado en el Informe de Maquinaria de 1883 (Report on Machinery nº 6147).

            DATOS TÉCNICOS COMPLETOS DE MAQUINARIA:
            {section_data_str}

            REGLAS CRÍTICAS:
            1. Analiza la planta propulsora completa: motores de vapor, calderas, sistemas de bombeo y caldera auxiliar.
            2. Contextualiza los datos técnicos en el marco de la ingeniería naval de vapor de la época (1880s).
            3. Ve DIRECTO al análisis. Sin introducciones ceremoniosas.
            4. USA HTML limpio (p, strong, ul, li). NO uses bloques de código con triple comilla (```).
            5. Idioma: ESPAÑOL. Tono: Académico, sobrio y técnico.
            """
        else:
            prompt = f"""
            Como experto analista de Lloyd's Register con conocimientos en ingeniería de vapor del siglo XIX, proporciona un informe técnico e histórico SOBRE la sección "{section_def['title']}" de la maquinaria del S.S. Sirio.

            DATOS TÉCNICOS DE LA SECCIÓN:
            {section_data_str}

            CONTEXTO HISTÓRICO:
            {context_base}

            REGLAS CRÍTICAS:
            1. Ve DIRECTO al análisis de los datos técnicos. Sin introducciones.
            2. Explica el significado técnico e histórico de estos sistemas de propulsión de vapor para la navegación de 1883.
            3. ILUSTRACIONES TÉCNICAS: Tienes permitido (y se recomienda) incluir imágenes de las piezas técnicas si las mencionas.
               USA ESTA SINTAXIS EXACTA: <img src="/static/img/tech/ARCHIVO.png" class="tech-img"> <span class="tech-caption">Título de la Imagen</span>
               ARCHIVOS DISPONIBLES: cilindros.png, calderas.png, helice.png, cigueñal.png.
            4. USA HTML limpio (p, strong, ul, li). NO uses bloques de código con triple comilla (```).
            5. Idioma: ESPAÑOL. Tono: Académico y ejecutivo.
            """

        analisis = ai.generate_content(prompt, temperature=0.7)

        if not analisis:
            return jsonify({'error': 'La IA no pudo generar el análisis.'}), 500

        return jsonify({'analisis': analisis, 'modelo_usado': model_name})

    except Exception as e:
        current_app.logger.error(f"Error en api_analizar_motores: {str(e)}")
        return jsonify({'error': str(e)}), 500
