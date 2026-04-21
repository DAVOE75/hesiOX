import os
import pandas as pd

# ===============================
# Control de dependencias opcionales
# ===============================
try:
    import plotly.express as px
    import plotly.io as pio
except ImportError as e:
    raise RuntimeError(
        "Falta una dependencia para generar gráficos con Plotly. "
        "Instálala con: pip install plotly kaleido"
    ) from e


def generar_graficos(df: pd.DataFrame, output_dir: str = "outputs") -> dict:
    """
    Genera gráficos descriptivos (edades, sexo, regiones).
    Guarda PNG/HTML en output_dir y devuelve figuras para usarlas en Streamlit.

    Parámetros
    ----------
    df : pd.DataFrame
        DataFrame con columnas opcionales: 'edad', 'sexo', 'region'.
    output_dir : str
        Carpeta donde se guardarán los gráficos.

    Devuelve
    --------
    dict
        Diccionario con objetos de figura de Plotly.
    """
    os.makedirs(output_dir, exist_ok=True)
    figs = {}

    # =====================
    # 1. Histograma de edades
    # =====================
    if "edad" in df.columns:
        fig_edad = px.histogram(
            df, x="edad", nbins=20,
            title="Distribución de Edades",
            template="simple_white"
        )
        if df["edad"].notna().sum() > 0:
            media_edad = df["edad"].mean()
            fig_edad.add_vline(
                x=media_edad,
                line_dash="dash",
                line_color="red",
                annotation_text=f"Media: {media_edad:.1f}",
                annotation_position="top left"
            )
        fig_edad.write_html(os.path.join(output_dir, "edad_histograma.html"))
        try:
            pio.write_image(
                fig_edad,
                os.path.join(output_dir, "edad_histograma.png"),
                width=800, height=500
            )
        except ValueError:
            # Kaleido no instalado o mal configurado
            print("⚠️ No se pudo exportar 'edad_histograma.png'. "
                  "Instala 'kaleido' con: pip install kaleido")
        figs["edad"] = fig_edad

    # =====================
    # 2. Circular de sexos
    # =====================
    if "sexo" in df.columns:
        sexo_counts = df["sexo"].value_counts().reset_index()
        sexo_counts.columns = ["Sexo", "Cantidad"]

        fig_sexo = px.pie(
            sexo_counts, names="Sexo", values="Cantidad",
            title="Distribución por Sexo",
            template="simple_white", hole=0.3
        )
        fig_sexo.update_traces(textposition="inside", textinfo="percent+label")
        fig_sexo.write_html(os.path.join(output_dir, "sexo_pie.html"))
        try:
            pio.write_image(
                fig_sexo,
                os.path.join(output_dir, "sexo_pie.png"),
                width=600, height=500
            )
        except ValueError:
            print("⚠️ No se pudo exportar 'sexo_pie.png'. "
                  "Instala 'kaleido' con: pip install kaleido")
        figs["sexo"] = fig_sexo

    # =====================
    # 3. Top 10 regiones
    # =====================
    if "region" in df.columns:
        region_counts = df["region"].value_counts(normalize=True).head(10) * 100
        region_counts = region_counts.reset_index()
        region_counts.columns = ["Región", "Porcentaje"]

        fig_region = px.bar(
            region_counts, x="Porcentaje", y="Región", orientation="h",
            title="Top 10 Regiones de Pasajeros",
            template="simple_white", text="Porcentaje"
        )
        fig_region.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
        fig_region.write_html(os.path.join(output_dir, "top_regiones.html"))
        try:
            pio.write_image(
                fig_region,
                os.path.join(output_dir, "top_regiones.png"),
                width=800, height=500
            )
        except ValueError:
            print("⚠️ No se pudo exportar 'top_regiones.png'. "
                  "Instala 'kaleido' con: pip install kaleido")
        figs["regiones"] = fig_region

    return figs
