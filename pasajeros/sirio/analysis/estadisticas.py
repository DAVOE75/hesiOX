import pandas as pd
import logging

logger = logging.getLogger(__name__)

def generar_resumen_estadistico(df: pd.DataFrame) -> dict:
    """
    Genera un resumen estadístico general del dataset.
    Incluye conteos, distribuciones y estadísticas básicas de edad y fechas.
    """
    try:
        resumen = {}
        resumen['total_pasajeros'] = len(df)
        resumen['columnas_disponibles'] = list(df.columns)

        # Columnas categóricas más comunes
        columnas_categoricas = [
            'municipio', 'provincia', 'region', 'pais', 'sexo',
            'pasaje', 'estado', 'hospedaje_cartagena', 'puerto_embarque'
        ]

        for col in columnas_categoricas:
            if col in df.columns:
                resumen[f'{col}_unicos'] = df[col].nunique()
                resumen[f'{col}_distribucion'] = (
                    df[col].value_counts().head(10).to_dict()
                )

        # Estadísticas de edad
        if 'edad' in df.columns:
            edad_stats = df['edad'].describe()
            resumen['edad_promedio'] = float(edad_stats['mean'])
            resumen['edad_minima'] = float(edad_stats['min'])
            resumen['edad_maxima'] = float(edad_stats['max'])
            resumen['edad_mediana'] = float(edad_stats['50%'])

        # Estadísticas de fechas
        fechas_columns = [
            'fecha_hundimiento', 'fecha_destino_final',
            'fecha_llegada_cartagena', 'fecha_salida_cartagena'
        ]
        for fecha_col in fechas_columns:
            if fecha_col in df.columns:
                fechas_validas = df[fecha_col].dropna()
                if len(fechas_validas) > 0:
                    resumen[f'{fecha_col}_primera'] = fechas_validas.min().strftime('%Y-%m-%d')
                    resumen[f'{fecha_col}_ultima'] = fechas_validas.max().strftime('%Y-%m-%d')

        return resumen

    except Exception as e:
        logger.error(f"Error en generar_resumen_estadistico: {e}")
        return {}

def validar_datos_pasajero(df_pasajero: pd.DataFrame) -> dict:
    """
    Valida los datos de un pasajero individual.
    Comprueba nombre, fechas y coherencia del estado.
    """
    try:
        if df_pasajero.empty:
            return {"estado": "vacio", "errores": ["No hay datos del pasajero"]}

        pasajero = df_pasajero.iloc[0]
        errores = []
        advertencias = []

        if pd.isna(pasajero.get('nombre')) or pd.isna(pasajero.get('apellidos')):
            errores.append("Faltan nombre o apellidos")

        fechas = []
        if pd.notna(pasajero.get('fecha_hundimiento')):
            fechas.append(('Hundimiento', pasajero['fecha_hundimiento']))
        if pd.notna(pasajero.get('fecha_llegada_cartagena')):
            fechas.append(('Llegada Cartagena', pasajero['fecha_llegada_cartagena']))
        if pd.notna(pasajero.get('fecha_salida_cartagena')):
            fechas.append(('Salida Cartagena', pasajero['fecha_salida_cartagena']))
        if pd.notna(pasajero.get('fecha_destino_final')):
            fechas.append(('Destino Final', pasajero['fecha_destino_final']))

        fechas_ordenadas = sorted(fechas, key=lambda x: x[1])
        for i in range(len(fechas_ordenadas) - 1):
            if fechas_ordenadas[i][1] > fechas_ordenadas[i + 1][1]:
                advertencias.append(
                    f"Posible incoherencia temporal: {fechas_ordenadas[i][0]} después de {fechas_ordenadas[i + 1][0]}"
                )

        estado = pasajero.get('estado')
        if estado == "superviviente" and pd.notna(pasajero.get('fecha_hundimiento')):
            advertencias.append("Pasajero marcado como superviviente pero tiene fecha de hundimiento")
        elif estado != "superviviente" and pd.notna(pasajero.get('fecha_destino_final')):
            advertencias.append("Pasajero no superviviente pero tiene fecha de destino final")

        return {
            "estado": "ok" if not errores else "con_errores",
            "errores": errores,
            "advertencias": advertencias,
            "total_validaciones": len(errores) + len(advertencias)
        }

    except Exception as e:
        logger.error(f"Error en validar_datos_pasajero: {e}")
        return {"estado": "error", "errores": [f"Error en validación: {str(e)}"]}
