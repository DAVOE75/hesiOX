"""
Sistema de logging de seguridad para hesiOX
Registra eventos de seguridad para auditoría y monitoreo
"""
import logging
import os
from datetime import datetime
from functools import wraps
from flask import request


# =========================================================
# CONFIGURACIÓN DE LOGGERS
# =========================================================

# Crear directorio de logs si no existe
LOGS_DIR = os.path.join(os.path.dirname(__file__), 'logs')
os.makedirs(LOGS_DIR, exist_ok=True)

# Configurar logger de seguridad
security_logger = logging.getLogger('security')
security_logger.setLevel(logging.INFO)

# Handler para archivo de seguridad
security_handler = logging.FileHandler(
    os.path.join(LOGS_DIR, 'security.log'),
    encoding='utf-8'
)
security_handler.setLevel(logging.INFO)

# Formato de log
security_formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - [%(ip)s] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
security_handler.setFormatter(security_formatter)
security_logger.addHandler(security_handler)

# Configurar logger de aplicación
app_logger = logging.getLogger('app')
app_logger.setLevel(logging.INFO)

# Handler para archivo de aplicación
app_handler = logging.FileHandler(
    os.path.join(LOGS_DIR, 'app.log'),
    encoding='utf-8'
)
app_handler.setLevel(logging.INFO)

app_formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
app_handler.setFormatter(app_formatter)
app_logger.addHandler(app_handler)


# =========================================================
# FUNCIONES DE LOGGING DE SEGURIDAD
# =========================================================

def log_login_attempt(email, success, ip_address, user_agent=None):
    """
    Registra intentos de login
    
    Args:
        email: Email del usuario
        success: True si login exitoso, False si falló
        ip_address: IP del cliente
        user_agent: User agent del navegador
    """
    extra = {'ip': ip_address}
    
    if success:
        security_logger.info(
            f"Login exitoso: {email} | User-Agent: {user_agent}",
            extra=extra
        )
    else:
        security_logger.warning(
            f"Login fallido: {email} | User-Agent: {user_agent}",
            extra=extra
        )


def log_logout(email, ip_address):
    """
    Registra cierre de sesión
    
    Args:
        email: Email del usuario
        ip_address: IP del cliente
    """
    extra = {'ip': ip_address}
    security_logger.info(
        f"Logout: {email}",
        extra=extra
    )


def log_registration(email, success, ip_address, error=None):
    """
    Registra intentos de registro
    
    Args:
        email: Email del nuevo usuario
        success: True si registro exitoso, False si falló
        ip_address: IP del cliente
        error: Mensaje de error si falló
    """
    extra = {'ip': ip_address}
    
    if success:
        security_logger.info(
            f"Registro exitoso: {email}",
            extra=extra
        )
    else:
        security_logger.warning(
            f"Registro fallido: {email} | Error: {error}",
            extra=extra
        )


def log_csrf_failure(ip_address, endpoint, user_email=None):
    """
    Registra fallos de validación CSRF
    
    Args:
        ip_address: IP del cliente
        endpoint: Endpoint donde falló CSRF
        user_email: Email del usuario si está autenticado
    """
    extra = {'ip': ip_address}
    user_info = f"Usuario: {user_email}" if user_email else "Usuario no autenticado"
    
    security_logger.warning(
        f"CSRF fallido en {endpoint} | {user_info}",
        extra=extra
    )


def log_rate_limit_exceeded(ip_address, endpoint, limit):
    """
    Registra excesos de rate limiting
    
    Args:
        ip_address: IP del cliente
        endpoint: Endpoint donde se excedió el límite
        limit: Límite que se excedió
    """
    extra = {'ip': ip_address}
    
    security_logger.warning(
        f"Rate limit excedido en {endpoint} | Límite: {limit}",
        extra=extra
    )


def log_unauthorized_access(ip_address, endpoint, user_email=None):
    """
    Registra intentos de acceso no autorizado
    
    Args:
        ip_address: IP del cliente
        endpoint: Endpoint al que intentó acceder
        user_email: Email del usuario si está autenticado
    """
    extra = {'ip': ip_address}
    user_info = f"Usuario: {user_email}" if user_email else "Usuario no autenticado"
    
    security_logger.warning(
        f"Acceso no autorizado a {endpoint} | {user_info}",
        extra=extra
    )


def log_data_export(user_email, export_type, ip_address, num_records=None):
    """
    Registra exportaciones de datos
    
    Args:
        user_email: Email del usuario
        export_type: Tipo de exportación (CSV, PDF, etc.)
        ip_address: IP del cliente
        num_records: Número de registros exportados
    """
    extra = {'ip': ip_address}
    records_info = f"| {num_records} registros" if num_records else ""
    
    security_logger.info(
        f"Exportación {export_type}: {user_email} {records_info}",
        extra=extra
    )


def log_data_deletion(user_email, entity_type, entity_id, ip_address):
    """
    Registra eliminación de datos
    
    Args:
        user_email: Email del usuario
        entity_type: Tipo de entidad eliminada (artículo, proyecto, etc.)
        entity_id: ID de la entidad
        ip_address: IP del cliente
    """
    extra = {'ip': ip_address}
    
    security_logger.warning(
        f"Eliminación de {entity_type} (ID: {entity_id}): {user_email}",
        extra=extra
    )


def log_password_change(user_email, success, ip_address):
    """
    Registra cambios de contraseña
    
    Args:
        user_email: Email del usuario
        success: True si cambio exitoso, False si falló
        ip_address: IP del cliente
    """
    extra = {'ip': ip_address}
    
    if success:
        security_logger.info(
            f"Cambio de contraseña exitoso: {user_email}",
            extra=extra
        )
    else:
        security_logger.warning(
            f"Cambio de contraseña fallido: {user_email}",
            extra=extra
        )


# =========================================================
# FUNCIONES DE LOGGING DE APLICACIÓN
# =========================================================

def log_error(error_message, exception=None, context=None):
    """
    Registra errores de aplicación
    
    Args:
        error_message: Mensaje de error
        exception: Excepción si existe
        context: Contexto adicional
    """
    if exception:
        app_logger.error(
            f"{error_message} | Exception: {str(exception)} | Context: {context}"
        )
    else:
        app_logger.error(f"{error_message} | Context: {context}")


def log_info(message, context=None):
    """
    Registra información general
    
    Args:
        message: Mensaje informativo
        context: Contexto adicional
    """
    if context:
        app_logger.info(f"{message} | Context: {context}")
    else:
        app_logger.info(message)


def log_warning(message, context=None):
    """
    Registra advertencias
    
    Args:
        message: Mensaje de advertencia
        context: Contexto adicional
    """
    if context:
        app_logger.warning(f"{message} | Context: {context}")
    else:
        app_logger.warning(message)


# =========================================================
# DECORADOR PARA LOGGING AUTOMÁTICO
# =========================================================

def log_route_access(f):
    """
    Decorador para registrar accesos a rutas
    
    Uso:
        @app.route('/ruta')
        @log_route_access
        def mi_ruta():
            pass
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        ip = request.remote_addr
        endpoint = request.endpoint
        method = request.method
        
        app_logger.info(
            f"Acceso a {endpoint} | Método: {method} | IP: {ip}"
        )
        
        return f(*args, **kwargs)
    
    return decorated_function
