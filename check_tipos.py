
from app import app, db
from models import TipoUbicacion

with app.app_context():
    tipos = TipoUbicacion.query.all()
    print("--- Todos los tipos ---")
    for t in tipos:
        print(f"ID: {t.id}, Codigo: {t.codigo}, Nombre: {t.nombre}, Categoria: {t.categoria}, Orden: {t.orden}, Activo: {t.activo}")
    
    print("\n--- Buscando 'Puerto' ---")
    puerto = TipoUbicacion.query.filter((TipoUbicacion.nombre.ilike('%Puerto%')) | (TipoUbicacion.codigo.ilike('%puerto%'))).all()
    if puerto:
        for t in puerto:
            print(f"ID: {t.id}, Codigo: {t.codigo}, Nombre: {t.nombre}, Categoria: {t.categoria}, Orden: {t.orden}, Activo: {t.activo}")
    else:
        print("No se encontró ningún tipo con nombre o código 'Puerto'")
