# Módulo graphs

Este módulo contiene la parte de **visualización estadística y grafos** del proyecto Sirio.

## Archivos

- **generar_graficos.py** → Histogramas, gráficos circulares y Top 10 regiones.
- **grafo.py** → Grafo interactivo de pasajeros con PyVis.
- **__init__.py** → Expone todas las funciones principales.

## Funciones principales

- `generar_histograma_edades(df, output_dir=None)`
- `generar_pie_sexo(df, output_dir=None)`
- `generar_top_regiones(df, output_dir=None)`
- `generar_grafo(df_pasajero)`

## Uso

```python
from sirio.graphs import (
    generar_histograma_edades,
    generar_pie_sexo,
    generar_top_regiones,
    generar_grafo
)

grafo = generar_grafo(df)
fig = generar_top_regiones(df)
