from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from extensions import db
from models import Hemeroteca, Publicacion, Proyecto
from .hemerotecas import hemerotecas_bp, get_proyecto_activo

@hemerotecas_bp.route("/hemeroteca/copiar/<int:id>", methods=["GET", "POST"])
@login_required
def copiar_hemeroteca(id):
    """Duplicar hemeroteca en otro proyecto, con opción de copiar publicaciones"""
    hemeroteca = Hemeroteca.query.get_or_404(id)
    proyecto_actual = get_proyecto_activo()
    if hemeroteca.proyecto_id != proyecto_actual.id:
        flash("❌ No tienes permiso para copiar esta hemeroteca", "danger")
        return redirect(url_for("hemerotecas.hemerotecas"))

    # Proyectos destino posibles
    proyectos = Proyecto.query.filter(
        Proyecto.user_id == current_user.id,
        Proyecto.id != proyecto_actual.id
    ).all()

    publicaciones = Publicacion.query.filter_by(hemeroteca_id=hemeroteca.id).all()
    if request.method == "POST":
        proyecto_id = request.form.get("proyecto_id")
        publicaciones_seleccionadas = request.form.getlist("publicaciones")
        if not proyecto_id:
            flash("⚠️ Debes seleccionar un proyecto destino", "warning")
            return redirect(url_for("hemerotecas.copiar_hemeroteca", id=id))
        proyecto_destino = Proyecto.query.get_or_404(proyecto_id)
        if proyecto_destino.user_id != current_user.id:
            flash("❌ No tienes permiso para copiar a ese proyecto", "danger")
            return redirect(url_for("hemerotecas.hemerotecas"))
        # Crear copia de la hemeroteca
        nueva = Hemeroteca(
            proyecto_id=proyecto_destino.id,
            nombre=hemeroteca.nombre,
            institucion=hemeroteca.institucion,
            pais=hemeroteca.pais,
            provincia=hemeroteca.provincia,
            ciudad=hemeroteca.ciudad,
            resumen_corpus=hemeroteca.resumen_corpus,
            url=hemeroteca.url
        )
        db.session.add(nueva)
        db.session.flush()  # Para obtener nueva.id
        nombres_omitidos = []
        nuevas_publicaciones = []
        if publicaciones_seleccionadas:
            # Obtener nombres ya existentes en el proyecto destino (una sola query)
            nombres_existentes = set(
                nombre for (nombre,) in db.session.query(Publicacion.nombre).filter_by(proyecto_id=proyecto_destino.id).all()
            )
            with db.session.no_autoflush:
                for pub in publicaciones:
                    if str(pub.id_publicacion) not in publicaciones_seleccionadas:
                        continue
                    if pub.nombre in nombres_existentes:
                        nombres_omitidos.append(pub.nombre)
                        continue
                    nueva_pub = Publicacion(
                        proyecto_id=proyecto_destino.id,
                        hemeroteca_id=nueva.id,
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
                    nombres_existentes.add(pub.nombre)
        db.session.commit()
        mensaje = f"✅ Hemeroteca '{nueva.nombre}' copiada a '{proyecto_destino.nombre}'"
        if publicaciones_seleccionadas:
            mensaje += " con publicaciones seleccionadas."
            if nombres_omitidos:
                mensaje += f"<br>⚠️ No se copiaron por duplicidad: {', '.join(nombres_omitidos)}."
        flash(mensaje, "success")
        return redirect(url_for("hemerotecas.hemerotecas"))
    return render_template("copiar_hemeroteca.html", hemeroteca=hemeroteca, proyectos=proyectos, publicaciones=publicaciones)
