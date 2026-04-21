def cargar_y_preprocesar(path_excel: str):
    pass
import pandas as pd

def limpiar_datos(df: pd.DataFrame) -> pd.DataFrame:
    """
    Limpieza y normalización de los datos del Sirio.
    - Normaliza las columnas de texto (espacios, mayúsculas/minúsculas).
    - Convierte las fechas a formato datetime.
    - Elimina duplicados.
    """
    df = df.copy()

    # Normalizar nombres de columnas
    df.columns = [col.strip().lower() for col in df.columns]

    # Convertir fechas si existen
    fecha_cols = [c for c in df.columns if "fecha" in c]
    for col in fecha_cols:
        df[col] = pd.to_datetime(df[col], errors="coerce")

    # Eliminar duplicados
    df = df.drop_duplicates()

    return df
