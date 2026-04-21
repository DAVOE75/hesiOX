import os
import time
import json
from flask import Blueprint, request, jsonify, current_app, render_template, flash, redirect, url_for
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from extensions import db
from models import MapaHistorico, Proyecto, LugarNoticia, Prensa
from utils import get_proyecto_activo

mapas_historicos_bp = Blueprint('mapas_historicos', __name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'tif', 'tiff', 'pdf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def generate_thumbnail(image_path, thumbnail_size=(300, 300), quality=85):
    """
    Genera una miniatura optimizada de una imagen.
    
    Args:
        image_path: Ruta completa a la imagen original
        thumbnail_size: Tupla (ancho, alto) para la miniatura
        quality: Calidad JPEG (1-100)
    
    Returns:
        Ruta al archivo de miniatura generado, o None si falla
    """
    try:
        from PIL import Image
        
        # Construir nombre del archivo thumbnail
        base_path, ext = os.path.splitext(image_path)
        thumb_path = f"{base_path}_thumb.jpg"
        
        # Abrir y procesar imagen
        with Image.open(image_path) as img:
            # Convertir a RGB si es necesario (para PNGs con transparencia, etc.)
            if img.mode not in ('RGB', 'L'):
                img = img.convert('RGB')
            
            # Crear thumbnail manteniendo aspect ratio
            img.thumbnail(thumbnail_size, Image.Resampling.LANCZOS)
            
            # Guardar con compresión optimizada
            img.save(thumb_path, 'JPEG', quality=quality, optimize=True)
        
        current_app.logger.info(f"Thumbnail generado: {os.path.basename(thumb_path)}")
        return thumb_path
        
    except Exception as e:
        current_app.logger.error(f"Error generando thumbnail: {e}")
        return None

@mapas_historicos_bp.route('/cartografia/mapas')
@login_required
def gestor_mapas():
    proyecto = get_proyecto_activo()
    if not proyecto:
        flash("Debes seleccionar un proyecto para acceder a la cartografía.", "warning")
        return redirect(url_for("proyectos.listar"))
    
    mapas_objects = MapaHistorico.query.filter_by(proyecto_id=proyecto.id).order_by(MapaHistorico.creado_en.desc()).all()
    
    # Convertir a dict para evitar errores de serialización en el template
    mapas = []
    for m in mapas_objects:
        mapas.append({
            'id': m.id,
            'nombre': m.nombre,
            'filename': m.filename,
            'creado_en': m.creado_en,
            'gcps': m.gcps,
            'visible': m.visible,
            'anio': m.anio,
            'autor': m.autor,
            'fuente': m.fuente,
            'escala': m.escala,
            'descripcion': m.descripcion,
            'licencia': m.licencia,
            'crop_polygon': m.crop_polygon
        })
    
    return render_template('cartografia/gestor_mapas.html', proyecto=proyecto, mapas=mapas, now=int(time.time()))

@mapas_historicos_bp.route('/cartografia/recortador/<int:mapa_id>')
@login_required
def recortador_mapa(mapa_id):
    """Interfaz dedicada al recorte de mapas históricos."""
    # Buscar el mapa y el proyecto
    mapa_obj = MapaHistorico.query.get_or_404(mapa_id)
    proyecto = get_proyecto_activo()  # Or get from mapa_obj directly if user context matches
    
    # Simple dict for template
    mapa = {
        'id': mapa_obj.id,
        'nombre': mapa_obj.nombre,
        'filename': mapa_obj.filename,
        'anio': mapa_obj.anio,
        'creado_en': mapa_obj.creado_en,
        'crop_polygon': mapa_obj.crop_polygon
    }
    
    return render_template('cartografia/recortador.html', mapa=mapa, proyecto=proyecto)

@mapas_historicos_bp.route('/cartografia/georreferenciador/<int:mapa_id>')
@login_required
def georreferenciador(mapa_id):
    m_obj = MapaHistorico.query.get_or_404(mapa_id)
    proyecto = get_proyecto_activo()
    
    # Pre-serializar el mapa principal
    mapa = {
        'id': m_obj.id,
        'nombre': m_obj.nombre,
        'filename': m_obj.filename,
        'gcps': m_obj.gcps,
        'opacidad': m_obj.opacidad,
        'visible': m_obj.visible
    }
    
    # Necesitamos todos los mapas del proyecto para las capas de referencia
    mapas_objects = MapaHistorico.query.filter_by(proyecto_id=proyecto.id).all() if proyecto else []
    mapas = []
    for m in mapas_objects:
        mapas.append({
            'id': m.id,
            'nombre': m.nombre,
            'filename': m.filename,
            'gcps': m.gcps
        })
        
    return render_template('cartografia/georreferenciador.html', mapa=mapa, proyecto=proyecto, mapas=mapas)

@mapas_historicos_bp.route('/api/mapas_historicos/upload', methods=['POST'])
@login_required
def upload_mapa():
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
        extension = filename.rsplit('.', 1)[1].lower()
        upload_dir = os.path.join(current_app.static_folder, 'uploads', 'mapas_historicos', str(proyecto.id))
        os.makedirs(upload_dir, exist_ok=True)
        
        # Prevenir colisiones de nombres añadiendo timestamp si existe
        base, ext = os.path.splitext(filename)
        final_filename = filename
        counter = 1
        while os.path.exists(os.path.join(upload_dir, final_filename)):
            final_filename = f"{base}_{counter}{ext}"
            counter += 1
            
        file_path = os.path.join(upload_dir, final_filename)
        file.save(file_path)

        # Si es PDF o TIFF, convertir a JPEG para compatibilidad con el navegador
        extracted_gcps = []
        if extension in ['pdf', 'tif', 'tiff']:
            try:
                # Nombre para el JPEG resultante
                jpeg_filename = f"{os.path.splitext(final_filename)[0]}.jpg"
                jpeg_path = os.path.join(upload_dir, jpeg_filename)
                
                # Prevenir colisión del JPEG
                counter = 1
                while os.path.exists(jpeg_path):
                    jpeg_filename = f"{os.path.splitext(final_filename)[0]}_{counter}.jpg"
                    jpeg_path = os.path.join(upload_dir, jpeg_filename)
                    counter += 1

                if extension == 'pdf':
                    import fitz
                    doc = fitz.open(file_path)
                    page = doc.load_page(0)  # Cargar primera página
                    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # Zoom 2x
                    pix.save(jpeg_path)
                    doc.close()
                else:
                    # TIFF/TIF conversion using PIL
                    from PIL import Image
                    with Image.open(file_path) as img:
                        # Convert to RGB if necessary (e.g. RGBA or CMYK TIFFs)
                        if img.mode != 'RGB':
                            rgb_img = img.convert('RGB')
                            rgb_img.save(jpeg_path, 'JPEG', quality=90)
                        else:
                            img.save(jpeg_path, 'JPEG', quality=90)
                
                # GeoTIFF Extraction
                if extension in ['tif', 'tiff']:
                    try:
                        import rasterio
                        from pyproj import Transformer
                        with rasterio.open(file_path) as src:
                            if src.crs:
                                transformer = Transformer.from_crs(src.crs, "EPSG:4326", always_xy=True)
                                points, crs = src.gcps
                                if points:
                                    current_app.logger.info(f"Detectados {len(points)} GCPs en GeoTIFF")
                                    for p in points:
                                        lon, lat = transformer.transform(p.x, p.y)
                                        # Georeferenciador usa img: [y, x] donde y es negativo
                                        extracted_gcps.append({
                                            "name": f"GeoTIFF GCP ({int(p.col)}, {int(p.row)})",
                                            "img": [-int(p.row), int(p.col)],
                                            "geo": [lat, lon]
                                        })
                                else:
                                    current_app.logger.info("No hay GCPs explícitos, generando esquinas desde geotransform")
                                    # Generar 4 esquinas
                                    corners = [(0, 0), (0, src.height), (src.width, 0), (src.width, src.height)]
                                    for c in corners:
                                        x, y = src.xy(c[1], c[0])
                                        lon, lat = transformer.transform(x, y)
                                        extracted_gcps.append({
                                            "name": f"Esquina GeoTIFF ({int(c[0])}, {int(c[1])})",
                                            "img": [-int(c[1]), int(c[0])],
                                            "geo": [lat, lon]
                                        })
                    except Exception as georef_err:
                        current_app.logger.warning(f"No se pudo extraer georreferencia del TIFF: {georef_err}")

                # Usar el JPEG como el archivo del mapa para el georreferenciador
                final_filename = jpeg_filename
                
            except Exception as e:
                current_app.logger.error(f"Error convirtiendo {extension.upper()} a imagen: {e}")
                return jsonify({"success": False, "error": f"Error al procesar {extension.upper()}: {str(e)}"}), 500

        # Generar thumbnail para optimizar carga de la página del gestor
        final_file_path = os.path.join(upload_dir, final_filename)
        generate_thumbnail(final_file_path)

        nuevo_mapa = MapaHistorico(
            proyecto_id=proyecto.id,
            nombre=request.form.get('nombre', base),
            filename=final_filename,
            gcps=json.dumps(extracted_gcps),
            anio=request.form.get('anio', type=int),
            autor=request.form.get('autor'),
            fuente=request.form.get('fuente'),
            escala=request.form.get('escala'),
            descripcion=request.form.get('descripcion'),
            licencia=request.form.get('licencia', 'CC BY 4.0')
        )
        db.session.add(nuevo_mapa)
        db.session.commit()

        return jsonify({
            "success": True, 
            "mapa": {
                "id": nuevo_mapa.id,
                "nombre": nuevo_mapa.nombre,
                "filename": nuevo_mapa.filename
            }
        })
    
    return jsonify({"success": False, "error": "Tipo de archivo no permitido"}), 400

@mapas_historicos_bp.route('/api/mapas_historicos/<int:id>/gcps', methods=['POST'])
@login_required
def save_gcps(id):
    mapa = MapaHistorico.query.get_or_404(id)
    data = request.get_json()
    
    if 'gcps' not in data:
        return jsonify({"success": False, "error": "Faltan datos de GCPs"}), 400
        
    mapa.gcps = json.dumps(data['gcps'])
    if 'opacidad' in data:
        mapa.opacidad = data['opacidad']
    if 'visible' in data:
        mapa.visible = data['visible']
        
    db.session.commit()
    return jsonify({"success": True})

@mapas_historicos_bp.route('/api/mapas_historicos/<int:id>', methods=['GET', 'POST', 'PUT', 'DELETE'])
@login_required
def api_mapas_id(id):
    mapa = MapaHistorico.query.get_or_404(id)
    
    if request.method == 'GET':
        return jsonify({
            "id": mapa.id,
            "nombre": mapa.nombre,
            "filename": mapa.filename,
            "gcps": json.loads(mapa.gcps) if mapa.gcps else [],
            "anio": mapa.anio,
            "autor": mapa.autor,
            "fuente": mapa.fuente,
            "escala": mapa.escala,
            "descripcion": mapa.descripcion
        })
        
    if request.method == 'DELETE':
        filename = mapa.filename
        proyecto_id = mapa.proyecto_id
        
        db.session.delete(mapa)
        db.session.commit()
        
        # Intentar borrar el archivo físico
        try:
            file_path = os.path.join(current_app.static_folder, 'uploads', 'mapas_historicos', str(proyecto_id), filename)
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            current_app.logger.error(f"Error al borrar archivo de mapa: {e}")
            
        return jsonify({"success": True})
        
    # POST o PUT (Actualización)
    # Soporte tanto para JSON como para FormData (para re-subida de archivos)
    if request.is_json:
        data = request.get_json()
    else:
        data = request.form.to_dict()

    if not data and not request.files:
        return jsonify({"success": False, "error": "No se enviaron datos"}), 400
        
    # Procesar archivo si se ha subido uno nuevo
    if 'file' in request.files:
        file = request.files['file']
        if file and file.filename != '' and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            proyecto_id = mapa.proyecto_id
            upload_dir = os.path.join(current_app.static_folder, 'uploads', 'mapas_historicos', str(proyecto_id))
            
            # Guardar nuevo archivo
            base, ext = os.path.splitext(filename)
            final_filename = filename
            counter = 1
            while os.path.exists(os.path.join(upload_dir, final_filename)):
                final_filename = f"{base}_{counter}{ext}"
                counter += 1
            
            file_path = os.path.join(upload_dir, final_filename)
            file.save(file_path)
            
            # Si es PDF o TIFF, convertir a JPEG (Reutilizando lógica simplificada)
            extension = final_filename.rsplit('.', 1)[1].lower()
            if extension in ['pdf', 'tif', 'tiff']:
                try:
                    jpeg_filename = f"{os.path.splitext(final_filename)[0]}.jpg"
                    jpeg_path = os.path.join(upload_dir, jpeg_filename)
                    
                    if extension == 'pdf':
                        import fitz
                        doc = fitz.open(file_path)
                        page = doc.load_page(0)
                        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                        pix.save(jpeg_path)
                        doc.close()
                    else:
                        from PIL import Image
                        with Image.open(file_path) as img:
                            if img.mode != 'RGB':
                                img.convert('RGB').save(jpeg_path, 'JPEG', quality=90)
                            else:
                                img.save(jpeg_path, 'JPEG', quality=90)
                    
                    final_filename = jpeg_filename
                except Exception as e:
                    current_app.logger.error(f"Error convirtiendo en re-upload: {e}")

            # Borrar archivo anterior y su thumbnail
            try:
                old_path = os.path.join(upload_dir, mapa.filename)
                if os.path.exists(old_path):
                    os.remove(old_path)
                
                # Borrar thumbnail anterior
                old_thumb = os.path.splitext(old_path)[0] + "_thumb.jpg"
                if os.path.exists(old_thumb):
                    os.remove(old_thumb)
            except Exception as e:
                current_app.logger.warning(f"No se pudo borrar archivo anterior: {e}")

            mapa.filename = final_filename
            # Regenerar thumbnail
            generate_thumbnail(os.path.join(upload_dir, final_filename))
            
            # Resetear recorte al cambiar imagen
            mapa.crop_polygon = None

    if 'nombre' in data:
        mapa.nombre = data['nombre']
    if 'visible' in data:
        # Manejar booleano en FormData (viene como string)
        val = data['visible']
        if isinstance(val, str):
            mapa.visible = val.lower() == 'true'
        else:
            mapa.visible = bool(val)
    if 'anio' in data:
        try:
            mapa.anio = int(data['anio']) if data['anio'] else None
        except (ValueError, TypeError):
            pass
    if 'autor' in data:
        mapa.autor = data['autor']
    if 'fuente' in data:
        mapa.fuente = data['fuente']
    if 'escala' in data:
        mapa.escala = data['escala']
    if 'descripcion' in data:
        mapa.descripcion = data['descripcion']
    if 'licencia' in data:
        mapa.licencia = data['licencia']
    
    db.session.commit()
    return jsonify({"success": True, "mapa": {"id": mapa.id, "nombre": mapa.nombre}})

@mapas_historicos_bp.route('/api/mapas_historicos/proyecto', methods=['GET'])
@login_required
def list_mapas_proyecto():
    proyecto = get_proyecto_activo()
    if not proyecto:
        return jsonify([])
    
    mapas = MapaHistorico.query.filter_by(proyecto_id=proyecto.id).all()
    resultado = []
    for m in mapas:
        if not m.gcps or m.gcps == '[]':
            continue
        try:
            gcps_data = json.loads(m.gcps)
            resultado.append({
                "id": m.id,
                "nombre": m.nombre,
                "url": f"/static/uploads/mapas_historicos/{proyecto.id}/{m.filename}",
                "gcps": gcps_data,
                "opacidad": m.opacidad or 1.0,
                "anio": m.anio,
                "visible": m.visible,
                "crop_polygon": m.crop_polygon
            })
        except (json.JSONDecodeError, TypeError) as e:
            current_app.logger.warning(f"Error al parsear GCPs del mapa {m.id}: {e}")
            continue
    return jsonify(resultado)
@mapas_historicos_bp.route('/api/mapas_historicos/<int:id>/auto_georef', methods=['POST'])
@login_required
def auto_georef(id):
    """
    Usa Gemini Vision para detectar nombres de lugares en el mapa y geocodificarlos.
    """
    mapa = MapaHistorico.query.get_or_404(id)
    proyecto = get_proyecto_activo()
    if not proyecto:
        return jsonify({"success": False, "error": "No hay proyecto activo"}), 400

    upload_dir = os.path.join(current_app.static_folder, 'uploads', 'mapas_historicos', str(proyecto.id))
    img_path = os.path.join(upload_dir, mapa.filename)

    if not os.path.exists(img_path):
        return jsonify({"success": False, "error": "Archivo de imagen no encontrado"}), 404

    try:
        import base64
        from PIL import Image
        import io

        # 1. Obtener pistas del proyecto (Ubicaciones ya conocidas)
        conocidas = db.session.query(LugarNoticia.nombre, LugarNoticia.lat, LugarNoticia.lon)\
            .join(Prensa, LugarNoticia.noticia_id == Prensa.id)\
            .filter(Prensa.proyecto_id == proyecto.id)\
            .order_by(db.func.count(LugarNoticia.id).desc())\
            .group_by(LugarNoticia.nombre, LugarNoticia.lat, LugarNoticia.lon)\
            .limit(50).all()
        
        hints = [{"name": c[0], "lat": c[1], "lon": c[2]} for c in conocidas]

        # 2. Preparar imagen
        img = Image.open(img_path)
        orig_w, orig_h = img.size
        img.thumbnail((1536, 1536))
        
        buffered = io.BytesIO()
        img.save(buffered, format="JPEG", quality=85)
        img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')

        # 3. Llamar a AI Service (Upgrade a Pro para mejor visión)
        from services.ai_service import AIService
        ai = AIService(provider='gemini', model='pro', user=current_user)
        
        if not ai.is_configured():
            return jsonify({"success": False, "error": "IA no configurada"}), 400

        prompt = f"""
        Eres un experto en cartografía histórica. Analiza esta imagen de mapa antiguo.
        TU OBJETIVO: Detectar entre 8 y 12 topónimos (nombres de lugares) claros que sirvan para georreferenciar el mapa.
        
        PISTAS DEL PROYECTO (Lugares frecuentes en los textos):
        {json.dumps([h['name'] for h in hints], ensure_ascii=False)}

        INSTRUCCIONES:
        1. Busca preferentemente los nombres de la lista de pistas en el mapa.
        2. Proporciona las coordenadas de píxel (pixel_x, pixel_y) en escala 0-1000.
        
        Responde ÚNICAMENTE con JSON:
        {{
            "points": [
                {{"name": "Nombre Detectado", "pixel_x": 500, "pixel_y": 450, "reasoning": "Breve nota"}}
            ]
        }}
        """

        raw_res = ai.generate_content(prompt, image_data=img_base64, temperature=0.1)
        data = ai._extract_json_from_text(raw_res)

        if not data or 'points' not in data:
            return jsonify({"success": False, "error": "La IA no detectó puntos válidos"}), 500

        # 4. Geocodificar con respaldo en BD
        from services.gemini_service import geocode_with_ai
        
        suggested_gcps = []
        for p in data['points']:
            # A. Intentar match exacto con hints de la BD
            match = next((h for h in hints if h['name'].lower() == p['name'].lower()), None)
            
            if match:
                geo_lat, geo_lon = match['lat'], match['lon']
                name_canonical = match['name']
                explanation = "Coincidencia exacta con ubicación del proyecto."
            else:
                # B. Si no hay match, usar geocodificación IA estándar
                geo = geocode_with_ai(p['name'], context={"proyecto": proyecto.nombre, "epoca": "histórica"})
                if geo and geo.get('found'):
                    geo_lat, geo_lon = geo['lat'], geo['lon']
                    name_canonical = geo['name_canonical']
                    explanation = geo.get('explanation', '')
                else:
                    continue

            # C. Convertir coords 0-1000 a píxeles negativos (Leaflet Simple)
            img_x = (p['pixel_x'] / 1000.0) * orig_w
            img_y = -(p['pixel_y'] / 1000.0) * orig_h
            
            suggested_gcps.append({
                "name": name_canonical,
                "img": [img_y, img_x],
                "geo": [geo_lat, geo_lon],
                "confidence": 0.9 if match else 0.7,
                "reasoning": explanation or p.get('reasoning', '')
            })

        return jsonify({
            "success": True,
            "suggestions": suggested_gcps
        })

    except Exception as e:
        current_app.logger.error(f"Error en auto_georef: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
@mapas_historicos_bp.route('/api/mapas_historicos/<int:id>/export', methods=['GET'])
@login_required
def export_gis_data(id):
    mapa = MapaHistorico.query.get_or_404(id)
    format_type = request.args.get('format', 'csv')
    
    if not mapa.gcps or mapa.gcps == '[]':
        return jsonify({"success": False, "error": "No hay puntos de control para exportar"}), 400
    
    data = json.loads(mapa.gcps)
    points = data if isinstance(data, list) else data.get('points', [])
    
    import io
    output = io.StringIO()
    
    if format_type == 'csv':
        import csv
        writer = csv.writer(output)
        writer.writerow(['ID', 'PixelX', 'PixelY', 'Lat', 'Lon', 'Name'])
        for i, p in enumerate(points):
            try:
                # Validar que los puntos tengan la estructura correcta
                if not isinstance(p, dict) or 'img' not in p or 'geo' not in p:
                    current_app.logger.warning(f"Punto {i} tiene estructura inválida: {p}")
                    continue
                img_x = float(p['img'][1]) if len(p['img']) > 1 else 0
                img_y = float(p['img'][0]) if len(p['img']) > 0 else 0
                geo_lat = float(p['geo'][0]) if len(p['geo']) > 0 else 0
                geo_lon = float(p['geo'][1]) if len(p['geo']) > 1 else 0
                writer.writerow([i+1, img_x, -img_y, geo_lat, geo_lon, p.get('name', '')])
            except (KeyError, TypeError, ValueError, IndexError) as e:
                current_app.logger.error(f"Error procesando punto {i}: {e}")
                continue
        
        filename = f"{os.path.splitext(mapa.filename)[0]}_gcps.csv"
        mimetype = 'text/csv'
        
    elif format_type == 'wld':
        # Generar World File (Afín de 6 parámetros)
        try:
            import numpy as np
            import math
            
            if len(points) < 3:
                 return jsonify({"success": False, "error": "Se necesitan al menos 3 puntos para generar un World File válido"}), 400
            
            # Cálculo de matriz afín: u = Ax + By + C, v = Dx + Ey + F
            # x, y son coordenadas de imagen (p[img][1], -p[img][0])
            # u, v son coordenadas geográficas (p[geo][1], p[geo][0])
            
            # Preparamos las matrices para resolver el sistema de ecuaciones
            # x*A + y*B + 1*C = u
            # x*D + y*E + 1*F = v
            
            X = []
            U = []
            V = []
            
            for p in points[:10]: # Usamos hasta 10 puntos para un ajuste por mínimos cuadrados
                try:
                    # Validar estructuras
                    if not isinstance(p, dict) or 'img' not in p or 'geo' not in p:
                        continue
                    if len(p['img']) < 2 or len(p['geo']) < 2:
                        current_app.logger.warning(f"Punto tiene estructura incompleta: {p}")
                        continue
                    img_x = float(p['img'][1])
                    img_y = -float(p['img'][0]) # Invertimos Y para que sea positivo desde arriba
                    geo_lon = float(p['geo'][1])
                    geo_lat = float(p['geo'][0])
                    if not (math.isfinite(img_x) and math.isfinite(img_y) and math.isfinite(geo_lat) and math.isfinite(geo_lon)):
                        continue
                    X.append([img_x, img_y, 1])
                    U.append(geo_lon)
                    V.append(geo_lat)
                except (KeyError, TypeError, ValueError, IndexError) as e:
                    current_app.logger.warning(f"Error validando punto para World File: {e}")
                    continue
            
            X = np.array(X)
            U = np.array(U)
            V = np.array(V)
            
            # Resolver por mínimos cuadrados: X * [A, B, C]^T = U
            sol_u, _, _, _ = np.linalg.lstsq(X, U, rcond=None)
            sol_v, _, _, _ = np.linalg.lstsq(X, V, rcond=None)
            
            A, B, C = sol_u
            D, E, F = sol_v
            
            # Formato World File (.wld):
            # Line 1: A (Dimension de pixel en X)
            # Line 2: D (Rotación en Y)
            # Line 3: B (Rotación en X)
            # Line 4: E (Dimensión de pixel en Y, usualmente negativo)
            # Line 5: C (Coordenada X del centro del pixel superior izquierdo 0,0)
            # Line 6: F (Coordenada Y del centro del pixel superior izquierdo 0,0)
            
            output.write(f"{A:.12f}\n")
            output.write(f"{D:.12f}\n")
            output.write(f"{B:.12f}\n")
            output.write(f"{E:.12f}\n")
            output.write(f"{C:.12f}\n")
            output.write(f"{F:.12f}\n")
            
        except Exception as e:
            current_app.logger.error(f"Error generando World File: {e}")
            return jsonify({"success": False, "error": "Error interno al calcular la matriz afín"}), 500
            
        filename = f"{os.path.splitext(mapa.filename)[0]}.wld"
        mimetype = 'text/plain'
    
    from flask import Response
    return Response(
        output.getvalue(),
        mimetype=mimetype,
        headers={"Content-disposition": f"attachment; filename={filename}"}
    )


@mapas_historicos_bp.route('/api/mapas_historicos/crop', methods=['POST'])
@login_required
def save_crop_polygon():
    """Guardar polígono de recorte y procesarla imagen para eliminar márgenes del mapa"""
    data = request.get_json()
    mapa_id = data.get('id')
    crop_polygon = data.get('crop_polygon')
    rotation = data.get('rotation', 0)  # Nueva propiedad para rotación
    
    # Parsear crop_polygon si es string (JSON)
    if isinstance(crop_polygon, str):
        try:
            crop_polygon = json.loads(crop_polygon)
        except Exception:
            pass
    
    # Asegurarnos de que tenemos una lista válida
    if not isinstance(crop_polygon, list) or len(crop_polygon) < 3:
        return jsonify({'success': False, 'error': 'Polígono de recorte inválido'})
    
    if not mapa_id:
        return jsonify({'success': False, 'error': 'ID de mapa requerido'})
    
    mapa = MapaHistorico.query.get_or_404(mapa_id)
    
    # Verificar que el mapa pertenece al proyecto activo del usuario
    from utils import get_proyecto_activo
    proyecto = get_proyecto_activo()
    if not proyecto or mapa.proyecto_id != proyecto.id:
        return jsonify({'success': False, 'error': 'Acceso denegado'})
    
    # Procesar la imagen físicamente
    try:
        from PIL import Image, ImageDraw
        import numpy as np
        
        # Usar la imagen ACTUAL que ve el usuario (para concordancia de coordenadas)
        upload_dir = os.path.join(current_app.static_folder, 'uploads', 'mapas_historicos', str(proyecto.id))
        source_path = os.path.join(upload_dir, mapa.filename)
        
        if not os.path.exists(source_path):
            return jsonify({'success': False, 'error': 'Imagen fuente no encontrada'}), 404
            
        # Calcular Bounding Box del recorte
        x_coords = [p[0] for p in crop_polygon]
        y_coords = [p[1] for p in crop_polygon]
        min_x = max(0, int(min(x_coords)))
        min_y = max(0, int(min(y_coords)))
        max_x = int(max(x_coords))
        max_y = int(max(y_coords))
        
        # Abrir imagen fuente
        with Image.open(source_path) as img_source:
            img = img_source.convert('RGBA')
            
            # Aplicar rotación si es necesario (expand=True ajusta el tamaño del canvas)
            if rotation:
                # PIL rota en sentido antihorario, el frontend en horario. Invertimos.
                img = img.rotate(-float(rotation), expand=True)
            
            # Dimensiones de la imagen (ya rotada si aplica)
            width, height = img.size
            
            # Validar coordenadas contra dimensiones reales
            # El frontend envía coordenadas relativas a la imagen visual (rotada)
            x_coords = [p[0] for p in crop_polygon]
            y_coords = [p[1] for p in crop_polygon]
            
            if not x_coords or not y_coords:
                 return jsonify({'success': False, 'error': 'Polígono inválido'})
                 
            min_x = max(0, int(min(x_coords)))
            min_y = max(0, int(min(y_coords)))
            max_x = min(width, int(max(x_coords)))
            max_y = min(height, int(max(y_coords)))
            
            # 1. Crear máscara del tamaño de la imagen (rotada)
            mask = Image.new('L', (width, height), 0)
            draw = ImageDraw.Draw(mask)
            
            # Dibujar polígono en la máscara
            # Puntos ya vienen en coordenadas de la imagen visual
            draw.polygon([(p[0], p[1]) for p in crop_polygon], fill=255)
            
            # 2. Crear nueva imagen transparente
            result = Image.new('RGBA', (width, height), (0, 0, 0, 0))
            
            # Pegar usando la máscara
            result.paste(img, (0, 0), mask)
            
            # 3. Recortar al Bounding Box del polígono
            cropped = result.crop((min_x, min_y, max_x, max_y))
            
            # ----------------------------------------------------------------
            # CORRECCIÓN DE GCPs (Georreferenciación)
            # Al recortar, el origen (0,0) se desplaza a (min_x, min_y).
            # Los GCPs existentes (img_y, img_x) referentes a la imagen original deben actualizarse.
            # Nota: img_y se almacena como negativo (Leaflet convention).
            if mapa.gcps and mapa.gcps != '[]' and not rotation:
                try:
                    gcps_list = json.loads(mapa.gcps)
                    updated_gcps = []
                    for g in gcps_list:
                        # g['img'] es [y, x] donde y es negativo
                        old_y_neg = g['img'][0]
                        old_x = g['img'][1]
                        
                        # Nuevo X = X_original - min_x (desplazamiento a la izquierda)
                        new_x = old_x - min_x
                        
                        # Nuevo Y (negativo) = Y_original (negativo) + min_y 
                        # Explicación: Si Y_orig = -100 (pixel 100) y recorto 20px arriba (min_y=20),
                        # el nuevo pixel es 80, por tanto Y_new = -80.
                        # -100 + 20 = -80. Correcto.
                        new_y_neg = old_y_neg + min_y
                        
                        g['img'] = [new_y_neg, new_x]
                        updated_gcps.append(g)
                    
                    mapa.gcps = json.dumps(updated_gcps)
                except Exception as ex_gcp:
                    current_app.logger.error(f"Error actualizando GCPs tras recorte: {ex_gcp}")
            # ----------------------------------------------------------------

            # Guardar sobrescribiendo (backup recomendado en producción, aquí asumimos destructivo)
            # Convertir a RGB si era jpg original para ahorrar espacio, o mantener PNG?
            # Si tiene transparencia, debe ser PNG. Si el original era JPG, ahora es PNG.
            # Pero el filename manda. Si original era .jpg, no soporta transparencia.
            # Para mapas históricos, lo ideal es mantener transparencia.
            
            name, ext = os.path.splitext(source_path)
            if ext.lower() in ['.jpg', '.jpeg']:
                # Forzar guardado como PNG para transparencia
                output_path = name + '.png'
                # Actualizar registro en DB
                mapa.filename = os.path.basename(output_path)
                db.session.commit()
                # Eliminar antiguo jpg
                if os.path.exists(source_path):
                    os.remove(source_path)
            else:
                output_path = source_path

            cropped.save(output_path)
            
            # 4. Actualizar metadata de recorte en la DB
            mapa.crop_polygon = json.dumps(crop_polygon)
            db.session.commit()

            # 5. Regenerar thumbnail para que refleje el recorte
            generate_thumbnail(output_path)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'Error procesando imagen: {str(e)}'})

    return jsonify({'success': True})
