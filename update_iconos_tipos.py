#!/usr/bin/env python3
"""
Script para actualizar iconos de tipos de ubicación
"""
from app import app, db
from models import TipoUbicacion

def actualizar_iconos():
    with app.app_context():
        # Actualizar iconos
        actualizaciones = [
            {'codigo': 'gulf', 'icono': 'fa-solid fa-water', 'nombre_esperado': 'Golfo'},
            {'codigo': 'lighthouse', 'icono': 'fa-solid fa-lightbulb', 'nombre_esperado': 'Faro'},
            {'codigo': 'island', 'icono': 'fa-solid fa-island-tropical', 'nombre_esperado': 'Isla'}
        ]
        
        actualizados = []
        no_encontrados = []
        
        for item in actualizaciones:
            tipo = TipoUbicacion.query.filter_by(codigo=item['codigo']).first()
            if tipo:
                tipo.icono = item['icono']
                actualizados.append(f"✅ {tipo.nombre} ({tipo.codigo}): {item['icono']}")
            else:
                no_encontrados.append(f"❌ No se encontró tipo con código: {item['codigo']}")
        
        db.session.commit()
        
        print("\n=== ACTUALIZACIÓN DE ICONOS ===")
        print("\nActualizados:")
        for msg in actualizados:
            print(f"  {msg}")
        
        if no_encontrados:
            print("\nNo encontrados:")
            for msg in no_encontrados:
                print(f"  {msg}")
        
        print(f"\nTotal actualizados: {len(actualizados)}")

if __name__ == '__main__':
    actualizar_iconos()
