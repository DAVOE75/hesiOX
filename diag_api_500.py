import sys
import os

# Base directory
BASE_DIR = "/opt/hesiox"
sys.path.append(BASE_DIR)

from app import app
from routes.noticias import cartografia_corpus_embeddings_api

with app.test_request_context():
    # Mocking a project_id=1 request
    from flask import request
    # Set request args
    with app.test_client() as client:
        # We need to be logged in and have a project.
        # But for debugging the logic in cartografia_corpus_embeddings_api:
        from models import Proyecto, Prensa
        from extensions import db
        
        # Ensure project 1 exists and has embeddings
        proj = db.session.get(Proyecto, 1)
        if not proj:
            print("Project 1 not found")
            sys.exit(1)
            
        print(f"Testing project: {proj.nombre}")
        
        # Test the function directly
        # Note: it calls get_proyecto_activo() which looks at session['proyecto_activo_id']
        from flask import session
        session['proyecto_activo_id'] = 1
        
        try:
            # Mock get_proyecto_activo in utils because it's imported locally in the function
            import utils
            utils.get_proyecto_activo = lambda: proj
            
            resp = cartografia_corpus_embeddings_api()
            if hasattr(resp, 'status_code'):
                print("Response status:", resp.status_code)
                print("Response data:", resp.data.decode('utf-8'))
            else:
                print("Response status (tuple):", resp[1] if isinstance(resp, tuple) else 200)
                print("Response body:", resp)
        except Exception as e:
            import traceback
            traceback.print_exc()
