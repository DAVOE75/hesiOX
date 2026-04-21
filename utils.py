# --- Proyecto activo ---
def get_proyecto_activo():
    """
    Función auxiliar para obtener el proyecto activo de la sesión
    """
    from routes.proyectos import get_proyecto_activo as get_proyecto
    return get_proyecto()

    return get_proyecto()

# =========================================================
# CONFIGURACIÓN DEL SISTEMA
# =========================================================
import json
import os

CONFIG_FILE = 'server_config.json'
DEFAULT_CONFIG = {
    "spacy_model": "es_core_news_lg",
    "max_char_limit": 15000
}

def load_config():
    """Carga la configuración del sistema desde archivo JSON"""
    if not os.path.exists(CONFIG_FILE):
        return DEFAULT_CONFIG
    try:
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error cargando config: {e}")
        return DEFAULT_CONFIG

def save_config(new_config):
    """Guarda la configuración en archivo JSON"""
    try:
        # Validar claves
        config = load_config()
        config.update(new_config)
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=4)
        
        # Invalidar modelo si cambió
        if hasattr(get_nlp, 'model'):
            delattr(get_nlp, 'model')
            
        print("Configuración guardada correctamente.")
        return True
    except Exception as e:
        print(f"Error guardando config: {e}")
        return False

def get_nlp():
    """
    Lazy loader para el modelo de Spacy (configurable)
    """
    if not hasattr(get_nlp, 'model'):
        import spacy
        config = load_config()
        modelo_seleccionado = config.get("spacy_model", "es_core_news_md")
        
        # Intentar cargar modelo seleccionado primero
        modelos = [modelo_seleccionado, 'es_core_news_md', 'es_core_news_sm']
        # Eliminar duplicados manteniendo orden
        modelos = list(dict.fromkeys(modelos))
        
        get_nlp.model = None
        
        for modelo in modelos:
            try:
                print(f"Intentando cargar modelo spaCy: {modelo}...")
                get_nlp.model = spacy.load(modelo)
                print(f"✅ Modelo {modelo} cargado correctamente.")
                break
            except OSError:
                print(f"⚠️ Modelo {modelo} no encontrado.")
            except Exception as e:
                print(f"❌ Error inesperado cargando {modelo}: {e}")
        
        if get_nlp.model is None:
            print("🚨 ERROR FATAL: Ningún modelo de spaCy pudo ser cargado.")
            
    return get_nlp.model
"""
Utilidades y funciones auxiliares optimizadas para el sistema de bibliografía
"""
import re
import unicodedata
from datetime import datetime
from functools import lru_cache
from urllib.parse import parse_qs, unquote, urlencode, urlparse

from sqlalchemy import func
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError

# =========================================================
# CONSTANTES PAÍSES
# =========================================================
COUNTRY_CODES = {
    "España": "es",
    "Francia": "fr",
    "Alemania": "de",
    "Reino Unido": "gb",
    "Estados Unidos": "us",
    "Italia": "it",
    "Portugal": "pt",
    "Argentina": "ar",
    "México": "mx",
    "Chile": "cl",
    "Colombia": "co",
    "Perú": "pe",
    "Brasil": "br",
    "Canadá": "ca",
    "Rusia": "ru",
    "China": "cn",
    "Japón": "jp",
    "India": "in",
    "Australia": "au",
    "Suiza": "ch",
    "Suecia": "se",
    "Noruega": "no",
    "Holanda": "nl",
    "Países Bajos": "nl",
    "Bélgica": "be",
    "Austria": "at",
    "Dinamarca": "dk",
    "Polonia": "pl",
    "Ucrania": "ua",
    "Grecia": "gr",
    "Turquía": "tr",
    "Israel": "il",
    "Egipto": "eg",
    "Marruecos": "ma",
    "Sudáfrica": "za",
    "Cuba": "cu",
    "Venezuela": "ve",
    "Uruguay": "uy",
    "Paraguay": "py",
    "Bolivia": "bo",
    "Ecuador": "ec",
    "Costa Rica": "cr",
    "Panamá": "pa",
    "República Dominicana": "do",
    "Puerto Rico": "pr",
    "Guinea Ecuatorial": "gq",
    "El Salvador": "sv",
    "Guatemala": "gt",
    "Honduras": "hn",
    "Nicaragua": "ni",
    "Filipinas": "ph",
}

def get_country_code(country_name):
    """Devuelve código ISO de 2 letras para flag-icon-css"""
    if not country_name:
        return None
    name = country_name.strip()
    # Try exact match
    code = COUNTRY_CODES.get(name)
    if code:
        return code
    # Try title case
    return COUNTRY_CODES.get(name.title(), "xx")


# =========================================================
# GEOCODIFICACIÓN
# =========================================================
def geocode_city(city_name, country_name=None):
    """
    Obtiene lat/lon de una ciudad usando Nominatim.
    Retorna (lat, lon, address_raw, status, provincia) 
    o (None, None, None, error_status, None).
    """
    if not city_name:
        return None, None, None, "EMPTY_QUERY", None

    try:
        # User-Agent requerido por términos de uso de Nominatim
        geolocator = Nominatim(user_agent="app_bibliografia_sirio", timeout=4)
        
        query = city_name
        if country_name:
            query = f"{city_name}, {country_name}"

        # Request addressdetails to get hierarchy (state, province, etc)
        location = geolocator.geocode(query, language="es", addressdetails=True)
        
        if location:
            # Extract province/state
            raw = location.raw.get('address', {})
            # Possible keys for province in Nominatim: state, province, region...
            # "state" is usually the top-level administrative division (Comunidad Autónoma or Province depending on country)
            # In Spain: state = Comunidad, province = Provincia. if province is missing, maybe it's uniprovincial (Madrid)
            provincia = raw.get('province') or raw.get('state') or raw.get('region')
            
            return location.latitude, location.longitude, location.address, "OK", provincia
        else:
            return None, None, None, "NOT_FOUND", None

    except (GeocoderTimedOut, GeocoderServiceError) as e:
        return None, None, None, "TIMEOUT_ERROR", None
    except Exception as e:
        return None, None, None, f"ERROR: {str(e)}", None


# =========================================================
# CACHÉ DE CONSULTAS FRECUENTES
# =========================================================
class QueryCache:
    """Caché simple para consultas frecuentes"""
    def __init__(self):
        self._cache = {}
        self._timestamps = {}
    
    def get(self, key):
        """Obtiene valor del caché si no ha expirado"""
        if key in self._cache:
            # Verificar que no haya pasado más de 5 minutos
            if (datetime.now() - self._timestamps[key]).seconds < 300:
                return self._cache[key]
            else:
                # Limpiar entrada expirada
                del self._cache[key]
                del self._timestamps[key]
        return None
    
    def set(self, key, value):
        """Guarda valor en caché con timestamp"""
        self._cache[key] = value
        self._timestamps[key] = datetime.now()
    
    def clear(self):
        """Limpia todo el caché"""
        self._cache.clear()
        self._timestamps.clear()


# Instancia global del caché
cache = QueryCache()


# =========================================================
# VALIDACIÓN Y NORMALIZACIÓN
# =========================================================
def validar_fecha_ddmmyyyy(fecha_str):
    """
    Valida que una fecha tenga formato DD/MM/YYYY y valores válidos.
    Retorna (True, None) si es válida o (False, mensaje_error) si no lo es.
    """
    if not fecha_str or not fecha_str.strip():
        return (True, None)  # Campo vacío es válido

    fecha_str = fecha_str.strip()
    match = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})$", fecha_str)
    if not match:
        return (False, f"Formato incorrecto: '{fecha_str}'. Use DD/MM/YYYY")

    dia, mes, anio = map(int, match.groups())

    if not (1 <= mes <= 12):
        return (False, f"Mes inválido ({mes}). Debe estar entre 1 y 12")

    if not (1800 <= anio <= 2100):
        return (False, f"Año fuera de rango ({anio}). Debe estar entre 1800 y 2100")

    # Validar días por mes (incluyendo años bisiestos)
    dias_mes = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    if (anio % 4 == 0 and anio % 100 != 0) or (anio % 400 == 0):
        dias_mes[1] = 29  # Febrero en año bisiesto

    if not (1 <= dia <= dias_mes[mes - 1]):
        return (
            False,
            f"Día inválido ({dia}) para el mes {mes}. Máximo: {dias_mes[mes - 1]}",
        )

    return (True, None)


def normalizar_texto(texto):
    """Normaliza texto: minúsculas, sin acentos, sin puntuación múltiple"""
    if not texto:
        return ""
    
    texto = texto.lower().strip()
    # Quitar acentos
    texto = "".join(
        c
        for c in unicodedata.normalize("NFD", texto)
        if unicodedata.category(c) != "Mn"
    )
    # Quitar puntuación múltiple
    texto = re.sub(r"[^\w\s]", "", texto)
    # Espacios múltiples a uno solo
    texto = re.sub(r"\s+", " ", texto)
    return texto


def normalizar_next(next_raw):
    """Normaliza y valida URLs de redirección"""
    if not next_raw:
        return None
    decoded = unquote(next_raw)
    parsed = urlparse(decoded)
    if not parsed.path.startswith("/"):
        return "/"
    if parsed.path.startswith("/filtrar"):
        safe_path = "/"
    else:
        safe_path = parsed.path
    query_dict = parse_qs(parsed.query)
    flat_query = {k: v[0] if len(v) == 1 else v for k, v in query_dict.items()}
    qs = urlencode(flat_query, doseq=True)
    if qs:
        return f"{safe_path}?{qs}"
    else:
        return safe_path or "/"


# =========================================================
# DISTANCIA DE LEVENSHTEIN (CON CACHÉ)
# =========================================================
@lru_cache(maxsize=1024)
def levenshtein_distance(s1, s2):
    """
    Calcula la distancia de Levenshtein entre dos strings con caché LRU.
    Retorna el número mínimo de operaciones necesarias.
    """
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)

    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


def similitud_titulos(titulo1, titulo2, umbral=0.85):
    """
    Compara dos títulos usando distancia de Levenshtein normalizada.
    Retorna True si la similitud >= umbral (por defecto 85%).
    """
    if not titulo1 or not titulo2:
        return False

    t1_norm = normalizar_texto(titulo1)
    t2_norm = normalizar_texto(titulo2)

    # Si son idénticos tras normalización
    if t1_norm == t2_norm:
        return True

    # Calcular similitud con Levenshtein
    distancia = levenshtein_distance(t1_norm, t2_norm)
    longitud_max = max(len(t1_norm), len(t2_norm))

    if longitud_max == 0:
        return False

    similitud = 1 - (distancia / longitud_max)
    return similitud >= umbral


def fechas_similares(fecha1, fecha2, tolerancia_dias=1):
    """
    Compara dos fechas DD/MM/YYYY.
    Retorna True si son iguales o están dentro de tolerancia_dias.
    """
    if not fecha1 or not fecha2:
        return False

    try:
        from datetime import datetime, timedelta

        f1 = datetime.strptime(fecha1.strip(), "%d/%m/%Y")
        f2 = datetime.strptime(fecha2.strip(), "%d/%m/%Y")
        diferencia = abs((f1 - f2).days)
        return diferencia <= tolerancia_dias
    except:
        return False


# =========================================================
# FUNCIONES DE FORMATEO
# =========================================================
def separar_autor(autor_raw):
    """Separa nombre y apellido de un autor en formato 'Apellido, Nombre'"""
    if not autor_raw:
        return ("", "")
    autor_raw = autor_raw.strip()
    partes = [p.strip() for p in autor_raw.split(",")]
    if len(partes) == 2:
        apellido, nombre = partes[0], partes[1]
        return (nombre, apellido)
    pedazos = autor_raw.split()
    if len(pedazos) > 1:
        nombre = " ".join(pedazos[:-1])
        apellido = pedazos[-1]
        return (nombre, apellido)
    return (autor_raw, "")


@lru_cache(maxsize=256)
def capitalizar_palabra(w):
    """Capitaliza una palabra (caché para palabras repetidas)"""
    if not w:
        return ""
    return w[0].upper() + w[1:].lower()


def formatear_autor_por_estilo(nombre, apellido, estilo):
    """Formatea nombre de autor según el estilo bibliográfico"""
    if apellido:
        apellido_cap = (
            apellido.upper() if estilo == "une" else capitalizar_palabra(apellido)
        )
    else:
        apellido_cap = ""

    def caps_nombres(nombres):
        return (
            " ".join(capitalizar_palabra(x) for x in nombres.split()) if nombres else ""
        )

    nombre_cap = caps_nombres(nombre)
    if estilo == "une":
        if apellido_cap or nombre_cap:
            if apellido_cap and nombre_cap:
                return f"{apellido_cap}, {nombre_cap}"
            elif apellido_cap:
                return apellido_cap
            else:
                return nombre_cap
        else:
            return ""
    else:
        if apellido_cap and nombre_cap:
            return f"{apellido_cap}, {nombre_cap}"
        elif apellido_cap:
            return apellido_cap
        elif nombre_cap:
            return nombre_cap
        else:
            return "Anónimo"


def try_parse_fecha_ddmmyyyy(fecha_texto):
    """Intenta parsear una fecha en formato DD/MM/YYYY, YYYY-MM-DD o YYYY"""
    if not fecha_texto:
        return None, None
    texto = fecha_texto.strip()
    # Formato DD/MM/YYYY
    try:
        if re.match(r"^\d{1,2}/\d{1,2}/\d{4}$", texto):
            dt = datetime.strptime(texto, "%d/%m/%Y")
            return dt, dt.year
    except Exception:
        pass
    # Formato ISO YYYY-MM-DD
    try:
        if re.match(r"^\d{4}-\d{2}-\d{2}$", texto):
            dt = datetime.strptime(texto, "%Y-%m-%d")
            return dt, dt.year
    except Exception:
        pass
    if texto.isdigit() and len(texto) == 4:
        return None, int(texto)
    return None, None


def formatear_fecha_para_ui(fecha_texto):
    """
    Estandariza cualquier formato de fecha a DD/MM/YYYY para la interfaz.
    Si no puede parsearlo, devuelve el texto original.
    """
    if not fecha_texto:
        return ""
    dt, anio = try_parse_fecha_ddmmyyyy(fecha_texto)
    if dt:
        return dt.strftime("%d/%m/%Y")
    if anio:
        return str(anio)
    return fecha_texto


def fecha_en_estilo(dt, solo_anio, estilo, original_raw):
    """Formatea fecha según el estilo bibliográfico"""
    meses_es_largo = {
        1: "enero", 2: "febrero", 3: "marzo", 4: "abril",
        5: "mayo", 6: "junio", 7: "julio", 8: "agosto",
        9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre",
    }
    if solo_anio and not dt:
        return str(solo_anio)
    if dt:
        d, m, y = dt.day, dt.month, dt.year
        if estilo == "chicago":
            return f"{d} de {meses_es_largo[m]} de {y}"
        return original_raw or f"{d:02d}/{m:02d}/{y}"
    return original_raw or ""


def construir_paginas(pagina_inicio, pagina_fin):
    """Construye string de páginas en formato bibliográfico"""
    if pagina_inicio and pagina_fin:
        return f"p. {pagina_inicio}-{pagina_fin}"
    elif pagina_inicio:
        return f"p. {pagina_inicio}"
    else:
        return ""


# =========================================================
# STOPWORDS ESPAÑOL (Conjunto extendido para filtrado O(1))
# =========================================================
STOPWORDS_ES = {
    "a", "á", "acá", "ademas", "además", "adonde", "adónde", "ahi", "ahí", "ahora", 
    "al", "algo", "algún", "alguna", "algunas", "alguno", "algunos", "allá", "alli", 
    "allí", "alrededor", "ambos", "ante", "antes", "apenas", "aquel", "aquél", 
    "aquella", "aquélla", "aquellas", "aquéllas", "aquello", "aquellos", "aquéllos", 
    "aqui", "aquí", "asi", "así", "atras", "atrás", "aun", "aún", "aunque", "ayer", 
    "b", "bajo", "bastante", "c", "cabe", "cada", "casi", "cerca", "cierta", 
    "ciertas", "cierto", "ciertos", "cinco", "claro", "como", "cómo", "con", 
    "conmigo", "consigo", "contigo", "contra", "cual", "cuál", "cuales", "cuáles", 
    "cualquier", "cualquiera", "cualquieras", "cuan", "cuán", "cuando", "cuándo", 
    "cuanta", "cuánta", "cuantas", "cuántas", "cuanto", "cuánto", "cuantos", 
    "cuántos", "cuatro", "d", "de", "debajo", "del", "delante", "demas", "demás", 
    "dentro", "desde", "despues", "después", "detras", "detrás", "dia", "dias", 
    "dña", "donde", "dónde", "dos", "durante", "e", "é", "el", "él", "ella", 
    "ellas", "ello", "ellos", "embargo", "en", "encima", "entonces", "entre", "era", 
    "erais", "eramos", "éramos", "eran", "eras", "eres", "es", "esa", "ésa", "esas", 
    "ésas", "ese", "ése", "eso", "esos", "ésos", "esta", "está", "ésta", "estaba", 
    "estabais", "estábamos", "estaban", "estabas", "estad", "estada", "estadas", 
    "estais", "estáis", "estamos", "estan", "están", "estando", "estar", "estará", 
    "estarán", "estarás", "estaré", "estaréis", "estaremos", "estaría", "estaríais", 
    "estaríamos", "estarían", "estarías", "estas", "estás", "éstas", "este", "esté", 
    "éste", "estéis", "estemos", "estén", "estés", "esto", "estos", "éstos", "estoy", 
    "estuve", "estuviera", "estuvierais", "estuviéramos", "estuvieran", "estuvieras", 
    "estuvieron", "estuviese", "estuvieseis", "estuviésemos", "estuviesen", 
    "estuvieses", "estuvimos", "estuviste", "estuvisteis", "estuvo", "etc", "ex", 
    "f", "fue", "fué", "fuera", "fuerais", "fuéramos", "fueran", "fueras", "fueron", 
    "fuese", "fueseis", "fuésemos", "fuesen", "fueses", "fui", "fuí", "fuimos", 
    "fuiste", "fuisteis", "g", "h", "ha", "habéis", "haber", "habia", "había", 
    "habíais", "habíamos", "habían", "habías", "habida", "habidas", "habido", 
    "habidos", "habiendo", "habla", "hablan", "habrá", "habrán", "habrás", "habré", 
    "habréis", "habremos", "habría", "habríais", "habríamos", "habrían", "habrías", 
    "hace", "hacen", "hacer", "hacia", "hacía", "hago", "han", "has", "hasta", 
    "hay", "haya", "hayáis", "hayamos", "hayan", "hayas", "he", "hecho", "hemos", 
    "hicieron", "hizo", "hube", "hubiera", "hubierais", "hubiéramos", "hubieran", 
    "hubieras", "hubieron", "hubiese", "hubieseis", "hubiésemos", "hubiesen", 
    "hubieses", "hubimos", "hubiste", "hubisteis", "hubo", "i", "incluso", "j", 
    "jamás", "junto", "k", "kg", "km", "l", "la", "las", "le", "les", "lo", "los", 
    "luego", "m", "mas", "más", "me", "mi", "mí", "mia", "mía", "mias", "mías", 
    "mientras", "mio", "mío", "mios", "míos", "mis", "mucho", "muchos", "muy", "n", 
    "nada", "ni", "no", "nos", "nosotras", "nosotros", "nuestra", "nuestras", 
    "nuestro", "nuestros", "o", "ó", "ocho", "os", "otra", "otras", "otro", "otros", 
    "p", "para", "pero", "poco", "por", "porque", "porqué", "pues", "q", "que", 
    "qué", "quien", "quién", "quienes", "quiénes", "quienesquiera", "quienquiera", 
    "quiza", "quizá", "quizas", "quizás", "r", "s", "se", "sé", "sea", "seáis", 
    "seamos", "sean", "seas", "segun", "según", "seis", "sera", "será", "serán", 
    "serás", "seré", "seréis", "seremos", "seria", "sería", "seríais", "seríamos", 
    "serían", "serías", "si", "sí", "sido", "siempre", "siendo", "siete", 
    "siguiente", "sin", "sín", "sino", "so", "sobre", "sois", "sola", "solamente", 
    "solas", "solo", "sólo", "solos", "somos", "son", "soy", "sr", "sra", "sres", 
    "srta", "sta", "sto", "su", "supuesto", "sus", "suya", "suyas", "suyo", "suyos", 
    "t", "tal", "tales", "tambien", "también", "tampoco", "tan", "tanta", "tantas", 
    "tanto", "tantos", "te", "ti", "tí", "toda", "todas", "todavia", "todavía", 
    "todo", "todos", "tras", "través", "tres", "tu", "tú", "tus", "tuya", "tuyas", 
    "tuyo", "tuyos", "u", "ú", "ud", "uds", "un", "una", "unas", "uno", "unos", 
    "usted", "ustedes", "v", "va", "van", "vd", "vds", "veces", "ver", "vez", 
    "vosotras", "vosotros", "voy", "vuestra", "vuestras", "vuestro", "vuestros", 
    "w", "x", "y", "ya", "yo", "z"
}


def filtrar_palabras_significativas(texto):
    """Extrae palabras significativas de un texto (sin stopwords)"""
    palabras = re.findall(r"\b[a-záéíóúüñ]+\b", texto.lower())
    return [p for p in palabras if p not in STOPWORDS_ES and len(p) > 2]


def limpieza_profunda_ocr(texto):
    """
    Realiza una limpieza exhaustiva de texto proveniente de OCR.
    Versión HESIOX v2.0: Unifica lógica de crónicas medievales y prensa moderna.
    """
    if not texto:
        return ""

    # 1. ELIMINAR RUIDO DE OCR (Ghosting y metadatos de escaneo)
    patrones_basura = [
        r'\d+\s+Viajes', r'por\s+España\.?\s+\d*', 
        r'[\^\|~¬\\{}]', r'WM\s+Pl', r'"{2,}', r'\.{2,}',
        r'\s\d+\s(?=\n|$)', # Números sueltos al final de línea
        r'[-_]{2,}', r'[=]{2,}', # Líneas divisorias de guiones o iguales
        r'\[\s*\d+\s*\]', # Referencias a pie de página [1]
        r'https?://\S+', # URLs accidentales
    ]
    for patron in patrones_basura:
        texto = re.sub(patron, '', texto, flags=re.IGNORECASE)

    # 2. RECONSTRUCCIÓN DE LÉXICO (De-hyphenation)
    # Soporta guiones, guiones largos (en/em dash) y otros caracteres similares de OCR
    hyphens = r'[-\u2010-\u2015\u00ad\u2043/]'
    letras = r'[a-zA-ZáéíóúÁÉÍÓÚñÑ]'
    
    # Une palabras cortadas al final de la línea: "bue- \n na" -> "buena"
    texto = re.sub(fr'({letras}){hyphens}\s*\n\s*({letras})', r'\1\2', texto)
    
    # Une palabras cortadas por guion en la misma línea con cualquier espaciado: "tie- ne", "tie -ne", "tie - ne"
    # Solo si el primer fragmento no es una palabra corta que podría ser legítima (ej: "de-", "la-") 
    # proactivamente unimos si parece fragmento técnico.
    texto = re.sub(fr'(\b{letras}+)\s*{hyphens}\s+({letras}+\b)', r'\1\2', texto)
    texto = re.sub(fr'(\b{letras}+)\s+{hyphens}\s*({letras}+\b)', r'\1\2', texto)
    
    # Caso específico del usuario: "Arzo- bispo", "Infan- tado", "tie- ne"
    # Unimos cualquier letra + guion + espacio(s) + letra
    texto = re.sub(fr'({letras}){hyphens}\s+({letras})', r'\1\2', texto)

    # 3. UNIFICACIÓN DE LÍNEAS
    texto = re.sub(r'\n\s*\n', '[[PARRAFO]]', texto)
    texto = texto.replace('\n', ' ')
    texto = texto.replace('[[PARRAFO]]', '\n\n')

    # 4. NORMALIZACIÓN DE ESPACIOS Y PUNTUACIÓN
    texto = re.sub(r'\s+', ' ', texto)
    texto = re.sub(r'\s+([.,;:])', r'\1', texto)
    # Asegurar espacio después de puntuación si falta
    texto = re.sub(r'([.,;:])([a-zA-ZáéíóúÁÉÍÓÚñÑ])', r'\1 \2', texto)

    # 5. ESTRUCTURACIÓN SEMÁNTICA (Párrafos inteligentes)
    texto = texto.replace(" ítem", "\n\nítem")
    texto = re.sub(r'\. ([A-ZÁÉÍÓÚÑ])', r'.\n\n\1', texto)

    # 6. CORRECCIONES DE ERRORES OCR FRECUENTES (Diccionario extendido con Regex)
    reemplazos_manuales = {
        r'seííora': 'señora',
        r'seííoras': 'señoras',
        r'\btn\s': 'en ',
        r'ia vieja': 'la vieja',
        r'\sde-\s': ' de ',
        r'\bl-': ' la',
        r'\be-': ' el',
        r'\bqne\b': 'que',
        r'\bdcl\b': 'del',
        r'\beon\b': 'con',
        r'\bporqne\b': 'porque',
        r'\btado\b': 'todo',
        r'\bsn\b': 'su',
        r'\bsns\b': 'sus',
    }
    for error_pat, fix in reemplazos_manuales.items():
        texto = re.sub(error_pat, fix, texto, flags=re.IGNORECASE)

    return texto.strip()

def clean_location_name(name):
    if not name: return ""
    import re
    prefijos = [
        r'^á\s+', r'^a\s+', r'^en\s+', r'^de\s+', r'^desde\s+', 
        r'^hasta\s+', r'^hacia\s+', r'^por\s+'
    ]
    cleaned = name.strip()
    for p in prefijos:
        cleaned = re.sub(p, '', cleaned, flags=re.IGNORECASE).strip()
    if cleaned and cleaned[0].islower():
        cleaned = cleaned[0].upper() + cleaned[1:]
    return cleaned