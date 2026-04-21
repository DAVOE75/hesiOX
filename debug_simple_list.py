
from app import app, db
from routes.noticias import api_noticias_simple_list
from flask import Flask, request

def debug_simple_list():
    with app.test_request_context('/api/noticias/simple_list?publicacion=Diario%20de%20Barcelona'):
        try:
            print("--- START DEBUG ---")
            # Simulate login if needed or bypass login_required decorator if possible
            # Since login_required wraps the view, calling the view function directly might fail if not mocked
            # However, we can try to inspect the logic inside the view function by copy-pasting or importing
            
            # Let's try to run the query manually first
            from utils import get_proyecto_activo
            # We need to mock get_proyecto_activo or ensure a project is active in session
            # For this script, let's just run the query logic directly
            
            from models import Prensa, Proyecto
            # Get first project
            proyecto = Proyecto.query.first()
            if not proyecto:
                print("No projects found.")
                return

            print(f"Project ID: {proyecto.id}")
            
            query = Prensa.query.filter_by(proyecto_id=proyecto.id)
            # query = query.filter(Prensa.publicacion == "Diario de Barcelona")
            query = query.order_by(Prensa.id.asc())
            
            print("Executing query...")
            resultados = query.with_entities(Prensa.id, Prensa.titulo, Prensa.fecha_original, Prensa.numero).limit(50).all()
            print(f"Rows found: {len(resultados)}")
            
            for i, r in enumerate(resultados):
                try:
                    # Logic from view
                    fecha_str = "Sin fecha"
                    # Accessing r.fecha_original
                    # In newer SQLAlchemy 'r' is a Row object, access by index or key
                    # Let's see what 'r' is
                    if i == 0:
                        print(f"Row type: {type(r)}")
                        print(f"Row content: {r}")
                    
                    val_fecha = r.fecha_original
                    
                    if val_fecha:
                        if len(val_fecha) >= 10 and val_fecha[4] == '-':
                             anio, mes, dia = val_fecha[:10].split('-')
                             fecha_str = f"{dia}/{mes}/{anio}"
                        else:
                             fecha_str = val_fecha
                    
                    titulo_corto = (r.titulo[:60] + '...') if r.titulo and len(r.titulo) > 60 else (r.titulo or "Sin título")
                    label = f"{fecha_str} - {titulo_corto}"
                    if r.numero:
                        label += f" (Nº {r.numero})"
                        
                    # print(f"Processed: {label}")
                except Exception as e:
                    print(f"Error processing row {r.id}: {e}")
                    raise e
                    
            print("--- SUCCESS ---")
            
        except Exception as e:
            print(f"CRASH: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    debug_simple_list()
