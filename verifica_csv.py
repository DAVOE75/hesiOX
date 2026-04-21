import csv

ruta = "C:/Users/David/Documents/app_hesiox/prensa.csv"
delimitador = ','  # Cambia a ';' si tu archivo usa punto y coma

with open(ruta, encoding="utf-8") as f:
    reader = csv.reader(f, delimiter=delimitador, quotechar='"')
    for i, row in enumerate(reader, 1):
        if len(row) != 51:
            print(f"Línea {i}: {len(row)} columnas -> {row}")