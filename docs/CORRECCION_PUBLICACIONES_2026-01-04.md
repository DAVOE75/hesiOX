# Corrección de Guardado y Propagación de Publicaciones

**Fecha:** 4 de enero de 2026  
**Ticket:** Corrección de campos faltantes en publicaciones

---

## 🐛 Problemas Corregidos

### 1. Campos NO se guardaban al crear/editar publicaciones

Los siguientes campos se enviaban desde el formulario pero **NO se guardaban** en la base de datos:

- ❌ **Fuente / Institución**: Campo marcado como readonly, no se capturaba
- ❌ **Tema / Género**: Se enviaba como `tema` pero no se guardaba
- ❌ **Editorial / Imprenta**: Se enviaba como `editorial` pero no se guardaba  
- ❌ **Tipo**: Se enviaba como `tipo` pero el modelo esperaba `tipo_recurso`

### 2. Propagación de cambios incompleta

Al marcar "Propagar cambios", solo se actualizaban:
- ✓ Nombre de publicación
- ✓ Ciudad
- ✓ País

**NO se propagaban** estos campos importantes:
- ❌ Fuente
- ❌ Licencia
- ❌ Formato fuente
- ❌ Editorial
- ❌ Tema
- ❌ Descripción histórica

---

## ✅ Soluciones Implementadas

### 1. Modelo de Datos (`models.py`)

Agregados los campos faltantes al modelo `Publicacion`:

```python
fuente = db.Column(db.Text)  # Fuente / Institución (Archivo)
tema = db.Column(db.Text)    # Tema / Género de la publicación
editorial = db.Column(db.Text)  # Editorial / Imprenta
```

### 2. Rutas de Guardado (`routes/hemerotecas.py`)

#### En `nueva_publicacion()`:
- ✅ Ahora captura `fuente`, `tema` y `editorial`
- ✅ Corregido mapeo de `tipo` → `tipo_recurso`

#### En `editar_publicacion()`:
- ✅ Ahora guarda `fuente`, `tema` y `editorial`
- ✅ Corregido mapeo de `tipo` → `tipo_recurso`
- ✅ **Nueva lógica de propagación mejorada**:
  - Se activa con checkbox "Propagar cambios"
  - Propaga **todos los campos relevantes**:
    * `nombre` → `publicacion`
    * `ciudad` → `ciudad`
    * `pais_publicacion` → `pais_publicacion`
    * `fuente` → `fuente`
    * `licencia` → `licencia`
    * `formato_fuente` → `formato_fuente`
    * `editorial` → `editorial`
    * `tema` → `temas`
    * `descripcion` → `notas` ⭐ **Descripción Histórica ahora se propaga**

### 3. Templates Actualizados

#### `editar_publicacion.html`:
- ✅ Campo `fuente` ahora editable cuando NO hay hemeroteca vinculada
- ✅ Se bloquea automáticamente cuando se selecciona una hemeroteca
- ✅ Descripción del checkbox actualizada para reflejar todos los campos

#### `nueva_publicacion.html`:
- ✅ Campo `fuente` editable por defecto
- ✅ Se autocompletará si se selecciona una hemeroteca
- ✅ JavaScript mejorado para gestión dinámica del campo

### 4. Migración de Base de Datos

**Archivo:** `migrations/add_tema_editorial_fuente_publicaciones.sql`

Agrega las columnas faltantes:
- `tema TEXT`
- `editorial TEXT`
- `fuente TEXT`

**Script de aplicación:** `migrations/run_add_tema_editorial_fuente.py`

---

## 🚀 Instrucciones de Aplicación

### Paso 1: Aplicar la migración de base de datos

```bash
python migrations/run_add_tema_editorial_fuente.py
```

Este script:
- ✅ Agrega las columnas faltantes a la tabla `publicaciones`
- ✅ Verifica que las columnas se crearon correctamente
- ✅ Es seguro ejecutarlo múltiples veces (usa `IF NOT EXISTS`)

### Paso 2: Reiniciar la aplicación

```bash
# Si está corriendo, detenerla con Ctrl+C y volver a ejecutar:
python app.py
```

### Paso 3: Probar la funcionalidad

1. **Crear nueva publicación:**
   - Ir a "Gestión de Medios" → "Nueva Publicación"
   - Llenar campos: Tema, Editorial, Fuente
   - Verificar que se guardan correctamente

2. **Editar publicación existente:**
   - Editar una publicación
   - Modificar Tema, Editorial, Fuente
   - Marcar checkbox "Propagar cambios"
   - Guardar y verificar que se actualicen las noticias vinculadas

3. **Verificar propagación:**
   - Editar una publicación con noticias vinculadas
   - Cambiar: Descripción histórica, Tema, Editorial
   - Marcar "Propagar cambios" ✓
   - Las noticias deben actualizarse:
     * `descripcion` (Publicacion) → `notas` (Prensa)
     * `tema` (Publicacion) → `temas` (Prensa)
     * `editorial` (Publicacion) → `editorial` (Prensa)

---

## 📋 Archivos Modificados

| Archivo | Cambios |
|---------|---------|
| `models.py` | Agregados campos `fuente`, `tema`, `editorial` |
| `routes/hemerotecas.py` | Corregido guardado y propagación |
| `templates/editar_publicacion.html` | Campo fuente editable, checkbox actualizado |
| `templates/nueva_publicacion.html` | Campo fuente editable por defecto |
| `migrations/add_tema_editorial_fuente_publicaciones.sql` | Migración SQL |
| `migrations/run_add_tema_editorial_fuente.py` | Script de aplicación |

---

## ⚠️ Notas Importantes

1. **Campo Fuente:**
   - Si hay hemeroteca vinculada → se autocompleta y bloquea
   - Si NO hay hemeroteca → se puede editar manualmente

2. **Propagación:**
   - Solo se activa si se marca el checkbox "Propagar cambios"
   - Actualiza TODAS las noticias vinculadas a la publicación
   - Es una operación masiva, usar con cuidado

3. **Compatibilidad:**
   - La migración es compatible con datos existentes
   - Las columnas nuevas aceptan valores NULL
   - No afecta publicaciones existentes

---

## 🎯 Resultado Final

✅ **Todos los campos se guardan correctamente**  
✅ **Propagación completa de cambios**  
✅ **Descripción Histórica se propaga a notas de noticias**  
✅ **Campo fuente flexible (manual o automático)**  
✅ **Base de datos actualizada con nuevas columnas**

---

**Autor:** Sistema de corrección automática  
**Revisado:** Pendiente de testing por usuario
