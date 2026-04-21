# sirio/maps/flujo.py
import folium
import pandas as pd

# 👇 Importa la función directamente del módulo geo
from sirio.utils.geo import obtener_coord


def generar_mapa_flujos(df, origen_col="municipio", destino_col="ciudad_destino_final"):
    """
    Genera un mapa de flujos básicos origen → destino.
    - Origen: municipio
    - Destino: ciudad_destino_final; si no hay y el estado no es 'superviviente', usamos 'Lugar hundimiento' (~Nápoles)
    """
    if df.empty or origen_col not in df.columns:
        return None

    rutas = []
    for _, row in df.iterrows():
        origen = row.get(origen_col)
        destino = row.get(destino_col)

        # Si no hay destino y no es superviviente, marcamos hundimiento
        if pd.isna(destino) and row.get("estado") != "superviviente":
            destino = "Lugar hundimiento"

        if pd.notna(origen) and pd.notna(destino):
            o = obtener_coord(str(origen))
            d = obtener_coord(str(destino if destino != "Lugar hundimiento" else "Nápoles"))  # fallback razonable
            if o and d:
                rutas.append((o, d))

    if not rutas:
        return None

    # Centro del mapa
    puntos = [p for par in rutas for p in par]
    center_lat = sum(p[0] for p in puntos) / len(puntos)
    center_lon = sum(p[1] for p in puntos) / len(puntos)
    m = folium.Map(location=[center_lat, center_lon], zoom_start=5, tiles="CartoDB positron")

    # Dibujar flujos
    for o, d in rutas:
        folium.PolyLine([o, d], color="blue", weight=2, opacity=0.6).add_to(m)

    return m

