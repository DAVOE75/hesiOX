import pandas as pd
from pyvis.network import Network


def generar_grafo(df, origen, destino, output_file="grafo.html"):
    """
    Genera un grafo interactivo a partir de dos columnas (origen y destino)
    y lo guarda en un archivo HTML para ser usado en Streamlit.
    """

    net = Network(height="600px", width="100%", bgcolor="#ffffff", font_color="black")
    net.barnes_hut()

    # Verificar que las columnas existen
    if origen not in df.columns or destino not in df.columns:
        raise ValueError(f"Las columnas {origen} y/o {destino} no existen en el DataFrame")

    # Crear nodos y aristas
    for _, row in df.iterrows():
        o = row.get(origen)
        d = row.get(destino)

        if pd.notna(o) and pd.notna(d):
            net.add_node(str(o), label=str(o))
            net.add_node(str(d), label=str(d))
            net.add_edge(str(o), str(d))

    # Guardar HTML sin intentar abrir navegador
    net.write_html(output_file, local=True)
    return output_file
