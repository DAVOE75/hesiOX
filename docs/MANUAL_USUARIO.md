# 📘 Manual de Usuario - hesiOX v2.7.5

**Sistema de Gestión de Referencias Bibliográficas para Humanidades Digitales**

**Última actualización**: 6 de marzo de 2026

---

## 📑 Tabla de Contenidos

1. [Introducción](#introducción)
2. [Primeros Pasos](#primeros-pasos)
3. [Registro y Autenticación](#registro-y-autenticación)
4. [Gestión de Proyectos](#gestión-de-proyectos)
5. [Gestión de Hemerotecas](#gestión-de-hemerotecas)
6. [Gestión de Artículos de Prensa](#gestión-de-artículos-de-prensa)
7. [Gestión de Publicaciones Académicas](#gestión-de-publicaciones-académicas)
8. [OCR Automático](#ocr-automático)
9. [Búsqueda y Filtrado Inteligente](#búsqueda-y-filtrado-inteligente)
10. [Laboratorio Geosemántico (IA)](#laboratorio-geosemántico)
    - 10.1 [Búsqueda Semántica](#búsqueda-semántica)
    - 10.2 [Topografía Semántica](#topografía-semántica)
    - 10.3 [Biblioteca de Conceptos](#biblioteca-de-conceptos)
11. [Generador de Citas Bibliográficas](#generador-de-citas-bibliográficas)
12. [Análisis y Estadísticas](#análisis-y-estadísticas)
13. [Análisis NLP con spaCy](#análisis-nlp-con-spacy)
14. [Visualizaciones](#visualizaciones)
15. [Exportación de Datos](#exportación-de-datos)
16. [Temas Visuales](#temas-visuales)
17. [Atajos de Teclado](#atajos-de-teclado)
18. [Solución de Problemas](#solución-de-problemas)

---

## 🎯 Introducción

### ¿Qué es hesiOX?

hesiOX es un sistema profesional de gestión de referencias bibliográficas diseñado específicamente para investigadores en Humanidades Digitales. Combina funcionalidades de catalogación, análisis de texto, visualización de datos y exportación académica en una plataforma integrada.

### Características Principales

- **🔐 Sistema Multi-Usuario**: Registro, login y datos aislados por cuenta
- **📂 Multi-Proyecto**: Organiza diferentes colecciones bibliográficas de forma independiente
- **🗄️ Gestión de Hemerotecas**: Base de datos de hemerotecas digitales con vinculación automática
- **📸 OCR Integrado**: Digitalización automática de documentos escaneados (2-3 segundos/imagen)
- **🔍 Búsqueda Inteligente**: Filtros con debounce 150ms, Choices.js para selects avanzados
- **🧠 Laboratorio Geosemántico**: Motor NLP con Búsqueda Semántica (<1s) y **Topografía Semántica** (Isosurfaces con IA).
- **🏷️ Generador de Citas**: 7 formatos académicos (ISO 690, APA 7, MLA 9, Chicago 17, Harvard, Vancouver, Hemerográfico)
- **📊 Análisis Avanzado**: Estadísticas, frecuencias, nubes de palabras, análisis temporal
- **🔬 Análisis NLP**: Extracción de entidades (PER, LOC, ORG) con spaCy es_core_news_md
- **🗺️ Visualizaciones**: Mapas geográficos (Leaflet), timeline, redes (D3.js), gráficos (Chart.js)
- **💾 Exportación**: BibTeX, RIS, CSV, JSON para integración con Zotero, Mendeley, EndNote

### Requisitos del Sistema

- Navegador moderno (Chrome 90+, Firefox 88+, Edge 90+)
- Resolución mínima: 1366x768
- JavaScript habilitado
- **Sin dependencias CDN**: Bootstrap 5.3.3 y Choices.js locales para uso offline

---

## 🚀 Primeros Pasos

### 1. Acceso a la Aplicación

1. Abre tu navegador web
2. Accede a la URL: `http://localhost:5000` (o la URL de tu instalación)
3. Verás la **página de inicio** con el logo de hesiOX

### 2. Navegación Principal

La barra de navegación superior contiene:

- **Inicio**: Página principal con información general
- **Información**: Detalles del sistema, tecnologías, historial de versiones
- **Proyectos** (dropdown):
  - Ver Proyectos
  - Crear Proyecto
  - Abrir: [Proyecto Activo]
- **Blog**: Enlace externo al blog del proyecto (https://sirio.hypotheses.org)
- **Ayuda**: Preguntas frecuentes y manual de uso
- **Usuario** (dropdown si autenticado):
  - Mi Cuenta
  - Cerrar Sesión

---

## 🔐 Registro y Autenticación

### Crear una Cuenta

1. Haz clic en **Registrarse** en la página de inicio
2. Completa el formulario:
   - **Usuario**: Nombre de usuario único (alfanumérico, sin espacios)
   - **Contraseña**: Mínimo 8 caracteres (se hasheará automáticamente)
   - **Confirmar contraseña**: Debe coincidir
3. Haz clic en **Crear Cuenta**
4. Serás redirigido automáticamente al login

### Iniciar Sesión

1. Haz clic en **Iniciar Sesión**
2. Ingresa tus credenciales:
   - **Usuario**
   - **Contraseña**
3. Haz clic en **Entrar**
4. Accederás a tu dashboard de proyectos

### Cerrar Sesión

1. Haz clic en tu **nombre de usuario** en la barra superior
2. Selecciona **Cerrar Sesión**
3. La sesión se cerrará y volverás a la página de inicio

**Nota de Seguridad**: Todos los proyectos y datos están aislados por usuario. Cada cuenta solo puede ver y gestionar sus propios proyectos.

---

## 📁 Gestión de Proyectos

### 3. Crear tu Primer Proyecto

1. Haz clic en **Proyectos → Crear Proyecto**
2. Completa el formulario:
   - **Nombre**: Identificador único (ej: "Prensa del Sirio", "Archivo Municipal")
   - **Descripción**: Breve explicación del contenido (opcional)
   - **Tipo**: Selecciona entre:
     - **Hemerografía**: Prensa histórica
     - **Libros**: Libros y monografías
     - **Archivos**: Documentos de archivo
     - **Mixto**: Varios tipos
3. Haz clic en **Crear Proyecto**
4. El proyecto se activará automáticamente

---

## 📁 Gestión de Proyectos

### Ver Todos los Proyectos

**Ruta**: `Proyectos → Ver Proyectos`

Muestra una vista en tarjetas con:
- Nombre del proyecto
- Tipo (badge de color)
- Descripción
- Número de artículos
- Número de publicaciones
- Fecha de creación
- Estado (Activo/Inactivo)

### Activar un Proyecto

1. Localiza el proyecto en la lista
2. Haz clic en **Abrir Proyecto**
3. El proyecto se marca como activo (badge naranja)
4. Solo puedes tener un proyecto activo a la vez

### Editar un Proyecto

1. En la lista de proyectos, haz clic en **Editar**
2. Modifica los campos que desees:
   - Nombre (debe ser único)
   - Descripción
   - Tipo
3. Haz clic en **Guardar Cambios**

### Eliminar un Proyecto

⚠️ **ADVERTENCIA**: La eliminación es irreversible.

El sistema usa **confirmación cuádruple** para prevenir eliminaciones accidentales:

1. Haz clic en **Eliminar**
2. **Paso 1**: Escribe el nombre exacto del proyecto
3. **Paso 2**: Marca el checkbox de confirmación
4. **Paso 3**: El botón "Eliminar Proyecto" se habilita
5. **Paso 4**: Confirma en la alerta JavaScript final

**Restricciones**:
- No puedes eliminar el proyecto activo (primero activa otro)
- No puedes eliminar el único proyecto (debe haber al menos uno)

### Salir de un Proyecto

Cuando estés dentro de un proyecto (biblioteca), haz clic en **Salir del Proyecto** en la parte superior para volver al inicio.

---

## 📰 Gestión de Artículos de Prensa

### Crear Nuevo Artículo

**Ruta**: Dentro de un proyecto activo → Botón **+ Nueva Noticia**

#### Campos del Formulario (Inteligencia Contextual)

El sistema ahora detecta automáticamente el tipo de recurso según el proyecto activo:
- **Proyecto de Hemerografía**: Preselecciona **Prensa**.
- **Proyecto de Bibliografía**: Preselecciona **Libro**.

**Identificación**:
- **Número de Referencia**: Código único para el artículo (auto-sugerido)
- **Tipo de Recurso**: Permite cambiar entre Prensa, Libro, Artículo, etc.
- **Publicación / Medio o Fuente**: 
  - Para **Prensa**, se solicita el nombre del periódico/revista.
  - Para **Libro**, se solicita el título de la obra.
- **Sección**: Sección del periódico (opcional)

**Información Temporal**:
- **Fecha / Año**: 
  - En **Prensa**, se usa fecha completa (DD/MM/AAAA).
  - En **Libro**, se solicita el año de publicación.
- **Época**: Siglo/período histórico (autocompletar activado)

**Información de Edición**:
- **Edición**: Desplegable dinámico que cambia según el recurso:
  - **Prensa**: Diaria, Mañana, Tarde, Semanal, etc.
  - **Libro**: Príncipe, De Bolsillo, De Lujo, Crítica, etc.
  - **Artículos Académicos**: Pre-print, Post-print, Editorial.
  - **Tesis**: Original, Publicada, Resumen (Adapta campos a Universidad/Defensa).
  - **Fotografía**: Época, Original, Digital (Adapta campos a Colección/Archivo).

**Contenido**:
- **Contenido/Extracto**: Editor TinyMCE con formato rico
  - Negrita, cursiva, subrayado
  - Listas ordenadas/desordenadas
  - Enlaces
  - Tablas HTML
  - Código fuente HTML

**Clasificación**:
- **Palabras Clave**: Separadas por comas (ej: "naufragio, inmigración, Argentina")
- **Autores**: Nombres de autores/periodistas (opcional)
- **Temáticas**: Temas principales (opcional)

**Páginas e Imágenes**:
- **Páginas**: Números de página (ej: "3-4" o "12")
- **URL Hemeroteca**: Enlace a versión digital (opcional)
- **Imágenes**: Ver sección [OCR Automático](#ocr-automático)

### Editar un Artículo

1. En el listado, haz clic en el **título** del artículo o en el icono de edición
2. Modifica los campos necesarios
3. Haz clic en **Actualizar**

**Tip**: Usa Ctrl+S para guardar rápidamente mientras editas.

### Eliminar Artículos

**Individual**:
1. Haz clic en el icono de **papelera** junto al artículo
2. Confirma la eliminación

**Masivo** (múltiples artículos):
1. Marca los checkboxes de los artículos a eliminar
2. El botón **Lotes (N)** se habilita
3. Selecciona **Borrar seleccionados**
4. Confirma la eliminación en masa

### Ver Imágenes de un Artículo

1. Haz clic en el icono de **imagen** junto al artículo
2. Se abrirá una galería con todas las imágenes OCR
3. Puedes navegar entre imágenes
4. Ver texto extraído por OCR
5. Descargar imágenes individuales

---

## 📚 Gestión de Publicaciones Académicas

### Crear Nueva Publicación

**Ruta**: Dentro de un proyecto activo → Menú **Acciones** → **Publicaciones**

#### Campos del Formulario

**Identificación**:
- **Autor(es)**: Apellido, Nombre (separar múltiples con ";"
- **Título**: Título completo de la publicación
- **Tipo**: Libro, Artículo, Capítulo, Tesis, Informe, etc.

**Publicación**:
- **Título de la Revista/Libro**: Para artículos de revista o capítulos de libro
- **Editorial**: Casa editorial
- **Año**: Año de publicación
- **Volumen**: Número de volumen (revistas)
- **Número**: Número de edición (revistas)
- **Páginas**: Rango de páginas (ej: "23-45")

**Identificadores**:
- **ISBN**: Número ISBN (libros)
- **ISSN**: Número ISSN (revistas)
- **DOI**: Digital Object Identifier
- **URL**: Enlace web a la publicación

**Clasificación**:
- **Palabras Clave**: Términos de búsqueda
- **Resumen**: Resumen del contenido
- **Notas**: Anotaciones adicionales

### Editar/Eliminar Publicaciones

Similar al proceso de artículos de prensa. Accede a través del menú de publicaciones.

---

## 🗄️ Gestión de Hemerotecas

### ¿Qué es una Hemeroteca Digital?

Una **hemeroteca** es un archivo digital de publicaciones periódicas (periódicos, revistas, boletines). En hesiOX, las hemerotecas te permiten organizar y vincular artículos de prensa a sus fuentes originales.

### Estructura de Datos

El sistema sigue una jerarquía:

```
Hemeroteca → Publicación → Artículo
```

- **Hemeroteca**: Institución o colección digital (ej: "Biblioteca Nacional de España")
- **Publicación**: Periódico específico (ej: "Diario de la Marina")
- **Artículo**: Noticia o artículo individual

### Crear/Editar Hemeroteca

**Ruta**: Menú **Hemerotecas** → **Nueva Hemeroteca** / **Editar**

#### Campos del Formulario

**Información Básica**:
- **Nombre**: Nombre oficial de la hemeroteca
  - Ejemplo: "Biblioteca Digital Hispánica"
- **País**: País de origen (selector con 14 países + genérico)
  - Incluye banderas automáticas 🇪🇸 🇦🇷 🇲🇽 🇨🇺 🇨🇴 🇵🇪 🇻🇪 🇨🇱 🇺🇾 🇧🇴 🇵🇾 🇪🇨 🇬🇹 🇵🇦

**Acceso y Ubicación**:
- **URL**: Enlace directo a la hemeroteca digital
  - Se valida que sea una URL válida (http/https)
- **Institución**: Organismo responsable
  - Ejemplo: "Biblioteca Nacional de España"
- **Ciudad**: Ciudad sede de la hemeroteca

**Características**:
- **Descripción**: Breve descripción del contenido y alcance
- **Notas**: Información adicional, restricciones de acceso, etc.

### Países Soportados con Banderas

El sistema incluye banderas para:

🇪🇸 España | 🇦🇷 Argentina | 🇲🇽 México | 🇨🇺 Cuba | 🇨🇴 Colombia | 🇵🇪 Perú | 🇻🇪 Venezuela | 🇨🇱 Chile | 🇺🇾 Uruguay | 🇧🇴 Bolivia | 🇵🇾 Paraguay | 🇪🇨 Ecuador | 🇬🇹 Guatemala | 🇵🇦 Panamá | 🌐 Genérico (otros países)

### Vincular Hemeroteca a Artículos

#### Desde el Formulario de Artículo

1. Abre **Nuevo Artículo** o **Editar Artículo**
2. En el campo **"Hemeroteca"**, selecciona de la lista desplegable
3. Las hemerotecas se muestran con bandera + nombre
4. El vínculo se guarda automáticamente

#### Desde el Listado de Artículos

1. Ve a **Listado de Artículos** de tu proyecto
2. La columna **Hemeroteca** muestra la institución vinculada
3. Haz clic en el nombre para ir a la página de la hemeroteca
4. Visualiza todos los artículos de esa hemeroteca

### Migrar Artículos entre Hemerotecas

**Ruta**: Menú **Hemerotecas** → **Migrar Artículos**

Permite trasladar artículos de una hemeroteca a otra:

1. Selecciona **Hemeroteca origen** (ej: "Genérico")
2. Selecciona **Hemeroteca destino** (ej: "BNE")
3. El sistema muestra cuántos artículos se migrarán
4. Confirma la migración
5. Todos los artículos se actualizan automáticamente

**Caso de Uso**: Si inicialmente subiste artículos sin hemeroteca específica y luego creaste una hemeroteca adecuada.

### Buscar y Filtrar Hemerotecas

**Desde el Listado**:
- Busca por nombre de hemeroteca
- Filtra por país (selector de países)
- Ordena por nombre, país, número de artículos

**Desde el Buscador Semántico**:
- Busca "artículos de la Biblioteca Nacional"
- El sistema encuentra artículos vinculados a esa hemeroteca
- Filtra resultados por institución

### Ver Estadísticas por Hemeroteca

**Ruta**: Menú **Hemerotecas** → Haz clic en una hemeroteca

Visualiza:
- **Total de artículos** de esa hemeroteca en tu proyecto
- **Distribución temporal** (gráfico de barras por años)
- **Palabras clave** más frecuentes en esos artículos
- **Enlace directo** a la hemeroteca digital

### Casos de Uso

✅ **Investigación histórica**: Vincula artículos a sus fuentes originales para citación académica
✅ **Organización por instituciones**: Separa artículos por hemeroteca de origen
✅ **Gestión de permisos**: Identifica qué artículos vienen de fuentes con restricciones
✅ **Análisis comparativo**: Compara cobertura de diferentes hemerotecas
✅ **Navegación intuitiva**: Filtra artículos por hemeroteca para análisis específico

---

## 🔍 OCR Automático

### ¿Qué es el OCR?

OCR (Optical Character Recognition) es la tecnología que convierte imágenes de texto en texto editable. hesiOX usa **Tesseract.js 4.1.1** para extraer automáticamente el texto de periódicos escaneados.

### Cómo Usar el OCR

#### Al Crear un Artículo Nuevo

1. En el formulario de nuevo artículo, busca la sección **"Subir Imágenes"**
2. Haz clic en **"Seleccionar archivos"** o arrastra imágenes
3. Formatos soportados: JPG, PNG, GIF, TIFF
4. Puedes subir **múltiples imágenes** a la vez

#### Proceso Automático

1. **Subida**: Las imágenes se cargan al servidor
2. **OCR Automático**: Tesseract procesa cada imagen (2-3 segundos/imagen)
3. **Extracción**: El texto se extrae automáticamente
4. **Inserción**: El texto se copia al editor TinyMCE
5. **Revisión**: Revisa y corrige el texto extraído

#### Durante la Edición

1. Al editar un artículo existente
2. Usa el botón **"Subir más imágenes"**
3. El OCR procesará las nuevas imágenes
4. El texto se añadirá al contenido existente

### Tips para Mejor OCR

✅ **Recomendaciones**:
- Usa imágenes de alta resolución (mínimo 300 DPI)
- Asegura buen contraste (texto oscuro sobre fondo claro)
- Evita imágenes borrosas o con manchas
- Escanea páginas rectas (sin inclinación)

⚠️ **Limitaciones**:
- Fuentes muy antiguas o góticas pueden tener menor precisión
- Texto en columnas puede necesitar orden manual
- Imágenes dentro del texto no se procesan
- Siempre revisa el texto extraído

### Ver Texto OCR Original

1. Ve a **Ver Imágenes** del artículo
2. Cada imagen muestra el texto extraído originalmente
3. Compara con el texto editado para verificar correcciones

---

## 🔎 Búsqueda y Filtrado Inteligente

### Búsqueda Rápida

En el listado de artículos, usa el **campo de búsqueda** en la parte superior:

1. Escribe cualquier término
2. La búsqueda es en **tiempo real** con **debounce de 150ms** (optimizado para velocidad)
3. Busca en: título, medio, contenido, palabras clave, autores
4. No distingue mayúsculas/minúsculas
5. Soporta acentos

**Ejemplo**: Buscar "inmigración" encuentra "Inmigración", "inmigración", "INMIGRACIÓN"

### Filtros Avanzados con Choices.js

Los selectores de filtros utilizan **Choices.js** para una experiencia mejorada:
- **Búsqueda instantánea** dentro de las opciones
- **Selección múltiple** en algunos campos
- **Interfaz táctil** optimizada para móviles
- **Accesibilidad** mejorada con teclado

Haz clic en **Filtros** para mostrar opciones avanzadas:

#### Por Fecha
- **Rango de fechas**: Desde - Hasta
- **Año específico**: Solo artículos de ese año
- **Década**: Filtra por década (1900-1909, etc.)
- **Validación automática**: DD/MM/AAAA con autoformateo

#### Por Ubicación
- **Ciudad**: Selector con búsqueda integrada
- **País**: Filtra por país de publicación
- **Búsqueda rápida**: Escribe para encontrar opciones

#### Por Medio
- **Medio específico**: Selector inteligente con lista completa
- **Búsqueda instantánea**: Encuentra periódicos por nombre
- **Autocompleta**: Hereda datos de publicación (ciudad, país, idioma)

#### Por Idioma
- **Idioma**: Selecciona de lista de 50+ idiomas
- **Búsqueda integrada**: Encuentra idiomas rápidamente

#### Combinación de Filtros
- Todos los filtros se pueden combinar
- **Actualización automática** al cambiar valores
- **Modo instant**: Sin delay para acciones de botones
- Usa **Limpiar Filtros** para resetear

### Debounce System

El sistema implementa un **debounce inteligente de 150ms**:

```javascript
// Usuario escribe rápido
Tecla 1 → Espera 150ms
Tecla 2 → Cancela timer anterior, espera 150ms
Tecla 3 → Cancela timer anterior, espera 150ms
[Pausa] → Ejecuta búsqueda (1 sola petición AJAX)
```

**Beneficios**:
- ⚡ Respuesta instantánea percibida
- 🚀 Reducción de carga del servidor (70% menos peticiones)
- 💾 Menor consumo de recursos
- ✅ Sin scroll animations (eliminadas para mejor performance)

### Ordenamiento

Ordena los resultados por:
- **Fecha** (ascendente/descendente)
- **Título** (A-Z / Z-A)
- **Medio** (alfabético)
- **Relevancia** (cuando hay búsqueda activa)

---

## 🧠 Laboratorio Geosemántico (IA)

El **Laboratorio Geosemántico** agrupa las herramientas de análisis más avanzadas de hesiOX, integrando Inteligencia Artificial para la interpretación profunda del corpus.

### 10.1 Búsqueda Semántica

#### ¿Qué es la Búsqueda Semántica?

**Ejemplo**:
- Búsqueda: "tragedia marítima"
- Encuentra: artículos sobre "naufragio", "hundimiento", "accidente naval", "catástrofe en el mar"

**Ruta**: Menú **Laboratorio Geosemántico** → **Buscador Semántico**

1. Escribe tu consulta en **lenguaje natural**:
   - "artículos sobre inmigración a Argentina"
   - "noticias de rescate de náufragos"

2. Haz clic en **Buscar** o presiona Enter.

### 10.2 Topografía Semántica (Fase 2)

#### ¿Qué es la Topografía Semántica?

Es una herramienta de visualización avanzada que utiliza **IA Generativa (Gemini 2.0)** para proyectar la intensidad de un concepto sobre el mapa. A diferencia de un mapa de calor estándar, la topografía crea "cumbres" y "valles" discursivos, permitiendo una interpretación morfológica del corpus.

#### Características Avanzadas (Phase 2 & 3)

1.  **📊 Modos de Visualización**:
    - **Sólido**: Polígonos de densidad rellenos (estilo DTM).
    - **Líneas (Isolinas)**: Curvas de nivel puras para análisis cartográfico técnico.
    - **Híbrido**: El equilibrio perfecto entre relieve sombreado con 10 isolinas de alta densidad por nivel para una lectura morfológica-cuantitativa.
2.  **⏳ Cronografía Animada (Time-Lapse)**: Utilice el control temporal del header para observar cómo el concepto "viaja" y evoluciona en el territorio a través de las décadas. El slider se sincroniza automáticamente con el origen histórico del corpus.
3.  **🏔️ Peak Explorer (Explorador de Cumbres)**: Haga clic en cualquier zona de alta densidad o punto de origen para abrir el panel lateral y ver los documentos originales que generan esa "montaña" de significado.
4.  **❤️ Análisis de Sentimiento Espacial**: Mapee no solo la presencia de un concepto, sino su carga emocional (Positivo/Negativo/Neutral) detectada por IA.
5.  **📍 Filtro por Texto**: Seleccione una noticia o referencia específica para visualizar exclusivamente sus puntos geográficos en el mapa topográfico.
6.  **📄 Informe Ejecutivo PDF**: Genere un documento profesional que incluye el mapa actual, la interpretación de la IA y el branding institucional.

#### Cómo Usar

**Ruta**: Menú **Laboratorio Geosemántico** → **Topografía Semántica**

1.  **Concepto Semilla**: Introduce un término abstracto (ej: "Revolución").
2.  **Expansión IA**: El sistema genera automáticamente un campo léxico de la época.
3.  **Representación**: Se genera un mapa de curvas de nivel (isosurfaces) que muestra dónde "pesa" más ese concepto.

### 10.3 Biblioteca de Conceptos

La **Biblioteca de Conceptos** es un repositorio centralizado de términos de investigación organizados por temáticas. Permite a los investigadores estandarizar sus búsquedas y reutilizar campos léxicos complejos.

#### Funcionalidades Principales

-   **🗂️ Organización Temática**: Los conceptos se agrupan en un acordeón interactivo (Naval, Arte, Administración, Ciencia, Sentimientos, etc.).
-   **🔍 Búsqueda Inteligente**: Localice términos rápidamente; el sistema expandirá automáticamente la temática correspondiente.
-   **🧠 Auto-detección de Temas**: Al escribir un concepto emocional (ej: "Miedo"), el sistema sugiere automáticamente la temática "Sentimientos y Emociones".
-   **⚡ Inserción Rápida**: Un solo clic en el icono del libro carga el concepto seleccionado directamente en el buscador de la topografía.
-   **📝 Gestión CRUD**: Añada, edite o elimine sus propios conceptos para personalizar su flujo de trabajo investigativo.

### Configuración Técnica

- **Threshold**: 0.01 (ajustado para más resultados)
- **Auto-inicialización**: Vectorizer se carga en primera consulta
- **Límite**: 20 resultados por búsqueda
- **Performance**: <1s en corpus de 659 documentos

### Tips para Mejores Resultados

✅ **Buenas prácticas**:
- Usa frases completas, no solo palabras clave
- Describe lo que buscas con tus propias palabras
- Sé específico pero no demasiado restrictivo
- Prueba diferentes formas de expresar lo mismo

❌ **Evita**:
- Consultas de una sola palabra (usa búsqueda rápida)
- Queries muy largas (>200 caracteres)
- Búsquedas de códigos o números exactos

### Tecnología

- **Motor**: scikit-learn TF-IDF Vectorizer
- **Modelo**: Multilingual embeddings
- **Velocidad**: <1 segundo en 653 documentos
- **Idiomas**: Soporta español, inglés, italiano, francés

---

## 📖 Generador de Citas Bibliográficas

### Acceso

**Desde el listado**:
1. Haz clic en el icono de **comillas** junto al artículo
2. Se abre el generador de citas

**Ruta directa**: `/citar/<id>`

### Formatos Disponibles

#### 1. ISO 690 (Internacional) - Por Defecto
Estándar internacional para referencias bibliográficas.

**Ejemplo**:
```
GARCÍA, Juan. La tragedia del Sirio. La Nación. Buenos Aires, 15 agosto 1906, p. 3.
```

#### 2. APA 7ª Edición (Psicología, Ciencias Sociales)
**Ejemplo**:
```
García, J. (1906, agosto 15). La tragedia del Sirio. La Nación, p. 3.
```

#### 3. MLA 9ª Edición (Humanidades, Literatura)
**Ejemplo**:
```
García, Juan. "La tragedia del Sirio." La Nación, 15 ago. 1906, p. 3.
```

#### 4. Chicago 17ª Edición (Historia, Humanidades)
**Ejemplo**:
```
García, Juan. "La tragedia del Sirio." La Nación (Buenos Aires), agosto 15, 1906.
```

#### 5. Harvard (Autor-Fecha)
**Ejemplo**:
```
García, J., 1906. La tragedia del Sirio. La Nación, 15 agosto, p.3.
```

#### 6. Vancouver (Medicina, Ciencias)
**Ejemplo**:
```
García J. La tragedia del Sirio. La Nación. 1906 ago 15;3.
```

#### 7. Hemerográfico (Prensa Histórica)
Formato especializado para hemerografía.

**Ejemplo**:
```
La Nación (Buenos Aires), 15 de agosto de 1906, p. 3. "La tragedia del Sirio" por Juan García.
```

### Opción: Sin Cita

Selecciona **"-- Sin cita (no generar) --"** si solo quieres ver los datos sin formato de cita.

### Copiar al Portapapeles

1. Selecciona el formato deseado
2. La cita se genera automáticamente
3. Haz clic en **Copiar al Portapapeles**
4. Pega donde necesites (Ctrl+V)

### Exportar Múltiples Citas

Para generar citas de múltiples artículos:
1. Usa la exportación BibTeX o RIS
2. Importa en tu gestor bibliográfico (Zotero, Mendeley)
3. Genera las citas desde allí

---

## 📊 Análisis y Estadísticas

### Dashboard Estadístico

**Ruta**: Menú **Acciones** → **Estadísticas**

#### Métricas Generales (Cards Superiores)

- **Noticias Totales**: Contador total de artículos en el proyecto
- **Medios Diferentes**: Número de periódicos/revistas únicos
- **Ciudades de Origen**: Número de ciudades únicas
- **Rango Temporal**: Fechas mínima y máxima

#### Gráficos Disponibles

**1. Distribución Temporal**
- Gráfico de línea que muestra artículos por año
- Identifica picos de cobertura
- Útil para análisis histórico

**2. Distribución por Medio**
- Gráfico de barras con los 10 medios principales
- Muestra volumen de artículos por periódico
- Identifica fuentes principales

**3. Distribución Geográfica**
- Gráfico de barras con las 10 ciudades principales
- Muestra concentración geográfica
- Útil para mapeo de difusión

**4. Distribución por Idioma**
- Gráfico de pastel con proporciones
- Muestra diversidad lingüística
- Identifica idiomas predominantes

**5. Frecuencia de Palabras Clave**
- Top 20 palabras clave más usadas
- Gráfico de barras horizontal
- Identifica temas recurrentes

**6. Evolución Mensual**
- Gráfico de línea con desglose mes a mes
- Identifica patrones estacionales
- Análisis de tendencias

### Exportar Gráficos

1. Haz clic en **Exportar datos**
2. Se descarga CSV con los datos de todos los gráficos
3. Usa en Excel, R, Python para análisis adicional

### Nube de Palabras

**Ruta**: Menú **Acciones** → **Nube de Palabras**

1. Se genera automáticamente basada en:
   - Títulos de artículos
   - Palabras clave
   - Contenido de artículos

2. Tamaño de palabra = frecuencia

3. Configuración:
   - Palabras vacías filtradas (stop words)
   - Mínimo 3 caracteres
   - Top 100 palabras más frecuentes

4. Uso:
   - Identifica temas dominantes
   - Descubre patrones temáticos
   - Visualización rápida de corpus

---

## 🔬 Análisis NLP con spaCy

### ¿Qué es el Análisis NLP?

El **Procesamiento de Lenguaje Natural (NLP)** permite extraer información estructurada de textos no estructurados. hesiOX utiliza **spaCy 3.8** con el modelo **es_core_news_md** para análisis avanzado en español.

### Características del Sistema

- **Modelo**: es_core_news_md v3.8.0
- **Idioma**: Español
- **Capacidades**:
  - Extracción de entidades nombradas (NER)
  - Análisis de dependencias sintácticas
  - Lematización y tokenización
  - Part-of-Speech tagging

### Red de Entidades

**Ruta**: Menú **Análisis** → **Red de Entidades**

#### Tipos de Entidades Extraídas

1. **PER (Personas)**:
   - Nombres de personas mencionadas
   - Autores, protagonistas, personajes históricos
   - Ejemplo: "García Lorca", "Alfonso XIII"

2. **LOC (Lugares)**:
   - Ubicaciones geográficas
   - Ciudades, países, regiones
   - Ejemplo: "Madrid", "Río de la Plata", "España"

3. **ORG (Organizaciones)**:
   - Instituciones, empresas, partidos
   - Gobiernos, universidades, asociaciones
   - Ejemplo: "Universidad de Salamanca", "Cruz Roja"

#### Visualización de Red con D3.js

La red de entidades muestra:

- **Nodos**: Círculos representan entidades
  - Tamaño = frecuencia de aparición
  - Color = tipo de entidad (PER/LOC/ORG)
  
- **Enlaces**: Líneas conectan entidades que co-ocurren
  - Grosor = frecuencia de co-ocurrencia
  - Indica relaciones entre entidades

#### Cómo Usar

1. Ve a **Análisis** → **Red de Entidades**
2. El sistema procesa **los primeros 30 documentos** del corpus
3. Extrae entidades de **los primeros 1000 caracteres** de cada documento
4. Genera una red interactiva:
   - **Arrastra nodos** para reorganizar
   - **Zoom** con la rueda del ratón
   - **Hover** sobre nodos para ver detalles
   - **Click** en nodos para resaltar conexiones

#### Performance

- **Corpus analizado**: 30 documentos (configurable)
- **Texto por documento**: Primeros 1000 caracteres
- **Tiempo de procesamiento**: 3-5 segundos
- **Entidades extraídas**: Variable según corpus

#### Casos de Uso

✅ **Descubrir personajes clave** en un corpus histórico
✅ **Identificar lugares mencionados** con frecuencia
✅ **Mapear organizaciones** relevantes en el periodo estudiado
✅ **Analizar co-ocurrencias** entre entidades (quién aparece con quién)
✅ **Detectar relaciones ocultas** en el corpus

### Requisitos

⚠️ **Importante**: Para usar el análisis NLP, asegúrate de que el modelo spaCy está instalado:

```bash
python -m spacy download es_core_news_md
```

Si el modelo no está instalado, la función mostrará un mensaje de error.

---

## 🗺️ Visualizaciones

### Mapa Geográfico

**Ruta**: Menú **Acciones** → **Mapa**

#### Características

- **Motor**: Leaflet.js con OpenStreetMap
- **Markers**: Un pin por cada ciudad con artículos
- **Clustering**: Agrupa pins cercanos automáticamente
- **Popups**: Haz clic en un pin para ver:
  - Nombre de la ciudad
  - Número de artículos
  - Lista de títulos
  - Enlaces a artículos

#### Controles Avanzados

- **📍 Filtro de Noticias**: Desplegable que permite filtrar los puntos del mapa para mostrar solo aquellos que pertenecen a un **texto o noticia específico**.
- **📐 Elipse de Desviación Estándar (SDE)**: Visualización que muestra la tendencia espacial (centro medio, dispersión y orientación) del conjunto de datos filtrado.
- **🤖 IA ADVANCED**: Botón que activa la geocodificación de alta precisión mediante IA (spaCy + Gemini), permitiendo la detección automática de lugares complejos en el texto.

#### Navegación

- **Zoom**: Rueda del ratón o botones +/-
- **Pan**: Arrastra el mapa
- **Click en cluster**: Expande para ver pins individuales
- **Click en pin**: Muestra popup con detalles

#### Geocodificación

- Sistema de geocodificación automática integrado
- Base de datos de 1400+ ciudades
- Coordenadas precisas lat/long
- Si una ciudad no está en la BD, no aparece en el mapa

### Gestión Dinámica de Tipos de Ubicación

**Novedad v5.0.0**: Sistema de gestión centralizada de tipos geográficos.

#### Acceso

1. Ve al **Gestor de Ubicaciones**
2. Haz clic en el botón **"Tipos"** en la barra superior
3. Se abrirá el modal de gestión de tipos

#### Añadir Nuevo Tipo

1. Clic en **"Añadir Nuevo Tipo"**
2. Completa los campos:
   - **Código**: Identificador único (minúsculas y guiones bajos). Ej: `gulf`, `country`, `archipelago`
   - **Nombre**: Nombre legible. Ej: `Golfo`, `País`, `Archipiélago`
   - **Categoría**: Grupo organizativo
     - Ciudades y Poblaciones
     - Vías
     - Edificios  
     - Geografía Natural
     - Hidrografía
     - Administrativo
     - Otros
   - **Icono**: Clase Font Awesome (opcional). Ej: `fa-solid fa-water`
   - **Orden**: Número para ordenar (menor = primero)
3. Clic en **"Guardar"**

#### Editar Tipo Existente

1. En la tabla de tipos, busca el tipo a modificar
2. Clic en el botón **✏️ Editar**
3. Modifica los campos necesarios (el código no se puede cambiar)
4. Clic en **"Guardar"**

#### Eliminar Tipo

1. En la tabla de tipos, clic en **🗑️ Eliminar**
2. Confirma la acción

**Nota**: Los tipos eliminados solo se desactivan. Los datos que ya usan ese tipo se mantienen intactos.

#### Tipos Predefinidos

El sistema incluye más de 100 tipos predefinidos:

- **Ciudades**: ciudad, pueblo, aldea, caserío
- **Hidrografía**: río, lago, mar, océano, golfo, isla, playa
- **Administrativo**: país, estado, provincia, región
- **Geografía Natural**: montaña, pico, volcán, valle, cueva, cabo
- **Edificios**: iglesia, castillo, hospital, faro, torre
- **Vías**: carretera, calle, autopista, sendero
- Y muchos más...

#### Ventajas

- **Sin código**: Añade tipos sin modificar archivos HTML o Python
- **Inmediato**: Los cambios se reflejan automáticamente en todos los selectores
- **Organizado**: Categorías claras y búsqueda por grupo
- **Iconos visuales**: Mejora la identificación rápida de tipos
- **Histórico preservado**: Los datos existentes nunca se pierden

### Gestión de Capas Externas (ArcGIS/QGIS)

jesiOX permite superponer capas geográficas externas para enriquecer el análisis del corpus con contexto territorial (ej: límites históricos, parcelarios, hidrografía).

#### Cómo Subir una Capa
1. En el Mapa del Corpus, pulsa el botón **"Capas"** de la barra superior.
2. Introduce un **Nombre** para la capa.
3. Selecciona el archivo (**GeoJSON**, **KML** o **SHP en ZIP**).
4. Elige un color identificativo.
5. Pulsa **Subir Capa**. El sistema la procesará y proyectará automáticamente.

#### Control y Visibilidad
- En la barra lateral de filtros del mapa, aparecerá una nueva sección de **Capas Externas**.
- Usa los interruptores (toggle) para mostrar u ocultar cada capa.
- Haz clic en cualquier elemento de la capa en el mapa para ver sus **Atributos Técnicos** en un popup.

#### Requisitos Técnicos
- El sistema utiliza `geopandas` en el servidor para la conversión automática.
- Se recomienda que los archivos no superen los 10MB para mantener la fluidez del navegador.

---

### 🎨 Digitalización Vectorial (Sistema GIS Profesional)

hesiOX incorpora un **sistema completo de digitalización vectorial** que permite crear y gestionar capas geográficas directamente sobre el mapa del corpus, siguiendo el flujo de trabajo de software GIS profesional (QGIS, ArcGIS).

#### ¿Qué es la Digitalización Vectorial?

La digitalización vectorial es el proceso de crear representaciones geométricas de elementos geográficos (puntos, líneas, polígonos) sobre un mapa. Es fundamental para:

- **Marcar ubicaciones específicas** mencionadas en el corpus
- **Trazar rutas históricas** de personajes o eventos
- **Delimitar áreas de influencia** territorial
- **Crear datos geográficos originales** para análisis espacial
- **Exportar capas personalizadas** para uso en otros GIS

#### Flujo de Trabajo Profesional

**1. Crear una Capa Vectorial**

Antes de digitalizar, debes crear una capa que contendrá tus elementos:

1. En el **Mapa del Corpus**, abre el menú desplegable **"Herramientas GIS"**
2. Selecciona **"CREAR NUEVA CAPA"**
3. En el modal de configuración, completa:
   - **Nombre de la capa**: Identificador descriptivo (ej: "Ruta del Quijote", "Ciudades mencionadas")
   - **Tipo de geometría**: Selecciona según tu necesidad:
     - 🟢 **Puntos**: Para ubicaciones específicas (ciudades, monumentos, eventos puntuales)
     - 🔵 **Líneas**: Para rutas, caminos, fronteras lineales, itinerarios
     - 🔴 **Polígonos**: Para áreas, territorios, regiones, zonas de influencia
   - **Color de visualización**: Elige un color identificativo (naranja por defecto)
   - **Descripción** (opcional): Contexto o propósito de la capa
4. Pulsa **"Crear Capa"**

**2. Digitalizar Elementos**

Una vez creada la capa, el sistema activa automáticamente el modo de digitalización:

##### **Digitalizar Puntos** 🟢
- **Acción**: Simplemente haz **clic** en el mapa donde desees colocar cada punto
- **Cada clic** crea un nuevo punto inmediatamente
- **Formulario**: Completa el nombre y descripción opcional antes de cada punto
- **Popup**: Al hacer clic sobre un punto creado, verás sus coordenadas geográficas

##### **Digitalizar Líneas** 🔵
- **Añadir vértices**: Haz **clic** sucesivos para añadir puntos de la línea
- **Visualización**: Verás una línea temporal punteada siguiendo el cursor
- **Finalizar**: Haz **doble clic** o pulsa el botón **"Finalizar"** en el panel
- **Estadística**: El sistema calcula automáticamente la **longitud en kilómetros**
- **Cancelar**: Pulsa **"Cancelar"** para descartar la línea actual

##### **Digitalizar Polígonos** 🔴
- **Añadir vértices**: Haz **clic** sucesivos para definir el perímetro
- **Mínimo**: Se requieren al menos **3 puntos**
- **Visualización**: Previsualización del polígono en tiempo real
- **Finalizar**: **Doble clic** o botón **"Finalizar"** cierra el polígono
- **Estadística**: Cálculo automático del **área en hectáreas**
- **Cancelar**: Descarta el polígono sin guardar

**3. Panel de Control de Digitalización**

Durante la digitalización, aparece un **panel Sirio-styled** con:

- **Estadísticas en tiempo real**:
  - Contador de elementos creados
  - Número de vértices del elemento actual
- **Campos de metadatos**:
  - Nombre del elemento
  - Descripción opcional
- **Controles**:
  - Botón **Finalizar** (líneas y polígonos)
  - Botón **Cancelar** para descartar el elemento actual

**4. Gestionar Capas Vectoriales**

Las capas creadas aparecen automáticamente en el **panel lateral "Filtros y Mapas"** con controles completos:

##### **Controles por Capa**

- **Toggle de visibilidad** ☑️: Muestra/oculta la capa en el mapa
- **Badge contador**: Indica el número de elementos en la capa
- **Indicador de color**: Muestra el color asignado a la capa
- **Icono de tipo**: Identifica visualmente el tipo de geometría (punto/línea/polígono)

##### **Botones de Acción**

- **Editar** ✏️: Reactiva el modo de digitalización para añadir más elementos
- **Exportar** 💾: Descarga la capa en formato **GeoJSON**
- **Eliminar** 🗑️: Borra la capa completa (requiere confirmación)

**5. Exportar Capas Vectoriales**

Cada capa se puede exportar individualmente:

1. Pulsa el botón **"Exportar"** en la fila de la capa
2. Se descarga un archivo **GeoJSON** con:
   - Todas las geometrías de la capa
   - Metadatos de cada elemento (nombre, descripción)
   - Métricas calculadas (longitudes, áreas)
   - Sistema de coordenadas **CRS84** (WGS 84)
   - Timestamp en el nombre del archivo

**Ejemplo de archivo exportado**:
```
Ruta_del_Quijote_2026-03-06.geojson
```

#### Características Avanzadas

##### **Múltiples Capas Simultáneas**

- Crea tantas capas como necesites
- Cada capa es independiente (geometría, color, elementos)
- Gestiona diferentes aspectos del análisis en capas separadas
- **Ejemplo**: Capa de "Ciudades" (puntos) + Capa de "Fronteras" (líneas) + Capa de "Territorios" (polígonos)

##### **Integración con Análisis del Corpus**

- Las capas vectoriales complementan los datos automáticos del corpus
- Digitaliza elementos **no detectados automáticamente** por el geocodificador
- Añade contexto geográfico **personalizado** a tu investigación
- Combina ubicaciones del corpus con capas históricas (límites, parcelarios)

##### **Diseño Responsivo**

- Soporte completo para **temas claro/oscuro**
- Interfaz adaptada al **sistema de diseño Sirio**
- Panel de digitalización con **estadísticas profesionales**
- Visualización optimizada en **diferentes resoluciones**

#### Casos de Uso Académicos

**1. Literatura de Viajes**

- Crea una capa de **puntos** para las ciudades visitadas
- Digitaliza la **línea** del itinerario seguido
- Exporta para análisis en herramientas GIS profesionales

**2. Historia Territorial**

- Delimita **polígonos** de territorios históricos mencionados
- Superpón con capas del corpus para análisis de referencias
- Compara extensiones territoriales en diferentes períodos

**3. Periodismo Histórico**

- Marca **puntos** de eventos noticiables
- Traza **líneas** de desplazamientos de corresponsales
- Define **polígonos** de áreas de conflicto o influencia

**4. Estudios Culturales**

- Digitaliza **puntos** de instituciones culturales
- Crea **polígonos** de barrios o distritos mencionados
- Exporta datos para visualizaciones externas

#### Interoperabilidad GIS

Las capas exportadas son compatibles con:

- **QGIS** (Software libre GIS de escritorio)
- **ArcGIS** (Software comercial profesional)
- **Leaflet.js** (Librería web de mapas)
- **Google Earth** (Importación vía conversión KML)
- **PostGIS** (Base de datos espacial PostgreSQL)
- **Mapbox** (Plataforma de mapas web)

#### Mejores Prácticas

1. **Nomenclatura clara**: Usa nombres descriptivos para capas y elementos
2. **Una geometría por capa**: No mezcles puntos, líneas y polígonos en la misma capa
3. **Documenta tus elementos**: Completa siempre el campo de descripción
4. **Exporta regularmente**: Guarda copias GeoJSON de tu trabajo
5. **Organiza por temas**: Crea capas separadas para diferentes aspectos del análisis
6. **Verifica coordenadas**: Usa el popup de elementos para validar posiciones

#### Limitaciones Conocidas

- No hay edición de elementos ya creados (solo añadir nuevos)
- No se soporta importación de capas externas para edición
- Las capas vectoriales no persisten en base de datos (solo exportación)
- No hay herramientas de snap o alineación automática

#### Roadmap Futuro

- **v2.8**: Edición de geometrías existentes
- **v2.9**: Persistencia en base de datos PostgreSQL/PostGIS
- **v3.0**: Análisis espacial (buffer, intersección, unión)
- **v3.1**: Importación de capas para edición
- **v3.2**: Herramientas de topología y validación

---

### Timeline (Línea de Tiempo)

**Ruta**: Menú **Acciones** → **Timeline**

#### Visualización

- Eje temporal horizontal
- Eventos representan artículos
- Escalado automático según rango de fechas
- Zoom y navegación temporal

#### Uso

- Identifica períodos de alta cobertura
- Encuentra gaps temporales
- Analiza cronología de eventos
- Detecta patrones históricos

---

## 📤 Exportación de Datos

### Formatos Disponibles

#### 1. BibTeX (.bib)

**Uso**: LaTeX, Overleaf, JabRef

**Características**:
- Formato estándar para documentos LaTeX
- Incluye todos los campos bibliográficos
- Compatible con \cite{} en LaTeX

**Exportar**:
1. Menú **Acciones** → **Exportar**
2. Selecciona **BibTeX**
3. Se descarga archivo `.bib`

**Ejemplo de entrada**:
```bibtex
@article{garcia1906tragedia,
  author = {García, Juan},
  title = {La tragedia del Sirio},
  journal = {La Nación},
  year = {1906},
  month = {agosto},
  day = {15},
  pages = {3},
  address = {Buenos Aires}
}
```

#### 2. RIS (.ris)

**Uso**: Zotero, Mendeley, EndNote, RefWorks

**Características**:
- Formato universal de gestores bibliográficos
- Importación directa en Zotero (arrastra y suelta)
- Preserva todos los metadatos

**Exportar**:
1. Menú **Acciones** → **Exportar**
2. Selecciona **RIS**
3. Importa en tu gestor bibliográfico

#### 3. CSV (.csv)

**Uso**: Excel, Google Sheets, análisis de datos

**Características**:
- Todos los campos en columnas
- Compatible con cualquier hoja de cálculo
- Codificación UTF-8 (acentos preservados)

**Columnas incluidas**:
- Número Referencia, Título, Medio, Fecha, Ciudad, País
- Idioma, Sección, Páginas, Autores, Palabras Clave
- Contenido, URL Hemeroteca, Época, Temáticas

**Exportar**:
1. Menú **Acciones** → **Exportar**
2. Selecciona **CSV**
3. Abre en Excel o Google Sheets

#### 4. JSON (.json)

**Uso**: Programación, APIs, análisis con Python/R

**Características**:
- Formato estructurado para desarrollo
- Ideal para procesamiento automatizado
- Incluye metadatos completos

**Exportar**:
1. Menú **Acciones** → **Exportar**
2. Selecciona **JSON**
3. Usa en scripts Python, R, JavaScript

### Exportación Selectiva

**Exportar solo artículos seleccionados**:
1. Marca checkboxes de artículos deseados
2. Botón **Lotes (N)** se habilita
3. Selecciona **Exportar seleccionados**
4. Elige formato
5. Solo se exportan los marcados

### Exportación Completa

Sin marcar ningún checkbox, la exportación incluye **todos los artículos del proyecto activo**.

---

## 🎨 Temas Visuales

hesiOX incluye 3 temas visuales diferentes para adaptarse a tus preferencias.

### Cambiar Tema

Botones en la esquina superior derecha de la navbar:

1. **Modo Web (Moderno)** - Icono de llama
   - Tema oscuro con acentos naranjas
   - Diseño limpio y moderno
   - Mejor para uso web general

2. **Modo Software (Gephi)** - Icono de monitor
   - Estilo de aplicación de escritorio
   - Inspirado en software de análisis de redes
   - Apariencia profesional y técnica

3. **Modo Retro (Win98)** - Icono de ventana
   - Nostalgia Windows 98
   - Bordes clásicos y colores vintage
   - Para los amantes del retro computing

### Persistencia

- El tema seleccionado se guarda en **LocalStorage**
- Se mantiene entre sesiones
- No necesitas iniciar sesión

---

## ⌨️ Atajos de Teclado

### Globales

- `Ctrl + S`: Guardar (al editar artículo/publicación)
- `Ctrl + F`: Buscar en página
- `Esc`: Cerrar modal activo
- `F5`: Recargar página

### En el Editor TinyMCE

- `Ctrl + B`: Negrita
- `Ctrl + I`: Cursiva
- `Ctrl + U`: Subrayado
- `Ctrl + Z`: Deshacer
- `Ctrl + Y`: Rehacer
- `Ctrl + K`: Insertar enlace

### En Listas

- `Clic + Shift + Clic`: Seleccionar rango de artículos
- `Ctrl + Clic`: Seleccionar múltiples no consecutivos

---

## 🔧 Solución de Problemas

### Problema: El OCR no funciona

**Síntomas**: Las imágenes se suben pero no se extrae texto

**Soluciones**:
1. Verifica que JavaScript esté habilitado
2. Espera 3-5 segundos por imagen (proceso en segundo plano)
3. Revisa la consola del navegador (F12) por errores
4. Prueba con una imagen más pequeña (<5MB)
5. Asegura que la imagen tenga texto legible

### Problema: Búsqueda semántica muy lenta

**Síntomas**: Más de 5 segundos para resultados

**Soluciones**:
1. Verifica tu conexión a internet
2. Cierra otras pestañas del navegador
3. Espera a que termine la indexación inicial
4. Reinicia el navegador si persiste

### Problema: No puedo eliminar un proyecto

**Síntomas**: El botón "Eliminar" está deshabilitado

**Causas posibles**:
1. **Es el proyecto activo**: Activa otro proyecto primero
2. **Es el único proyecto**: Debes tener al menos un proyecto
3. **No completaste la confirmación**: Escribe el nombre exacto + marca checkbox

### Problema: Las citas no se generan correctamente

**Síntomas**: Formato incorrecto o campos vacíos

**Soluciones**:
1. Verifica que el artículo tenga todos los campos requeridos:
   - Título, Medio, Fecha son obligatorios
2. Revisa el formato de fecha (DD/MM/AAAA)
3. Selecciona un formato diferente del dropdown
4. Refresca la página y vuelve a intentar

### Problema: Los filtros no funcionan

**Síntomas**: No se filtran resultados o muestra todos

**Soluciones**:
1. Haz clic en **Aplicar Filtros** después de seleccionar
2. Usa **Limpiar Filtros** y vuelve a intentar
3. Verifica que el campo tenga valores (no vacío)
4. Refresca la página (F5)

### Problema: Las imágenes no se muestran

**Síntomas**: Iconos rotos o no cargan

**Soluciones**:
1. Verifica la carpeta `static/uploads/` tenga permisos de lectura
2. Comprueba el espacio en disco del servidor
3. Revisa que las rutas sean correctas
4. Limpia caché del navegador (Ctrl + Shift + R)

### Problema: Error al exportar datos

**Síntomas**: Descarga no inicia o archivo vacío

**Soluciones**:
1. Verifica que haya artículos en el proyecto
2. Prueba con un formato diferente
3. Si exportas seleccionados, marca al menos uno
4. Desactiva bloqueadores de descargas
5. Usa un navegador diferente

### Obtener Más Ayuda

Si el problema persiste:
1. Consulta la sección **Ayuda → Preguntas Frecuentes**
2. Revisa el **CHANGELOG.md** para problemas conocidos
3. Contacta al desarrollador con:
   - Descripción del problema
   - Pasos para reproducirlo
   - Navegador y versión
   - Captura de pantalla de la consola (F12)

---

## 📞 Contacto y Soporte

**Desarrollador**: David García Pascual  
**Proyecto**: hesiOX v1.4.5  
**Email**: [tu-email@universidad.edu]  
**Blog**: https://sirio.hypotheses.org

**Documentación adicional**:
- [INSTALACION.md](INSTALACION.md) - Guía de instalación completa
- [CHANGELOG.md](CHANGELOG.md) - Historial de versiones
- [CONTRIBUTING.md](CONTRIBUTING.md) - Guía para contribuidores
- [README.md](README.md) - Documentación para desarrolladores

---

**Última actualización**: 15 de febrero de 2026  
**Versión del manual**: 2.7.0

---

_hesiOX - Digitalizando el pasado, construyendo el futuro de la investigación académica_
