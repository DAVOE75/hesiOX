import geopandas as gpd
import sys

def listar_nombres(filepath, columna):
    gdf = gpd.read_file(filepath)
    if columna not in gdf.columns:
        raise ValueError(f"La columna '{columna}' no está en el fichero. Columnas: {list(gdf.columns)}")
    nombres = sorted(gdf[columna].dropna().unique())
    return nombres

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Uso: python listar_geojson.py <ruta_geojson> <columna>")
        sys.exit(1)

    filepath = sys.argv[1]
    columna = sys.argv[2]

    nombres = listar_nombres(filepath, columna)
    print(f"\n✅ {len(nombres)} nombres únicos encontrados en '{columna}':\n")
    for n in nombres:
        print("-", n)
