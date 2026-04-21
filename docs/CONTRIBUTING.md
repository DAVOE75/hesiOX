# 🤝 Guía de Contribución - hesiOX v1.4.5

¡Gracias por tu interés en contribuir a hesiOX! Este documento te guiará en el proceso de contribución al proyecto.

---

## 📋 Tabla de Contenidos

1. [Código de Conducta](#código-de-conducta)
2. [Cómo Empezar](#cómo-empezar)
3. [Estructura del Proyecto](#estructura-del-proyecto)
4. [Convenciones de Código](#convenciones-de-código)
5. [Flujo de Trabajo Git](#flujo-de-trabajo-git)
6. [Testing](#testing)
7. [Documentación](#documentación)
8. [Roadmap y Prioridades](#roadmap-y-prioridades)

---

## 📜 Código de Conducta

### Nuestro Compromiso

Nos comprometemos a mantener un entorno abierto, acogedor y libre de acoso para todos los colaboradores, independientemente de:
- Experiencia técnica
- Género, identidad o expresión de género
- Orientación sexual
- Capacidades físicas
- Apariencia física
- Etnia, nacionalidad
- Edad, religión

### Comportamiento Esperado

✅ **SÍ**:
- Usa lenguaje inclusivo y respetuoso
- Acepta críticas constructivas
- Enfócate en lo mejor para la comunidad
- Muestra empatía hacia otros colaboradores
- Reporta comportamientos inapropiados

❌ **NO**:
- Lenguaje o imágenes sexualizadas
- Trolling, insultos o ataques personales
- Acoso público o privado
- Publicar información privada de otros sin permiso
- Conducta no profesional o inapropiada

### Reporte de Problemas

Si experimentas o presencias comportamiento inapropiado, contacta a: [tu@email.com]

---

## 🚀 Cómo Empezar

### 1. Fork y Clone

```bash
# Fork el repositorio en GitHub (botón "Fork")

# Clona tu fork
git clone https://github.com/TU_USUARIO/app_bibliografia.git
cd app_bibliografia

# Añade el repositorio original como upstream
git remote add upstream https://github.com/USUARIO_ORIGINAL/app_bibliografia.git
```

### 2. Configurar Entorno de Desarrollo

Sigue la guía completa en `INSTALACION.md`:

```bash
# Crear entorno virtual
python -m venv venv
venv\Scripts\activate  # Windows

# Instalar dependencias
pip install -r requirements.txt

# Instalar modelo NLP
python -m spacy download es_core_news_md

# Configurar PostgreSQL (ver INSTALACION.md)

# Crear .env (ver ejemplo en INSTALACION.md)

# Ejecutar aplicación
python app.py
```

### 3. Crear Rama de Trabajo

```bash
# Sincroniza con upstream
git fetch upstream
git checkout main
git merge upstream/main

# Crea rama descriptiva
git checkout -b feature/nombre-funcionalidad
# o
git checkout -b fix/descripcion-bug
```

---

## 📁 Estructura del Proyecto

```
app_bibliografia/
│
├── app.py                    # Aplicación Flask principal (2500+ líneas)
├── pdf_generator.py          # Generación de PDFs con ReportLab
│
├── templates/                # Plantillas Jinja2
│   ├── base.html            # Template base con navbar y estilos
│   ├── home.html            # Página de inicio
│   ├── login.html           # Sistema de autenticación
│   ├── new.html             # Formulario nuevo artículo prensa
│   ├── nueva_publicacion.html  # Formulario nueva publicación académica
│   ├── hemerotecas.html     # Listado de hemerotecas
│   ├── analisis.html        # Análisis y estadísticas
│   ├── bibliografia.html    # Generador de citas
│   └── ...                  # 30+ plantillas más
│
├── static/                  # Archivos estáticos
│   ├── style-hesirox.css    # Estilos tema Tech (dark)
│   ├── style-proyecto.css   # Estilos tema Proyecto (dark)
│   ├── flags.css            # Banderas de países (14)
│   │
│   ├── js/                  # JavaScript modular
│   │   ├── form-autocomplete.js      # Autocompletado inteligente
│   │   ├── form-autosave.js          # Autosave cada 30s
│   │   ├── form-citation-preview.js  # Vista previa de citas
│   │   ├── citation-generator.js     # Generador ISO/APA/MLA/Chicago
│   │   ├── export-utils.js           # Exportación BibTeX/RIS/CSV/JSON
│   │   ├── analisis.js               # Gráficos Chart.js
│   │   ├── semantic-search.js        # Búsqueda TF-IDF con debounce
│   │   ├── network-analysis.js       # Red de entidades D3.js
│   │   └── ...                       # 20+ módulos JS
│   │
│   ├── img/                 # Imágenes del proyecto
│   │   └── flags/           # Banderas PNG (14 países)
│   │
│   └── uploads/             # Imágenes OCR subidas por usuarios
│
├── migrations/              # Migraciones SQL
│   ├── add_hemerotecas.sql          # Sistema de hemerotecas
│   ├── add_articulos_cientificos.sql # Artículos científicos
│   └── add_proyectos_system.sql     # Multi-proyecto
│
├── db_backups/              # Backups automáticos de BD
│
├── exports/                 # Archivos exportados temporales
│
├── docs/                    # Documentación
│   ├── INSTALACION.md       # Guía de instalación
│   ├── MANUAL_USUARIO.md    # Manual completo (1100+ líneas)
│   ├── CONTRIBUTING.md      # Esta guía
│   ├── CHANGELOG.md         # Historial de versiones
│   └── README.md            # Descripción general
│
├── .env                     # Variables de entorno (NO subir a Git)
├── .gitignore               # Archivos ignorados
├── requirements.txt         # Dependencias Python
└── pyrightconfig.json       # Configuración Pylance
```

### Flujo de Datos

```
Usuario → Flask Routes (app.py) → SQLAlchemy ORM → PostgreSQL
                ↓
         Jinja2 Templates → HTML + CSS + JS
                ↓
         JavaScript Modules → AJAX → Flask API
                ↓
         spaCy NLP / TF-IDF / NetworkX → Análisis
                ↓
         Chart.js / D3.js / Leaflet → Visualizaciones
```

---

## 🎨 Convenciones de Código

### Python (Backend)

Seguimos **PEP 8** con algunas adaptaciones:

```python
# ✅ Nombres de funciones: snake_case
def generar_cita_apa(publicacion):
    pass

# ✅ Nombres de clases: PascalCase (SQLAlchemy)
class ArticuloPrensa(db.Model):
    __tablename__ = 'articulos_prensa'

# ✅ Constantes: UPPER_CASE
MAX_UPLOAD_SIZE = 5 * 1024 * 1024  # 5 MB

# ✅ Docstrings: Google Style
def extraer_entidades_nlp(texto, modelo_spacy):
    """
    Extrae entidades nombradas (PER, LOC, ORG) de un texto.

    Args:
        texto (str): Texto a analizar.
        modelo_spacy: Modelo spaCy cargado (es_core_news_md).

    Returns:
        dict: Diccionario con listas de entidades por tipo.
            {
                'PER': ['García Lorca', 'Alfonso XIII'],
                'LOC': ['Madrid', 'España'],
                'ORG': ['Universidad de Salamanca']
            }

    Raises:
        ValueError: Si el texto está vacío.
    """
    pass

# ✅ Type hints cuando sea posible (Python 3.10+)
from typing import List, Dict, Optional

def buscar_semantico(query: str, threshold: float = 0.01) -> List[Dict]:
    pass

# ✅ Rutas Flask: kebab-case en URLs
@app.route('/analisis/red-entidades')
def red_entidades():
    pass
```

### JavaScript (Frontend)

```javascript
// ✅ Variables: camelCase
const formArticulo = document.getElementById('form-articulo');

// ✅ Constantes: UPPER_SNAKE_CASE
const DEBOUNCE_DELAY = 150;
const API_ENDPOINT = '/api/buscar-semantico';

// ✅ Funciones: camelCase
function aplicarDebounce(callback, delay) {
    let timeoutId;
    return function (...args) {
        clearTimeout(timeoutId);
        timeoutId = setTimeout(() => callback.apply(this, args), delay);
    };
}

// ✅ Clases: PascalCase
class CitationGenerator {
    constructor(formato) {
        this.formato = formato;
    }

    generarCita(datos) {
        // ...
    }
}

// ✅ Comentarios JSDoc
/**
 * Genera una red de entidades con D3.js
 * @param {Array} entidades - Array de objetos {text, type, count}
 * @param {string} containerId - ID del contenedor SVG
 * @returns {void}
 */
function generarRedEntidades(entidades, containerId) {
    // ...
}

// ✅ Promesas y async/await
async function buscarSemantico(query) {
    try {
        const response = await fetch(`/api/buscar?q=${encodeURIComponent(query)}`);
        if (!response.ok) throw new Error('Error en búsqueda');
        const data = await response.json();
        return data.resultados;
    } catch (error) {
        console.error('Error:', error);
        mostrarNotificacion('Error en búsqueda semántica', 'error');
    }
}
```

### HTML/Jinja2 (Templates)

```html
<!-- ✅ Indentación: 2 espacios -->
<div class="container">
  <div class="row">
    <div class="col-md-6">
      <!-- Contenido -->
    </div>
  </div>
</div>

<!-- ✅ Clases CSS: kebab-case -->
<button class="btn-primary btn-lg btn-guardar">Guardar</button>

<!-- ✅ IDs: kebab-case -->
<input type="text" id="titulo-articulo" name="titulo">

<!-- ✅ Variables Jinja2: snake_case (match Python) -->
{% for articulo in articulos_prensa %}
  <h3>{{ articulo.titulo }}</h3>
  <p>{{ articulo.fecha_publicacion|fecha_espanol }}</p>
{% endfor %}

<!-- ✅ Bloques Jinja2: descriptivos -->
{% block contenido_principal %}
  <!-- Contenido específico de la página -->
{% endblock %}

<!-- ✅ Includes: usar paths relativos -->
{% include '_tabla.html' %}
{% include '_choices_includes.html' %}
```

### CSS

```css
/* ✅ Variables CSS: kebab-case con prefijo --proyecto- */
:root {
  --proyecto-bg-panel: #1e1e1e;
  --proyecto-bg-input: #252525;
  --proyecto-accent: #ff9800;
  --proyecto-text: #e0e0e0;
  --proyecto-border: #444;
}

/* ✅ Clases: BEM-like (bloque__elemento--modificador) */
.panel-herramientas {
  /* Bloque */
}

.panel-herramientas__boton {
  /* Elemento */
}

.panel-herramientas__boton--activo {
  /* Modificador */
}

/* ✅ Ordenar propiedades alfabéticamente */
.card {
  background-color: var(--proyecto-bg-panel);
  border: 1px solid var(--proyecto-border);
  border-radius: 8px;
  color: var(--proyecto-text);
  padding: 1rem;
}

/* ✅ Media queries al final del archivo */
@media (max-width: 768px) {
  .panel-herramientas {
    height: auto;
  }
}
```

### SQL (Migraciones)

```sql
-- ✅ Nombres de tablas: snake_case plural
CREATE TABLE articulos_prensa (
    id SERIAL PRIMARY KEY,
    titulo VARCHAR(500) NOT NULL,
    fecha_publicacion DATE
);

-- ✅ Nombres de columnas: snake_case
ALTER TABLE articulos_prensa
ADD COLUMN hemeroteca_id INTEGER REFERENCES hemerotecas(id);

-- ✅ Índices: idx_tabla_columna
CREATE INDEX idx_articulos_fecha ON articulos_prensa(fecha_publicacion);

-- ✅ Foreign keys: fk_tabla_columna
ALTER TABLE articulos_prensa
ADD CONSTRAINT fk_articulos_hemeroteca 
FOREIGN KEY (hemeroteca_id) REFERENCES hemerotecas(id);

-- ✅ Comentarios descriptivos
-- Añade sistema de hemerotecas digitales para vincular artículos a fuentes
-- Incluye 14 países con banderas y URL de acceso directo
```

---

## 🔀 Flujo de Trabajo Git

### Commits

Usamos **Conventional Commits**:

```bash
# ✅ Formato: <tipo>(<scope>): <descripción>

# Tipos principales:
feat:     # Nueva funcionalidad
fix:      # Corrección de bug
docs:     # Cambios en documentación
style:    # Formato, punto y coma, etc. (no afecta código)
refactor: # Refactorización (ni feat ni fix)
perf:     # Mejora de performance
test:     # Añadir/corregir tests
chore:    # Tareas de mantenimiento

# Ejemplos:
git commit -m "feat(nlp): añadir extracción de entidades con spaCy"
git commit -m "fix(búsqueda): corregir debounce en inputs múltiples"
git commit -m "docs(manual): actualizar sección de hemerotecas"
git commit -m "style(css): aplicar variables --proyecto-* en cita.html"
git commit -m "perf(búsqueda): optimizar TF-IDF con umbral 0.01"
git commit -m "refactor(app): modularizar rutas en blueprints"
```

### Branches

```bash
# Ramas principales
main          # Producción (solo merges de release)
develop       # Desarrollo (integración de features)

# Ramas de trabajo (crear desde develop)
feature/<nombre>    # Nueva funcionalidad
fix/<nombre>        # Corrección de bug
docs/<nombre>       # Documentación
refactor/<nombre>   # Refactorización

# Ejemplos:
git checkout -b feature/sistema-backup-automatico
git checkout -b fix/error-exportacion-bibtex
git checkout -b docs/actualizar-instalacion-windows
git checkout -b refactor/separar-rutas-api
```

### Pull Requests

1. **Título Descriptivo**:
   ```
   feat(hemerotecas): sistema de migración entre proyectos
   ```

2. **Descripción Completa**:
   ```markdown
   ## Cambios
   - Añadida ruta `/hemerotecas/migrar` para trasladar artículos
   - Formulario con selección de hemeroteca origen/destino
   - Validación de permisos de usuario
   - Actualización en batch con transacción SQL
   
   ## Testing
   - Probado con 150 artículos (migración exitosa en 2s)
   - Verificado rollback en caso de error
   
   ## Screenshots
   ![Formulario de migración](url_imagen)
   
   ## Checklist
   - [x] Código sigue convenciones
   - [x] Tests añadidos/actualizados
   - [x] Documentación actualizada
   - [x] Sin warnings de linter
   ```

3. **Review Process**:
   - Al menos 1 aprobación requerida
   - CI/CD debe pasar (si está configurado)
   - Resolver conversaciones antes de merge
   - Squash commits si hay muchos pequeños

---

## 🧪 Testing

### Estructura de Tests (futuro)

```
tests/
├── test_app.py              # Tests de rutas Flask
├── test_models.py           # Tests de modelos SQLAlchemy
├── test_nlp.py              # Tests de análisis NLP
├── test_export.py           # Tests de exportación
└── test_frontend.py         # Tests de JS (Selenium)
```

### Ejecutar Tests

```bash
# Instalar pytest
pip install pytest pytest-flask pytest-cov

# Ejecutar todos los tests
pytest

# Con cobertura
pytest --cov=app --cov-report=html

# Test específico
pytest tests/test_nlp.py::test_extraer_entidades
```

### Ejemplo de Test

```python
import pytest
from app import app, db
from models import ArticuloPrensa

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
        yield client
        with app.app_context():
            db.drop_all()

def test_crear_articulo(client):
    """Test crear nuevo artículo de prensa"""
    response = client.post('/new', data={
        'titulo': 'Test Artículo',
        'fecha': '2025-12-03',
        'periodico': 'El País',
        'contenido': 'Contenido de prueba'
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert b'Test Artículo' in response.data
    
    # Verificar en BD
    articulo = ArticuloPrensa.query.filter_by(titulo='Test Artículo').first()
    assert articulo is not None
    assert articulo.periodico == 'El País'
```

---

## 📝 Documentación

### Archivos a Actualizar

Cuando hagas cambios significativos, actualiza:

1. **CHANGELOG.md**: Añade entrada en sección `[Unreleased]`
   ```markdown
   ## [Unreleased]
   ### Añadido
   - Sistema de migración de artículos entre hemerotecas
   ### Corregido
   - Error en exportación BibTeX con caracteres especiales
   ```

2. **MANUAL_USUARIO.md**: Si hay nueva funcionalidad visible
   - Añade sección explicando la nueva función
   - Incluye screenshots si es necesario
   - Actualiza índice

3. **README.md**: Si cambia stack tecnológico, requisitos, o visión general
   - Actualiza badges si cambia versión
   - Añade nuevas tecnologías al stack
   - Actualiza roadmap si se completa algo

4. **Docstrings en Código**: Siempre documenta funciones públicas
   ```python
   def funcion_publica(arg1, arg2):
       """
       Descripción breve.

       Args:
           arg1 (tipo): Descripción.
           arg2 (tipo): Descripción.

       Returns:
           tipo: Descripción del retorno.

       Raises:
           ErrorTipo: Cuándo se lanza.
       """
       pass
   ```

---

## 🗺️ Roadmap y Prioridades

### v1.5.0 (Próxima versión - Q1 2025)

**Alta prioridad** 🔴:
- [ ] Sistema de ayuda contextual (tooltips, guías interactivas)
- [ ] Página de documentación integrada (MANUAL_USUARIO.md renderizado)
- [ ] Importador CSV masivo de artículos
- [ ] Sistema de backups automáticos (cron jobs)

**Media prioridad** 🟡:
- [ ] Tests unitarios (coverage >80%)
- [ ] API RESTful completa (endpoints JSON)
- [ ] Sistema de notificaciones (toast messages)
- [ ] Editor de temas personalizados (CSS custom)

**Baja prioridad** 🟢:
- [ ] Exportación a Zotero directo (plugin)
- [ ] Análisis de sentimiento (VADER/TextBlob)
- [ ] Gráficos avanzados (Sankey, choropleth)
- [ ] Sistema de comentarios y anotaciones

### Áreas que Necesitan Contribuciones

🆘 **Ayuda especialmente bienvenida en**:

1. **Testing**: Escribir tests unitarios y de integración
2. **Documentación**: Traducir manual al inglés
3. **Accesibilidad**: Mejorar ARIA labels, navegación por teclado
4. **Performance**: Optimizar queries SQL, lazy loading
5. **Frontend**: Mejorar responsiveness móvil
6. **i18n**: Internacionalización (inglés, francés, portugués)

---

## 🎓 Recursos para Nuevos Contribuyentes

### Tecnologías Principales

- **Python/Flask**: [Tutorial oficial](https://flask.palletsprojects.com/tutorial/)
- **SQLAlchemy**: [Documentación](https://docs.sqlalchemy.org/)
- **spaCy**: [Guía de inicio](https://spacy.io/usage)
- **Bootstrap 5**: [Documentación](https://getbootstrap.com/docs/5.3/)
- **D3.js**: [Tutoriales](https://d3js.org/)
- **Jinja2**: [Template Designer](https://jinja.palletsprojects.com/templates/)

### Issues para Empezar

Busca issues etiquetados:
- `good first issue`: Ideal para nuevos contribuyentes
- `help wanted`: Ayuda necesaria
- `documentation`: Mejoras de docs (no requiere código)
- `bug`: Reporte de errores para investigar

---

## 📬 Contacto y Soporte

- **Email**: [tu@email.com]
- **GitHub Issues**: Para bugs y feature requests
- **GitHub Discussions**: Para preguntas y discusiones generales
- **Twitter**: [@tu_usuario] (opcional)

---

## 📄 Licencia

Al contribuir a hesiOX, aceptas que tus contribuciones se licencien bajo **GPL v3**, la misma licencia del proyecto.

---

**¡Gracias por contribuir a hesiOX! 🎉**

Cada contribución, grande o pequeña, hace mejor este proyecto para toda la comunidad de Humanidades Digitales.
