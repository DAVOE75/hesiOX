
import sys
import os

# Añadir el directorio actual al path para importar módulos
sys.path.append(os.getcwd())

# IMPORTAR APP DIRECTAMENTE (No factory pattern)
from app import app
from extensions import db
from models import Publicacion, Hemeroteca

with app.app_context():
    print("Iniciando actualización masiva de instituciones (Fuente)...")
    
    # Buscar publicaciones que tienen hemeroteca vinculada
    publicaciones = Publicacion.query.filter(Publicacion.hemeroteca_id.isnot(None)).all()
    
    count = 0
    for pub in publicaciones:
        if pub.hemeroteca_id:
            hem = Hemeroteca.query.get(pub.hemeroteca_id)
            if hem:
                # La lógica es: Institucion o Nombre
                nueva_fuente = hem.institucion or hem.nombre
                
                # Solo actualizar si es diferente
                if pub.fuente != nueva_fuente:
                    print(f"Actualizando '{pub.nombre}': '{pub.fuente}' -> '{nueva_fuente}'")
                    pub.fuente = nueva_fuente
                    
                    # NOTA: Se ha eliminado la actualización de ciudad y país a petición del usuario.
                        
                    count += 1
    
    if count > 0:
        db.session.commit()
        print(f"✅ Se han actualizado {count} publicaciones correctamente.")
    else:
        print("ℹ️ No se encontraron publicaciones que requieran actualización.")
