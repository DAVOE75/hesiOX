"""
Módulo de Análisis Avanzado para Humanidades Digitales
Proyecto Sirio - Sistema de Análisis Bibliográfico
"""

import re
import numpy as np
import pandas as pd
from collections import Counter, defaultdict
from itertools import combinations
from datetime import datetime
from typing import List, Dict, Tuple, Any
import json
import html

# NLP Libraries
# Lazy loading implemented in class

try:
    from textblob import TextBlob
    from textblob.translate import NotTranslated
except:
    TextBlob = None

try:
    from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
    from sklearn.decomposition import LatentDirichletAllocation
    from sklearn.cluster import KMeans, DBSCAN
    from sklearn.metrics.pairwise import cosine_similarity
    from sklearn.manifold import TSNE
except:
    pass

try:
    from gensim import corpora
    from gensim.models import LdaModel
except:
    pass


class AnalisisAvanzado:
    """Clase principal para análisis avanzados de corpus textual"""
    
    def __init__(self, db_connection):
        self.db = db_connection
        self._nlp = None
        
        # Stopwords AGRESIVAS - Para análisis de contenido (noticias, artículos)
        self.stopwords_contenido = {
            'el', 'la', 'de', 'que', 'y', 'a', 'en', 'un', 'una', 'ser', 'se', 'no', 'haber', 
            'por', 'con', 'su', 'para', 'como', 'estar', 'tener', 'le', 'lo', 'todo',
            'pero', 'más', 'hacer', 'o', 'poder', 'decir', 'este', 'esta', 'ir', 'otro', 'otra', 'ese',
            'esa', 'si', 'me', 'ya', 'ver', 'porque', 'dar', 'cuando', 'él', 'muy', 'sin',
            'vez', 'mucho', 'saber', 'qué', 'sobre', 'mi', 'alguno', 'alguna', 'mismo', 'misma', 'yo', 'también',
            'hasta', 'año', 'dos', 'tres', 'querer', 'entre', 'así', 'primero', 'primera', 'desde', 'grande',
            'eso', 'ni', 'nos', 'llegar', 'pasar', 'tiempo', 'ella', 'sí', 'día', 'uno',
            'bien', 'poco', 'poca', 'deber', 'entonces', 'poner', 'cosa', 'tanto', 'tanta', 'hombre', 'parecer',
            'nuestro', 'nuestra', 'tan', 'donde', 'ahora', 'parte', 'después', 'vida', 'quedar', 'siempre',
            'creer', 'hablar', 'llevar', 'dejar', 'nada', 'cada', 'seguir', 'menos', 'nuevo', 'nueva',
            'encontrar', 'algo', 'solo', 'sola', 'decir', 'llamar', 'venir', 'pensar', 'salir', 'volver',
            'tomar', 'conocer', 'vivir', 'sentir', 'tratar', 'mirar', 'contar', 'empezar',
            'esperar', 'buscar', 'existir', 'entrar', 'trabajar', 'escribir', 'perder', 'producir',
            'ocurrir', 'entender', 'pedir', 'recibir', 'recordar', 'terminar', 'permitir', 'aparecer',
            'conseguir', 'comenzar', 'servir', 'sacar', 'necesitar', 'mantener', 'resultar', 'leer',
            'caer', 'cambiar', 'presentar', 'crear', 'abrir', 'considerar', 'oír', 'acabar', 'mil',
            'ha', 'han', 'había', 'he', 'has', 'hay', 'sido', 'era', 'eran', 'fueron', 'sea', 'fue',
            'estos', 'estas', 'esos', 'esas', 'aquel', 'aquella', 'aquellos', 'aquellas', 'cual', 'cuales',
            'quien', 'quienes', 'cuyo', 'cuya', 'cuyos', 'cuyas', 'cuanto', 'cuanta', 'cuantos', 'cuantas',
            'del', 'al', 'los', 'las', 'unos', 'unas', 'mis', 'tus', 'sus', 'nuestros', 'nuestras', 'vuestros', 'vuestras',
            'mío', 'tuyo', 'suyo', 'nuestro', 'vuestro', 'mía', 'tuya', 'suya', 'nuestra', 'vuestra',
            'míos', 'tuyos', 'suyos', 'mías', 'tuyas', 'suyas', 'tal', 'tales', 'algún', 'ningún', 'ninguna'
        }
        
        # Stopwords MÍNIMAS - Para análisis estilométrico (literatura, poesía, autor)
        # Solo las más comunes para que emerja el estilo del autor
        self.stopwords_estilometrico = {
            'el', 'la', 'de', 'que', 'y', 'a', 'en', 'un', 'una', 'del', 'al', 'los', 'las'
        }
        
        # Stopwords INTERMEDIAS - Para análisis mixto
        self.stopwords_mixto = {
            'el', 'la', 'de', 'que', 'y', 'a', 'en', 'un', 'una', 'ser', 'se', 'no', 
            'por', 'con', 'su', 'para', 'como', 'estar', 'tener', 'le', 'lo',
            'pero', 'más', 'o', 'este', 'esta', 'si', 'me', 'ya', 'muy', 'sin',
            'del', 'al', 'los', 'las', 'unos', 'unas'
        }
        
        # Alias para compatibilidad con código existente
        self.stopwords_es = self.stopwords_contenido
        
    @property
    def nlp(self):
        if self._nlp is None:
            from utils import get_nlp
            self._nlp = get_nlp()
        return self._nlp
    
    def set_perfil_analisis(self, perfil: str):
        """
        Configura el perfil de análisis para determinar qué stopwords usar
        
        Args:
            perfil: 'contenido', 'estilometrico' o 'mixto'
        """
        if perfil == 'estilometrico':
            self.stopwords_es = self.stopwords_estilometrico
        elif perfil == 'mixto':
            self.stopwords_es = self.stopwords_mixto
        else:  # 'contenido' por defecto
            self.stopwords_es = self.stopwords_contenido
    
    def _limpiar_html(self, texto: str) -> str:
        """Limpia etiquetas HTML y entidades del texto"""
        if not texto:
            return ""
        
        # Decodificar entidades HTML (&eacute; -> é, etc.)
        texto = html.unescape(texto)
        
        # Eliminar etiquetas HTML
        texto = re.sub(r'<[^>]+>', ' ', texto)
        
        # Eliminar fragmentos comunes de HTML mal parseado
        texto = re.sub(r'&\w+;', ' ', texto)  # Entidades que quedaron sin parsear
        texto = re.sub(r'\b(nbsp|quot|amp|lt|gt|iexcl|iquest)\b', ' ', texto, flags=re.IGNORECASE)
        
        # Eliminar palabras que parecen entidades HTML residuales
        texto = re.sub(r'\b[a-z]+(acute|grave|circ|tilde|uml|cedil)\b', ' ', texto, flags=re.IGNORECASE)
        
        # Normalizar espacios
        texto = re.sub(r'\s+', ' ', texto).strip()
        
        return texto
    
    def _preprocesar_texto(self, texto: str) -> str:
        """Preprocesa texto: limpia HTML, normaliza y filtra"""
        # Limpiar HTML primero
        texto = self._limpiar_html(texto)
        
        # Convertir a minúsculas
        texto = texto.lower()
        
        # Eliminar números y puntuación
        texto = re.sub(r'[0-9]+', '', texto)
        texto = re.sub(r'[^\w\s]', ' ', texto)
        
        # Eliminar stopwords
        palabras = texto.split()
        palabras_filtradas = [p for p in palabras if p not in self.stopwords_es and len(p) > 2]
        
        return ' '.join(palabras_filtradas)
    
    # ============================================
    # 1. ANÁLISIS DE SENTIMIENTO TEMPORAL
    # ============================================
    
    def analisis_sentimiento_temporal(self, publicaciones: List[Dict], eje_x: str = 'fecha') -> Dict:
        """
        Analiza el sentimiento de publicaciones a lo largo del tiempo o secuencia
        
        Args:
            publicaciones: Lista de diccionarios con 'contenido', 'fecha', 'titulo'
            eje_x: 'fecha' (por defecto) o 'secuencia' (orden por ID)
        
        Returns:
            Dict con datos para gráfico temporal de sentimiento
        """
        resultados = []
        
        for pub in publicaciones:
            texto = pub.get('contenido', '') or pub.get('titulo', '')
            fecha = pub.get('fecha')
            
            if not texto:
                continue
            
            # Limpiar HTML antes del análisis de sentimiento
            texto_limpio = self._limpiar_html(texto)
            
            # Análisis de sentimiento (multilingüe)
            sentimiento = self._calcular_sentimiento(texto_limpio)
            
            resultados.append({
                'fecha': fecha,
                'sentimiento': sentimiento['polaridad'],
                'subjetividad': sentimiento['subjetividad'],
                'titulo': pub.get('titulo', ''),
                'id': pub.get('id')
            })
        
        # Procesamiento según eje X
        df = pd.DataFrame(resultados)
        if len(df) > 0:
            if eje_x == 'secuencia':
                # Ordenar por ID para secuencia lógica
                df.sort_values('id', inplace=True)
                
                # Crear etiquetas secuenciales
                df['etiqueta'] = [f"{i+1}. {t[:20]}..." for i, t in enumerate(df['titulo'])]
                df['indice'] = range(1, len(df) + 1)
                
                # Para visualización, usaremos el índice/título como eje X
                # No agrupamos, mostramos cada punto individualmente (ideal para capítulos)
                
                return {
                            'exito': True,
                            'datos_temporales': df.rename(columns={'etiqueta': 'fecha'}).to_dict('records'), # Reusamos campo 'fecha' para label X
                            'datos_individuales': resultados,
                            'estadisticas': {
                                'promedio_sentimiento': float(df['sentimiento'].mean()),
                                'promedio_subjetividad': float(df['subjetividad'].mean()),
                                'mediana_sentimiento': float(df['sentimiento'].median()),
                                'mediana_subjetividad': float(df['subjetividad'].median()),
                                'total_documentos': len(df)
                            },
                            'tipo_eje': 'secuencia'
                        }
            
            else: # eje_x == 'fecha' (COMPORTAMIENTO ORIGINAL)
                # Intentar convertir a datetime, coercing errores (fechas < 1677 o > 2262)
                # IMPORTANTE: Convertir a string primero para que 'coerce' funcione con objetos datetime.date antiguos
                df['fecha_str'] = df['fecha'].astype(str)
                df['fecha_dt'] = pd.to_datetime(df['fecha_str'], errors='coerce')
                
                # Separar fechas válidas para pandas y fechas históricas/invalidas
                df_validas = df.dropna(subset=['fecha_dt'])
                
                # Si tenemos fechas válidas, procesamos normal
                if len(df_validas) > 0:
                    fecha_min = df_validas['fecha_dt'].min()
                    fecha_max = df_validas['fecha_dt'].max()
                    
                    delta_dias = (fecha_max - fecha_min).days
                    
                    if delta_dias <= 60:
                        periodo = 'D'
                    elif delta_dias <= 1095:
                        periodo = 'M'
                    else:
                        periodo = 'Y'
                    
                    try:
                        df_agrupado = df_validas.groupby(df_validas['fecha_dt'].dt.to_period(periodo)).agg({
                            'sentimiento': 'mean',
                            'subjetividad': 'mean',
                            'titulo': 'count'
                        }).reset_index()
                        
                        df_agrupado.rename(columns={'fecha_dt': 'fecha', 'titulo': 'count'}, inplace=True)
                        df_agrupado['fecha'] = df_agrupado['fecha'].astype(str)
                        datos_finales = df_agrupado.to_dict('records')
                    except Exception as e:
                        print(f"Error agrupando fechas pandas: {e}")
                        datos_finales = []
                else:
                    # Si todas las fechas fallaron (ej. corpus antiguo 1605), agrupar por string de fecha (simple)
                    # Asumimos formato YYYY-MM-DD o YYYY
                    try:
                        # Extraer año como agrupación básica para histórico
                        df['anio'] = df['fecha'].astype(str).str[:4] 
                        df_agrupado = df.groupby('anio').agg({
                            'sentimiento': 'mean',
                            'subjetividad': 'mean',
                            'titulo': 'count'
                        }).reset_index()
                        df_agrupado.rename(columns={'anio': 'fecha', 'titulo': 'count'}, inplace=True)
                        datos_finales = df_agrupado.to_dict('records')
                    except Exception as e:
                         print(f"Error agrupando fechas fallback: {e}")
                         datos_finales = []

                
        return {
                    'exito': True,
                    'datos_temporales': datos_finales,
                    'datos_individuales': resultados,
                    'estadisticas': {
                        'promedio_sentimiento': float(df['sentimiento'].mean()),
                        'promedio_subjetividad': float(df['subjetividad'].mean()),
                        'mediana_sentimiento': float(df['sentimiento'].median()),
                        'mediana_subjetividad': float(df['subjetividad'].median()),
                        'total_documentos': len(df)
                    },
                    'tipo_eje': 'fecha'
                }
        
        
        return {'exito': False, 'error': 'No hay datos suficientes'}
    
    def _calcular_sentimiento(self, texto: str) -> Dict:
        """Calcula sentimiento usando TextBlob (soporte multilingüe)"""
        if not TextBlob:
            return {'polaridad': 0, 'subjetividad': 0.5}
        
        try:
            # TextBlob funciona mejor en inglés, pero detecta español también
            blob = TextBlob(texto)
            return {
                'polaridad': blob.sentiment.polarity,  # -1 (negativo) a 1 (positivo)
                'subjetividad': blob.sentiment.subjectivity  # 0 (objetivo) a 1 (subjetivo)
            }
        except:
            return {'polaridad': 0, 'subjetividad': 0.5}
    
    # ============================================
    # 2. TOPIC MODELING (LDA)
    # ============================================
    
    def topic_modeling_lda(self, publicaciones: List[Dict], n_topics: int = 5, n_words: int = 10) -> Dict:
        """
        Descubre tópicos latentes en el corpus usando LDA
        
        Args:
            publicaciones: Lista de documentos
            n_topics: Número de tópicos a extraer
            n_words: Palabras por tópico a mostrar
        
        Returns:
            Dict con tópicos y palabras clave
        """
        textos = []
        metadata = []
        
        for pub in publicaciones:
            texto = pub.get('contenido', '') or pub.get('titulo', '')
            if texto:
                # Limpiar HTML y preprocesar
                texto_limpio = self._preprocesar_texto(texto)
                if texto_limpio:  # Solo añadir si queda contenido después de limpiar
                    textos.append(texto_limpio)
                    metadata.append({
                        'id': pub.get('id'),
                        'titulo': pub.get('titulo', ''),
                        'fecha': pub.get('fecha')
                    })
        
        if len(textos) < n_topics:
            return {'exito': False, 'error': 'No hay suficientes documentos con contenido válido'}
        
        # Vectorización con CountVectorizer (mejor para LDA que TF-IDF)
        vectorizer = CountVectorizer(
            max_df=0.85,  # Ignorar palabras que aparecen en más del 85% de docs
            min_df=3,  # Palabra debe aparecer al menos en 3 documentos
            max_features=1000,
            token_pattern=r'\b[a-záéíóúñü]{3,}\b',  # Solo palabras de 3+ letras
            stop_words=list(self.stopwords_es)  # Filtrar stopwords
        )
        
        matriz = vectorizer.fit_transform(textos)
        nombres_features = vectorizer.get_feature_names_out()
        
        # Modelo LDA
        lda = LatentDirichletAllocation(
            n_components=n_topics,
            random_state=42,
            max_iter=20
        )
        lda.fit(matriz)
        
        # Extraer tópicos
        topicos = []
        for idx, topic in enumerate(lda.components_):
            top_palabras_idx = topic.argsort()[-n_words:][::-1]
            palabras = [(nombres_features[i], float(topic[i])) for i in top_palabras_idx]
            topicos.append({
                'id': idx + 1,
                'palabras': palabras
            })
        
        # Asignar documentos a tópicos
        doc_topic = lda.transform(matriz)
        for i, meta in enumerate(metadata):
            topico_dominante = int(doc_topic[i].argmax())
            meta['topico'] = topico_dominante + 1
            meta['probabilidad'] = float(doc_topic[i][topico_dominante])
        
        
        return {
            'exito': True,
            'topicos': topicos,
            'documentos': metadata,
            'n_topics': n_topics
        }
    
    # ============================================
    # 3. COOCURRENCIA DE ENTIDADES
    # ============================================
    
    def analisis_coocurrencia_entidades(self, publicaciones: List[Dict], min_coocurrencias: int = 2) -> Dict:
        """
        Analiza qué entidades aparecen juntas en los mismos documentos
        
        Args:
            publicaciones: Lista de documentos
            min_coocurrencias: Mínimo de coocurrencias para incluir
        
        Returns:
            Matriz de coocurrencias y red de relaciones
        """
        if not self.nlp:
            return {'exito': False, 'error': 'spaCy no disponible'}
        
        # Extraer entidades por documento
        documentos_entidades = []
        for pub in publicaciones:
            texto = pub.get('contenido', '') or pub.get('titulo', '')
            # Limpiar HTML antes de procesar
            texto = self._limpiar_html(texto)
            doc = self.nlp(texto[:100000])  # Límite de tokens
            entidades = list(set([ent.text for ent in doc.ents if ent.label_ in ['PER', 'LOC', 'ORG']]))
            if entidades:
                documentos_entidades.append({
                    'id': pub.get('id'),
                    'titulo': pub.get('titulo', ''),
                    'entidades': entidades
                })
        
        # Calcular coocurrencias
        coocurrencias = defaultdict(int)
        for doc in documentos_entidades:
            for ent1, ent2 in combinations(doc['entidades'], 2):
                par = tuple(sorted([ent1, ent2]))
                coocurrencias[par] += 1
        
        # Filtrar por mínimo
        coocurrencias_filtradas = {k: v for k, v in coocurrencias.items() if v >= min_coocurrencias}
        
        # Convertir a formato de red
        nodos = set()
        enlaces = []
        for (ent1, ent2), peso in coocurrencias_filtradas.items():
            nodos.add(ent1)
            nodos.add(ent2)
            enlaces.append({
                'source': ent1,
                'target': ent2,
                'value': peso
            })
        
        nodos_lista = [{'id': n, 'name': n} for n in nodos]
        
        
        return {
            'exito': True,
            'nodos': nodos_lista,
            'enlaces': enlaces,
            'total_coocurrencias': len(coocurrencias_filtradas)
        }
    
    # ============================================
    # 4. ANÁLISIS ESTILOMÉTRICO
    # ============================================
    
    def analisis_estilometrico(self, publicaciones: List[Dict]) -> Dict:
        """
        Analiza características estilísticas del corpus
        
        Returns:
            Estadísticas de estilo por documento y agregadas
        """
        resultados = []
        
        for pub in publicaciones:
            texto = pub.get('contenido', '') or pub.get('titulo', '')
            
            if not texto:
                continue
            
            # Limpiar HTML antes del análisis estilométrico
            texto = self._limpiar_html(texto)
            
            metricas = self._calcular_metricas_estilo(texto)
            metricas['id'] = pub.get('id')
            metricas['titulo'] = pub.get('titulo', '')
            metricas['publicacion'] = pub.get('publicacion', '')
            metricas['fecha'] = pub.get('fecha')
            
            resultados.append(metricas)
        
        if resultados:
            df = pd.DataFrame(resultados)
            estadisticas_globales = {
                'promedio_palabras': float(df['total_palabras'].mean()),
                'promedio_oraciones': float(df['total_oraciones'].mean()),
                'promedio_palabras_por_oracion': float(df['palabras_por_oracion'].mean()),
                'promedio_longitud_palabra': float(df['longitud_promedio_palabra'].mean()),
                'promedio_diversidad_lexica': float(df['diversidad_lexica'].mean())
            }
            
            
        return {
                'exito': True,
                'documentos': resultados,
                'estadisticas_globales': estadisticas_globales
            }
        
        
        return {'exito': False, 'error': 'No hay datos'}
    
    def _calcular_metricas_estilo(self, texto: str) -> Dict:
        """Calcula métricas estilométricas de un texto"""
        # Limpieza básica
        texto_limpio = re.sub(r'\s+', ' ', texto).strip()
        
        # Oraciones
        oraciones = re.split(r'[.!?]+', texto_limpio)
        oraciones = [o.strip() for o in oraciones if o.strip()]
        
        # Palabras
        palabras = re.findall(r'\b\w+\b', texto_limpio.lower())
        
        # Puntuación (todos los símbolos no alfanuméricos ni espacios)
        puntuacion = re.findall(r'[^\w\s]', texto_limpio)
        
        # Pronombres comunes (aproximación simple para estilométrico)
        pronombres = re.findall(r'\b(yo|tú|él|ella|nosotros|nosotras|vosotros|vosotras|ellos|ellas|me|te|se|nos|os|le|les|mi|tu|su|mío|tuyo|suyo|nuestro|vuestro)\b', texto_limpio.lower())
        
        # Métricas
        total_palabras = len(palabras)
        total_oraciones = len(oraciones)
        conteo_palabras = Counter(palabras)
        palabras_unicas = len(conteo_palabras)
        hapax_legomena = sum(1 for p in conteo_palabras if conteo_palabras[p] == 1)
        
        
        return {
            'total_palabras': total_palabras,
            'total_oraciones': total_oraciones,
            'palabras_por_oracion': total_palabras / max(total_oraciones, 1),
            'longitud_promedio_palabra': sum(len(p) for p in palabras) / max(total_palabras, 1),
            'diversidad_lexica': palabras_unicas / max(total_palabras, 1),  # TTR
            'palabras_unicas': palabras_unicas,
            'densidad_puntuacion': (len(puntuacion) / max(total_palabras, 1)) * 100,
            'ratio_hapax': hapax_legomena / max(total_palabras, 1),
            'ratio_pronombres': (len(pronombres) / max(total_palabras, 1)) * 100
        }
    
    # ============================================
    # 5. ANÁLISIS DE N-GRAMAS
    # ============================================
    
    def _calcular_zeta(self, texto_p: List[str], texto_resto: List[str]) -> List[str]:
        """
        Implementación de Burrows' Zeta (simplificada para personajes).
        Identifica palabras que un personaje usa de forma consistente pero el resto no.
        """
        if not texto_p or not texto_resto:
            return []
            
        # Dividir en segmentos (ej. cada intervención es un segmento o grupos de 100 palabras)
        def segmentar(lista_textos, chunk_size=5):
            return [ " ".join(lista_textos[i:i + chunk_size]) for i in range(0, len(lista_textos), chunk_size) ]
            
        seg_p = segmentar(texto_p)
        seg_r = segmentar(texto_resto)
        
        if not seg_p or not seg_r:
            return []
            
        # Vocabulario total (filtrando stopwords)
        vocab = set()
        for s in seg_p + seg_r:
            words = [w.lower() for w in re.findall(r'\b[a-záéíóúñü]{4,}\b', s) if w.lower() not in self.stopwords_es]
            vocab.update(words)
            
        zeta_scores = {}
        for word in vocab:
            # Porcentaje de segmentos donde aparece la palabra
            p_p = sum(1 for s in seg_p if word in s.lower()) / len(seg_p)
            p_r = sum(1 for s in seg_r if word in s.lower()) / len(seg_r)
            
            # Zeta Score = Presencia en P - Presencia en Resto
            # Favorece palabras que P usa en CASI TODAS sus intervenciones y los demás NO
            zeta_scores[word] = p_p - p_r
            
        # Retornar top 5 palabras con mayor Zeta (más distintivas)
        sorted_zeta = sorted(zeta_scores.items(), key=lambda x: x[1], reverse=True)
        return [w for w, score in sorted_zeta if score > 0.1][:5]

    def _calcular_correlacion(self, v1: List[float], v2: List[float]) -> float:
        """Calcula la correlación de Pearson entre dos vectores de sentimiento."""
        if len(v1) < 3 or len(v2) < 3: return 0.0
        try:
            # Pearson Correlation Coefficient
            mu1 = sum(v1) / len(v1)
            mu2 = sum(v2) / len(v2)
            
            num = sum((x - mu1) * (y - mu2) for x, y in zip(v1, v2))
            den1 = sum((x - mu1)**2 for x in v1)
            den2 = sum((y - mu2)**2 for y in v2)
            
            if den1 == 0 or den2 == 0: return 0.0
            return num / (den1 * den2)**0.5
        except:
            return 0.0

    def analizar_drama(self, obras_analizadas: List[Dict], reparto_identities: Dict = None) -> Dict:
        """
        Extrae los n-gramas más frecuentes del corpus
        
        Args:
            publicaciones: Lista de documentos
            n: Tamaño del n-grama (2=bigramas, 3=trigramas)
            top_k: Cantidad de n-gramas a retornar
        
        Returns:
            Lista de n-gramas con frecuencias
        """
        if not self.nlp:
            return self._analisis_ngramas_simple(publicaciones, n, top_k)
        
        ngramas_counter = Counter()
        
        for pub in publicaciones:
            texto = pub.get('contenido', '') or pub.get('titulo', '')
            # Limpiar HTML primero
            texto = self._limpiar_html(texto)
            # Optimización: nlp.make_doc solo tokeniza, evitando NER y Parser (más rápido y menos memoria)
            doc = self.nlp.make_doc(texto.lower())
            
            # Filtrar stopwords y puntuación (basado en tokens de spaCy)
            # Nota: is_stop y otros flags funcionan mejor con el doc completo, pero para n-gramas 
            # podemos usar una lógica simple basada en texto si solo tenemos tokens
            tokens = [token.text for token in doc if len(token.text) > 2 and token.text.isalpha() and token.text not in self.stopwords_es]
            
            # Generar n-gramas
            for i in range(len(tokens) - n + 1):
                ngrama = ' '.join(tokens[i:i+n])
                ngramas_counter[ngrama] += 1
        
        # Top K
        top_ngramas = ngramas_counter.most_common(top_k)
        
        
        return {
            'exito': True,
            'ngramas': [{'texto': ng, 'frecuencia': freq} for ng, freq in top_ngramas],
            'n': n,
            'total_unicos': len(ngramas_counter)
        }
    
    def _analisis_ngramas_simple(self, publicaciones: List[Dict], n: int, top_k: int) -> Dict:
        """Análisis de n-gramas sin spaCy (fallback)"""
        from nltk import word_tokenize, ngrams
        from string import punctuation
        
        ngramas_counter = Counter()
        
        for pub in publicaciones:
            texto = pub.get('contenido', '') or pub.get('titulo', '')
            # Limpiar HTML
            texto = self._limpiar_html(texto)
            palabras = [w.lower() for w in re.findall(r'\b\w+\b', texto) 
                       if w.lower() not in self.stopwords_es and len(w) > 2]
            
            for i in range(len(palabras) - n + 1):
                ngrama = ' '.join(palabras[i:i+n])
                ngramas_counter[ngrama] += 1
        
        top_ngramas = ngramas_counter.most_common(top_k)
        
        
        return {
            'exito': True,
            'ngramas': [{'texto': ng, 'frecuencia': freq} for ng, freq in top_ngramas],
            'n': n,
            'total_unicos': len(ngramas_counter)
        }
    
    # ============================================
    # 6. CLUSTERING DE DOCUMENTOS
    # ============================================
    
    def clustering_documentos(self, publicaciones: List[Dict], n_clusters: int = 5, metodo: str = 'kmeans') -> Dict:
        """
        Agrupa documentos similares automáticamente
        
        Args:
            publicaciones: Lista de documentos
            n_clusters: Número de clusters
            metodo: 'kmeans' o 'dbscan'
        
        Returns:
            Documentos con cluster asignado y coordenadas para visualización
        """
        textos = []
        metadata = []
        
        for pub in publicaciones:
            texto = pub.get('contenido', '') or pub.get('titulo', '')
            if texto:
                # Limpiar HTML antes del clustering
                texto_limpio = self._limpiar_html(texto)
                if texto_limpio:
                    textos.append(texto_limpio)
                    metadata.append({
                        'id': pub.get('id'),
                        'titulo': pub.get('titulo', ''),
                        'fecha': pub.get('fecha'),
                        'publicacion': pub.get('publicacion', '')
                    })
        
        if len(textos) < n_clusters:
            return {'exito': False, 'error': 'No hay suficientes documentos'}
        
        # Vectorización TF-IDF con stopwords
        vectorizer = TfidfVectorizer(
            max_df=0.85,
            min_df=3,
            max_features=500,
            token_pattern=r'\b[a-záéíóúñü]{3,}\b',
            stop_words=list(self.stopwords_es)
        )
        
        matriz = vectorizer.fit_transform(textos)
        
        # Clustering
        if metodo == 'kmeans':
            modelo = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        else:
            modelo = DBSCAN(eps=0.5, min_samples=2)
        
        clusters = modelo.fit_predict(matriz)
        
        # Reducción dimensional para visualización (t-SNE)
        tsne = TSNE(n_components=2, random_state=42, perplexity=min(30, len(textos)-1))
        coordenadas = tsne.fit_transform(matriz.toarray())
        
        # Combinar resultados
        for i, meta in enumerate(metadata):
            meta['cluster'] = int(clusters[i])
            meta['x'] = float(coordenadas[i][0])
            meta['y'] = float(coordenadas[i][1])
        
        # Calcular palabras clave por cluster
        cluster_keywords = self._extraer_keywords_clusters(matriz, clusters, vectorizer, n_clusters)
        
        
        return {
            'exito': True,
            'documentos': metadata,
            'n_clusters': n_clusters,
            'cluster_keywords': cluster_keywords
        }
    
    def _extraer_keywords_clusters(self, matriz, clusters, vectorizer, n_clusters, top_k=5):
        """Extrae palabras clave de cada cluster"""
        keywords = {}
        nombres_features = vectorizer.get_feature_names_out()
        
        for cluster_id in range(n_clusters):
            indices = [i for i, c in enumerate(clusters) if c == cluster_id]
            if not indices:
                continue
            
            # Promedio TF-IDF del cluster
            cluster_center = matriz[indices].mean(axis=0).A1
            top_indices = cluster_center.argsort()[-top_k:][::-1]
            keywords[cluster_id] = [nombres_features[i] for i in top_indices]
        
        return keywords
    
    # ============================================
    # 7. ANÁLISIS DE SIMILITUD ENTRE DOCUMENTOS
    # ============================================
    
    def documentos_similares(self, id_documento: int, publicaciones: List[Dict], top_k: int = 5) -> Dict:
        """
        Encuentra los documentos más similares a uno dado
        
        Args:
            id_documento: ID del documento de referencia
            publicaciones: Corpus completo
            top_k: Cantidad de similares a retornar
        
        Returns:
            Lista de documentos similares con scores
        """
        # Encontrar documento objetivo
        doc_objetivo = None
        doc_objetivo_idx = None
        
        for i, pub in enumerate(publicaciones):
            if pub.get('id') == id_documento:
                doc_objetivo = pub
                doc_objetivo_idx = i
                break
        
        if not doc_objetivo:
            return {'exito': False, 'error': 'Documento no encontrado'}
        
        # Vectorización con limpieza HTML
        textos = [self._limpiar_html(pub.get('contenido', '') or pub.get('titulo', '')) for pub in publicaciones]
        vectorizer = TfidfVectorizer(
            max_features=500,
            max_df=0.85,
            min_df=3,
            token_pattern=r'\b[a-záéíóúñü]{3,}\b'
        )
        matriz = vectorizer.fit_transform(textos)
        
        # Similitud coseno
        similitudes = cosine_similarity(matriz[doc_objetivo_idx], matriz)[0]
        
        # Top K (excluyendo el propio documento)
        indices_top = similitudes.argsort()[::-1][1:top_k+1]
        
        similares = []
        for idx in indices_top:
            pub = publicaciones[idx]
            similares.append({
                'id': pub.get('id'),
                'titulo': pub.get('titulo', ''),
                'fecha': pub.get('fecha'),
                'similitud': float(similitudes[idx])
            })
        
        
        return {
            'exito': True,
            'documento_referencia': {
                'id': doc_objetivo.get('id'),
                'titulo': doc_objetivo.get('titulo', '')
            },
            'similares': similares
        }
    
    # ============================================
    # 8. ANÁLISIS DE KEYNESS (DH EXPERIMENTAL)
    # ============================================
    
    def analisis_keyness(self, publicaciones: List[Dict], eje: str = 'publicacion', top_k: int = 15) -> Dict:
        """
        Compara frecuencias de palabras entre grupos (ej. periódicos) 
        para encontrar 'palabras clave' estadísticas (Log-Likelihood).
        """
        import math
        
        grupos = defaultdict(Counter)
        total_por_grupo = defaultdict(int)
        vocabulario_global = set()
        
        for pub in publicaciones:
            grupo_val = pub.get(eje, 'Desconocido') or 'Desconocido'
            texto = self._preprocesar_texto(pub.get('contenido', '') or pub.get('titulo', ''))
            palabras = texto.split()
            
            for p in palabras:
                grupos[grupo_val][p] += 1
                total_por_grupo[grupo_val] += 1
                vocabulario_global.add(p)
        
        if len(grupos) < 2:
            return {'exito': False, 'error': 'Se necesitan al menos 2 grupos para comparar.'}
        
        resultados = {}
        ll_total_global = sum(total_por_grupo.values())
        
        # Comparar cada grupo contra el resto (O1 vs O2)
        for g_nombre, g_counts in grupos.items():
            g_total = total_por_grupo[g_nombre]
            resto_total = ll_total_global - g_total
            
            keyness_scores = []
            for p in g_counts:
                o1 = g_counts[p]
                # Sumar frecuencias del resto
                o2 = sum(grupos[otro][p] for otro in grupos if otro != g_nombre)
                
                # E1 = N1 * (O1+O2) / (N1+N2)
                e1 = g_total * (o1 + o2) / ll_total_global
                e2 = resto_total * (o1 + o2) / ll_total_global
                
                # Log-Likelihood = 2 * (O1*ln(O1/E1) + O2*ln(O2/E2))
                ll = 0
                if o1 > 0 and e1 > 0: ll += o1 * math.log(o1/e1)
                if o2 > 0 and e2 > 0: ll += o2 * math.log(o2/e2)
                ll = 2 * ll
                
                # Signo: si o1 > e1 es una 'keyword', si o1 < e1 es una 'lockword'
                signo = 1 if o1 >= e1 else -1
                keyness_scores.append((p, ll * signo, o1))
            
            # Ordenar por LL y tomar top
            top_keywords = sorted(keyness_scores, key=lambda x: x[1], reverse=True)[:top_k]
            resultados[g_nombre] = [{'palabra': p, 'score': float(s), 'frecuencia': f} for p, s, f in top_keywords]
            
        
        return {
            'exito': True,
            'eje': eje,
            'resultados': resultados,
            'total_documentos': len(publicaciones)
        }

    # ============================================
    # 9. DETECCIÓN DE REUSO TEXTUAL (DH EXPERIMENTAL)
    # ============================================
    
    def deteccion_reuso_textual(self, publicaciones: List[Dict], n_gram_size: int = 5, min_matching_grams: int = 3) -> Dict:
        """
        Detecta fragmentos de texto compartidos entre noticias (noticias virales o copias).
        """
        def get_grams(text, n):
            words = text.lower().split()
            return [' '.join(words[i:i+n]) for i in range(len(words)-n+1)]

        fingerprints = {}
        for pub in publicaciones:
            texto = self._limpiar_html(pub.get('contenido', '') or pub.get('titulo', ''))
            if not texto: continue
            grams = set(get_grams(texto, n_gram_size))
            if grams:
                fingerprints[pub['id']] = {
                    'grams': grams,
                    'titulo': pub.get('titulo', ''),
                    'fecha': pub.get('fecha'),
                    'publicacion': pub.get('publicacion', '')
                }
        
        reusos = []
        ids = list(fingerprints.keys())
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                id1, id2 = ids[i], ids[j]
                interseccion = fingerprints[id1]['grams'].intersection(fingerprints[id2]['grams'])
                
                if len(interseccion) >= min_matching_grams:
                    reusos.append({
                        'doc1': {'id': id1, 'titulo': fingerprints[id1]['titulo'], 'publicacion': fingerprints[id1]['publicacion']},
                        'doc2': {'id': id2, 'titulo': fingerprints[id2]['titulo'], 'publicacion': fingerprints[id2]['publicacion']},
                        'coincidencias': len(interseccion),
                        'ejemplos': list(interseccion)[:3]
                    })
        
        
        return {
            'exito': True,
            'reusos': sorted(reusos, key=lambda x: x['coincidencias'], reverse=True)[:50]
        }

    # ============================================
    # 10. MAPA GEOSEMÁNTICO (DH EXPERIMENTAL)
    # ============================================
    
    def mapas_geosemanticos(self, publicaciones: List[Dict]) -> Dict:
        """
        Mapea tópicos a ubicaciones geográficas extraídas del texto.
        """
        from models import LugarNoticia
        
        # Primero necesitamos tópicos por documento
        topic_data = self.topic_modeling_lda(publicaciones, n_topics=5)
        if not topic_data['exito']:
            return topic_data
        
        # Mapear topicos a ubicaciones físicas guardadas
        geo_topics = defaultdict(lambda: Counter())
        pub_ids = [p['id'] for p in publicaciones]
        
        # Obtener todos los lugares extraídos para los documentos actuales (no borrados)
        lugares = LugarNoticia.query.filter(
            LugarNoticia.noticia_id.in_(pub_ids),
            LugarNoticia.borrado == False,
            LugarNoticia.lat.isnot(None)
        ).all()
        
        # Mapear IDs de documentos a sus tópicos dominantes
        doc_topics = {doc['id']: doc['topico'] for doc in topic_data['documentos']}
        
        for lugar in lugares:
            topico = doc_topics.get(lugar.noticia_id)
            if topico:
                # Usamos el nombre del lugar extraído del texto
                geo_topics[lugar.nombre][topico] += 1
        
        resultado_geo = []
        for ciudad, counts in geo_topics.items():
            # Obtener coordenadas de referencia para esta ciudad (del primer registro encontrado)
            ref_lugar = next((l for l in lugares if l.nombre == ciudad), None)
            if not ref_lugar: continue
            
            topico_principal = counts.most_common(1)[0][0]
            resultado_geo.append({
                'ciudad': ciudad,
                'lat': ref_lugar.lat,
                'lon': ref_lugar.lon,
                'topicos': dict(counts),
                'topico_dominante': topico_principal,
                'intensidad': sum(counts.values())
            })
            
        
        return {
            'exito': True,
            'geo_data': resultado_geo,
            'topicos': topic_data['topicos']
        }

    # ============================================
    # 11. SEMANTIC SHIFT (DH EXPERIMENTAL)
    # ============================================
    
    def semantic_shift_analysis(self, publicaciones: List[Dict], palabra_objetivo: str) -> Dict:
        """
        Analiza el cambio semántico de una palabra en diferentes subperiodos.
        """
        if not palabra_objetivo:
            return {'exito': False, 'error': 'Palabra objetivo no proporcionada.'}
            
        # Dividir por periodos (tercios del corpus)
        df = pd.DataFrame(publicaciones)
        if df.empty: 
            return {'exito': False}
        df['fecha'] = pd.to_datetime(df['fecha'])
        df = df.sort_values('fecha')
        
        # Dividir en 2 periodos mínimo
        n = len(df)
        periodos = [df.iloc[:n//2], df.iloc[n//2:]]
        labels = ['Periodo Inicial', 'Periodo Final']
        
        resultados_periodos = []
        for i, p_df in enumerate(periodos):
            textos = [self._preprocesar_texto(t) for t in p_df['contenido'].fillna('')]
            # Usar Tfidf para ver vecinos inmediatos (proxy simplificado de embedding para este MVP)
            try:
                cv = CountVectorizer(ngram_range=(1,1), stop_words=list(self.stopwords_es))
                dtm = cv.fit_transform(textos)
                # Co-ocurrencia simple con la palabra objetivo
                if palabra_objetivo.lower() in cv.vocabulary_:
                    idx = cv.vocabulary_[palabra_objetivo.lower()]
                    # Similitud de perfiles de co-ocurrencia
                    cooc = (dtm.T * dtm)
                    words = cv.get_feature_names_out()
                    vecinos_idx = cooc[idx].toarray()[0].argsort()[-11:][::-1]
                    vecinos = [words[j] for j in vecinos_idx if words[j] != palabra_objetivo.lower()][:10]
                    resultados_periodos.append({'label': labels[i], 'vecinos': vecinos})
            except:
                continue
                
        
        return {
            'exito': True,
            'palabra': palabra_objetivo,
            'periodos': resultados_periodos
        }

    # ============================================
    # 12. ANÁLISIS DE COMUNIDADES (DH EXPERIMENTAL)
    # ============================================
    
    def analisis_comunidades_agentes(self, publicaciones: List[Dict]) -> Dict:
        """
        Calcula métricas de red para el grafo de entidades y detecta 'brokers' de información.
        """
        red = self.analisis_coocurrencia_entidades(publicaciones, min_coocurrencias=2)
        if not red['exito']: return red
        
        # Simular centralidad de intermediación simple (Betweenness proxy)
        # En un grafo real usaríamos NetworkX, aquí haremos un recuento de conexiones únicas
        for nodo in red['nodos']:
            conexiones = [e for e in red['enlaces'] if e['source'] == nodo['id'] or e['target'] == nodo['id']]
            nodo['centralidad'] = len(conexiones)
            nodo['influencia'] = sum(e['value'] for e in conexiones)
            
        # Ordenar por influencia
        red['nodos'] = sorted(red['nodos'], key=lambda x: x['influencia'], reverse=True)
        
        return red


    # ============================================
    # 13. ANÁLISIS RETÓRICO (DH EXPERIMENTAL)
    # ============================================
    
    def analisis_retorica(self, publicaciones: List[Dict], eje_x: str = 'fecha') -> Dict:
        """
        Analiza recursos retóricos en textos periodísticos:
        1. Ironía (contraste sentimiento/marcadores)
        2. Metáforas bélicas (vocabulario militar en contextos no bélicos)
        3. Lenguaje emocional (intensidad emocional)
        
        Args:
            publicaciones: Lista de documentos
            
        Returns:
            Dict con análisis temporal de recursos retóricos
        """
        
        # Diccionarios de referencia
        MARCADORES_IRONIA = {
            'por supuesto', 'naturalmente', 'evidentemente', 'como era de esperar',
            'qué sorpresa', 'vaya', 'llamado', 'supuesto', 'pretendido',
            'así llamado', 'mal llamado', 'entre comillas', 'dizque'
        }
        
        VOCABULARIO_BELICO = {
            'guerra', 'batalla', 'combate', 'lucha', 'ataque', 'atacar',
            'defensa', 'defender', 'estrategia', 'táctica', 'victoria', 'derrota',
            'enemigo', 'aliado', 'frente', 'trinchera', 'bombardeo', 'bombardear',
            'invasión', 'invadir', 'conquista', 'conquistar', 'rendición', 'armisticio',
            'ofensiva', 'defensiva', 'campaña', 'asalto', 'sitio', 'cerco',
            'armas', 'arsenal', 'munición', 'tropas', 'soldados', 'ejército',
            'conflicto', 'hostilidades', 'beligerante'
        }
        
        # Contextos NO bélicos (si aparecen con vocabulario bélico = metáfora)
        CONTEXTOS_NO_BELICOS = {
            'económico', 'economía', 'comercial', 'comercio', 'mercado', 'empresa',
            'político', 'política', 'electoral', 'elección', 'partido', 'gobierno',
            'social', 'sociedad', 'cultural', 'cultura', 'deportivo', 'deporte',
            'debate', 'discusión', 'argumento', 'negociación'
        }
        
        PALABRAS_EMOCIONALES = {
            'alta_intensidad': {
                'terrible', 'espantoso', 'horroroso', 'atroz', 'monstruoso',
                'maravilloso', 'extraordinario', 'magnífico', 'espléndido',
                'catastrófico', 'desastroso', 'glorioso', 'sublime', 'excelso'
            },
            'media_intensidad': {
                'malo', 'bueno', 'triste', 'alegre', 'difícil', 'fácil',
                'importante', 'grave', 'serio', 'notable', 'considerable'
            },
            'intensificadores': {
                'muy', 'sumamente', 'extremadamente', 'increíblemente', 'terriblemente',
                'enormemente', 'profundamente', 'absolutamente', 'totalmente', 'completamente'
            }
        }
        
        resultados = []
        
        for pub in publicaciones:
            texto = pub.get('contenido', '') or pub.get('titulo', '')
            fecha = pub.get('fecha')
            
            if not texto or not fecha:
                continue
            
            # Limpiar HTML
            texto_limpio = self._limpiar_html(texto)
            texto_lower = texto_limpio.lower()
            
            # 1. DETECTOR DE IRONÍA
            # Buscar marcadores irónicos
            marcadores_encontrados = sum(1 for m in MARCADORES_IRONIA if m in texto_lower)
            
            # Calcular sentimiento
            sentimiento = self._calcular_sentimiento(texto_limpio)
            polaridad = sentimiento['polaridad']
            
            # Ironía = marcadores + polaridad extrema (muy positiva o muy negativa)
            # Score de ironía: combinación de marcadores y polaridad absoluta
            ironia_score = marcadores_encontrados * 0.3 + abs(polaridad) * 0.7
            
            # 2. DETECTOR DE METÁFORAS BÉLICAS
            palabras = re.findall(r'\b\w+\b', texto_lower)
            
            # Contar vocabulario bélico
            vocab_belico_count = sum(1 for p in palabras if p in VOCABULARIO_BELICO)
            
            # Contar contextos no bélicos
            contexto_no_belico_count = sum(1 for p in palabras if p in CONTEXTOS_NO_BELICOS)
            
            # Metáfora bélica = vocabulario bélico + contexto no bélico
            # Si hay contexto no bélico, es probable que sea metafórico
            metafora_belica_score = 0
            if vocab_belico_count > 0:
                if contexto_no_belico_count > 0:
                    # Es metáfora (vocabulario bélico en contexto no bélico)
                    metafora_belica_score = vocab_belico_count * 2
                else:
                    # Podría ser literal (guerra real)
                    metafora_belica_score = vocab_belico_count * 0.5
            
            # 3. DETECTOR DE LENGUAJE EMOCIONAL
            # Contar palabras emocionales por intensidad
            alta_int = sum(1 for p in palabras if p in PALABRAS_EMOCIONALES['alta_intensidad'])
            media_int = sum(1 for p in palabras if p in PALABRAS_EMOCIONALES['media_intensidad'])
            intensif = sum(1 for p in palabras if p in PALABRAS_EMOCIONALES['intensificadores'])
            
            # Score emocional: ponderado por intensidad
            emocional_score = (alta_int * 3) + (media_int * 1.5) + (intensif * 2)
            
            # Normalizar por longitud del texto (palabras cada 100 palabras)
            total_palabras = len(palabras) if palabras else 1
            factor_normalizacion = 100 / total_palabras
            
            resultados.append({
                'fecha': fecha,
                'titulo': pub.get('titulo', ''),
                'id': pub.get('id'),
                'ironia': round(ironia_score * factor_normalizacion, 4),
                'metafora_belica': round(metafora_belica_score * factor_normalizacion, 4),
                'lenguaje_emocional': round(emocional_score * factor_normalizacion, 4),
                'marcadores_ironia': marcadores_encontrados,
                'vocab_belico': vocab_belico_count,
                'palabras_emocionales': alta_int + media_int
            })
        
        # Agrupar por fecha y calcular promedios
        if resultados:
            df = pd.DataFrame(resultados)
            
            if eje_x == 'secuencia':
                # Ordenar por ID para secuencia lógica
                df.sort_values('id', inplace=True)
                
                # Crear etiquetas secuenciales
                df['etiqueta'] = [f"{i+1}. {t[:20]}..." for i, t in enumerate(df['titulo'])]
                df['indice'] = range(1, len(df) + 1)
                
                # Para visualización, usaremos el índice/título como eje X
                # IMPORTANTE: Eliminar columna fecha original para evitar duplicados al renombrar
                if 'fecha' in df.columns:
                    df.drop(columns=['fecha'], inplace=True)
                
                
                return {
                'exito': True,
                'datos_temporales': df.rename(columns={'etiqueta': 'fecha'}).to_dict('records'), # Reusamos campo 'fecha' para label X
                'datos_individuales': resultados,
                'estadisticas': {
                'promedio_ironia': float(df['ironia'].mean()),
                'promedio_metafora_belica': float(df['metafora_belica'].mean()),
                'promedio_lenguaje_emocional': float(df['lenguaje_emocional'].mean()),
                'mediana_ironia': float(df['ironia'].median()),
                'mediana_metafora_belica': float(df['metafora_belica'].median()),
                'mediana_lenguaje_emocional': float(df['lenguaje_emocional'].median()),
                'total_documentos': len(df),
                'max_ironia': float(df['ironia'].max()),
                'max_metafora': float(df['metafora_belica'].max()),
                'max_emocional': float(df['lenguaje_emocional'].max())
                },
                'tipo_eje': 'secuencia'
                }

            # EJE X = FECHA (COMPORTAMIENTO ORIGINAL)
            else:
                # Intentar convertir a datetime, coercing errores (fechas < 1677)
                # IMPORTANTE: Convertir a string primero para que 'coerce' funcione con objetos datetime.date antiguos
                df['fecha_str'] = df['fecha'].astype(str)
                df['fecha_dt'] = pd.to_datetime(df['fecha_str'], errors='coerce')
            
            # Separar fechas válidas
            df_validas = df.dropna(subset=['fecha_dt'])
            
            if len(df_validas) > 0:
                fecha_min = df_validas['fecha_dt'].min()
                fecha_max = df_validas['fecha_dt'].max()
                delta_dias = (fecha_max - fecha_min).days
                
                if delta_dias <= 60:
                    periodo = 'D'
                elif delta_dias <= 1095:
                    periodo = 'M'
                else:
                    periodo = 'Y'
                
                try:
                    df_agrupado = df_validas.groupby(df_validas['fecha_dt'].dt.to_period(periodo)).agg({
                        'ironia': 'mean',
                        'metafora_belica': 'mean',
                        'lenguaje_emocional': 'mean',
                        'titulo': 'count'
                    }).reset_index()
                    
                    df_agrupado.rename(columns={'fecha_dt': 'fecha', 'titulo': 'count'}, inplace=True)
                    df_agrupado['fecha'] = df_agrupado['fecha'].astype(str)
                    datos_finales = df_agrupado.to_dict('records')
                except Exception as e:
                    print(f"Error agrupando fechas retorica pandas: {e}")
                    datos_finales = []
            else:
                 # Fallback: Agrupar por AÑO (string) si todas las fechas son históricas
                try:
                    df['anio'] = df['fecha'].astype(str).str[:4]
                    df_agrupado = df.groupby('anio').agg({
                        'ironia': 'mean',
                        'metafora_belica': 'mean',
                        'lenguaje_emocional': 'mean',
                        'titulo': 'count'
                    }).reset_index()
                    df_agrupado.rename(columns={'anio': 'fecha', 'titulo': 'count'}, inplace=True)
                    datos_finales = df_agrupado.to_dict('records')
                except Exception as e:
                    print(f"Error agrupando fechas retorica fallback: {e}")
                    datos_finales = []
            
            
        return {
                'exito': True,
                'datos_temporales': datos_finales,
                'datos_individuales': resultados,
                'estadisticas': {
                    'promedio_ironia': float(df['ironia'].mean()),
                    'promedio_metafora_belica': float(df['metafora_belica'].mean()),
                    'promedio_lenguaje_emocional': float(df['lenguaje_emocional'].mean()),
                    'mediana_ironia': float(df['ironia'].median()),
                    'mediana_metafora_belica': float(df['metafora_belica'].median()),
                    'mediana_lenguaje_emocional': float(df['lenguaje_emocional'].median()),
                    'total_documentos': len(df),
                    'max_ironia': float(df['ironia'].max()),
                    'max_metafora': float(df['metafora_belica'].max()),
                    'max_emocional': float(df['lenguaje_emocional'].max())
                }
            }
        
        
        return {'exito': False, 'error': 'No hay datos suficientes'}

    # ============================================
    # UTILIDADES
    # ============================================
    
    # ============================================
    # 14. ANÁLISIS PERIODÍSTICO INTEGRAL (DH EXPERIMENTAL)
    # ============================================
    
    def analisis_periodistico(self, publicaciones: List[Dict], eje_x: str = 'fecha') -> Dict:
        """
        Análisis integral del discurso periodístico con 5 dimensiones:
        1. Modalidad lingüística (certeza/obligación)
        2. Polarización (nosotros vs. ellos)
        3. Sensacionalismo (dramatización)
        4. Voz y agencia (responsabilidad)
        5. Propaganda (técnicas persuasivas)
        
        Args:
            publicaciones: Lista de documentos
            
        Returns:
            Dict con análisis temporal de las 5 dimensiones
        """
        
        # ===== DICCIONARIOS DE REFERENCIA =====
        
        # 1. MODALIDAD LINGÜÍSTICA
        MODALIDAD_FUERTE = {
            'sin duda', 'claramente', 'evidentemente', 'ciertamente', 'indudablemente',
            'obviamente', 'definitivamente', 'absolutamente', 'categóricamente',
            'debe', 'tiene que', 'es necesario', 'hay que', 'obliga', 'obligatorio',
            'imperativo', 'imprescindible', 'fundamental', 'esencial'
        }
        
        MODALIDAD_DEBIL = {
            'quizás', 'probablemente', 'tal vez', 'posiblemente', 'parece',
            'aparentemente', 'supuestamente', 'presumiblemente', 'acaso',
            'podría', 'pudiera', 'sería', 'pareciera', 'puede que'
        }
        
        # 2. POLARIZACIÓN
        NOSOTROS = {
            'nosotros', 'nuestro', 'nuestra', 'nuestros', 'nuestras',
            'nacional', 'patria', 'compatriota', 'pueblo', 'ciudadano',
            'chileno', 'argentino', 'mexicano', 'peruano', 'colombiano',
            'comunidad', 'sociedad', 'país', 'nación'
        }
        
        ELLOS = {
            'ellos', 'enemigo', 'adversario', 'oponente', 'rival',
            'extranjero', 'ajeno', 'foráneo', 'externo', 'otro',
            'invasor', 'intruso', 'amenaza'
        }
        
        DIVISIVO = {
            'contra', 'versus', 'enfrentamiento', 'oposición', 'conflicto',
            'división', 'separación', 'ruptura', 'cisma', 'fractura',
            'antagonismo', 'hostilidad', 'rivalidad'
        }
        
        # 3. SENSACIONALISMO
        DRAMATIZACION = {
            'catástrofe', 'tragedia', 'escándalo', 'crisis', 'alarma',
            'desastre', 'calamidad', 'drama', 'horror', 'pánico',
            'terror', 'espanto', 'conmoción', 'impacto', 'shock'
        }
        
        SUPERLATIVOS = {
            'máximo', 'mínimo', 'enorme', 'gigantesco', 'diminuto',
            'inmenso', 'colosal', 'monumental', 'extraordinario',
            'increíble', 'asombroso', 'sorprendente', 'impresionante'
        }
        
        URGENCIA = {
            'urgente', 'inmediato', 'ahora', 'ya', 'hoy mismo',
            'rápido', 'pronto', 'cuanto antes', 'sin demora',
            'apremiante', 'perentorio', 'inaplazable'
        }
        
        # 4. VOZ Y AGENCIA
        PASIVA_MARKERS = {
            'fue', 'fueron', 'sido', 'se dice', 'se afirma', 'se cree',
            'se piensa', 'se considera', 'se estima', 'se reporta',
            'se informa', 'se sabe', 'se conoce'
        }
        
        NOMINALIZACION = {
            'destrucción', 'construcción', 'creación', 'eliminación',
            'transformación', 'modificación', 'realización', 'ejecución',
            'implementación', 'desarrollo', 'establecimiento'
        }
        
        # 5. PROPAGANDA
        APELACION_EMOCIONAL = {
            'miedo', 'temor', 'esperanza', 'orgullo', 'vergüenza',
            'honor', 'dignidad', 'humillación', 'gloria', 'deshonra',
            'valentía', 'cobardía', 'heroísmo', 'traición'
        }
        
        SIMPLIFICACION = {
            'simple', 'claro', 'obvio', 'evidente', 'sencillo',
            'fácil', 'elemental', 'básico', 'fundamental'
        }
        
        DEMONIZACION = {
            'malvado', 'perverso', 'corrupto', 'traidor', 'vil',
            'infame', 'despreciable', 'ruin', 'miserable', 'canalla',
            'criminal', 'delincuente', 'malhechor'
        }
        
        GLORIFICACION = {
            'heroico', 'noble', 'valiente', 'glorioso', 'ilustre',
            'virtuoso', 'honorable', 'digno', 'ejemplar', 'admirable',
            'excelso', 'sublime'
        }
        
        # ===== PROCESAMIENTO =====
        
        resultados = []
        
        for pub in publicaciones:
            texto = pub.get('contenido', '') or pub.get('titulo', '')
            fecha = pub.get('fecha')
            
            if not texto or not fecha:
                continue
            
            # Limpiar y preparar texto
            texto_limpio = self._limpiar_html(texto)
            texto_lower = texto_limpio.lower()
            palabras = re.findall(r'\b\w+\b', texto_lower)
            total_palabras = len(palabras) if palabras else 1
            
            # 1. MODALIDAD LINGÜÍSTICA
            modalidad_fuerte_count = sum(1 for m in MODALIDAD_FUERTE if m in texto_lower)
            modalidad_debil_count = sum(1 for m in MODALIDAD_DEBIL if m in texto_lower)
            
            # Score: diferencia entre fuerte y débil (positivo = más asertivo)
            modalidad_score = (modalidad_fuerte_count * 2) - (modalidad_debil_count * 1)
            
            # 2. POLARIZACIÓN
            nosotros_count = sum(1 for p in palabras if p in NOSOTROS)
            ellos_count = sum(1 for p in palabras if p in ELLOS)
            divisivo_count = sum(1 for p in palabras if p in DIVISIVO)
            
            # Score: suma ponderada de elementos polarizadores
            polarizacion_score = (nosotros_count * 1.5) + (ellos_count * 2) + (divisivo_count * 2.5)
            
            # 3. SENSACIONALISMO
            drama_count = sum(1 for p in palabras if p in DRAMATIZACION)
            super_count = sum(1 for p in palabras if p in SUPERLATIVOS)
            urgencia_count = sum(1 for p in palabras if p in URGENCIA)
            exclamaciones = texto.count('!')
            
            # Score: suma ponderada de elementos sensacionalistas
            sensacionalismo_score = (drama_count * 3) + (super_count * 2) + (urgencia_count * 2.5) + (exclamaciones * 1.5)
            
            # 4. VOZ Y AGENCIA
            pasiva_count = sum(1 for m in PASIVA_MARKERS if m in texto_lower)
            nominal_count = sum(1 for p in palabras if p in NOMINALIZACION)
            
            # Score: agencia difusa (más alto = menos agencia clara)
            # Invertimos para que alto = agencia clara
            agencia_difusa = (pasiva_count * 2) + (nominal_count * 1.5)
            agencia_score = max(0, 10 - agencia_difusa)  # Invertir escala
            
            # 5. PROPAGANDA
            emocional_count = sum(1 for p in palabras if p in APELACION_EMOCIONAL)
            simple_count = sum(1 for p in palabras if p in SIMPLIFICACION)
            demon_count = sum(1 for p in palabras if p in DEMONIZACION)
            glori_count = sum(1 for p in palabras if p in GLORIFICACION)
            
            # Score: suma ponderada de técnicas propagandísticas
            propaganda_score = (emocional_count * 2.5) + (simple_count * 1) + (demon_count * 3) + (glori_count * 2.5)
            
            # Normalizar por longitud (por cada 100 palabras)
            factor_normalizacion = 100 / total_palabras
            
            resultados.append({
                'fecha': fecha,
                'titulo': pub.get('titulo', ''),
                'id': pub.get('id'),
                'modalidad': round(modalidad_score * factor_normalizacion, 4),
                'polarizacion': round(polarizacion_score * factor_normalizacion, 4),
                'sensacionalismo': round(sensacionalismo_score * factor_normalizacion, 4),
                'agencia': round(agencia_score * factor_normalizacion, 4),
                'propaganda': round(propaganda_score * factor_normalizacion, 4)
            })
        
        # Agrupar por fecha y calcular promedios
        if resultados:
            df = pd.DataFrame(resultados)
            
            if eje_x == 'secuencia':
                # Ordenar por ID para secuencia lógica
                df.sort_values('id', inplace=True)
                
                # Crear etiquetas secuenciales
                df['etiqueta'] = [f"{i+1}. {t[:20]}..." for i, t in enumerate(df['titulo'])]
                df['indice'] = range(1, len(df) + 1)
                
                # Para visualización, usaremos el índice/título como eje X
                # IMPORTANTE: Eliminar columna fecha original para evitar duplicados al renombrar
                if 'fecha' in df.columns:
                    df.drop(columns=['fecha'], inplace=True)
                
                
                return {
                'exito': True,
                'datos_temporales': df.rename(columns={'etiqueta': 'fecha'}).to_dict('records'), # Reusamos campo 'fecha' para label X
                'datos_individuales': resultados,
                'estadisticas': {
                'promedio_modalidad': float(df['modalidad'].mean()),
                'promedio_polarizacion': float(df['polarizacion'].mean()),
                'promedio_sensacionalismo': float(df['sensacionalismo'].mean()),
                'promedio_agencia': float(df['agencia'].mean()),
                'promedio_propaganda': float(df['propaganda'].mean()),
                'mediana_modalidad': float(df['modalidad'].median()),
                'mediana_polarizacion': float(df['polarizacion'].median()),
                'mediana_sensacionalismo': float(df['sensacionalismo'].median()),
                'mediana_agencia': float(df['agencia'].median()),
                'mediana_propaganda': float(df['propaganda'].median())
                },
                'tipo_eje': 'secuencia'
                }
            
            # EJE X = FECHA (COMPORTAMIENTO ORIGINAL)
            else:
                # Intentar convertir a datetime, coercing errores (fechas < 1677)
                # IMPORTANTE: Convertir a string primero para que 'coerce' funcione con objetos datetime.date antiguos
                df['fecha_str'] = df['fecha'].astype(str)
                df['fecha_dt'] = pd.to_datetime(df['fecha_str'], errors='coerce')
            
            # Separar fechas válidas
            df_validas = df.dropna(subset=['fecha_dt'])
            
            if len(df_validas) > 0:
                fecha_min = df_validas['fecha_dt'].min()
                fecha_max = df_validas['fecha_dt'].max()
                delta_dias = (fecha_max - fecha_min).days
                
                if delta_dias <= 60:
                    periodo = 'D'
                elif delta_dias <= 1095:
                    periodo = 'M'
                else:
                    periodo = 'Y'
                
                try:
                    df_agrupado = df_validas.groupby(df_validas['fecha_dt'].dt.to_period(periodo)).agg({
                        'modalidad': 'mean',
                        'polarizacion': 'mean',
                        'sensacionalismo': 'mean',
                        'agencia': 'mean',
                        'propaganda': 'mean',
                        'titulo': 'count'
                    }).reset_index()
                    
                    df_agrupado.rename(columns={'fecha_dt': 'fecha', 'titulo': 'count'}, inplace=True)
                    df_agrupado['fecha'] = df_agrupado['fecha'].astype(str)
                    datos_finales = df_agrupado.to_dict('records')
                except Exception as e:
                    print(f"Error agrupando fechas retorica pandas: {e}")
                    datos_finales = []
            else:
                 # Fallback: Agrupar por AÑO (string) si todas las fechas son históricas
                try:
                    df['anio'] = df['fecha'].astype(str).str[:4]
                    df_agrupado = df.groupby('anio').agg({
                        'modalidad': 'mean',
                        'polarizacion': 'mean',
                        'sensacionalismo': 'mean',
                        'agencia': 'mean',
                        'propaganda': 'mean',
                        'titulo': 'count'
                    }).reset_index()
                    df_agrupado.rename(columns={'anio': 'fecha', 'titulo': 'count'}, inplace=True)
                    datos_finales = df_agrupado.to_dict('records')
                except Exception as e:
                    print(f"Error agrupando fechas retorica fallback: {e}")
                    datos_finales = []
            
            
        return {
                'exito': True,
                'datos_temporales': datos_finales,
                'datos_individuales': resultados,
                'estadisticas': {
                    'promedio_modalidad': float(df['modalidad'].mean()),
                    'promedio_polarizacion': float(df['polarizacion'].mean()),
                    'promedio_sensacionalismo': float(df['sensacionalismo'].mean()),
                    'promedio_agencia': float(df['agencia'].mean()),
                    'promedio_propaganda': float(df['propaganda'].mean()),
                    'mediana_modalidad': float(df['modalidad'].median()),
                    'mediana_polarizacion': float(df['polarizacion'].median()),
                    'mediana_sensacionalismo': float(df['sensacionalismo'].median()),
                    'mediana_agencia': float(df['agencia'].median()),
                    'mediana_propaganda': float(df['propaganda'].median()),
                    'total_documentos': len(df),
                    'max_modalidad': float(df['modalidad'].max()),
                    'max_polarizacion': float(df['polarizacion'].max()),
                    'max_sensacionalismo': float(df['sensacionalismo'].max()),
                    'max_agencia': float(df['agencia'].max()),
                    'max_propaganda': float(df['propaganda'].max())
                }
            }
        
        
        return {'exito': False, 'error': 'No hay datos suficientes'}


    # ============================================
    # 9. BRÚJULA DE RAREZAS (ANOMALY DETECTION)
    # ============================================
    
    def detectar_anomalias_geograficas(self, publicaciones: List[Dict], precision_geo: int = 3, top_k: int = 50, ai_service: Any = None) -> Dict:
        """
        Detecta ubicaciones donde el discurso es estadísticamente anómalo respecto al corpus global.
        
        Args:
            publicaciones: Lista de documentos con 'contenido', 'lat', 'lon'
            precision_geo: Decimales para agrupar lat/lon (3 ~= 100m, 2 ~= 1km)
            top_k: Número de puntos anómalos a retornar
            ai_service: (Opcional) Instancia de AIService para generar descripciones interpretativas
            
        Returns:
            Lista de puntos anómalos con su score de rareza, palabras clave y (opcional) explicación IA
        """
        import math
        
        # 1. Agrupar documentos por ubicación geográfica
        grupos_geo = defaultdict(list)
        corpus_global = []
        
        for pub in publicaciones:
            lat = pub.get('lat')
            lon = pub.get('lon')
            texto = pub.get('contenido', '') or pub.get('titulo', '')
            
            if lat is None or lon is None or not texto:
                continue
                
            # Limpieza básica
            texto_limpio = self._preprocesar_texto(texto)
            if not texto_limpio:
                continue
                
            # Agrupar por coordenadas redondeadas para consolidar puntos cercanos
            key = (round(float(lat), precision_geo), round(float(lon), precision_geo))
            grupos_geo[key].append(texto_limpio)
            corpus_global.append(texto_limpio)
            
        if not grupos_geo:
            return {'exito': False, 'error': 'No hay documentos geolocalizados suficientes'}

        # 2. Construir recuentos de palabras (Global)
        global_counts = Counter()
        for doc in corpus_global:
            global_counts.update(doc.split())
            
        total_global = sum(global_counts.values())
        if total_global == 0:
            return {'exito': False, 'error': 'Corpus global sin términos procesables'}
        
        anomalias = []
        
        # 3. Analizar rareza de cada ubicación
        for coords, docs_locales in grupos_geo.items():
            # Solo analizar si hay suficiente densidad local
            if len(docs_locales) < 1:
                continue
                
            local_counts = Counter()
            for doc in docs_locales:
                local_counts.update(doc.split())
            
            total_local = sum(local_counts.values())
            if total_local < 30: # Ignorar puntos con muy poco texto (ruido)
                continue
                
            # Calcular Keyness (Log-Likelihood) acumulado
            score_rareza_total = 0
            palabras_contribuyentes = []
            
            # Analizar tokens locales
            for palabra, count_local in local_counts.items():
                if count_local < 2: continue # Ignorar palabras que aparecen 1 sola vez (ruido)

                count_global = global_counts[palabra]
                
                # Expected frequency
                expected = total_local * (count_global / total_global)
                
                # Log-Likelihood: LL = 2 * O * ln(O/E)
                # Buscamos SOBRE-representación (O > E)
                if count_local > expected and expected > 0:
                    try:
                        ll = 2 * count_local * math.log(count_local / expected)
                        score_rareza_total += ll
                        palabras_contribuyentes.append((palabra, ll))
                    except:
                        pass
            
            # Ordenar palabras por cuánto contribuyen a la rareza
            palabras_contribuyentes.sort(key=lambda x: x[1], reverse=True)
            top_palabras = [p[0] for p in palabras_contribuyentes[:5]]
            
            if top_palabras and score_rareza_total > 5: # Threshold mínimo
                anomalia = {
                    'lat': coords[0],
                    'lon': coords[1],
                    'score': round(score_rareza_total, 2),
                    'palabras': top_palabras,
                    'volumen_docs': len(docs_locales)
                }
                anomalias.append(anomalia)
        
        # 4. Ordenar por score y filtrar
        anomalias.sort(key=lambda x: x['score'], reverse=True)
        anomalias_top = anomalias[:top_k]

        # 5. Generar descripciones IA para los hallazgos más importantes (Top 15)
        if ai_service and ai_service.is_configured():
            for i, anom in enumerate(anomalias_top[:15]):
                palabras_str = ", ".join(anom['palabras'])
                prompt = (
                    f"Analiza por qué este lugar destaca por estos términos: {palabras_str}. "
                    f"Responde con una sola frase muy corta (máximo 12 palabras), "
                    f"evitativa de formalismos, sugerente y directa."
                )
                try:
                    desc = ai_service.generate_content(prompt)
                    if desc:
                        anom['explicacion'] = desc.strip()
                        import logging
                        logging.info(f"AI Success Rareza: {anom['explicacion']}")
                except Exception as e:
                    import logging
                    logging.error(f"AI Error Rareza: {e}")
        
        
        return {
            'exito': True,
            'anomalias': anomalias_top,
            'total_puntos_analizados': len(grupos_geo)
        }

    def _normalizar_personaje(self, nombre):
        """Unifica nombres de personajes (D. -> DON, etc)"""
        if not nombre: return ""
        import re
        n = nombre.upper().strip()
        # Normalizar Don / Doña (D. / Dª)
        n = re.sub(r'^D\.\s+|^D\s+', 'DON ', n)
        n = re.sub(r'^Dª\.?\s*|^DA\.?\s+', 'DOÑA ', n)
        # Eliminar puntos finales
        n = n.replace('.', '').strip()
        # Colapsar múltiples espacios
        n = re.sub(r'\s+', ' ', n).strip()
        return n

    def _clasificar_tactica(self, texto):
        """Clasificador heurístico de tácticas dramáticas"""
        if not texto: return "Informar"
        t = texto.lower()
        
        # Pesos por categoría
        scores = {
            "Persuadir": 0,
            "Atacar": 0,
            "Seducir": 0,
            "Manipular": 0,
            "Informar": 1 # Base
        }
        
        # Persuadir: Razonamiento, ruegos, preguntas retóricas
        if re.search(r'\?|debe|razón|creo|entiende|escucha|por favor|conviene', t): scores["Persuadir"] += 2
        if re.search(r'si .* entonces', t): scores["Persuadir"] += 1
        
        # Atacar: Imperativos, insultos, exclamaciones
        if re.search(r'!|¡|traidor|miente|calla|vete|jamás|nunca|odio|muerte', t): scores["Atacar"] += 3
        if len(t.split()) < 5 and '!' in t: scores["Atacar"] += 2
        
        # Seducir: Adjetivación, términos afectuosos
        if re.search(r'amor|belleza|querida|dulce|hermosa|cielo|vida mía|corazón', t): scores["Seducir"] += 3
        if re.search(r'tan .* como', t): scores["Seducir"] += 1
        
        # Manipular: Condicionales, ambigüedad, apelación a terceros
        if re.search(r'si tú|tal vez|quizá|dicen que|alguien|podría|acaso', t): scores["Manipular"] += 2
        if re.search(r'no me digas|sabes que', t): scores["Manipular"] += 1
        
        # Ganador
        return max(scores, key=scores.get)

    def analisis_dramatico(self, publicaciones, manual_aliases=None, filtrado_activo=False):
        """
        Análisis de redes y tensión para textos teatrales.
        filtrado_activo: Si es True, se purgarán personajes con 0 palabras.
        """
        import re
        from collections import Counter, defaultdict
        
        def roman_to_int(s):
            if not s: return 0
            if isinstance(s, int): return s
            rom_val = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100, 'D': 500, 'M': 1000}
            int_val = 0
            s = str(s).upper().strip()
            # Eliminar prefijos comunes como 'ACTO ', 'ESCENA '
            s = re.sub(r'^(ACTO|ESCENA|CUADRO|A|E)\.?\s*', '', s)
            for i in range(len(s)):
                if s[i] in rom_val:
                    if i > 0 and rom_val[s[i]] > rom_val[s[i - 1]]:
                        int_val += rom_val[s[i]] - 2 * rom_val[s[i - 1]]
                    else:
                        int_val += rom_val[s[i]]
                else:
                    # Si no es romano, intentar ver si es número arábigo
                    try:
                        nums = re.findall(r'\d+', s)
                        return int(nums[0]) if nums else 0
                    except: return 0
            return int_val

        def natural_key(val):
            """Key para ordenar por texto (romano o arábigo) preservando consistencia ABSOLUTA de TIPOS (Python 3)"""
            if not val: return (0, 0)
            # Intentar romano/arábigo primero
            r = roman_to_int(val)
            if r > 0: return (0, r) # (0, int) -> Prioridad numérica
            # Fallback a natural sort de strings (1, [list of variants])
            # Forzamos que el primer elemento de la lista interna sea un string para evitar colisiones
            parts = [int(c) if c.isdigit() else c.lower() for c in re.split(r'(\d+)', str(val)) if c]
            return (1, parts) # (1, list) -> Segundo nivel
        
        personajes_detectados = set()
        obras_analizadas = []
        
        for pub in publicaciones:
            # Metadata: Reparto (palabras_clave)
            reparto_meta = pub.get('palabras_clave', '') or ''
            if reparto_meta:
                # Minimal normalization for detection to preserve variants in UI
                reparto_list = [p.upper().strip() for p in re.split(r'[,;]', reparto_meta) if p.strip()]
                personajes_detectados.update([p for p in reparto_list if len(p) > 1])
            
            contenido_raw = pub.get('contenido', '') or ''
            titulo = pub.get('titulo', 'Obra sin título')
            
            # LIMPIEZA DE HTML (Crucial para detección por línea ^)
            contenido = re.sub(r'<(?:p|br|div|h\d)[^>]*?>', '\n', contenido_raw)
            contenido = re.sub(r'<[^>]*?>', '', contenido)
            contenido = contenido.replace('&nbsp;', ' ').replace('&quot;', '"').replace('&apos;', "'")
            
            # Intentar detectar personajes por formato (NOMBRE: o NOMBRE.-)
            # Soporta espacios, múltiples signos de puntuación y nombres con aclaraciones (apartes)
            nombres_formato = re.findall(r'^\s*([A-ZÁÉÍÓÚÑ\. ]+(?:\s*\(.*?\))?)\s*[:\.\-]{1,3}', contenido, re.MULTILINE)
            personajes_detectados.update([n.upper().strip() for n in nombres_formato if len(n.strip()) > 1])
            
            # Fallback extraction: If section/volume are empty, try finding Roman/Arabic nuggets in Title or Keywords
            actos_val = pub.get('seccion')
            escenas_val = pub.get('volumen')
            
            if not actos_val:
                match_a = re.search(r'(?i)(?:ACTO|A)\.?\s*([IVXLCDM\d]+)\b', f"{titulo} {reparto_meta}")
                if match_a: actos_val = match_a.group(1).upper()
            
            if not escenas_val:
                match_e = re.search(r'(?i)(?:ESCENA|E)\.?\s*([IVXLCDM\d]+)\b', f"{titulo} {reparto_meta}")
                if match_e: escenas_val = match_e.group(1).upper()

            obras_analizadas.append({
                'id': pub.get('id'),
                'titulo': titulo,
                'publicacion': pub.get('publicacion', 'Sin obra'),
                'publicacion_id': pub.get('publicacion_id'),
                'contenido': contenido,
                'actos': actos_val,
                'escenas': escenas_val,
                'personajes_meta': reparto_meta
            })
            
        if not obras_analizadas:
            return {'error': 'No hay contenido para analizar'}

        # ORDENACIÓN CRÍTICA: Asegurar flujo narrativo (Actos y Escenas)
        obras_analizadas.sort(key=lambda x: (natural_key(x['publicacion']), natural_key(x['actos']), natural_key(x['escenas'])))

        nodos = []
        enlaces = []
        tension_dramatica = []
        protagonismo = Counter()
        
        # Filtro de ruido y UNIFICACIÓN DE ALIAS
        stop_personajes = {
            'ACTO', 'ESCENA', 'CUADRO', 'TELÓN', 'TELON', 'PERSONAJES', 'REPARTO', 'FIN', 'ESCENAS', 'ACTOS',
            'ENTRAN', 'SALEN', 'VÁSE', 'VASE', 'MUTACIÓN', 'MUTACION', 'ESCENARIO', 'TEATRO', 'DENTRO', 
            'TODOS', 'TODAS', 'VOCES', 'OTRO', 'OTRA', 'RUIDO', 'MÚSICA', 'MUSICA', 'PAUSA', 'SILENCIO',
            'SALA', 'SALÓN', 'SALON', 'CALLE', 'PATIO', 'JARDÍN', 'JARDIN', 'CON EL MISMO', 'CON LA MISMA'
        }
        personajes_limpios = sorted([p for p in personajes_detectados if p.upper() not in stop_personajes])
        
        # --- UNIFICACIÓN DE ALIAS ROBUSTA ---
        # 1. Función de resolución recursiva
        def resolver_alias(nombre_original, mapa_aliases):
            visitados = set()
            actual = nombre_original
            while actual in mapa_aliases and actual not in visitados:
                visitados.add(actual)
                actual = mapa_aliases[actual]
            return actual

        # 2. Construir mapa de aliases
        aliases = {}
        
        # A. Normalización automática base
        for p in personajes_limpios:
            norm = self._normalizar_personaje(p)
            if norm != p:
                aliases[p] = norm
        
        # B. Aplicar alias manuales (Sobrescriben y extienden)
        if manual_aliases:
            for k, v in manual_aliases.items():
                if not k or not v: continue
                
                k_norm = self._normalizar_personaje(k)
                v_norm = self._normalizar_personaje(v)
                
                # Mapeamos tanto la forma original como la normalizada al destino
                aliases[k.upper().strip()] = v_norm
                if k_norm != k.upper().strip():
                    aliases[k_norm] = v_norm
        
        # 3. Recalcular personajes finales unificados
        personajes_finales_temp = set()
        for p in personajes_limpios:
            canonical = resolver_alias(p, aliases)
            personajes_finales_temp.add(canonical)
        
        personajes_finales = sorted(list(personajes_finales_temp))
        
        # DEBUG: Log final aliases
        if manual_aliases:
            print(f"[DEBUG] Dramático - Mapa de Aliases consolidado: {json.dumps(aliases, ensure_ascii=False)}")
            print(f"[DEBUG] Dramático - Personajes finales: {personajes_finales}")

        
        # Matriz de co-ocurrencia y Stats por personaje
        coocurrencias = defaultdict(int)
        
        # --- MAPEO DE VARIANTES A CANÓNICOS ---
        # Mapeamos cada variante (ej: "D. DIEGO") a su nombre canónico ("DON DIEGO")
        mapeo_variantes = defaultdict(set)
        
        # Mapa de roles para resolución inteligente (ej: si en reparto hay "LA VIUDA", "VIUDA" de diálogo apunta allí)
        mapa_roles_inteligente = {}
        for p_cat in personajes_finales:
            norm_cat = p_cat.upper().strip()
            # Si el nombre es largo (ej. "LA VIUDA DE ROQUE"), añadimos sus partes como posibles roles si no son ambiguos
            palabras_nombre = [w for w in re.split(r'[\s\.]+', norm_cat) if len(w) > 3]
            for w in palabras_nombre:
                if w not in mapa_roles_inteligente:
                    mapa_roles_inteligente[w] = p_cat
                else:
                    # Ambigüedad: si ya existe, lo marcamos como None para no auto-resolverlo
                    if mapa_roles_inteligente[w] != p_cat:
                        mapa_roles_inteligente[w] = None

        for p_original in personajes_detectados:
            canonical = resolver_alias(p_original, aliases)
            if canonical in personajes_finales:
                mapeo_variantes[canonical].add(p_original.upper().strip())
                norm = self._normalizar_personaje(p_original)
                mapeo_variantes[canonical].add(norm)

        # Mapeo de personajes a su primera publicación (para colores)
        personaje_a_grupo = {}
        
        # Pre-inicializar stats para TODOS los personajes finales detectados
        personajes_stats = {
            p: {
                'texto': [], 
                'palabras': 0, 
                'intervenciones': 0, 'palabras': 0, 'tacticas': Counter(),
                'presencia_por_bloque': [],
                'sentimiento_por_bloque': []
            } for p in personajes_finales
        }
        
        for obra in obras_analizadas:
            contenido_raw = obra['contenido']
            # Re-limpiar por si acaso (obras_analizadas guarda el contenido original)
            texto = re.sub(r'<(?:p|br|div|h\d)[^>]*?>', '\n', contenido_raw)
            texto = re.sub(r'<[^>]*?>', '', texto)
            texto = texto.replace('&nbsp;', ' ').replace('&quot;', '"').replace('&apos;', "'")
            # Dividir por escenas/actos si hay marcadores internos (regex mejorada)
            bloques_raw = re.split(r'(?i)(?:ACTO|ESCENA|CUADRO)\s+[IVXLCDM\d]+', texto)
            bloques_candidatos = [b for b in bloques_raw if b and len(b.strip()) > 15]
            
            # Decidir estrategia de granularidad
            if len(bloques_candidatos) > 1:
                # Si hay marcadores internos, los usamos
                bloques = bloques_candidatos
            elif len(obras_analizadas) > 1:
                # Si estamos analizando varias publicaciones/escenas, cada una es un bloque único
                bloques = [texto]
            else:
                # Si es una única obra y no tiene marcadores, dividimos por párrafos con un umbral de ruido
                bloques = [b for b in texto.split('\n\n') if len(b.strip()) > 50]
                
            for idx, bloque in enumerate(bloques):
                # Sentiment del bloque
                sent_bloque = self._calcular_sentimiento(bloque)
                # Etiquetado inteligente
                # Etiquetado inteligente (con soporte para nulos y limpieza)
                acto_raw = obra.get('actos')
                escena_raw = obra.get('escenas')
                acto = str(acto_raw).strip() if acto_raw not in [None, 'None', ''] else ''
                escena = str(escena_raw).strip() if escena_raw not in [None, 'None', ''] else ''
                
                if acto and escena:
                    label_bloque = f"A.{acto} E.{escena}"
                elif escena:
                    label_bloque = f"Esc.{escena}"
                elif acto:
                    label_bloque = f"Act.{acto}"
                else:
                    label_bloque = f"Esc.{idx+1}" if len(bloques) > 1 else obra['titulo'][:15]
                
                # Extraer locuciones para este bloque (diálogos) con regex robusta
                # Soporta multi-línea, varios formatos de guion y aclaraciones en el nombre (apartes)
                regex_loc = r'^\s*([A-ZÁÉÍÓÚÑ\. ]+(?:\s*\(.*?\))?)\s*[:\.\-]{1,3}\s*(.*?)((?=\n\s*[A-ZÁÉÍÓÚÑ\. ]+(?:\s*\(.*?\))?\s*[:\.\-]{1,3})|\Z)'
                matches_loc = list(re.finditer(regex_loc, bloque, re.MULTILINE | re.DOTALL))
                
                presentes_en_bloque = set()
                sentimiento_locuciones_bloque = defaultdict(list)
                locuciones_data = [] # Para el panel de contexto frontend

                for m in matches_loc:
                    # Limpieza del nombre (quitar apartes entre paréntesis) y resolución de alias
                    raw_p = re.sub(r'\(.*?\)', '', m.group(1)).upper().strip()
                    raw_p = re.sub(r'[^A-ZÁÉÍÓÚÑ ]', '', raw_p).strip()
                    nombre_p = resolver_alias(raw_p, aliases)
                    
                    if nombre_p not in personajes_finales:
                        norm_p = self._normalizar_personaje(raw_p)
                        nombre_p = resolver_alias(norm_p, aliases)
                        if nombre_p not in personajes_finales and norm_p in mapa_roles_inteligente:
                            nombre_p = mapa_roles_inteligente[norm_p]

                    # UNIFICACIÓN DEFINITIVA
                    p_final = self.find_identity(nombre_p, reparto_identities) if 'reparto_identities' in locals() else nombre_p
                    
                    if p_final in personajes_finales:
                        texto_p = m.group(2).strip()
                        presentes_en_bloque.add(p_final)
                        personajes_stats[p_final]['texto'].append(texto_p)
                        personajes_stats[p_final]['intervenciones'] += 1
                        personajes_stats[p_final]['palabras'] += len(re.findall(r'\b\w+\b', texto_p))
                        
                        sent_loc = self._calcular_sentimiento(texto_p)
                        sentimiento_locuciones_bloque[p_final].append(sent_loc['polaridad'])
                        
                        # Guardar para el panel de contexto (mismo nombre que la gráfica)
                        tactic = self._clasificar_tactica(texto_p)
                        locuciones_data.append({'p': p_final, 't': texto_p, 'tac': tactic})
                        personajes_stats[p_final]['tacticas'][tactic] += 1

                # Ahora sí, guardamos la tensión dramática con los datos sincronizados
                tension_dramatica.append({
                    'label': label_bloque,
                    'sentimiento': sent_bloque['polaridad'],
                    'subjetividad': sent_bloque['subjetividad'],
                    'titulo_obra': obra['publicacion'],
                    'publicacion_id': obra['publicacion_id'],
                    'doc_id': obra['id'],
                    'acto': acto,
                    'escena': escena,
                    'texto': bloque,
                    'locuciones': locuciones_data
                })

                # Incrementar protagonismo global (basado únicamente en intervenciones reales)
                for p in presentes_en_bloque:
                    protagonismo[p] += 1
                
                # Co-ocurrencias para la red y el heatmap
                presentes_list = list(presentes_en_bloque)
                if len(presentes_list) >= 2:
                    for i in range(len(presentes_list)):
                        for j in range(i + 1, len(presentes_list)):
                            par = tuple(sorted([presentes_list[i], presentes_list[j]]))
                            coocurrencias[par] += 1
                            
                # Guardar presencia y sentimiento detallado por bloque (Sincronizado)
                # Extraer acotaciones (texto que no es diálogo)
                acotaciones_bloque = re.sub(r'^\s*[A-ZÁÉÍÓÚÑ\. ]{2,30}\s*[:\.\-]{1,3}\s*.*', '', bloque, flags=re.MULTILINE).strip()
                sent_acotaciones = self._calcular_sentimiento(acotaciones_bloque) if acotaciones_bloque else None

                for p in personajes_finales:
                    if p in presentes_en_bloque:
                        personajes_stats[p]['presencia_por_bloque'].append(1)
                        sents = sentimiento_locuciones_bloque.get(p, [])
                        avg_sent = sum(sents)/len(sents) if sents else sent_bloque['polaridad']
                        personajes_stats[p]['sentimiento_por_bloque'].append(avg_sent)
                    else:
                        personajes_stats[p]['presencia_por_bloque'].append(0)
                        personajes_stats[p]['sentimiento_por_bloque'].append(None) # No presente
                
                # Guardar info de bloque para análisis de ritmo y acotaciones
                if 'ritmo_bloques' not in locals(): ritmo_bloques = []
                
                # Densidad y Dinamismo
                total_palabras_bloque = sum(len(re.findall(r'\b\w+\b', m.group(2))) for m in matches_loc)
                dinamismo = len(matches_loc) / (total_palabras_bloque / 100) if total_palabras_bloque > 0 else 0
                
                ritmo_bloques.append({
                    'label': label_bloque,
                    'intervenciones': len(matches_loc),
                    'palabras': total_palabras_bloque,
                    'dinamismo': round(dinamismo, 2),
                    'sent_acotaciones': sent_acotaciones['polaridad'] if sent_acotaciones else 0,
                    'texto_acotaciones': acotaciones_bloque[:200]
                })

        # Finalizar Stats Detallados
        detalles_reparto = []
        for p in personajes_finales:
            if p in personajes_stats:
                s = personajes_stats[p]
                texto_unido = " ".join(s['texto'])
                palabras_f = [w.lower() for w in re.findall(r'\b[a-záéíóúñü]{3,}\b', texto_unido) if w.lower() not in self.stopwords_es]
                
                # Extraer frases más repetidas (Trigramas y Bigramas)
                texto_limpio_frases = re.sub(r'[^\w\s]', ' ', texto_unido.lower())
                tokens_frases = texto_limpio_frases.split()
                
                trigramas = [" ".join(tokens_frases[i:i+3]) for i in range(len(tokens_frases)-2)]
                bigramas = [" ".join(tokens_frases[i:i+2]) for i in range(len(tokens_frases)-1)]
                


                def es_frase_relevante(f):
                    words = f.split()
                    if len(words) < 2: return False
                    if all(w in self.stopwords_es for w in words): return False
                    if len(f) < 8: return False
                    return True
                
                all_ngrams = trigramas + bigramas

                # Vocabulario dominante con frecuencias
                word_counts = Counter(palabras_f).most_common(10)
                top_words = [{'term': w, 'count': c} for w, c in word_counts]
                
                # Frases más repetidas con frecuencias
                all_ngrams_counts = Counter(all_ngrams).most_common(60)
                top_frases_data = []
                for f, count in all_ngrams_counts:
                    if es_frase_relevante(f):
                        top_frases_data.append({'term': f, 'count': count})
                top_frases = top_frases_data[:5]
                
                # Métricas Avanzadas: Distinctiveness (Burrows' Zeta)
                texto_resto = []
                for op in personajes_finales:
                    if op != p:
                        texto_resto.extend(personajes_stats[op]['texto'])
                
                distinctive_words = self._calcular_zeta(s['texto'], texto_resto)

                detalles_reparto.append({
                    'nombre': p,
                    'palabras': s['palabras'],
                    'intervenciones': s['intervenciones'],
                    'palabras_por_intervencion': round(s['palabras'] / s['intervenciones'], 1) if s['intervenciones'] > 0 else 0,
                    'top_words': top_words,
                    'distinctive_words': distinctive_words,
                    'top_frases': top_frases,
                    'presencia_matriz': s['presencia_por_bloque'],
                    'sentimiento_arc': s['sentimiento_por_bloque'], 'perfil_tactico': s['tacticas']
                })
        
        # Sincronía Emocional (Correlación de Arcos)
        sincronia_pares = []
        for i in range(len(detalles_reparto)):
            for j in range(i + 1, len(detalles_reparto)):
                p1 = detalles_reparto[i]
                p2 = detalles_reparto[j]
                arc1 = [v for v in p1['sentimiento_arc'] if v is not None]
                arc2 = [v for v in p2['sentimiento_arc'] if v is not None]
                # Correlación real si coinciden en suficientes bloques
                if len(arc1) > 3 and len(arc2) > 3:
                    # Encontrar bloques comunes
                    comunes = [(p1['sentimiento_arc'][k], p2['sentimiento_arc'][k]) 
                               for k in range(len(p1['sentimiento_arc'])) 
                               if p1['sentimiento_arc'][k] is not None and p2['sentimiento_arc'][k] is not None]
                    
                    if len(comunes) > 3:
                        v1 = [c[0] for c in comunes]
                        v2 = [c[1] for c in comunes]
                        corr = self._calcular_correlacion(v1, v2)
                        
                        sincronia_pares.append({
                            'p1': p1['nombre'],
                            'p2': p2['nombre'],
                            'score': round(corr, 2)
                        })

        # Purgar personajes sin intervenciones reales (Filtrado estricto de ruido post-análisis)
        detalles_reparto = [d for d in detalles_reparto if d['intervenciones'] > 0]
        nombres_activos = set([d['nombre'] for d in detalles_reparto])
        personajes_finales = [p for p in personajes_finales if p in nombres_activos]

        # Ordenar reparto por volumen de palabras
        detalles_reparto.sort(key=lambda x: x['palabras'], reverse=True)

        # Formatear Red (Vis.js)
        nodos = []
        enlaces = []
        for p in personajes_finales:
            if protagonismo[p] > 0:
                nodos.append({
                    'id': p,
                    'name': p,
                    'influencia': protagonismo[p],
                    'grupo': personaje_a_grupo.get(p, 0)
                })
                
        # Matriz de interacciones para Heatmap (p1, p2, value)
        interacciones_heatmap = []
        personajes_validos = set(personajes_finales)
        for (p1, p2), peso in coocurrencias.items():
            if p1 in personajes_validos and p2 in personajes_validos:
                enlaces.append({
                    'source': p1,
                    'target': p2,
                    'value': peso
                })
                interacciones_heatmap.append({
                    'p1': p1,
                    'p2': p2,
                    'valor': peso
                })
            
        

        # Cálculo del flujo táctico (Streamgraph)
        flujo_tactico = []
        for idx, s in enumerate(tension_dramatica):
            counts = Counter([l.get('tac', 'Informar') for l in s['locuciones']])
            for tac, count in counts.items():
                flujo_tactico.append({
                    'Bloque': s['label'],
                    'Táctica': tac,
                    'Valor': count
                })
        return {
            'exito': True,
            'nodos': nodos,
            'enlaces': enlaces,
            'sentimiento_temporal': tension_dramatica,
            'reparto_detalle': detalles_reparto,
            'interacciones_heatmap': interacciones_heatmap,
            'personajes': sorted(protagonismo.items(), key=lambda x: x[1], reverse=True)[:15],
            'total_personajes': len(nodos),
            'metricas_avanzadas': {
                'ritmo_bloques': ritmo_bloques if 'ritmo_bloques' in locals() else [],
                'sincronia_pares': sincronia_pares if 'sincronia_pares' in locals() else [],
                'flujo_tactico': flujo_tactico
            }
        }


