"""
Script para actualizar municipios_es_it.json con coordenadas faltantes
usando geopy.
"""

import os
import json
import pandas as pd
import time
from geopy.geocoders import Nominatim

# ==============================
# Rutas
# ==============================
BASE_DIR = os.path.dirname(os.path.dirname(__file__))  # carpeta sirio/
data_path = os.path.join(BASE_DIR, "data", "municipios_es_it.json")
csv_path = os.path.join(BASE_DIR, "..", "viajeros.csv")

# ==============================
# Cargar municipios actuales
# ==============================
if os.path.exists(data_path):
    with open(data_path, "r", encoding="utf-8") as f:
        municipios_dict = json.load(f)
else:
    municipios_dict = {}

print(f"✅ JSON inicial cargado con {len(municipios_dict)} municipios")

# ==============================
# Leer viajeros.csv
# ==============================
df = pd.read_csv(csv_path)
if "municipio" not in df.columns:
    raise RuntimeError("❌ No se encuentra la columna 'municipio' en viajeros.csv")

municipios_csv = set(df["municipio"].dropna().unique())

# ==============================
# Buscar los faltantes
# ==============================
faltantes = [m for m in municipios_csv if m not in municipios_dict]
print(f"🔎 Municipios únicos en CSV: {len(municipios_csv)}")
print(f"🆕 Municipios faltantes en JSON: {len(faltantes)}")

# ==============================
# Geocoding con geopy
# ==============================
geolocator = Nominatim(user_agent="sirio-mapas", timeout=10)

for municipio in faltantes:
    try:
        location = geolocator.geocode(f"{municipio}, España") or geolocator.geocode(f"{municipio}, Italia")
        if location:
            municipios_dict[municipio] = [location.latitude, location.longitude]
            print(f"✅ {municipio}: {location.latitude}, {location.longitude}")
        else:
            print(f"⚠️ No se encontró {municipio}, asignado fallback")
            municipios_dict[municipio] = [40.0, -3.0]
        time.sleep(1)  # Respetar el límite de Nominatim
    except Exception as e:
        print(f"❌ Error con {municipio}: {e}")
        municipios_dict[municipio] = [40.0, -3.0]

# ==============================
# Guardar JSON actualizado
# ==============================
with open(data_path, "w", encoding="utf-8") as f:
    json.dump(municipios_dict, f, ensure_ascii=False, indent=4)

print(f"💾 JSON actualizado guardado en {data_path} con {len(municipios_dict)} municipios")
