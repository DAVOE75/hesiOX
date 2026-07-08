from flask import Blueprint, request, jsonify
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename
import tempfile
import os
import io
import subprocess
import base64
import cv2
import numpy as np
from PIL import Image, ImageOps, ImageEnhance, ImageFilter
import pytesseract
import sys
from extensions import csrf
from utils import get_nlp, limpieza_profunda_ocr
from services.ai_service import AIService

ocr_bp = Blueprint('ocr', __name__)

def find_tesseract():
    if os.path.exists('/usr/bin/tesseract'):
        pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'
        return
    import shutil
    if shutil.which('tesseract'):
        pytesseract.pytesseract.tesseract_cmd = shutil.which('tesseract')
        return

find_tesseract()
        
def preprocess_historical_image(img_pil):
    """
    Aplica restauración digital equilibrada:
    CLAHE suave y Sharpening para tipografías finas.
    """
    # Convertir PIL a OpenCV
    open_cv_image = np.array(img_pil.convert('RGB'))
    gray = cv2.cvtColor(open_cv_image, cv2.COLOR_RGB2GRAY)
    
    # 1. CLAHE muy suave para no quemar blancos
    clahe = cv2.createCLAHE(clipLimit=1.5, tileGridSize=(8,8))
    gray_clahe = clahe.apply(gray)
    
    # 2. Sharpening (Unsharp Mask) para definir bordes de letras finas
    gaussian = cv2.GaussianBlur(gray_clahe, (0, 0), 2.0)
    sharpened = cv2.addWeighted(gray_clahe, 1.5, gaussian, -0.5, 0)
    
    return Image.fromarray(sharpened)

def extract_words_data(ocr_result, width, height, page=1):
    """ Extrae datos de palabras y coordenadas normalizadas (0-100) para el frontend """
    words_data = []
    if not ocr_result or 'level' not in ocr_result:
        return []
    for i in range(len(ocr_result['text'])):
        # Nivel 5 son palabras en Pytesseract
        if int(ocr_result['level'][i]) == 5 and ocr_result['text'][i].strip():
            # Calculamos en porcentaje (0-100) para compatibilidad con el visor
            x = (ocr_result['left'][i] / width) * 100
            y = (ocr_result['top'][i] / height) * 100
            w = (ocr_result['width'][i] / width) * 100
            h = (ocr_result['height'][i] / height) * 100
            
            words_data.append({
                'text': ocr_result['text'][i],
                'word': ocr_result['text'][i], # Para compatibilidad con frontend
                'confidence': int(ocr_result['conf'][i]),
                'x': x,
                'y': y,
                'w': w,
                'h': h,
                'bbox': [y*10, x*10, (y+h)*10, (x+w)*10], # 0-1000 format
                'p': page
            })
    return words_data

@ocr_bp.route('/api/ocr/pdf-info', methods=['POST'])
@login_required
def ocr_pdf_info():
    if 'file' not in request.files: return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '': return jsonify({'error': 'No selected file'}), 400
    filename = secure_filename(file.filename)
    ext = os.path.splitext(filename)[1].lower()
    if ext != '.pdf': return jsonify({'error': 'Not a PDF file'}), 400
    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = os.path.join(tmpdir, filename)
        file.save(filepath)
        try:
            from pdf2image import pdfinfo_from_path
            info = pdfinfo_from_path(filepath)
            return jsonify({'success': True, 'pages': int(info.get('Pages', 0))})
        except:
            return jsonify({'error': 'Error leyendo info del PDF'}), 500

@ocr_bp.route('/api/ocr/advanced', methods=['POST'])
@csrf.exempt
@login_required
def ocr_advanced():
    print(f"[OCR] Iniciando petición advanced...", file=sys.stderr)
    ocr_engine = request.form.get('ocr_engine', 'tesseract')
    ocr_model = request.form.get('ocr_model')
    page_number_raw = request.values.get('page_number') or request.form.get('page_number')
    page_number = None
    try:
        if page_number_raw:
            page_number = int(float(page_number_raw))
    except (ValueError, TypeError):
        print(f"[OCR] Error parseando page_number: {page_number_raw}", file=sys.stderr)
    
    print(f"[OCR] Engine: {ocr_engine}, Model: {ocr_model}, Page: {page_number}", file=sys.stderr)
    
    if 'file' not in request.files: return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    filename = secure_filename(file.filename)
    ext = os.path.splitext(filename)[1].lower()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = os.path.join(tmpdir, filename)
        file.save(filepath)
        
        total_pages_detected = 0
        if ext == '.pdf':
            try:
                from pdf2image import pdfinfo_from_path
                total_pages_detected = int(pdfinfo_from_path(filepath).get('Pages', 0))
            except: pass

        img = None
        if ext in ['.jpg', '.jpeg', '.png', '.tiff', '.bmp', '.webp']:
            try:
                img = Image.open(filepath).convert('RGB')
            except: pass

        # Validar page_number contra total_pages_detected
        if page_number and total_pages_detected > 0 and page_number > total_pages_detected:
            return jsonify({
                'error': f'La página {page_number} no existe en este PDF. El documento tiene {total_pages_detected} páginas (1–{total_pages_detected}).'
            }), 400

        # Pre-cargar imágenes si es PDF
        pages_to_process = []
        p_start = 1
        if ext == '.pdf':
            from pdf2image import convert_from_path
            try:
                if page_number:
                    pages_to_process = convert_from_path(filepath, first_page=page_number, last_page=page_number)
                    p_start = page_number
                else:
                    print(f"[OCR] Convirtiendo PDF completo ({total_pages_detected} páginas)...", file=sys.stderr)
                    pages_to_process = convert_from_path(filepath)
                    p_start = 1
            except Exception as e:
                print(f"[OCR ERROR pdf2image] {e}")
                return jsonify({'error': f'Error al convertir PDF a imágenes: {str(e)}'}), 500
        elif img:
            pages_to_process = [img]
            p_start = page_number or 1
        else:
            # Si no es PDF ni se cargó imagen, algo falló
            return jsonify({'error': 'No se pudo cargar la imagen o el PDF'}), 400

        text = ''
        confidence = None
        base64_image = None
        words_data = []
        image_data = None
        all_texts = []
        ocr_skip_ai_correction = False

        try:
            if ocr_engine == 'vision':
                print(f"[OCR] Usando Motor Vision IA (Gemini Native)...", file=sys.stderr)
                provider = 'gemini'
                model_variant = '2.0-flash'
                if ocr_model and ':' in ocr_model:
                    provider = ocr_model.split(':')[0]
                    model_variant = ocr_model.split(':')[1]
                
                ai_service = AIService(provider=provider, model=model_variant, user=current_user)
                for i, page_img in enumerate(pages_to_process):
                    curr_p = p_start + i
                    print(f"[OCR] Procesando página {curr_p} con Vision IA...", file=sys.stderr)
                    # Preparar imagen para Gemini
                    buf = io.BytesIO()
                    page_img.convert('RGB').save(buf, format="JPEG", quality=85)
                    page_base64 = f"data:image/jpeg;base64,{base64.b64encode(buf.getvalue()).decode()}"
                    
                    vision_res = ai_service.vision_ocr(page_base64)
                    words_list = vision_res.get('words', [])
                    
                    page_text = ' '.join([w.get('text', '') for w in words_list])
                    # No añadimos marcadores de página aquí, los añadiremos al final si es necesario
                    # para evitar que limpieza_profunda_ocr los borre prematuramente
                    all_texts.append(page_text)
                    
                    # Convertir coordenadas Gemini [ymin, xmin, ymax, xmax] (0-1000) a formato HesiOX (0-100)
                    for w_item in words_list:
                        box = w_item.get('box_2d', [0,0,0,0])
                        txt = w_item.get('text', '')
                        words_data.append({
                            'text': txt,
                            'word': txt,
                            'x': box[1] / 10.0,
                            'y': box[0] / 10.0,
                            'w': (box[3] - box[1]) / 10.0,
                            'h': (box[2] - box[0]) / 10.0,
                            'bbox': box,
                            'p': curr_p
                        })
                    
                    if i == 0:
                        image_data = page_base64

                if all_texts:
                    # Unimos con separadores temporales únicos
                    text = "\n\n===PAGE_BREAK===\n\n".join(all_texts)
                
                # Fallback de seguridad: Si la IA devolvió muy poco texto, algo fue mal (truncado/bloqueo)
                # Usamos Tesseract como respaldo
                if len(words_data) < 10:
                    print(f"[OCR] ADVERTENCIA: Vision IA devolvió resultados pobres ({len(words_data)} palabras). Usando fallback Tesseract...", file=sys.stderr)
                    # Forzar cambio de motor para el resto de la ejecución de esta función
                    ocr_engine = 'tesseract' 
                else:
                    # Si Vision IA funcionó bien, marcamos para no repetir corrección IA abajo
                    ocr_skip_ai_correction = True

            elif ocr_engine == 'ocrspace':
                import requests
                with open(filepath, 'rb') as f:
                    r = requests.post('https://api.ocr.space/parse/image', files={'file': f}, data={'language': 'spa', 'apikey': 'helloworld'})
                result = r.json()
                parsed = result.get('ParsedResults', [])
                text = '\n\n'.join([res.get('ParsedText', '') for res in parsed])
                if ext in ['.jpg', '.jpeg', '.png']:
                    with open(filepath, "rb") as img_f:
                        base64_image = base64.b64encode(img_f.read()).decode('utf-8')

            if ocr_engine == 'tesseract':
                for i, page_img in enumerate(pages_to_process):
                    curr_p = p_start + i
                    print(f"[OCR] Procesando página {curr_p} (Modo Estable)...", file=sys.stderr)
                    
                    # Usar el preprocesado de alta fidelidad que funcionaba bien
                    img_proc = preprocess_historical_image(page_img)
                    w, h = img_proc.size
                    
                    # Pase único PSM 3 (Layout automático) - EL MEJOR PARA PRESERVAR SALTOS DE LÍNEA
                    page_text = pytesseract.image_to_string(img_proc, config='--psm 3 -l spa')
                    
                    # Obtener coordenadas por separado
                    ocr_result = pytesseract.image_to_data(img_proc, config='--psm 3 -l spa', output_type=pytesseract.Output.DICT)
                    
                    print(f"[OCR] Página {curr_p} finalizada. Caracteres: {len(page_text)}", file=sys.stderr)
                    
                    all_texts.append(page_text)
                    
                    words_data.extend(extract_words_data(ocr_result, w, h, page=curr_p))
                    
                    # Base64 para la primera página o única (usar la ORIGINAL para visualización)
                    if i == 0:
                        buffered = io.BytesIO()
                        # Usar la imagen original convertida a RGB para mejor previsualización
                        page_img.convert('RGB').save(buffered, format="JPEG", quality=85)
                        base64_image = base64.b64encode(buffered.getvalue()).decode('utf-8')
                        image_data = f"data:image/jpeg;base64,{base64_image}"

                if all_texts:
                    text = "\n\n===PAGE_BREAK===\n\n".join(all_texts)

            elif ocr_engine == 'hybrid':
                import requests
                for i, page_img in enumerate(pages_to_process):
                    curr_p = p_start + i
                    print(f"[OCR-Hybrid] --- RECONCILIACIÓN MAESTRA PÁGINA {curr_p} ---", file=sys.stderr)
                    
                    img_rgb = page_img.convert('RGB')
                    width, height = img_rgb.size
                    buf = io.BytesIO()
                    img_rgb.save(buf, format="JPEG", quality=90)
                    img_bytes = buf.getvalue()
                    page_base64 = f"data:image/jpeg;base64,{base64.b64encode(img_bytes).decode()}"
                    
                    if i == 0:
                        image_data = page_base64

                    # 1. PASO 1: OCR.space Engine 2 (Ancla Espacial)
                    space_data = None
                    try:
                        r_space = requests.post('https://api.ocr.space/parse/image', 
                                        files={'file': ('page.jpg', img_bytes, 'image/jpeg')}, 
                                        data={'language': 'spa', 'apikey': 'K81234567888957', 'isOverlayRequired': True, 'OCREngine': '2'},
                                        timeout=45)
                        space_json = r_space.json()
                        if space_json.get('OCRExitCode') == 1:
                            space_data = space_json.get('ParsedResults', [{}])[0].get('TextOverlay', {})
                        else:
                            print(f"[OCR-Hybrid] Advertencia OCR.space: {space_json.get('ErrorMessage')}", file=sys.stderr)
                    except Exception as e_space:
                        print(f"[OCR-Hybrid] Error conectando a OCR.space: {e_space}", file=sys.stderr)

                    # 2. PASO 2: Gemini Reconciliación (Visión + Anchor)
                    try:
                        provider = 'gemini'
                        model_variant = '2.0-flash' # Usar estable
                        curr_ai_service = AIService(provider=provider, model=model_variant, user=current_user)
                        
                        print(f"[OCR-Hybrid] Reconciliando página {curr_p}...", file=sys.stderr)
                        reconciled = curr_ai_service.reconcile_ocr_spatial(page_base64, space_data, width=width, height=height)
                        
                        if reconciled and 'index' in reconciled and reconciled.get('transcription'):
                            all_texts.append(reconciled.get('transcription', ''))
                            for item in reconciled['index']:
                                box = item.get('box', [0,0,0,0])
                                t = item.get('text', '')
                                words_data.append({
                                    'text': t, 'word': t,
                                    'x': box[1] / 10.0, 'y': box[0] / 10.0,
                                    'w': (box[3] - box[1]) / 10.0, 'h': (box[2] - box[0]) / 10.0,
                                    'bbox': box, 'p': curr_p
                                })
                        else:
                            # FALLBACK 1: Vision OCR estándar
                            print(f"[OCR-Hybrid] Reconciliación fallida en pág {curr_p}. Intentando Vision...", file=sys.stderr)
                            v_res = curr_ai_service.vision_ocr(page_base64)
                            v_words = v_res.get('words', [])
                            
                            v_text_final = ' '.join([w.get('text', '') for w in v_words])
                            
                            if v_text_final.strip():
                                all_texts.append(v_text_final)
                                for vw in v_words:
                                    box = vw.get('box_2d', [0,0,0,0])
                                    t = vw.get('text', '')
                                    words_data.append({
                                        'text': t, 'word': t,
                                        'x': box[1] / 10.0, 'y': box[0] / 10.0,
                                        'w': (box[3] - box[1]) / 10.0, 'h': (box[2] - box[0]) / 10.0,
                                        'bbox': box, 'p': curr_p
                                    })
                            else:
                                # FALLBACK 2: Tesseract (EL SALVAVIDAS FINAL)
                                print(f"[OCR-Hybrid] IA falló totalmente (posible bloqueo). Usando Tesseract pág {curr_p}...", file=sys.stderr)
                                img_proc = preprocess_historical_image(page_img)
                                t_text = pytesseract.image_to_string(img_proc, config='--psm 3 -l spa')
                                all_texts.append(t_text)
                                # Extraer coordenadas base de tesseract para no dejar la página vacía de index
                                t_data = pytesseract.image_to_data(img_proc, config='--psm 3 -l spa', output_type=pytesseract.Output.DICT)
                                words_data.extend(extract_words_data(t_data, width, height, page=curr_p))
                                
                    except Exception as e_recon:
                        print(f"[OCR-Hybrid] Error crítico en lógica de página {curr_p}: {e_recon}", file=sys.stderr)
                        # Fallback de emergencia absoluto
                        all_texts.append("[ERROR EN PROCESAMIENTO DE PÁGINA]")

                text = "\n\n===PAGE_BREAK===\n\n".join(all_texts)
                confidence = 100
                ocr_skip_ai_correction = True

            elif ocr_engine == 'expert':
                # =============================================
                # MOTOR EXPERTO: PIPELINE DE 3 PASOS
                # Paso 1: Tesseract multi-PSM (borrador + coords)
                # Paso 2: Gemini Vision con contexto Tesseract
                # Paso 3: Gemini refinamiento final del texto
                # =============================================
                print(f"[OCR-Expert] === MODO EXPERTO 3 PASOS iniciado ===", file=sys.stderr)

                provider = 'gemini'
                model_variant = '2.0-flash'
                if ocr_model and ':' in ocr_model:
                    provider = ocr_model.split(':')[0]
                    model_variant = ocr_model.split(':')[1]

                expert_ai = AIService(provider=provider, model=model_variant, user=current_user)

                # Re-convertir PDF a alta resolución (400 DPI) para mejor calidad de imagen
                pages_hires = pages_to_process
                if ext == '.pdf':
                    try:
                        from pdf2image import convert_from_path as cfp_hires
                        print(f"[OCR-Expert] Re-convirtiendo PDF a 400 DPI...", file=sys.stderr)
                        if page_number:
                            pages_hires = cfp_hires(filepath, dpi=400, first_page=page_number, last_page=page_number)
                        else:
                            pages_hires = cfp_hires(filepath, dpi=400)
                        print(f"[OCR-Expert] {len(pages_hires)} páginas a 400 DPI listas.", file=sys.stderr)
                    except Exception as e_dpi:
                        print(f"[OCR-Expert] Error a 400 DPI: {e_dpi}. Usando resolución estándar.", file=sys.stderr)

                for i, page_img in enumerate(pages_hires):
                    curr_p = p_start + i
                    print(f"[OCR-Expert] --- Procesando página {curr_p} ---", file=sys.stderr)

                    img_rgb = page_img.convert('RGB')
                    width, height = img_rgb.size

                    # Preparar imagen base64 para Gemini (calidad alta)
                    buf = io.BytesIO()
                    img_rgb.save(buf, format="JPEG", quality=92)
                    img_bytes = buf.getvalue()
                    page_base64 = f"data:image/jpeg;base64,{base64.b64encode(img_bytes).decode()}"

                    if i == 0:
                        image_data = page_base64

                    # --- PASO 1: Tesseract multi-PSM ---
                    print(f"[OCR-Expert] Paso 1 - Tesseract multi-PSM página {curr_p}...", file=sys.stderr)
                    img_proc = preprocess_historical_image(page_img)

                    # PSM 3: layout automático (mejor para docs con decoración y columnas)
                    text_psm3 = pytesseract.image_to_string(img_proc, config='--psm 3 -l spa')
                    # PSM 6: bloque de texto uniforme (mejor cobertura en texto corrido)
                    text_psm6 = pytesseract.image_to_string(img_proc, config='--psm 6 -l spa')
                    # Usar el que más texto extrae como borrador
                    tess_draft = text_psm3 if len(text_psm3) >= len(text_psm6) else text_psm6
                    print(f"[OCR-Expert] Tesseract: PSM3={len(text_psm3)}ch PSM6={len(text_psm6)}ch -> draft={len(tess_draft)}ch", file=sys.stderr)

                    # Guardar coordenadas del PSM3 (mejor layout awareness)
                    ocr_result = pytesseract.image_to_data(img_proc, config='--psm 3 -l spa', output_type=pytesseract.Output.DICT)
                    words_data.extend(extract_words_data(ocr_result, width, height, page=curr_p))

                    # --- PASO 2: Gemini Vision con borrador Tesseract como contexto ---
                    print(f"[OCR-Expert] Paso 2 - Gemini Vision expert página {curr_p}...", file=sys.stderr)
                    vision_result = expert_ai.vision_ocr_expert(page_base64, tess_draft)

                    page_text = vision_result.get('text', tess_draft)
                    refined_words = vision_result.get('words', [])

                    # Actualizar coordenadas con las de Gemini si las devolvió
                    if refined_words:
                        words_data = [w for w in words_data if w.get('p') != curr_p]
                        for w_item in refined_words:
                            box = w_item.get('box_2d', [0, 0, 0, 0])
                            txt = w_item.get('text', '')
                            words_data.append({
                                'text': txt, 'word': txt,
                                'x': box[1] / 10.0, 'y': box[0] / 10.0,
                                'w': (box[3] - box[1]) / 10.0, 'h': (box[2] - box[0]) / 10.0,
                                'bbox': box, 'p': curr_p
                            })

                    all_texts.append(page_text)
                    print(f"[OCR-Expert] Página {curr_p} Paso 2 OK: {len(page_text)} chars.", file=sys.stderr)

                text = "\n\n===PAGE_BREAK===\n\n".join(all_texts)

                # --- PASO 3: Gemini refinamiento final del texto completo ---
                print(f"[OCR-Expert] Paso 3 - Refinamiento final del documento ({len(text)} chars)...", file=sys.stderr)
                try:
                    final_result = expert_ai.correct_ocr_text(text, image_data=image_data)
                    if final_result and final_result.get('corrected_text'):
                        text = final_result['corrected_text']
                        print(f"[OCR-Expert] Paso 3 OK. Texto final: {len(text)} chars.", file=sys.stderr)
                    else:
                        print(f"[OCR-Expert] Paso 3 sin resultado, manteniendo texto del Paso 2.", file=sys.stderr)
                except Exception as e_p3:
                    print(f"[OCR-Expert] Error en Paso 3: {e_p3}. Manteniendo texto del Paso 2.", file=sys.stderr)

                confidence = 97
                ocr_skip_ai_correction = True

        except Exception as e:
            print(f'[OCR ERROR Engine] {e}')
            import traceback
            traceback.print_exc()
            return jsonify({'error': f'Error en el motor OCR: {str(e)}'}), 500

        # AI Service correction (Optional step)
        if not ocr_skip_ai_correction:
            try:
                # [NUEVO] En modo híbrido NO limpiamos antes para no perder las etiquetas [BORRADOR BASE]
                if ocr_engine != 'hybrid':
                    text = limpieza_profunda_ocr(text)
                
                print(f"[OCR] Iniciando corrección IA con modelo: {ocr_model or 'default'}...", file=sys.stderr)
                provider = 'gemini'
                model_variant = ocr_model
                if ocr_model and ':' in ocr_model:
                    parts = ocr_model.split(':', 1)
                    provider = parts[0]
                    model_variant = parts[1]
                
                ai_service = AIService(provider=provider, model=model_variant, user=current_user)
                if ai_service.is_configured() and text:
                    # Preparar image_data si no existe
                    if not image_data:
                        try:
                            # Usar la primera imagen del set para el refinamiento
                            if pages_to_process:
                                buf = io.BytesIO()
                                pages_to_process[0].convert('RGB').save(buf, format="JPEG", quality=85)
                                image_data = f"data:image/jpeg;base64,{base64.b64encode(buf.getvalue()).decode()}"
                        except Exception as ve:
                            print(f"[OCR] No se pudo generar preview para IA: {ve}", file=sys.stderr)
                    
                    # PROMPT UNIVERSAL PARA REFINAMIENTO DE OCR (MÁXIMA CALIDAD)
                    prompt = f"""
ACTÚA COMO UN EXPERTO EN PROCESAMIENTO DE DOCUMENTOS Y RECONSTRUCCIÓN TEXTUAL DE ALTA FIDELIDAD.
Tu misión es depurar este OCR para generar una transcripción perfecta y coherente del documento original.

INSTRUCCIONES DE PROCESAMIENTO:
1. LIMPIEZA DE METADATOS: Elimina elementos ajenos al cuerpo del texto como números de página, encabezados repetitivos, pies de página, marcas de escaneo o ruido marginal.
2. DEDUPLICACIÓN Y RECONCILIACIÓN: El texto puede contener fragmentos repetidos o versiones alternativas del mismo párrafo ([BORRADOR BASE] vs [TRANSCRIPCIÓN LIMPIA]). Reintégralos en un flujo narrativo único y lógico, eliminando las repeticiones y errores de lectura.
3. RECONSTRUCCIÓN DE ESTRUCTURA: Une palabras divididas por guiones al final de línea y restaura los párrafos originales. Asegura que el texto fluya de manera natural sin interrupciones técnicas.
4. INTEGRIDAD TEXTUAL: No resumas ni cambies el contenido. Usa la imagen proporcionada (si existe) para resolver dudas de lectura, pero cíñete estrictamente a lo que dice el documento.
5. PRESERVACIÓN DE ESTILO: Mantén escrupulosamente el idioma, la ortografía y el estilo original del texto (ya sea técnico, legal, histórico o literario). No modernices el lenguaje.

FORMATO DE SALIDA: Devuelve ÚNICAMENTE el texto limpio y estructurado. Sin comentarios, sin etiquetas de sistema y sin explicaciones adicionales.
"""
                    # Forzar el uso del prompt si el motor es híbrido
                    if ocr_engine == 'hybrid' or request.form.get('reconcile_hybrid') == 'true':
                        print(f"[OCR] Aplicando prompt de reconciliación híbrida.", file=sys.stderr)
                    else:
                        prompt = None
                    
                    ai_res = ai_service.correct_ocr_text(text, image_data=image_data, custom_prompt=prompt)
                    if ai_res and ai_res.get('corrected_text'):
                        print(f"[OCR] Corrección IA completada con éxito.", file=sys.stderr)
                        text = ai_res['corrected_text']
                    else:
                        print(f"[OCR] La corrección IA no devolvió resultados: {ai_service.last_error}", file=sys.stderr)
            except Exception as e_ai:
                print(f'[OCR ERROR IA] {e_ai}', file=sys.stderr)
                # No fallamos la petición completa si falla la IA

        # NLP (Optional step)
        entities = []
        try:
            print(f"[OCR] Extrayendo entidades NLP...", file=sys.stderr)
            nlp = get_nlp()
            if nlp and text:
                # Limitar texto para Spacy para evitar cuelgues
                doc = nlp(text[:100000]) 
                entities = [{'text': ent.text, 'label': ent.label_} for ent in doc.ents]
                print(f"[OCR] NLP completado: {len(entities)} entidades.", file=sys.stderr)
        except Exception as e_nlp:
            print(f'[OCR ERROR NLP] {e_nlp}', file=sys.stderr)

        # Re-insertar marcadores de página si venían de un PDF multipágina
        # y no están presentes en el texto (fueron limpiados por la IA)
        if len(pages_to_process) > 1 and "--- [PÁGINA" not in text:
            # Si el texto es una sola masa, no podemos re-insertarlos fácilmente
            # pero al menos aseguramos que limpieza_profunda no vea un bloque gigante duplicado
            pass

        print(f"[OCR] Petición finalizada con éxito. Longitud texto: {len(text)}", file=sys.stderr)
        
        # Limpieza final profunda para eliminar cualquier eco que la IA haya dejado
        final_text = limpieza_profunda_ocr(text)
        
        return jsonify({
            'text': final_text,
            'confidence': confidence,
            'entities': entities,
            'words_data': words_data,
            'image_data': image_data,
            'total_pages': total_pages_detected or 1
        })

@ocr_bp.route('/api/ocr/corregir', methods=['POST'])
@csrf.exempt
@login_required
def ocr_corregir():
    try:
        data = request.get_json()
        ai_service = AIService(user=current_user)
        if ai_service.is_configured() and data.get('texto'):
            # Prompt de refuerzo para evitar duplicados en el refinamiento global
            prompt = """
ACTÚA COMO UN EDITOR FINAL. 
Recibirás el texto completo de un documento OCR.
Tu tarea es:
1. Eliminar repeticiones accidentales de párrafos o secciones.
2. Corregir la continuidad entre páginas.
3. NO añadidas comentarios personales.
4. MANTÉN el texto íntegro pero sin duplicados.
"""
            res = ai_service.correct_ocr_text(data['texto'], image_data=data.get('image_data'), custom_prompt=prompt)
            if res and res.get('corrected_text'):
                # Aplicamos limpieza profunda al resultado de la IA para asegurar eliminación de ecos
                clean_text = limpieza_profunda_ocr(res['corrected_text'])
                return jsonify({
                    'success': True, 
                    'corrected_text': clean_text, 
                    'metadatos': {**data.get('metadatos', {}), **res.get('metadata', {})}
                })
        return jsonify({'success': True, 'corrected_text': limpieza_profunda_ocr(data.get('texto', '')), 'metadatos': data.get('metadatos', {})})
    except Exception as e:
        print(f"[OCR] Error en corregir: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
