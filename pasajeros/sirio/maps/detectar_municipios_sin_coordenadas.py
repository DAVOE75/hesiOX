import pandas as pd

# ===============================
# Control de dependencias opcionales
# ===============================
try:
    from geopy.geocoders import Nominatim
except ImportError as e:
    raise RuntimeError(
        "Falta la librería 'geopy'. Instálala con: pip install geopy"
    ) from e

from sirio.constantes import COORDENADAS_CIUDADES


def detectar_municipios_sin_coordenadas(df, columna="municipio", user_agent="sirio-mapas"):
    """
    Detecta municipios sin coordenadas en el diccionario COORDENADAS_CIUDADES.
    Intenta resolverlos usando geopy (Nominatim).

    Parámetros
    ----------
    df : pd.DataFrame
        DataFrame con una columna de municipios.
    columna : str
        Nombre de la columna con los municipios.
    user_agent : str
        Nombre de la aplicación para Nominatim (recomendado personalizar).

    Devuelve
    --------
    dict
        Diccionario con municipios detectados y sus coordenadas encontradas.
    """
    if df.empty or columna not in df.columns:
        return {}

    municipios = df[columna].dropna().unique()
    sin_coords = [m for m in municipios if m not in COORDENADAS_CIUDADES]

    if not sin_coords:
        return {}

    geolocator = Nominatim(user_agent=user_agent)
    nuevos = {}

    for mun in sin_coords:
        try:
            location = geolocator.geocode(mun)
            if location:
                nuevos[mun] = [location.latitude, location.longitude]
        except Exception as e:
            print(f"⚠️ No se pudo obtener coordenadas para '{mun}': {e}")

    return nuevos
