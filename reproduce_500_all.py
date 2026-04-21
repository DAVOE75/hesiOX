import sys
import os

# Añadir el directorio actual al path
sys.path.append(os.getcwd())

try:
    from app import app
    print("✅ App importada correctamente.")
    with app.test_request_context():
        from flask import render_template
        from routes.proyectos import listar as proyectos_index
        # Intentar renderizar la página de proyectos
        try:
            print("Probando renderizado de /proyectos/...")
            res = proyectos_index()
            print("✅ /proyectos/ renderizado correctamente en prueba local.")
        except Exception as e:
            import traceback
            print("❌ Error renderizando /proyectos/:")
            traceback.print_exc()
            
        from routes.pasajeros import ficha as pasajeros_ficha
        try:
            print("Probando renderizado de /pasajeros/ficha/11...")
            res = pasajeros_ficha(11)
            print("✅ /pasajeros/ficha/11 renderizado correctamente en prueba local.")
        except Exception as e:
            import traceback
            print("❌ Error renderizando /pasajeros/ficha/11:")
            traceback.print_exc()
            
except Exception as e:
    import traceback
    print("❌ Error fatal importando la aplicación:")
    traceback.print_exc()
