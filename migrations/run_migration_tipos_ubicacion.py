#!/usr/bin/env python3
"""
Script de migración: Crear tabla tipo_ubicacion y poblarla
Fecha: 2026-03-05

Uso:
    python3 migrations/run_migration_tipos_ubicacion.py
"""

import sys
import os

# Añadir el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Importar app y db directamente (no existe create_app en este proyecto)
from app import app
from extensions import db
from models import TipoUbicacion

# Definición de tipos predefinidos
TIPOS_PREDEFINIDOS = [
    # Desconocido
    {'codigo': 'unknown', 'nombre': 'Desconocido', 'categoria': 'Otros', 'icono': 'fa-solid fa-question', 'orden': 1},
    
    # Ciudades y Poblaciones
    {'codigo': 'city', 'nombre': 'Ciudad', 'categoria': 'Ciudades y Poblaciones', 'icono': 'fa-solid fa-city', 'orden': 10},
    {'codigo': 'town', 'nombre': 'Pueblo', 'categoria': 'Ciudades y Poblaciones', 'icono': 'fa-solid fa-house-chimney', 'orden': 11},
    {'codigo': 'village', 'nombre': 'Aldea', 'categoria': 'Ciudades y Poblaciones', 'icono': 'fa-solid fa-house', 'orden': 12},
    {'codigo': 'hamlet', 'nombre': 'Caserío', 'categoria': 'Ciudades y Poblaciones', 'icono': 'fa-solid fa-home', 'orden': 13},
    {'codigo': 'suburb', 'nombre': 'Barrio', 'categoria': 'Ciudades y Poblaciones', 'icono': 'fa-solid fa-building', 'orden': 14},
    {'codigo': 'locality', 'nombre': 'Localidad', 'categoria': 'Ciudades y Poblaciones', 'icono': 'fa-solid fa-map-pin', 'orden': 15},
    
    # Vías
    {'codigo': 'road', 'nombre': 'Carretera', 'categoria': 'Vías', 'icono': 'fa-solid fa-road', 'orden': 100},
    {'codigo': 'street', 'nombre': 'Calle', 'categoria': 'Vías', 'icono': 'fa-solid fa-road', 'orden': 101},
    {'codigo': 'highway', 'nombre': 'Autopista', 'categoria': 'Vías', 'icono': 'fa-solid fa-highway', 'orden': 102},
    {'codigo': 'path', 'nombre': 'Sendero', 'categoria': 'Vías', 'icono': 'fa-solid fa-person-hiking', 'orden': 103},
    
    # Edificios
    {'codigo': 'building', 'nombre': 'Edificio', 'categoria': 'Edificios', 'icono': 'fa-solid fa-building', 'orden': 200},
    {'codigo': 'house', 'nombre': 'Casa', 'categoria': 'Edificios', 'icono': 'fa-solid fa-house', 'orden': 201},
    {'codigo': 'church', 'nombre': 'Iglesia', 'categoria': 'Edificios', 'icono': 'fa-solid fa-church', 'orden': 202},
    {'codigo': 'castle', 'nombre': 'Castillo', 'categoria': 'Edificios', 'icono': 'fa-solid fa-chess-rook', 'orden': 206},
    {'codigo': 'hospital', 'nombre': 'Hospital', 'categoria': 'Edificios', 'icono': 'fa-solid fa-hospital', 'orden': 208},
    {'codigo': 'school', 'nombre': 'Escuela', 'categoria': 'Edificios', 'icono': 'fa-solid fa-school', 'orden': 209},
    {'codigo': 'lighthouse', 'nombre': 'Faro', 'categoria': 'Edificios', 'icono': 'fa-solid fa-lighthouse', 'orden': 212},
    
    # Geografía Natural
    {'codigo': 'mountain', 'nombre': 'Montaña', 'categoria': 'Geografía Natural', 'icono': 'fa-solid fa-mountain', 'orden': 300},
    {'codigo': 'peak', 'nombre': 'Pico', 'categoria': 'Geografía Natural', 'icono': 'fa-solid fa-mountain-sun', 'orden': 301},
    {'codigo': 'volcano', 'nombre': 'Volcán', 'categoria': 'Geografía Natural', 'icono': 'fa-solid fa-volcano', 'orden': 302},
    {'codigo': 'hill', 'nombre': 'Colina', 'categoria': 'Geografía Natural', 'icono': 'fa-solid fa-mountain', 'orden': 303},
    {'codigo': 'valley', 'nombre': 'Valle', 'categoria': 'Geografía Natural', 'icono': 'fa-solid fa-mountain', 'orden': 304},
    {'codigo': 'cave', 'nombre': 'Cueva', 'categoria': 'Geografía Natural', 'icono': 'fa-solid fa-dungeon', 'orden': 305},
    {'codigo': 'cape', 'nombre': 'Cabo', 'categoria': 'Geografía Natural', 'icono': 'fa-solid fa-location-arrow', 'orden': 307},
    
    # Hidrografía
    {'codigo': 'river', 'nombre': 'Río', 'categoria': 'Hidrografía', 'icono': 'fa-solid fa-water', 'orden': 400},
    {'codigo': 'lake', 'nombre': 'Lago', 'categoria': 'Hidrografía', 'icono': 'fa-solid fa-water', 'orden': 402},
    {'codigo': 'sea', 'nombre': 'Mar', 'categoria': 'Hidrografía', 'icono': 'fa-solid fa-water', 'orden': 405},
    {'codigo': 'ocean', 'nombre': 'Océano', 'categoria': 'Hidrografía', 'icono': 'fa-solid fa-water', 'orden': 406},
    {'codigo': 'gulf', 'nombre': 'Golfo', 'categoria': 'Hidrografía', 'icono': 'fa-solid fa-water', 'orden': 407},
    {'codigo': 'island', 'nombre': 'Isla', 'categoria': 'Hidrografía', 'icono': 'fa-solid fa-island-tropical', 'orden': 408},
    {'codigo': 'beach', 'nombre': 'Playa', 'categoria': 'Hidrografía', 'icono': 'fa-solid fa-umbrella-beach', 'orden': 409},
    
    # Administrativo
    {'codigo': 'country', 'nombre': 'País', 'categoria': 'Administrativo', 'icono': 'fa-solid fa-flag', 'orden': 500},
    {'codigo': 'state', 'nombre': 'Estado/Provincia', 'categoria': 'Administrativo', 'icono': 'fa-solid fa-landmark', 'orden': 501},
    {'codigo': 'province', 'nombre': 'Provincia', 'categoria': 'Administrativo', 'icono': 'fa-solid fa-landmark', 'orden': 502},
    {'codigo': 'region', 'nombre': 'Región', 'categoria': 'Administrativo', 'icono': 'fa-solid fa-map', 'orden': 503},
    {'codigo': 'administrative', 'nombre': 'División Administrativa', 'categoria': 'Administrativo', 'icono': 'fa-solid fa-sitemap', 'orden': 505},
]


def run_migration():
    """Ejecutar la migración"""
    
    with app.app_context():
        print("🚀 Iniciando migración de tipos de ubicación...")
        
        # Crear la tabla si no existe (SQLAlchemy lo hace automáticamente)
        db.create_all()
        print("✓ Tabla tipo_ubicacion verificada/creada")
        
        # Poblar con tipos predefinidos
        insertados = 0
        existentes = 0
        
        for tipo_data in TIPOS_PREDEFINIDOS:
            # Verificar si ya existe
            existe = TipoUbicacion.query.filter_by(codigo=tipo_data['codigo']).first()
            
            if existe:
                existentes += 1
                print(f"  ⊙ {tipo_data['codigo']}: ya existe")
            else:
                nuevo_tipo = TipoUbicacion(
                    codigo=tipo_data['codigo'],
                    nombre=tipo_data['nombre'],
                    categoria=tipo_data['categoria'],
                    icono=tipo_data.get('icono'),
                    orden=tipo_data['orden']
                )
                db.session.add(nuevo_tipo)
                insertados += 1
                print(f"  + {tipo_data['codigo']}: {tipo_data['nombre']}")
        
        # Guardar cambios
        db.session.commit()
        
        print(f"\n✅ Migración completada:")
        print(f"   • {insertados} tipos insertados")
        print(f"   • {existentes} tipos ya existían")
        print(f"   • Total: {insertados + existentes} tipos disponibles")
        print("\n💡 Ahora puedes gestionar los tipos desde el Gestor de Ubicaciones")


if __name__ == '__main__':
    run_migration()
