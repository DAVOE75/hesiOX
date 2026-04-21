import argparse
import subprocess
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "sirio", "data")
OUTPUT_DIR = os.path.join(BASE_DIR, "sirio", "outputs")
APP_DIR = os.path.join(BASE_DIR, "app")
PPT_FILE = os.path.join(BASE_DIR, "presentacion_tfm.pptx")


def run_command(command):
    """Ejecuta un comando en shell"""
    try:
        print(f"👉 Ejecutando: {' '.join(command)}")
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Error ejecutando {command}: {e}")
        sys.exit(1)


def preprocess():
    run_command([
        sys.executable, "preprocesar_sirio.py",
        os.path.join(DATA_DIR, "tus_datos_sirio.xlsx"),
        "-o", os.path.join(DATA_DIR, "tus_datos_sirio_limpio.csv")
    ])


def graphs():
    run_command([sys.executable, "-m", "sirio.graphs.generar_graficos"])


def app():
    run_command(["streamlit", "run", os.path.join(APP_DIR, "app_sirio.py")])


def ppt():
    run_command([sys.executable, "actualizar_pptx.py"])


def test():
    run_command(["pytest", "tests/"])


def clean():
    if not os.path.exists(OUTPUT_DIR):
        print("⚠️ No hay carpeta de outputs para limpiar.")
        return
    for f in os.listdir(OUTPUT_DIR):
        if f.endswith(".png") or f.endswith(".html"):
            os.remove(os.path.join(OUTPUT_DIR, f))
    print("🧹 Outputs limpiados.")


def test_flujo():
    """
    Ejecuta un flujo completo de prueba:
    - Preprocesamiento
    - Gráficos
    - Mapas
    - Grafo
    - Timeline
    """
    import pandas as pd
    from sirio.preprocessing import limpiar_datos
    from sirio.graphs.generar_graficos import generar_graficos
    from sirio.maps.basicos import generar_heatmap, generar_mapa_cluster, generar_mapa_graduado
    from sirio.maps.rutas import generar_mapa_rutas
    from sirio.graphs.grafo import generar_grafo
    from sirio.timeline.timeline import generar_timeline

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("📥 Cargando datos de ejemplo...")
    df = pd.read_csv(os.path.join(DATA_DIR, "datos_sirio.csv"))
    df = limpiar_datos(df)
    print(f"✅ Datos cargados: {df.shape[0]} filas, {df.shape[1]} columnas")

    print("📊 Generando gráficos...")
    generar_graficos(df, output_dir=OUTPUT_DIR)
    print("✅ Gráficos generados")

    print("🗺 Generando mapas...")
    m1 = generar_heatmap(df)
    m2 = generar_mapa_cluster(df)
    m3 = generar_mapa_graduado(df)

    if m1: m1.save(os.path.join(OUTPUT_DIR, "heatmap.html"))
    if m2: m2.save(os.path.join(OUTPUT_DIR, "cluster.html"))
    if m3: m3.save(os.path.join(OUTPUT_DIR, "graduado.html"))
    print("✅ Mapas generados")

    print("🔗 Generando grafo...")
    generar_grafo(df, origen="puerto_embarque", destino="destino",
                  output_file=os.path.join(OUTPUT_DIR, "grafo.html"))
    print("✅ Grafo generado")

    print("⏳ Generando timeline...")
    t = generar_timeline(df, fecha_col="fecha", categoria_col="puerto_embarque")
    if t:
        t.write_html(os.path.join(OUTPUT_DIR, "timeline.html"))
        print("✅ Timeline generado")
    else:
        print("⚠️ No se pudo generar timeline (faltan datos con 'fecha')")

    print("🎉 Flujo completo ejecutado con éxito.")


def main():
    parser = argparse.ArgumentParser(description="CLI para gestionar Sirio Project")
    parser.add_argument(
        "command",
        choices=["preprocess", "graphs", "app", "ppt", "test", "clean", "test-flujo"],
        help="Comando a ejecutar"
    )
    args = parser.parse_args()

    if args.command == "preprocess":
        preprocess()
    elif args.command == "graphs":
        graphs()
    elif args.command == "app":
        app()
    elif args.command == "ppt":
        ppt()
    elif args.command == "test":
        test()
    elif args.command == "clean":
        clean()
    elif args.command == "test-flujo":
        test_flujo()


if __name__ == "__main__":
    main()
