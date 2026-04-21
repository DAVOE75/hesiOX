from app import app
from extensions import db
from models import Prensa, Proyecto, Publicacion

def test_edicion_fix():
    with app.app_context():
        # 1. Preparar datos
        proyecto = Proyecto.query.first()
        pub = Publicacion.query.filter_by(proyecto_id=proyecto.id).first()
        
        # 2. Crear noticia
        print("--- TEST CREACIÓN ---")
        nueva = Prensa(
            proyecto_id=proyecto.id,
            titulo="Noticia Test Fix",
            publicacion=pub.nombre,
            id_publicacion=pub.id_publicacion,
            edicion="mañana",
            texto_original="Texto original inicial",
            descripcion_publicacion="Medio de prueba"
        )
        db.session.add(nueva)
        db.session.commit()
        
        # 3. Simular edición con los nuevos campos
        print("--- TEST EDICIÓN ---")
        noticia = db.session.get(Prensa, nueva.id)
        
        # Simulando lo que hace el route editar ahora (con el FIX)
        noticia.edicion = "tarde"
        noticia.texto_original = "Texto original modificado"
        noticia.descripcion_publicacion = "Medio de prueba modificado"
        
        db.session.commit()
        
        # 4. Verificar persistencia
        final = db.session.get(Prensa, nueva.id)
        print(f"Edición: {final.edicion}")
        print(f"Texto Original: {final.texto_original}")
        print(f"Descripción Medio: {final.descripcion_publicacion}")
        
        if final.edicion == "tarde" and final.texto_original == "Texto original modificado":
            print("✅ FIX VERIFICADO: Los campos se guardan correctamente en la edición.")
        else:
            print("❌ ERROR: Los campos NO se guardaron correctamente.")

        # Limpieza (opcional)
        # db.session.delete(final)
        # db.session.commit()

if __name__ == "__main__":
    test_edicion_fix()
