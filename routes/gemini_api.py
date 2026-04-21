import os
import requests
import json
import re
from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required
from extensions import csrf

# Blueprint para funciones de IA Gemini
gemini_bp = Blueprint('gemini', __name__)

# Configuración API Key (Prioridad a la versión 1.5 Flash por ser más rápida para OCR)
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
GEMINI_API_URL = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent'

def extract_json_from_text(text):
    """Extrae un bloque JSON de una respuesta de texto que podría contener markdown"""
    try:
        # 1. Intentar parsear directamente
        return json.loads(text)
    except json.JSONDecodeError:
        # 2. Buscar bloque de código ```json ... ```
        match = re.search(r'```json\s*(\{.*?\})\s*```', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except: pass
        
        # 3. Buscar cualquier objeto JSON {...}
        match = re.search(r'(\{.*\})', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except: pass
            
    return None

@gemini_bp.route('/api/gemini/correct', methods=['POST'])
@login_required
@csrf.exempt
def correct_ocr_text_advanced():
    """
    Endpoint avanzado que usa AIService para corregir texto OCR con soporte para textos largos (chunking)
    y múltiples modelos/proveedores.
    """
    from services.ai_service import AIService
    from flask_login import current_user
    import logging
    app_logger = logging.getLogger('app')

    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'No se recibieron datos JSON'}), 400

    texto_ocr = data.get('text', '') or data.get('texto', '')
    image_data = data.get('image_data')
    
    # Extraer potencia (proveedor:modelo) si viene en el request
    potencia = data.get('model') or data.get('potencia', 'gemini:flash')
    parts = potencia.split(':')
    provider = parts[0] if len(parts) > 0 else 'gemini'
    model = parts[1] if len(parts) > 1 else None
    
    if not texto_ocr or len(texto_ocr.strip()) < 5:
         return jsonify({'success': False, 'error': 'Texto insuficiente para procesar'}), 400

    # Inicializar AIService
    ai_service = AIService(provider=provider, model=model, user=current_user)
    if not ai_service.is_configured():
        return jsonify({
            'success': False, 
            'error': f'El servicio de IA ({provider}) no está configurado (falta API Key).'
        }), 400

    # Configuración de chunking para textos largos
    # Un fragmento de 15,000 caracteres es seguro para la mayoría de modelos
    CHUNK_SIZE = 15000
    chunks = [texto_ocr[i:i + CHUNK_SIZE] for i in range(0, len(texto_ocr), CHUNK_SIZE)]
    num_chunks = len(chunks)
    
    textos_corregidos = []
    metadatos_finales = {}
    
    try:
        app_logger.info(f"[OCR-IA] Procesando {len(texto_ocr)} carac. en {num_chunks} fragmentos con {potencia}.")

        for i, chunk in enumerate(chunks):
            # Pass image_data only to the first chunk (typical for news clippings)
            current_image = image_data if i == 0 else None
            
            # Usar el método centralizado de AIService para mantener consistencia
            res = ai_service.correct_ocr_text(chunk, part_num=i+1, total_parts=num_chunks, image_data=current_image)
            
            if res:
                # El método devuelve corrected_text y metadata (keys estandarizadas)
                textos_corregidos.append(res.get('corrected_text', ''))
                if i == 0:
                    # Mapear metadatos a la estructura que espera el frontend (metadatos -> metadata)
                    metadatos_finales = res.get('metadata', {})
            else:
                # Fallback: si falla la IA, usar el chunk original
                textos_corregidos.append(chunk)
                    
        # Unir todos los fragmentos
        texto_final = "\n".join(textos_corregidos)

        return jsonify({
            'success': True,
            'corrected_text': texto_final,
            'metadatos': metadatos_finales, # Mantener compatibilidad con JS
            'mensaje': f'Procesado correctamente en {num_chunks} fragmentos.' if num_chunks > 1 else 'Procesado correctamente.'
        })

    except Exception as e:
        app_logger.error(f"Error en endpoint OCR-IA: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@gemini_bp.route('/api/gemini/extract_locations', methods=['POST'])
@login_required
@csrf.exempt
def extract_locations_gemini():
    """
    Usa el servicio Gemini para extraer ubicaciones precisas.
    """
    from services.gemini_service import extract_locations_with_gemini
    
    data = request.get_json()
    texto = data.get('text', '')
    contexto = data.get('context', {})

    res = extract_locations_with_gemini(texto, contexto)
    if not res:
        return jsonify({'success': False, 'error': 'Fallo en el procesamiento de IA'}), 500
        
    return jsonify({
        'success': True,
        'locations': res.get('locations', []),
        'summary': res.get('summary', '')
    })