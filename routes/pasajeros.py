import json
import os
import io
import pandas as pd
import pdfkit
from datetime import datetime
from werkzeug.utils import secure_filename
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, flash, current_app, send_file
from flask_login import login_required, current_user
from sqlalchemy.orm import joinedload, selectinload
from models import PasajeroSirio, Proyecto, Publicacion, Prensa, PasajeroRelacion
from extensions import db
from sqlalchemy import func
from services.ai_service import AIService

# Tipos de recursos para Prensa y Listas
PRENSA_TYPES = ['Prensa', 'prensa', 'Diario', 'revista', 'Semanario', 'Boletín', 'boletin']

pasajeros_bp = Blueprint('pasajeros', __name__, url_prefix='/pasajeros')
per_page = 50

def check_sirio_access():
    proyecto_id = session.get('proyecto_activo_id')
    if not proyecto_id or str(proyecto_id) != '1':
        return False
    return True

def get_filtered_pasajeros_query(args):
    query = PasajeroSirio.query.options(
        selectinload(PasajeroSirio.relaciones_como_sujeto),
        selectinload(PasajeroSirio.relaciones_como_objeto),
        selectinload(PasajeroSirio.publicaciones)
    )
    
    # Filtros opcionales
    search = args.get('search', '')
    if search:
        query = query.filter(
            (PasajeroSirio.nombre.ilike(f'%{search}%')) | 
            (PasajeroSirio.apellidos.ilike(f'%{search}%')) |
            (PasajeroSirio.municipio.ilike(f'%{search}%'))
        )
    
    # Filtro por estado
    estado_filter = args.get('estado', '')
    if estado_filter:
        query = query.filter(PasajeroSirio.estado == estado_filter)

    sexo_filter = args.get('sexo', '')
    if sexo_filter:
        query = query.filter(PasajeroSirio.sexo == sexo_filter)

    pasaje_filter = args.get('pasaje', '')
    if pasaje_filter:
        query = query.filter(PasajeroSirio.pasaje.ilike(f'%{pasaje_filter}%'))

    puerto_filter = args.get('puerto', '')
    if puerto_filter:
        query = query.filter(PasajeroSirio.puerto_embarque.ilike(f'%{puerto_filter}%'))

    destino_filter = args.get('destino', '')
    if destino_filter:
        query = query.filter(PasajeroSirio.ciudad_destino_final.ilike(f'%{destino_filter}%'))

    edad_min = args.get('edad_min', '')
    edad_max = args.get('edad_max', '')
    if edad_min:
        try: query = query.filter(PasajeroSirio.edad >= float(edad_min))
        except: pass
    if edad_max:
        try: query = query.filter(PasajeroSirio.edad <= float(edad_max))
        except: pass
    
    # Filtro por Nacionalidad (País)
    nacionalidad_filter = args.get('nacionalidad', '')
    if nacionalidad_filter:
        query = query.filter(PasajeroSirio.pais.ilike(f'%{nacionalidad_filter}%'))
    
    # Filtro por Fuente de Presencia (Publicación)
    fuentepub_filter = args.get('fuentepub', '')
    if fuentepub_filter:
        query = query.filter(PasajeroSirio.publicaciones.any(Publicacion.id_publicacion == int(fuentepub_filter)))
    
    # Filtro de Solo Prensa / Solo Listas
    solo_prensa = args.get('solo_prensa', '')
    if solo_prensa == '1':
        # Mostrar solo pasajeros con alguna fuente de prensa
        query = query.filter(PasajeroSirio.publicaciones.any(Publicacion.tipo_recurso.in_(PRENSA_TYPES)))
    else:
        # A petición del usuario (actualizado): Por defecto mostrar TODOS los pasajeros
        # Se asegura que la query base sea limpia y no contenga joins restrictivos
        pass
    
    # Filtros de embarque
    lista_filter = args.get('lista', '')
    if lista_filter == 'I-B':
        query = query.filter(PasajeroSirio.en_lista_italia_ba == True)
    elif lista_filter == 'I-M':
        query = query.filter(PasajeroSirio.en_lista_italia_mvd == True)
    elif lista_filter == 'R-S':
        query = query.filter(PasajeroSirio.en_lista_ravena_sp == True)
    elif lista_filter == 'O-G':
        query = query.filter(PasajeroSirio.en_lista_orione_ge == True)

    return query

@pasajeros_bp.route('/listado')
@login_required
def listado():
    if not check_sirio_access():
        return render_template('errors/403.html'), 403
    
    # Nos saltamos la paginación a petición del usuario
    page = 1
    
    # DEBUG: Investigar 904 vs 938
    query = get_filtered_pasajeros_query(request.args)
    total_db = PasajeroSirio.query.count()
    total_filtered = query.count()
    
    with open('/tmp/pasajeros_debug.log', 'a') as f:
        f.write(f"\n[{datetime.now()}] listado() - Args: {request.args}\n")
        f.write(f"Total DB: {total_db} | Total Filtered: {total_filtered}\n")
        f.write(f"SQL: {str(query)}\n")
    
    # Ordenación
    sort_by = request.args.get('sort', 'apellidos')
    order = request.args.get('order', 'asc')
    
    if sort_by == 'nombre':
        query = query.order_by(PasajeroSirio.nombre.asc() if order == 'asc' else PasajeroSirio.nombre.desc())
    elif sort_by == 'edad':
        query = query.order_by(PasajeroSirio.edad.asc() if order == 'asc' else PasajeroSirio.edad.desc())
    else: # Por defecto apellidos
        query = query.order_by(PasajeroSirio.apellidos.asc() if order == 'asc' else PasajeroSirio.apellidos.desc())
    
    total_count = query.count()
    # DEBUG: Para investigar discrepancia 904 vs 938
    print(f"DEBUG: listado() total_count={total_count} | Raw count: {PasajeroSirio.query.count()}")
    
    total_pages = 1
    pasajeros = query.all()
    
    # Todas las publicaciones del proyecto Sirio para el dropdown inicial
    # Filtramos según el estado inicial de solo_prensa
    # NOTA: Excluimos Italia(393), Ravena(394), Orione(395) y duplicado Maria Luisa(402)
    solo_prensa_val = request.args.get('solo_prensa', '')
    publicaciones_q = Publicacion.query.join(Publicacion.pasajeros_sirio)\
        .filter(Publicacion.proyecto_id == 1)\
        .filter(Publicacion.id_publicacion.notin_([393, 394, 395, 402]))
        
    if solo_prensa_val == '1':
        publicaciones_q = publicaciones_q.filter(Publicacion.tipo_recurso.in_(PRENSA_TYPES))
    else:
        # Por defecto o si no es solo_prensa, mostrar solo listados
        publicaciones_q = publicaciones_q.filter(Publicacion.tipo_recurso == 'Lista de Pasajeros')
        
    publicaciones = publicaciones_q.distinct().order_by(Publicacion.nombre).all()

    # Valores únicos iniciales para los selectores de filtro
    puertos = db.session.query(PasajeroSirio.puerto_embarque).filter(
        PasajeroSirio.puerto_embarque.isnot(None), PasajeroSirio.puerto_embarque != '').distinct().order_by(PasajeroSirio.puerto_embarque).all()
    destinos = db.session.query(PasajeroSirio.ciudad_destino_final).filter(
        PasajeroSirio.ciudad_destino_final.isnot(None),
        PasajeroSirio.ciudad_destino_final != ''
    ).distinct().order_by(PasajeroSirio.ciudad_destino_final).all()
    nacionalidades = db.session.query(PasajeroSirio.pais).filter(
        PasajeroSirio.pais.isnot(None),
        PasajeroSirio.pais != ''
    ).distinct().order_by(PasajeroSirio.pais).all()

    filters = {k: request.args.get(k, '') for k in [
        'search', 'estado', 'sexo', 'pasaje', 'puerto', 'destino', 
        'edad_min', 'edad_max', 'lista', 'fuentepub', 'nacionalidad', 'solo_prensa'
    ]}
    
    return render_template('pasajeros/listado.html', 
                           pasajeros=pasajeros, 
                           total_count=total_count,
                           page=page,
                           total_pages=total_pages,
                           publicaciones=publicaciones,
                           puertos=[p[0] for p in puertos],
                           destinos=[d[0] for d in destinos],
                           nacionalidades=[n[0] for n in nacionalidades],
                           sort_by=sort_by,
                           order=order,
                           filters=filters,
                           max=max, min=min,
                           **filters)

@pasajeros_bp.route('/filtrar')
@login_required
def filtrar():
    if not check_sirio_access():
        return jsonify({'error': 'No autorizado'}), 403
        
    # Nos saltamos la paginación a petición del usuario
    page = 1
    
    # Query filtrada para los resultados
    query = get_filtered_pasajeros_query(request.args)
    
    # Ordenación
    sort_by = request.args.get('sort', 'apellidos')
    order = request.args.get('order', 'asc')
    if sort_by == 'nombre':
        query = query.order_by(PasajeroSirio.nombre.asc() if order == 'asc' else PasajeroSirio.nombre.desc())
    elif sort_by == 'edad':
        query = query.order_by(PasajeroSirio.edad.asc() if order == 'asc' else PasajeroSirio.edad.desc())
    else:
        query = query.order_by(PasajeroSirio.apellidos.asc() if order == 'asc' else PasajeroSirio.apellidos.desc())
        
    total_count = query.count()
    total_pages = 1
    pasajeros = query.all()
    
    # HTML Parcial
    html = render_template('pasajeros/_tabla_pasajeros.html', 
                           pasajeros=pasajeros, 
                           total_count=total_count,
                           page=page,
                           total_pages=total_pages,
                           sort_by=sort_by,
                           order=order,
                           max=max, min=min)
    
    # Para estadísticas (filtros adaptativos), limpiamos el order_by previo para evitar errores de SQL (DISTINCT vs ORDER BY)
    query_stats = query.order_by(None)
    
    # Nacionalidades (basado en el campo 'pais')
    nacionalidades_f = [r[0] for r in query_stats.with_entities(PasajeroSirio.pais).filter(PasajeroSirio.pais.isnot(None), PasajeroSirio.pais != '').distinct().order_by(PasajeroSirio.pais).all()]
    puertos_f = [r[0] for r in query_stats.with_entities(PasajeroSirio.puerto_embarque).filter(PasajeroSirio.puerto_embarque.isnot(None), PasajeroSirio.puerto_embarque != '').distinct().order_by(PasajeroSirio.puerto_embarque).all()]
    destinos_f = [r[0] for r in query_stats.with_entities(PasajeroSirio.ciudad_destino_final).filter(PasajeroSirio.ciudad_destino_final.isnot(None), PasajeroSirio.ciudad_destino_final != '').distinct().order_by(PasajeroSirio.ciudad_destino_final).all()]
    
    # Para fuentes (publicaciones), filtramos según el toggle de solo_prensa
    # NOTA: Excluimos Italia(393), Ravena(394), Orione(395) y duplicado Maria Luisa(402)
    solo_prensa_val = request.args.get('solo_prensa', '')
    publicaciones_q = db.session.query(Publicacion.id_publicacion, Publicacion.nombre)\
        .join(Publicacion.pasajeros_sirio)\
        .filter(PasajeroSirio.id.in_(query_stats.with_entities(PasajeroSirio.id)))\
        .filter(Publicacion.id_publicacion.notin_([393, 394, 395, 402]))
        
    if solo_prensa_val == '1':
        publicaciones_q = publicaciones_q.filter(Publicacion.tipo_recurso.in_(PRENSA_TYPES))
    else:
        publicaciones_q = publicaciones_q.filter(Publicacion.tipo_recurso == 'Lista de Pasajeros')
        
    publicaciones_f = publicaciones_q.distinct().order_by(Publicacion.nombre).all()

    return jsonify({
        'html': html,
        'total_count': total_count,
        'options': {
            'nacionalidad': [{'value': n, 'label': n} for n in nacionalidades_f],
            'puerto': [{'value': p, 'label': p} for p in puertos_f],
            'destino': [{'value': d, 'label': d} for d in destinos_f],
            'fuentepub': [{'value': p[0], 'label': p[1]} for p in publicaciones_f]
        }
    })

@pasajeros_bp.route('/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo():
    if not check_sirio_access():
        return render_template('errors/403.html'), 403
        
    if request.method == 'POST':
        try:
            pasajero = PasajeroSirio(
                nombre=request.form.get('nombre'),
                apellidos=request.form.get('apellidos'),
                edad=float(request.form.get('edad')) if request.form.get('edad') else None,
                sexo=request.form.get('sexo'),
                pasaje=request.form.get('pasaje'),
                municipio=request.form.get('municipio'),
                provincia=request.form.get('provincia'),
                region=request.form.get('region'),
                puerto_embarque=request.form.get('puerto_embarque'),
                ciudad_destino=request.form.get('ciudad_destino'),
                ciudad_destino_final=request.form.get('ciudad_destino_final'),
                estado=request.form.get('estado'),
                punto_residencia=request.form.get('punto_residencia'),
                hospedaje_cartagena=request.form.get('hospedaje_cartagena') or request.form.get('residencia_cartagena'),
                en_lista_italia_mvd=True if request.form.get('en_lista_italia_mvd') else False,
                en_lista_italia_ba=True if request.form.get('en_lista_italia_ba') else False,
                en_lista_ravena_sp=True if request.form.get('en_lista_ravena_sp') else False,
                en_lista_diana_bcn=True if request.form.get('en_lista_diana_bcn') else False,
                en_lista_orione_ge=True if request.form.get('en_lista_orione_ge') else False,
                comentarios=request.form.get('comentarios'),
                pais=request.form.get('pais'),
                fecha_emb_napoles=request.form.get('fecha_emb_napoles'),
                fecha_emb_genova=request.form.get('fecha_emb_genova'),
                fecha_emb_barcelona=request.form.get('fecha_emb_barcelona'),
                situacion_post_naufragio=request.form.get('situacion_post_naufragio'),
                puerto_retorno=request.form.get('puerto_retorno'),
                fecha_retorno=request.form.get('fecha_retorno')
            )
            
            pub_ids = request.form.getlist('publicaciones')
            if pub_ids:
                selected_pubs = Publicacion.query.filter(Publicacion.id_publicacion.in_(pub_ids)).all()
                for p in selected_pubs:
                    pasajero.publicaciones.append(p)
            
            # Gestión de foto
            if 'foto' in request.files:
                file = request.files['foto']
                if file and file.filename:
                    filename = secure_filename(f"pasajero_{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}")
                    upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'pasajeros')
                    os.makedirs(upload_path, exist_ok=True)
                    file.save(os.path.join(upload_path, filename))
                    pasajero.foto = filename
            db.session.add(pasajero)
            db.session.commit()
            flash('Pasajero añadido correctamente', 'success')
            return redirect(url_for('pasajeros.ficha', id=pasajero.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al añadir pasajero: {str(e)}', 'danger')
            
    publicaciones = Publicacion.query.order_by(Publicacion.nombre).all()
    return render_template('pasajeros/form.html', action='nuevo', publicaciones=publicaciones)

@pasajeros_bp.route('/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar(id):
    if not check_sirio_access():
        return render_template('errors/403.html'), 403
        
    pasajero = PasajeroSirio.query.get_or_404(id)
    
    # Todos los pasajeros (optimizado: solo campos necesarios)
    todos_pasajeros = db.session.query(PasajeroSirio.id, PasajeroSirio.nombre, PasajeroSirio.apellidos).order_by(PasajeroSirio.apellidos).all()
    
    # Relaciones actuales (ordenadas)
    relaciones_directas = sorted(pasajero.relaciones_como_sujeto, key=lambda r: r.orden or 0)
    relaciones_inversas = pasajero.relaciones_como_objeto

    if request.method == 'POST':
        # DIAGNÓSTICO TEMPORAL
        napoles = request.form.get('fecha_emb_napoles')
        situacion = request.form.get('situacion_post_naufragio')
        msg = f"DIAGNÓSTICO POST: Napoles='{napoles}', Situacion='{situacion}'"
        print(msg)
        flash(msg, 'info')
        try:
            pasajero.nombre = request.form.get('nombre')
            pasajero.apellidos = request.form.get('apellidos')
            pasajero.edad = float(request.form.get('edad')) if request.form.get('edad') else None
            pasajero.sexo = request.form.get('sexo')
            pasajero.pasaje = request.form.get('pasaje')
            pasajero.municipio = request.form.get('municipio')
            pasajero.provincia = request.form.get('provincia')
            pasajero.region = request.form.get('region')
            pasajero.punto_residencia = request.form.get('punto_residencia')
            pasajero.puerto_embarque = request.form.get('puerto_embarque')
            pasajero.ciudad_destino = request.form.get('ciudad_destino')
            pasajero.ciudad_destino_final = request.form.get('ciudad_destino_final')
            pasajero.estado = request.form.get('estado')
            pasajero.hospedaje_cartagena = request.form.get('hospedaje_cartagena') or request.form.get('residencia_cartagena')
            pasajero.en_lista_italia_mvd = True if request.form.get('en_lista_italia_mvd') else False
            pasajero.en_lista_italia_ba = True if request.form.get('en_lista_italia_ba') else False
            pasajero.en_lista_ravena_sp = True if request.form.get('en_lista_ravena_sp') else False
            pasajero.en_lista_diana_bcn = True if request.form.get('en_lista_diana_bcn') else False
            pasajero.en_lista_orione_ge = True if request.form.get('en_lista_orione_ge') else False
            pasajero.comentarios = request.form.get('comentarios')
            pasajero.pais = request.form.get('pais')
            
            # Nuevos campos de itinerario
            pasajero.fecha_emb_napoles = request.form.get('fecha_emb_napoles')
            pasajero.fecha_emb_genova = request.form.get('fecha_emb_genova')
            pasajero.fecha_emb_barcelona = request.form.get('fecha_emb_barcelona')
            pasajero.fecha_hundimiento = request.form.get('fecha_hundimiento')
            pasajero.fecha_llegada_cartagena = request.form.get('fecha_llegada_cartagena')
            pasajero.fecha_salida_cartagena = request.form.get('fecha_salida_cartagena')
            pasajero.situacion_post_naufragio = request.form.get('situacion_post_naufragio')
            pasajero.puerto_retorno = request.form.get('puerto_retorno')
            pasajero.fecha_retorno = request.form.get('fecha_retorno')

            # Limpieza de valores "None" accidentales
            for attr in ['fecha_emb_napoles', 'fecha_emb_genova', 'fecha_emb_barcelona', 
                        'fecha_hundimiento', 'fecha_llegada_cartagena', 'fecha_salida_cartagena',
                        'fecha_retorno', 'puerto_retorno', 'ciudad_destino', 'ciudad_destino_final']:
                val = getattr(pasajero, attr)
                if val == 'None' or val == 'none':
                    setattr(pasajero, attr, '')
            
            pub_ids = request.form.getlist('publicaciones')
            pasajero.publicaciones = []
            if pub_ids:
                selected_pubs = Publicacion.query.filter(Publicacion.id_publicacion.in_(pub_ids)).all()
                for p in selected_pubs:
                    pasajero.publicaciones.append(p)
            
            # Gestión de foto
            if 'foto' in request.files:
                file = request.files['foto']
                if file and file.filename:
                    filename = secure_filename(f"pasajero_{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}")
                    upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'pasajeros')
                    os.makedirs(upload_path, exist_ok=True)
                    file.save(os.path.join(upload_path, filename))
                    pasajero.foto = filename
            db.session.add(pasajero)
            db.session.commit()
            flash('Datos del pasajero actualizados', 'success')
            return redirect(url_for('pasajeros.ficha', id=pasajero.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar: {str(e)}', 'danger')
            
    publicaciones = Publicacion.query.order_by(Publicacion.nombre).all()
    
    return render_template('pasajeros/form.html', 
                         pasajero=pasajero, 
                         action='editar', 
                         todos_pasajeros=todos_pasajeros,
                         relaciones_directas=relaciones_directas,
                         relaciones_inversas=relaciones_inversas,
                         publicaciones=publicaciones)

@pasajeros_bp.route('/eliminar/<int:id>', methods=['POST'])
@login_required
def eliminar(id):
    if not check_sirio_access():
        return jsonify({'error': 'No autorizado'}), 403
        
    pasajero = PasajeroSirio.query.get_or_404(id)
    try:
        db.session.delete(pasajero)
        db.session.commit()
        flash('Pasajero eliminado correctamente', 'success')
        return redirect(url_for('pasajeros.listado'))
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar: {str(e)}', 'danger')
        return redirect(url_for('pasajeros.ficha', id=id))

@pasajeros_bp.route('/api/search_autocomplete')
@login_required
def search_autocomplete():
    q = request.args.get('q', '').strip()
    if not q or len(q) < 2:
        return jsonify([])
    
    # Búsqueda por nombre o apellidos
    results = PasajeroSirio.query.filter(
        (PasajeroSirio.nombre.ilike(f'%{q}%')) | 
        (PasajeroSirio.apellidos.ilike(f'%{q}%'))
    ).limit(10).all()
    
    return jsonify([{
        'id': p.id,
        'nombre': p.nombre,
        'apellidos': p.apellidos,
        'clase': p.pasaje
    } for p in results])

@pasajeros_bp.route('/ficha/<int:id>')
@login_required
def ficha(id):
    if not check_sirio_access():
        return render_template('errors/403.html'), 403
        
    pasajero = PasajeroSirio.query.get_or_404(id)
    publicaciones = Publicacion.query.order_by(Publicacion.nombre).all()
    
    # Obtener relaciones
    relaciones_directas = sorted(pasajero.relaciones_como_sujeto, key=lambda r: r.orden or 0)
    relaciones_inversas = pasajero.relaciones_como_objeto
    
    # Pasajeros del mismo apellido para el buscador de familiares rápido
    apellido_base = pasajero.apellidos.split('(')[0].strip() if pasajero.apellidos else ""
    sugerencias = PasajeroSirio.query.filter(
        PasajeroSirio.apellidos.ilike(f"{apellido_base}%"),
        PasajeroSirio.id != pasajero.id
    ).all()

    # Relaciones extendidas (Nivel 2) para el árbol familiar
    rel_ids = [r.relacionado_id for r in relaciones_directas if r.relacionado_id]
    rel_ids += [r.pasajero_id for r in relaciones_inversas if r.pasajero_id]
    
    relaciones_extendidas = []
    if rel_ids:
        relaciones_extendidas = PasajeroRelacion.query.filter(
            (PasajeroRelacion.pasajero_id.in_(rel_ids)) | (PasajeroRelacion.relacionado_id.in_(rel_ids))
        ).filter(
            PasajeroRelacion.pasajero_id != id,
            PasajeroRelacion.relacionado_id != id
        ).all()

    return render_template('pasajeros/ficha.html', 
                         pasajero=pasajero, 
                         publicaciones=publicaciones,
                         relaciones_directas=relaciones_directas,
                         relaciones_inversas=relaciones_inversas,
                         relaciones_extendidas=relaciones_extendidas,
                         sugerencias=sugerencias)

@pasajeros_bp.route('/api/buscar_en_prensa/<int:id>', methods=['GET', 'POST'])
@login_required
def buscar_en_prensa(id):
    if not check_sirio_access():
        return jsonify({'error': 'No autorizado'}), 403
        
    pasajero = PasajeroSirio.query.get_or_404(id)
    
    # Búsqueda mejorada: buscamos por términos del apellido
    # para máxima cobertura, usando unaccent para ignorar acentos.
    search_terms = []
    if pasajero.apellidos:
        # Limpiar y separar apellidos (ej: "Maggi, Giulio" -> ["Maggi", "Giulio"])
        # pero nos interesan los apellidos principales
        apell_clean = pasajero.apellidos.replace(',', ' ').strip()
        search_terms.extend([t.strip() for t in apell_clean.split() if len(t.strip()) > 2])
    
    # Si no hay apellidos largos, probar con el nombre
    if not search_terms and pasajero.nombre:
        nomb_clean = pasajero.nombre.replace(',', ' ').strip()
        search_terms.extend([t.strip() for t in nomb_clean.split() if len(t.strip()) > 2])

    found_articles = []
    if not search_terms:
         return jsonify({'success': True, 'count': 0, 'results': []})

    proyecto_id = session.get('proyecto_activo_id')
    from sqlalchemy import or_, func
    
    # Construir condiciones OR para cada término en título o contenido
    # Usamos func.unaccent para que "Maggi" encuentre "Mággi" y viceversa
    condiciones = []
    for term in search_terms:
        # pattern = f"%{term}%"
        # ilike es case-insensitive en Postgres por defecto
        condiciones.append(func.unaccent(Prensa.titulo).ilike(f"%{term}%"))
        condiciones.append(func.unaccent(Prensa.contenido).ilike(f"%{term}%"))
        condiciones.append(func.unaccent(Prensa.texto_original).ilike(f"%{term}%"))
    
    query = Prensa.query
    if proyecto_id:
        query = query.filter(Prensa.proyecto_id == proyecto_id)
    
    if condiciones:
        query = query.filter(or_(*condiciones))
        
    # Limitar resultados para evitar sobrecarga si el apellido es muy común
    found_articles = query.limit(100).all()
                
    # Vincular automáticamente si se encuentran? 
    # Mejor devolver la lista para que el usuario confirme o simplemente informar
    results = []
    # Obtener IDs de menciones ya vinculadas para marcarlas
    menciones_vinculadas_ids = [m.id for m in pasajero.menciones_prensa]
    
    for art in found_articles:
        results.append({
            'id': art.id,
            'titulo': art.titulo,
            'publicacion': art.publicacion,
            'fecha': art.fecha_original,
            'vinculada': art.id in menciones_vinculadas_ids
        })
        
    return jsonify({
        'success': True,
        'count': len(results),
        'results': results
    })

@pasajeros_bp.route('/api/menciones/<int:id>', methods=['GET'])
@login_required
def get_menciones(id):
    if not check_sirio_access():
        return jsonify({'error': 'No autorizado'}), 403
    pasajero = PasajeroSirio.query.get_or_404(id)
    results = []
    for art in pasajero.menciones_prensa:
        results.append({
            'id': art.id,
            'titulo': art.titulo,
            'publicacion': art.publicacion,
            'fecha': art.fecha_original
        })
    return jsonify({'success': True, 'menciones': results})

@pasajeros_bp.route('/api/mencion_texto/<int:pasajero_id>/<int:prensa_id>', methods=['GET'])
@login_required
def get_mencion_texto(pasajero_id, prensa_id):
    if not check_sirio_access():
        return jsonify({'error': 'No autorizado'}), 403
        
    pasajero = PasajeroSirio.query.get_or_404(pasajero_id)
    noticia = Prensa.query.get_or_404(prensa_id)
    
    # Términos de búsqueda
    terms = []
    if pasajero.apellidos:
        # Extraer apellidos (limpiar de paréntesis y comas)
        apell_clean = pasajero.apellidos.replace(',', ' ').split('(')[0].strip()
        terms.extend([t.strip().lower() for t in apell_clean.split() if len(t.strip()) > 2])
    
    if pasajero.nombre:
        nomb_clean = pasajero.nombre.strip().lower()
        terms.extend([t.strip() for t in nomb_clean.split() if len(t.strip()) > 2])
        
    # Obtener contenido
    content = noticia.texto_original or noticia.contenido or ""
    if not content:
        return jsonify({'success': True, 'parrafos': [], 'titulo': noticia.titulo})
        
    # Dividir en párrafos
    parrafos_raw = [p.strip() for p in content.split('\n') if p.strip()]
    
    # Filtrar párrafos que contengan los términos
    parrafos_filtrados = []
    import re
    
    def normalize(text):
        # Normalización básica de acentos para búsqueda
        import unicodedata
        return ''.join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn').lower()

    norm_terms = [normalize(t) for t in terms]
    
    for p in parrafos_raw:
        norm_p = normalize(p)
        found = False
        for t in norm_terms:
            if t in norm_p:
                found = True
                break
        if found:
            parrafos_filtrados.append(p)
            
    # Si no se encontró ningún párrafo con los términos específicos, devolvemos todo si es corto o nada
    # (A veces la mención está por contexto y no por nombre exacto si es un artículo sobre "el pasajero")
    # Pero el usuario pidió donde se menciona, así que seremos estrictos o devolveremos una muestra si hay pocos.
    
    return jsonify({
        'success': True, 
        'parrafos': parrafos_filtrados, 
        'titulo': noticia.titulo,
        'fecha': noticia.fecha_original,
        'publicacion': noticia.publicacion
    })

@pasajeros_bp.route('/api/vincular_mencion', methods=['POST'])
@login_required
def vincular_mencion():
    if not check_sirio_access():
        return jsonify({'error': 'No autorizado'}), 403
    try:
        data = request.get_json()
        pasajero_id = data.get('pasajero_id')
        prensa_id = data.get('prensa_id')
        
        current_app.logger.info(f"[VINCULAR] Intentando vincular pasajero_id={pasajero_id} con prensa_id={prensa_id}")
        
        pasajero = PasajeroSirio.query.get_or_404(pasajero_id)
        articulo = Prensa.query.get_or_404(prensa_id)
        
        if articulo not in pasajero.menciones_prensa:
            pasajero.menciones_prensa.append(articulo)
            db.session.commit()
            current_app.logger.info(f"[VINCULAR] Éxito: pasajero {pasajero_id} - artículo {prensa_id}")
            return jsonify({'success': True, 'message': 'Noticia vinculada correctamente'})
        
        current_app.logger.info(f"[VINCULAR] Ya estaba vinculada: pasajero {pasajero_id} - artículo {prensa_id}")
        return jsonify({'success': False, 'message': 'Ya está vinculada'})
    except Exception as e:
        import traceback
        error_msg = traceback.format_exc()
        current_app.logger.error(f"[VINCULAR] Error crítico: {str(e)}\n{error_msg}")
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error interno del servidor: {str(e)}'}), 500

@pasajeros_bp.route('/api/desvincular_mencion', methods=['POST'])
@login_required
def desvincular_mencion():
    if not check_sirio_access():
        return jsonify({'error': 'No autorizado'}), 403
    data = request.get_json()
    pasajero_id = data.get('pasajero_id')
    prensa_id = data.get('prensa_id')
    
    pasajero = PasajeroSirio.query.get_or_404(pasajero_id)
    articulo = Prensa.query.get_or_404(prensa_id)
    
    if articulo in pasajero.menciones_prensa:
        pasajero.menciones_prensa.remove(articulo)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Noticia desvinculada'})
    return jsonify({'success': False, 'message': 'No estaba vinculada'})

@pasajeros_bp.route('/api/crear_mencion_manual', methods=['POST'])
@login_required
def crear_mencion_manual():
    if not check_sirio_access():
        return jsonify({'error': 'No autorizado'}), 403
    data = request.get_json()
    pasajero_id = data.get('pasajero_id')
    titulo = data.get('titulo')
    publicacion_nombre = data.get('publicacion')
    fecha = data.get('fecha')
    notas = data.get('notas', '')
    
    pasajero = PasajeroSirio.query.get_or_404(pasajero_id)
    proyecto_id = session.get('proyecto_activo_id') or 1
    
    # Crear un registro básico en Prensa
    nueva_noticia = Prensa(
        proyecto_id=proyecto_id,
        titulo=titulo,
        publicacion=publicacion_nombre,
        fecha_original=fecha,
        notas=f"Creado manualmente desde ficha de pasajero. {notas}",
        incluido=False # No se incluye automáticamente en el análisis global a menos que se quiera
    )
    
    db.session.add(nueva_noticia)
    pasajero.menciones_prensa.append(nueva_noticia)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Noticia creada y vinculada', 'id': nueva_noticia.id})

@pasajeros_bp.route('/api/vincular_publicacion', methods=['POST'])
@login_required
def vincular_publicacion():
    if not check_sirio_access():
        return jsonify({'error': 'No autorizado'}), 403
        
    data = request.get_json()
    pasajero_id = data.get('pasajero_id')
    publicacion_id = data.get('publicacion_id')
    
    pasajero = PasajeroSirio.query.get_or_404(pasajero_id)
    publicacion = Publicacion.query.get_or_404(publicacion_id)
    
    if publicacion not in pasajero.publicaciones:
        pasajero.publicaciones.append(publicacion)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Vinculación exitosa'})
    
    return jsonify({'success': False, 'message': 'Ya está vinculado'})

@pasajeros_bp.route('/api/desvincular_publicacion', methods=['POST'])
@login_required
def desvincular_publicacion():
    if not check_sirio_access():
        return jsonify({'error': 'No autorizado'}), 403
        
    data = request.get_json()
    pasajero_id = data.get('pasajero_id')
    publicacion_id = data.get('publicacion_id')
    
    pasajero = PasajeroSirio.query.get_or_404(pasajero_id)
    publicacion = Publicacion.query.get_or_404(publicacion_id)
    
    if publicacion in pasajero.publicaciones:
        pasajero.publicaciones.remove(publicacion)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Desvinculación exitosa'})
    return jsonify({'success': False, 'message': 'No está vinculado'})

@pasajeros_bp.route('/api/vincular_familiar', methods=['POST'])
@login_required
def vincular_familiar():
    if not check_sirio_access():
        return jsonify({'error': 'No autorizado'}), 403
    
    data = request.get_json()
    pasajero_id = data.get('pasajero_id')
    relacionado_id = data.get('relacionado_id')
    tipo = data.get('tipo_relacion', 'Familiar').upper()
    comentarios = data.get('comentarios', '')
    
    if not pasajero_id or not relacionado_id:
        return jsonify({'success': False, 'message': 'IDs faltantes'})
        
    # Evitar duplicados
    existe = PasajeroRelacion.query.filter_by(
        pasajero_id=pasajero_id,
        relacionado_id=relacionado_id,
        tipo_relacion=tipo
    ).first()
    
    if existe:
        return jsonify({'success': False, 'message': 'Esta relación ya existe'})
        
    nueva_rel = PasajeroRelacion(
        pasajero_id=pasajero_id,
        relacionado_id=relacionado_id,
        tipo_relacion=tipo,
        comentarios=comentarios
    )
    db.session.add(nueva_rel)
    db.session.commit() # Commit inicial para tener la relación base

    # Ejecutar propagación inteligente
    _ejecutar_propagacion_familiar(pasajero_id, relacionado_id, tipo, comentarios)
    
    return jsonify({'success': True, 'message': 'Relación vinculada y propagada correctamente'})

def _ejecutar_propagacion_familiar(pasajero_id, relacionado_id, tipo, comentarios=''):
    """
    Lógica avanzada para deducir y crear vínculos familiares automáticamente.
    Evita redundancias y construye el árbol familiar de forma proactiva.
    """
    try:
        p1 = PasajeroSirio.query.get(pasajero_id)
        p2 = PasajeroSirio.query.get(relacionado_id)
        if not p1 or not p2: return

        def safe_link(subject_id, object_id, role, comm='Propagado automáticamente'):
            if subject_id == object_id: return
            role = role.strip().upper()
            
            # Buscamos si ya existe cualquier vínculo entre estos dos
            existing_links = PasajeroRelacion.query.filter_by(pasajero_id=subject_id, relacionado_id=object_id).all()
            
            if not existing_links:
                new_rel = PasajeroRelacion(pasajero_id=subject_id, relacionado_id=object_id, tipo_relacion=role, comentarios=comm)
                db.session.add(new_rel)
                return True
            else:
                # Si ya existe un vínculo exacto, no hacemos nada
                for rel in existing_links:
                    if rel.tipo_relacion.strip().upper() == role:
                        return False
                
                # Si existe un vínculo genérico (FAMILIAR), lo actualizamos con el rol específico
                for rel in existing_links:
                    if rel.tipo_relacion.strip().upper() in ['FAMILIAR', 'PROCESANDO']:
                        rel.tipo_relacion = role
                        rel.comentarios = comm
                        return True
                return False

        # Normalizar tipo
        tipo = tipo.strip().upper()

        # 1. VÍNCULO INVERSO (RECIPROCIDAD)
        # ¿Qué es P2 para P1? Basado en el género de P2
        p2_sexo = p2.sexo or 'Hombre'
        inv_role = 'FAMILIAR'
        
        if tipo in ['PADRE', 'MADRE', 'PADRE DE', 'MADRE DE']:
            inv_role = 'HIJO' if p2_sexo == 'Hombre' else 'HIJA'
        elif tipo in ['HIJO', 'HIJA', 'HIJO DE', 'HIJA DE']:
            inv_role = 'PADRE' if p2_sexo == 'Hombre' else 'MADRE'
        elif tipo in ['HERMANO', 'HERMANA', 'HERMANO DE', 'HERMANA DE']:
            inv_role = 'HERMANO' if p2_sexo == 'Hombre' else 'HERMANA'
        elif tipo in ['ESPOSO', 'ESPOSO DE']: inv_role = 'ESPOSA'
        elif tipo in ['ESPOSA', 'ESPOSA DE']: inv_role = 'ESPOSO'
        elif tipo in ['ABUELO', 'ABUELA', 'ABUELO DE', 'ABUELA DE']:
            inv_role = 'NIETO' if p2_sexo == 'Hombre' else 'NIETA'
        elif tipo in ['NIETO', 'NIETA', 'NIETO DE', 'NIETA DE']:
            inv_role = 'ABUELO' if p2_sexo == 'Hombre' else 'ABUELA'
        elif tipo in ['SUEGRO', 'SUEGRA', 'SUEGRO DE', 'SUEGRA DE']:
            inv_role = 'YERNO' if p2_sexo == 'Hombre' else 'NUERA'
        elif tipo in ['YERNO', 'NUERA', 'YERNO DE', 'NUERA DE']:
            inv_role = 'SUEGRO' if p2_sexo == 'Hombre' else 'SUEGRA'
        elif tipo in ['HIJASTRO', 'HIJASTRA', 'HIJASTRO DE', 'HIJASTRA DE']:
            inv_role = 'PADRASTRO' if p2_sexo == 'Hombre' else 'MADRASTRA'
        elif tipo in ['PADRASTRO', 'MADRASTRA', 'PADRASTRO DE', 'MADRASTRA DE']:
            inv_role = 'HIJASTRO' if p2_sexo == 'Hombre' else 'HIJASTRA'
        elif tipo in ['SOBRINO', 'SOBRINA', 'SOBRINO DE', 'SOBRINA DE']:
            inv_role = 'TÍO' if p2_sexo == 'Hombre' else 'TÍA'
        elif tipo in ['TÍO', 'TÍA', 'TÍO DE', 'TÍA DE']:
            inv_role = 'SOBRINO' if p2_sexo == 'Hombre' else 'SOBRINA'

        safe_link(relacionado_id, pasajero_id, inv_role, f'Inverso automático de {tipo}')

        # 2. PROPAGACIÓN POR HERMANDAD (MISMO NIVEL)
        if tipo in ['PADRE', 'MADRE', 'HIJO', 'HIJA', 'HERMANO', 'HERMANA']:
            # Si A y B son hermanos, comparten padres
            hermanos_ids = [r.relacionado_id for r in p1.relaciones_como_sujeto if r.tipo_relacion.upper() in ['HERMANO', 'HERMANA']]
            hermanos_ids += [r.pasajero_id for r in p1.relaciones_como_objeto if r.tipo_relacion.upper() in ['HERMANO', 'HERMANA']]
            
            # Si estoy vinculando un PADRE a P1, vincularlo también a todos los hermanos de P1
            if tipo in ['PADRE', 'MADRE']:
                for h_id in set(hermanos_ids):
                    h_obj = PasajeroSirio.query.get(h_id)
                    h_role = 'HIJO' if h_obj.sexo == 'Hombre' else 'HIJA'
                    safe_link(h_id, relacionado_id, tipo, f'Propagado vía hermano {p1.nombre}')
                    safe_link(relacionado_id, h_id, h_role, f'Propagado vía hermano {p1.nombre}')

            # Si estoy vinculando un HIJO a P1 (P1 es padre), todos los otros hijos de P1 son HERMANOS del nuevo
            if tipo in ['HIJO', 'HIJA']:
                otros_hijos = [r.pasajero_id for r in p1.relaciones_como_objeto if r.tipo_relacion.upper() in ['HIJO', 'HIJA']]
                otros_hijos += [r.relacionado_id for r in p1.relaciones_como_sujeto if r.tipo_relacion.upper() in ['PADRE', 'MADRE']]
                for oh_id in set(otros_hijos):
                    if oh_id == relacionado_id: continue
                    oh_obj = PasajeroSirio.query.get(oh_id)
                    oh_role = 'HERMANO' if oh_obj.sexo == 'Hombre' else 'HERMANA'
                    p2_role = 'HERMANO' if p2.sexo == 'Hombre' else 'HERMANA'
                    safe_link(relacionado_id, oh_id, oh_role, 'Propagado vía progenitor común')
                    safe_link(oh_id, relacionado_id, p2_role, 'Propagado vía progenitor común')

        # 3. PROPAGACIÓN GENERACIONAL (ABUELOS)
        if tipo in ['PADRE', 'MADRE']:
            # Los padres de mi padre son mis abuelos
            p2_parents = [r.relacionado_id for r in p2.relaciones_como_sujeto if r.tipo_relacion.upper() in ['PADRE', 'MADRE']]
            p2_parents += [r.pasajero_id for r in p2.relaciones_como_objeto if r.tipo_relacion.upper() in ['HIJO', 'HIJA']]
            for g_id in set(p2_parents):
                g_obj = PasajeroSirio.query.get(g_id)
                g_role = 'ABUELO' if g_obj.sexo == 'Hombre' else 'ABUELA'
                p1_role = 'NIETO' if p1.sexo == 'Hombre' else 'NIETA'
                safe_link(pasajero_id, g_id, g_role, f'Propagado vía progenitor {p2.nombre}')
                safe_link(g_id, pasajero_id, p1_role, f'Propagado vía descendiente {p2.nombre}')

        db.session.commit()
    except Exception as e:
        print(f"ERROR PROPAGACIÓN FAMILIAR: {e}")
        db.session.rollback()

@pasajeros_bp.route('/api/desvincular_familiar', methods=['POST'])
@login_required
def desvincular_familiar():
    if not check_sirio_access():
        return jsonify({'error': 'No autorizado'}), 403
        
    data = request.get_json()
    relacion_id = data.get('relacion_id')
    
    rel = PasajeroRelacion.query.get_or_404(relacion_id)
    db.session.delete(rel)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Relación eliminada'})
    
@pasajeros_bp.route('/api/actualizar_familiar', methods=['POST'])
@login_required
def actualizar_familiar():
    if not check_sirio_access():
        return jsonify({'error': 'No autorizado'}), 403
        
    data = request.get_json()
    relacion_id = data.get('relacion_id')
    nuevo_tipo = data.get('tipo_relacion')
    nuevos_comentarios = data.get('comentarios')
    
    if not relacion_id or not nuevo_tipo:
        return jsonify({'success': False, 'message': 'Faltan datos obligatorios'})
        
    rel = PasajeroRelacion.query.get_or_404(relacion_id)
    rel.tipo_relacion = nuevo_tipo
    if nuevos_comentarios is not None:
        rel.comentarios = nuevos_comentarios
        
    db.session.commit()

    # Propagación tras actualización
    _ejecutar_propagacion_familiar(rel.pasajero_id, rel.relacionado_id, nuevo_tipo.upper(), nuevos_comentarios)
    
    return jsonify({'success': True, 'message': 'Relación actualizada y propagada'})

@pasajeros_bp.route('/api/reordenar-familiares', methods=['POST'])
@login_required
def reordenar_familiares():
    if not check_sirio_access():
        return jsonify({'error': 'No autorizado'}), 403
    
    data = request.json
    orden_data = data.get('orden', [])
    try:
        for item in orden_data:
            rel_id = item.get('id')
            pos = item.get('position')
            if rel_id is not None:
                rel = PasajeroRelacion.query.get(rel_id)
                if rel:
                    rel.orden = pos
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@pasajeros_bp.route('/api/actualizar_residencia', methods=['POST'])
@login_required
def actualizar_residencia():
    if not check_sirio_access():
        return jsonify({'error': 'No autorizado'}), 403
        
    data = request.get_json()
    pasajero_id = data.get('pasajero_id')
    punto_residencia = data.get('punto_residencia', '')
    
    pasajero = PasajeroSirio.query.get_or_404(pasajero_id)
    try:
        pasajero.punto_residencia = punto_residencia
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@pasajeros_bp.route('/api/editar_masivo', methods=['POST'])
@login_required
def editar_masivo():
    if not check_sirio_access():
        return jsonify({'error': 'No autorizado'}), 403
        
    req = request.get_json()
    pasajero_ids = req.get('pasajero_ids', [])
    datos = req.get('datos', {})
    
    if not pasajero_ids:
        return jsonify({'success': False, 'error': 'Ningún pasajero seleccionado'})
        
    try:
        pasajeros = PasajeroSirio.query.filter(PasajeroSirio.id.in_(pasajero_ids)).all()
        modificados = 0
        
        for p in pasajeros:
            actualizado = False
            for k, v in datos.items():
                if v and str(v).strip() != '':
                    # Casos especiales para booleanos
                    if k in ['en_lista_italia_mvd', 'en_lista_italia_ba', 'en_lista_ravena_sp', 'en_lista_diana_bcn', 'en_lista_orione_ge']:
                        setattr(p, k, True if str(v) == '1' else False)
                        actualizado = True
                    # Campos de texto normales
                    elif hasattr(p, k):
                        setattr(p, k, str(v).strip())
                        actualizado = True

            if actualizado:
                modificados += 1
                
        db.session.commit()
        return jsonify({
            'success': True, 
            'message': f'Se actualizaron con éxito {modificados} pasajeros.'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@pasajeros_bp.route('/exportar', methods=['GET'])
@login_required
def exportar():
    if not check_sirio_access():
        return jsonify({'error': 'No autorizado'}), 403
        
    format = request.args.get('format', 'csv')
    query = get_filtered_pasajeros_query(request.args)
    pasajeros = query.all()
    
    data = []
    for p in pasajeros:
        data.append({
            'ID': p.id,
            'Nombre': p.nombre,
            'Apellidos': p.apellidos,
            'Edad': p.edad,
            'Sexo': p.sexo,
            'Clase': p.pasaje,
            'Estado': p.estado,
            'Municipio': p.municipio,
            'Provincia': p.provincia,
            'País': p.pais,
            'Destino': p.ciudad_destino_final,
            'Embarque': p.puerto_embarque
        })
    
    df = pd.DataFrame(data)
    
    output = io.BytesIO()
    filename = f"pasajeros_sirio_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    if format == 'excel':
        df.to_excel(output, index=False, engine='openpyxl')
        output.seek(0)
        return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', as_attachment=True, download_name=f"{filename}.xlsx")
    
    elif format == 'pdf':
        html = df.to_html(classes='table table-striped', index=False)
        # Custom styling for the PDF
        styled_html = f"""
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: sans-serif; font-size: 10px; }}
                table {{ width: 100%; border-collapse: collapse; }}
                th, td {{ border: 1px solid #ddd; padding: 4px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                h1 {{ color: #a52a2a; text-align: center; }}
            </style>
        </head>
        <body>
            <h1>Listado de Pasajeros - S.S. Sirio</h1>
            {html}
        </body>
        </html>
        """
        pdf = pdfkit.from_string(styled_html, False)
        output.write(pdf)
        output.seek(0)
        return send_file(output, mimetype='application/pdf', as_attachment=True, download_name=f"{filename}.pdf")
    
    else: # Default CSV
        csv_data = df.to_csv(index=False, encoding='utf-8-sig')
        output.write(csv_data.encode('utf-8-sig'))
        output.seek(0)
        return send_file(output, mimetype='text/csv', as_attachment=True, download_name=f"{filename}.csv")
    
def get_ticket_price(clase, destino, age=None, custom_prices=None):
    """
    Calcula el precio del billete en Liras según clase, destino y edad.
    Precios por defecto de 1906: 1ª=760, 2ª=560, 3ª=178(Brasil)/190(Plata)
    """
    if not clase: return 0
    c = str(clase).lower()
    d = str(destino or '').lower()
    
    # Precios base (valores actualizados según cartel 1888: 750/550/200)
    p1 = 750
    p2 = 550
    p3b = 200 # Brasil/Santos
    p3p = 200 # Plata/BA
    
    if custom_prices:
        try:
            p1 = float(custom_prices.get('p1', p1))
            p2 = float(custom_prices.get('p2', p2))
            p3b = float(custom_prices.get('p3b', p3b))
            p3p = float(custom_prices.get('p3p', p3p))
        except (ValueError, TypeError):
            pass

    base_price = 0
    if '1' in c or 'prim' in c: 
        base_price = p1
    elif '2' in c or 'segu' in c: 
        base_price = p2
    elif '3' in c or 'terc' in c:
        if 'brasil' in d or 'santos' in d or 'janeiro' in d: 
            base_price = p3b
        else: 
            base_price = p3p
    else:
        # Por defecto si no se reconoce clase, pero es pasaje, asumimos 3ª Plata o 0
        base_price = 0
    
    # Aplicar # Descuentos por edad según "Condizioni di Passaggio" (S.S. Sirio Historical)
    if age is not None:
        try:
            age_val = float(age)
            if age_val < 1:
                return 0  # < 1 año: imbarco gratuito
            elif age_val < 4:
                base_price *= 0.25  # 1-3 años: un quarto di posto (25%)
            elif age_val < 12:
                base_price *= 0.5   # 4-11 años: mezzo posto (50%)
            # 12+ años: posto intero (100%)
        except:
            pass
            
    return base_price

@pasajeros_bp.route('/api/stats')
@login_required
def get_stats():
    if not check_sirio_access():
        return jsonify({'error': 'No autorizado'}), 403
        
    subset = request.args.get('subset', 'general', type=str).strip().lower()
    nacionalidad = request.args.get('nacionalidad', '', type=str).strip()
    sexo = request.args.get('sexo', '', type=str).strip().lower()
    franja_edad = request.args.get('franja_edad', '', type=str).strip()
    clase = request.args.get('clase', '', type=str).strip()
    
    # DEBUG FILE LOGGING
    with open('/tmp/get_stats_debug.log', 'a') as f:
        import datetime
        f.write(f"[{datetime.datetime.now()}] stats_req: subset={subset}, nac={nacionalidad}, sex={sexo}, age={franja_edad}, clase={clase}\n")
    
    # Base Query
    base_query = PasajeroSirio.query
    
    # Filtro por Nacionalidad (País)
    if nacionalidad:
        base_query = base_query.filter(PasajeroSirio.pais.ilike(f'%{nacionalidad}%'))
    
    from sqlalchemy import or_
    
    # Filtro por Sexo (Extremadamente robusto con or_)
    if sexo:
        if 'homb' in sexo or sexo == 'm' or sexo == 'h':
            base_query = base_query.filter(or_(
                PasajeroSirio.sexo.ilike('h%'),
                PasajeroSirio.sexo.ilike('m'), # Maschio
                PasajeroSirio.sexo == '1' # Possible numeric encoding
            ))
        elif 'muf' in sexo or 'muj' in sexo or sexo == 'f':
            base_query = base_query.filter(or_(
                PasajeroSirio.sexo.ilike('m%'),
                PasajeroSirio.sexo.ilike('f'),
                PasajeroSirio.sexo == '2'
            ))
    
    # Filtro por Franja de Edad
    if franja_edad:
        if franja_edad == '0-14':
            base_query = base_query.filter(PasajeroSirio.edad <= 14)
        elif franja_edad == '15-30':
            base_query = base_query.filter(PasajeroSirio.edad >= 15, PasajeroSirio.edad <= 30)
        elif franja_edad == '31-45':
            base_query = base_query.filter(PasajeroSirio.edad >= 31, PasajeroSirio.edad <= 45)
        elif franja_edad == '46-60':
            base_query = base_query.filter(PasajeroSirio.edad >= 46, PasajeroSirio.edad <= 60)
        elif franja_edad == '60+':
            base_query = base_query.filter(PasajeroSirio.edad > 60)
            
    # Filtro por Clase
    if clase:
        base_query = base_query.filter(PasajeroSirio.pasaje.ilike(f'%{clase}%'))
    
    # Pricing and Conversion Params
    custom_prices = {
        'p1': request.args.get('p1', 760, type=float),
        'p2': request.args.get('p2', 560, type=float),
        'p3b': request.args.get('p3b', 178, type=float),
        'p3p': request.args.get('p3p', 190, type=float)
    }
    luggage_fee = request.args.get('luggage', 0, type=float)
    conv_factor = request.args.get('conv', 5.8, type=float)
    
    # Subset Filter
    if subset == 'survivors':
        base_query = base_query.filter(PasajeroSirio.estado == 'SOBREVIVIENTE')
    elif subset == 'deceased':
        base_query = base_query.filter(PasajeroSirio.estado.in_(['DESAPARECIDO/A', 'FALLECIDO/A']))
    
    # Final counts and logging
    total_in_subset = base_query.count()
    
    # LOGGING PARA DEPURACIÓN (Ver terminal)
    print(f"\n[GET_STATS DEBUG]")
    print(f"Params: nac='{nacionalidad}', sex='{sexo}', age='{franja_edad}', clase='{clase}', subset='{subset}'")
    print(f"Base Query results: {total_in_subset}")
    # Ver las primeras 5 filas para ver qué cargamos
    first_few = base_query.limit(5).all()
    for p in first_few:
        print(f" - {p.nombre} {p.apellidos} | Sex: {p.sexo} | Age: {p.edad} | Class: {p.pasaje} | Country: {p.pais}")
    
    # Overall total for percentage calculations
    overall_total_query = PasajeroSirio.query
    if nacionalidad:
        overall_total_query = overall_total_query.filter(PasajeroSirio.pais.ilike(f'%{nacionalidad}%'))
    
    if sexo:
        if 'homb' in sexo or sexo == 'm' or sexo == 'h':
            overall_total_query = overall_total_query.filter(or_(
                PasajeroSirio.sexo.ilike('h%'),
                PasajeroSirio.sexo.ilike('m'), # Maschio
                PasajeroSirio.sexo == '1'
            ))
        elif 'muf' in sexo or 'muj' in sexo or sexo == 'f':
            overall_total_query = overall_total_query.filter(or_(
                PasajeroSirio.sexo.ilike('m%'),
                PasajeroSirio.sexo.ilike('f'),
                PasajeroSirio.sexo == '2'
            ))
        
    if franja_edad:
        if franja_edad == '0-14':
            overall_total_query = overall_total_query.filter(PasajeroSirio.edad <= 14)
        elif franja_edad == '15-30':
            overall_total_query = overall_total_query.filter(PasajeroSirio.edad >= 15, PasajeroSirio.edad <= 30)
        elif franja_edad == '31-45':
            overall_total_query = overall_total_query.filter(PasajeroSirio.edad >= 31, PasajeroSirio.edad <= 45)
        elif franja_edad == '46-60':
            overall_total_query = overall_total_query.filter(PasajeroSirio.edad >= 46, PasajeroSirio.edad <= 60)
        elif franja_edad == '60+':
            overall_total_query = overall_total_query.filter(PasajeroSirio.edad > 60)
            
    if clase:
        overall_total_query = overall_total_query.filter(PasajeroSirio.pasaje.ilike(f'%{clase}%'))
            
    overall_total = overall_total_query.count()
    
    print(f"[DEBUG API] Subset: {subset}, Country: {nacionalidad}, Class: {clase}, Subtotal: {total_in_subset}, Overall: {overall_total}")
    
    # Distribución por Sexo (Subset)
    gender_counts = base_query.with_entities(PasajeroSirio.sexo, func.count(PasajeroSirio.id))\
        .group_by(PasajeroSirio.sexo).all()
    
    # Pirámide de Población (Subset) - Franjas de 5 años
    age_groups = [
        (0, 4, '0-4'), (5, 9, '5-9'), (10, 14, '10-14'), (15, 19, '15-19'),
        (20, 24, '20-24'), (25, 29, '25-29'), (30, 34, '30-34'), (35, 39, '35-39'),
        (40, 44, '40-44'), (45, 49, '45-49'), (50, 54, '50-54'), (55, 59, '55-59'),
        (60, 64, '60-64'), (65, 69, '65-69'), (70, 74, '70-74'), (75, 79, '75-79'),
        (80, 120, '80+')
    ]
    
    pyramid_data = {'labels': [g[2] for g in age_groups], 'males': [], 'females': []}
    for low, high, label in age_groups:
        m_count = base_query.filter(PasajeroSirio.sexo.in_(['Hombre', 'M']), 
                                    PasajeroSirio.edad >= low, 
                                    PasajeroSirio.edad <= high).count()
        f_count = base_query.filter(PasajeroSirio.sexo.in_(['Mujer', 'F']), 
                                    PasajeroSirio.edad >= low, 
                                    PasajeroSirio.edad <= high).count()
        pyramid_data['males'].append(m_count)
        pyramid_data['females'].append(f_count)

    # Subset list for specific aggregations
    all_subset_passengers = base_query.all()
    passenger_ids = [p.id for p in all_subset_passengers]

    # 1. Survival Rate and Gender distribution by Class (Optimized)
    # We use a single query to get all counts grouped by class and survival/sex
    stats_by_class = db.session.query(
        PasajeroSirio.pasaje,
        PasajeroSirio.sexo,
        PasajeroSirio.estado,
        func.count(PasajeroSirio.id)
    ).filter(PasajeroSirio.id.in_(passenger_ids)).group_by(
        PasajeroSirio.pasaje,
        PasajeroSirio.sexo,
        PasajeroSirio.estado
    ).all() if passenger_ids else []

    survival_class = {}
    class_gender = {}
    
    # Process results in memory
    temp_class_stats = {} # {class_name: {'total': 0, 'survived': 0, 'males': 0, 'females': 0}}
    for pasaje, sexo, estado, count in stats_by_class:
        if not pasaje: continue
        # Normalize class name for aggregation (this is a bit tricky with raw labels, but we'll try)
        # For the radar chart, we'll just use the first word or some identifier
        c_key = pasaje.split()[0] if pasaje else '?'
        if c_key not in temp_class_stats:
            temp_class_stats[c_key] = {'total': 0, 'survived': 0, 'males': 0, 'females': 0}
        
        temp_class_stats[c_key]['total'] += count
        if estado == 'SOBREVIVIENTE':
            temp_class_stats[c_key]['survived'] += count
        if (sexo or '').lower() in ['hombre', 'm']:
            temp_class_stats[c_key]['males'] += count
        elif (sexo or '').lower() in ['mujer', 'f']:
            temp_class_stats[c_key]['females'] += count

    for ck, v in temp_class_stats.items():
        survival_class[ck] = round((v['survived'] / v['total'] * 100), 1) if v['total'] > 0 else 0
        class_gender[ck] = {'Hombres': v['males'], 'Mujeres': v['females']}

    # 3. Migration Density: Top Origins (Municipios)
    top_origins = base_query.with_entities(PasajeroSirio.municipio, func.count(PasajeroSirio.id))\
        .filter(PasajeroSirio.municipio.isnot(None))\
        .group_by(PasajeroSirio.municipio)\
        .order_by(func.count(PasajeroSirio.id).desc()).limit(10).all()

    # 4. Final Destinations
    top_destinations = base_query.with_entities(PasajeroSirio.ciudad_destino_final, func.count(PasajeroSirio.id))\
        .filter(PasajeroSirio.ciudad_destino_final.isnot(None))\
        .group_by(PasajeroSirio.ciudad_destino_final)\
        .order_by(func.count(PasajeroSirio.id).desc()).limit(10).all()

    # 5. Sankey Data (Flow: Origen -> Puerto -> Destino)
    sankey_data = []
    flows = base_query.with_entities(PasajeroSirio.pais, PasajeroSirio.puerto_embarque, PasajeroSirio.ciudad_destino_final, func.count(PasajeroSirio.id))\
        .filter(PasajeroSirio.pais.isnot(None), PasajeroSirio.puerto_embarque.isnot(None), PasajeroSirio.ciudad_destino_final.isnot(None))\
        .group_by(PasajeroSirio.pais, PasajeroSirio.puerto_embarque, PasajeroSirio.ciudad_destino_final)\
        .order_by(func.count(PasajeroSirio.id).desc()).limit(50).all()
    
    for origin, port, dest, count in flows:
        # We use spaces to differentiate nodes and prevent loops while keeping labels clean
        # origin (0 spaces), port (1 space), destination (2 spaces)
        sankey_data.append({'from': str(origin or 'Unknown'), 'to': f"{port or 'Unknown'} ", 'flow': count})
        sankey_data.append({'from': f"{port or 'Unknown'} ", 'to': f"{dest or 'Unknown'}  ", 'flow': count})

    # 6. Survival Heatmap (Age Group vs Class)
    heatmap_age_groups = [
        (0, 14, 'Niños (0-14)'),
        (15, 30, 'Jóvenes (15-30)'),
        (31, 50, 'Adultos (31-50)'),
        (51, 120, 'Mayores (51+)')
    ]
    heatmap_classes = ['1ª', '2ª', '3ª', 'Tripulación']
    survival_heatmap = []
    for low, high, age_label in heatmap_age_groups:
        for c in heatmap_classes:
            q = base_query.filter(
                PasajeroSirio.edad >= low, 
                PasajeroSirio.edad <= high,
                PasajeroSirio.pasaje.ilike(f'%{c}%')
            )
            total = q.count()
            survived = q.filter(PasajeroSirio.estado == 'SOBREVIVIENTE').count()
            rate = round(float(survived * 100) / float(total), 1) if total > 0 else 0.0
            survival_heatmap.append({'age': age_label, 'class': c, 'rate': rate, 'count': total})

    # 6. Economic Analytics (Investment)
    total_liras = 0.0
    investment_by_class = {'1ª Clase': 0.0, '2ª Clase': 0.0, '3ª Clase': 0.0, 'Tripulación': 0.0}
    
    for p in all_subset_passengers:
        price = get_ticket_price(p.pasaje, p.ciudad_destino_final, age=p.edad, custom_prices=custom_prices)
        
        # Tasa fija (3.10 L.) aplicada si no es gratuito (< 1 año)
        if price > 0:
            price += luggage_fee
            
        total_liras += price
        
        # Group by class (Normalized labels for the chart)
        clase_norm = "3ª Clase"
        if p.pasaje:
            p_low = p.pasaje.lower()
            if '1' in p_low or 'primera' in p_low: clase_norm = '1ª Clase'
            elif '2' in p_low or 'segunda' in p_low: clase_norm = '2ª Clase'
            elif 'trip' in p_low: clase_norm = 'Tripulación'
        
        investment_by_class[clase_norm] = investment_by_class.get(clase_norm, 0) + price
        
    # Conversión histórica a EUR (Factor configurable)
    total_eur = total_liras * conv_factor

    # Average Age calculation (Subset - Overall)
    avg_age = base_query.with_entities(func.avg(PasajeroSirio.edad))\
        .filter(PasajeroSirio.edad.isnot(None)).scalar()
    
    # Average Age by Sex (Subset)
    age_m_q = base_query.filter(PasajeroSirio.sexo.in_(['Hombre', 'M']))\
        .with_entities(func.avg(PasajeroSirio.edad))\
        .filter(PasajeroSirio.edad.isnot(None))
    avg_age_male = age_m_q.scalar()
        
    age_f_q = base_query.filter(PasajeroSirio.sexo.in_(['Mujer', 'F']))\
        .with_entities(func.avg(PasajeroSirio.edad))\
        .filter(PasajeroSirio.edad.isnot(None))
    avg_age_female = age_f_q.scalar()

    # Global Status for Summary
    status_counts = base_query.with_entities(PasajeroSirio.estado, func.count(PasajeroSirio.id))\
        .group_by(PasajeroSirio.estado).all()

    # Dynamic Press Mentions
    from models import pasajero_publicacion
    passenger_ids = [p.id for p in all_subset_passengers]
    if passenger_ids:
        mentions_count = db.session.query(func.count(pasajero_publicacion.c.pasajero_id))\
            .filter(pasajero_publicacion.c.pasajero_id.in_(passenger_ids))\
            .scalar() or 0
    else:
        mentions_count = 0

    # Removed survival_sex and survival_class_detailed as requested (frontend cards deleted)

    survivors_ages = [p.edad for p in base_query.filter(PasajeroSirio.estado == 'SOBREVIVIENTE', PasajeroSirio.edad.isnot(None)).all()]
    deceased_ages = [p.edad for p in base_query.filter(PasajeroSirio.estado.in_(['DESAPARECIDO/A', 'FALLECIDO/A']), PasajeroSirio.edad.isnot(None)).all()]

    scatter_data = []
    for p in all_subset_passengers:
        if p.edad is not None:
            p_price = get_ticket_price(p.pasaje, p.ciudad_destino_final, age=p.edad, custom_prices=custom_prices)
            if p_price > 0: p_price += luggage_fee
            is_survived = 1 if p.estado == 'SOBREVIVIENTE' else 0
            clase_simple = 3
            if p.pasaje:
                if '1' in p.pasaje: clase_simple = 1
                elif '2' in p.pasaje: clase_simple = 2
                elif 'trip' in p.pasaje.lower(): clase_simple = 4
            # Asegurar tipos para evitar 500 (Robustez extra)
            scatter_data.append({
                'name': f"{p.nombre or ''} {p.apellidos or ''}".strip() or "Sin nombre",
                'age': float(p.edad) if (p.edad is not None and str(p.edad).replace('.','').isdigit()) else 30,
                'price': float(p_price or 0),
                'survived': 1 if str(p.estado or '').upper() == 'SOBREVIVIENTE' else 0,
                'class': 1 if '1' in str(p.pasaje or '') else (2 if '2' in str(p.pasaje or '') else (3 if '3' in str(p.pasaje or '') else 4))
            })

    # 7. Chronology: Embarkation Ports
    embarkation_stats = {}
    survival_by_port = {} # {port: {total: 0, survived: 0}}
    
    # 8. Rescue Ships (for survivors)
    rescue_ships = {
        'S.S. Orione': 0,
        'Vapor Diana': 0,
        'Vapor Ravena': 0,
        'Vapor Italia (BA)': 0,
        'Vapor Italia (MVD)': 0
    }

    for p in all_subset_passengers:
        # Determine port from specific fields or general field
        port = (p.puerto_embarque or "").strip().title()
        if not port:
            if p.fecha_emb_napoles: port = "Nápoles"
            elif p.fecha_emb_genova: port = "Génova"
            elif p.fecha_emb_barcelona: port = "Barcelona"
        
        if port:
            embarkation_stats[port] = embarkation_stats.get(port, 0) + 1
            if port not in survival_by_port: survival_by_port[port] = {'total': 0, 'survived': 0}
            survival_by_port[port]['total'] += 1
            if p.estado == 'SOBREVIVIENTE':
                survival_by_port[port]['survived'] += 1
        
        # Rescue Ships
        if p.estado == 'SOBREVIVIENTE':
            if p.en_lista_orione_ge: rescue_ships['S.S. Orione'] += 1
            if p.en_lista_diana_bcn: rescue_ships['Vapor Diana'] += 1
            if p.en_lista_ravena_sp: rescue_ships['Vapor Ravena'] += 1
            if p.en_lista_italia_ba: rescue_ships['Vapor Italia (BA)'] += 1
            if p.en_lista_italia_mvd: rescue_ships['Vapor Italia (MVD)'] += 1

    # 9. Post-Shipwreck Situation (Continúa / Retorno)
    post_naufragio_stats = {'Continúa viaje': 0, 'Retorno a origen': 0, 'Desconocido': 0}
    for p in all_subset_passengers:
        if p.estado == 'SOBREVIVIENTE':
            sit = (p.situacion_post_naufragio or "Desconocido").strip().capitalize()
            if 'cont' in sit.lower() or 'lleg' in sit.lower(): post_naufragio_stats['Continúa viaje'] += 1
            elif 'ret' in sit.lower(): post_naufragio_stats['Retorno a origen'] += 1
            else: post_naufragio_stats['Desconocido'] += 1

    # Format survival by port for frontend
    survival_port_final = {}
    for pt, st in survival_by_port.items():
        if st['total'] > 5: # Only show significant ports
            survival_port_final[pt] = round((st['survived'] / st['total']) * 100, 1)

    # 10. Family Analytics
    import collections
    from models import PasajeroRelacion
    relationships = PasajeroRelacion.query.all()
    adj = collections.defaultdict(list)
    for rel in relationships:
        adj[rel.pasajero_id].append(rel.relacionado_id)
        adj[rel.relacionado_id].append(rel.pasajero_id)
        
    explicit_fam_sizes = {}
    visited_ids = set()
    for p_id in adj:
        if p_id not in visited_ids:
            comp = []
            stack = [p_id]
            visited_ids.add(p_id)
            while stack:
                curr = stack.pop()
                comp.append(curr)
                for neighbor in adj[curr]:
                    if neighbor not in visited_ids:
                        visited_ids.add(neighbor)
                        stack.append(neighbor)
            for cid in comp:
                explicit_fam_sizes[cid] = len(comp)
                
    unverified_pool = [p for p in all_subset_passengers if p.id not in visited_ids and p.apellidos]
    suggested_map = collections.defaultdict(list)
    for p in unverified_pool:
        key = f"{p.apellidos.strip().upper()}|{p.provincia or 'Unknown'}"
        suggested_map[key].append(p.id)
        
    p_family_size = {}
    for p in all_subset_passengers:
        if p.id in explicit_fam_sizes:
            p_family_size[p.id] = explicit_fam_sizes[p.id]
        else:
            if p.apellidos:
                key = f"{p.apellidos.strip().upper()}|{p.provincia or 'Unknown'}"
                size = len(suggested_map[key])
                p_family_size[p.id] = size if size > 1 else 1
            else:
                p_family_size[p.id] = 1

    size_bins = {'1 Persona (Solo)': 0, '2 Personas (Pareja)': 0, '3-4 Personas': 0, '5-9 Personas': 0, '10+ Personas': 0}
    survival_by_size = {k: {'survived': 0, 'total': 0} for k in size_bins}
    class_by_fam = collections.defaultdict(lambda: collections.defaultdict(int))
    
    for p in all_subset_passengers:
        fs = p_family_size[p.id]
        if fs == 1: s_bin = '1 Persona (Solo)'
        elif fs == 2: s_bin = '2 Personas (Pareja)'
        elif fs <= 4: s_bin = '3-4 Personas'
        elif fs <= 9: s_bin = '5-9 Personas'
        else: s_bin = '10+ Personas'
        
        size_bins[s_bin] += 1
        survival_by_size[s_bin]['total'] += 1
        if p.estado == 'SOBREVIVIENTE':
            survival_by_size[s_bin]['survived'] += 1
            
        clase_norm = "3ª Clase"
        if p.pasaje:
            p_low = p.pasaje.lower()
            if '1' in p_low or 'primera' in p_low: clase_norm = '1ª Clase'
            elif '2' in p_low or 'segunda' in p_low: clase_norm = '2ª Clase'
            elif 'trip' in p_low: clase_norm = 'Tripulación'
        class_by_fam[clase_norm][s_bin] += 1

    family_stats = {
        'distribution': size_bins,
        'survival': survival_by_size,
        'class_distribution': {k: dict(v) for k, v in class_by_fam.items()}
    }

    return jsonify({
        'success': True,
        'subset_info': {
            'name': subset,
            'total': total_in_subset,
            'overall_total': overall_total,
            'mentions': mentions_count,
            'total_liras': total_liras,
            'total_eur': round(total_eur, 2),
            'avg_price': round(float(total_liras) / float(total_in_subset), 1) if total_in_subset > 0 else 0.0
        },
        'economic': {
            'by_class': investment_by_class,
            'conversion_factor': conv_factor,
            'description': f"Capital migratorio basado en 'Condizioni di Passaggio' (1906). Factor: 1 Lira ≈ {conv_factor} €."
        },
        'gender': {str(k or 'Desconocido'): v for k, v in gender_counts},
        'status': {str(k or 'Desconocido'): v for k, v in status_counts},
        'pyramid': pyramid_data,
        'survival_sex': {},
        'survival_class_detailed': {},
        'survival_age_raw': {
            'survivors': survivors_ages,
            'deceased': deceased_ages
        },
        'scatter_data': scatter_data,
        'survival_class': survival_class,
        'class_gender': class_gender,
        'top_origins': {str(k): v for k, v in top_origins},
        'top_destinations': {str(k): v for k, v in top_destinations},
        'sankey': sankey_data,
        'heatmap': survival_heatmap,
        'avg_age': round(float(avg_age), 1) if avg_age else 0.0,
        'avg_age_male': round(float(avg_age_male), 1) if avg_age_male else 0.0,
        'avg_age_female': round(float(avg_age_female), 1) if avg_age_female else 0.0,
        'chronology': {
            'embarkation': {str(k): v for k, v in embarkation_stats.items()},
            'survival_port': survival_port_final,
            'rescue_ships': rescue_ships,
            'post_situation': post_naufragio_stats
        },
        'family_stats': family_stats
    })

@pasajeros_bp.route('/api/map-data')
@login_required
def get_map_data():
    if not check_sirio_access():
        return jsonify({'error': 'No autorizado'}), 403
    
    # Coordinates of country centroids to place passengers without specific geodata
    country_centroids = {
        'España': (40.4637, -3.7492),
        'Italia': (41.8719, 12.5674),
        'Argentina': (-38.4161, -63.6167),
        'Uruguay': (-32.5228, -55.7658),
        'Brasil': (-14.2350, -51.9253),
        'Estados Unidos': (37.0902, -95.7129),
        'Cuba': (21.5218, -77.7812),
        'México': (23.6345, -102.5528),
        'Francia': (46.2276, 2.2137),
        'Rusia': (61.5240, 105.3188),
        'Austria': (47.5162, 14.5501),
        'Suiza': (46.8182, 8.2275),
        'Costa Rica': (9.7489, -83.7534),
        'Chile': (-35.6751, -71.5430),
        'Puerto Rico': (18.2208, -66.5901)
    }
    
    # Optional filtration: All passengers (return lat/lon even if null for correct counts)
    pasajeros = PasajeroSirio.query.all()
    
    results = []
    for p in pasajeros:
        lat, lon = p.lat, p.lon
        
        # Fallback to country centroid if missing coordinates
        if (lat is None or lon is None) and p.pais in country_centroids:
            lat, lon = country_centroids[p.pais]
        
        # Calculate arrival and wreck status for migration arcs
        ha_llegado_destino = any([
            p.ciudad_destino, 
            p.ciudad_destino_final, 
            p.puerto_retorno,
            p.situacion_post_naufragio and "CONTIN" in p.situacion_post_naufragio.upper()
        ])
        ha_naufragado = bool(p.fecha_hundimiento or (p.estado and "FALLECIDO" in p.estado.upper()))

        results.append({
            'id': p.id,
            'nombre': p.nombre,
            'apellidos': p.apellidos,
            'lat': lat,
            'lon': lon,
            'provincia': p.provincia,
            'municipio': p.municipio,
            'region': p.region,
            'pais': p.pais,
            'clase': p.pasaje,
            'estado': p.estado,
            'edad': p.edad,
            'sexo': p.sexo,
            'puerto_embarque': p.puerto_embarque,
            'ciudad_destino': p.ciudad_destino,
            'ciudad_destino_final': p.ciudad_destino_final,
            'fecha_emb_napoles': p.fecha_emb_napoles,
            'fecha_emb_genova': p.fecha_emb_genova,
            'fecha_emb_barcelona': p.fecha_emb_barcelona,
            'fecha_hundimiento': p.fecha_hundimiento,
            'fecha_llegada_cartagena': p.fecha_llegada_cartagena,
            'fecha_salida_cartagena': p.fecha_salida_cartagena,
            'puerto_retorno': p.puerto_retorno,
            'fecha_retorno': p.fecha_retorno,
            'situacion_post_naufragio': p.situacion_post_naufragio,
            'en_lista_italia_mvd': p.en_lista_italia_mvd,
            'en_lista_italia_ba': p.en_lista_italia_ba,
            'en_lista_ravena_sp': p.en_lista_ravena_sp,
            'en_lista_diana_bcn': p.en_lista_diana_bcn,
            'en_lista_orione_ge': p.en_lista_orione_ge,
            'ha_llegado_destino': ha_llegado_destino,
            'ha_naufragado': ha_naufragado
        })
    
    return jsonify(results)

@pasajeros_bp.route('/api/update_journey', methods=['POST'])
@login_required
def update_journey():
    if not check_sirio_access():
        return jsonify({'success': False, 'message': 'No autorizado'}), 403
        
    data = request.get_json()
    pasajero_id = data.get('pasajero_id')
    pasajero = PasajeroSirio.query.get_or_404(pasajero_id)
    
    try:
        pasajero.fecha_emb_napoles = data.get('fecha_emb_napoles')
        pasajero.fecha_emb_genova = data.get('fecha_emb_genova')
        pasajero.fecha_emb_barcelona = data.get('fecha_emb_barcelona')
        pasajero.fecha_hundimiento = data.get('fecha_hundimiento')
        pasajero.fecha_llegada_cartagena = data.get('fecha_llegada_cartagena')
        pasajero.fecha_salida_cartagena = data.get('fecha_salida_cartagena')
        pasajero.situacion_post_naufragio = data.get('situacion_post_naufragio')
        pasajero.puerto_retorno = data.get('puerto_retorno')
        pasajero.fecha_retorno = data.get('fecha_retorno')
        
        # Limpieza de valores "None" accidentales
        for attr in ['fecha_emb_napoles', 'fecha_emb_genova', 'fecha_emb_barcelona', 
                    'fecha_hundimiento', 'fecha_llegada_cartagena', 'fecha_salida_cartagena',
                    'fecha_retorno', 'puerto_retorno']:
            val = getattr(pasajero, attr)
            if val == 'None' or val == 'none' or val == 'null':
                setattr(pasajero, attr, '')
        
        db.session.add(pasajero)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@pasajeros_bp.route('/api/update-coordinates', methods=['POST'])
@login_required
def api_update_coordinates():
    if not check_sirio_access():
        return jsonify({'success': False, 'error': 'No autorizado'}), 403
        
    data = request.get_json()
    pasajero_id = data.get('pasajero_id') or data.get('id')
    lat = data.get('lat')
    lon = data.get('lon')
    
    if not pasajero_id:
        return jsonify({'success': False, 'error': 'ID faltante'}), 400
        
    pasajero = PasajeroSirio.query.get(pasajero_id)
    if not pasajero:
        return jsonify({'success': False, 'error': 'Pasajero no encontrado'}), 404
        
    try:
        pasajero.lat = lat
        pasajero.lon = lon
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@pasajeros_bp.route('/api/family-data')
@login_required
def get_family_data():
    if not check_sirio_access():
        return jsonify({'error': 'No autorizado'}), 403
        
    import collections
    
    # 1. Cargar todos los pasajeros y sus relaciones
    all_pasajeros = PasajeroSirio.query.all()
    pasajeros_dict = {p.id: p for p in all_pasajeros}
    relationships = PasajeroRelacion.query.all()
    
    # 2. Construir el grafo de linajes explícitos
    adj = collections.defaultdict(list)
    for rel in relationships:
        adj[rel.pasajero_id].append(rel.relacionado_id)
        adj[rel.relacionado_id].append(rel.pasajero_id)
        
    visited_ids = set()
    family_groups = []
    
    # 3. Identificar Linajes Confirmados (Componentes conexas)
    for p_id in adj:
        if p_id not in visited_ids:
            component_ids = []
            stack = [p_id]
            visited_ids.add(p_id)
            while stack:
                curr = stack.pop()
                component_ids.append(curr)
                for neighbor in adj[curr]:
                    if neighbor not in visited_ids:
                        visited_ids.add(neighbor)
                        stack.append(neighbor)
            
            members = [pasajeros_dict[mid] for mid in component_ids if mid in pasajeros_dict]
            if not members: continue
            
            # Determinar apellido representativo y coordenadas
            # Limpiamos posibles notas manuales en paréntesis para el nombre del grupo
            clean_surnames = [m.apellidos.split('(')[0].strip() for m in members if m.apellidos]
            main_surname = collections.Counter(clean_surnames).most_common(1)[0][0] if clean_surnames else "Familia"
            rep_coord = next((m for m in members if m.lat and m.lon), None)
            if not rep_coord: continue
            
            def get_inverse_relation(tipo, sexo):
                t = tipo.upper()
                if 'HERMAN' in t: return 'HERMANO' if sexo == 'Hombre' else 'HERMANA'
                if 'HIJ' in t and 'HIJAST' not in t: return 'PADRE' if sexo == 'Hombre' else 'MADRE'
                if 'PADRE' in t or 'MADRE' in t: return 'HIJO' if sexo == 'Hombre' else 'HIJA'
                if 'ESPOS' in t or t == 'CONYUGE' or t == 'MARIDO' or t == 'MUJER': 
                    return 'ESPOSO' if sexo == 'Hombre' else 'ESPOSA'
                if 'TIO' in t or 'TIA' in t: return 'SOBRINO' if sexo == 'Hombre' else 'SOBRINA'
                if 'SOBRIN' in t: return 'TIO' if sexo == 'Hombre' else 'TIA'
                if 'NIET' in t: return 'ABUELO' if sexo == 'Hombre' else 'ABUELA'
                if 'ABUEL' in t: return 'NIETO' if sexo == 'Hombre' else 'NIETA'
                if 'HIJAST' in t: return 'PADRASTRO' if sexo == 'Hombre' else 'MADRASTRA'
                if 'PADRAST' in t or 'MADRAST' in t: return 'HIJASTRO' if sexo == 'Hombre' else 'HIJASTRA'
                return t

            # Construir detalles con info de relación
            member_details = []
            for m in members:
                # 1. Relaciones directas (m es el sujeto)
                m_rels = [r for r in relationships if r.pasajero_id == m.id]
                # 2. Relaciones inversas (donde otros mencionan a m como su pariente)
                m_inv_rels = [r for r in relationships if r.relacionado_id == m.id]
                
                labels = []
                # Evitar duplicados si ya existen ambas direcciones en DB
                seen_others = set()

                for r in m_rels:
                    other = pasajeros_dict.get(r.relacionado_id)
                    if other:
                        labels.append(f"{r.tipo_relacion} de {other.nombre}")
                        seen_others.add(other.id)
                
                for r in m_inv_rels:
                    subject = pasajeros_dict.get(r.pasajero_id)
                    if subject and subject.id not in seen_others:
                        # Inferimos qué es 'm' para 'subject' basándonos en qué es 'subject' para 'm'
                        inv_label = get_inverse_relation(r.tipo_relacion, m.sexo)
                        labels.append(f"{inv_label} de {subject.nombre}")
                        seen_others.add(subject.id)
                
                rel_info = ""
                display_apellidos = m.apellidos
                if labels:
                    rel_info = " (" + ", ".join(labels) + ")"
                    # Si tenemos info explícita, usamos el apellido limpio
                    display_apellidos = m.apellidos.split('(')[0].strip()
                
                member_details.append({
                    'id': m.id,
                    'nombre': f"{m.nombre} {display_apellidos}{rel_info}",
                    'edad': m.edad,
                    'estado': m.estado,
                    'clase': m.pasaje,
                    'sexo': m.sexo
                })
 
            family_groups.append({
                'surname': f"Linaje {main_surname}",
                'province': members[0].provincia or "Varios",
                'count': len(members),
                'members': member_details,
                'lat': rep_coord.lat,
                'lon': rep_coord.lon,
                'is_verified': True # Marca para frontend
            })

    # 4. Agrupación por Apellidos (Sugeridos) - Fallback para el resto
    suggested_families = {}
    remaining_pasajeros = [p for p in all_pasajeros if p.id not in visited_ids and p.lat is not None]
    
    for p in remaining_pasajeros:
        if not p.apellidos: continue
        key = f"{p.apellidos.strip().upper()}|{p.provincia or 'Unknown'}"
        if key not in suggested_families:
            suggested_families[key] = {
                'surname': p.apellidos,
                'province': p.provincia,
                'count': 0,
                'members': [],
                'lat': p.lat,
                'lon': p.lon,
                'is_verified': False
            }
        suggested_families[key]['count'] += 1
        suggested_families[key]['members'].append({
            'id': p.id,
            'nombre': p.nombre + " " + p.apellidos,
            'edad': p.edad,
            'estado': p.estado,
            'clase': p.pasaje,
            'sexo': p.sexo
        })
        
    filtered_suggested = [f for f in suggested_families.values() if f['count'] > 1]
    
    return jsonify(family_groups + filtered_suggested)

@pasajeros_bp.route('/api/region-stats')
@login_required
def get_region_stats():
    if not check_sirio_access():
        return jsonify({'error': 'No autorizado'}), 403
    
    # Group by region
    region_counts = db.session.query(PasajeroSirio.region, func.count(PasajeroSirio.id))\
        .filter(PasajeroSirio.region.isnot(None), PasajeroSirio.region != '')\
        .group_by(PasajeroSirio.region).all()
        
    provincia_counts = db.session.query(PasajeroSirio.provincia, func.count(PasajeroSirio.id))\
        .filter(PasajeroSirio.provincia.isnot(None), PasajeroSirio.provincia != '')\
        .group_by(PasajeroSirio.provincia).all()

    country_counts = db.session.query(PasajeroSirio.pais, func.count(PasajeroSirio.id))\
        .filter(PasajeroSirio.pais.isnot(None), PasajeroSirio.pais != '')\
        .group_by(PasajeroSirio.pais).all()

    return jsonify({
        'regions': {str(r): count for r, count in region_counts},
        'provincias': {str(p): count for p, count in provincia_counts},
        'countries': {str(c): count for c, count in country_counts}
    })

@pasajeros_bp.route('/graficos')
@login_required
def graficos():
    if not check_sirio_access():
        return render_template('errors/403.html'), 403
        
    # Obtener nacionalidades disponibles para el filtro
    nacionalidades_query = db.session.query(PasajeroSirio.pais).filter(
        PasajeroSirio.pais.isnot(None),
        PasajeroSirio.pais != ''
    ).distinct().all()
    
    # Normalizar (Mayúsculas) y eliminar duplicados de casing
    paises = []
    if nacionalidades_query:
        paises = sorted(list(set([str(n[0]).strip().upper() for n in nacionalidades_query if n[0]])))
    
    # Fallback if DB query failed for some reason (should not happen based on manual check)
    if not paises:
        paises = ["ESPAÑA", "ITALIA", "ARGENTINA", "BRASIL", "URUGUAY"]
        print("WARNING: Nationalities query returned empty, using fallback!")
    
    print(f"DEBUG: graficos() sending {len(paises)} paises: {paises}")
    
    return render_template('pasajeros/graficos.html', 
                           paises=paises)

@pasajeros_bp.route('/mapas')
@login_required
def mapas():
    if not check_sirio_access():
        return render_template('errors/403.html'), 403
    return render_template('pasajeros/mapas.html')

@pasajeros_bp.route('/redes')
@login_required
def redes():
    if not check_sirio_access():
        return render_template('errors/403.html'), 403
    return render_template('pasajeros/redes.html')

@pasajeros_bp.route('/timeline')
@login_required
def timeline():
    if not check_sirio_access():
        return render_template('errors/403.html'), 403
    return render_template('pasajeros/timeline.html')
@pasajeros_bp.route('/api/ai-population-insight', methods=['POST'])
@login_required
def ai_population_insight():
    if not check_sirio_access():
        return jsonify({'error': 'No autorizado'}), 403
        
    data = request.get_json() or {}
    stats = data.get('stats', {})
    
    if not stats:
        return jsonify({'success': False, 'error': 'No hay datos estadísticos para analizar.'})
        
    try:
        # Initialize AIService with current user's keys
        # We try to use Gemini first as it's the default, but AIService handles fallbacks
        ai_service = AIService(user=current_user)
        
        if not ai_service.is_configured():
            return jsonify({
                'success': False, 
                'error': 'IA no configurada. Por favor, define tus API Keys (OpenAI o Gemini) en tu perfil de usuario.'
            })
            
        # Construct the detailed prompt
        prompt = f"""
        Actúa como un experto en sociología histórica, demografía y humanidades digitales. 
        Analiza el siguiente resumen estadístico de una población de pasajeros del naufragio del S.S. Sirio (1906):

        RESUMENESTADÍSTICO:
        - Total de Pasajeros en esta vista: {stats.get('total', 0)}
        - Supervivientes: {stats.get('survived', 0)} ({stats.get('survivalRate', 0)}%)
        - Fallecidos/Desaparecidos: {stats.get('deceased', 0)}
        - Distribución por Clase: {json.dumps(stats.get('classes', {}), ensure_ascii=False)}
        - Distribución por Sexo: {json.dumps(stats.get('gender', {}), ensure_ascii=False)}
        - Orígenes Principales (Países/Regiones): {json.dumps(stats.get('topOrigins', []), ensure_ascii=False)}
        - Destinos Principales: {json.dumps(stats.get('topDestinations', []), ensure_ascii=False)}
        - Edad Media: {stats.get('avgAge', 'N/A')} años

        OBJETIVODELANÁLISIS:
        Genera un informe analítico breve pero profundo que incluya:
        1. **Perfil Sociodemográfico**: Describe qué tipo de población es esta (ej: familias emigrantes, viajeros de élite, etc.).
        2. **Paradojas de Supervivencia**: Analiza si la tasa de supervivencia es inusual para este grupo y qué factores socioculturales podrían explicarlo (clase, género, "mujeres y niños primero", etc.).
        3. **Contexto Histórico**: Vincula estos datos con el fenómeno de la gran emigración transoceánica de principios del siglo XX.
        4. **Líneas de Investigación**: Sugiere una o dos preguntas críticas que un historiador debería hacerse al ver estos datos.

        Responde en formato Markdown, con un tono profesional, académico y empático. 
        Máximo 400 palabras.
        """
        
        insight = ai_service.generate_content(prompt, temperature=0.4)
        
        if not insight:
            return jsonify({'success': False, 'error': 'La IA no pudo generar una respuesta en este momento.'})
            
        return jsonify({
            'success': True,
            'insight': insight
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)})
