"""
Verificar configuración de red del proyecto activo
"""
import sys
sys.path.insert(0, '.')

from app import app, db, Proyecto
import json

def verificar():
    with app.app_context():
        proyectos = Proyecto.query.all()
        
        print("📊 Configuraciones de red por proyecto:\n")
        
        for p in proyectos:
            print(f"{'='*60}")
            print(f"Proyecto: {p.nombre} (ID: {p.id})")
            print(f"{'='*60}")
            
            if p.red_tipos:
                try:
                    config = json.loads(p.red_tipos)
                    print(f"✅ Tiene configuración guardada:\n")
                    
                    for tipo_key, tipo_data in config.items():
                        print(f"  {tipo_key}:")
                        print(f"    - Nombre: {tipo_data.get('nombre', 'N/A')}")
                        print(f"    - Color: {tipo_data.get('color', 'N/A')}")
                        print(f"    - Forma: {tipo_data.get('forma', 'N/A')}")
                        entidades = tipo_data.get('entidades', [])
                        print(f"    - Entidades ({len(entidades)}): {entidades[:5]}{'...' if len(entidades) > 5 else ''}")
                        print()
                        
                except Exception as e:
                    print(f"❌ Error parseando JSON: {e}")
                    print(f"Contenido: {p.red_tipos[:200]}...")
            else:
                print("⚠️ Sin configuración (red_tipos = NULL)\n")
            
            print()

if __name__ == "__main__":
    verificar()
