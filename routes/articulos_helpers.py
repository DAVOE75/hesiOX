"""
Rutas complejas de artículos: crear y editar
Separadas para mejor organización del código
"""
import os
from datetime import datetime
from flask import current_app, request, redirect, url_for, flash, render_template, abort
from flask_login import login_required
from werkzeug.utils import secure_filename

from extensions import db
from models import Prensa, Publicacion, Hemeroteca, ImagenPrensa
from utils import validar_fecha_ddmmyyyy, normalizar_next, separar_autor


def allowed_file(filename):
    """Verificar si la extensión del archivo es permitida"""
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def get_form_data_for_templates():
    """Obtener datos comunes para formularios de artículos"""
    idiomas = ["es", "it", "fr", "en", "pt", "ct"]
    tipos_autor = ["anónimo", "firmado", "corresponsal"]
    
    publicaciones = [
        p.nombre for p in Publicacion.query.order_by(Publicacion.nombre.asc()).all()
    ]
    
    ciudades = sorted(
        {
            *(
                p.ciudad
                for p in Publicacion.query.filter(Publicacion.ciudad.isnot(None))
            ),
            *(r.ciudad for r in Prensa.query.filter(Prensa.ciudad.isnot(None))),
        }
    )
    
    # Obtener todos los temas, separarlos por comas y limpiar espacios
    raw_temas = db.session.query(Prensa.temas).filter(Prensa.temas.isnot(None)).all()
    temas_set = set()
    for (t_str,) in raw_temas:
        if t_str:
            for t in t_str.split(','):
                clean_t = t.strip()
                if clean_t:
                    temas_set.add(clean_t)
    temas = sorted(temas_set)
    
    licencias = sorted(
        {
            *(
                p.licencia
                for p in Publicacion.query.filter(Publicacion.licencia.isnot(None))
            ),
            *(r.licencia for r in Prensa.query.filter(Prensa.licencia.isnot(None))),
        }
        | {"CC BY 4.0"}
    )
    
    formatos = sorted(
        {
            *(
                p.formato_fuente
                for p in Publicacion.query.filter(
                    Publicacion.formato_fuente.isnot(None)
                )
            ),
            *(
                r.formato_fuente
                for r in Prensa.query.filter(Prensa.formato_fuente.isnot(None))
            ),
        }
    )
    
    paises = sorted(
        {
            *(
                p.pais_publicacion
                for p in Publicacion.query.filter(
                    Publicacion.pais_publicacion.isnot(None)
                )
            ),
            *(
                r.pais_publicacion
                for r in Prensa.query.filter(Prensa.pais_publicacion.isnot(None))
            ),
        }
    )
    
    return {
        "idiomas": idiomas,
        "tipos_autor": tipos_autor,
        "publicaciones": publicaciones,
        "ciudades": ciudades,
        "temas": temas,
        "licencias": licencias,
        "formatos": formatos,
        "paises": paises,
    }


def crear_articulo_view(get_proyecto_activo_func):
    pub = None  # Siempre definir pub por defecto
    """Vista para crear nuevo artículo"""
    # Verificar proyecto activo
    proyecto = get_proyecto_activo_func()
    if not proyecto:
        flash("⚠️ Debes seleccionar un proyecto antes de crear artículos", "warning")
        return redirect(url_for("proyectos.listar"))


    precargados = {key: request.args.get(key) for key in request.args}
    form_data = get_form_data_for_templates()
    # Definir hemerotecas por defecto para evitar UnboundLocalError
    if proyecto:
        hemerotecas = Hemeroteca.query.filter_by(proyecto_id=proyecto.id).order_by(Hemeroteca.nombre).all()
    else:
        hemerotecas = Hemeroteca.query.order_by(Hemeroteca.nombre).all()

    if request.method == "POST":
        # Validación de fechas
        fecha_original = (request.form.get("fecha_original") or "").strip()
        fecha_consulta = (request.form.get("fecha_consulta") or "").strip()

        # Validar fecha_original
        valida, error_msg = validar_fecha_ddmmyyyy(fecha_original)
        if not valida:
            flash(f"⚠️ Fecha Original inválida: {error_msg}", "danger")
            form_data = get_form_data_for_templates()
            precargados_form = {k: (request.form.get(k) or "") for k in request.form.keys()}
            
            # Obtener hemerotecas
            if proyecto:
                hemerotecas = Hemeroteca.query.filter_by(proyecto_id=proyecto.id).order_by(Hemeroteca.nombre).all()
            else:
                hemerotecas = Hemeroteca.query.order_by(Hemeroteca.nombre).all()
            
            return render_template(
                "new.html",
                **form_data,
                hemerotecas=hemerotecas,
                next_url=normalizar_next(request.args.get("next")),
                precargados=precargados_form,
            )

        # Validar fecha_consulta
        valida, error_msg = validar_fecha_ddmmyyyy(fecha_consulta)
        if not valida:
            flash(f"⚠️ Fecha Consulta inválida: {error_msg}", "danger")
            form_data = get_form_data_for_templates()
            precargados_form = {k: (request.form.get(k) or "") for k in request.form.keys()}
            
            if proyecto:
                hemerotecas = Hemeroteca.query.filter_by(proyecto_id=proyecto.id).order_by(Hemeroteca.nombre).all()
            else:
                hemerotecas = Hemeroteca.query.order_by(Hemeroteca.nombre).all()
            
            return render_template(
                "new.html",
                **form_data,
                hemerotecas=hemerotecas,
                next_url=normalizar_next(request.args.get("next")),
                precargados=precargados_form,
            )

        # 1. GESTIÓN DE AUTOR
        nombre = (request.form.get("nombre_autor") or "").strip()
        apellido = (request.form.get("apellido_autor") or "").strip()
        es_anonimo = "anonimo" in request.form

        if es_anonimo:
            autor_final = None
        elif apellido or nombre:
            if apellido and nombre:
                autor_final = f"{apellido}, {nombre}"
            elif apellido:
                autor_final = apellido
            else:
                autor_final = nombre
        else:
            autor_final = None

        # 2. GESTIÓN DE PUBLICACIÓN (MEDIO)
        nombre_pub = (request.form.get("publicacion") or "").strip()
        pub = None

        if nombre_pub:
            # Buscar publicación existente o crear nueva
            pub = Publicacion.query.filter_by(
                nombre=nombre_pub, proyecto_id=proyecto.id
            ).first()
            if not pub:
                pub = Publicacion(nombre=nombre_pub, proyecto_id=proyecto.id)
                db.session.add(pub)
                db.session.flush()  # Obtener ID sin hacer commit completo

            # Actualizar campos de la publicación solo si hay datos
            campos_pub = {
                "descripcion": request.form.get("descripcion_publicacion"),
                "tipo_recurso": request.form.get("tipo_recurso"),
                "ciudad": request.form.get("ciudad"),
                "idioma": request.form.get("idioma"),
                "licencia": request.form.get("licencia") or "CC BY 4.0",
                "formato_fuente": request.form.get("formato_fuente"),
                "pais_publicacion": request.form.get("pais_publicacion"),
            }

            for campo, valor in campos_pub.items():
                if valor and (getattr(pub, campo) is None or getattr(pub, campo) == ""):
                    setattr(pub, campo, valor)

        # Heredar frecuencia de la publicación si existe y si edición no es mañana/tarde/noche
        edicion_val = request.form.get("edicion")
        frecuencia_pub = pub.frecuencia if pub else None
        if edicion_val in [None, "", "diaria", "semanal", "quincenal", "mensual", "bimensual", "semestral", "anual"] and frecuencia_pub:
            edicion_val = frecuencia_pub

        nuevo = Prensa(
            proyecto_id=proyecto.id,  # ASIGNAR PROYECTO ACTIVO
            titulo=request.form.get("titulo"),
            publicacion=nombre_pub,
            id_publicacion=pub.id_publicacion if pub else None,
            ciudad=request.form.get("ciudad"),
            fecha_original=fecha_original,
            anio=request.form.get("anio") or None,
            numero=request.form.get("numero"),
            edicion=edicion_val,
            pagina_inicio=request.form.get("pagina_inicio"),
            pagina_fin=request.form.get("pagina_fin"),
            paginas=request.form.get("paginas"),
            url=request.form.get("url"),
            fecha_consulta=fecha_consulta,
            autor=autor_final,
            idioma=request.form.get("idioma"),
            tipo_autor=request.form.get("tipo_autor"),
            fuente_condiciones=request.form.get("fuente_condiciones"),
            temas=request.form.get("temas"),
            notas=request.form.get("notas"),
            contenido=request.form.get("contenido"),
            texto_original=request.form.get("texto_original"),
            licencia=request.form.get("licencia") or "CC BY 4.0",
            incluido=(request.form.get("incluido") == "si"),
            es_referencia=(request.form.get("es_referencia") == "si"),
            numero_referencia=int(request.form.get("numero_referencia"))
            if request.form.get("numero_referencia")
            and request.form.get("numero_referencia").strip().isdigit()
            else None,
            tipo_recurso=request.form.get("tipo_recurso"),
            editor=request.form.get("editor"),
            lugar_publicacion=request.form.get("lugar_publicacion"),
            issn=request.form.get("issn"),
            volumen=request.form.get("volumen"),
            seccion=request.form.get("seccion"),
            palabras_clave=request.form.get("palabras_clave"),
            resumen=request.form.get("resumen"),
            editorial=request.form.get("editorial"),
            isbn=request.form.get("isbn"),
            doi=request.form.get("doi"),
            pais_publicacion=request.form.get("pais_publicacion"),
            formato_fuente=request.form.get("formato_fuente"),
            referencias_relacionadas=request.form.get("referencias_relacionadas"),
            archivo_pdf=request.form.get("archivo_pdf"),
            imagen_scan=None,  # Este campo queda obsoleto
            nombre_investigador=request.form.get("nombre_investigador"),
            universidad_investigador=request.form.get("universidad_investigador"),
        )
        db.session.flush()

        # Heredar frecuencia de la publicación si existe y si edición no es mañana/tarde/noche
        edicion_val = request.form.get("edicion")
        frecuencia_pub = pub.frecuencia if pub else None
        if edicion_val in [None, "", "diaria", "semanal", "quincenal", "mensual", "bimensual", "semestral", "anual"] and frecuencia_pub:
            edicion_val = frecuencia_pub

        campo_map = [
            "titulo", "fecha_original", "numero", "pagina_inicio", "pagina_fin",
            "paginas", "url", "fecha_consulta", "idioma", "licencia",
            "notas", "contenido", "texto_original", "ciudad",
            "pais_publicacion", "fuente", "formato_fuente", "tipo_recurso",
        ]
        for campo in campo_map:
            valor = request.form.get(campo)
            if valor is not None:
                setattr(nuevo, campo, valor)
        
        # Procesar temas (puede venir como lista de select multiple o string)
        temas_list = request.form.getlist("temas")
        if temas_list:
            # Si viene de select multiple, son varios items. Si es text input, puede ser uno con comas.
            # Normalizamos a lista plana
            final_temas = []
            for t in temas_list:
                if "," in t:
                    final_temas.extend([x.strip() for x in t.split(",") if x.strip()])
                else:
                    if t.strip():
                        final_temas.append(t.strip())
            nuevo.temas = ", ".join(final_temas)
        else:
            nuevo.temas = request.form.get("temas")

        # Asignar edición después de heredar frecuencia si corresponde
        nuevo.edicion = edicion_val

        # Año (int)
        anio_val = request.form.get("anio")
        if anio_val:
            try:
                anio_int = int(anio_val)
                nuevo.anio = anio_int
            except Exception:
                pass

        db.session.add(nuevo)
        db.session.flush()

        # Gestión de imágenes
        imagenes = request.files.getlist("imagen_scan")
        for imagen in imagenes:
            if imagen and allowed_file(imagen.filename):
                nombre_imagen = secure_filename(
                    f"{nuevo.id}_{datetime.now().timestamp()}_{imagen.filename}"
                )
                imagen.save(os.path.join(current_app.config["UPLOAD_FOLDER"], nombre_imagen))
                nueva_imagen = ImagenPrensa(prensa_id=nuevo.id, filename=nombre_imagen)
                db.session.add(nueva_imagen)

        db.session.commit()
        flash("✅ Noticia guardada correctamente.", "success")
        return redirect(url_for("articulos.listar", publicacion=nombre_pub))

    next_url = normalizar_next(request.args.get("next"))
    return render_template(
        "new.html",
        **form_data,
        hemerotecas=hemerotecas,
        next_url=next_url,
        precargados=precargados,
        publicacion_rel=pub,
    )


def editar_articulo_view(id, get_proyecto_activo_func):
    """Vista para editar artículo existente"""
    ref = db.session.get(Prensa, id)
    if not ref:
        return abort(404)

    form_data = get_form_data_for_templates()

    if request.method == "POST":
        nombre = (request.form.get("nombre_autor") or "").strip()
        apellido = (request.form.get("apellido_autor") or "").strip()
        es_anonimo = "anonimo" in request.form

        # Solo modificar autor si hay cambios explícitos
        if es_anonimo:
            ref.autor = None
        elif apellido or nombre:
            if apellido and nombre:
                ref.autor = f"{apellido}, {nombre}"
            elif apellido:
                ref.autor = apellido
            elif nombre:
                ref.autor = nombre

        nombre_pub = (request.form.get("publicacion") or "").strip()
        pub = None
        if nombre_pub:
            pub = Publicacion.query.filter_by(nombre=nombre_pub).first()
            if not pub:
                pub = Publicacion(nombre=nombre_pub)
                db.session.add(pub)

            campos_pub = {
                "descripcion": request.form.get("descripcion_publicacion"),
                "tipo_recurso": request.form.get("tipo_recurso"),
                "ciudad": request.form.get("ciudad"),
                "idioma": request.form.get("idioma"),
                "licencia": request.form.get("licencia"),
                "formato_fuente": request.form.get("formato_fuente"),
                "pais_publicacion": request.form.get("pais_publicacion"),
                "fuente": request.form.get("fuente"),
            }
            for campo, valor in campos_pub.items():
                if valor is not None:
                    setattr(pub, campo, valor)

            db.session.flush()

            # Heredar frecuencia de la publicación si existe y si edición no es mañana/tarde/noche
            edicion_val = request.form.get("edicion")
            frecuencia_pub = pub.frecuencia if pub else None
            if edicion_val in [None, "", "diaria", "semanal", "quincenal", "mensual", "bimensual", "semestral", "anual"] and frecuencia_pub:
                edicion_val = frecuencia_pub

            campo_map = [
                "titulo", "fecha_original", "numero", "pagina_inicio", "pagina_fin",
                "paginas", "url", "fecha_consulta", "idioma", "licencia",
                "notas", "contenido", "texto_original", "ciudad",
                "pais_publicacion", "fuente", "formato_fuente", "tipo_recurso",
                "descripcion_publicacion", "nombre_investigador", "universidad_investigador"
            ]
            for campo in campo_map:
                valor = request.form.get(campo)
                if valor is not None:
                    setattr(ref, campo, valor)
            
            # Procesar temas (puede venir como lista de select multiple o string)
            temas_list = request.form.getlist("temas")
            if temas_list:
                final_temas = []
                for t in temas_list:
                    if "," in t:
                        final_temas.extend([x.strip() for x in t.split(",") if x.strip()])
                    else:
                        if t.strip():
                            final_temas.append(t.strip())
                ref.temas = ", ".join(final_temas)
            else:
                # Fallback si viene vacío o como string simple
                val_t = request.form.get("temas")
                if val_t is not None:
                    ref.temas = val_t

            # Asignar edición después de heredar frecuencia si corresponde
            ref.edicion = edicion_val

            # Año (int)
            anio_val = request.form.get("anio")
            if anio_val:
                try:
                    ref.anio = int(anio_val)
                except ValueError:
                    ref.anio = None

            # Validación de fechas
            fecha_original = (request.form.get("fecha_original") or "").strip()
            fecha_consulta = (request.form.get("fecha_consulta") or "").strip()

            valida, error_msg = validar_fecha_ddmmyyyy(fecha_original)
            if not valida:
                flash(f"⚠️ Fecha Original inválida: {error_msg}", "danger")
                # Recargar el objeto ref para reflejar cambios en imágenes
                ref = db.session.get(Prensa, id)
                return render_template(
                    "editar.html",
                    ref=ref,
                    **form_data,
                    next_url=normalizar_next(request.args.get("next")),
                    nombre_autor_val=nombre,
                    apellido_autor_val=apellido,
                )

            valida, error_msg = validar_fecha_ddmmyyyy(fecha_consulta)
            if not valida:
                flash(f"⚠️ Fecha Consulta inválida: {error_msg}", "danger")
                ref = db.session.get(Prensa, id)
                return render_template(
                    "editar.html",
                    ref=ref,
                    **form_data,
                    next_url=normalizar_next(request.args.get("next")),
                    nombre_autor_val=nombre,
                    apellido_autor_val=apellido,
                )

        # Incluido (checkbox)
        ref.incluido = (request.form.get("incluido") == "si") or (
            "incluido" in request.form and request.form.get("incluido") is None
        )

        # Es referencia bibliográfica
        ref.es_referencia = (request.form.get("es_referencia") == "si")

        # Número de referencia
        numero_ref_str = request.form.get("numero_referencia", "").strip()
        ref.numero_referencia = (
            int(numero_ref_str) if numero_ref_str and numero_ref_str.isdigit() else None
        )

        # Asociación a publicación
        ref.publicacion = nombre_pub
        ref.id_publicacion = pub.id_publicacion if pub else None

        # Gestión de imágenes
        imagenes = request.files.getlist("imagen_scan")
        for imagen in imagenes:
            if imagen and allowed_file(imagen.filename):
                nombre_imagen = secure_filename(
                    f"{id}_{datetime.now().timestamp()}_{imagen.filename}"
                )
                imagen.save(os.path.join(current_app.config["UPLOAD_FOLDER"], nombre_imagen))
                nueva_imagen = ImagenPrensa(prensa_id=ref.id, filename=nombre_imagen)
                db.session.add(nueva_imagen)

        db.session.commit()
        flash("💾 Cambios guardados correctamente.", "info")

        # Recargar el objeto ref para reflejar cambios en imágenes
        ref = db.session.get(Prensa, id)

        return redirect(url_for("articulos.listar", publicacion=nombre_pub))
    # Si no es POST, mostrar el formulario con los datos actuales
    nombre = ref.autor.split(', ')[1] if ref.autor and ',' in ref.autor else ''
    apellido = ref.autor.split(', ')[0] if ref.autor and ',' in ref.autor else ref.autor or ''
    return render_template(
        "editar.html",
        ref=ref,
        **form_data,
        next_url=normalizar_next(request.args.get("next")),
        nombre_autor_val=nombre,
        apellido_autor_val=apellido,
    )
