import pandas as pd

# ===============================
# Control de dependencias opcionales
# ===============================
try:
    import plotly.express as px
except ImportError as e:
    raise RuntimeError(
        "Falta la librería 'plotly'. Instálala con: pip install plotly"
    ) from e


def generar_timeline(df, fecha_col="fecha", categoria_col="evento", titulo="Línea de tiempo de eventos"):
    """
    Genera una línea de tiempo interactiva usando Plotly.

    Parámetros
    ----------
    df : pd.DataFrame
        DataFrame con al menos una columna de fechas y otra de categorías/eventos.
    fecha_col : str
        Nombre de la columna con las fechas (formato reconocible por pandas).
    categoria_col : str
        Nombre de la columna con la categoría o evento.
    titulo : str
        Título de la visualización.

    Devuelve
    --------
    plotly.graph_objects.Figure
        Figura interactiva de Plotly.
    """
    if df.empty or fecha_col not in df.columns or categoria_col not in df.columns:
        return None

    # Asegurar que la columna de fechas esté en datetime
    df = df.copy()
    df[fecha_col] = pd.to_datetime(df[fecha_col], errors="coerce")
    df = df.dropna(subset=[fecha_col])

    if df.empty:
        return None

    # Ordenar por fecha
    df = df.sort_values(by=fecha_col)

    # Crear scatter plot para timeline
    fig = px.scatter(
        df,
        x=fecha_col,
        y=[0] * len(df),  # Línea base
        text=categoria_col,
        title=titulo,
        labels={fecha_col: "Fecha"},
        height=400
    )

    # Ajustar diseño
    fig.update_traces(marker=dict(size=12, color="blue"), textposition="top center")
    fig.update_yaxes(visible=False, showticklabels=False)
    fig.update_layout(
        xaxis=dict(showline=True, showgrid=True),
        margin={"r": 0, "t": 50, "l": 0, "b": 0}
    )

    return fig
