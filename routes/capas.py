try:
    import rasterio
except ImportError:
    rasterio = None
import os
import zipfile
import tempfile
import shutil
from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required
from werkzeug.utils import secure_filename
import geopandas as gpd
from extensions import db, csrf
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

@capas_bp.route('/api/layers/upload_dem', methods=['POST'])
@csrf.exempt
@login_required
def upload_dem():
    """Endpoint específico para subir un MDT (GeoTIFF) para el perfil de elevación"""
    if 'file' not in request.files:
        return jsonify({"success": False, "error": "No hay archivo"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"success": False, "error": "Nombre vacío"}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        if not (filename.lower().endswith('.tif') or filename.lower().endswith('.tiff')):
            return jsonify({"success": False, "error": "Solo se permiten archivos .tif o .tiff para MDT"}), 400
            
        dem_dir = os.path.join(current_app.static_folder, "uploads", "dem")
        os.makedirs(dem_dir, exist_ok=True)
        
        file_path = os.path.join(dem_dir, filename)
        file.save(file_path)
        
        # Obtener bounds para visualización inmediata
        import rasterio
        from rasterio.warp import transform_bounds
        bounds_data = None
        try:
            with rasterio.open(file_path) as src:
                b = transform_bounds(src.crs, 'EPSG:4326', *src.bounds)
                bounds_data = {"west": b[0], "south": b[1], "east": b[2], "north": b[3]}
        except:
            pass

        return jsonify({
            "success": True, 
            "message": "MDT cargado correctamente. Ahora puede ser usado para el perfil de elevación.",
            "filename": filename,
            "bounds": bounds_data
        })
    
    return jsonify({"success": False, "error": "Extensión no permitida"}), 400

@capas_bp.route('/api/layers/check_dem', methods=['GET'])
@login_required
def check_dem():
    """Verifica si ya existen archivos MDT en el servidor y devuelve sus extensiones geográficas"""
    import rasterio
    dem_dir = os.path.join(current_app.static_folder, "uploads", "dem")
    if not os.path.exists(dem_dir):
        return jsonify({"count": 0, "files": []})
    
    files = [f for f in os.listdir(dem_dir) if f.lower().endswith(('.tif', '.tiff'))]
    results = []
    
    for f in files:
        file_path = os.path.join(dem_dir, f)
        try:
            with rasterio.open(file_path) as src:
                from rasterio.warp import transform_bounds
                # Obtener los bounds en WGS84 (Lat/Lon)
                bounds = transform_bounds(src.crs, 'EPSG:4326', *src.bounds)
                results.append({
                    "filename": f,
                    "bounds": {
                        "west": bounds[0],
                        "south": bounds[1],
                        "east": bounds[2],
                        "north": bounds[3]
                    }
                })
        except Exception as e:
            print(f"Error procesando {f}: {e}")
            results.append({"filename": f, "bounds": None})

    return jsonify({
        "count": len(files),
        "files": results
    })

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
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Referer': 'https://www.ign.es/web/ign/portal'
        }
        
        # Log the attempt
        current_app.logger.info(f"[Proxy] Fetching (truncated): {url[:200]}")
        
        resp = requests.get(url, params=params, stream=True, timeout=15, verify=False, headers=custom_headers)
        
        excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
        headers = [(name, value) for (name, value) in resp.headers.items()
                   if name.lower() not in excluded_headers]

        return Response(resp.iter_content(chunk_size=1024 * 64), 
                        status=resp.status_code, 
                        headers=headers,
                        content_type=resp.headers.get('Content-Type'))
    except Exception as e:
        safe_url = url[:100] + "..." if url else "unknown"
        print(f"!!! [PROXY ERROR] {safe_url}: {e}")
        return jsonify({"error": f"Error de conexion con el servicio externo: {str(e)}"}), 502

@capas_bp.route('/api/altitud_raster', methods=['POST'])
@csrf.exempt
def get_altitud_raster():
    """
    Recibe un array de puntos [[lon, lat], ...] y busca la altitud en un archivo local (MDT/LiDAR).
    El archivo debe estar configurado en la variable de entorno DEM_PATH o buscarse en uploads/dem/.
    """
    if not rasterio:
        return jsonify({"error": "Libreria rasterio no instalada"}), 500
        
    data = request.json
    points = data.get('points', []) # [[lon, lat], ...]
    if not points:
        return jsonify({"error": "No se enviaron puntos"}), 400
        
    # Directorio de modelos de elevación
    dem_dir = os.path.join(current_app.static_folder, "uploads", "dem")
    
    # Buscamos todos los archivos .tif en la carpeta
    dem_files = [os.path.join(dem_dir, f) for f in os.listdir(dem_dir) if f.lower().endswith('.tif')]
    
    if not dem_files:
        return jsonify({"error": "No se encontraron archivos .tif en uploads/dem/"}), 404
        
    results = [None] * len(points)
    pending_indices = list(range(len(points)))
    sources_used = []

    try:
        for dem_path in dem_files:
            if not pending_indices: break
            
            with rasterio.open(dem_path) as src:
                # Filtrar puntos que caen dentro de este raster
                bounds = src.bounds
                indices_to_check = [i for i in pending_indices if (bounds.left <= points[i][0] <= bounds.right and bounds.bottom <= points[i][1] <= bounds.top)]
                
                if not indices_to_check: continue
                
                sources_used.append(os.path.basename(dem_path))
                pts_to_sample = [points[i] for i in indices_to_check]
                
                for idx, val_tuple in zip(indices_to_check, src.sample(pts_to_sample)):
                    val = val_tuple[0]
                    results[idx] = {
                        "altitud": float(val) if val is not None and val > -9999 else 0
                    }
                    # Si encontramos una altitud válida (>0), lo quitamos de pendientes
                    if results[idx]["altitud"] > 0:
                        pending_indices.remove(idx)
        
        # Rellenar con 0 los puntos que no cayeron en ningún raster
        for i in range(len(results)):
            if results[i] is None:
                results[i] = {"altitud": 0}
        
        return jsonify({
            "success": True, 
            "items": results,
            "sources": sources_used
        })
    except Exception as e:
        return jsonify({"error": f"Error procesando raster: {str(e)}"}), 500
