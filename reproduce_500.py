import os
from app import app
from models import Prensa, Publicacion, Proyecto
from extensions import db

with app.app_context():
    # Simulate the request
    publicacion = "Corriere della Sera"
    # We need a project. Let's find one that has this publication.
    noticia = Prensa.query.filter_by(publicacion=publicacion).first()
    if not noticia:
        print(f"No news found for publication '{publicacion}'")
        # Try finding ANY publication to test the logic
        noticia = Prensa.query.first()
        if noticia:
            publicacion = noticia.publicacion
            print(f"Testing with publication: {publicacion}")
        else:
            print("No news in DB at all.")
            exit()

    proyecto_id = noticia.proyecto_id
    print(f"Testing with proyecto_id: {proyecto_id}, publicacion: {publicacion}")

    try:
        # Replicate the logic in api_noticias_por_publicacion
        noticias = Prensa.query.filter_by(proyecto_id=proyecto_id, publicacion=publicacion)\
            .order_by(Prensa.fecha_original.desc()).all()
        
        print(f"Found {len(noticias)} news.")
        res = [{
            'id': n.id,
            'titulo': n.titulo,
            'fecha': n.fecha_original if n.fecha_original else 'S/F'
        } for n in noticias]
        print("Successfully generated response.")
        if res:
            print(f"First item: {res[0]}")
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
