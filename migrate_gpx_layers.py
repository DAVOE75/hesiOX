from app import app
from extensions import db
from models import CapaGeografica
import os

def migrate_layers():
    with app.app_context():
        capas = CapaGeografica.query.filter_by(tipo='geojson').all()
        fixed = 0
        for capa in capas:
            # Try to see if there is an original .gpx file
            # Filename in DB is like 'something.geojson'
            if capa.filename.endswith('.geojson'):
                original_gpx = capa.filename.replace('.geojson', '.gpx')
                # Check in the same directory
                upload_dir = os.path.join(app.static_folder, 'uploads', 'layers', str(capa.proyecto_id))
                gpx_path = os.path.join(upload_dir, original_gpx)
                
                if os.path.exists(gpx_path):
                    print(f"Fixing layer {capa.id}: {capa.nombre} -> tipo=gpx")
                    capa.tipo = 'gpx'
                    fixed += 1
                elif ' (GPS)' in capa.nombre: # Fallback if filename naming convention changed
                    print(f"Fixing layer {capa.id} by name: {capa.nombre} -> tipo=gpx")
                    capa.tipo = 'gpx'
                    fixed += 1
        
        if fixed > 0:
            db.session.commit()
            print(f"Migration finished. Fixed {fixed} layers.")
        else:
            print("No layers needed fixing.")

if __name__ == "__main__":
    migrate_layers()
