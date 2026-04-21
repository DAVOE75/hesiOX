import streamlit as st
import pandas as pd

# Importar gráficas estadísticas
from sirio.graphs import (
    generar_histograma_edades,
    generar_pie_sexo,
    generar_top_regiones,
    generar_grafo
)

# Importar mapas
from sirio.maps import (
    generar_mapa_coropletas,
    generar_heatmap,
    generar_mapa_cluster,
    generar_mapa_graduado,
    generar_mapa,
    generar_mapa_rutas,
    generar_mapa_comparativo
)

st.set_page_config(page_title="📊 Dashboard Sirio", layout="wide")
st.title("🚢 Análisis del Naufragio del Sirio")

# ======================
# Subida de datos
# ======================
uploaded_file = st.file_uploader("Sube un archivo CSV", type=["csv"])

if uploaded_file:
    df = pd.read_csv(uploaded_file)

    st.success("✅ Datos cargados correctamente")

    # ======================
    # Sección Estadística
    # ======================
    st.header("📊 Estadísticas de Pasajeros")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Distribución de Edades")
        fig_edad = generar_histograma_edades(df)
        st.plotly_chart(fig_edad, use_container_width=True)

    with col2:
        st.subheader("Distribución por Sexo")
        fig_sexo = generar_pie_sexo(df)
        st.plotly_chart(fig_sexo, use_container_width=True)

    st.subheader("Top 10 Regiones")
    fig_regiones = generar_top_regiones(df)
    st.plotly_chart(fig_regiones, use_container_width=True)

    # ======================
    # Sección Geográfica
    # ======================
    st.header("🗺️ Análisis Geográfico")

    tab1, tab2, tab3 = st.tabs(["Coropletas", "Heatmap", "Clusters"])

    with tab1:
        fig_coropletas = generar_mapa_coropletas(df)
        if fig_coropletas:
            st.plotly_chart(fig_coropletas, use_container_width=True)

    with tab2:
        mapa_heat = generar_heatmap(df)
        if mapa_heat:
            st.components.v1.html(mapa_heat._repr_html_(), height=500)

    with tab3:
        mapa_cluster = generar_mapa_cluster(df)
        if mapa_cluster:
            st.components.v1.html(mapa_cluster._repr_html_(), height=500)

    st.subheader("🛣️ Rutas de Viaje")
    mapa_rutas = generar_mapa_rutas(df)
    if mapa_rutas:
        st.components.v1.html(mapa_rutas._repr_html_(), height=500)

    # ======================
    # Sección Redes
    # ======================
    st.header("🌐 Grafo de Pasajeros")

    grafo = generar_grafo(df)

    # ✅ Guardar como HTML y embeberlo en Streamlit
    grafo_path = "grafo_temp.html"
    grafo.write_html(grafo_path)

    with open(grafo_path, "r", encoding="utf-8") as f:
        html_grafo = f.read()

    st.components.v1.html(html_grafo, height=600, scrolling=True)

else:
    st.warning("⚠️ Sube un archivo CSV para comenzar.")
