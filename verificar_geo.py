# script: verificar_geo.py
import os
from flask import Flask
from app import app, db, GeoPlace, Proyecto
from utils import geocode_city

# Configura el contexto de la aplicación
with app.app_context():
    print("--- INICIANDO VERIFICACIÓN GEO ---")
    
    # 1. Verificar si la función geocode_city funciona
    print("\n1. Probando geocode_city('Madrid')...")
    lat, lon, address, status = geocode_city("Madrid", "España")
    print(f"Resultado: Status={status}, Lat={lat}, Lon={lon}")
    
    if status != "OK" or not lat:
        print("❌ FALLO: geocode_city no devolvió coordenadas válidas.")
    else:
        print("✅ ÉXITO: geocode_city funciona correctamente.")

    # 2. Verificar inserción en base de datos (simulación)
    print("\n2. Verificando modelo GeoPlace...")
    try:
        # Buscar un proyecto existente para asociar
        proyecto = Proyecto.query.first()
        if not proyecto:
            print("⚠️ ADVERTENCIA: No hay proyectos para probar la inserción en BD.")
        else:
            # Crear entrada dummy
            dummy_city = "TestCity_" + str(os.urandom(4).hex())
            geo = GeoPlace(
                proyecto_id=proyecto.id,
                place_raw=dummy_city,
                place_norm=dummy_city.lower(),
                status="TEST",
                lat=0.0,
                lon=0.0
            )
            db.session.add(geo)
            db.session.commit()
            print(f"✅ ÉXITO: Registro creado en GeoPlace para '{dummy_city}'.")
            
            # Limpieza
            db.session.delete(geo)
            db.session.commit()
            print("✅ ÉXITO: Registro de prueba eliminado.")

    except Exception as e:
        print(f"❌ FALLO: Error interactuando con la BD: {e}")

    print("\n--- FIN VERIFICACIÓN ---")
