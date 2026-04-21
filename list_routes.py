#!/usr/bin/env python3
"""Script para listar todas las rutas registradas en la aplicación Flask"""
import sys
sys.path.insert(0, '/opt/hesiox')

from app import app

with app.app_context():
    print("\n=== RUTAS REGISTRADAS ===\n")
    routes = []
    for rule in app.url_map.iter_rules():
        routes.append({
            'endpoint': rule.endpoint,
            'methods': ','.join(sorted(rule.methods -{'OPTIONS', 'HEAD'})),
            'path': str(rule)
        })
    
    # Filtrar por noticias
    noticias_routes = [r for r in routes if 'imagen' in r['endpoint'] or 'imagen' in r['path']]
    
    print("Rutas con 'imagen':")
    for route in sorted(noticias_routes, key=lambda x: x['endpoint']):
        print(f"  {route['endpoint']:50s} {route['methods']:10s} {route['path']}")
    
    print("\nBuscando 'eliminar_imagen_prensa':")
    found = [r for r in routes if 'eliminar_imagen' in r['endpoint']]
    if found:
        for route in found:
            print(f"  ✓ {route['endpoint']:50s} {route['methods']:10s} {route['path']}")
    else:
        print("  ✗ NO ENCONTRADO")
        
    print("\nBuscando rutas similares ('borrar', 'eliminar'):")
    similar = [r for r in routes if any(word in r['endpoint'].lower() for word in ['borrar', 'eliminar', 'delete', 'remove'])]
    for route in sorted(similar, key=lambda x: x['endpoint'])[:20]:
        print(f"  {route['endpoint']:50s} {route['methods']:10s} {route['path']}")
