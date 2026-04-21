import pandas as pd

# ===============================
# Control de dependencias opcionales
# ===============================
try:
    import folium
except ImportError as e:
    raise RuntimeError(
        "Falta la librería 'folium'. Instálala con: pip install folium"
    ) from e

try:
    from geopy.distance import geodesic
except ImportError as e:
    raise RuntimeError(
        "Falta la librería 'geopy'. Instálala con: pip install geopy"
    ) from e

from sirio.constantes import COORDENADAS_CIUDADES   # ✅


def generar_mapa_rutas(df, origen_col="puerto_embarque", destino_col="destino"):
    """
    Genera un mapa de rutas marítimas entre origen y destino.
    Cada ruta se representa con una línea geodésica.
    """
    if df.empty or origen_col not in df.columns or destino_col not in df.columns:
        return None

    rutas = []
    for _, row in df.iterrows():
        origen = row.get(origen_col)
        destino = row.get(destino_col)
        if pd.notna(origen) and pd.notna(destino):
            if origen in COORDENADAS_CIUDADES and destino in COORDENADAS_CIUDADES:
                rutas.append((COORDENADAS_CIUDADES[origen], COORDENADAS_CIUDADES[destino]))

    if not rutas:
        return None

    # Calcular centro aproximado
    coords = [p for ruta in rutas for p in ruta]
    center = [sum(c[0] for c in coords) / len(coords),
              sum(c[1] for c in coords) / len(coords)]

    m = folium.Map(location=center, zoom_start=4)

    for origen, destino in rutas:
        distancia = geodesic(origen, destino).km
        folium.PolyLine([origen, destino], color="blue", weight=2.5,
                        tooltip=f"Distancia: {distancia:.1f} km").add_to(m)

    return m
