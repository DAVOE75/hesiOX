from flask import Blueprint, render_template, jsonify, request, url_for
from flask_login import login_required, current_user
from models import Prensa, Proyecto
from utils import get_proyecto_activo, validar_fecha_ddmmyyyy
from extensions import db
from sqlalchemy import text
from datetime import datetime

visualizaciones_bp = Blueprint('visualizaciones', __name__)

@visualizaciones_bp.route('/timeline', methods=['GET'])
@login_required
def timeline():
    """Renderiza la vista de línea de tiempo"""
    proyecto = get_proyecto_activo()
    if not proyecto:
        return render_template('timeline.html', items=[], proyecto=None)
    
    return render_template('timeline.html', proyecto=proyecto)

@visualizaciones_bp.route('/api/timeline-data', methods=['GET'])
@login_required
def api_timeline_data():
    """
    API que devuelve los datos para el timeline en formato JSON compatible con Vis.js
    """
    proyecto = get_proyecto_activo()
    if not proyecto:
        return jsonify([])

    # Consultar noticias del proyecto
    # Filtramos aquellas que tengan fecha_original no nula
    query = Prensa.query.filter_by(proyecto_id=proyecto.id, incluido=True).filter(Prensa.fecha_original != None).filter(Prensa.fecha_original != '')
    
    noticias = query.all()
    timeline_items = []

    for noticia in noticias:
        # Intentar parsear la fecha
        fecha_str = noticia.fecha_original
        fecha_obj = None
        
        # Soportar varios formatos: DD/MM/YYYY, YYYY-MM-DD, YYYY
        try:
            # Intentar parseo básico
            if "/" in fecha_str:
                parts = fecha_str.split("/")
                if len(parts) == 3:
                     # Vis.js acepta strings YYYY-MM-DD o objetos Date
                     # Convertimos a YYYY-MM-DD
                     fecha_obj = datetime.strptime(fecha_str, "%d/%m/%Y")
            elif "-" in fecha_str:
                # Formato ISO YYYY-MM-DD
                parts = fecha_str.split("-")
                if len(parts) == 3:
                     fecha_obj = datetime.strptime(fecha_str, "%Y-%m-%d")
            elif len(fecha_str) == 4 and fecha_str.isdigit():
                # Solo año -> 01/01/YYYY
                fecha_obj = datetime(int(fecha_str), 1, 1)
        except:
            pass
            
        if fecha_obj:
            start_date = fecha_obj.strftime("%Y-%m-%d")
            
            # Construir item para Vis.js
            item = {
                "id": noticia.id,
                "content": f"<div class='item-date'>{fecha_str}</div><div class='item-title'>{noticia.titulo or 'Sin título'}</div>",
                "start": start_date,
                "titulo_completo": noticia.titulo,
                "nombre_publicacion": noticia.publicacion,
                "ciudad": noticia.ciudad,
                "url_editar": url_for('noticias.editar', id=noticia.id),
                "className": "sirio-timeline-item",
                # Data adicional para filtros o estilos
                "group": noticia.publicacion or "General",
                "type": "box" # O 'point'
            }
            
            # Añadir indicador de día de la semana para estilo
            # week_days = ["DOM", "LUN", "MAR", "MIE", "JUE", "VIE", "SAB"]
            # isoweekday: 1=Mon, 7=Sun
            days_es = ["LUN", "MAR", "MIE", "JUE", "VIE", "SAB", "DOM"]
            day_idx = fecha_obj.weekday()
            
            # Inyectamos atributo data-weekday en el elemento DOM mediante template string en content?
            # Vis.js permite 'template' functions, pero aquí pasamos string HTML.
            # Mejor usamos una clase o dejamos que el CSS actúe si podemos pasar atributos.
            # Alternativamente, modificamos el content para incluirlo.
                        # Tarjeta profesional: título arriba, color, icono clic
            item["content"] = f"""
<div class='sirio-timeline-item' data-weekday='{days_es[day_idx]}'>
    <div class='item-title'>
        <span class='title-text'>{noticia.titulo or 'Sin título'}</span>
        <span class='timeline-icon' title='Ver detalles'><i class='fa-solid fa-magnifying-glass'></i></span>
    </div>
    <div class='item-date'>{fecha_str}</div>
</div>
"""
            
            # NOTE: En timeline.html el CSS espera .sirio-timeline-item dentro de .vis-item
            # Pero en la configuración de Vis.js, si item.className es 'sirio-timeline-item',
            # la clase se aplica al contenedor .vis-item.
            # El CSS en timeline.html linea 208: .sirio-timeline-item { ... }
            # Y linea 239: .vis-item:hover .sirio-timeline-item { ... }
            # Esto sugiere que .sirio-timeline-item es un HIJO del elemento vis-item actual.
            # Por lo tanto, mi construcción del HTML en 'content' es CORRECTA.
            # Y la propiedad className del item debe ser algo genérico o vacío para no interferir,
            # o quizás 'vis-item-transparent' si queremos quitar bordes por defecto.
            # timeline.html linea 174 limpia .vis-item.
            
            item["className"] = "" # Dejamos limpio, el CSS de timeline.html se encarga del .vis-item global

            timeline_items.append(item)

    return jsonify(timeline_items)

@visualizaciones_bp.route('/api/noticia/<int:id>', methods=['GET'])
@login_required
def api_noticia_detalle(id):
    """
    API para obtener detalles de una noticia específica (resumen y contenido)
    para el modal del timeline.
    """
    noticia = db.session.get(Prensa, id)
    proyecto = get_proyecto_activo()

    if not noticia:
        return jsonify({"error": "Noticia no encontrada"}), 404
    
    # IDOR check: asegurar que la noticia pertenece al proyecto activo
    if not proyecto or noticia.proyecto_id != proyecto.id:
        return jsonify({"error": "Acceso no autorizado a esta noticia"}), 403
    
    return jsonify({
        "id": noticia.id,
        "titulo": noticia.titulo,
        "resumen": noticia.resumen,
        "contenido": noticia.contenido or "<em>Sin contenido disponible.</em>"
    })
