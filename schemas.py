"""
Schemas de validación para hesiOX
Utiliza Marshmallow para validación robusta de datos de entrada
"""
from marshmallow import Schema, fields, validate, ValidationError, validates, validates_schema
import re
from datetime import datetime


# =========================================================
# SCHEMAS DE AUTENTICACIÓN
# =========================================================

class LoginSchema(Schema):
    """Schema para validación de login"""
    class Meta:
        unknown = 'exclude'  # Ignorar campos desconocidos como csrf_token
    
    email = fields.Email(
        required=True,
        error_messages={
            'required': 'El email es obligatorio',
            'invalid': 'Email inválido'
        }
    )
    password = fields.Str(
        required=True,
        validate=validate.Length(min=6, max=200),
        error_messages={
            'required': 'La contraseña es obligatoria',
            'invalid': 'Contraseña inválida'
        }
    )


class RegistroSchema(Schema):
    """Schema para validación de registro de usuario"""
    class Meta:
        unknown = 'exclude'  # Ignorar campos desconocidos como csrf_token
    
    nombre = fields.Str(
        required=True,
        validate=validate.Length(min=2, max=100),
        error_messages={
            'required': 'El nombre es obligatorio',
            'invalid': 'Nombre inválido'
        }
    )
    email = fields.Email(
        required=True,
        error_messages={
            'required': 'El email es obligatorio',
            'invalid': 'Email inválido'
        }
    )
    password = fields.Str(
        required=True,
        validate=validate.Length(min=8, max=200),
        error_messages={
            'required': 'La contraseña es obligatoria',
            'invalid': 'La contraseña debe tener al menos 8 caracteres'
        }
    )
    password_confirm = fields.Str(
        required=True,
        error_messages={
            'required': 'Confirma tu contraseña'
        }
    )
    
    @validates_schema
    def validate_passwords_match(self, data, **kwargs):
        """Valida que las contraseñas coincidan"""
        if data.get('password') != data.get('password_confirm'):
            raise ValidationError('Las contraseñas no coinciden', 'password_confirm')


# =========================================================
# SCHEMAS DE PROYECTOS
# =========================================================

class ProyectoSchema(Schema):
    """Schema para validación de proyectos"""
    nombre = fields.Str(
        required=True,
        validate=validate.Length(min=1, max=200),
        error_messages={
            'required': 'El nombre del proyecto es obligatorio',
            'invalid': 'Nombre inválido'
        }
    )
    descripcion = fields.Str(
        validate=validate.Length(max=1000),
        allow_none=True
    )
    tipo = fields.Str(
        validate=validate.OneOf(['hemerografia', 'libros', 'archivos', 'mixto']),
        allow_none=True
    )


# =========================================================
# SCHEMAS DE ARTÍCULOS
# =========================================================

class ArticuloSchema(Schema):
    """Schema para validación de artículos de prensa"""
    titulo = fields.Str(
        required=True,
        validate=validate.Length(min=1, max=500),
        error_messages={
            'required': 'El título es obligatorio',
            'invalid': 'Título inválido'
        }
    )
    autor = fields.Str(
        validate=validate.Length(max=200),
        allow_none=True
    )
    fecha_original = fields.Str(
        allow_none=True
    )
    anio = fields.Int(
        validate=validate.Range(min=1800, max=2100),
        allow_none=True
    )
    ciudad = fields.Str(
        validate=validate.Length(max=100),
        allow_none=True
    )
    pais = fields.Str(
        validate=validate.Length(max=100),
        allow_none=True
    )
    publicacion = fields.Str(
        validate=validate.Length(max=200),
        allow_none=True
    )
    contenido = fields.Str(
        allow_none=True
    )
    url = fields.Url(
        allow_none=True,
        error_messages={'invalid': 'URL inválida'}
    )
    pagina_inicio = fields.Str(
        validate=validate.Length(max=20),
        allow_none=True
    )
    pagina_fin = fields.Str(
        validate=validate.Length(max=20),
        allow_none=True
    )
    temas = fields.Str(
        allow_none=True
    )
    
    @validates('fecha_original')
    def validate_fecha(self, value):
        """Valida formato de fecha DD/MM/YYYY"""
        if value and value.strip():
            pattern = r'^\d{1,2}/\d{1,2}/\d{4}$'
            if not re.match(pattern, value.strip()):
                raise ValidationError('Formato de fecha inválido. Use DD/MM/YYYY')
            
            # Validar que la fecha sea válida
            try:
                parts = value.strip().split('/')
                day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
                datetime(year, month, day)
            except (ValueError, IndexError):
                raise ValidationError('Fecha inválida')


# =========================================================
# SCHEMAS DE PUBLICACIONES
# =========================================================

class PublicacionSchema(Schema):
    """Schema para validación de publicaciones académicas"""
    nombre = fields.Str(
        required=True,
        validate=validate.Length(min=1, max=300),
        error_messages={
            'required': 'El nombre de la publicación es obligatorio',
            'invalid': 'Nombre inválido'
        }
    )
    autor = fields.Str(
        validate=validate.Length(max=200),
        allow_none=True
    )
    tipo = fields.Str(
        validate=validate.OneOf(['libro', 'articulo', 'capitulo', 'tesis', 'otro']),
        allow_none=True
    )
    editorial = fields.Str(
        validate=validate.Length(max=200),
        allow_none=True
    )
    anio = fields.Int(
        validate=validate.Range(min=1800, max=2100),
        allow_none=True
    )
    ciudad = fields.Str(
        validate=validate.Length(max=100),
        allow_none=True
    )
    pais = fields.Str(
        validate=validate.Length(max=100),
        allow_none=True
    )
    isbn = fields.Str(
        validate=validate.Length(max=20),
        allow_none=True
    )
    doi = fields.Str(
        validate=validate.Length(max=100),
        allow_none=True
    )
    url = fields.Url(
        allow_none=True,
        error_messages={'invalid': 'URL inválida'}
    )


# =========================================================
# SCHEMAS DE HEMEROTECAS
# =========================================================

class HemerotecaSchema(Schema):
    """Schema para validación de hemerotecas"""
    nombre = fields.Str(
        required=True,
        validate=validate.Length(min=1, max=200),
        error_messages={
            'required': 'El nombre de la hemeroteca es obligatorio',
            'invalid': 'Nombre inválido'
        }
    )
    ciudad = fields.Str(
        validate=validate.Length(max=100),
        allow_none=True
    )
    pais = fields.Str(
        validate=validate.Length(max=100),
        allow_none=True
    )
    institucion_gestora = fields.Str(
        validate=validate.Length(max=200),
        allow_none=True
    )
    url = fields.Url(
        allow_none=True,
        error_messages={'invalid': 'URL inválida'}
    )
    descripcion = fields.Str(
        validate=validate.Length(max=1000),
        allow_none=True
    )


# =========================================================
# SCHEMAS DE BÚSQUEDA Y FILTROS
# =========================================================

class BusquedaSchema(Schema):
    """Schema para validación de búsquedas"""
    query = fields.Str(
        required=True,
        validate=validate.Length(min=1, max=500),
        error_messages={
            'required': 'El término de búsqueda es obligatorio',
            'invalid': 'Búsqueda inválida'
        }
    )
    tipo = fields.Str(
        validate=validate.OneOf(['simple', 'semantica', 'avanzada']),
        allow_none=True
    )


class FiltroSchema(Schema):
    """Schema para validación de filtros"""
    autor = fields.Str(
        validate=validate.Length(max=200),
        allow_none=True
    )
    publicacion = fields.Str(
        validate=validate.Length(max=200),
        allow_none=True
    )
    ciudad = fields.Str(
        validate=validate.Length(max=100),
        allow_none=True
    )
    pais = fields.Str(
        validate=validate.Length(max=100),
        allow_none=True
    )
    fecha_desde = fields.Str(
        allow_none=True
    )
    fecha_hasta = fields.Str(
        allow_none=True
    )
    tema = fields.Str(
        validate=validate.Length(max=100),
        allow_none=True
    )
