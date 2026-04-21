# 📊 Guía de Análisis Avanzados - Proyecto Sirio

## 🎯 Descripción General

Se han implementado **10 tipos de análisis avanzados** de Humanidades Digitales en tu aplicación bibliográfica. Todos están accesibles desde el menú lateral: **Mapas y Redes → 🔬 Análisis Avanzado**

---

## 📚 Análisis Implementados

### 1. **Dashboard General** 📈
**¿Qué hace?**
- Vista panorámica con métricas clave del corpus
- Previsualización de sentimiento, tópicos y n-gramas
- 4 tarjetas con estadísticas principales

**Cuándo usarlo:**
- Primera exploración del corpus
- Obtener vista general rápida
- Identificar áreas de interés para análisis detallado

---

### 2. **Análisis de Sentimiento Temporal** 😊😐😢
**¿Qué hace?**
- Detecta el tono emocional (positivo/negativo/neutral) de cada noticia
- Muestra evolución del sentimiento a lo largo del tiempo
- Incluye análisis de subjetividad (objetivo vs. subjetivo)

**Aplicaciones:**
- Ver cómo cambia la percepción de eventos históricos
- Identificar periodos de crisis o celebración
- Comparar tonos entre publicaciones diferentes

**Métricas:**
- **Polaridad**: -1 (muy negativo) a +1 (muy positivo)
- **Subjetividad**: 0 (objetivo) a 1 (muy subjetivo)

---

### 3. **Topic Modeling (LDA)** 🧠
**¿Qué hace?**
- Descubre automáticamente temas ocultos en el corpus
- Agrupa documentos por temáticas similares
- Extrae palabras clave de cada tópico

**Aplicaciones:**
- Descubrir temas no etiquetados manualmente
- Organizar corpus grande por áreas temáticas
- Identificar tendencias emergentes

**Parámetros ajustables:**
- **n_topics**: Número de tópicos a descubrir (por defecto: 5)
- **n_words**: Palabras por tópico a mostrar (por defecto: 10)

**Ejemplo de salida:**
```
Tópico 1: gobierno, presidente, elección, congreso, ministro, ...
Tópico 2: guerra, soldados, batalla, conflicto, paz, ...
Tópico 3: economía, mercado, precio, comercio, exportación, ...
```

---

### 4. **Coocurrencia de Entidades** 🕸️
**¿Qué hace?**
- Detecta qué personas, lugares y organizaciones aparecen juntas
- Genera una red visual de conexiones
- Grosor de líneas = frecuencia de aparición conjunta

**Aplicaciones:**
- Descubrir relaciones no evidentes
- Mapear redes de actores históricos
- Identificar alianzas y conflictos

**Visualización:**
- Red interactiva con vis.js
- Hover para ver detalles de nodos
- Click para explorar documentos relacionados

---

### 5. **Análisis Estilométrico** ✍️
**¿Qué hace?**
- Analiza el estilo de escritura de cada documento
- Mide complejidad, longitud de frases, riqueza léxica
- Compara estilos entre publicaciones

**Métricas calculadas:**
- **Palabras por oración**: Complejidad sintáctica
- **Diversidad léxica (TTR)**: Riqueza de vocabulario
- **Longitud promedio de palabra**: Complejidad léxica

**Aplicaciones:**
- Comparar estilos editoriales
- Identificar autoría (estilometría forense)
- Estudiar evolución del lenguaje periodístico
- Detectar textos plagiados (baja diversidad)

---

### 6. **Análisis de N-gramas** 📝
**¿Qué hace?**
- Identifica frases completas más frecuentes
- Bigramas (2 palabras): "guerra civil", "presidente electo"
- Trigramas (3 palabras): "banco central europeo"

**Aplicaciones:**
- Detectar expresiones típicas de la época
- Identificar clichés periodísticos
- Analizar frames narrativos recurrentes

**Controles:**
- **Tipo**: Bigramas, Trigramas, 4-gramas
- **Top K**: Cantidad de frases a mostrar (10-50)

**Ejemplo:**
```
"guerra mundial" (123 apariciones)
"primera guerra" (98 apariciones)
"gran guerra" (87 apariciones)
```

---

### 7. **Clustering de Documentos** 📂
**¿Qué hace?**
- Agrupa automáticamente documentos similares
- Visualización espacial con t-SNE (2D)
- Extrae palabras clave de cada cluster

**Aplicaciones:**
- Organizar corpus sin etiquetas previas
- Detectar noticias duplicadas o muy similares
- Segmentar corpus por subtemas

**Algoritmos disponibles:**
- **K-Means**: Clusters bien definidos (por defecto)
- **DBSCAN**: Detecta clusters de forma irregular

**Parámetros:**
- **n_clusters**: Número de grupos (3-10)

---

### 8. **Similitud entre Documentos** 🔍
**¿Qué hace?**
- Encuentra los documentos más parecidos a uno dado
- Usa similitud coseno en vectores TF-IDF
- Retorna top 5 más similares con scores

**Aplicaciones:**
- Sistema de recomendación ("Noticias relacionadas")
- Detectar plagio o republicaciones
- Seguimiento de historias a través del tiempo

**Endpoint:** `/api/analisis/similares/<id_documento>`

---

## 🎛️ Filtros Disponibles

Todos los análisis pueden filtrarse por:
- **Proyecto**: Limitar a un proyecto específico
- **Rango de fechas**: Desde-hasta
- **Publicación**: Ej. "El Mercurio", "La Nación"
- **Ciudad/País**: Filtros geográficos

**Botón "Filtros"** en la barra superior → Aplicar → Recargar análisis

---

## 🔧 Instalación de Dependencias

```bash
# Activar entorno virtual
venv\Scripts\activate

# Instalar nuevas librerías
pip install textblob==0.17.1
pip install gensim==4.3.2
pip install pandas==2.1.4

# Descargar corpus de TextBlob para sentimiento
python -m textblob.download_corpora

# Verificar que spaCy esté instalado
python -m spacy download es_core_news_md
```

---

## 📊 Tecnologías Utilizadas

| Librería | Función |
|----------|---------|
| **scikit-learn** | Clustering, TF-IDF, LDA, t-SNE |
| **spaCy** | NLP, entidades, tokenización |
| **gensim** | Topic modeling alternativo |
| **textblob** | Análisis de sentimiento |
| **pandas** | Manipulación de datos temporales |
| **vis.js** | Visualización de redes |
| **Chart.js** | Gráficos interactivos |

---

## 🚀 Cómo Usar

1. **Acceder a la interfaz:**
   - Menú lateral → **Mapas y Redes** → **🔬 Análisis Avanzado**

2. **Seleccionar tipo de análisis:**
   - Dashboard: Vista general
   - Sentimiento: Evolución emocional
   - Tópicos: Temas ocultos
   - Entidades: Red de relaciones
   - Estilo: Complejidad textual
   - N-gramas: Frases frecuentes
   - Clustering: Agrupación automática

3. **Aplicar filtros (opcional):**
   - Click en **"Filtros"**
   - Seleccionar proyecto, fechas, publicación
   - Click en **"Aplicar Filtros"**

4. **Interactuar con visualizaciones:**
   - Hover en gráficos para detalles
   - Click en elementos para explorar
   - Scroll en paneles con muchos datos

5. **Exportar resultados:**
   - Click en **"Exportar"**
   - Descarga archivo JSON con todos los datos
   - Usar en Gephi, R, Python, Excel, etc.

---

## 📈 Casos de Uso Reales

### **Caso 1: Análisis de Crisis Política**
1. Filtrar por fechas del evento (ej. Agosto 1906)
2. Ver **Sentimiento Temporal** → ¿Cambió el tono?
3. Ver **Entidades** → ¿Quiénes aparecen juntos?
4. Ver **N-gramas** → ¿Qué expresiones se repiten?

### **Caso 2: Comparación de Publicaciones**
1. Filtrar por "El Mercurio"
2. Ver **Estilometría** → Guardar métricas
3. Cambiar filtro a "La Nación"
4. Comparar palabras/oración, diversidad léxica

### **Caso 3: Descubrimiento de Temas**
1. Sin filtros (corpus completo)
2. Ver **Topic Modeling** con 7-10 tópicos
3. Revisar palabras clave de cada tópico
4. Etiquetar tópicos manualmente
5. Ver **Clustering** para validar agrupación

### **Caso 4: Seguimiento de Historias**
1. Buscar noticia sobre evento específico
2. Copiar ID de la noticia
3. Usar `/api/analisis/similares/<id>`
4. Ver top 5 noticias relacionadas
5. Construir cronología del evento

---

## ⚠️ Limitaciones y Consideraciones

- **Rendimiento**: Análisis limitados a ~200-500 docs por consulta para mantener velocidad
- **Idioma**: Optimizado para español (TextBlob funciona mejor en inglés, pero detecta español)
- **Calidad de datos**: Resultados dependen de calidad del texto (OCR, transcripción)
- **Topic Modeling**: Requiere mínimo 5 documentos por tópico
- **Clustering**: Funciona mejor con +30 documentos

---

## 🆘 Solución de Problemas

**Error: "spaCy no disponible"**
→ Instalar: `python -m spacy download es_core_news_md`

**Error: "No hay suficientes documentos"**
→ Reducir n_topics o n_clusters, o ampliar filtros

**Análisis muy lento**
→ Reducir rango de fechas o limitar a una publicación

**Sentimiento siempre neutro**
→ TextBlob funciona mejor con textos largos y opinativos

**Gráficos no se muestran**
→ Verificar consola del navegador (F12), revisar que Chart.js se cargue

---

## 📚 Referencias y Lecturas Recomendadas

- **Topic Modeling**: Blei et al. (2003) - "Latent Dirichlet Allocation"
- **Estilometría**: Burrows (2002) - "Delta: a Measure of Stylistic Difference"
- **Análisis de Sentimiento**: Liu & Zhang (2012) - "Sentiment Analysis and Opinion Mining"
- **Clustering**: MacQueen (1967) - "K-means clustering"

---

## 🎓 Créditos

**Desarrollado para:** Proyecto Sirio  
**Tecnologías:** Flask + scikit-learn + spaCy + vis.js + Chart.js  
**Última actualización:** Enero 2026

---

¿Dudas? Revisa la consola del navegador (F12) para mensajes de debug detallados.
