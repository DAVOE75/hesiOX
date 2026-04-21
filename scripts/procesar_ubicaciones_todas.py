# Script para procesar todas las noticias y extraer ubicaciones automáticamente
# Uso: python scripts/procesar_ubicaciones_todas.py


import os
import sys
# Asegura que la raíz del proyecto está en sys.path
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Script para procesar todas las noticias y extraer ubicaciones automáticamente
# Uso: python scripts/procesar_ubicaciones_todas.py

import os
import sys

# Asegura que la raíz del proyecto está en sys.path
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import spacy
import requests
from flask import Flask
from extensions import db
from models import Prensa, LugarNoticia
from app import app as flask_app

nlp = spacy.load('es_core_news_md')


def extraer_y_guardar_ubicaciones(noticia, session):
    ubicaciones_contenido = []
    ubicaciones_titulo = []
    if noticia.contenido:
        doc_contenido = nlp(noticia.contenido)
        ubicaciones_contenido = [ent.text for ent in doc_contenido.ents if ent.label_ in ('LOC', 'GPE')]
    if noticia.titulo:
        doc_titulo = nlp(noticia.titulo)
        ubicaciones_titulo = [ent.text for ent in doc_titulo.ents if ent.label_ in ('LOC', 'GPE')]
    lugares_detectados = set(ubicaciones_contenido + ubicaciones_titulo)
    nombres_borrados = set([
        l.nombre for l in session.query(LugarNoticia).filter_by(borrado=True, noticia_id=noticia.id).all()
    ])
    for lugar_nombre in lugares_detectados:
        if lugar_nombre in nombres_borrados:
            continue
        existe = session.query(LugarNoticia).filter_by(noticia_id=noticia.id, nombre=lugar_nombre, borrado=False).first()
        if not existe:
            try:
                resp = requests.get('https://nominatim.openstreetmap.org/search', params={
                    'q': lugar_nombre,
                    'format': 'json',
                    'limit': 1
                }, headers={'User-Agent': 'app-hesiox/1.0'})
                data_geo = resp.json()
                if data_geo:
                    lat = float(data_geo[0]['lat'])
                    lon = float(data_geo[0]['lon'])
                    nuevo = LugarNoticia(
                        noticia_id=noticia.id,
                        nombre=lugar_nombre,
                        lat=lat,
                        lon=lon,
                        frecuencia=1,
                        tipo='extraido',
                        borrado=False
                    )
                    session.add(nuevo)
                    session.commit()
                    print(f"[OK] {noticia.id}: {lugar_nombre} -> {lat},{lon}")
            except Exception as e:
                print(f"[ERROR] {noticia.id}: {lugar_nombre} - {e}")

if __name__ == "__main__":
    with flask_app.app_context():
        total = Prensa.query.count()
        print(f"Procesando {total} noticias...")
        for i, noticia in enumerate(Prensa.query, 1):
            print(f"[{i}/{total}] Noticia ID {noticia.id}")
            extraer_y_guardar_ubicaciones(noticia, db.session)
        print("Proceso completado.")
