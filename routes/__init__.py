"""
Módulo de rutas para hesiOX
Organiza las rutas en blueprints por funcionalidad
"""

from flask import Blueprint

# Importar todos los blueprints

from .auth import auth_bp
from .proyectos import proyectos_bp
from .articulos import articulos_bp
from .hemerotecas import hemerotecas_bp
from .copiar_hemeroteca import copiar_hemeroteca
from .analisis_avanzado import analisis_bp
from .distribucion import distribucion_bp
from .maintenance import maintenance_bp
from .analisis_espacial import analisis_espacial_bp
from .capas import capas_bp
from .mapas_historicos import mapas_historicos_bp
from .simulacion import simulacion_bp
from .pasajeros import pasajeros_bp
from .barco import barco_bp
from .blog import blog_bp
from .contacto import contacto_bp
from .metadata_api import metadata_api



from .ocr import ocr_bp

from .spacy_api_test import spacy_bp
from .gemini_api import gemini_bp
from .noticias import noticias_bp
from .noticias_api import noticias_api_bp
from .visualizaciones import visualizaciones_bp
from .quality import quality_bp

# Lista de blueprints para registro fácil
all_blueprints = [
    auth_bp,
    proyectos_bp,
    articulos_bp,
    noticias_bp,
    hemerotecas_bp,
    analisis_bp,
    maintenance_bp,
    ocr_bp,
    spacy_bp,
    gemini_bp,
    noticias_api_bp,
    visualizaciones_bp,
    quality_bp,
    distribucion_bp,
    analisis_espacial_bp,
    capas_bp,
    mapas_historicos_bp,
    simulacion_bp,
    pasajeros_bp,
    barco_bp,
    blog_bp,
    contacto_bp,
    metadata_api
]

