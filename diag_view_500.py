import sys
import os

# Base directory
BASE_DIR = "/opt/hesiox"
sys.path.append(BASE_DIR)

from app import app
from routes.noticias import topografia_semantica_view

with app.test_request_context():
    from models import Proyecto, Usuario
    from extensions import db
    import utils
    from flask_login import login_user
    
    # Mock current_user
    class MockUser:
        def __init__(self):
            self.nombre = "Admin"
            self.is_authenticated = True
            self.is_active = True
            self.is_anonymous = False
            self.get_id = lambda: "1"
            
    import flask_login
    flask_login.current_user = MockUser()
    
    project_ids = [6, 7, 17, 16, 15, 29, 1]
    
    for pid in project_ids:
        print(f"\n--- Testing Project ID: {pid} ---")
        proj = db.session.get(Proyecto, pid)
        if not proj:
            print(f"Project {pid} not found")
            continue
            
        # Mock get_proyecto_activo
        utils.get_proyecto_activo = lambda p=proj: p
        
        try:
            resp = topografia_semantica_view()
            if isinstance(resp, tuple):
                print(f"[{pid}] Response status from view logic:", resp[1])
                print(f"[{pid}] Response error message:", resp[0])
            elif hasattr(resp, 'status_code'):
                print(f"[{pid}] Response status from flask response:", resp.status_code)
                if resp.status_code == 500:
                    print(f"[{pid}] Response data (truncated):", resp.data.decode('utf-8')[:500])
            else:
                print(f"[{pid}] Response type:", type(resp))
                if isinstance(resp, str):
                    print(f"[{pid}] HTML Start:", resp[:100])
                print(f"[{pid}] Success (likely returned rendered HTML or redirect object)")
        except Exception as e:
            import traceback
            print(f"[{pid}] CRITICAL ERROR in diagnostic loop: {str(e)}")
            traceback.print_exc()

    sys.exit(0)
