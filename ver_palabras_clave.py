"""
Ver palabras clave y temas disponibles en el proyecto activo
"""
import sys
sys.path.insert(0, '.')

from app import app, db, Prensa
from collections import Counter

def analizar_proyecto(proyecto_id=1):
    with app.app_context():
        noticias = Prensa.query.filter_by(proyecto_id=proyecto_id).all()
        
        print(f"📊 Análisis de palabras clave y temas (Proyecto ID: {proyecto_id})")
        print(f"Total de artículos: {len(noticias)}\n")
        
        # Contador de palabras clave
        palabras = Counter()
        temas = Counter()
        
        for n in noticias:
            if n.palabras_clave:
                for p in n.palabras_clave.split(','):
                    p = p.strip()
                    if p:
                        palabras[p] += 1
            
            if n.temas:
                for t in n.temas.split(','):
                    t = t.strip()
                    if t:
                        temas[t] += 1
        
        print("🔑 TOP 30 PALABRAS CLAVE más frecuentes:")
        print("-" * 60)
        for palabra, count in palabras.most_common(30):
            print(f"  {palabra:<40} ({count} veces)")
        
        print(f"\n📚 TOP 30 TEMAS más frecuentes:")
        print("-" * 60)
        for tema, count in temas.most_common(30):
            print(f"  {tema:<40} ({count} veces)")
        
        print(f"\n💡 TIP: Copia estos nombres EXACTAMENTE como aparecen aquí")
        print(f"    y agrégalos en la configuración de red")

if __name__ == "__main__":
    analizar_proyecto(1)  # Proyecto Sirio
