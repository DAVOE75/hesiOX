"""
Servicio de Embeddings Semánticos para Búsqueda de Deep Learning
================================================================

Este servicio genera vectores semánticos (embeddings) de alta dimensionalidad
que capturan el significado profundo de los textos, permitiendo búsquedas
conceptuales más allá de coincidencias exactas de palabras.

Modelos soportados:
- OpenAI: text-embedding-3-small (1536 dims), text-embedding-3-large (3072 dims)
- Google: text-embedding-004 (768 dims)

Autor: HESIOX Team
"""

import numpy as np
import requests
import json
from typing import List, Optional, Tuple
from flask_login import current_user


class EmbeddingService:
    """Servicio para generar y comparar embeddings semánticos"""
    
    # Configuración de modelos
    MODELS = {
        'openai-small': {
            'name': 'text-embedding-3-small',
            'dimensions': 1536,
            'provider': 'openai',
            'cost_per_million': 0.02  # USD
        },
        'openai-large': {
            'name': 'text-embedding-3-large',
            'dimensions': 3072,
            'provider': 'openai',
            'cost_per_million': 0.13
        },
        'google': {
            'name': 'models/gemini-embedding-001',
            'dimensions': 768,  # Dimensión estándar de gemini-embedding-001
            'provider': 'google',
            'cost_per_million': 0.00  # Gratis hasta cierto límite
        }
    }
    
    def __init__(self, user=None, default_model='openai-small'):
        """
        Inicializa el servicio de embeddings
        
        Args:
            user: Usuario Flask-Login para obtener API keys personales
            default_model: Modelo por defecto a usar
        """
        self.user = user if user else current_user
        self.default_model = default_model
        self._api_keys_cache = {}
    
    def _get_api_key(self, provider: str) -> Optional[str]:
        """Obtiene la API key del usuario o del entorno"""
        if provider in self._api_keys_cache:
            return self._api_keys_cache[provider]
        
        import os
        key = None
        
        if provider == 'openai':
            # Prioridad: usuario > entorno
            if self.user and hasattr(self.user, 'api_key_openai') and self.user.api_key_openai:
                if getattr(self.user, 'ai_openai_active', True):
                    key = self.user.api_key_openai
            else:
                key = os.getenv('OPENAI_API_KEY')
        
        elif provider == 'google':
            if self.user and hasattr(self.user, 'api_key_gemini') and self.user.api_key_gemini:
                if getattr(self.user, 'ai_gemini_active', True):
                    key = self.user.api_key_gemini
            else:
                key = os.getenv('GOOGLE_API_KEY') or os.getenv('GEMINI_API_KEY')
        
        self._api_keys_cache[provider] = key
        return key
    
    def generate_embedding(self, text: str, model: str = None) -> Optional[List[float]]:
        """
        Genera un embedding semántico para un texto
        
        Args:
            text: Texto a vectorizar
            model: Modelo a usar (openai-small, openai-large, google)
        
        Returns:
            Lista de floats representando el embedding, o None si falla
        """
        if not text or not text.strip():
            return None
        
        model = model or self.default_model
        model_config = self.MODELS.get(model)
        
        if not model_config:
            raise ValueError(f"Modelo no soportado: {model}")
        
        provider = model_config['provider']
        api_key = self._get_api_key(provider)
        
        if not api_key:
            raise ValueError(f"No hay API key disponible para {provider}")
        
        try:
            if provider == 'openai':
                return self._generate_openai_embedding(text, model_config['name'], api_key)
            elif provider == 'google':
                return self._generate_google_embedding(text, model_config['name'], api_key)
        except Exception as e:
            # Propagamos el error real para que el usuario sepa qué pasa (ej: quota excedida)
            raise e
    
    def _generate_openai_embedding(self, text: str, model_name: str, api_key: str) -> List[float]:
        """Genera embedding usando OpenAI API (REST directo para evitar conflictos de librerías)"""
        url = "https://api.openai.com/v1/embeddings"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # Truncar texto si es muy largo (OpenAI tiene límite de ~8191 tokens)
        text = text[:30000]  # ~7500 tokens aproximadamente
        
        payload = {
            "model": model_name,
            "input": text,
            "encoding_format": "float"
        }
        
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        
        if response.status_code != 200:
            error_details = response.text
            raise Exception(f"OpenAI API Error {response.status_code}: {error_details}")
            
        data = response.json()
        return data['data'][0]['embedding']
    
    def _generate_google_embedding(self, text: str, model_name: str, api_key: str) -> List[float]:
        """Genera embedding usando Google Gemini API"""
        try:
            import google.generativeai as genai
        except ImportError:
            raise ImportError("El paquete 'google-generativeai' no está instalado. Ejecuta: pip install google-generativeai")
        
        genai.configure(api_key=api_key)
        
        # Truncar texto si es muy largo
        text = text[:10000]
        
        # Dimensiones deseadas (si el modelo lo soporta, suele ser 768 por defecto)
        model_info = self.get_model_info('google')
        target_dim = model_info.get('dimensions', 768)
        
        result = genai.embed_content(
            model=model_name,
            content=text,
            task_type="retrieval_document",
            output_dimensionality=target_dim  # Forzar dimensión deseada si es posible
        )
        
        emb = result['embedding']
        if len(emb) != target_dim:
            print(f"[EMBEDDING] WARNING: Google API devolvió {len(emb)} dimensiones, se esperaban {target_dim}")
            
        return emb
    
    def generate_query_embedding(self, query: str, model: str = None) -> Optional[List[float]]:
        """
        Genera embedding optimizado para queries de búsqueda
        
        Args:
            query: Consulta del usuario
            model: Modelo a usar
        
        Returns:
            Embedding del query
        """
        model = model or self.default_model
        model_config = self.MODELS.get(model)
        
        if not model_config:
            return None
        
        provider = model_config['provider']
        
        # Para Google, usar task_type específico para queries
        if provider == 'google':
            api_key = self._get_api_key('google')
            if not api_key:
                return None
            
            try:
                import google.generativeai as genai
            except ImportError:
                return None
            
            try:
                # Dimensiones deseadas
                model_info = self.get_model_info('google')
                target_dim = model_info.get('dimensions', 768)
                
                genai.configure(api_key=api_key)
                result = genai.embed_content(
                    model=model_config['name'],
                    content=query,
                    task_type="retrieval_query",  # Optimizado para búsquedas
                    output_dimensionality=target_dim
                )
                return result['embedding']
            except Exception as e:
                # Propagamos el error real
                raise e
        
        # Para OpenAI, usar el método estándar
        return self.generate_embedding(query, model)
    
    @staticmethod
    def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
        """
        Calcula similitud coseno entre dos vectores
        
        Args:
            vec1, vec2: Vectores a comparar
        
        Returns:
            Similitud entre -1 y 1 (1 = idénticos, 0 = ortogonales, -1 = opuestos)
        """
        v1 = np.array(vec1)
        v2 = np.array(vec2)
        
        dot_product = np.dot(v1, v2)
        norm_v1 = np.linalg.norm(v1)
        norm_v2 = np.linalg.norm(v2)
        
        if norm_v1 == 0 or norm_v2 == 0:
            return 0.0
        
        return float(dot_product / (norm_v1 * norm_v2))
    
    @staticmethod
    def batch_cosine_similarity(query_vec: List[float], doc_vecs: List[List[float]]) -> List[float]:
        """
        Calcula similitud coseno entre un query y múltiples documentos (vectorizado)
        
        Args:
            query_vec: Vector del query
            doc_vecs: Lista de vectores de documentos
        
        Returns:
            Lista de similitudes
        """
        # Filtrar vectores que no tengan la misma dimensión que el query
        # Esto evita el error "inhomogeneous shape" de NumPy
        query_dim = len(query_vec)
        valid_doc_vecs = [v for v in doc_vecs if v is not None and len(v) == query_dim]
        
        if not valid_doc_vecs:
            return [0.0] * len(doc_vecs)
            
        q = np.array(query_vec)
        docs = np.array(valid_doc_vecs)
        
        # Normalizar query
        norm_q = np.linalg.norm(q)
        if norm_q == 0:
            return [0.0] * len(doc_vecs)
        q_norm = q / norm_q
        
        # Normalizar documentos
        doc_norms = np.linalg.norm(docs, axis=1, keepdims=True)
        doc_norms[doc_norms == 0] = 1  # Evitar división por cero
        docs_norm = docs / doc_norms
        
        # Producto punto vectorizado
        similarities = np.dot(docs_norm, q_norm)
        
        # Reconstruir lista manteniendo el orden original (rellenando con 0 donde no era válido)
        final_similarities = []
        sim_idx = 0
        for v in doc_vecs:
            if v is not None and len(v) == query_dim:
                final_similarities.append(float(similarities[sim_idx]))
                sim_idx += 1
            else:
                final_similarities.append(0.0)
                
        return final_similarities
    
    def prepare_text_for_embedding(self, titulo: str, contenido: str, temas: str = None) -> str:
        """
        Prepara un texto combinando título, temas y contenido para embedding
        
        Args:
            titulo: Título del documento
            contenido: Contenido del documento
            temas: Temas/tags del documento (opcional)
        
        Returns:
            Texto combinado optimizado para embedding
        """
        parts = []
        
        # El título es importante, lo duplicamos para darle más peso
        if titulo and titulo.strip():
            parts.append(f"{titulo}. {titulo}.")
        
        # Los temas son muy relevantes para búsqueda conceptual
        if temas and temas.strip():
            parts.append(f"Temas: {temas}.")
        
        # Contenido principal (truncado si es muy largo)
        if contenido and contenido.strip():
            # Primeros 25000 caracteres (suficiente para contexto semántico)
            parts.append(contenido[:25000])
        
        return " ".join(parts)
    
    def get_model_info(self, model: str) -> dict:
        """Retorna información sobre un modelo de embeddings"""
        return self.MODELS.get(model, {})
    
        return available
        
    def detect_model_from_dimension(self, dimension: int) -> Optional[str]:
        """
        Infiere el modelo de embedding basado en la dimensión del vector
        
        Args:
            dimension: Longitud del vector
            
        Returns:
            Identificador del modelo (openai-small, google, etc.) o None
        """
        for model_id, config in self.MODELS.items():
            if config['dimensions'] == dimension:
                return model_id
        return None
