# hesiOX - Sistema de Gestión Hemerográfica y Análisis Lab (v4.2.0)

<p align="center">
  <img src="static/img/hesiox_logo2.png" width="30%">
</p>

**hesiOX** es una metodología integral y un laboratorio de software diseñado para la conversión de activos documentales en conocimiento estructurado e interoperable. Representa la convergencia entre la **Archivística**, la **Ingeniería de Datos** y las **Humanidades Digitales**.

Desarrollado originalmente para el estudio académico de la prensa histórica (Proyecto S.S. Sirio), hesiOX ha evolucionado hasta convertirse en una herramienta multipropósito para la gestión y el análisis de corpus documentales complejos.

## 🚀 Características Principales

### 📂 Gestión de Corpus Académico
- **Soporte Multi-proyecto**: Gestiona proyectos de investigación independientes (tesis, artículos, libros) con sus propias bibliotecas de referencia.
- **Exportación Académica**: Exporta referencias en formatos BibTeX, RIS, Chicago, APA, MLA y Vancouver.
- **Interoperabilidad**: Compatible con Zotero, Mendeley y EndNote.

### 🤖 Inteligencia Artificial y NLP
- **Redes de Conocimiento Inteligentes**: Detección automática de entidades (Personas, Lugares, Organizaciones) utilizando **spaCy NER**.
- **Corpus CHAT (RAG)**: Interacción en lenguaje natural con tus documentos mediante modelos multimodales, con trazabilidad total a las fuentes primarias.
- **Búsqueda Semántica**: Motor impulsado por NLP que comprende el contexto de tus consultas.

### 🗺️ Análisis Geoespacial (GIS)
- **Georreferenciación de Mapas Antiguos**: Vectorización y digitalización de mapas históricos como Sistemas de Información Geográfica.
- **Patrones Espaciales**: Visualiza la evolución geográfica de las fuentes documentales.
- **Análisis Geosemántico**: Cálculo de geodésicas (Haversine) y exportación a GeoJSON.

### 🎭 Procesamiento del Discurso Teatral
- **Análisis Dramático**: Estudio de co-presencia, redes de personajes y trayectorias emocionales.
- **Análisis de Sentimiento**: Visualización del flujo emocional a lo largo de las obras teatrales.

### 🔍 Digitalización y Forense
- **OCR Inteligente**: Extracción automática de texto de imágenes de prensa histórica utilizando **Tesseract.js**.
- **Navegación Monte Carlo**: Ejecución de trayectorias aleatorias y análisis forense de la deriva histórica mediante IA.

## 🛠️ Stack Tecnológico

- **Backend**: Python Flask
- **Base de Datos**: PostgreSQL (SQLAlchemy)
- **Frontend**: Bootstrap 5, D3.js, Chart.js, Leaflet Maps, Choices.js
- **Inteligencia Artificial**: spaCy (NLP), integración con las APIs de OpenAI/Gemini/Anthropic para RAG.
- **OCR**: Tesseract.js

## 📄 Licencia

**Software 100% Libre** - Licenciado bajo **GPL v3**. Código abierto y extensible para la comunidad académica.

## 📜 Historial de Versiones (Changelog)

hesiOX ha evolucionado a través de múltiples fases de innovación técnica y académica. A continuación se resumen los hitos principales:

<details>
<summary><b>[5.0.0] - Gestión Dinámica de Tipos de Ubicación (MAJOR)</b></summary>

- **Gestión sin código**: Sistema completo para añadir y editar tipos geográficos desde la web.
- **Base de datos centralizada**: Nueva tabla `tipo_ubicacion` con más de 100 tipos predefinidos.
- **Categorización**: Tipos organizados en 7 categorías (Ciudades, Vías, Edificios, Hidrografía, etc.).
- **API RESTful**: Endpoints completos para el mantenimiento de la taxonomía geográfica.
</details>

<details>
<summary><b>[4.1.0] - Validación Avanzada y Colaboración Multi-Usuario</b></summary>

- **Filtro Lexicográfico**: Eliminación de falsos positivos en geocodificación (gentilicios vs ubicaciones).
- **Colaboración**: Sistema de proyectos compartidos con roles de Propietario y Colaborador.
- **Sistema de Bloqueos (Locks)**: Prevención de conflictos de edición simultánea (timeout de 5 min).
- **Seguridad**: Validación CSRF robusta en todas las operaciones.
</details>

<details>
<summary><b>[2.8.0] - Capas Externas GIS y Estabilidad</b></summary>

- **Soporte Multi-Formato**: Ingesta de archivos GeoJSON, KML y Shapefile (ZIP).
- **Conversión Automática**: Integración con Geopandas para normalización GIS.
- **Interrogación de Atributos**: Consulta de metadatos internos mediante popups.
- **Fix Críticos**: Resolución de errores 500 y optimización de lógica de limpieza de nombres.
</details>

<details>
<summary><b>[2.7.5] - Digitalización Vectorial GIS (INNOVACIÓN MAYOR)</b></summary>

- **Digitalización Profesional**: Primera implementación DH open-source de digitalización vectorial (puntos, líneas, polígonos).
- **Cálculos Geométricos**: Cálculo automático de longitudes (km) y áreas (hectáreas) usando algoritmos Haversine y Shoelace.
- **Panel de Control Sirio**: Interfaz profesional para gestión de capas simultáneas.
- **Exportación GeoJSON**: Cumplimiento con el estándar RFC 7946 para interoperabilidad con QGIS y ArcGIS.
</details>

<details>
<summary><b>[2.7.0] - IA Advanced y Geosemántica</b></summary>

- **Topografía Semántica Híbrida**: Visualización 3D combinada con curvas de nivel.
- **Elipse de Desviación Estándar (SDE)**: Análisis de dispersión y orientación del corpus.
- **IA Advanced Button**: Acceso directo al motor de precisión spaCy + Gemini.
- **Automatización de Referencias**: Detección contextual del tipo de recurso (Prensa vs Libro).
</details>

<details>
<summary><b>[1.5.0] - Auditoría TFM y Perfiles de Análisis</b></summary>

- **Perfiles de Stopwords**: Tres niveles de análisis (Contenido, Estilométrico, Mixto).
- **Auditoría Técnica**: Verificación de calidad para presentación académica (32,500+ líneas de código).
- **Branding Sirius**: Rediseño de visualizaciones con paleta corporativa y navegación compacta.
- **Limpieza de Proyecto**: Eliminación masiva de archivos obsoletos.
</details>

<details>
<summary><b>[1.0.0] - Lanzamiento Inicial</b></summary>

- **Core Multi-Proyecto**: Aislamiento de datos y gestión de referencias bibliográficas.
- **Motor OCR**: Integración inicial con Tesseract.js.
- **Base SQL**: Migración a PostgreSQL con relaciones en cascada.
- **Visualización**: Primeras implementaciones de nubes de palabras y mapas Leaflet.
</details>

---
Desarrollado para el **LINHD-UNED** y la comunidad de Humanidades Digitales.
