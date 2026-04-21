import pandas as pd
import plotly.express as px
import folium
from folium.plugins import HeatMap, MarkerCluster, TimestampedGeoJson
from branca.colormap import LinearColormap

from sirio.utils.geo import obtener_coord


def generar_mapa_coropletas(df, columna_valor="conteo", titulo="Distribución Geográfica"):
    if df.empty:
        return None

    agrupaciones = ['municipio', 'provincia', 'region', 'pais']
    agrupacion = next((a for a in agrupaciones if a in df.columns and df[a].notna().any()), None)
    if not agrupacion:
        return None

    if columna_valor == "conteo":
        datos = df.groupby(agrupacion).size().reset_index(name="valor")
    else:
        datos = df.groupby(agrupacion)[columna_valor].mean().reset_index(name="valor")

    datos["coords"] = datos[agrupacion].map(obtener_coord)
    datos[["lat", "lon"]] = pd.DataFrame(datos["coords"].tolist(), index=datos.index)

    if datos.empty:
        return None

    fig = px.scatter_mapbox(
        datos, lat="lat", lon="lon", size="valor", color="valor",
        hover_name=agrupacion, size_max=50, color_continuous_scale="Viridis",
        title=f"{titulo} - Por {agrupacion}", zoom=5, height=600
    )
    fig.update_layout(mapbox_style="open-street-map", margin={"r": 0, "t": 50, "l": 0, "b": 0})
    return fig


def generar_heatmap(df, columna_agrupacion="municipio"):
    if df.empty or columna_agrupacion not in df.columns:
        return None

    datos = df[columna_agrupacion].value_counts().reset_index()
    datos.columns = [columna_agrupacion, "count"]
    datos["coords"] = datos[columna_agrupacion].map(obtener_coord)
    datos[["lat", "lon"]] = pd.DataFrame(datos["coords"].tolist(), index=datos.index)

    if datos.empty:
        return None

    center = [datos["lat"].mean(), datos["lon"].mean()]
    m = folium.Map(location=center, zoom_start=5)
    heat_data = [[row["lat"], row["lon"]] for _, row in datos.iterrows() for _ in range(min(row["count"], 10))]
    HeatMap(heat_data, radius=15, blur=10).add_to(m)
    return m


def generar_mapa_cluster(df, columna_agrupacion="municipio"):
    """
    Genera un mapa con clusters de pasajeros.
    Al hacer clic, muestra 'Nombre Apellidos' (si existen esas columnas).
    Si no existen, muestra el valor de la columna de agrupación (p. ej., municipio).
    """

    if df.empty or columna_agrupacion not in df.columns:
        return None

    # Helper para armar el nombre completo
    def _nombre_completo(row) -> str:
        candidatos_nombre = ["nombre", "Nombre", "nombres", "first_name", "given_name"]
        candidatos_apellidos = ["apellidos", "apellido", "Apellidos", "last_name", "surname"]

        def _pick(cols):
            for c in cols:
                if c in row and pd.notna(row[c]) and str(row[c]).strip():
                    return str(row[c]).strip()
            return ""

        nombre = _pick(candidatos_nombre)
        apell = _pick(candidatos_apellidos)

        if nombre or apell:
            return f"{nombre} {apell}".strip()

        # fallback: nombre completo en una sola columna
        for c in ["nombre_completo", "Nombre completo", "full_name", "Full Name"]:
            if c in row and pd.notna(row[c]) and str(row[c]).strip():
                return str(row[c]).strip()

        return ""

    # Calcular centro aproximado
    coords_validas = []
    for _, row in df.iterrows():
        ubic = row.get(columna_agrupacion)
        if pd.notna(ubic):
            c = obtener_coord(str(ubic))
            if c:
                coords_validas.append(c)

    if not coords_validas:
        return None

    center = [
        sum(c[0] for c in coords_validas) / len(coords_validas),
        sum(c[1] for c in coords_validas) / len(coords_validas)
    ]

    m = folium.Map(location=center, zoom_start=5)
    cluster = MarkerCluster().add_to(m)

    for _, row in df.iterrows():
        ubic = row.get(columna_agrupacion)
        if not pd.notna(ubic):
            continue

        coord = obtener_coord(str(ubic))
        if not coord:
            continue

        # Construir popup: Nombre Apellidos + extras
        nombre_completo = _nombre_completo(row)
        popup_title = nombre_completo if nombre_completo else str(ubic)

        extras = []
        for etiqueta, col in [("Edad", "edad"), ("Pasaje", "pasaje"), ("Estado", "estado")]:
            if col in df.columns and pd.notna(row.get(col)):
                extras.append(f"{etiqueta}: {row[col]}")

        if extras:
            popup_html = f"<b>{popup_title}</b><br>" + "<br>".join(extras)
        else:
            popup_html = f"<b>{popup_title}</b>"

        folium.Marker(
            coord,
            popup=folium.Popup(popup_html, max_width=300),
            tooltip=str(ubic)  # tooltip al pasar el ratón
        ).add_to(cluster)

    return m


def generar_mapa_graduado(df, columna_valor="conteo", columna_agrupacion="municipio"):
    if df.empty or columna_agrupacion not in df.columns:
        return None

    if columna_valor == "conteo":
        datos = df.groupby(columna_agrupacion).size().reset_index(name="valor")
    elif columna_valor in df.columns:
        datos = df.groupby(columna_agrupacion)[columna_valor].mean().reset_index(name="valor")
    else:
        return None

    datos["coords"] = datos[columna_agrupacion].map(obtener_coord)
    datos[["lat", "lon"]] = pd.DataFrame(datos["coords"].tolist(), index=datos.index)

    if datos.empty:
        return None

    center = [datos["lat"].mean(), datos["lon"].mean()]
    m = folium.Map(location=center, zoom_start=5)
    colormap = LinearColormap(['green', 'yellow', 'red'], vmin=datos["valor"].min(), vmax=datos["valor"].max())

    for _, row in datos.iterrows():
        folium.Circle(
            [row["lat"], row["lon"]],
            radius=min(row["valor"] * 2000, 50000),
            color=colormap(row["valor"]),
            fill=True
        ).add_to(m)

    colormap.add_to(m)
    return m


def generar_mapa(df_pasajero):
    if df_pasajero.empty:
        return folium.Map(location=[40.0, -3.0], zoom_start=4)

    features = []
    for _, row in df_pasajero.iterrows():
        if pd.notna(row.get("puerto_embarque")):
            ciudad = row["puerto_embarque"]
            coord = obtener_coord(ciudad)
            features.append({
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [coord[1], coord[0]]},
                "properties": {"time": "1906-08-04", "popup": ciudad, "icon": "circle"}
            })

    geojson = {"type": "FeatureCollection", "features": features}
    m = folium.Map(location=[40.0, -3.0], zoom_start=5)
    TimestampedGeoJson(geojson, period="P30D", add_last_point=True).add_to(m)
    return m
