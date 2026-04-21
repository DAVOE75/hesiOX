# Optimización de Base de Datos - Índices

## Fecha: 2025-12-28

## Descripción
Se han añadido índices a las tablas principales para mejorar el rendimiento de las queries más frecuentes.

## Cambios Realizados

### Modelos Actualizados
Los índices están definidos en `models.py` usando `__table_args__`:

#### Tabla `prensa` (Artículos)
- `idx_prensa_proyecto_id` - Filtrado por proyecto
- `idx_prensa_fecha_original` - Ordenamiento y filtrado por fecha
- `idx_prensa_publicacion` - Filtrado por publicación
- `idx_prensa_ciudad` - Filtrado por ciudad
- `idx_prensa_autor` - Filtrado por autor
- `idx_prensa_anio` - Filtrado por año
- `idx_prensa_incluido` - Filtrado por estado de inclusión
- `idx_prensa_id_publicacion` - Joins con tabla publicaciones

#### Tabla `publicaciones`
- `idx_publicacion_proyecto_id` - Filtrado por proyecto
- `idx_publicacion_hemeroteca_id` - Joins con hemerotecas
- `idx_publicacion_nombre` - Búsqueda por nombre

#### Tabla `proyectos`
- `idx_proyecto_user_id` - Filtrado por usuario
- `idx_proyecto_nombre` - Búsqueda por nombre

#### Tabla `hemerotecas`
- `idx_hemeroteca_proyecto_id` - Filtrado por proyecto
- `idx_hemeroteca_nombre` - Búsqueda por nombre

## Aplicación de Índices

### Para Nuevas Instalaciones
Los índices se crearán automáticamente al ejecutar:
```python
python app.py
```

### Para Bases de Datos Existentes
Los índices se pueden crear manualmente ejecutando en PostgreSQL:

```sql
-- Índices para tabla prensa
CREATE INDEX IF NOT EXISTS idx_prensa_proyecto_id ON prensa(proyecto_id);
CREATE INDEX IF NOT EXISTS idx_prensa_fecha_original ON prensa(fecha_original);
CREATE INDEX IF NOT EXISTS idx_prensa_publicacion ON prensa(publicacion);
CREATE INDEX IF NOT EXISTS idx_prensa_ciudad ON prensa(ciudad);
CREATE INDEX IF NOT EXISTS idx_prensa_autor ON prensa(autor);
CREATE INDEX IF NOT EXISTS idx_prensa_anio ON prensa(anio);
CREATE INDEX IF NOT EXISTS idx_prensa_incluido ON prensa(incluido);
CREATE INDEX IF NOT EXISTS idx_prensa_id_publicacion ON prensa(id_publicacion);

-- Índices para tabla publicaciones
CREATE INDEX IF NOT EXISTS idx_publicacion_proyecto_id ON publicaciones(proyecto_id);
CREATE INDEX IF NOT EXISTS idx_publicacion_hemeroteca_id ON publicaciones(hemeroteca_id);
CREATE INDEX IF NOT EXISTS idx_publicacion_nombre ON publicaciones(nombre);

-- Índices para tabla proyectos
CREATE INDEX IF NOT EXISTS idx_proyecto_user_id ON proyectos(user_id);
CREATE INDEX IF NOT EXISTS idx_proyecto_nombre ON proyectos(nombre);

-- Índices para tabla hemerotecas
CREATE INDEX IF NOT EXISTS idx_hemeroteca_proyecto_id ON hemerotecas(proyecto_id);
CREATE INDEX IF NOT EXISTS idx_hemeroteca_nombre ON hemerotecas(nombre);
```

## Verificación
Para verificar que los índices se crearon correctamente:

```sql
SELECT 
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'public'
AND indexname LIKE 'idx_%'
ORDER BY tablename, indexname;
```

## Impacto Esperado
- ⚡ Mejora significativa en queries con filtros por proyecto
- ⚡ Ordenamiento por fecha más rápido
- ⚡ Búsquedas por autor, publicación y ciudad optimizadas
- ⚡ Joins entre tablas más eficientes

## Notas
- Los índices ocupan espacio adicional en disco (mínimo)
- Se actualizan automáticamente al insertar/actualizar/eliminar registros
- No requieren mantenimiento manual
