"""
Rutas de gestión de hemerotecas y publicaciones académicas
Incluye: listar, crear, editar, eliminar hemerotecas y publicaciones
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user

from extensions import db
from models import Hemeroteca, Publicacion, Proyecto, Prensa, Tema, AutorPublicacion
import json
from utils import geocode_city

hemerotecas_bp = Blueprint('hemerotecas', __name__)


def get_proyecto_activo():
    """Función auxiliar para obtener el proyecto activo de la sesión"""
    from routes.proyectos import get_proyecto_activo as get_proyecto
    return get_proyecto()


@hemerotecas_bp.route("/hemerotecas")
@login_required
def hemerotecas():
    """Listar hemerotecas del proyecto activo"""
    proyecto = get_proyecto_activo()
    if not proyecto:
        flash("⚠️ Debes seleccionar un proyecto primero", "warning")
        return redirect(url_for("proyectos.listar"))
    
    hemerotecas = (
        Hemeroteca.query.filter_by(proyecto_id=proyecto.id)
        .order_by(Hemeroteca.nombre)
        .all()
    )
    
    # Contar publicaciones por hemeroteca
    stats = {}
    for h in hemerotecas:
        stats[h.id] = Publicacion.query.filter_by(hemeroteca_id=h.id).count()
    
    total_hemerotecas = len(hemerotecas)
    
    return render_template("hemerotecas.html", hemerotecas=hemerotecas, stats=stats, 
                         total_hemerotecas=total_hemerotecas, proyecto=proyecto)


@hemerotecas_bp.route("/hemeroteca/nueva", methods=["GET", "POST"])
@login_required
def nueva_hemeroteca():
    """Crear nueva hemeroteca"""
    proyecto = get_proyecto_activo()
    if not proyecto:
        flash("⚠️ Debes seleccionar un proyecto primero", "warning")
        return redirect(url_for("proyectos.listar"))
    
    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        resumen_corpus = request.form.get("resumen_corpus", "").strip()
        ciudad = request.form.get("ciudad", "").strip()
        provincia = request.form.get("provincia", "").strip()
        pais = request.form.get("pais", "").strip()
        institucion = request.form.get("institucion", "").strip()
        url = request.form.get("url", "").strip()
        compartida = request.form.get("compartida") == "on"  # Checkbox value
        
        if not nombre:
            flash("❌ El nombre de la hemeroteca es obligatorio", "danger")
            return redirect(url_for("hemerotecas.nueva_hemeroteca"))
        
        # Verificar si ya existe
        existe = Hemeroteca.query.filter_by(
            nombre=nombre,
            proyecto_id=proyecto.id
        ).first()
        
        if existe:
            flash(f"⚠️ Ya existe una hemeroteca con el nombre '{nombre}'", "warning")
            return redirect(url_for("hemerotecas.hemerotecas"))
        
        nueva_hemeroteca = Hemeroteca(
            nombre=nombre,
            resumen_corpus=resumen_corpus,
            ciudad=ciudad,
            provincia=provincia,
            pais=pais,
            institucion=institucion,
            url=url,
            compartida=compartida,
            proyecto_id=proyecto.id
        )
        
        # Geocodificar ciudad si existe
        if ciudad:
            try:
                coords = geocode_city(ciudad)
                if coords:
                    nueva_hemeroteca.latitud = coords[0]
                    nueva_hemeroteca.longitud = coords[1]
            except Exception as e:
                print(f"Error geocodificando: {e}")
        
        db.session.add(nueva_hemeroteca)
        db.session.commit()
        
        flash(f"✅ Hemeroteca '{nombre}' creada correctamente", "success")
        return redirect(url_for("hemerotecas.hemerotecas"))
    
    return render_template("hemeroteca_form.html", hemeroteca=None, proyecto=proyecto, accion='nueva')


@hemerotecas_bp.route("/hemeroteca/editar/<int:id>", methods=["GET", "POST"])
@login_required
def editar_hemeroteca(id):
    """Editar hemeroteca existente"""
    hemeroteca = Hemeroteca.query.get_or_404(id)
    
    # Verificar permisos
    if hemeroteca.proyecto_id != get_proyecto_activo().id:
        flash("❌ No tienes permiso para editar esta hemeroteca", "danger")
        return redirect(url_for("hemerotecas.hemerotecas"))
    
    if request.method == "POST":
        hemeroteca.nombre = request.form.get("nombre", "").strip()
        hemeroteca.resumen_corpus = request.form.get("resumen_corpus", "").strip()
        hemeroteca.ciudad = request.form.get("ciudad", "").strip()
        hemeroteca.provincia = request.form.get("provincia", "").strip()
        hemeroteca.pais = request.form.get("pais", "").strip()
        hemeroteca.institucion = request.form.get("institucion", "").strip()
        hemeroteca.url = request.form.get("url", "").strip()
        hemeroteca.compartida = request.form.get("compartida") == "on"
        
        # Actualizar geocodificación si cambió la ciudad
        if hemeroteca.ciudad:
            try:
                coords = geocode_city(hemeroteca.ciudad)
                if coords:
                    hemeroteca.latitud = coords[0]
                    hemeroteca.longitud = coords[1]
            except Exception as e:
                print(f"Error geocodificando: {e}")
        
        db.session.commit()
        flash(f"💾 Hemeroteca '{hemeroteca.nombre}' actualizada", "success")
        return redirect(url_for("hemerotecas.hemerotecas"))
    
    proyecto = get_proyecto_activo()
    return render_template("hemeroteca_form.html", hemeroteca=hemeroteca, proyecto=proyecto, accion='editar')


@hemerotecas_bp.route("/hemeroteca/borrar/<int:id>", methods=["POST"])
@login_required
def borrar_hemeroteca(id):
    """Eliminar hemeroteca"""
    hemeroteca = Hemeroteca.query.get_or_404(id)
    
    # Verificar permisos
    if hemeroteca.proyecto_id != get_proyecto_activo().id:
        flash("❌ No tienes permiso para eliminar esta hemeroteca", "danger")
        return redirect(url_for("hemerotecas.hemerotecas"))
    
    # Verificar si tiene publicaciones asociadas
    num_publicaciones = Publicacion.query.filter_by(hemeroteca_id=hemeroteca.id).count()
    if num_publicaciones > 0:
        flash(f"⚠️ No se puede eliminar '{hemeroteca.nombre}' porque tiene {num_publicaciones} publicaciones asociadas", "warning")
        return redirect(url_for("hemerotecas.hemerotecas"))
    
    nombre = hemeroteca.nombre
    db.session.delete(hemeroteca)
    db.session.commit()
    
    flash(f"🗑️ Hemeroteca '{nombre}' eliminada correctamente", "success")
    return redirect(url_for("hemerotecas.hemerotecas"))


@hemerotecas_bp.route("/hemeroteca/migrar/<int:id>", methods=["GET", "POST"])
@login_required
def migrar_hemeroteca(id):
    """Migrar hemeroteca a otro proyecto"""
    hemeroteca = Hemeroteca.query.get_or_404(id)
    
    # Verificar permisos
    proyecto_actual = get_proyecto_activo()
    if hemeroteca.proyecto_id != proyecto_actual.id:
        flash("❌ No tienes permiso para migrar esta hemeroteca", "danger")
        return redirect(url_for("hemerotecas.hemerotecas"))
    
    # Obtener todos los proyectos del usuario excepto el actual
    from models import Proyecto
    proyectos = Proyecto.query.filter(
        Proyecto.user_id == current_user.id,
        Proyecto.id != proyecto_actual.id
    ).all()
    
    if request.method == "POST":
        proyecto_id = request.form.get("proyecto_id")
        
        if not proyecto_id:
            flash("⚠️ Debes seleccionar un proyecto destino", "warning")
            return redirect(url_for("hemerotecas.migrar_hemeroteca", id=id))
        
        # Verificar que el proyecto destino pertenece al usuario
        proyecto_destino = Proyecto.query.get_or_404(proyecto_id)
        if proyecto_destino.user_id != current_user.id:
            flash("❌ No tienes permiso para migrar a ese proyecto", "danger")
            return redirect(url_for("hemerotecas.hemerotecas"))
        
        # Migrar la hemeroteca
        hemeroteca.proyecto_id = proyecto_destino.id
        db.session.commit()
        
        flash(f"✅ Hemeroteca '{hemeroteca.nombre}' migrada a '{proyecto_destino.nombre}'", "success")
        return redirect(url_for("hemerotecas.hemerotecas"))
    
    return render_template("migrar_hemeroteca.html", hemeroteca=hemeroteca, proyectos=proyectos)


@hemerotecas_bp.route("/hemerotecas/repositorio")
@login_required
def repositorio_global():
    """Listar hemerotecas del repositorio global (todas las únicas)"""
    proyecto_actual = get_proyecto_activo()
    
    # Obtener países para el filtro (solo de repositorios externos compartidos)
    query_base = Hemeroteca.query.filter(
        Hemeroteca.proyecto_id != proyecto_actual.id,
        Hemeroteca.compartida == True
    )
    
    # Obtener lista de países únicos (solo de hemerotecas compartidas)
    paises = db.session.query(Hemeroteca.pais).filter(
        Hemeroteca.proyecto_id != proyecto_actual.id,
        Hemeroteca.compartida == True,
        Hemeroteca.pais != None,
        Hemeroteca.pais != ""
    ).distinct().order_by(Hemeroteca.pais).all()
    lista_paises = [p[0] for p in paises]
    
    # Filtrar si hay país seleccionado
    pais_seleccionado = request.args.get("pais")
    if pais_seleccionado:
        query_base = query_base.filter(Hemeroteca.pais == pais_seleccionado)
        
    # Obtener datos y agrupar por nombre para evitar duplicados en la vista
    # Priorizamos verificadas en el ordenamiento inicial
    todas = query_base.order_by(Hemeroteca.verificada.desc(), Hemeroteca.nombre).all()
    
    # Deduplicar por nombre (case insensitive) y url
    unicas = {}
    for h in todas:
        key = (h.nombre.lower().strip(), (h.url or "").lower().strip())
        if key not in unicas:
            unicas[key] = h
        elif h.verificada and not unicas[key].verificada:
            # Si encontramos una versión verificada del mismo repositorio, la preferimos
            unicas[key] = h
            
    # Convertir a lista y ordenar
    lista_global = sorted(unicas.values(), key=lambda x: x.nombre)
    
    return render_template("repositorio_hemerotecas.html", 
                         hemerotecas=lista_global, 
                         total_globales=len(lista_global),
                         proyecto=proyecto_actual,
                         paises=lista_paises,
                         pais_seleccionado=pais_seleccionado)


@hemerotecas_bp.route("/hemeroteca/importar/<int:id>", methods=["POST"])
@login_required
def importar_hemeroteca(id):
    """Importar (clonar) una hemeroteca del global al proyecto actual"""
    origen = Hemeroteca.query.get_or_404(id)
    proyecto_destino = get_proyecto_activo()
    
    if not proyecto_destino:
        flash("⚠️ Selecciona un proyecto primero", "warning")
        return redirect(url_for("proyectos.listar"))
        
    # Verificar si ya existe en destino
    existe = Hemeroteca.query.filter_by(
        proyecto_id=proyecto_destino.id,
        nombre=origen.nombre
    ).first()
    
    if existe:
        flash(f"⚠️ La hemeroteca '{origen.nombre}' ya existe en tu proyecto", "warning")
        return redirect(url_for("hemerotecas.repositorio_global"))
        
    # Clonar Hemeroteca (compartida=False para que no aparezca en el global)
    nueva_hemeroteca = Hemeroteca(
        proyecto_id=proyecto_destino.id,
        nombre=origen.nombre,
        institucion=origen.institucion,
        pais=origen.pais,
        provincia=origen.provincia,
        ciudad=origen.ciudad,
        resumen_corpus=origen.resumen_corpus,
        url=origen.url,
        compartida=False  # No compartir por defecto al importar
    )
    db.session.add(nueva_hemeroteca)
    db.session.flush() # Para obtener ID
    
    # Clonar Publicaciones Hijas
    contador_pubs = 0
    for pub in origen.publicaciones:
        # Verificar unicidad de publicación en destino (por si acaso)
        pub_existe = Publicacion.query.filter_by(
            proyecto_id=proyecto_destino.id, 
            nombre=pub.nombre
        ).first()
        
        if not pub_existe:
            nueva_pub = Publicacion(
                proyecto_id=proyecto_destino.id,
                hemeroteca_id=nueva_hemeroteca.id, # Vincular a la nueva copia
                nombre=pub.nombre,
                descripcion=pub.descripcion,
                tipo_recurso=pub.tipo_recurso,
                ciudad=pub.ciudad,
                provincia=pub.provincia,
                pais_publicacion=pub.pais_publicacion,
                idioma=pub.idioma,
                licencia=pub.licencia,
                formato_fuente=pub.formato_fuente,
                licencia_predeterminada=pub.licencia_predeterminada,
                fuente=pub.fuente,
                tema=pub.tema,
                editorial=pub.editorial,
                url_publi=pub.url_publi,
                frecuencia=pub.frecuencia
            )
            db.session.add(nueva_pub)
            contador_pubs += 1
            
    db.session.commit()
    
    flash(f"✅ Importada '{nueva_hemeroteca.nombre}' con {contador_pubs} publicaciones", "success")
    return redirect(url_for("hemerotecas.hemerotecas"))


# =========================================================
# RUTAS DE ADMINISTRACIÓN: VERIFICACIÓN Y FUSIÓN
# =========================================================

@hemerotecas_bp.route("/hemeroteca/verificar/<int:id>", methods=["POST"])
@login_required
def verificar_hemeroteca(id):
    """Marcar una hemeroteca como verificada (solo admin)"""
    if current_user.rol != "admin":
        flash("❌ No tienes permisos de administrador", "danger")
        return redirect(url_for("hemerotecas.repositorio_global"))
        
    hemeroteca = Hemeroteca.query.get_or_404(id)
    hemeroteca.verificada = not hemeroteca.verificada  # Toggle
    db.session.commit()
    
    estado = "verificada" if hemeroteca.verificada else "desmarcada como verificada"
    flash(f"✅ La hemeroteca '{hemeroteca.nombre}' ha sido {estado}", "success")
    return redirect(url_for("hemerotecas.repositorio_global"))


@hemerotecas_bp.route("/hemeroteca/fusionar", methods=["GET", "POST"])
@login_required
def fusionar_hemerotecas():
    """Herramienta para fusionar dos hemerotecas duplicadas (solo admin)"""
    if current_user.rol != "admin":
        flash("❌ No tienes permisos de administrador", "danger")
        return redirect(url_for("dashboard"))
        
    if request.method == "POST":
        id_origen = request.form.get("id_origen", type=int)
        id_destino = request.form.get("id_destino", type=int)
        
        if not id_origen or not id_destino or id_origen == id_destino:
            flash("⚠️ Debes seleccionar dos hemerotecas diferentes", "warning")
            return redirect(url_for("hemerotecas.fusionar_hemerotecas"))
            
        origen = Hemeroteca.query.get_or_404(id_origen)
        destino = Hemeroteca.query.get_or_404(id_destino)
        
        # Mover todas las publicaciones
        publicaciones = Publicacion.query.filter_by(hemeroteca_id=origen.id).all()
        contador = 0
        for pub in publicaciones:
            # Comprobar si ya existe una con el mismo nombre en el destino
            existe = Publicacion.query.filter_by(hemeroteca_id=destino.id, nombre=pub.nombre).first()
            if not existe:
                pub.hemeroteca_id = destino.id
                # Si la publicación original pertenecía a otro proyecto, 
                # la vinculamos al proyecto de la hemeroteca destino para coherencia
                pub.proyecto_id = destino.proyecto_id
                contador += 1
            else:
                # Si ya existe, podríamos intentar mover los artículos vinculados
                # pero por seguridad de datos, solo informamos o los movemos si el nombre es idéntico
                # Actualizar Prensa (artículos) vinculados a la publicación redundante
                Prensa.query.filter_by(id_publicacion=pub.id_publicacion).update({"id_publicacion": existe.id_publicacion})
                db.session.delete(pub) # Eliminamos la publicación duplicada
        
        nombre_eliminada = origen.nombre
        db.session.delete(origen)
        db.session.commit()
        
        flash(f"🚀 Fusión completada. Se han movido/fusionado {len(publicaciones)} publicaciones de '{nombre_eliminada}' a '{destino.nombre}'", "success")
        return redirect(url_for("hemerotecas.repositorio_global"))
        
    # Obtener todas las hemerotecas compartidas para el formulario de fusión
    hemerotecas = Hemeroteca.query.filter_by(compartida=True).order_by(Hemeroteca.nombre).all()
    return render_template("fusionar_hemerotecas.html", hemerotecas=hemerotecas)


# =========================================================
# RUTAS DE PUBLICACIONES ACADÉMICAS
# =========================================================

@hemerotecas_bp.route("/publicaciones")
@login_required
def lista_publicaciones():
    """Listar publicaciones académicas del proyecto activo"""
    proyecto = get_proyecto_activo()
    if not proyecto:
        flash("⚠️ Debes seleccionar un proyecto primero", "warning")
        return redirect(url_for("proyectos.listar"))
    
    # Filtrar por hemeroteca si se especifica
    hemeroteca_id = request.args.get("hemeroteca_id", type=int)
    
    query = Publicacion.query.filter_by(proyecto_id=proyecto.id)
    if hemeroteca_id:
        query = query.filter_by(hemeroteca_id=hemeroteca_id)
    
    publicaciones = query.order_by(Publicacion.nombre).all()
    
    # Crear diccionario de estadísticas
    stats = {}
    for p in publicaciones:
        # Contar artículos que usan esta publicación
        num_articulos = Prensa.query.filter_by(
            id_publicacion=p.id_publicacion,
            proyecto_id=proyecto.id
        ).count()
        stats[p.id_publicacion] = num_articulos
    
    # Obtener hemerotecas para el formulario
    hemerotecas = Hemeroteca.query.filter_by(proyecto_id=proyecto.id).order_by(Hemeroteca.nombre).all()
    
    # Determinar filtro activo
    filtro_activo = None
    if hemeroteca_id:
        hem = Hemeroteca.query.get(hemeroteca_id)
        if hem:
            filtro_activo = f"Hemeroteca: {hem.nombre}"
    
    # Calcular totales
    total_medios = len(publicaciones)
    # Contar total de noticias vinculadas a estas publicaciones
    total_noticias = 0
    if publicaciones:
        pub_ids = [p.id_publicacion for p in publicaciones]
        total_noticias = Prensa.query.filter(
            Prensa.id_publicacion.in_(pub_ids),
            Prensa.proyecto_id == proyecto.id
        ).count()

    return render_template(
        "publicaciones.html",
        publicaciones=publicaciones,
        stats=stats,
        hemerotecas=hemerotecas,
        proyecto=proyecto,
        filtro_activo=filtro_activo,
        total_medios=total_medios,
        total_noticias=total_noticias
    )


@hemerotecas_bp.route("/publicacion/nueva", methods=["GET", "POST"])
@login_required
def nueva_publicacion():
    """Crear nueva publicación académica"""
    proyecto = get_proyecto_activo()
    if not proyecto:
        flash("⚠️ Debes seleccionar un proyecto primero", "warning")
        return redirect(url_for("proyectos.listar"))
    
    if request.method == "POST":
        with open("/opt/hesiox/debug_post.log", "a") as f:
            f.write(f"\n[HEMEROTECAS] POST Data (Nueva):\n")
            for k, v in request.form.items():
                f.write(f"  {k}: {v}\n")
            f.write(f"  coleccion (get): {request.form.get('coleccion')}\n")
            f.write(f"  pseudonimo (get): {request.form.get('pseudonimo')}\n")

        nombre = request.form.get("nombre", "").strip()
        
        if not nombre:
            flash("❌ El nombre de la publicación es obligatorio", "danger")
            return redirect(url_for("hemerotecas.nueva_publicacion"))
        
        # Verificar si ya existe
        existe = Publicacion.query.filter_by(
            nombre=nombre,
            proyecto_id=proyecto.id
        ).first()
        
        if existe:
            flash(f"⚠️ Ya existe una publicación con el nombre '{nombre}'", "warning")
            return redirect(url_for("hemerotecas.lista_publicaciones"))
        
        tema_val = request.form.get("tema", "").strip()

        nueva_pub = Publicacion(
            nombre=nombre,
            descripcion=request.form.get("descripcion", "").strip(),
            tipo_recurso=request.form.get("tipo_recurso", "").strip(),
            ciudad=request.form.get("ciudad", "").strip(),
            provincia=request.form.get("provincia", "").strip(),
            pais_publicacion=request.form.get("pais_publicacion", "").strip(),
            idioma=request.form.get("idioma", "").strip(),
            licencia=request.form.get("licencia", "CC BY 4.0").strip(),
            formato_fuente=request.form.get("formato_fuente", "").strip(),
            fuente=request.form.get("fuente", "").strip(),
            tema=tema_val,
            editorial=request.form.get("editorial", "").strip(),
            url_publi=request.form.get("url_publi", "").strip(),
            frecuencia=request.form.get("frecuencia", "").strip(),
            proyecto_id=proyecto.id,
            actos_totales=request.form.get("actos_totales", "").strip(),
            escenas_totales=request.form.get("escenas_totales", "").strip(),
            reparto_total=request.form.get("reparto_total", "").strip(),
            coleccion=request.form.get("coleccion", "").strip(),
            pseudonimo=request.form.get("pseudonimo", "").strip()
        )
        
        # 2.5 GUARDAR AUTORES RELACIONADOS
        nombres_lista = request.form.getlist("nombre_autor[]")
        apellidos_lista = request.form.getlist("apellido_autor[]")
        tipos_lista = request.form.getlist("tipo_autor[]")
        anonimos_raw = request.form.getlist("es_anonimo_raw[]")

        for i in range(len(tipos_lista)):
            nom = (nombres_lista[i] if i < len(nombres_lista) else "").strip()
            ape = (apellidos_lista[i] if i < len(apellidos_lista) else "").strip()
            tip = tipos_lista[i]
            es_anon = (i < len(anonimos_raw) and anonimos_raw[i] == "si")
            
            nuevo_aut = AutorPublicacion(
                nombre=nom if not es_anon else None,
                apellido=ape if not es_anon else None,
                tipo=tip,
                es_anonimo=es_anon,
                orden=i
            )
            nueva_pub.autores.append(nuevo_aut)
            
            # Sincronizar el primero para compatibilidad
            if i == 0:
                nueva_pub.nombre_autor = nom if not es_anon else None
                nueva_pub.apellido_autor = ape if not es_anon else None
        
        # Asociar a hemeroteca si se seleccionó
        hemeroteca_id = request.form.get("hemeroteca_id")
        if hemeroteca_id and hemeroteca_id.isdigit():
            nueva_pub.hemeroteca_id = int(hemeroteca_id)
        
        db.session.add(nueva_pub)
        db.session.commit()
        
        flash(f"✅ Publicación '{nombre}' creada correctamente", "success")
        return redirect(url_for("hemerotecas.lista_publicaciones"))
    
    # Serializar datos de hemerotecas para el frontend
    hemerotecas = Hemeroteca.query.filter_by(proyecto_id=proyecto.id).order_by(Hemeroteca.nombre).all()
    hemerotecas_data = {}
    for h in hemerotecas:
        hemerotecas_data[h.id] = {
            "id": h.id,
            "nombre": h.nombre,
            "institucion": h.institucion or h.nombre,
            "ciudad": h.ciudad or "",
            "provincia": h.provincia or "",
            "pais": h.pais or ""
        }

    return render_template("nueva_publicacion.html", hemerotecas=hemerotecas, proyecto=proyecto, hemerotecas_data=hemerotecas_data)


@hemerotecas_bp.route("/publicacion/editar/<int:id>", methods=["GET", "POST"])
@login_required
def editar_publicacion(id):
    """Editar publicación académica existente"""
    publicacion = Publicacion.query.get_or_404(id)
    
    # Verificar permisos
    if publicacion.proyecto_id != get_proyecto_activo().id:
        flash("❌ No tienes permiso para editar esta publicación", "danger")
        return redirect(url_for("hemerotecas.lista_publicaciones"))
    
    if request.method == "POST":
        with open("/opt/hesiox/debug_post.log", "a") as f:
            f.write(f"\n[HEMEROTECAS] POST Data for ID {id}:\n")
            for k, v in request.form.items():
                f.write(f"  {k}: {v}\n")
            f.write(f"  tema (get): {request.form.get('tema')}\n")
            f.write(f"  coleccion (get): {request.form.get('coleccion')}\n")
            f.write(f"  pseudonimo (get): {request.form.get('pseudonimo')}\n")

        nuevo_nombre = request.form.get("nombre", "").strip()
        # Validar unicidad del nombre (ignorando la publicación actual)
        existe = Publicacion.query.filter(Publicacion.nombre == nuevo_nombre, Publicacion.id_publicacion != publicacion.id_publicacion).first()
        if existe:
            flash(f"❌ Ya existe otra publicación con el nombre '{nuevo_nombre}'. Elige un nombre diferente.", "danger")
            proyecto = get_proyecto_activo()
            hemerotecas = Hemeroteca.query.filter_by(proyecto_id=proyecto.id).order_by(Hemeroteca.nombre).all()
            # Serializar datos para el frontend en caso de error
            hemerotecas_data = {h.id: {"id": h.id, "nombre": h.nombre, "institucion": h.institucion or h.nombre, "ciudad": h.ciudad or "", "provincia": h.provincia or "", "pais": h.pais or ""} for h in hemerotecas}
            autores_data = [{"nombre": a.nombre, "apellido": a.apellido, "tipo": a.tipo, "es_anonimo": a.es_anonimo} for a in publicacion.autores]
            return render_template("editar_publicacion.html", pub=publicacion, hemerotecas=hemerotecas, proyecto=proyecto, hemerotecas_data=hemerotecas_data, autores_json=json.dumps(autores_data))

        publicacion.nombre = nuevo_nombre
        with open("/opt/hesiox/debug_post.log", "a") as f:
            f.write(f"  NAME CHECK PASSED: {nuevo_nombre}\n")
        publicacion.descripcion = request.form.get("descripcion", "").strip()
        publicacion.tipo_recurso = request.form.get("tipo_recurso", "").strip()
        publicacion.ciudad = request.form.get("ciudad", "").strip()
        publicacion.provincia = request.form.get("provincia", "").strip()
        publicacion.pais_publicacion = request.form.get("pais_publicacion", "").strip()
        publicacion.idioma = request.form.get("idioma", "").strip()
        publicacion.licencia = request.form.get("licencia", "CC BY 4.0").strip()
        publicacion.formato_fuente = request.form.get("formato_fuente", "").strip()
        publicacion.fuente = request.form.get("fuente", "").strip()
        publicacion.tema = request.form.get("tema", "").strip()

        publicacion.editorial = request.form.get("editorial", "").strip()
        publicacion.url_publi = request.form.get("url_publi", "").strip()
        publicacion.frecuencia = request.form.get("frecuencia", "").strip()
        
        # Campos teatrales
        publicacion.actos_totales = request.form.get("actos_totales", "").strip()
        publicacion.escenas_totales = request.form.get("escenas_totales", "").strip()
        publicacion.reparto_total = request.form.get("reparto_total", "").strip()
        publicacion.coleccion = request.form.get("coleccion", "").strip()
        publicacion.pseudonimo = request.form.get("pseudonimo", "").strip()

        try:
            # 1. GESTIÓN DE MÚLTIPLES AUTORES
            nombres_lista = request.form.getlist("nombre_autor[]")
            apellidos_lista = request.form.getlist("apellido_autor[]")
            tipos_lista = request.form.getlist("tipo_autor[]")
            anonimos_raw = request.form.getlist("es_anonimo_raw[]")

            # Limpiar autores antiguos usando la relación (delete-orphan se encargará de borrarlos de la DB)
            publicacion.autores = []
            db.session.flush()
            
            # Procesamos la nueva lista
            for i in range(len(tipos_lista)):
                nom = (nombres_lista[i] if i < len(nombres_lista) else "").strip()
                ape = (apellidos_lista[i] if i < len(apellidos_lista) else "").strip()
                tip = tipos_lista[i]
                es_anon = (i < len(anonimos_raw) and anonimos_raw[i] == "si")
                
                nuevo_aut = AutorPublicacion(
                    publicacion_id=publicacion.id_publicacion,
                    nombre=nom if not es_anon else None,
                    apellido=ape if not es_anon else None,
                    tipo=tip,
                    es_anonimo=es_anon,
                    orden=i
                )
                publicacion.autores.append(nuevo_aut)
                
                # Sincronizar el primero para compatibilidad
                if i == 0:
                    publicacion.nombre_autor = nom if not es_anon else None
                    publicacion.apellido_autor = ape if not es_anon else None
        except Exception as e:
            with open("/opt/hesiox/debug_post.log", "a") as f:
                f.write(f"  ERROR IN AUTHORS LOOP: {str(e)}\n")
            raise e


        # Actualizar hemeroteca
        old_hemeroteca_id = publicacion.hemeroteca_id
        new_hemeroteca_id = None

        hemeroteca_id_form = request.form.get("hemeroteca_id")
        if hemeroteca_id_form and hemeroteca_id_form.isdigit():
            new_hemeroteca_id = int(hemeroteca_id_form)
            publicacion.hemeroteca_id = new_hemeroteca_id
        else:
            publicacion.hemeroteca_id = None

        # ---------------------------------------------------------
        # LÓGICA DE PROPAGACIÓN DE CAMBIOS A NOTICIAS VINCULADAS
        # ---------------------------------------------------------
        propagar = request.form.get("propagar") == "on"

        db.session.add(publicacion) # Asegurar que está en sesión
        db.session.flush()
        
        with open("/opt/hesiox/debug_post.log", "a") as f:
            f.write(f"  STATE BEFORE COMMIT (ID {publicacion.id_publicacion}):\n")
            f.write(f"    nombre: {publicacion.nombre}\n")
            f.write(f"    coleccion: {publicacion.coleccion}\n")
            f.write(f"    pseudonimo: {publicacion.pseudonimo}\n")
            f.write(f"    actos_totales: {publicacion.actos_totales}\n")

        db.session.commit()
        db.session.refresh(publicacion)
        
        with open("/opt/hesiox/debug_post.log", "a") as f:
            f.write(f"  AFTER COMMIT (ID {publicacion.id_publicacion}):\n")
            f.write(f"    coleccion in DB: {publicacion.coleccion}\n")
            f.write(f"    pseudonimo in DB: {publicacion.pseudonimo}\n")
            f.write(f"    autores count in DB: {len(publicacion.autores)}\n")
            for a in publicacion.autores:
                f.write(f"      - {a.nombre} {a.apellido} ({a.tipo})\n")

        # Si el usuario marcó la opción de propagar cambios
        count_updated = 0
        if propagar:
            # Construir diccionario de actualización para Prensa
            update_payload = {}
            
            # Propagar nombre de publicación
            if publicacion.nombre:
                update_payload['publicacion'] = publicacion.nombre
                
            # Propagar autoría principal (compatibilidad)
            if publicacion.nombre_autor is not None:
                update_payload['nombre_autor'] = publicacion.nombre_autor
            if publicacion.apellido_autor is not None:
                update_payload['apellido_autor'] = publicacion.apellido_autor
            
            # Propagar ciudad
            if publicacion.ciudad:
                update_payload['ciudad'] = publicacion.ciudad
            
            if publicacion.coleccion:
                update_payload['coleccion'] = publicacion.coleccion
            
            if publicacion.pseudonimo:
                update_payload['pseudonimo'] = publicacion.pseudonimo
                
            if publicacion.pais_publicacion:
                update_payload['pais_publicacion'] = publicacion.pais_publicacion

            # Propagar fuente (desde hemeroteca o campo directo)
            fuente_a_propagar = None
            if publicacion.hemeroteca_id:
                hem = Hemeroteca.query.get(publicacion.hemeroteca_id)
                if hem:
                    fuente_a_propagar = hem.institucion or hem.nombre
            elif publicacion.fuente:
                fuente_a_propagar = publicacion.fuente
                
            if fuente_a_propagar:
                update_payload['fuente'] = fuente_a_propagar
            
            # Propagar licencia
            if publicacion.licencia:
                update_payload['licencia'] = publicacion.licencia
            
            # Propagar formato_fuente
            if publicacion.formato_fuente:
                update_payload['formato_fuente'] = publicacion.formato_fuente
            
            # Propagar editorial
            if publicacion.editorial:
                update_payload['editorial'] = publicacion.editorial
            
            # Propagar descripcion histórica de publicación a descripcion_publicacion de la noticia
            if publicacion.descripcion:
                update_payload['descripcion_publicacion'] = publicacion.descripcion
            
            if update_payload:
                try:
                    # 1. Actualizar campos directos en la tabla Prensa
                    updated_rows = Prensa.query.filter_by(id_publicacion=publicacion.id_publicacion).update(update_payload)
                    
                    # 2. Sincronizar relación de autores (tabla autores_prensa)
                    prensa_ids_query = db.session.query(Prensa.id).filter_by(id_publicacion=publicacion.id_publicacion).all()
                    prensa_ids = [p[0] for p in prensa_ids_query]
                    
                    if prensa_ids:
                        # Eliminar autores actuales de esas noticias
                        AutorPrensa.query.filter(AutorPrensa.prensa_id.in_(prensa_ids)).delete(synchronize_session=False)
                        
                        # Preparar inserción masiva de los nuevos autores (copiados de la publicación)
                        nuevos_autores_data = []
                        for aut_pub in publicacion.autores:
                            for p_id in prensa_ids:
                                nuevos_autores_data.append({
                                    'prensa_id': p_id,
                                    'nombre': aut_pub.nombre,
                                    'apellido': aut_pub.apellido,
                                    'tipo': aut_pub.tipo,
                                    'es_anonimo': aut_pub.es_anonimo,
                                    'orden': aut_pub.orden
                                })
                        
                        if nuevos_autores_data:
                            db.session.execute(AutorPrensa.__table__.insert(), nuevos_autores_data)
                    
                    db.session.commit()
                    count_updated = updated_rows
                except Exception as e:
                    db.session.rollback()
                    app.logger.error(f"Error propagando cambios de autoría: {e}")
                    print(f"Error propagando cambios: {e}")

        msg_extra = ""
        if count_updated > 0:
            msg_extra = f" y se actualizaron {count_updated} noticias vinculadas."
            
        flash(f"💾 Publicación '{publicacion.nombre}' actualizada{msg_extra}", "success")
        return redirect(url_for("hemerotecas.lista_publicaciones"))
    
    proyecto = get_proyecto_activo()
    hemerotecas = Hemeroteca.query.filter_by(proyecto_id=proyecto.id).order_by(Hemeroteca.nombre).all()
    
    # Serializar datos de hemerotecas para el frontend
    hemerotecas_data = {}
    for h in hemerotecas:
        hemerotecas_data[h.id] = {
            "id": h.id,
            "nombre": h.nombre,
            "institucion": h.institucion or h.nombre,
            "ciudad": h.ciudad or "",
            "provincia": h.provincia or "",
            "pais": h.pais or ""
        }

    autores_json = json.dumps([{
        'nombre': a.nombre or '',
        'apellido': a.apellido or '',
        'tipo': a.tipo or 'autor',
        'es_anonimo': a.es_anonimo,
        'orden': a.orden
    } for a in publicacion.autores])

    return render_template("editar_publicacion.html", pub=publicacion, hemerotecas=hemerotecas, proyecto=proyecto, hemerotecas_data=hemerotecas_data, autores_json=autores_json)


@hemerotecas_bp.route("/publicacion/borrar/<int:id>", methods=["POST"])
@login_required
def borrar_publicacion(id):
    """Eliminar publicación académica"""
    publicacion = Publicacion.query.get_or_404(id)
    
    # Verificar permisos
    if publicacion.proyecto_id != get_proyecto_activo().id:
        flash("❌ No tienes permiso para eliminar esta publicación", "danger")
        return redirect(url_for("hemerotecas.lista_publicaciones"))
    
    # Verificar si tiene artículos asociados
    num_articulos = Prensa.query.filter_by(id_publicacion=publicacion.id_publicacion).count()
    if num_articulos > 0:
        flash(f"⚠️ No se puede eliminar '{publicacion.nombre}' porque tiene {num_articulos} artículos asociados", "warning")
        return redirect(url_for("hemerotecas.lista_publicaciones"))
    
    nombre = publicacion.nombre
    db.session.delete(publicacion)
    db.session.commit()
    
    flash(f"🗑️ Publicación '{nombre}' eliminada correctamente", "success")
    return redirect(url_for("hemerotecas.lista_publicaciones"))


@hemerotecas_bp.route("/api/hemeroteca/<int:id>/datos")
@login_required
def get_hemeroteca_datos(id):
    """API para obtener datos de una hemeroteca (AJAX)"""
    hemeroteca = Hemeroteca.query.get_or_404(id)
    
    # Verificar permisos
    if hemeroteca.proyecto_id != get_proyecto_activo().id:
        return jsonify({"error": "Sin permisos"}), 403
    
    return jsonify({
        "nombre": hemeroteca.nombre,
        "descripcion": hemeroteca.descripcion or "",
        "ciudad": hemeroteca.ciudad or "",
        "pais": hemeroteca.pais or "",
        "institucion_gestora": hemeroteca.institucion_gestora or "",
        "url": hemeroteca.url or ""
    })


@hemerotecas_bp.route("/api/publicacion/<int:id>")
@login_required
def api_publicacion_get(id):
    """API para obtener datos de una publicación (AJAX)"""
    pub = Publicacion.query.get_or_404(id)
    
    # Verificar permisos
    if pub.proyecto_id != get_proyecto_activo().id:
        return jsonify({"error": "Sin permisos"}), 403
    
    return jsonify({
        "id_publicacion": pub.id_publicacion,
        "nombre": pub.nombre,
        "ciudad": pub.ciudad,
        "provincia": pub.provincia,
        "pais_publicacion": pub.pais_publicacion,
        "fuente": pub.fuente,
        "formato_fuente": pub.formato_fuente,
        "descripcion": pub.descripcion,
        "idioma": pub.idioma,
        "licencia_predeterminada": pub.licencia_predeterminada,
        "url_publi": getattr(pub, "url_publi", None),
    })


@hemerotecas_bp.route("/migrar_publicacion", methods=["GET", "POST"])
@login_required
def migrar_publicacion():
    proyectos = Proyecto.query.all()
    publicaciones = []
    proyecto_origen_id = request.args.get("origen") or request.form.get("origen")
    proyecto_destino_id = request.args.get("destino") or request.form.get("destino")
    mensaje = None

    try:
        proyecto_origen_id_int = int(proyecto_origen_id) if proyecto_origen_id is not None else None
        proyecto_destino_id_int = int(proyecto_destino_id) if proyecto_destino_id is not None else None
    except Exception:
        proyecto_origen_id_int = None
        proyecto_destino_id_int = None

    if proyecto_origen_id_int:
        publicaciones = Publicacion.query.filter_by(proyecto_id=proyecto_origen_id_int).all()

    hemerotecas_destino_ids = set()
    if proyecto_destino_id_int:
        hemerotecas_destino_ids = {h.id for h in Hemeroteca.query.filter_by(proyecto_id=proyecto_destino_id_int).all()}

    hemerotecas_faltantes = set()
    publicaciones_no_migradas = []

    if request.method == "POST":
        if not proyecto_origen_id_int or not proyecto_destino_id_int:
            mensaje = "Debes seleccionar ambos proyectos antes de migrar."
        else:
            seleccionadas = request.form.getlist("publicaciones")
            migradas = 0
            for pub_id in seleccionadas:
                pub = Publicacion.query.get(pub_id)
                if pub:
                    # Verificar hemeroteca
                    if pub.hemeroteca_id and pub.hemeroteca_id not in hemerotecas_destino_ids:
                        hemerotecas_faltantes.add(pub.hemeroteca_id)
                        publicaciones_no_migradas.append(pub.nombre)
                        continue
                    existe = Publicacion.query.filter_by(proyecto_id=proyecto_destino_id_int, nombre=pub.nombre).first()
                    if not existe:
                        nueva = Publicacion(
                            proyecto_id=proyecto_destino_id_int,
                            nombre=pub.nombre,
                            descripcion=pub.descripcion,
                            tipo_recurso=pub.tipo_recurso,
                            ciudad=pub.ciudad,
                            provincia=pub.provincia,
                            pais_publicacion=pub.pais_publicacion,
                            idioma=pub.idioma,
                            licencia=pub.licencia,
                            formato_fuente=pub.formato_fuente,
                            licencia_predeterminada=pub.licencia_predeterminada,
                            fuente=pub.fuente,
                            tema=pub.tema,
                            editorial=pub.editorial,
                            url_publi=pub.url_publi,
                            frecuencia=pub.frecuencia,
                            hemeroteca_id=pub.hemeroteca_id,
                        )
                        db.session.add(nueva)
                        migradas += 1
            db.session.commit()
            if hemerotecas_faltantes:
                mensaje = f"Migradas {migradas} publicaciones. Las siguientes publicaciones NO se migraron porque su hemeroteca no existe en el proyecto destino: {', '.join(publicaciones_no_migradas)}. Migra primero la hemeroteca correspondiente."
            else:
                mensaje = f"Migradas {migradas} publicaciones de proyecto {proyecto_origen_id_int} a {proyecto_destino_id_int}."

    return render_template(
        "migrar_publicacion.html",
        proyectos=proyectos,
        publicaciones=publicaciones,
        proyecto_origen_id=proyecto_origen_id,
        proyecto_destino_id=proyecto_destino_id,
        mensaje=mensaje,
    )
