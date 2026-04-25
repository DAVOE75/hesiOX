from flask import Blueprint, request, jsonify, flash, redirect, url_for, render_template
from extensions import db
from models import MensajeContacto
from datetime import datetime
import os

contacto_bp = Blueprint('contacto', __name__)

@contacto_bp.route("/contacto/enviar", methods=["POST"])
def enviar():
    """Maneja el envío del formulario de contacto con protección contra bots."""
    
    # 1. Protección Honeypot
    # Si el campo oculto 'website' tiene contenido, es un bot
    if request.form.get("website"):
        return jsonify({"success": False, "message": "Bot detectado."}), 400
    
    # 2. Validación de Desafío (Simple Math)
    desafio_ans = request.form.get("desafio_ans")
    desafio_val = request.form.get("desafio_val") # El valor esperado oculto o en sesión
    
    # Por simplicidad en este paso, usaremos un campo estático o validaremos que sea numérico
    # En una implementación más avanzada esto vendría de la sesión
    if not desafio_ans or desafio_ans.strip() != "5": # Esperamos 2+3=5
        return jsonify({"success": False, "message": "Respuesta de seguridad incorrecta."}), 400

    # 3. Obtención de datos
    nombre = request.form.get("nombre", "").strip()
    email = request.form.get("email", "").strip()
    asunto = request.form.get("asunto", "").strip()
    contenido = request.form.get("contenido", "").strip()
    
    if not all([nombre, email, asunto, contenido]):
        return jsonify({"success": False, "message": "Todos los campos son obligatorios."}), 400
    
    # 4. Guardar en base de datos
    try:
        nuevo_mensaje = MensajeContacto(
            nombre=nombre,
            email=email,
            asunto=asunto,
            contenido=contenido,
            ip_address=request.remote_addr
        )
        db.session.add(nuevo_mensaje)
        db.session.commit()
        
        # Aquí se podría añadir la lógica para enviar el email real
        # send_contact_email(nuevo_mensaje)
        
        return jsonify({
            "success": True, 
            "message": "¡Gracias! Tu mensaje ha sido enviado correctamente. Nos pondremos en contacto contigo pronto."
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": f"Error al enviar el mensaje: {str(e)}"}), 500

@contacto_bp.route("/admin/mensajes")
def listar_mensajes():
    """Vista opcional para que el admin vea los mensajes (requiere login de admin)"""
    # Aquí iría la lógica de admin_required
    return "Panel de mensajes (en desarrollo)"
