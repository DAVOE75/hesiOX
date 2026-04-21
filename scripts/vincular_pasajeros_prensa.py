import os
import sys

# Añadir el directorio raíz al path para poder importar app y models
sys.path.append(os.getcwd())

from app import app
from models import PasajeroSirio, Prensa, db
from sqlalchemy import or_, func
import argparse

def vincular_pasajeros_prensa(proyecto_id=1, dry_run=False, limit=None):
    print(f"Iniciando proceso {'(DRY RUN)' if dry_run else ''} para proyecto ID: {proyecto_id}")
    
    with app.app_context():
        # 1. Obtener todos los pasajeros
        pasajeros_query = PasajeroSirio.query
        if limit:
            pasajeros_query = pasajeros_query.limit(limit)
        
        pasajeros = pasajeros_query.all()
        total_pasajeros = len(pasajeros)
        print(f"Procesando {total_pasajeros} pasajeros...")

        total_vinculos = 0
        pasajeros_con_menciones = 0

        for i, pasajero in enumerate(pasajeros):
            if i % 100 == 0 and i > 0:
                print(f"Progreso: {i}/{total_pasajeros} pasajeros procesados...")

            search_terms = []
            if pasajero.apellidos:
                # Limpiamos paréntesis y comas
                # Lista de palabras a ignorar (preposiciones comunes en apellidos)
                blacklist = {'del', 'los', 'las', 'dos', 'san', 'santa', 'von', 'van', 'der', 'das', 'den'}
                apell_clean = pasajero.apellidos.split('(')[0].replace(',', ' ').strip()
                
                # Normalizamos para comparar con blacklist pero mantenemos el término original para la búsqueda
                for t in apell_clean.split():
                    term = t.strip()
                    if len(term) > 2 and term.lower() not in blacklist:
                        search_terms.append(term)
            
            # Si no hay apellidos largos, probar con el nombre (solo si es largo)
            if not search_terms and pasajero.nombre:
                nomb_clean = pasajero.nombre.replace(',', ' ').strip()
                search_terms.extend([t.strip() for t in nomb_clean.split() if len(t.strip()) > 2])

            if not search_terms:
                continue

            condiciones = []
            for term in search_terms:
                # Usamos func.unaccent para ignorar acentos
                condiciones.append(func.unaccent(Prensa.titulo).ilike(f"%{term}%"))
                condiciones.append(func.unaccent(Prensa.contenido).ilike(f"%{term}%"))
                condiciones.append(func.unaccent(Prensa.texto_original).ilike(f"%{term}%"))

            query = Prensa.query
            if proyecto_id:
                query = query.filter(Prensa.proyecto_id == proyecto_id)
            
            if condiciones:
                query = query.filter(or_(*condiciones))
            
            found_articles = query.all()
            
            new_links = 0
            if found_articles:
                menciones_actuales_ids = {art.id for art in pasajero.menciones_prensa}
                for art in found_articles:
                    if art.id not in menciones_actuales_ids:
                        if not dry_run:
                            pasajero.menciones_prensa.append(art)
                        new_links += 1
            
            if new_links > 0:
                print(f"[{i}/{total_pasajeros}] Pasajero: {pasajero.nombre} {pasajero.apellidos} -> {new_links} nuevas menciones encontradas.")
                total_vinculos += new_links
                pasajeros_con_menciones += 1

            # Commit periódico para no saturar la memoria y asegurar persistencia
            if not dry_run and total_vinculos > 0 and total_vinculos % 50 == 0:
                try:
                    db.session.commit()
                except Exception as e:
                    print(f"Error en commit intermedio: {e}")
                    db.session.rollback()

        if not dry_run:
            try:
                db.session.commit()
                print(f"\nProceso finalizado correctamente.")
                print(f"Total vinculaciones realizadas: {total_vinculos}")
            except Exception as e:
                print(f"\nError en commit final: {e}")
                db.session.rollback()
        else:
            print(f"\nSimulación finalizada (DRY RUN).")
            print(f"Total vinculaciones potenciales: {total_vinculos}")
        
        print(f"Pasajeros con menciones encontradas: {pasajeros_con_menciones}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Vincular pasajeros con noticias de prensa automáticamente.')
    parser.add_argument('--proyecto', type=int, default=1, help='ID del proyecto (por defecto 1: Sirio)')
    parser.add_argument('--dry-run', action='store_true', help='Simular el proceso sin guardar cambios')
    parser.add_argument('--limit', type=int, help='Limitar el número de pasajeros a procesar (para pruebas)')
    
    args = parser.parse_args()
    
    # Asegurarse de que el directorio de logs existe si fuera necesario
    # os.makedirs('logs', exist_ok=True)
    
    vincular_pasajeros_prensa(proyecto_id=args.proyecto, dry_run=args.dry_run, limit=args.limit)
