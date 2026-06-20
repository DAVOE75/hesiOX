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
    """ Extrae datos de palabras y coordenadas normalizadas (0-1000) """
    words_data = []
    if not ocr_result or 'level' not in ocr_result:
        return []
    for i in range(len(ocr_result['text'])):
        # Nivel 5 son palabras en Pytesseract
        if int(ocr_result['level'][i]) == 5 and ocr_result['text'][i].strip():
            ymin = int((ocr_result['top'][i] / height) * 1000)
            xmin = int((ocr_result['left'][i] / width) * 1000)
            ymax = int(((ocr_result['top'][i] + ocr_result['height'][i]) / height) * 1000)
            xmax = int(((ocr_result['left'][i] + ocr_result['width'][i]) / width) * 1000)
            words_data.append({
                'word': ocr_result['text'][i],
                'confidence': int(ocr_result['conf'][i]),
                'bbox': [ymin, xmin, ymax, xmax],
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
                    # Preparar imagen para Gemini
                    buf = io.BytesIO()
                    page_img.convert('RGB').save(buf, format="JPEG", quality=85)
                    page_base64 = f"data:image/jpeg;base64,{base64.b64encode(buf.getvalue()).decode()}"
                    
                    vision_res = ai_service.vision_ocr(page_base64)
                    words_list = vision_res.get('words', [])
                    
                    page_text = ' '.join([w.get('text', '') for w in words_list])
                    if len(pages_to_process) > 1:
                        all_texts.append(f"--- [PÁGINA {curr_p}] ---\n{page_text}")
                    else:
                        text = page_text
                    
                    # Convertir coordenadas Gemini [ymin, xmin, ymax, xmax] (0-1000) a formato HesiOX (0-100)
                    for w_item in words_list:
                        box = w_item.get('box_2d', [0,0,0,0])
                        words_data.append({
                            'text': w_item.get('text', ''),
                            'x': box[1] / 10.0,
                            'y': box[0] / 10.0,
                            'w': (box[3] - box[1]) / 10.0,
                            'h': (box[2] - box[0]) / 10.0,
                            'p': curr_p
                        })
                    
                    if i == 0:
                        image_data = page_base64

                if all_texts:
                    text = '\n\n'.join(all_texts)
                
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
                    
                    # Pase único PSM 3 (Layout automático) - El más estable para periódicos
                    ocr_result = pytesseract.image_to_data(img_proc, config='--psm 3 -l spa', output_type=pytesseract.Output.DICT)
                    
                    # Extraer texto limpio
                    page_text = ' '.join([t for t in ocr_result['text'] if t.strip()])
                    
                    print(f"[OCR] Página {curr_p} finalizada. Caracteres: {len(page_text)}", file=sys.stderr)
                    
                    if len(pages_to_process) > 1:
                        all_texts.append(f"--- [PÁGINA {curr_p}] ---\n{page_text}")
                    else:
                        text = page_text
                    
                    words_data.extend(extract_words_data(ocr_result, w, h, page=curr_p))
                    
                    # Base64 para la primera página o única (usar la ORIGINAL para visualización)
                    if i == 0:
                        buffered = io.BytesIO()
                        # Usar la imagen original convertida a RGB para mejor previsualización
                        page_img.convert('RGB').save(buffered, format="JPEG", quality=85)
                        base64_image = base64.b64encode(buffered.getvalue()).decode('utf-8')
                        image_data = f"data:image/jpeg;base64,{base64_image}"

                if all_texts:
                    text = '\n\n'.join(all_texts)

            elif ocr_engine == 'hybrid':
                for i, page_img in enumerate(pages_to_process):
                    curr_p = p_start + i
                    print(f"[OCR-Hybrid-V3] Procesando página {curr_p}...", file=sys.stderr)
                    
                    # 1. Preprocesado suave (Sharpening)
                    img_restored = preprocess_historical_image(page_img)
                    img_rgb = page_img.convert('RGB')
                    width, height = img_restored.size
                    
                    # 2. DOBLE PASADA TESSERACT
                    # Pass 1: PSM 3 (Cuerpo)
                    res1 = pytesseract.image_to_data(img_restored, config='--psm 3 -l spa', output_type=pytesseract.Output.DICT)
                    txt1 = ' '.join([t for t in res1['text'] if t.strip()])
                    
                    # Pass 2: PSM 6 (Cabeceras)
                    res2 = pytesseract.image_to_data(img_restored, config='--psm 6 -l spa', output_type=pytesseract.Output.DICT)
                    txt2 = ' '.join([t for t in res2['text'] if t.strip()])
                    
                    # 3. Borrador para IA (Más limpio)
                    page_combined = f"--- [PÁGINA {curr_p}] ---\n\n[BORRADOR BASE]\n{txt1}\n\n[DATOS CABECERA]\n{txt2}"
                    all_texts.append(page_combined)
                    
                    # 4. Fusión de Spatial Index
                    words_v1 = extract_words_data(res1, width, height, page=curr_p)
                    words_v2 = extract_words_data(res2, width, height, page=curr_p)
                    words_data.extend(words_v1)
                    words_data.extend([w for w in words_v2 if w['confidence'] > 50])
                    
                    if i == 0:
                        buf = io.BytesIO()
                        img_rgb.save(buf, format="JPEG", quality=90)
                        image_data = f"data:image/jpeg;base64,{base64.b64encode(buf.getvalue()).decode()}"

                text = '\n\n'.join(all_texts)
                confidence = 92
                ocr_skip_ai_correction = False

        except Exception as e:
            print(f'[OCR ERROR Engine] {e}')
            import traceback
            traceback.print_exc()
            return jsonify({'error': f'Error en el motor OCR: {str(e)}'}), 500

        # AI Service correction (Optional step)
        if not ocr_skip_ai_correction:
            try:
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
                            with Image.open(filepath) as v_img:
                                if v_img.mode != 'RGB': v_img = v_img.convert('RGB')
                                v_img.thumbnail((2000, 2000))
                                buf = io.BytesIO()
                                v_img.save(buf, format="JPEG", quality=85)
                                image_data = f"data:image/jpeg;base64,{base64.b64encode(buf.getvalue()).decode()}"
                        except Exception as ve:
                            print(f"[OCR] No se pudo generar preview para IA: {ve}", file=sys.stderr)
                    
                    prompt = None
                    if request.form.get('reconcile_hybrid') == 'true':
                        prompt = "Actúa como un experto paleógrafo. Compara y reconcilia estos borradores de OCR usando la imagen adjunta."
                    
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

        print(f"[OCR] Petición finalizada con éxito. Longitud texto: {len(text)}", file=sys.stderr)
        return jsonify({
            'text': limpieza_profunda_ocr(text),
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
            res = ai_service.correct_ocr_text(data['texto'], image_data=data.get('image_data'))
            if res:
                return jsonify({'success': True, 'corrected_text': res.get('corrected_text'), 'metadatos': {**data.get('metadatos', {}), **res.get('metadata', {})}})
        return jsonify({'success': True, 'corrected_text': data.get('texto'), 'metadatos': data.get('metadatos', {})})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
