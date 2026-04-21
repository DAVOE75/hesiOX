"""
Sistema de Rate Limiting para hesiOX
Previene abuso de endpoints sensibles
"""
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask import request, current_app
import os


# =========================================================
# CONFIGURACIÓN DE RATE LIMITER
# =========================================================

def get_limiter_key():
    """
    Función personalizada para obtener la clave de rate limiting
    Usa IP del cliente como identificador
    """
    # Obtener IP real considerando proxies
    if request.headers.get('X-Forwarded-For'):
        # Si hay proxy, tomar la primera IP
        ip = request.headers.get('X-Forwarded-For').split(',')[0].strip()
    else:
        ip = request.remote_addr or '127.0.0.1'
    
    return ip


# Inicializar limiter
limiter = Limiter(
    key_func=get_limiter_key,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",  # Usar Redis en producción: "redis://localhost:6379"
    strategy="fixed-window",
    headers_enabled=True,  # Añadir headers X-RateLimit-*
)


# =========================================================
# LÍMITES PERSONALIZADOS POR ENDPOINT
# =========================================================

# Límites para autenticación
AUTH_LIMITS = {
    'login': "20 per minute",  # Aumentado de 5 a 20 para desarrollo
    'registro': "3 per hour",
    'password_reset': "3 per hour",
    'password_change': "5 per hour",
}

# Límites para búsqueda
SEARCH_LIMITS = {
    'busqueda_simple': "30 per minute",
    'busqueda_semantica': "20 per minute",
    'busqueda_avanzada': "20 per minute",
}

# Límites para exportación
EXPORT_LIMITS = {
    'export_csv': "10 per hour",
    'export_pdf': "10 per hour",
    'export_bibtex': "10 per hour",
    'export_json': "10 per hour",
}

# Límites para API
API_LIMITS = {
    'api_general': "100 per hour",
    'api_bulk': "10 per hour",
}

# Límites para operaciones pesadas
HEAVY_LIMITS = {
    'analisis_nlp': "10 per hour",
    'generar_red': "10 per hour",
    'generar_mapa': "20 per hour",
    'ocr_processing': "5 per hour",
}


# =========================================================
# FUNCIONES DE UTILIDAD
# =========================================================

def get_rate_limit_message(limit_type):
    """
    Genera mensaje personalizado según el tipo de límite
    
    Args:
        limit_type: Tipo de límite (login, export, etc.)
    
    Returns:
        str: Mensaje de error personalizado
    """
    messages = {
        'login': 'Demasiados intentos de login. Por favor, espera un momento.',
        'registro': 'Límite de registros alcanzado. Intenta más tarde.',
        'export': 'Límite de exportaciones alcanzado. Intenta más tarde.',
        'search': 'Demasiadas búsquedas. Por favor, espera un momento.',
        'api': 'Límite de API alcanzado. Intenta más tarde.',
        'heavy': 'Operación pesada en progreso. Espera antes de intentar de nuevo.',
    }
    
    return messages.get(limit_type, 'Límite de tasa alcanzado. Intenta más tarde.')


def is_rate_limit_exempt(user):
    """
    Verifica si un usuario está exento de rate limiting
    
    Args:
        user: Usuario actual
    
    Returns:
        bool: True si está exento
    """
    # Admins están exentos
    if user and hasattr(user, 'rol') and user.rol == 'admin':
        return True
    
    return False


# =========================================================
# HANDLER DE ERRORES DE RATE LIMITING
# =========================================================

def rate_limit_error_handler(e):
    """
    Handler personalizado para errores de rate limiting
    
    Args:
        e: Excepción de rate limiting
    
    Returns:
        tuple: (mensaje, código HTTP)
    """
    from flask import jsonify, render_template, request
    from security_logger import log_rate_limit_exceeded
    
    # Registrar en log
    ip = get_limiter_key()
    endpoint = request.endpoint or 'unknown'
    log_rate_limit_exceeded(ip, endpoint, str(e.description))
    
    # Si es petición AJAX/API, devolver JSON
    if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            'error': 'Rate limit exceeded',
            'message': 'Demasiadas peticiones. Por favor, espera un momento.',
            'retry_after': e.description
        }), 429
    
    # Si es petición normal, renderizar template
    return render_template(
        'errors/429.html',
        message='Demasiadas peticiones. Por favor, espera un momento.',
        retry_after=e.description
    ), 429


# =========================================================
# DECORADORES PERSONALIZADOS
# =========================================================

def limit_by_user(limit_string):
    """
    Decorador para limitar por usuario autenticado en lugar de IP
    
    Uso:
        @app.route('/ruta')
        @login_required
        @limit_by_user("10 per hour")
        def mi_ruta():
            pass
    """
    def decorator(f):
        from functools import wraps
        from flask_login import current_user
        
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Si el usuario está autenticado, usar su ID
            if current_user.is_authenticated:
                key = f"user_{current_user.id}"
            else:
                key = get_limiter_key()
            
            # Aplicar límite
            limiter.limit(limit_string, key_func=lambda: key)(f)(*args, **kwargs)
            
            return f(*args, **kwargs)
        
        return decorated_function
    
    return decorator


# =========================================================
# CONFIGURACIÓN DE WHITELIST
# =========================================================

# IPs exentas de rate limiting (localhost, IPs internas, etc.)
RATE_LIMIT_WHITELIST = [
    '127.0.0.1',
    'localhost',
    '::1',
]


def is_ip_whitelisted(ip):
    """
    Verifica si una IP está en la whitelist
    
    Args:
        ip: Dirección IP
    
    Returns:
        bool: True si está en whitelist
    """
    return ip in RATE_LIMIT_WHITELIST
