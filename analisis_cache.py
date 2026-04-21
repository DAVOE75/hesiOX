"""
Sistema de caché para análisis avanzados
Guarda resultados en archivos JSON para evitar recálculos
"""

import json
import os
import hashlib
from datetime import datetime, timedelta
from pathlib import Path


class AnalisisCache:
    def __init__(self, cache_dir='cache/analisis'):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl_hours = 24  # Tiempo de vida de la caché: 24 horas
    
    def _generar_clave(self, tipo_analisis, filtros, **kwargs):
        """Genera una clave única basada en el tipo de análisis y filtros"""
        # Crear un diccionario ordenado con todos los parámetros
        params = {
            'tipo': tipo_analisis,
            **filtros,
            **kwargs
        }
        
        # Convertir a string ordenado y hacer hash
        params_str = json.dumps(params, sort_keys=True)
        hash_obj = hashlib.md5(params_str.encode())
        return hash_obj.hexdigest()
    
    def _get_cache_path(self, clave):
        """Retorna la ruta del archivo de caché"""
        return self.cache_dir / f"{clave}.json"
    
    def obtener(self, tipo_analisis, filtros, **kwargs):
        """
        Obtiene resultado de la caché si existe y no ha expirado
        
        Returns:
            dict o None: Los datos cacheados o None si no existe/expiró
        """
        clave = self._generar_clave(tipo_analisis, filtros, **kwargs)
        cache_path = self._get_cache_path(clave)
        
        if not cache_path.exists():
            return None
        
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Verificar si ha expirado
            timestamp = datetime.fromisoformat(data['timestamp'])
            if datetime.now() - timestamp > timedelta(hours=self.ttl_hours):
                # Caché expirada, eliminar archivo
                cache_path.unlink()
                return None
            
            print(f"[CACHE HIT] {tipo_analisis} - {clave[:8]}")
            return data['resultado']
        
        except Exception as e:
            print(f"[CACHE ERROR] Error al leer caché: {e}")
            return None
    
    def guardar(self, tipo_analisis, filtros, resultado, **kwargs):
        """
        Guarda resultado en la caché
        
        Args:
            tipo_analisis: Tipo de análisis (sentimiento, topics, etc.)
            filtros: Diccionario con filtros aplicados
            resultado: Resultado a cachear
            **kwargs: Parámetros adicionales (n, top_k, etc.)
        """
        clave = self._generar_clave(tipo_analisis, filtros, **kwargs)
        cache_path = self._get_cache_path(clave)
        
        try:
            data = {
                'timestamp': datetime.now().isoformat(),
                'tipo_analisis': tipo_analisis,
                'filtros': filtros,
                'params': kwargs,
                'resultado': resultado
            }
            
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            print(f"[CACHE SAVE] {tipo_analisis} - {clave[:8]}")
        
        except Exception as e:
            print(f"[CACHE ERROR] Error al guardar caché: {e}")
    
    def limpiar_todo(self):
        """Elimina todos los archivos de caché"""
        count = 0
        for cache_file in self.cache_dir.glob('*.json'):
            try:
                cache_file.unlink()
                count += 1
            except Exception as e:
                print(f"[CACHE ERROR] No se pudo eliminar {cache_file}: {e}")
        
        print(f"[CACHE] Limpiados {count} archivos de caché")
        return count
    
    def limpiar_expirados(self):
        """Elimina archivos de caché expirados"""
        count = 0
        for cache_file in self.cache_dir.glob('*.json'):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                timestamp = datetime.fromisoformat(data['timestamp'])
                if datetime.now() - timestamp > timedelta(hours=self.ttl_hours):
                    cache_file.unlink()
                    count += 1
            
            except Exception as e:
                # Si hay error al leer, eliminar el archivo corrupto
                cache_file.unlink()
                count += 1
        
        if count > 0:
            print(f"[CACHE] Limpiados {count} archivos expirados")
        return count
    
    def obtener_estadisticas(self):
        """Retorna estadísticas de la caché"""
        archivos = list(self.cache_dir.glob('*.json'))
        total = len(archivos)
        expirados = 0
        tamano_total = 0
        
        for cache_file in archivos:
            try:
                tamano_total += cache_file.stat().st_size
                
                with open(cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                timestamp = datetime.fromisoformat(data['timestamp'])
                if datetime.now() - timestamp > timedelta(hours=self.ttl_hours):
                    expirados += 1
            
            except Exception:
                pass
        
        return {
            'total_archivos': total,
            'expirados': expirados,
            'activos': total - expirados,
            'tamano_mb': round(tamano_total / (1024 * 1024), 2),
            'ttl_horas': self.ttl_hours
        }


# Instancia global
cache = AnalisisCache()
