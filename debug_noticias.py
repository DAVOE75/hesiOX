from app import app
from extensions import db
from models import Prensa, LugarNoticia, Proyecto

def test_query():
    with app.app_context():
        print("Imports successful.")
        proyecto = Proyecto.query.first()
        if not proyecto:
            print("No active project found for testing.")
            return

        print(f"Testing with project: {proyecto.nombre}")
        query = Prensa.query.filter_by(proyecto_id=proyecto.id)
        
        v = "Las Marcas"
        print(f"Applying filter for lugar: {v}")
        
        try:
            # Replicating the logic added to routes/noticias.py
            query = query.join(LugarNoticia).filter(
                LugarNoticia.nombre == v,
                LugarNoticia.borrado == False
            )
            print("Query construction successful.")
            print(f"SQL: {query.statement}")
            
            # Try executing
            count = query.count()
            print(f"Count: {count}")
            
        except Exception as e:
            print(f"ERROR: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_query()
