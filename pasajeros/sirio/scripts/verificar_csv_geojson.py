import geopandas as gpd
import pandas as pd
import sys

def verificar_coincidencias(csv_file, csv_col, geo_file, geo_col):
    # Cargar CSV
    df = pd.read_csv(csv_file)
    if csv_col not in df.columns:
        raise ValueError(f"La columna '{csv_col}' no existe en el CSV. Columnas: {list(df.columns)}")
    valores_csv = set(df[csv_col].dropna().unique())

    # Cargar GeoJSON
    gdf = gpd.read_file(geo_file)
    if geo_col not in gdf.columns:
        raise ValueError(f"La columna '{geo_col}' no existe en el GeoJSON. Columnas: {list(gdf.columns)}")
    valores_geo = set(gdf[geo_col].dropna().unique())

    # Comparación
    en_comun = valores_csv & valores_geo
    solo_csv = valores_csv - valores_geo
    solo_geo = valores_geo - valores_csv

    print(f"\n🔎 Comparación entre CSV ({csv_col}) y GeoJSON ({geo_col}):")
    print(f"✅ Coincidencias: {len(en_comun)}")
    print(f"⚠️ En CSV pero no en GeoJSON: {len(solo_csv)}")
    print(f"➕ En GeoJSON pero no en CSV: {len(solo_geo)}")

    if solo_csv:
        print("\n⚠️ Nombres en CSV pero no en GeoJSON:")
        for val in sorted(solo_csv):
            print(" -", val)

    if solo_geo:
        print("\n➕ Nombres en GeoJSON pero no en CSV (puede ser normal):")
        for val in sorted(solo_geo):
            print(" -", val)

if __name__ == "__main__":
    if len(sys.argv) != 5:
        print("Uso: python verificar_csv_geojson.py <archivo_csv> <columna_csv> <archivo_geojson> <columna_geojson>")
        sys.exit(1)

    csv_file, csv_col, geo_file, geo_col = sys.argv[1:]
    verificar_coincidencias(csv_file, csv_col, geo_file, geo_col)
