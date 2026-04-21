from app import app
from extensions import db
from models import EdicionTipoRecurso

with app.app_context():
    ediciones = EdicionTipoRecurso.query.all()
    print("--- Ediciones actuales ---")
    for e in ediciones:
        print(f"ID: {e.id}, Tipo: {e.tipo_recurso}, Valor: {e.valor}, Etiqueta: {e.etiqueta}, Orden: {e.orden}")
    
    # Buscar si hay 'Diaria' en 'libro'
    diaria_libro = EdicionTipoRecurso.query.filter_by(tipo_recurso='libro', valor='Diaria').first()
    if not diaria_libro:
        diaria_libro = EdicionTipoRecurso.query.filter_by(tipo_recurso='libro', etiqueta='Diaria').first()
        
    if diaria_libro:
        print(f"Encontrado 'Diaria' para 'libro' (ID: {diaria_libro.id}). Procediendo a eliminarlo...")
        db.session.delete(diaria_libro)
        db.session.commit()
        print("Eliminado correctamente.")
    else:
        print("No se encontró 'Diaria' para 'libro' en la BD.")
