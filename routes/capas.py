import os
import zipfile
import tempfile
import shutil
from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required
from werkzeug.utils import secure_filename
import geopandas as gpd
from extensions import db
from models import CapaGeografica
from utils import get_proyecto_activo
import requests
from flask import Response

capas_bp = Blueprint('capas', __name__)

ALLOWED_EXTENSIONS = {'geojson', 'kml', 'zip', 'json', 'shp', 'gpx', 'ecw', 'tif', 'tiff'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@capas_bp.route('/api/layers/upload', methods=['POST'])
@login_required
def upload_layer():
    try:
        import geopandas as gpd
    except ImportError:
        return jsonify({"success": False, "error": "El servidor no tiene instaladas las librerías GIS (geopandas) necesarias para procesar capas."}), 500

    proyecto = get_proyecto_activo()
    if not proyecto:
        return jsonify({"success": False, "error": "No hay proyecto activo"}), 400

    if 'file' not in request.files:
        return jsonify({"success": False, "error": "No se subió ningún archivo"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"success": False, "error": "Nombre de archivo vacío"}), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        upload_dir = os.path.join(current_app.static_folder, 'uploads', 'layers', str(proyecto.id))
        os.makedirs(upload_dir, exist_ok=True)
        
        file_path = os.path.join(upload_dir, filename)
        file.save(file_path)

        # Convertir a GeoJSON si es necesario
        ext = filename.rsplit('.', 1)[1].lower()
        geojson_filename = filename.rsplit('.', 1)[0] + '.geojson'
        geojson_path = os.path.join(upload_dir, geojson_filename)

        try:
            if ext == 'shp':
                return jsonify({"success": False, "error": "Los archivos .shp no pueden subirse solos. Por favor, sube un archivo .zip que contenga el .shp y sus archivos auxiliares (.shx, .dbf, .prj)."}), 400
            
            if ext == 'zip':
                # Asumimos que es un Shapefile comprimido
                with tempfile.TemporaryDirectory() as tmp_dir:
                    with zipfile.ZipFile(file_path, 'r') as zip_ref:
                        zip_ref.extractall(tmp_dir)
                    
                    # Buscar el archivo .shp dentro de la carpeta extraída
                    shp_file = None
                    for root, dirs, files in os.walk(tmp_dir):
                        for f in files:
                            if f.lower().endswith('.shp'):
                                shp_file = os.path.join(root, f)
                                break
                        if shp_file: break
                    
                    if not shp_file:
                        return jsonify({"success": False, "error": "No se encontró un archivo .shp dentro del ZIP"}), 400
                        
                    # Leer con geopandas y reyectar a WGS84 para Leaflet
                    gdf = gpd.read_file(shp_file)
                    if gdf.crs and gdf.crs.to_epsg() != 4326:
                        gdf = gdf.to_crs(epsg=4326)
                    gdf.to_file(geojson_path, driver='GeoJSON')
            elif ext == 'kml':
                # Habilitar KML en fiona/geopandas
                import fiona
                fiona.drvsupport.supported_drivers['KML'] = 'rw'
                gdf = gpd.read_file(file_path)
                if gdf.crs and gdf.crs.to_epsg() != 4326:
                    gdf = gdf.to_crs(epsg=4326)
                gdf.to_file(geojson_path, driver='GeoJSON')
            elif ext == 'gpx':
                # GPX puede tener múltiples capas (tracks, routes, waypoints, etc.)
                import fiona
                import pandas as pd
                fiona.drvsupport.supported_drivers['GPX'] = 'rw'
                layers = fiona.listlayers(file_path)
                parts = []
                for layer in layers:
                    if layer in ['tracks', 'routes', 'track_points', 'route_points', 'waypoints']:
                        try:
                            gdf_layer = gpd.read_file(file_path, layer=layer)
                            if not gdf_layer.empty:
                                parts.append(gdf_layer)
                        except:
                            continue
                
                if not parts:
                    return jsonify({"success": False, "error": "No se encontraron datos geográficos válidos en el archivo GPX"}), 400
                
                gdf = gpd.GeoDataFrame(pd.concat(parts, ignore_index=True))
                if gdf.crs and gdf.crs.to_epsg() != 4326:
                    gdf = gdf.to_crs(epsg=4326)
                gdf.to_file(geojson_path, driver='GeoJSON')
            elif ext == 'ecw':
                # ECW es un formato raster. No lo convertimos, usamos el original.
                geojson_filename = filename
            elif ext in ['json', 'geojson']:
                # Ya es GeoJSON, solo nos aseguramos de que sea válido y reyectamos si es necesario
                gdf = gpd.read_file(file_path)
                if gdf.crs and gdf.crs.to_epsg() != 4326:
                    gdf = gdf.to_crs(epsg=4326)
                gdf.to_file(geojson_path, driver='GeoJSON')
            elif ext in ['tif', 'tiff']:
                # GeoTIFF es un formato raster. No lo convertimos, usamos el original.
                # Marcamos geojson_filename como el nombre del original para que el frontend lo descargue/use directamente.
                geojson_filename = filename
            
            # Crear registro en BD
            nueva_capa = CapaGeografica(
                proyecto_id=proyecto.id,
                nombre=request.form.get('nombre', filename),
                tipo=ext if ext in ['gpx', 'kml', 'shp', 'ecw', 'tif', 'tiff'] else 'geojson',
                filename=geojson_filename,
                color=request.form.get('color', '#3388ff')
            )
            db.session.add(nueva_capa)
            db.session.commit()

            return jsonify({
                "success": True, 
                "layer": {
                    "id": nueva_capa.id,
                    "nombre": nueva_capa.nombre,
                    "filename": nueva_capa.filename,
                    "color": nueva_capa.color
                }
            })

        except Exception as e:
            current_app.logger.error(f"Error procesando capa geográfica: {e}")
            return jsonify({"success": False, "error": f"Error al procesar el archivo: {str(e)}"}), 500
    
    return jsonify({"success": False, "error": "Tipo de archivo no permitido"}), 400

@capas_bp.route('/api/layers', methods=['GET'])
@login_required
def list_layers():
    proyecto = get_proyecto_activo()
    if not proyecto:
        return jsonify([])
    
    capas = CapaGeografica.query.filter_by(proyecto_id=proyecto.id).all()
    return jsonify([{
        "id": c.id,
        "nombre": c.nombre,
        "filename": f"/static/uploads/layers/{proyecto.id}/{c.filename}",
        "color": c.color,
        "visible": c.visible,
        "tipo": c.tipo
    } for c in capas])

@capas_bp.route('/api/layers/<int:id>', methods=['DELETE'])
@login_required
def delete_layer(id):
    capa = CapaGeografica.query.get_or_404(id)
    # Verificar que pertenezca al proyecto activo (opcional pero recomendado)
    db.session.delete(capa)
    db.session.commit()
    # No borramos el archivo físico por ahora para evitar problemas de concurrencia, 
    # o podríamos hacerlo si estamos seguros.
    return jsonify({"success": True})

@capas_bp.route('/api/proxy/wms')
@login_required
def wms_proxy():
    url = request.args.get('url')
    if not url:
        return jsonify({"error": "No URL provided"}), 400
    
    # Forward all other parameters
    params = request.args.to_dict()
    params.pop('url', None)
    
    try:
        # Some WMS servers require exact parameter casing, but request.args.to_dict() handles it
        # Use verify=False to handle institutional servers with SSL certificate issues
        # Add a User-Agent to avoid 403 Forbidden on strict servers like Catastro
        custom_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        resp = requests.get(url, params=params, stream=True, timeout=30, verify=False, headers=custom_headers)
        
        excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
        headers = [(name, value) for (name, value) in resp.raw.headers.items()
                   if name.lower() not in excluded_headers]

        return Response(resp.iter_content(chunk_size=1024 * 64), 
                        status=resp.status_code, 
                        headers=headers,
                        content_type=resp.headers.get('Content-Type'))
    except Exception as e:
        current_app.logger.error(f"WMS Proxy error: {e}")
        return jsonify({"error": str(e)}), 500
