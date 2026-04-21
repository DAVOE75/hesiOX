"""
Configuración de sistema de caché para hesiOX
Optimiza queries frecuentes y reduce carga en base de datos
"""
from flask_caching import Cache

# Configuración de caché
cache_config = {
    'CACHE_TYPE': 'SimpleCache',  # En producción: 'RedisCache'
    'CACHE_DEFAULT_TIMEOUT': 300,  # 5 minutos
    'CACHE_KEY_PREFIX': 'hesiox_',
    # Para Redis en producción:
    # 'CACHE_REDIS_URL': 'redis://localhost:6379/0'
}

# Instancia de caché (se inicializa en app.py)
cache = Cache()


def init_cache(app):
    """
    Inicializa el sistema de caché con la aplicación Flask
    
    Args:
        app: Instancia de Flask
    """
    app.config.update(cache_config)
    cache.init_app(app)
    app.logger.info("✅ Sistema de caché inicializado")


def clear_proyecto_cache(proyecto_id):
    """
    Limpia la caché relacionada con un proyecto específico
    
    Args:
        proyecto_id: ID del proyecto
    """
    patterns = [
        f'valores_unicos_*_{proyecto_id}',
        f'proyecto_{proyecto_id}_*',
        f'stats_proyecto_{proyecto_id}',
    ]
    
    for pattern in patterns:
        cache.delete_memoized(pattern)


def cache_key_proyecto(proyecto_id, *args):
    """
    Genera una clave de caché única para un proyecto
    
    Args:
        proyecto_id: ID del proyecto
        *args: Argumentos adicionales para la clave
    
    Returns:
        str: Clave de caché única
    """
    return f"proyecto_{proyecto_id}_{'_'.join(map(str, args))}"


# Decoradores de caché predefinidos

def cache_valores_unicos(timeout=600):
    """
    Decorador para cachear valores únicos de columnas
    Timeout: 10 minutos (se actualizan poco)
    """
    def decorator(f):
        return cache.memoize(timeout=timeout)(f)
    return decorator


def cache_estadisticas(timeout=300):
    """
    Decorador para cachear estadísticas
    Timeout: 5 minutos (se actualizan con frecuencia)
    """
    def decorator(f):
        return cache.memoize(timeout=timeout)(f)
    return decorator


def cache_geocoding(timeout=86400):
    """
    Decorador para cachear resultados de geocodificación
    Timeout: 24 horas (datos geográficos no cambian)
    """
    def decorator(f):
        return cache.memoize(timeout=timeout)(f)
    return decorator
