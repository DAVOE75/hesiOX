# Implementación de Clasificación de Tipos de Lugar

## Cambios Realizados

### 1. Base de Datos
- **Nuevo campo**: `tipo_lugar` (VARCHAR(50)) en tabla `lugar_noticia`
- **Valores posibles**: city, town, village, road, building, church, mountain, river, island, etc.
- **Default**: 'unknown'

### 2. Backend (Python/Flask)
- **models.py**: Agregado campo `tipo_lugar` al modelo `LugarNoticia`
- **routes/noticias.py**: 
  - Captura automática del tipo desde API Nominatim durante geocodificación
  - Inclusión de `tipo_lugar` en respuesta JSON de `/cartografia_corpus_api`

### 3. Frontend (JavaScript)
- **Funciones helper**:
  - `getTipoLugarIcon(tipo)`: Retorna clase Font Awesome según el tipo
  - `getTipoLugarColor(tipo)`: Retorna clase de color CSS
- **UI Mejorada**:
  - Iconos profesionales (Font Awesome) visibles en cada fila de la tabla
  - Filtro selector por categoría de lugar
  - Tooltip con nombre del tipo al pasar el cursor

### 4. Scripts de Migración
- `scripts/add_tipo_lugar_migration.sql`: Migración SQL
- `scripts/classify_existing_locations.py`: Script para clasificar ubicaciones existentes

## Instalación

### Paso 1: Ejecutar Migración SQL

```bash
cd /opt/hesiox
psql -U tu_usuario -d tu_database -f scripts/add_tipo_lugar_migration.sql
```

O alternativamente:

```bash
cd /opt/hesiox
sqlite3 noticias.db < scripts/add_tipo_lugar_migration.sql  # Si usas SQLite
```

### Paso 2: Clasificar Ubicaciones Existentes (Opcional)

**ADVERTENCIA**: Este proceso puede tardar varios minutos dependiendo del número de ubicaciones. Respeta límite de 1 req/seg de Nominatim.

```bash
cd /opt/hesiox
python3 scripts/classify_existing_locations.py
```

## Iconografía Profesional

### Poblaciones
- 🏙️ **Ciudad** (`city`): `fa-solid fa-city`
- 🏘️ **Localidad** (`town`): `fa-solid fa-building`
- 🏡 **Pueblo** (`village`): `fa-solid fa-house-chimney`

### Vías y Transporte
- 🛣️ **Carretera/Calle** (`road`, `street`): `fa-solid fa-road`
- 🚂 **Ferrocarril** (`railway`): `fa-solid fa-train`

### Edificios
- 🏢 **Edificio** (`building`): `fa-solid fa-building`
- ⛪ **Iglesia** (`church`): `fa-solid fa-church`
- 🕌 **Mezquita** (`mosque`): `fa-solid fa-mosque`
- 🏰 **Castillo** (`castle`): `fa-solid fa-fort-awesome`

### Geografía Natural
- 🏔️ **Montaña** (`mountain`, `peak`): `fa-solid fa-mountain`
- 🌊 **Hidrografía** (`river`, `lake`, `sea`): `fa-solid fa-water`
- 🏝️ **Isla** (`island`): `fa-solid fa-island-tropical`

### Otros
- 📍 **Sin clasificar** (`unknown`): `fa-solid fa-location-dot`

## Uso en la Aplicación

### Filtrado por Tipo
1. Ir a **Gestor de Ubicaciones**
2. Usar el selector **"Filtrar por Tipo de Lugar"**
3. Seleccionar:
   - Ciudades
   - Calles
   - Edificios/Templos
   - Montañas
   - Hidrografía
   - etc.

### Visualización
- Cada ubicación muestra su icono correspondiente
- Color distintivo según categoría
- Tooltip con nombre del tipo al pasar cursor

## Notas Técnicas

### Captura Automática
A partir de ahora, todas las geocodificaciones nuevas capturarán automáticamente el tipo desde Nominatim:

```python
# En routes/noticias.py
if data_geo:
    lat = float(data_geo[0]['lat'])
    lon = float(data_geo[0]['lon'])
    tipo_lugar = data_geo[0].get('type', 'unknown')
```

### Performance
- El campo está indexado para búsquedas rápidas
- No afecta consultas existentes (compatible hacia atrás)

### Extensibilidad
Para agregar nuevos tipos:
1. Añadir en `getTipoLugarIcon()` (templates/gestor_ubicaciones.html)
2. Añadir en filtro selector HTML
3. Nominatim ya proporciona 50+ tipos diferentes
