# TODO: Corrección de filtros dependientes

## Problema
- El select de fechas está vacío al inicio
- Los filtros no se actualizan correctamente al seleccionar valores
- Colisión de funciones ya corregida, pero falta lógica de cascada

## Solución implementada

### 1. Carga inicial de filtros
- Función `cargarFiltrosIniciales()` que llama a `/api/valores_filtrados` sin parámetros
- Pobla todos los selects con todos los valores posibles

### 2. Filtros dependientes en cascada
- Al cambiar un filtro, se pasan TODOS los filtros actuales al endpoint
- El endpoint devuelve los valores únicos para CADA campo según los filtros aplicados
- Se actualizan todos los selects EXCEPTO el que se está modificando

### 3. Estructura de funciones
- `cargarFiltrosIniciales()`: carga todos los filtros al inicio
- `sincronizarFiltrosConBackend(filtroModificado)`: actualiza filtros cuando uno cambia
- `actualizarSelectChoices(id, valores)`: helper para actualizar un select específico
- `obtenerFiltrosActuales()`: helper para obtener estado actual de todos los filtros

### 4. Reseteo de filtros
- El botón Reset limpia todos los selects
- Vuelve a cargar todos los valores desde el backend

## Archivos modificados
- `static/js/tabla.js`: lógica de filtros

