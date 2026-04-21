import os
import requests
import json
import re

GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
# URL de la API REST de Gemini (usando el modelo flash 2.0 recomendado para la mayoría de tareas generales)
GEMINI_API_URL = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent'

def extract_json_from_text(text):
    if not text: return None
    try:
        # Intento directo
        return json.loads(text)
    except json.JSONDecodeError:
        # Intento con bloques de código markdown
        match = re.search(r'```json\s*(\{.*?\})\s*```', text, re.DOTALL)
        if match:
            try: return json.loads(match.group(1))
            except: pass
        # Intento buscando el primer { y el último }
        match = re.search(r'(\{.*\})', text, re.DOTALL)
        if match:
            try: return json.loads(match.group(1))
            except: pass
    return None

class GeminiService:
    def __init__(self, model=None):
        self.api_key = os.environ.get('GEMINI_API_KEY')
        
        # Mapeo de alias comunes a modelos reales de Google (Verificado via ListModels)
        model_map = {
            'flash': 'gemini-2.0-flash', 
            'pro': 'gemini-1.5-pro-002'
        }
        
        # Si se pasa un alias, lo mapeamos. Si no, usamos el modelo tal cual o el default.
        self.model = model_map.get(model, model) or "gemini-2.0-flash"
        self.url = f'https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent'

    def is_configured(self):
        return bool(self.api_key)

    def _call_gemini(self, prompt, temperature=0.1, model=None):
        if not self.is_configured():
            import logging
            logging.error("GeminiService: API Key no configurada.")
            return None
        
        # dynamic model selection
        target_url = self.url
        if model:
            target_url = f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent'

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": temperature},
            "safetySettings": [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
            ]
        }
        
        try:
            import logging
            resp = requests.post(target_url, params={"key": self.api_key}, json=payload, timeout=60) # Aumentado a 60s
            if resp.status_code != 200:
                logging.error(f"Gemini API Error {resp.status_code}: {resp.text}")
                return None
                
            data = resp.json()
            if 'candidates' not in data or not data['candidates']:
                logging.warning(f"Gemini API: No se encontraron candidatos en la respuesta: {data}")
                return None
                
            return data['candidates'][0]['content']['parts'][0]['text']
        except Exception as e:
            import logging
            logging.exception(f"Exception during Gemini API Call: {e}")
            return None
    def generate_content(self, prompt, temperature=0.1, model=None):
        """
        Public method to generate content using Gemini.
        """
        return self._call_gemini(prompt, temperature=temperature, model=model)

    def correct_ocr_text(self, text):
        """
        Lógica original esperada por routes/ocr.py
        """
        prompt = f"Corrige este texto de OCR y extrae metadatos (titulo, autor, fecha, publicacion, lugar). Responde en JSON:\n\n{text}"
        raw_text = self._call_gemini(prompt)
        return extract_json_from_text(raw_text)

    def expand_semantic_concept(self, concept, context=None):
        """
        Expande un concepto semántico buscando sinónimos, términos relacionados 
        y asociaciones históricas/periodísticas.
        """
        if not self.is_configured():
            return None
            
        prompt = f"""
        Actúa como un experto en historia y lingüística. 
        Dado el concepto "{concept}", genera una lista de 10 a 15 términos relacionados, sinónimos, 
        o palabras clave que podrían aparecer en noticias históricas (siglos XIX-XXI) asociadas a este concepto.
        Incluye variaciones antiguas o temáticas específicas.
        
        CONTEXTO ADICIONAL: {json.dumps(context or {}, ensure_ascii=False)}
        
        Responde ÚNICAMENTE con un JSON:
        {{
            "terms": ["termino1", "termino2", ...]
        }}
        """
        
        raw_text = self._call_gemini(prompt, temperature=0.3)
        data = extract_json_from_text(raw_text)
        if data and 'terms' in data:
            return data['terms']
        return None

def is_valid_location_in_text(location_name, source_text):
    """
    Valida que una ubicación detectada sea una palabra completa en el texto,
    no parte de otra palabra (para evitar falsos positivos como 'italia' en 'italiano',
    'roma' en 'romántico', etc.).
    
    Args:
        location_name: Nombre de la ubicación detectada (ej: "Italia", "Roma")
        source_text: Texto original donde se detectó
    
    Returns:
        bool: True si es una palabra completa, False si es parte de otra palabra
    """
    if not location_name or not source_text:
        return False
    
    # Patrón que busca la ubicación como palabra completa (con límites de palabra)
    # \b = word boundary (límite de palabra: espacio, puntuación, inicio/fin de línea)
    pattern = r'\b' + re.escape(location_name) + r'\b'
    
    # Buscar con case-insensitive
    match = re.search(pattern, source_text, re.IGNORECASE)
    
    return match is not None

def clean_location_name(name):
    """
    Limpia nombres de ubicaciones eliminando preposiciones históricas ('á ') 
    o modernas ('en ', 'de ', etc.) que el extractor podría haber incluido erróneamente.
    """
    if not name:
        return ""
    
    # Lista de prefijos a eliminar (insensible a mayúsculas, solo al inicio seguido de espacio)
    # Incluimos el 'á' histórico y otras preposiciones comunes de lugar
    # Usamos \b para asegurar que son palabras completas (no prefijos de palabras como Alicante)
    prefijos = [
        r'^á\s+', r'^a\s+', r'^en\s+', r'^de\s+', r'^desde\s+', 
        r'^hasta\s+', r'^hacia\s+', r'^por\s+', r'^para\s+', r'^sobre\s+',
        r'^del\s+', r'^al\s+'
    ]
    
    cleaned = name.strip()
    
    # Algunas IAs devuelven comillas o puntos al final
    cleaned = re.sub(r'^["\'«´‘]+', '', cleaned)
    cleaned = re.sub(r'["\'»´’]+$', '', cleaned)
    cleaned = cleaned.strip(' .,;')

    for p in prefijos:
        cleaned = re.sub(p, '', cleaned, flags=re.IGNORECASE).strip()
    
    # Repetir limpieza de mayúscula por si tras quitar el prefijo quedó en minúscula
    if cleaned and cleaned[0].islower():
        cleaned = cleaned[0].upper() + cleaned[1:]
    
    return cleaned

def merge_nested_locations(conteo_dict):
    """
    Deduplica nombres de ubicaciones basados en contención.
    Si 'Valencia' y 'Reino de Valencia' están presentes, se queda solo con el más corto
    (el más general) EXCEPTO si el largo es el nombre con artículo (Toboso -> El Toboso).
    Recibe: {'Valencia': 6, 'Reino de Valencia': 3}
    Retorna: {'Valencia': 9}
    """
    if not conteo_dict:
        return {}
        
    nombres = sorted(conteo_dict.keys(), key=len)
    final_dict = {}
    omitir = set()
    articulos = ['el ', 'la ', 'los ', 'las ', 'del ', 'al ']
    
    for i, corto in enumerate(nombres):
        if corto in omitir:
            continue
            
        for largo in nombres[i+1:]:
            if largo in omitir:
                continue
            
            # Si el corto está contenido en el largo (ej: "Valencia" in "Reino de Valencia")
            if corto.lower() in largo.lower():
                # CASO ESPECIAL: Si el largo es simplemente el corto con un artículo al inicio
                es_articulo = False
                for art in articulos:
                    if largo.lower() == art + corto.lower():
                        es_articulo = True
                        break
                
                if es_articulo:
                    # Preferimos el largo (con artículo)
                    conteo_dict[largo] += conteo_dict.get(corto, 0)
                    omitir.add(corto)
                    break # Salimos del bucle del corto i porque ya lo hemos omitido
                else:
                    # Omitimos el largo porque el corto ya lo representa/aglutina
                    conteo_dict[corto] += conteo_dict.get(largo, 0)
                    omitir.add(largo)
        
        if corto not in omitir:
            final_dict[corto] = conteo_dict[corto]
        
    return final_dict

def extract_locations_with_gemini(texto, contexto=None):
    """
    Función de alta precisión para extracción de lugares
    """
    service = GeminiService()
    if not service.is_configured():
        return None
    
    prompt = f"""
    Extrae ÚNICAMENTE las ubicaciones geográficas reales de este texto.
    Normaliza los nombres y desambigua según el contexto.
    
    INSTRUCCIONES CRÍTICAS (SKEPTIC MODE):
    1. EXCLUYE sustantivos comunes que no sean lugares en el contexto (ej: 'colonia' de olor, 'puerto' de conexión USB -si fuera moderno-, 'vía' de tren si se usa como metáfora).
    2. EXCLUYE preposiciones iniciales (ej: 'á Toledo' -> 'Toledo').
    3. NORMALIZA al estándar actual (ej: 'Escorial' -> 'El Escorial').
    4. **GENTILICIOS NO SON UBICACIONES**: NO extraigas gentilicios (italiano, español, francés, etc.) como ubicaciones. Solo extrae el topónimo si aparece como palabra COMPLETA.
    5. **VALIDACIÓN DE PALABRA COMPLETA**: Solo extrae una ubicación si aparece como palabra independiente (con espacios/puntuación antes y después), NO si es parte de otra palabra:
       - ❌ "italiano" NO contiene la ubicación "Italia"
       - ❌ "romántico" NO contiene la ubicación "Roma"  
       - ❌ "romance" NO contiene la ubicación "Roma"
       - ✅ "Italia es bella" SÍ contiene la ubicación "Italia"
       - ✅ "viajó a Roma" SÍ contiene la ubicación "Roma"
    6. SI TIENES DUDAS, NO LO EXTRAIGAS. Es preferible omitir que tener falsos positivos.
    
    CONTEXTO: {json.dumps(contexto or {}, ensure_ascii=False)}
    TEXTO: \"\"\"{texto[:50000]}\"\"\"
    
    Responde ÚNICAMENTE con un JSON:
    {{
        "locations": [
            {{ "original": "...", "normalized": "...", "confidence": 0.0-1.0, "reasoning": "..." }}
        ]
    }}
    """
    
    raw_text = service._call_gemini(prompt)
    data = extract_json_from_text(raw_text)
    
    if data and 'locations' in data:
        # Post-procesamiento de limpieza por si la IA falla en la instrucción
        for loc in data['locations']:
            if 'normalized' in loc:
                loc['normalized'] = clean_location_name(loc['normalized'])
            if 'original' in loc:
                loc['original'] = clean_location_name(loc['original'])
                
    return data

def geocode_with_ai(name, context=None):
    """
    Usa Gemini para intentar geocodificar un nombre que Nominatim no reconoce.
    Útil para erratas, nombres antiguos o variantes lingüísticas (Carinano -> Carignano).
    """
    service = GeminiService()
    if not service.is_configured():
        return None
    
    prompt = f"""
    Actúa como un experto en geografía e historia.
    Intenta identificar la ubicación "{name}" y devolver sus coordenadas (latitud y longitud).
    Si es una errata (ej. Carinano -> Carignano) o un nombre antiguo, identifícalo.
    
    INSTRUCCIÓN CRÍTICA: El 'name_canonical' NO debe incluir preposiciones iniciales (á, a, en, de), pero SÍ debe incluir el artículo si es parte del nombre propio (ej: 'El Toboso'). Prioriza resultados en España si el contexto corresponde a la obra de Cervantes o literatura española.
    
    CONTEXTO: {json.dumps(context or {}, ensure_ascii=False)}
    
    Responde ÚNICAMENTE con un JSON:
    {{
        "found": true/false,
        "name_canonical": "nombre correcto",
        "lat": 0.0,
        "lon": 0.0,
        "explanation": "breve explicación si es typo o histórico"
    }}
    """
    
    raw_text = service._call_gemini(prompt, temperature=0.1)
    data = extract_json_from_text(raw_text)
    if data and data.get('found'):
        if 'name_canonical' in data:
            data['name_canonical'] = clean_location_name(data['name_canonical'])
        return data
    return None

def interpret_semantic_topography_map(concept, terms, points_summary, context=None):
    """
    Analiza los resultados de una topografía semántica y genera una lectura interpretativa.
    Ahora incluye evidencias narrativas de los textos para una lectura más profunda.
    """
    service = GeminiService()
    if not service.is_configured():
        return None
        
    evidencias = (context or {}).get('evidencias', [])
    evidencias_str = ""
    for ev in evidencias:
        evidencias_str += f"- DOC: {ev['titulo']} ({ev['fecha']}) en [{ev['lat']}, {ev['lon']}]: \"{ev['texto']}\"\n"

    prompt = f"""
    Actúa como un historiador experto en geosemántica y analista de datos. 
    He generado una 'Topografía Semántica' en HesiOX para el concepto "{concept}".
    
    TÉRMINOS ASOCIADOS (Expansión Semántica): {", ".join(terms)}
    RESUMEN DE DENSIDAD (Coordenadas y Pesos): {points_summary}
    CONTEXTO DEL PROYECTO: {json.dumps({"nombre": (context or {}).get('proyecto_nombre'), "desc": (context or {}).get('proyecto_descripcion')}, ensure_ascii=False)}
    
    EVIDENCIAS NARRATIVAS (Textos en los focos de mayor densidad):
    {evidencias_str}
    
    Tu tarea es realizar una LECTURA GEOPRENSÍSTICA de estos datos:
    1. **Correlación Narrativa**: Analiza cómo el contenido de los textos (evidencias) justifica la formación de los "picos" o focos en la topografía. ¿Por qué el concepto '{concept}' se concentra en esos lugares según lo que dicen los textos?
    2. **Interpretación del Territorio**: Explica qué nos dice esta distribución sobre la importancia del concepto en el mapa. ¿Es un fenómeno urbano, fronterizo, regional? 
    3. **Lectura de la Locura/Sentido**: (Ejemplo) Si hablamos de 'miedo', identifica en los fragmentos la causa de ese miedo en relación al lugar.
    
    El tono debe ser profesional, académico y extremadamente analítico. Cita o menciona títulos de los documentos si es necesario para dar solidez a la interpretación.
    
    Responde en español, con 3-4 párrafos bien estructurados.
    """
    
    return service._call_gemini(prompt, temperature=0.4)

def analyze_sentiment_batch(texts, context=None):
    """
    Analiza el sentimiento de una lista de fragmentos de texto.
    Devuelve una lista de puntuaciones entre -1 (negativo) y 1 (positivo).
    """
    service = GeminiService()
    if not service.is_configured() or not texts:
        return [0] * len(texts)
        
    prompt = f"""
    Actúa como un historiador experto en análisis de discurso. 
    Analiza el sentimiento de los siguientes fragmentos de prensa histórica respecto al tema del proyecto.
    
    CONTEXTO PROYECTO: {json.dumps(context or {}, ensure_ascii=False)}
    
    FRAGMENTOS:
    {json.dumps(texts, ensure_ascii=False)}
    
    Responde ÚNICAMENTE con un JSON que contenga una lista de 'scores' (flotantes entre -1 y 1):
    {{
        "scores": [-0.5, 0.8, 0.0, ...]
    }}
    -1 = Muy negativo/amenazante/pesimista
     0 = Neutral/informativo
     1 = Muy positivo/esperanzador/optimista
    """
    
    raw_text = service._call_gemini(prompt, temperature=0.1)
    data = extract_json_from_text(raw_text)
    if data and 'scores' in data:
        return data['scores']
    return [0] * len(texts)

def summarize_text_gemini(text, context=None):
    """
    Genera un resumen periodístico y analítico del texto proporcionado.
    """
    service = GeminiService()
    if not service.is_configured():
        return None
        
    prompt = f"""
    Actúa como un analista de inteligencia y redactor jefe de prensa.
    Tu tarea es generar un RESUMEN EJECUTIVO del siguiente texto histórico/periodístico.
    
    TEXTO:
    \"\"\"{text[:30000]}\"\"\"
    
    Instrucciones:
    1. Genera un título conceptual (diferente al original) que capture la esencia.
    2. Redacta un resumen de 2-3 párrafos destacando los hechos clave (qué, quién, cuándo, dónde, por qué).
    3. Extrae 3-5 "Puntos Clave" o "Insights" en formato lista.
    4. El tono debe ser objetivo, profesional y en español.
    
    Responde ÚNICAMENTE con un JSON:
    {{
        "titulo_conceptual": "...",
        "resumen": "...",
        "puntos_clave": ["...", "..."]
    }}
    """
    
    raw_text = service._call_gemini(prompt, temperature=0.3)
    return extract_json_from_text(raw_text)
    
