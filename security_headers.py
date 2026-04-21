"""
Configuración de Headers de Seguridad HTTP para hesiOX
Implementa CSP, HSTS, y otros headers de seguridad
"""
from flask import Flask


def configure_security_headers(app: Flask):
    """
    Configura headers de seguridad HTTP para proteger la aplicación
    
    Headers implementados:
    - Content-Security-Policy (CSP)
    - Strict-Transport-Security (HSTS)
    - X-Frame-Options
    - X-Content-Type-Options
    - X-XSS-Protection
    - Referrer-Policy
    """
    
    @app.after_request
    def set_security_headers(response):
        """Añade headers de seguridad a todas las respuestas"""
        
        # Content Security Policy
        # NOTA: Permitimos 'unsafe-inline' y 'unsafe-eval' para TinyMCE, Chart.js, D3.js, Vis-network
        # Añadidos CDNs necesarios para iconografía y grafos
        csp_policy = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' "
            "https://cdn.tiny.cloud https://cdnjs.cloudflare.com https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' "
            "https://fonts.googleapis.com https://cdnjs.cloudflare.com https://cdn.jsdelivr.net; "
            "img-src 'self' data: https: blob:; "
            "font-src 'self' data: https://fonts.gstatic.com https://cdnjs.cloudflare.com https://cdn.jsdelivr.net; "
            "connect-src 'self'; "
            "frame-src 'self'; "
            "object-src 'none'; "
            "base-uri 'self'; "
            "form-action 'self'; "
        )
        response.headers['Content-Security-Policy'] = csp_policy
        
        # Strict Transport Security (HSTS)
        # Solo activar en producción con HTTPS
        if not app.debug:
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        
        # Prevenir clickjacking
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        
        # Prevenir MIME sniffing
        response.headers['X-Content-Type-Options'] = 'nosniff'
        
        # XSS Protection (legacy, pero útil para navegadores antiguos)
        response.headers['X-XSS-Protection'] = '1; mode=block'
        
        # Referrer Policy
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # Permissions Policy (antes Feature-Policy)
        response.headers['Permissions-Policy'] = (
            'geolocation=(), '
            'microphone=(), '
            'camera=(), '
            'payment=(), '
            'usb=()'
        )
        
        return response
    
    app.logger.info("✅ Headers de seguridad configurados")


def configure_cors(app: Flask, allowed_origins=None):
    """
    Configura CORS si es necesario (para API)
    
    Args:
        app: Instancia de Flask
        allowed_origins: Lista de orígenes permitidos (None = solo mismo origen)
    """
    if allowed_origins is None:
        allowed_origins = []
    
    @app.after_request
    def set_cors_headers(response):
        """Añade headers CORS si es necesario"""
        origin = request.headers.get('Origin')
        
        if origin in allowed_origins:
            response.headers['Access-Control-Allow-Origin'] = origin
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-CSRF-Token'
            response.headers['Access-Control-Allow-Credentials'] = 'true'
        
        return response
