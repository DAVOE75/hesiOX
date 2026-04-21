# hesiOX API Documentation

## Base URL
```
http://localhost:5000
```

## Authentication
All API endpoints require authentication via Flask-Login session cookies.

---

## Endpoints

### Artículos (Prensa)

#### GET `/api/valores_filtrados`
Obtiene valores únicos de columnas para filtros dinámicos.

**Query Parameters:**
- `columna` (optional): Columna específica a consultar (`publicacion`, `autor`, `ciudad`, `temas`, `fecha_original`)
- `publicacion` (optional): Filtrar por publicación
- `autor` (optional): Filtrar por autor
- `ciudad` (optional): Filtrar por ciudad
- `fecha_original` (optional): Filtrar por fecha
- `temas` (optional): Filtrar por temas

**Response:**
```json
{
  "autores": ["García, Juan", "López, María"],
  "fechas": ["01/01/1920", "15/03/1921"],
  "ciudades": ["Madrid", "Barcelona"],
  "temas": ["Política", "Economía"],
  "publicaciones": ["El Imparcial", "ABC"]
}
```

**Example:**
```bash
curl -X GET "http://localhost:5000/api/valores_filtrados?columna=autor" \
  --cookie "session=..."
```

---

#### GET `/api/publicacion/datos`
Obtiene datos de una publicación por nombre.

**Query Parameters:**
- `nombre` (required): Nombre de la publicación

**Response:**
```json
{
  "found": true,
  "pais": "España",
  "fuente": "Biblioteca Nacional de España"
}
```

**Example:**
```bash
curl -X GET "http://localhost:5000/api/publicacion/datos?nombre=El%20Imparcial" \
  --cookie "session=..."
```

---

#### POST `/actualizar_nota/<id>`
Actualiza la nota de un artículo.

**Path Parameters:**
- `id` (required): ID del artículo

**Request Body:**
```json
{
  "nota": "Nueva nota del artículo"
}
```

**Response:**
```json
{
  "success": true
}
```

**Example:**
```bash
curl -X POST "http://localhost:5000/actualizar_nota/123" \
  -H "Content-Type: application/json" \
  -d '{"nota": "Artículo relevante para investigación"}' \
  --cookie "session=..."
```

---

#### POST `/borrar/<id>`
Elimina un artículo.

**Path Parameters:**
- `id` (required): ID del artículo

**Response:**
```json
{
  "success": true
}
```

**Error Response:**
```json
{
  "success": false,
  "message": "No encontrado"
}
```

**Example:**
```bash
curl -X POST "http://localhost:5000/borrar/123" \
  --cookie "session=..."
```

---

#### POST `/actualizar_lote`
Actualiza múltiples artículos en lote.

**Request Body:**
```json
{
  "ids": [1, 2, 3],
  "updates": {
    "ciudad": "Madrid",
    "idioma": "Español",
    "incluido": "si",
    "licencia": "CC BY 4.0"
  }
}
```

**Response:**
```json
{
  "success": true
}
```

**Error Response:**
```json
{
  "success": false,
  "message": "Error description"
}
```

**Example:**
```bash
curl -X POST "http://localhost:5000/actualizar_lote" \
  -H "Content-Type: application/json" \
  -d '{"ids": [1,2,3], "updates": {"ciudad": "Madrid"}}' \
  --cookie "session=..."
```

---

### Proyectos

#### GET `/proyectos`
Lista todos los proyectos del usuario autenticado.

**Response:** HTML page

---

#### POST `/proyectos/nuevo`
Crea un nuevo proyecto.

**Form Data:**
- `nombre` (required): Nombre del proyecto
- `descripcion` (optional): Descripción
- `tipo` (optional): Tipo de proyecto (`hemerografia`, `libros`, `archivos`, `mixto`)

**Response:** Redirect to `/proyectos`

---

#### POST `/proyectos/<id>/activar`
Activa un proyecto como proyecto de trabajo actual.

**Path Parameters:**
- `id` (required): ID del proyecto

**Response:** Redirect to previous page

---

#### GET `/proyectos/api/usuarios`
Obtiene la lista de usuarios disponibles para compartir proyectos (excluye al usuario actual).

**Response:**
```json
[
  {
    "id": 2,
    "nombre": "Juan Pérez",
    "email": "juan@example.com"
  },
  {
    "id": 5,
    "nombre": "María García",
    "email": "maria@example.com"
  }
]
```

**Example:**
```bash
curl -X GET "http://localhost:5000/proyectos/api/usuarios" \
  --cookie "session=..."
```

---

#### POST `/proyectos/<id>/compartir`
Comparte un proyecto con uno o más usuarios. Solo el propietario puede ejecutar esta acción.

**Path Parameters:**
- `id` (required): ID del proyecto

**Headers:**
- `X-CSRFToken` (required): CSRF token from meta tag
- `Content-Type: application/json`

**Request Body:**
```json
{
  "usuarios_ids": [2, 5, 8]
}
```

**Response:**
```json
{
  "success": true,
  "mensaje": "Proyecto compartido con 3 usuarios",
  "compartidos": [
    {
      "id": 15,
      "usuario": {
        "id": 2,
        "nombre": "Juan Pérez",
        "email": "juan@example.com"
      },
      "compartido_en": "2026-03-04T10:30:00",
      "activo": false
    }
  ]
}
```

**Error Response:**
```json
{
  "success": false,
  "mensaje": "No tienes permisos para compartir este proyecto"
}
```

**Example:**
```bash
curl -X POST "http://localhost:5000/proyectos/123/compartir" \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: your-csrf-token" \
  -d '{"usuarios_ids": [2, 5]}' \
  --cookie "session=..."
```

---

#### POST `/proyectos/<id>/dejar-de-compartir`
Revoca el acceso de un usuario a un proyecto compartido. Solo el propietario puede ejecutar esta acción.

**Path Parameters:**
- `id` (required): ID del proyecto

**Headers:**
- `X-CSRFToken` (required): CSRF token from meta tag
- `Content-Type: application/json`

**Request Body:**
```json
{
  "usuario_id": 5
}
```

**Response:**
```json
{
  "success": true,
  "mensaje": "Acceso revocado correctamente"
}
```

**Error Response:**
```json
{
  "success": false,
  "mensaje": "No se pudo revocar el acceso"
}
```

**Example:**
```bash
curl -X POST "http://localhost:5000/proyectos/123/dejar-de-compartir" \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: your-csrf-token" \
  -d '{"usuario_id": 5}' \
  --cookie "session=..."
```

---

#### POST `/proyectos/<id>/dejar-de-compartir-todos`
Revoca el acceso de TODOS los usuarios a un proyecto compartido. Solo el propietario puede ejecutar esta acción.

**Path Parameters:**
- `id` (required): ID del proyecto

**Headers:**
- `X-CSRFToken` (required): CSRF token from meta tag
- `Content-Type: application/json`

**Request Body:**
No requiere body (objeto JSON vacío)

**Response:**
```json
{
  "success": true,
  "mensaje": "Se revocó el acceso de 5 usuarios"
}
```

**Error Response:**
```json
{
  "success": false,
  "mensaje": "El proyecto no está compartido con ningún usuario"
}
```

**Example:**
```bash
curl -X POST "http://localhost:5000/proyectos/123/dejar-de-compartir-todos" \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: your-csrf-token" \
  --cookie "session=..."
```

**Notes:**
- Esta acción elimina TODOS los registros de `ProyectoCompartido` asociados al proyecto
- Es irreversible, pero se puede volver a compartir posteriormente
- Se recomienda confirmar con el usuario antes de ejecutar

---

#### GET `/proyectos/<id>/compartidos`
Obtiene la lista de usuarios con los que está compartido un proyecto, incluyendo el estado de activación (lock).

**Path Parameters:**
- `id` (required): ID del proyecto

**Response:**
```json
[
  {
    "id": 15,
    "usuario": {
      "id": 5,
      "nombre": "María García",
      "email": "maria@example.com"
    },
    "compartido_en": "2026-03-04T10:30:00",
    "activo": true
  },
  {
    "id": 16,
    "usuario": {
      "id": 8,
      "nombre": "Pedro López",
      "email": "pedro@example.com"
    },
    "compartido_en": "2026-03-04T11:15:00",
    "activo": false
  }
]
```

**Notes:**
- `activo`: Indica si el usuario tiene el proyecto activo actualmente (lock de 5 minutos)
- Solo visibles para el propietario del proyecto

**Example:**
```bash
curl -X GET "http://localhost:5000/proyectos/123/compartidos" \
  --cookie "session=..."
```

---

### Hemerotecas

#### GET `/hemerotecas`
Lista todas las hemerotecas del proyecto activo.

**Response:** HTML page with hemerotecas list

---

#### POST `/hemerotecas/nueva`
Crea una nueva hemeroteca.

**Form Data:**
- `nombre` (required): Nombre de la hemeroteca
- `institucion` (optional): Institución gestora
- `ciudad` (optional): Ciudad
- `pais` (optional): País
- `url` (optional): URL de la hemeroteca
- `resumen_corpus` (optional): Descripción del corpus

**Response:** Redirect to `/hemerotecas`

---

## Error Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 400 | Bad Request - Invalid input data |
| 403 | Forbidden - No access to resource |
| 404 | Not Found - Resource doesn't exist |
| 429 | Too Many Requests - Rate limit exceeded |
| 500 | Internal Server Error |

---

## Rate Limits

| Endpoint | Limit |
|----------|-------|
| `/login` | 5 per minute |
| `/registro` | 3 per hour |
| `/api/*` | 100 per hour |
| `/exportar` | 10 per hour |

---

## Data Models

### Artículo (Prensa)
```json
{
  "id": 1,
  "titulo": "Título del artículo",
  "autor": "García, Juan",
  "publicacion": "El Imparcial",
  "fecha_original": "15/03/1920",
  "ciudad": "Madrid",
  "pais_publicacion": "España",
  "contenido": "Texto del artículo...",
  "temas": "Política, Economía",
  "incluido": true,
  "url": "https://...",
  "notas": "Notas del investigador"
}
```

### Proyecto
```json
{
  "id": 1,
  "nombre": "Mi Proyecto",
  "descripcion": "Descripción del proyecto",
  "tipo": "hemerografia",
  "activo": true,
  "user_id": 1
}
```

### Hemeroteca
```json
{
  "id": 1,
  "nombre": "Biblioteca Nacional de España",
  "institucion": "BNE",
  "ciudad": "Madrid",
  "pais": "España",
  "url": "http://www.bne.es/",
  "resumen_corpus": "Descripción del corpus"
}
```

---

## Notes

- All timestamps are in UTC
- Dates in `fecha_original` use format `DD/MM/YYYY`
- CSRF tokens are required for all POST requests
- Session cookies expire after 24 hours of inactivity
