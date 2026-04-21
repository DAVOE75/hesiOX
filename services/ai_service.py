import os
import requests
import json
import sys
import anthropic
import google.generativeai as genai

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
        return None

    def _call_gemini(self, prompt, temperature, image_data=None, top_p=None):
        import sys
        try:
            # Version-resilient model mapping for Gemini (preferring -latest for stability in this env)
            model_map = {
                'flash': 'gemini-flash-latest',
                'pro': 'gemini-pro-latest',
                '1.5-pro': 'gemini-pro-latest',
                '1.5-flash': 'gemini-flash-latest',
                'gemini-1.5-flash': 'gemini-flash-latest',
                'gemini-1.5-pro': 'gemini-pro-latest',
                '2.0-flash': 'gemini-2.0-flash-exp',
                'gemini-pro': 'gemini-pro-latest' # Redirect old name to modern pro
            }
            # Fallback direct names for models that might be in different API versions
            model_name = model_map.get(self.model, self.model or "gemini-flash-latest")
            
            # Robust prefix verification
            if not model_name.startswith('gemini-') and not model_name.startswith('models/'):
                model_name = 'gemini-1.5-flash-latest' # Final safety fallback
            
            # Verificar origen de la API KEY para log
            usando_key_usuario = self.user and getattr(self.user, 'api_key_gemini', None)
            key_info = f"Usuario (ID: {self.user.id})" if usando_key_usuario else "Sistema (Environment)"
            
            print(f"[AIService Gemini] Configurando Gemini con modelo: {model_name} | Key source: {key_info}", file=sys.stderr)
            genai.configure(api_key=self.api_key)
            
            try:
                model = genai.GenerativeModel(model_name)
            except Exception as e:
                print(f"[AIService Gemini] Error inicializando {model_name}: {e}. Intentando fallback a gemini-flash-latest.", file=sys.stderr)
                model = genai.GenerativeModel('gemini-flash-latest')
            
            parts = [prompt]
            if image_data:
                # Handle base64 image data
                base64_content = image_data
                mime_type = "image/jpeg"
                if "," in image_data:
                    header, base64_content = image_data.split(",", 1)
                    if "image/" in header:
                        mime_type = header.split(";")[0].split(":")[1]
                
                parts.append({
                    "mime_type": mime_type,
                    "data": base64_content
                })
                
            gen_config_kwargs = {'temperature': temperature}
            if top_p is not None:
                gen_config_kwargs['top_p'] = top_p
            
            print(f"[AIService Gemini] Llamando a generate_content con {model_name}...", file=sys.stderr)
            try:
                response = model.generate_content(
                    parts,
                    generation_config=genai.types.GenerationConfig(**gen_config_kwargs)
                )
            except Exception as e:
                # Si falla el primer modelo (ej. 404 on Pro), intentamos fallback a Flash Latest
                fallback_model_name = "gemini-flash-latest"
                print(f"[AIService Gemini] Error con {model_name}: {e}. Intentando fallback a {fallback_model_name}...", file=sys.stderr)
                model = genai.GenerativeModel(fallback_model_name)
                response = model.generate_content(
                    parts,
                    generation_config=genai.types.GenerationConfig(**gen_config_kwargs)
                )

            print(f"[AIService Gemini] Respuesta recibida satisfactoriamente.", file=sys.stderr)
            return response.text
        except Exception as e:
            self.last_error = f"Gemini Error: {str(e)}"
            print(f"[AIService Gemini] ERROR: {type(e).__name__}: {e}", file=sys.stderr)
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

    def correct_ocr_text(self, text, part_num=1, total_parts=1, image_data=None):
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

        prompt = f"""System Instructions: Arquetipo de Transcriptor Paleográfico
Actúa como un experto en paleografía y digitalización de prensa histórica de élite. Tu objetivo es realizar una transcripción diplomática (literal) del documento.
{instrucciones_contexto}
{vision_instruction}

1. Reglas de Fidelidad Textual:
- Literalidad Absoluta: Transcribe exactamente lo que ves. No corrijas ortografía antigua, no modernices términos (ej. mantener "septentrión", "sármatas") y no omitas conjunciones aunque parezcan redundantes.
- Puntuación Histórica: Respeta escrupulosamente el uso de puntos y comas (;), guiones largos (—) y paréntesis. En prensa histórica, la puntuación dicta el ritmo de la lectura original.
- Tratamiento de Superíndices: Identifica las llamadas a notas al pie (números pequeños como 15, 16) y sepáralas del texto mediante etiquetas, por ejemplo: [nota: 15]. Esto evita que el OCR fusione el número con la palabra anterior.

2. Optimización para Prensa Histórica (Layout):
- Reconstrucción de Párrafos: Si una palabra está dividida por un guion al final de una línea o una frase continúa en la siguiente captura, realiza una "unión inteligente" para mantener la fluidez del párrafo.
- Detección de Columnas: En caso de formato de periódico, transcribe columna por columna de izquierda a derecha, manteniendo la separación visual mediante saltos de línea dobles.
- Gestión de Errores de Imprenta: Si encuentras una errata evidente del cajista original (ej. una letra invertida o una mancha de tinta), transcribe lo que se lee pero añade un marcador [sic] o [ilegible] si es necesario.

3. Verificación de Entidades Propias (Nombres y Geografía):
- Validación de Onomástica: Cruza los nombres propios detectados con contextos históricos y bíblicos (específicamente la genealogía de los hijos de Jafet: Gomer, Magog, Madai, Javán, etc.) para asegurar que una "n" no se confunda con una "u".
- Toponimia Antigua: Mantén los nombres de lugares tal como aparecen (ej. "Tánais", "Meótida", "Gades"), asegurando que los acentos se preserven según el original impreso.

4. Estructuración y Formato de Salida (CRÍTICO):
Debes generar la transcripción literal en la propiedad "corrected_text" del JSON y extraer los metadatos relevantes en la propiedad "metadata".
El output debe ser EXCLUSIVAMENTE el JSON, sin introducciones ni comentarios tuyos (Response Mimicry).

RESPONDE EXCLUSIVAMENTE EN FORMATO JSON con esta estructura exacta y sin bloque markdown de código:
{{
    "corrected_text": "Tu transcripción paleográfica estricta aquí, respetando superíndices, saltos dobles y notas.",
    "metadata": {{
        "titulo": "Título detectado o null",
        "autor": "Autor detectado o null",
        "fecha_original": "Fecha tal cual aparece (ej. 15 de mayo de 1906) o null",
        "anio": 1906,
        "publicacion": "Nombre de la obra/periódico o null",
        "ciudad": "Ciudad mencionada o null",
        "confianza": 0.99,
        "correcciones": ["Lista de inferencias paleográficas realizadas, como uniones de guiones o adición de [sic]"]
    }}
}}

TEXTO OCR DE REFERENCIA:
\"\"\"{text}\"\"\"
"""
        raw_text = self.generate_content(prompt, temperature=0.0, image_data=image_data, top_p=1.0)
        return self._extract_json_from_text(raw_text)

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
