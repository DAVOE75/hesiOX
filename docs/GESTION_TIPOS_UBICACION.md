# Gestión de Tipos de Ubicación

Sistema para gestionar dinámicamente los tipos de ubicaciones geográficas en hesiOX.

## 📋 Descripción

Este módulo permite administrar los tipos de ubicaciones (ciudad, montaña, río, golfo, etc.) de forma dinámica desde la interfaz web, sin necesidad de modificar código.

## 🚀 Instalación

### 1. Ejecutar la migración

```bash
cd /opt/hesiox
python migrations/run_migration_tipos_ubicacion.py
```

O usando SQL directamente:

```bash
psql -U tu_usuario -d tu_database -f migrations/add_tipo_ubicacion_table.sql
```

### 2. Reiniciar la aplicación

```bash
# Si usas systemd
sudo systemctl restart hesiox

# O si usas otro método, reinicia el servidor
```

## 📱 Uso

### Acceso a la gestión

1. Ve al **Gestor de Ubicaciones**
2. Haz clic en el botón **"Tipos"** en la barra superior
3. Se abrirá el modal de gestión de tipos

### Añadir un nuevo tipo

1. Clic en **"Añadir Nuevo Tipo"**
2. Rellena los campos:
   - **Código**: Identificador único (solo minúsculas y guiones bajos). Ej: `gulf`, `country`
   - **Nombre**: Nombre visible. Ej: `Golfo`, `País`
   - **Categoría**: Grupo al que pertenece. Ej: `Hidrografía`, `Administrativo`
   - **Icono**: Clase de Font Awesome. Ej: `fa-solid fa-water`
   - **Orden**: Número para ordenar en listados (menor = primero)
3. Clic en **"Guardar"**

### Editar un tipo existente

1. En la tabla de tipos, clic en el botón **✏️ Editar**
2. Modifica los campos necesarios (el código no se puede cambiar)
3. Clic en **"Guardar"**

### Eliminar un tipo

1. En la tabla de tipos, clic en el botón **🗑️ Eliminar**
2. Confirma la eliminación

**Nota:** Los tipos eliminados solo se desactivan, no se borran físicamente. Los datos existentes que usen ese tipo se mantienen intactos.

## 🏗️ Estructura de la base de datos

### Tabla: `tipo_ubicacion`

| Campo          | Tipo         | Descripción                          |
|----------------|--------------|--------------------------------------|
| id             | SERIAL       | ID autoincremental                   |
| codigo         | VARCHAR(50)  | Código único (ej: `city`, `gulf`)    |
| nombre         | VARCHAR(100) | Nombre visible (ej: `Ciudad`)        |
| categoria      | VARCHAR(50)  | Categoría del tipo                   |
| icono          | VARCHAR(100) | Clase de icono Font Awesome          |
| orden          | INTEGER      | Orden de visualización               |
| activo         | BOOLEAN      | Si está activo o desactivado         |
| fecha_creacion | TIMESTAMP    | Fecha de creación                    |

## 🔌 API Endpoints

### Listar tipos
```http
GET /api/tipos-ubicacion/listar
```

### Crear tipo
```http
POST /api/tipos-ubicacion/crear
Content-Type: application/json

{
  "codigo": "gulf",
  "nombre": "Golfo",
  "categoria": "Hidrografía",
  "icono": "fa-solid fa-water",
  "orden": 407
}
```

### Editar tipo
```http
PUT /api/tipos-ubicacion/editar/<id>
Content-Type: application/json

{
  "nombre": "Golfo Geográfico",
  "categoria": "Hidrografía",
  "orden": 408
}
```

### Eliminar tipo
```http
DELETE /api/tipos-ubicacion/eliminar/<id>
```

## 📂 Archivos modificados

- **models.py**: Modelo `TipoUbicacion`
- **routes/noticias.py**: Endpoints API para CRUD
- **templates/gestor_ubicaciones.html**: Interfaz de gestión
- **migrations/add_tipo_ubicacion_table.sql**: Script SQL de migración
- **migrations/run_migration_tipos_ubicacion.py**: Script Python de migración

## 🎨 Categorías predefinidas

- Ciudades y Poblaciones
- Vías
- Edificios
- Geografía Natural
- Hidrografía
- Administrativo
- Otros

## 💡 Consejos

1. **Códigos únicos**: Usa códigos descriptivos y únicos (ej: `gulf`, `country`, `mountain_range`)
2. **Iconos**: Busca iconos en [Font Awesome](https://fontawesome.com/icons)
3. **Orden**: Usa múltiplos de 10 para facilitar insertar tipos intermedios luego
4. **Categorías**: Mantén las categorías consistentes para mejor organización

## 🐛 Solución de problemas

### Los tipos no aparecen en los selectores

1. Verifica que el tipo esté **activo**
2. Refresca la página con `Ctrl+F5`
3. Revisa la consola del navegador para errores

### Error "Ya existe un tipo con código..."

El código debe ser único. Usa otro código diferente.

### Los cambios no se guardan

1. Verifica que tengas permisos de usuario autenticado
2. Revisa que el CSRF token esté presente
3. Comprueba los logs del servidor para errores

## 📝 Notas

- Los tipos se cargan dinámicamente desde la base de datos
- Los selectores se actualizan automáticamente al añadir/editar/eliminar tipos
- Los tipos inactivos no aparecen en los selectores pero se mantienen en la BD
- Al eliminar un tipo, los lugares que ya tengan ese tipo asignado lo conservan

## 🔄 Actualización desde versiones anteriores

Si ya tenías tipos hardcodeados en el HTML, esta migración los importa automáticamente a la base de datos. Los tipos existentes en `lugar_noticia.tipo_lugar` seguirán funcionando correctamente.

## 📧 Soporte

Para problemas o sugerencias, contacta al equipo de desarrollo de hesiOX.
