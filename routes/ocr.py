from flask import Blueprint, request, jsonify
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename
import tempfile
import os
from PIL import Image, ImageOps, ImageEnhance, ImageFilter
import pytesseract
import sys
from utils import get_nlp, limpieza_profunda_ocr
from services.ai_service import AIService
from extensions import csrf

ocr_bp = Blueprint('ocr', __name__)

# Configuración de Tesseract para Windows
# Intentar localizar el ejecutable en rutas comunes si no está en el PATH
def find_tesseract():
    # 1. Prioridad: Ruta estándar de Linux (Server Production)
    if os.path.exists('/usr/bin/tesseract'):
        pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'
        print(f'[OCR CONFIG] Tesseract encontrado y configurado en: /usr/bin/tesseract')
        return

    # 2. Rutas comunes de Windows (Local Dev)
    tesseract_paths = [
        r'C:\Program Files\Tesseract-OCR\tesseract.exe',
        r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
        os.path.expandvars(r'%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe')
    ]
    for path in tesseract_paths:
        if os.path.exists(path):
            pytesseract.pytesseract.tesseract_cmd = path
            print(f'[OCR CONFIG] pytesseract usará: {path}')
            return
            
    # 3. Fallback: shutil.which
    import shutil
    if shutil.which('tesseract'):
        pytesseract.pytesseract.tesseract_cmd = shutil.which('tesseract')
        print(f'[OCR CONFIG] pytesseract usará desde PATH: {pytesseract.pytesseract.tesseract_cmd}')
        return
    
    print('[OCR CONFIG] ERROR: Tesseract no encontrado. Verifique instalación y PATH.')

# Ejecutar búsqueda al inicio
find_tesseract()

@ocr_bp.route('/api/ocr/advanced', methods=['POST'])
@csrf.exempt
@login_required
def ocr_advanced():
    """
    Endpoint OCR avanzado: recibe imagen o PDF, preprocesa y ejecuta Tesseract nativo
    """
    ocr_engine = request.form.get('ocr_engine', 'tesseract')
    print(f'[OCR DEBUG] Motor OCR seleccionado: {ocr_engine}')
    if 'file' not in request.files:
        print('[OCR DEBUG] No file part in request.files')
        return jsonify({'error': 'No file part in the request'}), 400
    file = request.files['file']
    if file.filename == '':
        print('[OCR DEBUG] No selected file')
        return jsonify({'error': 'No selected file'}), 400
        
    filename = secure_filename(file.filename)
    ext = os.path.splitext(filename)[1].lower()
    print(f'[OCR DEBUG] Archivo recibido: {filename} (ext: {ext})')
    
    allowed_extensions = {'.jpg', '.jpeg', '.png', '.tiff', '.bmp', '.webp', '.pdf'}
    if not ext or ext not in allowed_extensions:
        print(f'[OCR DEBUG] Tipo de archivo no soportado: {ext}')
        return jsonify({'error': f'Unsupported file type: {ext}. Allowed: {", ".join(allowed_extensions)}'}), 400
    
    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = os.path.join(tmpdir, filename)
        file.save(filepath)
        text = ''
        confidence = None
        try:
            # Condicional revisado: usar el motor OCR seleccionado, no solo por extensión
            if ocr_engine == 'ocrspace':
                import requests
                api_url = 'https://api.ocr.space/parse/image'
                with open(filepath, 'rb') as f:
                    r = requests.post(api_url,
                        files={'file': f},
                        data={'language': 'spa', 'isOverlayRequired': False},
                        headers={'apikey': 'helloworld'})
                result = r.json()
                if result.get('IsErroredOnProcessing'):
                    return jsonify({'error': result.get('ErrorMessage', 'Error en OCR.space')}), 500
                parsed = result['ParsedResults'][0]
                text = parsed.get('ParsedText', '')
                confidence = None
                print(f'[OCR DEBUG] Texto extraído OCR.space: {text}')
            elif ocr_engine == 'tesseract' and ext in ['.jpg', '.jpeg', '.png', '.tiff', '.bmp', '.webp']:
                # Preprocesado: escala de grises, binarización, contraste, deskew
                img = Image.open(filepath)
                img = img.convert('L')  # Escala de grises
                img = ImageOps.autocontrast(img)
                from PIL import ImageFilter, ImageEnhance
                # Reducción de ruido
                # Doble reducción de ruido
                img = img.filter(ImageFilter.MedianFilter(size=3))
                img = img.filter(ImageFilter.MedianFilter(size=3))
                # Nitidez fuerte
                img = img.filter(ImageFilter.UnsharpMask(radius=2, percent=200, threshold=3))
                # Contraste alto
                img = ImageEnhance.Contrast(img).enhance(3)
                # Brillo
                img = ImageEnhance.Brightness(img).enhance(1.3)
                # img = img.point(lambda x: 0 if x < 180 else 255, '1')  # Binarización eliminada
                # Deskew (opcional, requiere OpenCV)
                # ...
                # OCR
                print(f'[OCR DEBUG] Usando tesseract cmd: {pytesseract.pytesseract.tesseract_cmd}')
                custom_config = '--psm 1 -l spa'
                ocr_result = pytesseract.image_to_data(img, config=custom_config, output_type=pytesseract.Output.DICT)
                text = ' '.join(ocr_result['text'])
                print(f'[OCR DEBUG] Texto extraído Tesseract: {text}')
                # Calcular confianza media
                confidences = [float(c) for c in ocr_result['conf'] if c != '-1']
                confidence = sum(confidences) / len(confidences) if confidences else None
            elif ocr_engine == 'tesseract' and ext == '.pdf':
                # Convertir PDF a imágenes (requiere pdf2image)
                from pdf2image import convert_from_path
                # Check if poppler is installed/configured if needed, or handle import error gracefully
                try:
                    images = convert_from_path(filepath)
                except Exception as e:
                     print(f'[OCR DEBUG] Error converting PDF: {e}')
                     return jsonify({'error': f'Error processing PDF: {str(e)}'}), 500
                     
                texts = []
                confidences = []
                for img in images:
                    img = img.convert('L')
                    img = ImageOps.autocontrast(img)
                    img = img.point(lambda x: 0 if x < 180 else 255, '1')
                    ocr_result = pytesseract.image_to_data(img, config='--psm 3 -l spa', output_type=pytesseract.Output.DICT)
                    texts.append(' '.join(ocr_result['text']))
                    print(f"[OCR DEBUG] Texto extraído página PDF: {' '.join(ocr_result['text'])}")
                    page_conf = [float(c) for c in ocr_result['conf'] if c != '-1']
                    if page_conf:
                        confidences.extend(page_conf)
                text = '\\n'.join(texts)
                confidence = sum(confidences) / len(confidences) if confidences else None
            elif ocr_engine == 'paddle':
                try:
                    from paddleocr import PaddleOCR
                    # PaddleOCR: lang='es' para español, use_angle_cls=True para detectar orientación
                    # lazy load del modelo para evitar consumo de RAM si no se usa
                    ocr_p = PaddleOCR(use_angle_cls=True, lang='es', show_log=False)
                    result = ocr_p.ocr(filepath, cls=True)
                    if result and result[0]:
                        # Aplanar resultados: Paddle devuelve [ [[coords], [text, conf]], ... ]
                        lines = [line[1][0] for line in result[0]]
                        text = '\n'.join(lines)
                        confidences = [line[1][1] for line in result[0]]
                        confidence = (sum(confidences) / len(confidences)) * 100 if confidences else None
                    print(f'[OCR DEBUG] Texto extraído PaddleOCR: {text[:100]}...')
                except ImportError:
                    print('[OCR DEBUG] PaddleOCR no instalado')
                    return jsonify({'error': 'Motor PaddleOCR no instalado en el servidor. Instale paddlepaddle y paddleocr.'}), 501
                except Exception as e_paddle:
                    print(f'[OCR DEBUG] Error en PaddleOCR: {e_paddle}')
                    return jsonify({'error': f'Error en PaddleOCR: {str(e_paddle)}'}), 500

            elif ocr_engine == 'yolo':
                try:
                    from ultralytics import YOLO
                    import cv2
                    import numpy as np
                    
                    # Cargamos el modelo YOLO (preferiblemente uno de detección de texto/layout)
                    # Usamos yolov8n como base si no hay uno específico
                    model_yolo = YOLO('yolov8n.pt') 
                    results_yolo = model_yolo(filepath, verbose=False)
                    
                    img_cv = cv2.imread(filepath)
                    blocks_text = []
                    conf_list = []
                    
                    # Si YOLO detecta objetos, intentamos OCR por bloques
                    has_detections = False
                    for r in results_yolo:
                        if len(r.boxes) > 0:
                            has_detections = True
                            # Ordenar cajas de arriba a abajo para mantener orden de lectura
                            boxes = sorted(r.boxes.data.tolist(), key=lambda x: x[1])
                            for box in boxes:
                                x1, y1, x2, y2, conf_yolo, cls = box
                                # Crop con un pequeño margen
                                h, w = img_cv.shape[:2]
                                pad = 5
                                crop = img_cv[max(0, int(y1)-pad):min(h, int(y2)+pad), 
                                              max(0, int(x1)-pad):min(w, int(x2)+pad)]
                                
                                # Usamos Tesseract para el texto dentro del bloque detectado por YOLO
                                ocr_data = pytesseract.image_to_data(crop, config='--psm 6 -l spa', output_type=pytesseract.Output.DICT)
                                block_txt = ' '.join([t for t in ocr_data['text'] if t.strip()])
                                if block_txt.strip():
                                    blocks_text.append(block_txt.strip())
                                    c_vals = [float(c) for c in ocr_data['conf'] if c != '-1']
                                    if c_vals: conf_list.extend(c_vals)

                    if has_detections and blocks_text:
                        text = '\n\n'.join(blocks_text)
                        confidence = sum(conf_list) / len(conf_list) if conf_list else None
                    else:
                        # Fallback: Si YOLO no detecta nada o falla la segmentación, Tesseract normal
                        ocr_data = pytesseract.image_to_data(img_cv, config='--psm 3 -l spa', output_type=pytesseract.Output.DICT)
                        text = ' '.join([t for t in ocr_data['text'] if t.strip()])
                        c_vals = [float(c) for c in ocr_data['conf'] if c != '-1']
                        confidence = sum(c_vals) / len(c_vals) if c_vals else None

                    print(f'[OCR DEBUG] Texto extraído YOLO+Tesseract: {text[:100]}...')
                except ImportError:
                    print('[OCR DEBUG] Ultralytics/OpenCV no instalado')
                    return jsonify({'error': 'Motor YOLO requiere ultralytics y opencv-python.'}), 501
                except Exception as e_yolo:
                    print(f'[OCR DEBUG] Error en YOLO: {e_yolo}')
                    return jsonify({'error': f'Error en YOLO: {str(e_yolo)}'}), 500

            else:
                return jsonify({'error': 'Unsupported OCR engine or file type combo'}), 400
        except Exception as e:
            print(f'[OCR DEBUG] Exception during OCR processing: {e}')
            import traceback
            traceback.print_exc()
            return jsonify({'error': f'Internal OCR Error: {str(e)}'}), 500
        
        # Capturar el modelo de IA seleccionado para la corrección profunda automática
        ocr_model_raw = request.form.get('ocr_model', 'gemini:flash')
        parts = ocr_model_raw.split(':')
        provider = parts[0] if len(parts) > 0 else 'gemini'
        model = parts[1] if len(parts) > 1 else None

        # Preparar imagen en Base64 para Visión Multimodal
        import base64
        with open(filepath, 'rb') as image_file:
            image_base64 = base64.b64encode(image_file.read()).decode('utf-8')
            # Detectar MIME type simplificado
            mime_type = "image/jpeg"
            if ext == '.png': mime_type = "image/png"
            elif ext == '.pdf': mime_type = "application/pdf"
            image_data = f"data:{mime_type};base64,{image_base64}"

        # Aplicar limpieza profunda técnica (heurísticas) antes de la IA
        text = limpieza_profunda_ocr(text)
        # ==============================================================================
        # PROCESAMIENTO MEJORADO CON IA (AIService) — Deep Vision Hybrid
        # ==============================================================================
        # Hibridación: Se pasa el Borrador OCR + Imagen Original a la IA
        ai_service = AIService(provider=provider, model=model, user=current_user)
        ai_metadata = {}

        if ai_service.is_configured() and text and len(text.strip()) > 5:
            print(f"[OCR ADVANCED - DEEP VISION] Iniciando hibridación con {provider}:{model}...")
            try:
                # Usamos el servicio con soporte para Visión
                ai_result = ai_service.correct_ocr_text(text, image_data=image_data)
            
                if ai_result and ai_result.get('corrected_text'):
                    print("[OCR ADVANCED] Texto mejorado por Gemini correctamente.")
                    # REEMPLAZO CRÍTICO: Usamos el texto de la IA como el texto principal
                    text = ai_result.get('corrected_text')
                    ai_metadata = ai_result.get('metadata', {})
                else:
                    print("[OCR ADVANCED] Gemini no devolvió corrección, usando texto original.")
            except Exception as e_gemini:
                print(f"[OCR ADVANCED] Error no bloqueante en Gemini: {e_gemini}")

        # ==============================================================================
        # PROCESAMIENTO NLP (Spacy)
        # ==============================================================================
        entities = []
        try:
            if text:
                nlp = get_nlp()
                if nlp:
                    doc = nlp(text)
                    for ent in doc.ents:
                        if ent.label_ in ['LOC', 'PER', 'ORG', 'MISC']:
                            entities.append({
                                'text': ent.text,
                                'label': ent.label_
                            })
                    print(f'[OCR NLP] Entidades detectadas (Spacy sobre texto optimizado): {len(entities)}')
        except Exception as e:
            print(f'[OCR NLP] Error procesando entidades: {e}')

        return jsonify({'text': text, 'confidence': confidence, 'entities': entities})

@ocr_bp.route('/api/ocr/corregir', methods=['POST'])
@csrf.exempt
@login_required
def ocr_corregir():
    """
    Endpoint para corregir/mejorar texto y metadatos usando IA (Gemini) o fallback local.
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
            
        texto = data.get('texto', '')
        metadatos = data.get('metadatos', {})
        
        print(f'[OCR CORREGIR] Recibido texto de len={len(texto)}')
        
        correcciones = []
        advertencias = []
        
        # 1. Intentar con AIService (Priorizando claves de usuario)
        ai_service = AIService(user=current_user)
        if ai_service.is_configured():
            print("[OCR CORREGIR] Usando IA para corrección (con perfil de usuario)...")
            ai_result = ai_service.correct_ocr_text(texto)
            
            if ai_result:
                print("[OCR CORREGIR] Gemini devolvió resultados exitosos.")
                
                # Actualizar texto corregido
                corrected_text = ai_result.get('corrected_text', texto)
                
                # Actualizar metadatos si Gemini encontró algo
                ai_meta = ai_result.get('metadata', {})
                
                if ai_meta.get('titulo') and not metadatos.get('titulo'):
                    metadatos['titulo'] = ai_meta['titulo']
                    correcciones.append(f"Título sugerido (AI): {ai_meta['titulo']}")
                    
                if ai_meta.get('autor') and not metadatos.get('autor'):
                    metadatos['autor'] = ai_meta['autor']
                    correcciones.append(f"Autor sugerido (AI): {ai_meta['autor']}")
                    
                if ai_meta.get('fecha') and not metadatos.get('fecha_original'):
                    metadatos['fecha_original'] = ai_meta['fecha']
                    # Intentar extraer año
                    import re
                    match = re.search(r'\d{4}', ai_meta['fecha'])
                    if match:
                        metadatos['anio'] = match.group(0)
                    correcciones.append(f"Fecha detectada (AI): {ai_meta['fecha']}")
                    
                if ai_meta.get('publicacion') and not metadatos.get('publicacion'):
                    metadatos['publicacion'] = ai_meta['publicacion']
                    correcciones.append(f"Publicación sugerida (AI): {ai_meta['publicacion']}")
                    
                if ai_meta.get('lugar') and not metadatos.get('ciudad'):
                    metadatos['ciudad'] = ai_meta['lugar']
                    correcciones.append(f"Ciudad sugerida (AI): {ai_meta['lugar']}")

                metadatos['confianza'] = 95  # Alta confianza con AI
                correcciones.append("Texto corregido y estructurado por Gemini AI.")
                
                return jsonify({
                    'success': True,
                    'metadatos': metadatos,
                    'corrected_text': corrected_text
                })
            else:
                print("[OCR CORREGIR] Falló Gemini, usando fallback local...")
                advertencias.append("El servicio de IA no pudo procesar la solicitud. Se usaron heurísticas locales.")
        else:
            print("[OCR CORREGIR] Gemini no configurado. Usando métodos locales.")

        # ==============================================================================
        # FALLBACK: LÓGICA LOCAL (Spacy + Regex)
        # ==============================================================================
        
        # Procesamiento con Spacy
        nlp = get_nlp()
        if nlp and texto:
            doc = nlp(texto)
            
            # 1. Detectar posibles AUTORES (PER)
            autores = [ent.text for ent in doc.ents if ent.label_ == 'PER']
            if autores:
                # Heurística simple: tomar el primero si no hay autor definido
                sugerencia = autores[0]
                if not metadatos.get('autor'):
                    metadatos['autor'] = sugerencia
                    correcciones.append(f"Autor sugerido: {sugerencia}")
            
            # 2. Detectar posibles CIUDADES (LOC)
            lugares = [ent.text for ent in doc.ents if ent.label_ == 'LOC']
            if lugares:
                sugerencia = lugares[0]
                if not metadatos.get('ciudad'):
                    metadatos['ciudad'] = sugerencia
                    correcciones.append(f"Ciudad sugerida: {sugerencia}")

            # 3. Detectar ORGANIZACIONES (ORG) -> Posible Publicación
            orgs = [ent.text for ent in doc.ents if ent.label_ == 'ORG']
            if orgs:
                sugerencia = orgs[0]
                if not metadatos.get('publicacion'):
                    metadatos['publicacion'] = sugerencia
                    correcciones.append(f"Publicación sugerida: {sugerencia}")

        # 4. Heurística de FECHA (Regex simple)
        import re
        # Buscar dd/mm/yyyy o dd-mm-yyyy
        date_pattern = r'\b(\d{1,2})[-/](\d{1,2})[-/](\d{2,4})\b'
        match = re.search(date_pattern, texto)
        if match:
            dia, mes, anio = match.groups()
            if len(anio) == 2: anio = '19' + anio # Asumir siglo XX por defecto
            fecha_fmt = f"{int(dia):02d}/{int(mes):02d}/{anio}"
            if not metadatos.get('fecha_original'):
                metadatos['fecha_original'] = fecha_fmt
                metadatos['anio'] = anio
                correcciones.append(f"Fecha detectada: {fecha_fmt}")

        # Simular confianza mejorada
        metadatos['confianza'] = min((metadatos.get('confianza', 0) or 50) + 10, 100)
        
        if not correcciones:
            correcciones.append("Revisión completada. No se encontraron cambios obvios.")

        return jsonify({
            'success': True,
            'metadatos': {
                'titulo': metadatos.get('titulo'),
                'autor': metadatos.get('autor'),
                'fecha_original': metadatos.get('fecha_original'),
                'anio': metadatos.get('anio'),
                'publicacion': metadatos.get('publicacion'),
                'ciudad': metadatos.get('ciudad'),
                'pagina_inicio': metadatos.get('pagina_inicio'),
                'pagina_fin': metadatos.get('pagina_fin'),
                'confianza': metadatos['confianza'],
                'correcciones': correcciones,
                'advertencias': advertencias
            },
            'corrected_text': texto # Fallback devuelve mismo texto
        })

    except Exception as e:
        print(f'[OCR CORREGIR] Error: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500
