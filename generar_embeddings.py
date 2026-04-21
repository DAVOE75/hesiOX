"""
Script para generar embeddings semánticos en batch
===================================================

Este script genera vectores semánticos (embeddings) para todas las noticias
del proyecto activo que aún no tienen embeddings.

Uso:
    python generar_embeddings.py [--modelo openai-small|openai-large|google] [--batch-size 50] [--limite 1000]

Ejemplos:
    python generar_embeddings.py --modelo openai-small --batch-size 50
    python generar_embeddings.py --modelo google --limite 500

El script:
1. Busca noticias del proyecto activo sin embeddings
2. Genera embeddings usando el servicio configurado
3. Guarda los embeddings en la base de datos
4. Muestra progreso y estimación de costos

Autor: HESIOX Team
"""

import sys
import os
import argparse
from datetime import datetime
import time
import json

# Añadir el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import Prensa, Proyecto
from services.embedding_service import EmbeddingService
from flask import current_app
from sqlalchemy import func


def obtener_proyecto_activo():
    """Obtiene el proyecto activo desde la configuración"""
    with app.app_context():
        # Buscar el primer proyecto activo (simplificado para script)
        proyecto = Proyecto.query.first()
        if not proyecto:
            print("❌ No hay proyectos en la base de datos")
            return None
        return proyecto


def contar_noticias_pendientes(proyecto_id=None):
    """Cuenta cuántas noticias necesitan embeddings"""
    query = db.session.query(func.count(Prensa.id)).filter(
        Prensa.incluido == True,
        Prensa.embedding_vector.is_(None)
    )
    
    if proyecto_id:
        query = query.filter(Prensa.proyecto_id == proyecto_id)
    
    return query.scalar()


def _guardar_progreso(proyecto_id, procesados, total, errores=0, status="running"):
    """Guarda el progreso en un archivo JSON para ser consumido por la API"""
    progreso_id = proyecto_id if proyecto_id else "global"
    path = f"/tmp/embedding_progress_{progreso_id}.json"
    
    data = {
        "proyecto_id": proyecto_id,
        "procesados": procesados,
        "total": total,
        "errores": errores,
        "status": status,
        "porcentaje": round((procesados / total * 100), 1) if total > 0 else 0,
        "actualizado_en": datetime.utcnow().isoformat()
    }
    
    try:
        with open(path, "w") as f:
            json.dump(data, f)
    except Exception as e:
        print(f"Error guardando progreso: {e}")


def generar_embeddings_batch(proyecto_id=None, modelo='openai-small', batch_size=50, limite=None, interactive=True):
    """
    Genera embeddings en batch para las noticias sin embeddings
    
    Args:
        proyecto_id: ID del proyecto (None = todos los proyectos)
        modelo: Modelo de embeddings a usar
        batch_size: Número de embeddings por commit de DB
        limite: Límite máximo de noticias a procesar (None = todas)
        interactive: Si es True, pide confirmación por consola
    """
    with app.app_context():
        # Inicializar servicio de embeddings (sin usuario, usa env vars)
        embedding_service = EmbeddingService(user=None, default_model=modelo)
        
        # Obtener información del modelo
        model_info = embedding_service.get_model_info(modelo)
        
        # Inicializar progreso INMEDIATAMENTE para evitar 404 en el frontend
        _guardar_progreso(proyecto_id, 0, 0, status="initializing")
        
        # Verificar API keys disponibles
        modelos_disponibles = embedding_service.list_available_models()
        if modelo not in modelos_disponibles:
            error_msg = f"Modelo {modelo} no disponible. API keys no configuradas."
            print(f"❌ {error_msg}")
            _guardar_progreso(proyecto_id, 0, 0, status="error")
            return
        
        # Obtener información del modelo
        model_info = embedding_service.get_model_info(modelo)
        print(f"\n{'='*70}")
        print(f"🧠 GENERADOR DE EMBEDDINGS SEMÁNTICOS")
        print(f"{'='*70}")
        print(f"Modelo: {model_info['name']}")
        print(f"Dimensiones: {model_info['dimensions']}")
        print(f"Proveedor: {model_info['provider'].upper()}")
        print(f"Costo estimado: ${model_info['cost_per_million']:.4f} por millón de tokens")
        print(f"{'='*70}\n")
        
        # Contar noticias pendientes
        total_pendientes = contar_noticias_pendientes(proyecto_id)
        
        if limite:
            total_a_procesar = min(total_pendientes, limite)
        else:
            total_a_procesar = total_pendientes
        
        print(f"📊 Noticias pendientes: {total_pendientes}")
        print(f"📊 Noticias a procesar: {total_a_procesar}")
        
        if total_a_procesar == 0:
            print("✅ No hay noticias pendientes. Todas tienen embeddings.")
            return
        
        # Confirmación (solo si es interactivo)
        if interactive:
            print(f"\n⚠️  Se generarán {total_a_procesar} embeddings")
            if model_info['cost_per_million'] > 0:
                # Estimación aproximada (asumiendo ~500 tokens por documento)
                tokens_estimados = total_a_procesar * 500
                costo_estimado = (tokens_estimados / 1_000_000) * model_info['cost_per_million']
                print(f"💰 Costo estimado: ~${costo_estimado:.4f} USD")
            
            respuesta = input("\n¿Continuar? (s/n): ").strip().lower()
            if respuesta != 's':
                print("❌ Operación cancelada")
                return
        
        # Procesar en batches
        procesados = 0
        errores = 0
        inicio = time.time()
        
        # Query para obtener noticias sin embeddings
        query = db.session.query(Prensa).filter(
            Prensa.incluido == True,
            Prensa.embedding_vector.is_(None)
        ).order_by(Prensa.id)
        
        if proyecto_id:
            query = query.filter(Prensa.proyecto_id == proyecto_id)
        
        if limite:
            query = query.limit(limite)
        
        noticias = query.all()
        
        print(f"\n🚀 Iniciando generación de embeddings...\n")
        
        # Inicializar progreso
        _guardar_progreso(proyecto_id, 0, total_a_procesar, status="running")
        
        for i, noticia in enumerate(noticias, 1):
            try:
                # Preparar texto para embedding
                texto = embedding_service.prepare_text_for_embedding(
                    titulo=noticia.titulo or "",
                    contenido=noticia.contenido or "",
                    temas=noticia.temas or ""
                )
                
                # Generar embedding
                embedding = embedding_service.generate_embedding(texto, model=modelo)
                
                if embedding:
                    # Guardar en la base de datos
                    noticia.embedding_vector = embedding
                    noticia.embedding_model = model_info['name']
                    noticia.embedding_generado_en = datetime.utcnow()
                    
                    procesados += 1
                    
                    # Commit cada batch_size documentos
                    if procesados % batch_size == 0:
                        db.session.commit()
                        
                        # Calcular velocidad y tiempo restante
                        elapsed = time.time() - inicio
                        velocidad = procesados / elapsed
                        restantes = total_a_procesar - procesados
                        tiempo_restante = restantes / velocidad if velocidad > 0 else 0
                        
                        print(f"✓ {procesados}/{total_a_procesar} | "
                              f"Velocidad: {velocidad:.1f} docs/seg | "
                              f"Tiempo restante: ~{int(tiempo_restante/60)}min {int(tiempo_restante%60)}s")
                        
                        # Actualizar progreso en archivo
                        _guardar_progreso(proyecto_id, procesados, total_a_procesar, errores, status="running")
                else:
                    errores += 1
                    print(f"✗ Error en noticia ID {noticia.id}: No se generó embedding")
                    
            except Exception as e:
                errores += 1
                print(f"✗ Error en noticia ID {noticia.id}: {e}")
                continue
        
        # Commit final
        db.session.commit()
        
        # Resumen final
        tiempo_total = time.time() - inicio
        print(f"\n{'='*70}")
        print(f"✅ PROCESO COMPLETADO")
        print(f"{'='*70}")
        print(f"Procesados exitosamente: {procesados}")
        print(f"Errores: {errores}")
        print(f"Tiempo total: {int(tiempo_total/60)}min {int(tiempo_total%60)}s")
        print(f"Velocidad promedio: {procesados/tiempo_total:.2f} docs/seg")
        print(f"{'='*70}\n")
        
        # Finalizar progreso
        _guardar_progreso(proyecto_id, procesados, total_a_procesar, errores, status="completed")


def main():
    parser = argparse.ArgumentParser(
        description='Genera embeddings semánticos para noticias sin vectores',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  %(prog)s --modelo openai-small --batch-size 50
  %(prog)s --modelo google --limite 1000
  %(prog)s --modelo openai-large --batch-size 20
        """
    )
    
    parser.add_argument(
        '--proyecto-id',
        type=int,
        default=None,
        help='ID del proyecto específico (default: todos los proyectos)'
    )
    
    parser.add_argument(
        '--modelo',
        choices=['openai-small', 'openai-large', 'google'],
        default='openai-small',
        help='Modelo de embeddings a usar (default: openai-small)'
    )
    
    parser.add_argument(
        '--batch-size',
        type=int,
        default=50,
        help='Número de embeddings por commit de DB (default: 50)'
    )
    
    parser.add_argument(
        '--limite',
        type=int,
        default=None,
        help='Límite máximo de noticias a procesar (default: todas)'
    )
    
    args = parser.parse_args()
    
    with app.app_context():
        # Mostrar proyecto(s) a procesar
        if args.proyecto_id:
            proyecto = db.session.query(Proyecto).get(args.proyecto_id)
            if not proyecto:
                print(f"❌ Proyecto con ID {args.proyecto_id} no encontrado")
                sys.exit(1)
            print(f"📂 Proyecto: {proyecto.nombre} (ID: {proyecto.id})")
        else:
            print("📂 Procesando TODOS los proyectos")
        
        # Generar embeddings
        generar_embeddings_batch(
            proyecto_id=args.proyecto_id,
            modelo=args.modelo,
            batch_size=args.batch_size,
            limite=args.limite,
            interactive=True
        )


if __name__ == '__main__':
    main()
