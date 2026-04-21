import streamlit as st
import pandas as pd
import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import streamlit.components.v1 as components
import plotly.express as px

from sirio.preprocessing import limpiar_datos
from sirio.graphs.generar_graficos import generar_graficos
from sirio.maps.basicos import generar_heatmap, generar_mapa_cluster, generar_mapa_graduado
from sirio.maps.rutas import generar_mapa_rutas
from sirio.maps.flujo import generar_mapa_flujos
from sirio.maps.coropletas import generar_mapa_coropletas
from sirio.graphs.grafo import generar_grafo
from sirio.timeline.timeline import generar_timeline
import unicodedata

def normalizar_columnas(df):
    """Convierte columnas a minúsculas, elimina acentos pero conserva ñ."""
    def clean_text(text):
        text = text.lower()
        text = text.replace("ñ", "ñ")  # mantiene ñ
        text = "".join(
            c for c in unicodedata.normalize("NFD", text)
            if unicodedata.category(c) != "Mn"
        )
        return text

    df.columns = [clean_text(col) for col in df.columns]
    return df

st.set_page_config(page_title="Proyecto Sirio", layout="wide")
OUTPUT_DIR = "sirio/outputs"
os.makedirs(OUTPUT_DIR, exist_ok=True)


# ================================
# Cargar datos con file uploader
# ================================
st.title("🚢 Proyecto Sirio - Análisis de Pasajeros")
st.markdown("Visualización interactiva de datos históricos del naufragio del Sirio.")

uploaded_file = st.file_uploader("📂 Sube tu archivo de datos (CSV o Excel)", type=["csv", "xlsx"])

if uploaded_file is not None:
    # Detectar formato y cargar
    try:
        if uploaded_file.name.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        elif uploaded_file.name.endswith(".xlsx"):
            df = pd.read_excel(uploaded_file)
        else:
            st.error("Formato de archivo no soportado. Usa CSV o Excel.")
            st.stop()
    except Exception as e:
        st.error(f"❌ Error al leer el archivo: {e}")
        st.stop()

    # Preprocesar
    df = limpiar_datos(df)

    # Sidebar
    st.sidebar.header("Opciones")
    seccion = st.sidebar.radio(
        "Selecciona una sección:",
        ["Gráficos descriptivos", "Mapas", "Grafo", "Timeline"]
    )

    # ================================
    # Gráficos descriptivos
    # ================================
    if seccion == "Gráficos descriptivos":
        st.subheader("📊 Gráficos Descriptivos")
        figs = generar_graficos(df, output_dir=OUTPUT_DIR)

        if "edad" in figs:
            st.plotly_chart(figs["edad"], use_container_width=True)
        if "sexo" in figs:
            st.plotly_chart(figs["sexo"], use_container_width=True)
        if "regiones" in figs:
            st.plotly_chart(figs["regiones"], use_container_width=True)

    # ================================
    # Mapas
    # ================================
    elif seccion == "Mapas":
        st.subheader("🗺 Mapas")

        # País y nivel en la misma fila
        col1, col2 = st.columns(2)
        with col1:
            pais = st.selectbox("🌍 Selecciona país", ["España + Italia", "España", "Italia"], index=0)
        with col2:
            nivel = st.selectbox("📌 Selecciona nivel", ["Región", "Provincia", "Municipio"], index=0)
        
        # =========================
        # Mapa coroplético principal
        # =========================
        try:
            mapa = generar_mapa_coropletas(df, nivel=nivel, pais=pais)
            st.components.v1.html(mapa._repr_html_(), height=800)
        except Exception as e:
            st.error(f"⚠️ No se pudo generar el mapa coroplético: {e}")

        # =========================
        # Selección de columna ubicación + filtros dinámicos
        # =========================
        st.markdown("### 🔎 Filtros dinámicos")
        default_index = 0
        if "municipio" in df.columns:
            try:
                default_index = df.columns.get_loc("municipio")
            except Exception:
                default_index = 0

        col_mapa = st.selectbox("📌 Selecciona la columna de ubicación", df.columns, index=default_index)

        activar_filtros = st.checkbox("🎛️ Activar filtros dinámicos", value=False)
        df_filtrado = df.copy()

        if activar_filtros:
            col1, col2 = st.columns(2)

            with col1:
                if "sexo" in df.columns:
                    sexos = st.multiselect("Sexo", options=df["sexo"].dropna().unique())
                    if sexos:
                        df_filtrado = df_filtrado[df_filtrado["sexo"].isin(sexos)]

                if "provincia" in df.columns:
                    provincias = st.multiselect("Provincia", options=df["provincia"].dropna().unique())
                    if provincias:
                        df_filtrado = df_filtrado[df_filtrado["provincia"].isin(provincias)]

                if "pais" in df.columns:
                    paises = st.multiselect("País", options=df["pais"].dropna().unique())
                    if paises:
                        df_filtrado = df_filtrado[df_filtrado["pais"].isin(paises)]

            with col2:
                if "estado" in df.columns:
                    estados = st.multiselect("Estado", options=df["estado"].dropna().unique())
                    if estados:
                        df_filtrado = df_filtrado[df_filtrado["estado"].isin(estados)]

                if "pasaje" in df.columns:
                    pasajes = st.multiselect("Tipo de pasaje", options=df["pasaje"].dropna().unique())
                    if pasajes:
                        df_filtrado = df_filtrado[df_filtrado["pasaje"].isin(pasajes)]

        # =========================
        # Segundo bloque de mapas (heatmap + opciones)
        # =========================
        st.markdown("### 🔥 Otros mapas")

        tipo_mapa = st.selectbox("Selecciona el tipo de mapa", ["Heatmap", "Cluster", "Graduado", "Flujos"], index=0)

        mapa2 = None
        if tipo_mapa == "Heatmap":
            mapa2 = generar_heatmap(df_filtrado, columna_agrupacion=col_mapa)
        elif tipo_mapa == "Cluster":
            mapa2 = generar_mapa_cluster(df_filtrado, columna_agrupacion=col_mapa)
        elif tipo_mapa == "Graduado":
            mapa2 = generar_mapa_graduado(df_filtrado, columna_agrupacion=col_mapa)
        elif tipo_mapa == "Flujos":
            mapa2 = generar_mapa_flujos(df_filtrado, origen_col="municipio", destino_col="ciudad_destino_final")

        if mapa2 is not None:
            st.components.v1.html(mapa2._repr_html_(), height=600)
        else:
            st.info("⚠️ No se pudo generar el mapa. Verifica los datos y las coordenadas.")

    # ================================
    # Grafo
    # ================================
    elif seccion == "Grafo":
        st.subheader("🔗 Grafo de Relaciones")

        col_origen = st.selectbox("Nodo origen", df.columns, index=0)
        col_destino = st.selectbox("Nodo destino", df.columns, index=1)

        grafo_path = os.path.join(OUTPUT_DIR, "grafo.html")
        generar_grafo(df, origen=col_origen, destino=col_destino, output_file=grafo_path)

        if os.path.exists(grafo_path):
            with open(grafo_path, "r", encoding="utf-8") as f:
                st.components.v1.html(f.read(), height=600)
        else:
            st.warning("⚠️ No se pudo generar el grafo. Revisa las columnas seleccionadas.")

    # ================================
    # Timeline
    # ================================
    elif seccion == "Timeline":
        st.subheader("⏳ Línea de Tiempo")

        col_fecha = st.selectbox("📅 Columna de fecha", df.columns, index=0)
        col_evento = st.selectbox("📌 Columna de evento/categoría", df.columns, index=1)

        t = generar_timeline(df, fecha_col=col_fecha, categoria_col=col_evento)
        if t:
            st.plotly_chart(t, use_container_width=True)
        else:
            st.warning("⚠️ No se pudo generar el timeline. Verifica la columna de fechas.")

# ================================
# Botón de cierre en el sidebar
# ================================
st.sidebar.markdown("---")
if st.sidebar.button("❌ Cerrar aplicación"):
    st.sidebar.warning("Cerrando aplicación...")

    close_script = """
        <script>
        window.open('', '_self'); window.close();
        </script>
    """
    components.html(close_script, height=0, width=0)
    os._exit(0)
