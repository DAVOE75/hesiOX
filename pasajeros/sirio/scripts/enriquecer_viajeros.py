"""
Script para enriquecer viajeros con coordenadas de municipios.
"""

import os
import json
import pandas as pd

# ===============================
# Cargar municipios con coordenadas
# ===============================
ruta_json = os.path.join(os.path.dirname(__file__), "..", "data", "municipios_es_it.json")
ruta_json = os.path.abspath(ruta_json)  # normaliza la ruta

try:
    with open(ruta_json, "r", encoding="utf-8") as f:
        municipios = json.load(f)
    print(f"✅ Se cargaron {len(municipios)} municipios desde {ruta_json}")
except FileNotFoundError:
    raise RuntimeError(f"❌ No se encontró el archivo: {ruta_json}")
except json.JSONDecodeError as e:
    raise RuntimeError(f"❌ Error al leer JSON: {e}")

# ===============================
# Ejemplo de uso: enriquecer CSV de viajeros
# ===============================
def enriquecer_viajeros(csv_path="viajeros.csv", salida="viajeros_enriquecidos.csv"):
    if not os.path.exists(csv_path):
        raise RuntimeError(f"❌ No se encontró el archivo {csv_path}")

    df = pd.read_csv(csv_path)

    # Añadir columnas de coordenadas
    df["lat"] = df["municipio"].map(lambda x: municipios.get(x, [40.0, -3.0])[0])
    df["lon"] = df["municipio"].map(lambda x: municipios.get(x, [40.0, -3.0])[1])

    # Guardar resultado
    df.to_csv(salida, index=False, encoding="utf-8")
    print(f"✅ Archivo enriquecido guardado en {salida}")


if __name__ == "__main__":
    enriquecer_viajeros()
