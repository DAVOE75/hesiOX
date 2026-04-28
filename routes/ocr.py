from flask import Blueprint, request, jsonify
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename
import tempfile
import os
import io
from extensions import csrf
import subprocess
import base64
import cv2
import numpy as np
from PIL import Image, ImageOps, ImageEnhance, ImageFilter
import pytesseract
import sys
from utils import get_nlp, limpieza_profunda_ocr
from services.ai_service import AIService

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

@ocr_bp.route('/api/ocr/pdf-info', methods=['POST'])
@login_required
def ocr_pdf_info():
    """
    Retorna el número de páginas de un PDF
    """
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
        
    filename = secure_filename(file.filename)
    ext = os.path.splitext(filename)[1].lower()
    if ext != '.pdf':
        return jsonify({'error': 'Not a PDF file'}), 400
        
    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = os.path.join(tmpdir, filename)
        file.save(filepath)
        try:
            from pdf2image import pdfinfo_from_path
            info = pdfinfo_from_path(filepath)
            pages = int(info.get('Pages', 0))
            
            # Si detecta 0, forzar al menos 1 o intentar fallback
            if pages == 0:
                raise ValueError("pdfinfo returned 0 pages")
                
            return jsonify({'success': True, 'pages': pages})
        except Exception as e:
            print(f'[OCR DEBUG] pdfinfo_from_path falló o devolvió 0: {e}. Intentando fallback...')
            try:
                # Fallback lento pero seguro: convertir a imágenes y contar
                from pdf2image import convert_from_path
                # Solo cargamos info de las primeras 200 páginas para no saturar memoria en el conteo
                images = convert_from_path(filepath, last_page=200, paths_only=True)
                return jsonify({'success': True, 'pages': len(images)})
            except Exception as e2:
                print(f'[OCR DEBUG] Fallback de conteo también falló: {e2}')
                return jsonify({'error': f'No se pudo determinar el número de páginas: {str(e2)}'}), 500

@ocr_bp.route('/api/ocr/advanced', methods=['POST'])
@csrf.exempt
@login_required
def ocr_advanced():
    """
    Endpoint OCR avanzado: recibe imagen o PDF, preprocesa y ejecuta Tesseract nativo
    """
    ocr_engine = request.form.get('ocr_engine', 'tesseract')
    
    # DEBUG: Ver qué llega exactamente
    print(f'[OCR DEBUG] request.form keys: {list(request.form.keys())}')
    print(f'[OCR DEBUG] request.form values: {request.form.to_dict(flat=True)}')
    
    # Obtener número de página de forma redundante (form, args, values)
    page_number_raw = request.values.get('page_number') or request.form.get('page_number') or request.args.get('page_number')
    page_number = None
    if page_number_raw:
        try:
            page_number = int(float(page_number_raw)) # Soportar posibles decimales por error
        except (ValueError, TypeError):
            page_number = None
            
    print(f'[OCR DEBUG] Motor: {ocr_engine}, Página detectada en backend: {page_number}')
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
        
        # 1. Detectar total de páginas si es PDF (para sincronización UI)
        total_pages_detected = 0
        if ext == '.pdf':
            try:
                from pdf2image import pdfinfo_from_path
                info = pdfinfo_from_path(filepath)
                total_pages_detected = int(info.get('Pages', 0))
            except: pass
            
        # 2. CAPA DE NORMALIZACIÓN: Si es una página específica de PDF, la convertimos en imagen YA
        # Esto hace que el resto de los motores (Tesseract, OCRSpace, AI) vean solo una imagen
        if ext == '.pdf' and page_number:
            print(f'[OCR DEBUG] NORMALIZACIÓN FORZADA: Convirtiendo PDF pág {page_number} a JPEG')
            normalized_base = os.path.join(tmpdir, "normalized_page")
            try:
                subprocess.run([
                    'pdftoppm', '-jpeg', '-f', str(page_number), '-l', str(page_number),
                    '-singlefile', filepath, normalized_base
                ], check=True, capture_output=True)
                
                normalized_path = normalized_base + ".jpg"
                if os.path.exists(normalized_path):
                    filepath = normalized_path
                    ext = ".jpg" # El archivo ahora es un JPEG para el resto de la función
                    print(f'[OCR DEBUG] ✓ PDF normalizado con éxito. Continuando como imagen.')
            except Exception as e_norm:
                print(f'[OCR DEBUG] ⚠ Error en normalización: {e_norm}. Se usará lógica PDF nativa.')

        # 3. Cargar imagen para procesamiento local (PIL)
        img = None
        if ext in ['.jpg', '.jpeg', '.png', '.tiff', '.bmp', '.webp']:
            try:
                img = Image.open(filepath)
            except Exception as e_img:
                print(f'[OCR DEBUG] Error abriendo imagen: {e_img}')

        text = ''
        confidence = None
        base64_image = None
        words_data = [] # Para el mapa de calor
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
                
                parsed_results = result.get('ParsedResults', [])
                if page_number:
                    if len(parsed_results) >= page_number:
                        text = parsed_results[page_number - 1].get('ParsedText', '')
                    else:
                        text = parsed_results[0].get('ParsedText', '') if parsed_results else ''
                else:
                    # EXTRACCIÓN MULTI-PÁGINA: Concatenar todas las páginas detectadas
                    text = '\n\n'.join([res.get('ParsedText', '') for res in parsed_results])
                
                confidence = None
                print(f'[OCR DEBUG] Texto extraído OCR.space ({len(parsed_results)} pág): {text[:100]}...')
                # Para imágenes, devolver base64 para que la IA corrija viendo el original
                if ext in ['.jpg', '.jpeg', '.png']:
                    with open(filepath, "rb") as img_f:
                        base64_image = base64.b64encode(img_f.read()).decode('utf-8')
            elif ocr_engine == 'tesseract' and ext in ['.jpg', '.jpeg', '.png', '.tiff', '.bmp', '.webp']:
                # --- PREPROCESADO AVANZADO (OPENCV) ---
                print(f'[OCR DEBUG] Iniciando preprocesado OpenCV. img type: {type(img)}')
                try:
                    if img is None:
                        raise ValueError("La imagen (img) es None antes de np.array")
                        
                    open_cv_image = np.array(img)
                    print(f'[OCR DEBUG] np.array(img) ok. Shape: {open_cv_image.shape}')
                    
                    # Convertir a escala de grises si no lo está
                    if len(open_cv_image.shape) == 3:
                        gray = cv2.cvtColor(open_cv_image, cv2.COLOR_RGB2GRAY)
                    else:
                        gray = open_cv_image
                    
                    print(f'[OCR DEBUG] Escala de grises ok. Shape: {gray.shape}')
                    
                    # --- AUTO-DESKEW (Corrección de inclinación) ---
                    coords = np.column_stack(np.where(gray < 127))
                    if coords.size > 0:
                        angle = cv2.minAreaRect(coords)[-1]
                        # Ajustar el ángulo para que sea entre -45 y 45 grados
                        if angle < -45:
                            angle = -(90 + angle)
                        else:
                            angle = -angle
                        
                        if abs(angle) > 0.5: # Solo rotar si hay inclinación significativa
                            (h, w) = gray.shape[:2]
                            center = (w // 2, h // 2)
                            M = cv2.getRotationMatrix2D(center, angle, 1.0)
                            gray = cv2.warpAffine(gray, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
                            print(f'[OCR DEBUG] Deskew aplicado: {angle:.2f} grados')
                    
                    # Eliminación de ruido no local (Non-Local Means Denoising)
                    denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
                    
                    # Umbralado adaptativo
                    thresh = cv2.adaptiveThreshold(denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
                    
                    # Volver a PIL para Tesseract
                    img = Image.fromarray(thresh)
                    print(f'[OCR DEBUG] Preprocesado finalizado con éxito.')
                except Exception as e_pre:
                    print(f'[OCR WARNING] Fallo en preprocesado OpenCV: {e_pre}. Usando imagen original.')
                    # No fallar el OCR por el preprocesado, usar imagen original como fallback
                    img = Image.open(filepath) if img is None else img
                
                # Guardar imagen procesada para devolverla (Base64)
                buffered = io.BytesIO()
                img.save(buffered, format="JPEG")
                base64_image = base64.b64encode(buffered.getvalue()).decode('utf-8')
                
                # OCR con DATA (para mapa de calor)
                print(f'[OCR DEBUG] Usando tesseract cmd: {pytesseract.pytesseract.tesseract_cmd}')
                custom_config = '--psm 1 -l spa'
                ocr_result = pytesseract.image_to_data(img, config=custom_config, output_type=pytesseract.Output.DICT)
                
                # Reconstruir texto y recopilar datos de confianza por palabra
                text = ' '.join([w for w in ocr_result['text'] if w.strip()])
                words_data = []
                for i in range(len(ocr_result['text'])):
                    word = ocr_result['text'][i]
                    if word.strip():
                        words_data.append({
                            'word': word,
                            'confidence': int(ocr_result['conf'][i])
                        })
                
                print(f'[OCR DEBUG] Texto extraído Tesseract: {text[:100]}...')
                # Calcular confianza media global
                confidences = [float(c) for c in ocr_result['conf'] if c != '-1']
                confidence = sum(confidences) / len(confidences) if confidences else None
            elif ocr_engine == 'tesseract' and ext == '.pdf':
                # Convertir PDF a imágenes (requiere pdf2image)
                from pdf2image import convert_from_path, pdfinfo_from_path
                # Ya tenemos page_number del inicio de la función
                
                total_pages_detected = 0
                try:
                    info = pdfinfo_from_path(filepath)
                    total_pages_detected = int(info.get('Pages', 0))
                    print(f'[OCR DEBUG] PDF info detectado: {total_pages_detected} páginas')
                except Exception as e_info:
                    print(f'[OCR DEBUG] Error obteniendo info del PDF: {e_info}')
                
                try:
                    if page_number:
                        print(f'[OCR DEBUG] EXTRACCIÓN DIRECTA pdftoppm (Pág {page_number})')
                        # Usar pdftoppm para extraer SOLO la página solicitada a un JPG temporal
                        # -singlefile asegura que no añada sufijos de numeración si solo es una pág
                        output_base = os.path.join(tmpdir, f"page_extract_{page_number}")
                        try:
                            subprocess.run([
                                'pdftoppm', '-jpeg', '-f', str(page_number), '-l', str(page_number),
                                '-singlefile', filepath, output_base
                            ], check=True, capture_output=True)
                            
                            extracted_img_path = output_base + ".jpg"
                            if os.path.exists(extracted_img_path):
                                images = [Image.open(extracted_img_path)]
                            else:
                                raise FileNotFoundError(f"No se encontró el archivo extraído: {extracted_img_path}")
                        except Exception as e_cmd:
                            print(f'[OCR WARNING] pdftoppm falló: {e_cmd}. Usando fallback pdf2image.')
                            images = convert_from_path(filepath, first_page=page_number, last_page=page_number)
                            if len(images) > 1 and page_number <= len(images):
                                images = [images[page_number - 1]]
                    else:
                        print(f'[OCR DEBUG] Procesando todas las páginas del PDF')
                        images = convert_from_path(filepath)
                except Exception as e:
                     print(f'[OCR DEBUG] Error converting PDF: {e}')
                     return jsonify({'error': f'Error processing PDF: {str(e)}'}), 500
                     
                texts = []
                confidences = []
                for idx, img in enumerate(images):
                    img = img.convert('L')
                    img = ImageOps.autocontrast(img)
                    # Mejora: no binarizar tan agresivamente para Tesseract 
                    # img = img.point(lambda x: 0 if x < 180 else 255, '1')
                    
                    # Si es una página específica, guardarla temporalmente para que Deep Vision la use
                    if page_number:
                        temp_page_path = os.path.join(tmpdir, f"page_{page_number}.jpg")
                        img.save(temp_page_path, "JPEG")
                        filepath = temp_page_path # Reemplazamos filepath para que el bloque de Vision use esta página

                    custom_config = '--psm 3 -l spa'
                    ocr_result = pytesseract.image_to_data(img, config=custom_config, output_type=pytesseract.Output.DICT)
                    page_text = ' '.join([t for t in ocr_result['text'] if t.strip()])
                    texts.append(page_text)
                    
                    print(f"[OCR DEBUG] Texto extraído página {page_number if page_number else idx+1}: {page_text[:100]}...")
                    page_conf = [float(c) for c in ocr_result['conf'] if c != '-1']
                    if page_conf:
                        confidences.extend(page_conf)
                
                if page_number:
                    # SEGURO FINAL: Si por algún error de lógica llegamos aquí con varias páginas
                    # pero se solicitó una sola, nos aseguramos de devolver solo el primer texto extraído.
                    if len(texts) > 1:
                        print(f'[OCR WARNING] Se detectaron {len(texts)} páginas pero se solicitó la {page_number}. Truncando.')
                        texts = [texts[0]]
                
                text = '\n\n'.join(texts)
                confidence = sum(confidences) / len(confidences) if confidences else None
            elif ocr_engine == 'paddle':
                try:
                    from paddleocr import PaddleOCR
                    # PaddleOCR: lang='es' para español, use_angle_cls=True para detectar orientación
                    # lazy load del modelo para evitar consumo de RAM si no se usa
                    ocr_p = PaddleOCR(use_angle_cls=True, lang='es', show_log=False)
                    result = ocr_p.ocr(filepath, cls=True)
                    
                    texts = []
                    all_confidences = []
                    
                    if result:
                        # Si es PDF, result es una lista de listas (una por página)
                        # Si es imagen, result es una lista de líneas
                        # Detectamos si es multi-página por la estructura de la lista
                        is_multi = isinstance(result, list) and len(result) > 0 and isinstance(result[0], list) and len(result[0]) > 0 and isinstance(result[0][0], list)
                        
                        if is_multi:
                            for page_res in result:
                                if page_res:
                                    page_lines = [line[1][0] for line in page_res]
                                    texts.append('\n'.join(page_lines))
                                    all_confidences.extend([line[1][1] for line in page_res])
                        else:
                            # Imagen única
                            target = result[0] if isinstance(result, list) and len(result) > 0 and isinstance(result[0], list) else result
                            lines = [line[1][0] for line in target if isinstance(line, list) and len(line) > 1]
                            texts.append('\n'.join(lines))
                            all_confidences.extend([line[1][1] for line in target if isinstance(line, list) and len(line) > 1])
                    
                    text = '\n\n'.join(texts)
                    confidence = (sum(all_confidences) / len(all_confidences)) * 100 if all_confidences else 90
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

            elif ocr_engine == 'hybrid':
                print('[OCR DEBUG] Modo HÍBRIDO activado: Ejecutando doble paso de Tesseract...')
                # Paso 1: Configuración estándar (PSM 1 - Auto segmentation)
                res1 = pytesseract.image_to_data(img, config='--psm 1 -l spa', output_type=pytesseract.Output.DICT)
                txt1 = ' '.join([w for w in res1['text'] if w.strip()])
                
                # Paso 2: Configuración de bloque único (PSM 6 - Assume a single uniform block of text)
                res2 = pytesseract.image_to_data(img, config='--psm 6 -l spa', output_type=pytesseract.Output.DICT)
                txt2 = ' '.join([w for w in res2['text'] if w.strip()])
                
                # Usaremos la IA para reconciliar ambos borradores más adelante
                text = f"--- BORRADOR 1 ---\n{txt1}\n\n--- BORRADOR 2 ---\n{txt2}"
                words_data = [] # En modo híbrido la confianza es gestionada por la reconciliación IA
                confidence = 85 # Valor nominal
                
                # Indicar al servicio de IA que debe reconciliar
                request.form = request.form.copy()
                request.form['reconcile_hybrid'] = 'true'
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
        with open(filepath, 'rb') as image_file:
            image_base64 = base64.b64encode(image_file.read()).decode('utf-8')
            # Detectar MIME type corregido
            if ext == '.pdf' and page_number:
                mime_type = "image/jpeg" # Es el JPG extraído
            elif ext == '.pdf':
                mime_type = "application/pdf"
            elif ext == '.png': 
                mime_type = "image/png"
            else:
                mime_type = "image/jpeg"
            
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
                # Prompt especial si estamos en modo híbrido
                custom_prompt = None
                if request.form.get('reconcile_hybrid') == 'true':
                    custom_prompt = "Actúa como un experto paleógrafo. Te proporciono dos borradores de OCR (Borrador 1 y Borrador 2) del mismo documento histórico. Tu tarea es compararlos, reconciliar las discrepancias usando tu conocimiento del contexto y la imagen adjunta, y generar la transcripción maestra definitiva. Mantén la estructura de columnas y marcadores si los detectas."
                
                # Usamos el servicio con soporte para Visión
                ai_result = ai_service.correct_ocr_text(text, image_data=image_data, custom_prompt=custom_prompt)
            
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

        if text:
            text = text.replace('**', '').replace('*', '')
            import re
            text = re.sub(r'#+\s*', '', text)

        return jsonify({
            'text': text, 
            'confidence': confidence, 
            'entities': entities,
            'metadata': ai_metadata,
            'words_data': words_data,
            'total_pages': total_pages_detected if 'total_pages_detected' in locals() else 1,
            'image_data': image_data if 'image_data' in locals() else None
        })

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
        image_data = data.get('image_data')  # Base64 de la imagen para Vision
        
        print(f'[OCR CORREGIR] Recibido texto de len={len(texto)} | Vision: {bool(image_data)}')
        
        correcciones = []
        advertencias = []
        
        # 1. Intentar con AIService (Priorizando claves de usuario)
        ai_service = AIService(user=current_user)
        if ai_service.is_configured():
            print("[OCR CORREGIR] Usando IA para corrección (con perfil de usuario y Vision)...")
            ai_result = ai_service.correct_ocr_text(texto, image_data=image_data)
            
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
                
                if corrected_text:
                    corrected_text = corrected_text.replace('**', '').replace('*', '')
                    import re
                    corrected_text = re.sub(r'#+\s*', '', corrected_text)

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
