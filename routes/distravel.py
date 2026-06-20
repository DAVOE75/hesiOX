from flask import Blueprint, send_from_directory, request, jsonify, send_file
import os
import requests
import logging

# Configurar logging
logger = logging.getLogger(__name__)

distravel_bp = Blueprint('distravel_admin', __name__, url_prefix='/distravel')

# Rutas absolutas verificadas
BASE_PATH = '/opt/hesiox/distravel'
ADMIN_DIST_DIR = os.path.join(BASE_PATH, 'admin-web/dist')
UPLOADS_DIR = os.path.join(BASE_PATH, 'server/uploads')
NODE_BACKEND_URL = "http://localhost:3000"

@distravel_bp.route('/admin/')
@distravel_bp.route('/admin/<path:path>')
def serve_admin(path=''):
    """Sirve el frontend de React (Vite)"""
    try:
        # Si el path está vacío o es una ruta de React Router (no un archivo real), servimos index.html
        target_file = os.path.join(ADMIN_DIST_DIR, path)
        if not path or not os.path.isfile(target_file):
            index_path = os.path.join(ADMIN_DIST_DIR, 'index.html')
            if os.path.exists(index_path):
                return send_file(index_path)
            return f"Error: No se encuentra index.html en {ADMIN_DIST_DIR}", 404
        
        # Si es un archivo real (assets, imágenes, etc), lo servimos
        return send_from_directory(ADMIN_DIST_DIR, path)
    except Exception as e:
        logger.error(f"Error serving distravel admin: {str(e)}")
        return f"Error sirviendo el panel administrativo: {str(e)}", 500

@distravel_bp.route('/api/<path:path>', methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE'])
def proxy_api(path):
    """Proxy para las peticiones a la API de Node/Express"""
    url = f"{NODE_BACKEND_URL}/api/{path}"
    
    try:
        # Reenviar la petición al backend de Node
        # Filtramos 'Host' y 'Content-Length' para evitar conflictos
        headers = {key: value for (key, value) in request.headers if key.lower() not in ['host', 'content-length']}
        
        resp = requests.request(
            method=request.method,
            url=url,
            headers=headers,
            data=request.get_data(),
            cookies=request.cookies,
            allow_redirects=False,
            params=request.args,
            timeout=10
        )
        
        # Filtrar cabeceras que pueden causar problemas al reenviar la respuesta
        excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
        resp_headers = [(name, value) for (name, value) in resp.headers.items()
                        if name.lower() not in excluded_headers]
        
        return (resp.content, resp.status_code, resp_headers)
    except requests.exceptions.ConnectionError:
        return jsonify({"error": "El servidor de Distravel no está respondiendo (Node.js offline)"}), 503
    except Exception as e:
        logger.error(f"Error in Distravel API Proxy: {str(e)}")
        return jsonify({"error": f"Error en el servidor intermedio: {str(e)}"}), 500

@distravel_bp.route('/uploads/<path:filename>')
def serve_uploads(filename):
    """Sirve las imágenes subidas por distravel"""
    return send_from_directory(UPLOADS_DIR, filename)

@distravel_bp.route('/test')
def test_route():
    return "Distravel Blueprint is fully functional!"
