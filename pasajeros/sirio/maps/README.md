# Módulo `maps`

Este módulo contiene las funciones de visualización geográfica para el proyecto **Sirio**.

## Archivos

- **basicos.py** → mapas coropléticos, heatmap, cluster, graduado y animado (`generar_mapa`).
- **rutas.py** → rutas de viaje entre ciudades.
- **comparativos.py** → comparaciones entre datos filtrados y el dataset completo.
- **__init__.py** → exporta todas las funciones de forma unificada.

## Uso

```python
from sirio.maps import (
    generar_mapa_coropletas, generar_heatmap, generar_mapa_cluster,
    generar_mapa_graduado, generar_mapa, generar_mapa_rutas, generar_mapa_comparativo
)
```
