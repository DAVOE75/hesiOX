import folium
from sirio.utils.geo import obtener_coord

def generar_mapa_comparativo(df, col1="puerto_embarque", col2="destino"):
    if df.empty or col1 not in df.columns or col2 not in df.columns:
        return None

    coords1 = [obtener_coord(val) for val in df[col1].dropna()]
    coords2 = [obtener_coord(val) for val in df[col2].dropna()]

    if not coords1 or not coords2:
        return None

    m = folium.Map(location=[40.0, -3.0], zoom_start=4)

    for c1, c2 in zip(coords1, coords2):
        folium.PolyLine([c1, c2], color="blue", weight=2).add_to(m)

    return m
