import pandas as pd
from sirio.preprocessing import limpiar_datos
from sirio.graphs.generar_graficos import generar_graficos
from sirio.maps.basicos import generar_heatmap, generar_mapa_cluster, generar_mapa_graduado
from sirio.maps.rutas import generar_mapa_rutas
from sirio.graphs.grafo import generar_grafo
from sirio.timeline.timeline import generar_timeline

# ================================
# 1. Cargar y preprocesar datos
# ================================
print("📥 Cargando datos de ejemplo...")
df = pd.read_csv("sirio/sirio/data/datos_sirio.csv")  # ajusta ruta si es necesario
df = limpiar_datos(df)
print(f"✅ Datos cargados: {df.shape[0]} filas, {df.shape[1]} columnas")

# ================================
# 2. Gráficos descriptivos
# ================================
print("📊 Generando gráficos...")
figs = generar_graficos(df, output_dir="sirio/outputs")
print(f"✅ {len(figs)} gráficos generados")

# ================================
# 3. Mapas
# ================================
print("🗺 Generando mapas...")
m1 = generar_heatmap(df)
m2 = generar_mapa_cluster(df)
m3 = generar_mapa_graduado(df)

if m1: m1.save("sirio/outputs/heatmap.html")
if m2: m2.save("sirio/outputs/cluster.html")
if m3: m3.save("sirio/outputs/graduado.html")
print("✅ Mapas guardados")

# ================================
# 4. Grafo
# ================================
print("🔗 Generando grafo...")
g = generar_grafo(df, origen="puerto_embarque", destino="destino", output_file="sirio/outputs/grafo.html")
print("✅ Grafo generado")

# ================================
# 5. Timeline
# ================================
print("⏳ Generando timeline...")
t = generar_timeline(df, fecha_col="fecha", categoria_col="puerto_embarque")
if t:
    t.write_html("sirio/outputs/timeline.html")
    print("✅ Timeline generado")
else:
    print("⚠️ No se pudo generar timeline (faltan datos con 'fecha')")
