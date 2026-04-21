"""
sirio/utils/geo.py
Utilidades de geocodificación para mapas.
"""

import unicodedata
import time
import logging
from functools import lru_cache

try:
    from geopy.geocoders import Nominatim
except ImportError as e:
    raise RuntimeError(
        "Falta la librería 'geopy'. Instálala con: pip install geopy"
    ) from e

# 👇 IMPORTA SIEMPRE DESDE constantes.py EN EL RAÍZ DE SIRIO
from sirio.constantes import COORDENADAS_CIUDADES

# Inicializar geolocalizador global
_geolocator = Nominatim(user_agent="sirio-mapas", timeout=10)

def _normalizar(texto: str) -> str:
    """Normaliza texto quitando tildes y pasando a minúsculas."""
    if not isinstance(texto, str):
        return ""
    texto = texto.strip().lower()
    texto = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in texto if not unicodedata.combining(c))

@lru_cache(maxsize=500)
def obtener_coord(nombre: str):
    """
    Devuelve coordenadas (lat, lon) de un lugar.

    Orden de búsqueda:
    1. Diccionario local COORDENADAS_CIUDADES.
    2. Geopy (Nominatim).
    3. Fallback a Madrid (40.0, -3.0).
    """
    if not isinstance(nombre, str) or not nombre.strip():
        return (40.0, -3.0)

    nombre_norm = _normalizar(nombre)

    # 1. Buscar en diccionario local
    for key, coord in COORDENADAS_CIUDADES.items():
        if _normalizar(key) == nombre_norm:
            return coord

    # 2. Intentar con geopy
    try:
        location = _geolocator.geocode(nombre)
        if location:
            time.sleep(1)  # respetar límite
            return (location.latitude, location.longitude)
    except Exception as e:
        logging.warning(f"⚠️ Geocoding falló para '{nombre}': {e}")

    # 3. Fallback
    return (40.0, -3.0)
