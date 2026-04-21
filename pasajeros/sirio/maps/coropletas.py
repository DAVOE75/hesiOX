import os
import geopandas as gpd
import folium
import pandas as pd
import branca.colormap as cm   # para el gradiente de colores

BASE_PATH = os.path.dirname(__file__)
DATA_PATH = os.path.join(BASE_PATH, "..", "data")


def cargar_geojson(nivel, pais, debug=True):
    file_map = {
        "España": {
            "Región": "gadm41_ESP_1.json",
            "Provincia": "gadm41_ESP_2.json",
            "Municipio": "gadm41_ESP_3.json",
        },
        "Italia": {
            "Región": "gadm41_ITA_1.json",
            "Provincia": "gadm41_ITA_2.json",
            "Municipio": "gadm41_ITA_3.json",
        },
        "España + Italia": {
            "Región": ["gadm41_ESP_1.json", "gadm41_ITA_1.json"],
            "Provincia": ["gadm41_ESP_2.json", "gadm41_ITA_2.json"],
            "Municipio": ["gadm41_ESP_3.json", "gadm41_ITA_3.json"],
        },
    }

    if pais not in file_map or nivel not in file_map[pais]:
        raise ValueError(f"Nivel {nivel} no soportado para {pais}")

    filepaths = file_map[pais][nivel]
    if isinstance(filepaths, str):
        filepaths = [filepaths]

    geos = []
    for f in filepaths:
        filepath = os.path.join(DATA_PATH, f)
        if not os.path.exists(filepath):
            raise FileNotFoundError(filepath)
        geo = gpd.read_file(filepath)
        if geo.crs is None:
            geo = geo.set_crs("EPSG:4326")
        else:
            geo = geo.to_crs("EPSG:4326")
        geos.append(geo)

    geo = gpd.GeoDataFrame(pd.concat(geos, ignore_index=True))

    # Mapeo de columnas de nombre
    col_map = {
        "España": {"región": "NAME_1", "provincia": "NAME_2", "municipio": "NAME_3"},
        "Italia": {"región": "NAME_1", "provincia": "NAME_2", "municipio": "NAME_3"},
        "España + Italia": {"región": "NAME_1", "provincia": "NAME_2", "municipio": "NAME_3"},
    }

    geo.columns = [c.lower() for c in geo.columns]
    nivel_lower = nivel.lower()
    geo_name_col = col_map[pais][nivel_lower].lower()

    if geo_name_col not in geo.columns:
        raise ValueError(
            f"No se encontró la columna {geo_name_col} en {filepaths}. Columnas disponibles: {list(geo.columns)}"
        )

    return geo, geo_name_col, nivel_lower


def generar_mapa_coropletas(df, nivel="Región", pais="España"):
    geo, geo_name_col, join_col = cargar_geojson(nivel, pais, debug=True)

    # Normalizar columnas del DataFrame
    df.columns = [c.lower() for c in df.columns]
    join_col = join_col.lower()

    if join_col not in df.columns:
        raise KeyError(
            f"La columna '{join_col}' no existe en el DataFrame. Columnas: {list(df.columns)}"
        )

    datos = df.groupby(join_col).size().reset_index(name="valor")
    geo = geo.merge(datos, left_on=geo_name_col, right_on=join_col, how="left").fillna(0)

    max_val = geo["valor"].max()

    # Crear mapa base sin tiles fijos
    m = folium.Map(location=[42, 12], zoom_start=5, tiles=None)

    # Fondos de mapa disponibles
    folium.TileLayer("OpenStreetMap", name="OpenStreetMap",
                     attr="© OpenStreetMap contributors").add_to(m)
    folium.TileLayer("CartoDB positron", name="CartoDB Claro",
                     attr="© OpenStreetMap contributors & © CARTO").add_to(m)
    folium.TileLayer("CartoDB dark_matter", name="CartoDB Oscuro",
                     attr="© OpenStreetMap contributors & © CARTO").add_to(m)
    folium.TileLayer("Stamen Terrain", name="Terreno",
                     attr="Map tiles by Stamen Design, CC BY 3.0 — Map data © OSM").add_to(m)
    folium.TileLayer("Stamen Toner", name="Blanco y Negro",
                     attr="Map tiles by Stamen Design, CC BY 3.0 — Map data © OSM").add_to(m)
    folium.TileLayer("Stamen Watercolor", name="Acuarela",
                     attr="Map tiles by Stamen Design, CC BY 3.0 — Map data © OSM").add_to(m)
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        name="Satélite",
        attr="Tiles © Esri & contributors"
    ).add_to(m)
    folium.raster_layers.TileLayer(
        tiles="",
        name="Sin fondo",
        attr="Mapa vacío"
    ).add_to(m)

    # Escala de colores azulada
    colormap = cm.LinearColormap(
        colors=["#eff3ff", "#c6dbef", "#9ecae1",
                "#6baed6", "#3182bd", "#08519c"],
        vmin=1, vmax=max_val
    )
    colormap.caption = f"Distribución por {nivel}"
    colormap.add_to(m)

    def style_function(feature):
        val = feature["properties"]["valor"]
        if val == 0:
            return {"fillColor": "rgba(0,0,0,0.2)", "color": "gray", "weight": 0.3, "fillOpacity": 0.2}
        return {"fillColor": colormap(val), "color": "gray", "weight": 0.3, "fillOpacity": 0.7}

    geo_json = folium.GeoJson(
        geo,
        style_function=style_function,
        tooltip=folium.GeoJsonTooltip(
            fields=[geo_name_col, "valor"],
            aliases=["", ""],
            labels=False,
            localize=True,
            sticky=False,
        ),
        name="Coropletas"
    ).add_to(m)

    m.fit_bounds(geo_json.get_bounds())
    folium.LayerControl(collapsed=False, position="topright").add_to(m)

    return m
