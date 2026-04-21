import sys
import os

# Añadir el directorio actual al path
sys.path.append(os.getcwd())

from app import app
from models import db, PasajeroSirio

with app.app_context():
    try:
        id_test = 11
        pasajero = PasajeroSirio.query.get(id_test)
        if not pasajero:
            print(f"Pasajero con ID {id_test} no encontrado.")
            sys.exit(0)
            
        print(f"Probando ficha para: {pasajero.nombre} {pasajero.apellidos}")
        
        # Simular el renderizado de la plantilla
        from flask import render_template
        # Necesitamos mockear el request context para url_for y otros
        with app.test_request_context():
            from routes.pasajeros import ficha
            # Llamar directamente a la función de la ruta
            response = ficha(id_test)
            print("Renderizado exitoso.")
    except Exception as e:
        import traceback
        print("ERROR DETECTADO:")
        traceback.print_exc()
