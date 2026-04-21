def get_proyecto_activo():
    """
    Función auxiliar para obtener el proyecto activo de la sesión
    """
    from routes.proyectos import get_proyecto_activo as get_proyecto
    return get_proyecto()
