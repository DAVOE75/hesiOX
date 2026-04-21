# Búsqueda Semántica con Deep Learning - Guía de Uso

## 🎯 Descripción

HESIOX ahora incluye **búsqueda semántica real** basada en **embeddings de modelos de lenguaje de última generación**, no solo TF-IDF. Esto permite encontrar documentos conceptualmente relacionados incluso cuando no comparten palabras exactas.

## 🧠 ¿Qué son los Embeddings Semánticos?

Los embeddings son **vectores numéricos de alta dimensionalidad** (768-3072 dimensiones) que representan el significado profundo de un texto:

- **OpenAI text-embedding-3-small**: 1536 dimensiones
- **OpenAI text-embedding-3-large**: 3072 dimensiones  
- **Google text-embedding-004**: 768 dimensiones

Ejemplo real de tu problema:
```
Query: "embarque clandestino"
Documento sin las palabras exactas: "...personas que intentaban cruzar 
la frontera de manera irregular sin documentación..."

Con TF-IDF: ❌ No encuentra (0% coincidencia)
Con Embeddings: ✅ Encuentra (85% similitud semántica)
```

## 📋 Configuración Inicial

### 1. Configurar API Keys

Añade tus API keys en tu perfil de usuario:

- **OpenAI**: `api_key_openai`
- **Google Gemini**: `api_key_gemini`

El sistema prioriza tus keys personales sobre las del entorno.

### 2. Generar Embeddings para tu Corpus

**IMPORTANTE**: Antes de usar la búsqueda por embeddings, debes generar los vectores para tus noticias:

```bash
# Activar entorno virtual
cd /opt/hesiox
source venv/bin/activate

# Opción 1: Generar embeddings con OpenAI (pequeño, rápido)
python generar_embeddings.py --modelo openai-small --batch-size 50

# Opción 2: Generar embeddings con OpenAI (grande, mejor calidad)
python generar_embeddings.py --modelo openai-large --batch-size 20

# Opción 3: Generar embeddings con Google (gratuito hasta cierto límite)
python generar_embeddings.py --modelo google --batch-size 50

# Solo procesar 100 documentos (prueba)
python generar_embeddings.py --modelo openai-small --limite 100
```

**Estimación de costos** (con OpenAI):
- openai-small: ~$0.02 por millón de tokens
- openai-large: ~$0.13 por millón de tokens
- Corpus de 1000 noticias ≈ 500k tokens ≈ $0.01-$0.07

**Tiempo estimado**:
- Google: ~5-10 docs/seg (gratuito)
- OpenAI: ~20-30 docs/seg

### 3. Monitoreo del Proceso

El script muestra progreso en tiempo real:

```
🧠 GENERADOR DE EMBEDDINGS SEMÁNTICOS
======================================================================
Modelo: text-embedding-3-small
Dimensiones: 1536
Proveedor: OPENAI
Costo estimado: $0.0200 por millón de tokens
======================================================================

📊 Noticias pendientes: 871
📊 Noticias a procesar: 871

⚠️  Se generarán 871 embeddings
💰 Costo estimado: ~$0.0087 USD

¿Continuar? (s/n): s

🚀 Iniciando generación de embeddings...

✓ 50/871 | Velocidad: 25.3 docs/seg | Tiempo restante: ~0min 32s
✓ 100/871 | Velocidad: 26.1 docs/seg | Tiempo restante: ~0min 29s
...
```

## 🔍 Uso del Buscador Semántico

### Modo TF-IDF (Tradicional)

**Sin activar IA**: Usa TF-IDF estadístico (rápido pero limitado)

```
1. Ir a "Buscador Semántico"
2. NO activar el switch "Potenciador IA"
3. Escribir consulta
4. Obtener resultados basados en palabras clave
```

### Modo Deep Learning (Embeddings)

**Con IA activada**: Usa vectores semánticos reales

```
1. Ir a "Buscador Semántico"
2. ✅ Activar el switch "Potenciador IA"
3. Seleccionar modelo:
   - Gemini 2.0 Flash → Usa embeddings de Google
   - GPT-4o → Usa embeddings de OpenAI
   - Claude 3.5 → Usa embeddings de OpenAI (fallback)
4. Escribir consulta conceptual
5. Obtener resultados por similitud semántica REAL
```

## 📊 Ejemplos de Búsqueda

### Caso 1: Embarques Clandestinos

**Query**: "embarque clandestino"

**Documentos encontrados** (incluso sin las palabras exactas):
- "migración irregular"
- "cruce fronterizo sin documentación"
- "tráfico de personas"
- "contrabando humano"
- "paso ilegal de fronteras"

### Caso 2: Crisis Económica

**Query**: "crisis económica"

**Documentos encontrados**:
- "recesión financiera"
- "colapso bursátil"
- "desempleo masivo"
- "inflación galopante"
- "quiebra de bancos"

### Caso 3: Conflictos Bélicos

**Query**: "guerra civil"

**Documentos encontrados**:
- "conflicto armado interno"
- "enfrentamientos entre facciones"
- "insurrección militar"
- "revuelta popular violenta"

## ⚙️ Configuración Avanzada

### Filtros Disponibles

- **Publicación**: Limitar a fuente específica
- **País**: Filtrar por país de publicación
- **Fechas**: Rango temporal (desde/hasta)
- **Límite**: 50, 100, 200, 500, 1000 documentos
- **Modelo IA**: Gemini Flash, Pro, GPT-4o, Claude
- **Temperatura**: 0.0 (preciso) a 1.0 (creativo)

### Umbral de Similitud

El sistema usa un umbral de **50% de similitud coseno** para filtrar resultados irrelevantes. Documentos con menor similitud se descartan automáticamente.

## 🔬 Arquitectura Técnica

### Pipeline de Búsqueda

```
1. Usuario escribe query: "embarque clandestino"
2. Sistema genera embedding del query (vector de 1536 dims)
3. Calcula similitud coseno con TODOS los documentos
4. Ordena por similitud descendente
5. Aplica filtros (publicación, fecha, país)
6. Retorna top N resultados
```

### Cálculo de Similitud

```python
similitud = cosine_similarity(query_vector, doc_vector)
# Resultado: 0.0 (ortogonal) a 1.0 (idéntico)
# Umbral mínimo: 0.5 (50%)
```

### Optimización

- **Búsqueda vectorizada** con NumPy (no bucles)
- **Límite de candidatos**: 2000 documentos máximo
- **Índice en base de datos** por modelo de embedding
- **Caché de embeddings** en PostgreSQL (JSON)

## 📈 Métricas de Calidad

### TF-IDF vs Embeddings

| Métrica | TF-IDF | Embeddings |
|---------|--------|------------|
| Entiende sinónimos | ❌ No | ✅ Sí |
| Contexto semántico | ❌ No | ✅ Sí |
| Búsqueda conceptual | ❌ No | ✅ Sí |
| Velocidad | ⚡ Muy rápida | 🐢 Más lenta |
| Costo | 💰 Gratis | 💰💰 Uso de API |
| Dimensionalidad | ~5000 sparse | 768-3072 dense |

## 🔧 Troubleshooting

### Problema: No aparecen resultados con IA activada

**Solución**: Verificar que los embeddings se generaron:

```bash
python -c "from app import app, db; from models import Prensa; 
with app.app_context():
    count = db.session.query(Prensa).filter(
        Prensa.embedding_vector.isnot(None)
    ).count()
    print(f'Documentos con embeddings: {count}')"
```

### Problema: Error "No se pudo generar embedding"

**Causas posibles**:
1. API key no configurada
2. Cuota de API agotada
3. Modelo no disponible

**Solución**: Verificar API keys y cambiar de modelo.

### Problema: Resultados muy lentos

**Optimizaciones**:
1. Reducir límite de documentos (usar 100 en vez de 1000)
2. Aplicar más filtros (publicación, fecha)
3. Generar embeddings con modelo más pequeño (openai-small vs large)

## 📚 Investigación con HESIOX

### Workflow Recomendado

1. **Exploración inicial**: Usar TF-IDF para búsquedas rápidas de palabras clave
2. **Profundización conceptual**: Activar embeddings para búsqueda semántica
3. **Análisis de patrones**: Usar Regex Lab con IA para categorización
4. **Visualización**: Topografía Semántica para ver clusters conceptuales

### Ejemplo de Investigación: Migración

```
Paso 1: TF-IDF → "migración" (1000 resultados en 0.5s)
Paso 2: Embeddings → "desplazamiento forzado población civil" (150 resultados en 2s)
Paso 3: Regex Lab → "\b(refugiado|asilado|exiliado)\b" (85 resultados con análisis IA)
Paso 4: Topografía → Visualizar clusters espacio-temporales
```

## 🚀 Siguientes Pasos

1. **Generar embeddings** para tu corpus completo
2. **Experimentar** con diferentes modelos (Google vs OpenAI)
3. **Comparar** resultados TF-IDF vs Embeddings
4. **Ajustar** umbrales y filtros según necesidades
5. **Integrar** con otras herramientas (Regex Lab, Topografía)

---

**Para soporte técnico**: Consultar logs en `/opt/hesiox/logs/` o activar debug en app.py
