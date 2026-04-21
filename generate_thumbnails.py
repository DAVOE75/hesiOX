#!/usr/bin/env python3
"""
Script para generar miniaturas de mapas históricos existentes.
Ejecutar con: python generate_thumbnails.py
"""

import os
import sys
from PIL import Image

# Asegurar que estamos en el directorio correcto
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)

# Importar app context
from app import app, db
from models import MapaHistorico

def generate_thumbnail(image_path, thumbnail_size=(300, 300), quality=85):
    """
    Genera una miniatura optimizada de una imagen.
    """
    try:
        # Construir nombre del archivo thumbnail
        base_path, ext = os.path.splitext(image_path)
        thumb_path = f"{base_path}_thumb.jpg"
        
        # Si ya existe, saltar
        if os.path.exists(thumb_path):
            print(f"  ✓ Thumbnail ya existe: {os.path.basename(thumb_path)}")
            return thumb_path
        
        # Abrir y procesar imagen
        with Image.open(image_path) as img:
            # Convertir a RGB si es necesario
            if img.mode not in ('RGB', 'L'):
                img = img.convert('RGB')
            
            # Crear thumbnail manteniendo aspect ratio
            img.thumbnail(thumbnail_size, Image.Resampling.LANCZOS)
            
            # Guardar con compresión optimizada
            img.save(thumb_path, 'JPEG', quality=quality, optimize=True)
        
        print(f"  ✓ Generado: {os.path.basename(thumb_path)}")
        return thumb_path
        
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return None


def main():
    with app.app_context():
        mapas = MapaHistorico.query.all()
        
        if not mapas:
            print("No hay mapas históricos en la base de datos.")
            return
        
        print(f"\n🗺️  Procesando {len(mapas)} mapas históricos...\n")
        
        generated = 0
        skipped = 0
        errors = 0
        
        for mapa in mapas:
            print(f"[{mapa.id}] {mapa.nombre} ({mapa.filename})")
            
            # Construir ruta completa
            upload_dir = os.path.join(
                app.static_folder, 
                'uploads', 
                'mapas_historicos', 
                str(mapa.proyecto_id)
            )
            image_path = os.path.join(upload_dir, mapa.filename)
            
            if not os.path.exists(image_path):
                print(f"  ⚠️  Archivo no encontrado: {image_path}")
                errors += 1
                continue
            
            # Verificar si ya existe thumbnail
            thumb_path = f"{os.path.splitext(image_path)[0]}_thumb.jpg"
            if os.path.exists(thumb_path):
                skipped += 1
                print(f"  → Thumbnail ya existe, saltando...")
                continue
            
            # Generar thumbnail
            result = generate_thumbnail(image_path)
            if result:
                generated += 1
            else:
                errors += 1
        
        print(f"\n" + "="*60)
        print(f"✅ Generados: {generated}")
        print(f"⏭️  Saltados: {skipped}")
        print(f"❌ Errores: {errors}")
        print("="*60 + "\n")


if __name__ == '__main__':
    main()
