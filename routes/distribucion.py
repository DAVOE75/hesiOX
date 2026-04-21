from flask import Blueprint, render_template

distribucion_bp = Blueprint('distribucion', __name__)

@distribucion_bp.route('/distribucion')
def distribucion():
    return render_template('distribucion.html')
