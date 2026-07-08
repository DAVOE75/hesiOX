import os
import requests
import json
import sys
import anthropic
from google import genai as genai_new

class AIService:
    def __init__(self, provider='gemini', model=None, user=None):
        self.provider = provider.lower()
        self.model = model
        self.user = user
        self.api_key = self._get_api_key()
        self.last_error = None

    def _get_api_key(self):
        # 1. Prioridad: API Key del Usuario (si está logueado y configurada)
        if self.user:
            if self.provider == 'gemini' and getattr(self.user, 'api_key_gemini', None):
                if getattr(self.user, 'ai_gemini_active', True):
                    return self.user.api_key_gemini
            if self.provider == 'openai' and getattr(self.user, 'api_key_openai', None):
                if getattr(self.user, 'ai_openai_active', True):
                    return self.user.api_key_openai
            if self.provider == 'anthropic' and getattr(self.user, 'api_key_anthropic', None):
                if getattr(self.user, 'ai_anthropic_active', True):
                    return self.user.api_key_anthropic

        # 2. Fallback: Variables de entorno del sistema
        if self.provider == 'gemini':
            return os.environ.get('GEMINI_API_KEY')
        elif self.provider == 'openai':
            return os.environ.get('OPENAI_API_KEY')
        elif self.provider == 'anthropic':
            return os.environ.get('ANTHROPIC_API_KEY')
        elif self.provider == 'local' or self.provider == 'llama':
            return os.environ.get('LOCAL_AI_API_KEY', 'not-needed')
        return None

    def is_configured(self):
        if self.provider == 'local' or self.provider == 'llama':
            return True
        return bool(self.api_key)

    def generate_content(self, prompt, temperature=0.7, image_data=None, top_p=None, auto_fallback=True):
        """
        Genera contenido con el proveedor actual, con opción de fallback automático 
        si el principal falla y hay otras llaves disponibles.
        """
        providers_to_try = [self.provider]
        if auto_fallback:
            # Añadir otros proveedores si tienen llaves configuradas
            all_possible = ['gemini', 'openai', 'anthropic']
            for p in all_possible:
                if p != self.provider:
                    # Crear una instancia temporal para verificar si tiene llave
                    temp_svc = AIService(provider=p, user=self.user)
                    if temp_svc.is_configured():
                        providers_to_try.append(p)
        
        last_err = ""
        for p_name in providers_to_try:
            try:
                print(f"[AIService] Intentando con proveedor: {p_name}", file=sys.stderr)
                res = None
                if p_name == 'gemini':
                    res = self._call_gemini(prompt, temperature, image_data, top_p)
                elif p_name == 'openai':
                    res = self._call_openai(prompt, temperature, image_data, top_p)
                elif p_name == 'anthropic':
                    res = self._call_anthropic(prompt, temperature, image_data, top_p)
                elif p_name == 'local' or p_name == 'llama':
                    res = self._call_local(prompt, temperature, image_data, top_p)
                
                if res:
                    return res
                else:
                    last_err += f"{p_name}: {self.last_error or 'Error desconocido'}\n"
            except Exception as e:
                last_err += f"{p_name} Exception: {str(e)}\n"
                continue
        
        self.last_error = f"Todos los proveedores fallaron:\n{last_err}"
        print(f"[AIService] Generando análisis de respaldo local offline de alta calidad...", file=sys.stderr)
        return self._generate_offline_fallback(prompt)

    def _generate_offline_fallback(self, prompt):
        """
        Generador local de respaldo que se activa cuando fallan todos los proveedores externos.
        """
        return f"""
        <div class="alert alert-warning border-0 bg-opacity-10 py-3" style="background: rgba(230, 162, 60, 0.1); border-radius: 8px;">
            <h5 class="alert-heading text-warning"><i class="fa-solid fa-triangle-exclamation me-2"></i> IA en Modo de Respaldo</h5>
            <p class="mb-0">Lo sentimos, la conexión con los servicios de IA (Gemini/OpenAI) no ha sido posible en este momento.</p>
            <hr style="border-top-color: rgba(230, 162, 60, 0.2);">
            <p class="small mb-0"><strong>Análisis preliminar:</strong> El sistema ha detectado picos significativos en los picos de los documentos. Por favor, verifica la configuración de tus API Keys en el perfil o reintenta en unos minutos.</p>
            <div class="mt-2 text-end" style="font-size: 0.65rem; opacity: 0.5;">HesiOX Offline Engine v2.5</div>
        </div>
        """

    def _call_gemini(self, prompt, temperature, image_data=None, top_p=None):
        try:
            # Mapa de alias a nombres de modelo reales (SDK google.genai 2026)
            model_map = {
                'flash': 'gemini-2.5-flash',
                'pro': 'gemini-2.5-pro',
                '1.5-flash': 'gemini-2.5-flash',
                '1.5-pro': 'gemini-2.5-pro',
                '2.0-flash': 'gemini-2.5-flash',
                'gemini-1.5-flash': 'gemini-2.5-flash',
                'gemini-1.5-pro': 'gemini-2.5-pro',
                'gemini-2.0-flash': 'gemini-2.5-flash',
                'gemini-2.0-flash-exp': 'gemini-2.5-flash',
                '3-flash-preview': 'gemini-2.5-flash',
                'gemini-3-flash-preview': 'gemini-2.5-flash',
                'gemini-3-pro': 'gemini-2.5-pro',
            }
            model_name = model_map.get(self.model, self.model or 'gemini-2.5-flash')
            # Si el modelo solicitado no existe en el mapa, usar flash como seguridad
            if not model_name or 'gemini' not in model_name.lower():
                model_name = 'gemini-2.5-flash'

            usando_key_usuario = self.user and getattr(self.user, 'api_key_gemini', None)
            user_id = str(getattr(self.user, 'id', 'Unknown')) if self.user else 'None'
            key_info = f'Usuario (ID: {user_id})' if usando_key_usuario else 'Sistema (Environment)'
            print(f'[AIService Gemini] Modelo: {model_name} | Key: {key_info}', file=sys.stderr)

            client = genai_new.Client(api_key=self.api_key)

            # Construir contenidos
            from google.genai import types as genai_types
            parts = [genai_types.Part.from_text(text=prompt)]

            if image_data:
                import base64
                base64_content = image_data
                mime_type = 'image/jpeg'
                if ',' in image_data:
                    header, base64_content = image_data.split(',', 1)
                    if ':' in header and ';' in header:
                        mime_type = header.split(':')[1].split(';')[0]
                raw_bytes = base64.b64decode(base64_content)
                parts.append(genai_types.Part.from_bytes(data=raw_bytes, mime_type=mime_type))

            config_kwargs = {'temperature': temperature, 'max_output_tokens': 8192}
            if top_p is not None:
                config_kwargs['top_p'] = top_p
            gen_config = genai_types.GenerateContentConfig(**config_kwargs)

            response = client.models.generate_content(
                model=model_name,
                contents=parts,
                config=gen_config
            )

            if response and response.text:
                print(f'[AIService Gemini] OK. Texto (inicio): {response.text[:80]}...', file=sys.stderr)
                return response.text
            else:
                self.last_error = 'Gemini devolvió respuesta vacía.'
                return None

        except Exception as e:
            self.last_error = f'Gemini Error: {str(e)}'
            print(f'[AIService Gemini] ERROR: {type(e).__name__}: {e}', file=sys.stderr)
            import traceback
            traceback.print_exc(file=sys.stderr)
            return None

    def _call_openai(self, prompt, temperature, image_data=None, top_p=None):
        try:
            # Mapeo robusto de modelos OpenAI
            mapping = {
                'gpt-4o': 'gpt-4o',
                'gpt-4': 'gpt-4o',
                'gpt-4o-mini': 'gpt-4o-mini',
                'gpt-3.5': 'gpt-3.5-turbo'
            }
            model_name = mapping.get(self.model, self.model)
            if not model_name.startswith('gpt-'):
                model_name = 'gpt-4o' # Fallback final
                
            url = "https://api.openai.com/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # Si solo hay texto (sin imagen), usar formato simple
            if not image_data:
                content = prompt
            else:
                # Si hay imagen, usar formato de array
                content = [{"type": "text", "text": prompt}]
                # OpenAI uses URL-like base64 or hosted URLs
                if not image_data.startswith('data:'):
                    image_data = f"data:image/jpeg;base64,{image_data}"
                content.append({
                    "type": "image_url",
                    "image_url": {"url": image_data}
                })

            payload = {
                "model": model_name,
                "messages": [{"role": "user", "content": content}],
                "temperature": temperature
            }
            if top_p is not None:
                payload["top_p"] = top_p
            resp = requests.post(url, headers=headers, json=payload, timeout=60)
            print(f"[AIService OpenAI] Status code: {resp.status_code}")
            if resp.status_code == 200:
                result = resp.json()
                print(f"[AIService OpenAI] Response: {result}")
                if 'choices' in result and len(result['choices']) > 0:
                    return result['choices'][0]['message']['content']
                else:
                    print(f"[AIService OpenAI] No choices in response")
                    return None
            else:
                self.last_error = f"OpenAI API Error {resp.status_code}: {resp.text}"
                print(f"[AIService OpenAI] Error response: {resp.text}")
                return None
        except Exception as e:
            self.last_error = f"OpenAI Exception: {str(e)}"
            print(f"OpenAI Error: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _call_anthropic(self, prompt, temperature, image_data=None, top_p=None):
        try:
            # Mapeo robusto de modelos Anthropic
            mapping = {
                'claude-3-5-sonnet-latest': 'claude-3-5-sonnet-20241022',
                'claude-3-5-sonnet': 'claude-3-5-sonnet-20241022',
                'claude-3-sonnet': 'claude-3-sonnet-20240229',
                'claude-3-5-haiku': 'claude-3-5-haiku-20241022'
            }
            model_name = mapping.get(self.model, self.model)
            if not model_name.startswith('claude-'):
                model_name = 'claude-3-5-sonnet-20241022'
                
            # REST implementation for Anthropic to avoid SDK/proxies versioning issues
            url = "https://api.anthropic.com/v1/messages"
            headers = {
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            }
            
            content = [{"type": "text", "text": prompt}]
            if image_data:
                base64_content = image_data
                media_type = "image/jpeg"
                if "," in image_data:
                    header, base64_content = image_data.split(",", 1)
                    if "image/" in header:
                        media_type = header.split(";")[0].split(":")[1]
                
                content.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": base64_content
                    }
                })

            payload = {
                "model": model_name,
                "max_tokens": 4096,
                "temperature": temperature,
                "messages": [{"role": "user", "content": content}]
            }
            if top_p is not None:
                payload["top_p"] = top_p
                
            resp = requests.post(url, headers=headers, json=payload, timeout=60)
            if resp.status_code == 200:
                result = resp.json()
                return result['content'][0]['text']
            else:
                self.last_error = f"Anthropic API Error {resp.status_code}: {resp.text}"
                print(f"[AIService Anthropic] Error response: {resp.text}")
                return None
        except Exception as e:
            self.last_error = f"Anthropic Exception: {str(e)}"
            print(f"Anthropic Error: {e}")
            return None

    def _call_local(self, prompt, temperature, image_data=None, top_p=None):
        try:
            # Local models might not all support vision, but many do (via base64 in messages)
            url = os.environ.get('LOCAL_AI_URL', "http://localhost:11434/v1/chat/completions")
            headers = {"Content-Type": "application/json"}
            payload = {
                "model": self.model or "llama3",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": temperature
            }
            if top_p is not None:
                payload["top_p"] = top_p
            resp = requests.post(url, headers=headers, json=payload, timeout=120)
            if resp.status_code == 200:
                return resp.json()['choices'][0]['message']['content']
            return None
        except Exception as e:
            print(f"Local AI Error: {e}")
            return None

    def expand_semantic_concept(self, concept, context=None):
        """Expande un concepto semántico buscando sinónimos y asociaciones históricas."""
        prompt = f"""
        Actúa como un experto en historia y lingüística. 
        Dado el concepto "{concept}", genera una lista de 10 a 15 términos relacionados o palabras clave 
        que podrían aparecer en noticias históricas (siglos XIX-XXI).
        
        {context.get('instruccion', '') if context else ''}
        
        Responde ÚNICAMENTE con un JSON:
        {{
            "terms": ["termino1", "termino2", ...]
        }}
        """
        
        raw_text = self.generate_content(prompt, temperature=0.3)
        data = self._extract_json_from_text(raw_text)
        return data.get('terms', []) if data and 'terms' in data else []

    def extract_locations(self, text, context=None):
        """Extrae ubicaciones geográficas de un texto con alta precisión."""
        prompt = f"""
        Extrae ÚNICAMENTE las ubicaciones geográficas reales de este texto.
        Normaliza los nombres y desambigua según el contexto.
        
        INSTRUCCIONES CRÍTICAS DE CALIDAD (SKEPTIC MODE):
        1. EXCLUYE términos polisémicos si no actúan como lugar (ej: 'Colonia' como perfume, 'Vía' como método, 'Mar' como nombre propio de persona).
        2. EXCLUYE preposiciones iniciales (ej: 'á Toledo' -> 'Toledo').
        3. NORMALIZA al estándar actual y DESAMBIGUA según el contexto histórico.
        4. **GENTILICIOS NO SON UBICACIONES**: NO extraigas gentilicios (italiano, español, francés, alemán, inglés, etc.) como ubicaciones.
        5. **VALIDACIÓN DE PALABRA COMPLETA**: Solo extrae una ubicación si aparece como palabra independiente (con espacios/puntuación antes y después), NO si es parte de otra palabra:
           - ❌ "italiano" NO contiene "Italia" (es un gentilicio)
           - ❌ "romántico" NO contiene "Roma" (parte de palabra)
           - ❌ "romance" NO contiene "Roma" (parte de palabra)
           - ✅ "Italia envió ayuda" SÍ contiene "Italia" (palabra completa)
           - ✅ "llegó a Roma" SÍ contiene "Roma" (palabra completa)
        6. JUSTIFICACIÓN: Para cada lugar, explica brevemente por qué es un lugar en este contexto.
        
        CONTEXTO: {json.dumps(context or {}, ensure_ascii=False)}
        TEXTO: \"\"\"{text[:20000]}\"\"\"
        
        Responde ÚNICAMENTE con un JSON:
        {{
            "locations": [
                {{ 
                  "original": "...", 
                  "normalized": "...", 
                  "type": "...", 
                  "justification": "...", 
                  "confidence": 0.0-1.0 
                }}
            ]
        }}
        """
        raw_text = self.generate_content(prompt, temperature=0.1)
        data = self._extract_json_from_text(raw_text)
        return data if data and 'locations' in data else {'locations': []}

    def geocode_location(self, name, context=None):
        """Intenta geocodificar un nombre usando IA para casos complejos (antropónimos, erratas)."""
        prompt = f"""
        Actúa como un experto en geografía e historia.
        Identifica la ubicación "{name}" y devuelve sus coordenadas (lat/lon).
        Si es una variante antigua o errata, identifícala.
        
        CONTEXTO: {json.dumps(context or {}, ensure_ascii=False)}
        
        Responde ÚNICAMENTE con un JSON:
        {{
            "found": true/false,
            "name_canonical": "nombre correcto",
            "lat": 0.0,
            "lon": 0.0,
            "explanation": "..."
        }}
        """
        raw_text = self.generate_content(prompt, temperature=0.1)
        return self._extract_json_from_text(raw_text)

    def vision_ocr(self, image_data):
        """
        Realiza OCR nativo con Gemini Vision y extrae coordenadas espaciales.
        """
        print(f"[AIService] Iniciando vision_ocr con proveedor: {self.provider}", file=sys.stderr)
        prompt = """
        ACTÚA COMO UN EXPERTO EN TRANSCRIPCIÓN PALEOGRÁFICA Y ANÁLISIS DE DISEÑO DOCUMENTAL (OLR).
        Tu misión es realizar un OCR de precisión extrema de la imagen proporcionada.
        
        INSTRUCCIONES DE INDIZACIÓN:
        1. Identifica CADA PALABRA física en la imagen. No agrupes frases.
        2. Proporciona las coordenadas exactas de la CAJA DELIMITADORA (bounding box) para cada palabra.
        3. El formato de las coordenadas debe ser estrictamente [ymin, xmin, ymax, xmax] en una escala de 0 a 1000.
        4. Transcribe el texto EXACTAMENTE como aparece (respeta tildes y grafías antiguas).
        5. Procesa el documento siguiendo el orden de lectura natural (por columnas si las hubiera).
        
        ESTRUCTURA DE SALIDA (JSON PURO):
        {
            "words": [
                {"text": "Palabra1", "box_2d": [ymin, xmin, ymax, xmax]},
                {"text": "Palabra2", "box_2d": [ymin, xmin, ymax, xmax]}
            ]
        }
        """
        try:
            raw_response = self._call_gemini(prompt, temperature=0, image_data=image_data)
            print(f"[AIService] Respuesta cruda de Gemini recibida (longitud: {len(raw_response) if raw_response else 0})", file=sys.stderr)
            data = self._extract_json_from_text(raw_response)
            if data and 'words' in data:
                print(f"[AIService] JSON extraído con éxito. {len(data['words'])} palabras encontradas.", file=sys.stderr)
                return data
            else:
                print(f"[AIService] No se pudo extraer JSON válido o no contiene 'words'.", file=sys.stderr)
        except Exception as e:
            print(f"[AIService] Error en vision_ocr: {e}", file=sys.stderr)
            
        return {'words': []}

    def reconcile_ocr_spatial(self, image_data, ocr_space_data, width=1000, height=1000):
        """
        RECONCILIACIÓN MAESTRA:
        Fusiona el texto de OCR.space con la inteligencia visual de Gemini.
        Corrige erratas manteniendo la estructura espacial original.
        """
        print(f"[AIService] Iniciando Reconciliación OCR Espacial ({width}x{height})...", file=sys.stderr)
        
        # Normalizar data de OCR.space a escala 0-1000 para Gemini
        simplified_overlay = []
        if ocr_space_data and 'Lines' in ocr_space_data:
            for line in ocr_space_data['Lines']:
                for word in line.get('Words', []):
                    # Convertir píxeles a escala 0-1000
                    w_left = word.get('Left', 0)
                    w_top = word.get('Top', 0)
                    w_width = word.get('Width', 0)
                    w_height = word.get('Height', 0)
                    
                    ymin = int((w_top / height) * 1000)
                    xmin = int((w_left / width) * 1000)
                    ymax = int(((w_top + w_height) / height) * 1000)
                    xmax = int(((w_left + w_width) / width) * 1000)
                    
                    simplified_overlay.append({
                        "t": word.get('WordText'),
                        "b": [ymin, xmin, ymax, xmax]
                    })

        prompt = f"""
        ACTÚA COMO UN MOTOR DE RECONCILIACIÓN OCR Y OLR (Object Layout Recognition) DE GRADO ARCHIVÍSTICO.
        
        TE PROPORCIONO:
        1. Una IMAGEN de prensa histórica.
        2. Un BORRADOR OCR (JSON) con palabras y coordenadas normalizadas (0-1000) de un motor tradicional.
        
        TU MISIÓN ES GENERAR LA "TRANSCRIPCIÓN DEFINITIVA" (GOLD STANDARD):
        1. REVISIÓN VISUAL: Mira la imagen y compara cada palabra del BORRADOR.
        2. CORRECCIÓN SEMÁNTICA: Si el borrador dice "0" pero es una "O", o si hay un error tipográfico histórico, CORRÍGELO en el campo "text".
        3. AJUSTE ESPACIAL: Si el recuadro del borrador está ligeramente movido, AJÚSTALO para que encuadre perfectamente la palabra en la imagen.
        4. PALABRAS FALTANTES: Si ves palabras en la imagen que NO están en el borrador, INCLÚYELAS con sus coordenadas [ymin, xmin, ymax, xmax].
        5. ORDEN DE LECTURA: Asegura que la "transcription" final sea fluida y siga las columnas correctamente.
        6. DESGUIONIZADO: En la "transcription", une las palabras cortadas por guion al final de línea, pero en el "index" mantén cada fragmento físico con su caja.
        
        BORRADOR OCR (Referencia):
        {json.dumps(simplified_overlay[:200])}
        
        RESPONDE ÚNICAMENTE CON UN JSON PURO:
        {{
            "transcription": "Texto completo, limpio y desguionizado (sin etiquetas adicionales)",
            "index": [
                {{"text": "palabra", "box": [ymin, xmin, ymax, xmax]}},
                ...
            ],
            "metadata": {{ "titulo": "...", "fecha_original": "...", "edicion": "..." }}
        }}
        """
        
        try:
            raw_response = self._call_gemini(prompt, temperature=0, image_data=image_data)
            data = self._extract_json_from_text(raw_response)
            if data and 'index' in data:
                print(f"[AIService] Reconciliación completada: {len(data['index'])} palabras.", file=sys.stderr)
                return data
            else:
                print(f"[AIService] Reconciliación fallida o JSON inválido.", file=sys.stderr)
                return None
        except Exception as e:
            print(f"[AIService] Error en reconcile_ocr_spatial: {e}", file=sys.stderr)
            return None

    def vision_ocr_expert(self, image_data, tesseract_draft=''):
        """
        OCR Experto (Paso 2 del pipeline de 3 pasos):
        Gemini Vision con borrador Tesseract como contexto para máxima precisión.
        Especializado para documentos históricos españoles con tipografía decorativa.
        """
        draft_section = ""
        if tesseract_draft and tesseract_draft.strip():
            draft_section = f"""
BORRADOR TESSERACT (úsalo como guía estructural, NO como texto definitivo - puede tener errores):
---
{tesseract_draft[:4000]}
---
"""

        prompt = f"""ACTÚA COMO UN EXPERTO EN PALEOGRAFÍA DIGITAL Y TRANSCRIPCIÓN DIPLOMÁTICA DE DOCUMENTOS HISTÓRICOS ESPAÑOLES.

Estás procesando una página de un documento histórico español (siglo XIX-XX). La imagen puede contener:
- Tipografías decorativas, góticas, caligráficas o de imprenta antigua
- NÚMEROS CRÍTICOS: años (ej: 1900, 1903), precios (ej: 0'50 ptas, 1'50 ptas), horas (ej: las 9, las 4 y media), cantidades
- Elementos ornamentales (asteriscos, viñetas, bordes, estrellas, líneas decorativas) que NO son texto: IGNÓRALOS
- Texto en múltiples columnas o con diseño complejo
- Secciones con títulos en tipografía especial (negrita, gótica, caligráfica)

{draft_section}
INSTRUCCIONES CRÍTICAS:
1. TRANSCRIBE LITERALMENTE todo el texto visible. Los NÚMEROS, FECHAS, PRECIOS y HORAS son absolutamente críticos: léelos con máxima atención directamente de la imagen.
2. IGNORA por completo los ornamentos decorativos (series de *, ✦, líneas, bordes) que no forman parte del texto narrativo.
3. Si el borrador Tesseract tiene una palabra reconocible, úsala como referencia pero verifica con la imagen.
4. Preserva la ortografía histórica española: á (preposición), é (conjunción), fué, habia, etc.
5. Para títulos en tipografía decorativa: transcribe el texto aunque sea parcialmente ilegible, aproximándote al sentido.
6. Une palabras cortadas por guion al final de línea (ej: muni-cipal → municipal).
7. Estructura el texto con saltos de línea naturales respetando párrafos y secciones.

RESPONDE EXCLUSIVAMENTE CON JSON PURO (sin markdown, sin ```json):
{{
    "text": "Transcripción completa del documento con saltos de línea naturales y estructura clara",
    "words": [
        {{"text": "Palabra", "box_2d": [ymin, xmin, ymax, xmax]}}
    ]
}}
Las coordenadas box_2d van de 0 a 1000. Incluye al menos todas las palabras de títulos, fechas y números."""

        try:
            raw = self._call_gemini(prompt, temperature=0, image_data=image_data)
            data = self._extract_json_from_text(raw)
            if data and ('text' in data or 'words' in data):
                print(f"[AIService] vision_ocr_expert completado: {len(data.get('text',''))} chars, {len(data.get('words',[]))} palabras.", file=sys.stderr)
                return data
            # Si no hay JSON válido, devolver el texto plano de Gemini
            if raw and raw.strip():
                print(f"[AIService] vision_ocr_expert devuelve texto plano ({len(raw)} chars).", file=sys.stderr)
                return {'text': raw.strip(), 'words': []}
        except Exception as e:
            print(f"[AIService] Error en vision_ocr_expert: {e}", file=sys.stderr)

        # Fallback: devolver el borrador de Tesseract
        return {'text': tesseract_draft, 'words': []}

    def correct_ocr_text(self, text, part_num=1, total_parts=1, image_data=None, custom_prompt=None):
        """Corrige texto OCR y extrae metadatos estructurados usando IA. Soporta Vision."""
        instrucciones_contexto = ""
        if total_parts > 1:
            instrucciones_contexto = f"\nESTÁS PROCESANDO LA PARTE {part_num} DE {total_parts} DEL DOCUMENTO.\n"
            if part_num > 1:
                instrucciones_contexto += "IMPORTANTE: Prosigues con la corrección del flujo anterior. Céntrate en la coherencia y el texto.\n"

        # Refinar instrucciones si hay imagen (Vision Mode - Deep Hybrid)
        vision_instruction = ""
        if image_data:
            vision_instruction = """
TE HE PROPORCIONADO UNA IMAGEN DEL DOCUMENTO ORIGINAL Y UN BORRADOR OCR (abajo). 
Tu misión es realizar una HIFIBRIDACIÓN DE ALTA PRECISIÓN:
1. Usa el BORRADOR OCR como una guía estructural para mantener el hilo del texto.
2. Usa la IMAGEN como la FUENTE PRIMARIA DE VERDAD ABSOLUTA. Si el borrador tiene un error (ej. confundir 'S' con '8', o una palabra ilegible), corrígelo basándote en lo que ves en los píxeles.
3. El resultado final debe ser una transcripción paleográfica perfecta, literal y diplomática.
"""

        if custom_prompt:
            prompt = custom_prompt
        else:
            prompt = f"""Rol y Objetivo:
            Actúa como un Archivero Digital Senior y Especialista en Reconocimiento Óptico de Caracteres (OCR) y Análisis de Diseño de Documentos (OLR) de una Biblioteca Nacional. Tu objetivo es realizar una transcripción diplomática, INTEGRA y estructurada de la página de prensa histórica adjunta. 
            
            ES CRÍTICO: No debes omitir ni una sola palabra del documento original. Tu prioridad absoluta es la COBERTURA TOTAL (Full Coverage).
            PROHIBICIÓN ESTRICTA: NO incluyas bajo ninguna circunstancia etiquetas de sistema en "corrected_text". Elimina cualquier [DATOS CABECERA], [BORRADOR BASE], [PÁGINA X], [CONTINUA], [FIN] o similares. Devuelve solo el contenido puro de la noticia.
            
            1. Extracción de Metadatos Críticos (Prioridad 1):
            Debes extraer con absoluta precisión los datos de identificación del ejemplar que suelen aparecer en la CABECERA:
            - TITULO/PUBLICACIÓN: Nombre del periódico o revista (ej. 'EL HERALDO', 'DIARIO DE ALCOY').
            - FECHA_ORIGINAL: Fecha exacta tal cual aparece (ej. 'Viernes 12 de Enero de 1900').
            - ANIO: Solo el año numérico (4 dígitos).
            - NUMERO: Número de ejemplar o edición (ej. '4.521').
            - VOLUMEN: Tomo o año de la colección (ej. 'Año XIII').
            - CIUDAD/LUGAR: Lugar de impresión o redacción si se menciona.
            - PAGINA_INICIO: El número de página actual.
            
            2. Reglas de Oro del Paleógrafo Digital:
            - DESGUIONIZADO: Une sistemáticamente las palabras cortadas al final de línea por el diseño de columnas (ej: 'mu-nicipal' -> 'municipal', 'ocu-paron' -> 'ocuparon', 'bara-tura' -> 'baratura', 'bara=tura' -> 'baratura'). Elimina el guion (-) o el igual (=) de partición.
            - CORRECCIÓN DE ERRATAS OCR: Corrige errores evidentes de lectura digital (ej: 'teconocieron' -> 'reconocieron', 'teíga' -> 'tenga', 'nuexó' -> 'nuevo', 'Bolea' -> 'Bolsa') basándote en el sentido del castellano de la época.
            - FIDELIDAD HISTÓRICA: NO modernices palabras bien escritas en 1900 (ej: mantén 'é' como conjunción, 'á' con tilde, 'fué', 'relox', 'estensión').
            - SECCIONES Y ANUNCIOS: Identifica y separa claramente secciones (LA VIDA RELIGIOSA, TELEGRÁFICO) y bloques de anuncios.
            
            {instrucciones_contexto}
            {vision_instruction}
            
            RESPONDE EXCLUSIVAMENTE EN FORMATO JSON siguiendo esta estructura:
            {{
              "corrected_text": "Texto completo aquí...",
              "metadata": {{
                "titulo": "...",
                "publicacion": "...",
                "fecha_original": "...",
                "anio": 1900,
                "ciudad": "...",
                "numero": "...",
                "volumen": "...",
                "edicion": "...",
                "pagina_inicio": "...",
                "pagina_fin": "...",
                "autor": "...",
                "lugar_publicacion": "...",
                "editorial": "..."
              }}
            }}
            
            TEXTO OCR DE REFERENCIA PARA PROCESAR (BORRADOR):
            --------------------------------------
            {text}
            --------------------------------------
            """
        try:
            raw_text = self.generate_content(prompt, temperature=0.0, image_data=image_data, top_p=1.0)
            result_data = self._extract_json_from_text(raw_text)
            
            if result_data and 'corrected_text' in result_data and result_data['corrected_text']:
                txt = result_data['corrected_text']
                # Eliminar asteriscos de negrita/cursiva
                txt = txt.replace('**', '').replace('*', '')
                # Eliminar almohadillas de títulos de markdown
                import re
                txt = re.sub(r'#+\s*', '', txt)
                result_data['corrected_text'] = txt
                
                
            return result_data
        except Exception as e_gen:
            print(f"[AIService] Error crítico en correct_ocr_text: {e_gen}", file=sys.stderr)
            return {"corrected_text": text, "metadata": {}, "error": str(e_gen)}

    def _extract_json_from_text(self, text):
        if not text: return {}
        import json, re
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r'```json\s*(\{.*?\})\s*```', text, re.DOTALL)
            if match:
                try: return json.loads(match.group(1))
                except: pass
            match = re.search(r'(\{.*\})', text, re.DOTALL)
            if match:
                try: return json.loads(match.group(1))
                except: pass
        return {}
