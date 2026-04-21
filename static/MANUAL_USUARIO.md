# 📘 Manual de Usuario - hesiOX v1.4.5

**Sistema de Gestión de Referencias Bibliográficas para Humanidades Digitales**

**Última actualización**: 3 de diciembre de 2025

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
10. [Búsqueda Semántica](#búsqueda-semántica)
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
- **🧠 Búsqueda Semántica**: Motor NLP con TF-IDF (659 docs indexados, <1s respuesta)
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

#### Campos del Formulario

**Identificación**:
- **Número de Referencia**: Código único para el artículo (auto-sugerido)
- **Título**: Título completo del artículo
- **Medio**: Nombre del periódico/revista
- **Sección**: Sección del periódico (opcional)

**Información Temporal**:
- **Fecha**: Fecha de publicación (formato: DD/MM/AAAA)
- **Época**: Siglo/período histórico (autocompletar activado)

**Información Geográfica**:
- **Ciudad**: Ciudad de publicación
- **País**: País de publicación
- **Idioma**: Idioma del artículo (autocompletar con 50+ idiomas)

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

## 🧠 Búsqueda Semántica

### ¿Qué es la Búsqueda Semántica?

A diferencia de la búsqueda tradicional que solo busca palabras exactas, la búsqueda semántica **entiende el significado** y encuentra contenido relacionado aunque no contenga las palabras exactas.

**Ejemplo**:
- Búsqueda: "tragedia marítima"
- Encuentra: artículos sobre "naufragio", "hundimiento", "accidente naval", "catástrofe en el mar"

### Cómo Usar

**Ruta**: Menú **Acciones** → **Búsqueda Semántica**

1. Escribe tu consulta en **lenguaje natural**:
   - "artículos sobre inmigración a Argentina"
   - "noticias de rescate de náufragos"
   - "opiniones sobre la tragedia"

2. Haz clic en **Buscar** o presiona Enter

3. El sistema:
   - Convierte tu consulta en vectores TF-IDF
   - Compara con **659 documentos indexados**
   - Calcula similitud semántica (coseno)
   - Ordena por relevancia
   - **Respuesta <1 segundo**

4. Resultados muestran:
   - **Score de similitud** (0-100%, ej: 16.1%, 8.8%, 6.8%)
   - Título del artículo
   - Extracto relevante
   - Fecha y medio
   - Enlace para ver completo

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

**Última actualización**: 3 de diciembre de 2025  
**Versión del manual**: 1.4.5

---

_hesiOX - Digitalizando el pasado, construyendo el futuro de la investigación académica_
