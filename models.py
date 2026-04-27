from extensions import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy import case, and_, func

SQL_PRENSA_DATE = """
CASE 
    WHEN prensa.fecha_original ~ '^[0-3]?[0-9]/[0-1]?[0-9]/[0-9]{2,4}$' THEN to_date(prensa.fecha_original, 'DD/MM/YYYY')
    WHEN prensa.fecha_original ~ '^[0-9]{4}-[0-1]?[0-9]-[0-3]?[0-9]$' THEN to_date(prensa.fecha_original, 'YYYY-MM-DD')
    ELSE NULL 
END
"""

# Modelo para lugares manuales asociados a una noticia
class LugarNoticia(db.Model):
    __tablename__ = "lugar_noticia"
    id = db.Column(db.Integer, primary_key=True)
    noticia_id = db.Column(db.Integer, db.ForeignKey("prensa.id", ondelete="CASCADE"), nullable=False)
    nombre = db.Column(db.String(255), nullable=False)
    borrado = db.Column(db.Boolean, default=False, nullable=False)  # Persistente: ocultar y no re-extraer
    vinculada = db.Column(db.Boolean, default=True, nullable=False)  # Si está vinculada a esta noticia (para frecuencia)
    lat = db.Column(db.Float, nullable=False)
    lon = db.Column(db.Float, nullable=False)
    frecuencia = db.Column(db.Integer, nullable=False, default=1)
    frecuencia_desvinculada = db.Column(db.Integer, nullable=False, default=0)  # Cuántas ocurrencias están desvinculadas
    frec_titulo = db.Column(db.Integer, nullable=False, default=0)
    frec_contenido = db.Column(db.Integer, nullable=False, default=0)
    tipo = db.Column(db.String(20), nullable=False, default="manual")  # 'manual' o 'extraido'
    tipo_lugar = db.Column(db.String(50), nullable=True, default="unknown")  # Clasificación geográfica: city, road, building, mountain, etc.
    en_titulo = db.Column(db.Boolean, nullable=False, default=False)
    en_contenido = db.Column(db.Boolean, nullable=False, default=False)
    verificada = db.Column(db.Boolean, default=False, nullable=False)  # Estado de verificación manual
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)

    noticia = db.relationship("Prensa", backref=db.backref("lugares", cascade="all, delete-orphan", lazy=True))


    def __repr__(self):
        return f"<LugarNoticia {self.nombre} ({self.lat}, {self.lon}) x{self.frecuencia}>"


# Modelo para tipos de ubicaciones configurables
class TipoUbicacion(db.Model):
    __tablename__ = "tipo_ubicacion"
    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(50), unique=True, nullable=False, index=True)  # ej: 'city', 'mountain', 'gulf'
    nombre = db.Column(db.String(100), nullable=False)  # ej: 'Ciudad', 'Montaña', 'Golfo'
    categoria = db.Column(db.String(50), nullable=False, default='Otros')  # ej: 'Hidrografía', 'Administrativo', 'Geografía Natural'
    icono = db.Column(db.String(100), nullable=True)  # Clase de icono Font Awesome: 'fa-solid fa-city'
    orden = db.Column(db.Integer, nullable=False, default=999)  # Orden de visualización
    activo = db.Column(db.Boolean, default=True, nullable=False)  # Permite desactivar sin eliminar
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<TipoUbicacion {self.codigo}: {self.nombre}>"

    def to_dict(self):
        return {
            'id': self.id,
            'codigo': self.codigo,
            'nombre': self.nombre,
            'categoria': self.categoria,
            'icono': self.icono,
            'orden': self.orden,
            'activo': self.activo
        }


class Usuario(db.Model, UserMixin):
    __tablename__ = "usuarios"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)

    # Mapeamos el atributo "nombre" a la columna física "username"
    nombre = db.Column("username", db.String(150), nullable=False)

    password_hash = db.Column(db.String(255), nullable=False)

    # Mapeamos "creado_en" a la columna "created_at"
    creado_en = db.Column("created_at", db.DateTime, default=datetime.utcnow)

    # Rol del usuario: 'user' (default) o 'admin' (mantenimiento técnico)
    rol = db.Column(db.String(20), default="user", nullable=False)

    # Estado de la cuenta (para suspensión técnica)
    activo = db.Column(db.Boolean, default=True, nullable=False)

    # API Keys personales de IA
    api_key_gemini = db.Column(db.String(255), nullable=True)
    api_key_openai = db.Column(db.String(255), nullable=True)
    api_key_anthropic = db.Column(db.String(255), nullable=True)

    # Flags de activación para IA personal
    ai_gemini_active = db.Column(db.Boolean, default=True, nullable=False)
    ai_openai_active = db.Column(db.Boolean, default=True, nullable=False)
    ai_anthropic_active = db.Column(db.Boolean, default=True, nullable=False)
    foto_perfil = db.Column(db.String(255), nullable=True)
    institucion = db.Column(db.String(255), nullable=True)
    orcid = db.Column(db.String(50), nullable=True)
    telefono = db.Column(db.String(50), nullable=True)
    fondo_perfil = db.Column(db.String(255), nullable=True)

    # IDE Personal — servicios WMS/WMTS favoritos del usuario (JSON array)
    wms_favoritos = db.Column(db.Text, nullable=True, default='[]')

    proyectos = db.relationship("Proyecto", backref="usuario", lazy=True)

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


class GeoPlace(db.Model):
    __tablename__ = "geo_places"
    id = db.Column(db.Integer, primary_key=True)
    proyecto_id = db.Column(db.Integer, db.ForeignKey("proyectos.id"), nullable=True)

    place_raw = db.Column(db.Text, nullable=False)
    place_norm = db.Column(db.Text, nullable=False)
    pais = db.Column(db.Text, nullable=True)

    lat = db.Column(db.Float, nullable=True)
    lon = db.Column(db.Float, nullable=True)

    status = db.Column(db.Text, nullable=False, default="PENDING")  # OK/NOT_FOUND/PENDING/MANUAL
    provider = db.Column(db.Text, nullable=True)
    provider_ref = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

class Proyecto(db.Model):
    """Modelo para gestionar múltiples proyectos bibliográficos independientes"""

    __tablename__ = "proyectos"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.Text, unique=True, nullable=False)
    descripcion = db.Column(db.Text)
    tipo = db.Column(
        db.Text, default="hemerografia"
    )  # hemerografia, libros, archivos, mixto
    
    # Perfil de análisis de texto (determina qué stopwords usar)
    perfil_analisis = db.Column(
        db.Text, default="contenido"
    )  # contenido, estilometrico, mixto
    
    activo = db.Column(db.Boolean, default=True)
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Configuración de red (JSON con tipos de nodos y sus entidades)
    red_tipos = db.Column(db.Text, default='{"tipo1": {"nombre": "Principales", "color": "#ff9800", "forma": "dot", "entidades": []}, "tipo2": {"nombre": "Secundarios", "color": "#03a9f4", "forma": "dot", "entidades": []}, "tipo3": {"nombre": "Lugares", "color": "#4a7c2f", "forma": "square", "entidades": []}}')

    # Módulos activados para este proyecto (personas, barco, etc.)
    modulos_activados = db.Column(db.JSON, default=list)

    # 🔐 Relación con Usuario (de momento nullable=True para migración tranquila)
    user_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=True)

    # Relaciones
    articulos = db.relationship(
        "Prensa", backref="proyecto", lazy=True, cascade="all, delete-orphan"
    )
    publicaciones = db.relationship(
        "Publicacion", backref="proyecto", lazy=True, cascade="all, delete-orphan"
    )
    
    # Índices para optimizar queries
    __table_args__ = (
        db.Index('idx_proyecto_user_id', 'user_id'),
        db.Index('idx_proyecto_nombre', 'nombre'),
    )

    def __repr__(self):
        return f"<Proyecto {self.id}: {self.nombre}>"

    def count_articulos(self):
        """Cuenta el número de artículos en este proyecto"""
        return len(self.articulos)


class Hemeroteca(db.Model):
    __tablename__ = "hemerotecas"
    id = db.Column(db.Integer, primary_key=True)
    proyecto_id = db.Column(db.Integer, db.ForeignKey("proyectos.id"), nullable=True)
    nombre = db.Column(db.Text, nullable=False)
    institucion = db.Column(db.Text)  # Institución que gestiona la hemeroteca
    pais = db.Column(db.Text)
    provincia = db.Column(db.Text)
    ciudad = db.Column(db.Text)
    resumen_corpus = db.Column(db.Text)  # Descripción del corpus de la hemeroteca
    url = db.Column(db.Text)
    compartida = db.Column(db.Boolean, default=True, nullable=False)  # Control de compartición en repositorio global
    verificada = db.Column(db.Boolean, default=False, nullable=False)  # Repositorio validado por administrador
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)
    modificado_en = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relación con publicaciones
    publicaciones = db.relationship("Publicacion", backref="hemeroteca_rel", lazy=True)
    
    # Índices para optimizar queries
    __table_args__ = (
        db.Index('idx_hemeroteca_proyecto_id', 'proyecto_id'),
        db.Index('idx_hemeroteca_nombre', 'nombre'),
    )

    def __repr__(self):
        return f"<Hemeroteca {self.id} {self.nombre}>"


class Publicacion(db.Model):
    __tablename__ = "publicaciones"
    id_publicacion = db.Column(db.Integer, primary_key=True)
    proyecto_id = db.Column(
        db.Integer, db.ForeignKey("proyectos.id"), nullable=True
    )  # NULL para compatibilidad inicial
    hemeroteca_id = db.Column(
        db.Integer, db.ForeignKey("hemerotecas.id"), nullable=True
    )  # Vinculación con hemeroteca
    nombre = db.Column(db.Text, nullable=False)
    descripcion = db.Column(db.Text)
    tipo_recurso = db.Column(db.Text)
    ciudad = db.Column(db.Text)
    provincia = db.Column(db.Text) # Provincia/Región para mapa de coropletas
    pais_publicacion = db.Column(db.Text)
    idioma = db.Column(db.Text)
    licencia = db.Column(db.Text, default="CC BY 4.0")
    formato_fuente = db.Column(db.Text)
    licencia_predeterminada = db.Column(db.Text)
    articulos = db.relationship("Prensa", backref="publicacion_rel", lazy=True)
    fuente = db.Column(db.Text)  # Fuente / Institución (Archivo)
    tema = db.Column(db.Text)  # Tema / Género de la publicación
    editorial = db.Column(db.Text)  # Editorial / Imprenta
    url_publi = db.Column(db.Text)  # URL de la publicación (sitio oficial / hemeroteca / ficha)
    frecuencia = db.Column(db.Text, nullable=True)  # Frecuencia de la publicación: diaria, semanal, quincenal, mensual, bimensual, semestral, anual
    tipo_publicacion = db.Column(db.Text)
    periodicidad = db.Column(db.Text)
    lugar_publicacion = db.Column(db.Text)
    
    # Datos teatrales globales (si aplica)
    actos_totales = db.Column(db.Text)
    escenas_totales = db.Column(db.Text)
    reparto_total = db.Column(db.Text)
    
    # Nuevos campos para Colección y Autoría
    coleccion = db.Column(db.Text)
    nombre_autor = db.Column(db.Text)
    apellido_autor = db.Column(db.Text)
    pseudonimo = db.Column(db.Text)

    # Relación para múltiples autores
    autores = db.relationship(
        "AutorPublicacion", backref="publicacion_rel_aut", cascade="all, delete-orphan", order_by="AutorPublicacion.orden"
    )

    # Relación para archivos adjuntos (PDFs, etc.)
    archivos = db.relationship(
        "ArchivoPublicacion", backref="publicacion", lazy="dynamic", cascade="all, delete-orphan"
    )

    
    @property
    def tipo(self):
        return self.tipo_recurso

    @tipo.setter
    def tipo(self, value):
        self.tipo_recurso = value

    # Índices y restricción de unicidad por proyecto
    __table_args__ = (
        db.Index('idx_publicacion_proyecto_id', 'proyecto_id'),
        db.Index('idx_publicacion_hemeroteca_id', 'hemeroteca_id'),
        db.Index('idx_publicacion_nombre', 'nombre'),
        db.UniqueConstraint('proyecto_id', 'nombre', name='uq_publicacion_proyecto_nombre'),
    )

class Ciudad(db.Model):
    __tablename__ = "ciudad"  # confirma si es "ciudad" o "ciudades"

    id = db.Column(db.Integer, primary_key=True)

    # Si en tu BD la columna se llama "name", cámbialo; si se llama "nombre", deja "nombre".
    name = db.Column(db.Text, nullable=False)

    lat = db.Column(db.Float, nullable=True)
    lon = db.Column(db.Float, nullable=True)
    
    # Campo para almacenar la provincia/región obtenida por geocodificación
    provincia = db.Column(db.Text, nullable=True)

    # opcional (solo si existen en tu tabla real)
    bbox = db.Column(db.Text, nullable=True)      # ej: "minLon,minLat,maxLon,maxLat" o JSON
    geojson = db.Column(db.Text, nullable=True)
    tipo_lugar = db.Column(db.String(50), nullable=True, default="unknown")
    verificada = db.Column(db.Boolean, default=False, nullable=False)
    blacklisted = db.Column(db.Boolean, default=False, nullable=False)  # Lista negra global: ignorar en NER de cualquier proyecto


# Relación N:M entre Pasajeros y Publicaciones
pasajero_publicacion = db.Table('pasajero_publicacion',
    db.Column('pasajero_id', db.Integer, db.ForeignKey('pasajeros_sirio.id'), primary_key=True),
    db.Column('publicacion_id', db.Integer, db.ForeignKey('publicaciones.id_publicacion'), primary_key=True)
)

prensa_tema = db.Table('prensa_tema',
    db.Column('prensa_id', db.Integer, db.ForeignKey('prensa.id', ondelete="CASCADE"), primary_key=True),
    db.Column('tema_id', db.Integer, db.ForeignKey('temas.id', ondelete="CASCADE"), primary_key=True)
)

# Relación N:M entre Pasajeros Sirio y Prensa (Artículos/Noticias)
pasajero_prensa = db.Table('pasajero_prensa',
    db.Column('pasajero_id', db.Integer, db.ForeignKey('pasajeros_sirio.id', ondelete="CASCADE"), primary_key=True),
    db.Column('prensa_id', db.Integer, db.ForeignKey('prensa.id', ondelete="CASCADE"), primary_key=True)
)

class AutorPrensa(db.Model):
    __tablename__ = "autores_prensa"
    id = db.Column(db.Integer, primary_key=True)
    prensa_id = db.Column(db.Integer, db.ForeignKey("prensa.id", ondelete="CASCADE"), nullable=False)
    nombre = db.Column(db.Text)
    apellido = db.Column(db.Text)
    tipo = db.Column(db.Text) # firmado, corresponsal, etc.
    es_anonimo = db.Column(db.Boolean, default=False)
    orden = db.Column(db.Integer, default=0)

    def __repr__(self):
        return f"<AutorPrensa {self.apellido}, {self.nombre}>"

class AutorPublicacion(db.Model):
    __tablename__ = "autores_publicacion"
    id = db.Column(db.Integer, primary_key=True)
    publicacion_id = db.Column(db.Integer, db.ForeignKey("publicaciones.id_publicacion", ondelete="CASCADE"), nullable=False)
    nombre = db.Column(db.Text)
    apellido = db.Column(db.Text)
    tipo = db.Column(db.Text) # autor, editor, compilador, etc.
    es_anonimo = db.Column(db.Boolean, default=False)
    orden = db.Column(db.Integer, default=0)

    def __repr__(self):
        return f"<AutorPublicacion {self.apellido}, {self.nombre}>"

class ArchivoPublicacion(db.Model):
    __tablename__ = "archivos_publicacion"
    id = db.Column(db.Integer, primary_key=True)
    publicacion_id = db.Column(db.Integer, db.ForeignKey("publicaciones.id_publicacion", ondelete="CASCADE"), nullable=False)
    filename = db.Column(db.Text, nullable=False) # Nombre en el sistema de archivos (secure_filename)
    original_filename = db.Column(db.Text, nullable=False) # Nombre original subido por el usuario
    fecha_subida = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<ArchivoPublicacion {self.id} {self.original_filename}>"

class AutorBio(db.Model):
    __tablename__ = "autor_bio"
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.Text)
    apellido = db.Column(db.Text)
    seudonimo = db.Column(db.Text)
    fecha_nacimiento = db.Column(db.Text)
    lugar_nacimiento = db.Column(db.Text)
    fecha_defuncion = db.Column(db.Text)
    lugar_defuncion = db.Column(db.Text)
    nacionalidad = db.Column(db.Text)
    foto = db.Column(db.Text) # Path a la imagen
    
    # Contexto y Trayectoria
    formacion_academica = db.Column(db.Text)
    ocupaciones_secundarias = db.Column(db.Text)
    movimiento_literario = db.Column(db.Text)
    influencias = db.Column(db.Text)
    
    # Producción Literaria
    generos_literarios = db.Column(db.Text)
    obras_principales = db.Column(db.Text)
    tematicas_recurrentes = db.Column(db.Text)
    estilo = db.Column(db.Text)
    
    # Reconocimientos y Legado
    premios = db.Column(db.Text)
    impacto = db.Column(db.Text)
    
    # Información Adicional
    bibliografia = db.Column(db.Text)
    citas = db.Column(db.Text)
    enlaces = db.Column(db.Text)
    
    proyecto_id = db.Column(db.Integer, db.ForeignKey("proyectos.id", ondelete="CASCADE"))
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)

    proyecto = db.relationship("Proyecto", backref=db.backref("autores_bio", lazy=True))

    def calcular_completitud(self):
        """Calcula el porcentaje de campos rellenados."""
        campos_clave = [
            'nombre', 'apellido', 'seudonimo', 'fecha_nacimiento', 'lugar_nacimiento',
            'fecha_defuncion', 'lugar_defuncion', 'nacionalidad', 'foto',
            'formacion_academica', 'ocupaciones_secundarias', 'movimiento_literario',
            'influencias', 'generos_literarios', 'obras_principales', 'tematicas_recurrentes',
            'estilo', 'premios', 'impacto', 'bibliografia', 'citas', 'enlaces'
        ]
        rellenados = 0
        for campo in campos_clave:
            val = getattr(self, campo)
            if val and str(val).strip() and val != '-':
                rellenados += 1
        
        return int((rellenados / len(campos_clave)) * 100)

    @property
    def fechas_vida(self):
        if not self.fecha_nacimiento and not self.fecha_defuncion:
            return None
        birth = self.fecha_nacimiento if self.fecha_nacimiento else "?"
        death = self.fecha_defuncion if self.fecha_defuncion else ""
        if death:
            return f"{birth} — {death}"
        return birth

    def to_dict(self):
        d = {c.name: getattr(self, c.name) for c in self.__table__.columns if c.name != 'creado_en'}
        if self.proyecto:
            d['proyecto_nombre'] = self.proyecto.nombre
        d['completitud'] = self.calcular_completitud()
        return d

class Prensa(db.Model):
    __tablename__ = "prensa"
    id = db.Column(db.Integer, primary_key=True)
    proyecto_id = db.Column(db.Integer, db.ForeignKey("proyectos.id"), nullable=True)  # NULL para compatibilidad inicial
    titulo = db.Column(db.Text)
    publicacion = db.Column(db.Text)
    id_publicacion = db.Column(db.Integer, db.ForeignKey("publicaciones.id_publicacion"))
    ciudad = db.Column(db.Text)
    fecha_original = db.Column(db.Text)
    anio = db.Column(db.Integer)
    numero = db.Column(db.Text)
    pagina_inicio = db.Column(db.Text)
    pagina_fin = db.Column(db.Text)
    paginas = db.Column(db.Text)
    url = db.Column(db.Text)
    fecha_consulta = db.Column(db.Text)
    nombre_autor = db.Column(db.Text)
    apellido_autor = db.Column(db.Text)
    tipo_autor = db.Column(db.Text)
    pseudonimo = db.Column(db.Text)
    coleccion = db.Column(db.Text)
    idioma = db.Column(db.Text)
    licencia = db.Column(db.String(120), nullable=True, default="CC BY 4.0")
    fuente_condiciones = db.Column(db.Text)
    temas = db.Column(db.Text)
    notas = db.Column(db.Text)
    contenido = db.Column(db.Text)
    incluido = db.Column(db.Boolean, default=False)
    es_referencia = db.Column(db.Boolean, default=False)
    numero_referencia = db.Column(
        db.Integer, nullable=True
    )  # Número para citas bibliográficas
    tipo_recurso = db.Column(db.Text)
    editor = db.Column(db.Text)
    lugar_publicacion = db.Column(db.Text)
    issn = db.Column(db.Text)
    volumen = db.Column(db.Text)
    seccion = db.Column(db.Text)
    palabras_clave = db.Column(db.Text)
    resumen = db.Column(db.Text)
    editorial = db.Column(db.Text)
    isbn = db.Column(db.Text)
    doi = db.Column(db.Text)
    pais_publicacion = db.Column(db.Text)
    escenas = db.Column(db.Text)
    reparto = db.Column(db.Text)
    
    # Datos teatrales globales (heredados o manuales)
    actos_totales = db.Column(db.Text)
    escenas_totales = db.Column(db.Text)
    reparto_total = db.Column(db.Text)

    formato_fuente = db.Column(db.Text)
    referencias_relacionadas = db.Column(db.Text)
    archivo_pdf = db.Column(db.Text)
    
    # Nueva relación con Temas (Many-to-Many)
    temas_rel = db.relationship('Tema', secondary=prensa_tema, backref=db.backref('articulos', lazy='dynamic'))

    # CAMPOS NUEVOS
    fuente = db.Column(db.Text)
    imagen_scan = db.Column(db.Text)
    texto_original = db.Column(db.Text)
    descripcion_publicacion = db.Column(db.Text)  # Descripción de la publicación/medio
    
    # Campos específicos para Prensa/Folleto
    tipo_publicacion = db.Column(db.Text)  # Diario, Revista, etc.
    periodicidad = db.Column(db.Text)     # Diaria, Semanal, etc.

    # Campos para investigador y universidad
    nombre_investigador = db.Column(db.Text)
    universidad_investigador = db.Column(db.Text)

    edicion = db.Column(db.Text)  # Edición del diario (mañana, tarde, etc.)
    # Relación profesional para múltiples imágenes
    imagenes = db.relationship(
        "ImagenPrensa", backref="prensa", lazy="dynamic", cascade="all, delete-orphan"
    )

    # Relación para múltiples autores
    autores = db.relationship(
        "AutorPrensa", backref="prensa", cascade="all, delete-orphan", order_by="AutorPrensa.orden"
    )

    @property
    def tipo(self):
        return self.tipo_recurso

    @tipo.setter
    def tipo(self, value):
        self.tipo_recurso = value

    creado_en = db.Column(db.DateTime, default=datetime.utcnow)
    modificado_en = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    @hybrid_property
    def autor(self):
        """Propiedad de compatibilidad que combina nombre y apellido."""
        if self.apellido_autor and self.nombre_autor:
            return f"{self.apellido_autor}, {self.nombre_autor}"
        return self.apellido_autor or self.nombre_autor or ""

    @autor.expression
    def autor(cls):
        # Concatenación robusta para búsqueda (Apellido, Nombre) con unaccent
        from sqlalchemy import func
        return func.public.unaccent(case(
            (and_(cls.apellido_autor != None, cls.nombre_autor != None),
             cls.apellido_autor + ", " + cls.nombre_autor),
            (cls.apellido_autor != None, cls.apellido_autor),
            (cls.nombre_autor != None, cls.nombre_autor),
            else_=""
        ))

    @autor.setter
    def autor(self, value):
        """Setter de compatibilidad (no realiza cambios directos si se usan campos separados)."""
        pass
    
    # Vectores semánticos para búsqueda de Deep Learning
    embedding_vector = db.Column(db.JSON, nullable=True)  # Array de floats del embedding
    embedding_model = db.Column(db.String(100), nullable=True)  # Modelo usado (text-embedding-3-small, etc.)
    embedding_generado_en = db.Column(db.DateTime, nullable=True)  # Timestamp de generación
    
    # Índices para optimizar queries frecuentes
    __table_args__ = (
        db.Index('idx_prensa_proyecto_id', 'proyecto_id'),
        db.Index('idx_prensa_fecha_original', 'fecha_original'),
        db.Index('idx_prensa_publicacion', 'publicacion'),
        db.Index('idx_prensa_ciudad', 'ciudad'),
        db.Index('idx_prensa_autor', 'nombre_autor'),
        db.Index('idx_prensa_anio', 'anio'),
        db.Index('idx_prensa_incluido', 'incluido'),
        db.Index('idx_prensa_es_referencia', 'es_referencia'),
        db.Index('idx_prensa_id_publicacion', 'id_publicacion'),
    )

    def __repr__(self):
        return f"<Prensa {self.id} {self.titulo}>"


class ImagenPrensa(db.Model):
    __tablename__ = "imagenes_prensa"
    id = db.Column(db.Integer, primary_key=True)
    prensa_id = db.Column(
        db.Integer, db.ForeignKey("prensa.id", ondelete="CASCADE"), nullable=False
    )
    filename = db.Column(db.Text, nullable=False)
    fecha_subida = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<ImagenPrensa {self.id} {self.filename}>"


def get_or_create_city_with_coords(session, city_name, country=None):
    """
    Busca la ciudad en la tabla Ciudad. Si no existe, la crea sin coordenadas.
    Devuelve el objeto Ciudad (creado o existente).
    
    Nota: La funcionalidad de geocodificación automática ha sido deshabilitada.
    Las coordenadas deben ser añadidas manualmente si se requieren.
    """
    if not city_name:
        return None
    
    city = session.query(Ciudad).filter(Ciudad.name == city_name).first()
    
    if not city:
        # Crear ciudad sin coordenadas
        city = Ciudad(name=city_name, lat=None, lon=None)
        session.add(city)
        session.commit()
    
    return city


class ValidacionDuplicados(db.Model):
    """
    Almacena pares de registros que el usuario ha validado como NO DUPLICADOS
    para evitar que vuelvan a aparecer en los reportes de calidad.
    """
    __tablename__ = "validacion_duplicados"

    id = db.Column(db.Integer, primary_key=True)
    proyecto_id = db.Column(db.Integer, db.ForeignKey("proyectos.id"), nullable=False)
    
    # IDs de los registros de prensa comparados
    # Ordenamos siempre menor -> mayor al guardar para facilitar búsquedas
    prensa_id_1 = db.Column(db.Integer, db.ForeignKey("prensa.id"), nullable=False)
    prensa_id_2 = db.Column(db.Integer, db.ForeignKey("prensa.id"), nullable=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Índice único para evitar duplicados en esta misma tabla
    __table_args__ = (
        db.UniqueConstraint('proyecto_id', 'prensa_id_1', 'prensa_id_2', name='uix_validacion_pair'),
        db.Index('idx_validacion_p1', 'prensa_id_1'),
        db.Index('idx_validacion_p2', 'prensa_id_2'),
    )

    def __repr__(self):
        return f"<Validacion {self.prensa_id_1}-{self.prensa_id_2}>"


class Tema(db.Model):
    __tablename__ = 'temas'
    id = db.Column(db.Integer, primary_key=True)
    proyecto_id = db.Column(db.Integer, db.ForeignKey('proyectos.id'), nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text)
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('proyecto_id', 'nombre', name='uq_tema_proyecto_nombre'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'proyecto_id': self.proyecto_id,
            'nombre': self.nombre,
            'descripcion': self.descripcion,
            'creado_en': self.creado_en.isoformat() if self.creado_en else None
        }

class SemanticConcept(db.Model):
    __tablename__ = "semantic_concepts"

    id = db.Column(db.Integer, primary_key=True)
    proyecto_id = db.Column(db.Integer, db.ForeignKey("proyectos.id"), nullable=True) # None means global
    tema = db.Column(db.String(255), nullable=False)
    concepto = db.Column(db.Text, nullable=False)
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)

class MetadataOption(db.Model):
    """Modelo para gestionar opciones dinámicas de metadatos (Géneros, Subgéneros, Frecuencia)"""
    __tablename__ = "metadata_options"

    id = db.Column(db.Integer, primary_key=True)
    categoria = db.Column(db.String(50), nullable=False, index=True) # tipo_recurso, tipo_publicacion, frecuencia
    valor = db.Column(db.String(100), nullable=False)
    etiqueta = db.Column(db.String(100), nullable=False)
    grupo = db.Column(db.String(100), nullable=True) # Para optgroups
    orden = db.Column(db.Integer, default=0)

    def __repr__(self):
        return f"<MetadataOption {self.categoria}: {self.etiqueta}>"

    def to_dict(self):
        return {
            'id': self.id,
            'categoria': self.categoria,
            'valor': self.valor,
            'etiqueta': self.etiqueta,
            'grupo': self.grupo,
            'orden': self.orden
        }


class EdicionTipoRecurso(db.Model):
    """Modelo para gestionar las opciones del desplegable de ediciones según tipo de recurso"""
    __tablename__ = "ediciones_tipo_recurso"

    id = db.Column(db.Integer, primary_key=True)
    tipo_recurso = db.Column(db.String(50), nullable=False, index=True) # prensa, libro, etc.
    valor = db.Column(db.String(100), nullable=False) # lo que se guarda en BD
    etiqueta = db.Column(db.String(100), nullable=False) # lo que ve el usuario
    orden = db.Column(db.Integer, default=0) # para ordenar el desplegable

    def __repr__(self):
        return f"<Edicion {self.tipo_recurso}: {self.etiqueta}>"

    def to_dict(self):
        return {
            'value': self.valor,
            'text': self.etiqueta
        }


class ServicioIDE(db.Model):
    """
    Catálogo global compartido de servicios WMS/WMTS.
    Compartido entre todos los usuarios y proyectos.
    Cualquier usuario puede añadir nuevos servicios; se guardan aquí para todos.
    """
    __tablename__ = "servicios_ide"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(255), nullable=False)
    tipo = db.Column(db.String(10), nullable=False, default='WMS')   # 'WMS' | 'WMTS'
    url = db.Column(db.Text, nullable=False)
    capas = db.Column(db.Text, nullable=True)          # Comma-separated layer names
    formato = db.Column(db.String(50), default='image/png')
    attribution = db.Column(db.Text, nullable=True)
    pais = db.Column(db.String(100), nullable=True)
    categoria = db.Column(db.String(100), nullable=True)
    opacidad = db.Column(db.Float, default=0.85)
    # Usuario que lo registró (NULL = pre-cargado / sistema)
    creado_por = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=True)
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('url', 'tipo', 'capas', name='uq_servicio_ide_url_tipo_capas'),
        db.Index('idx_servicio_ide_pais', 'pais'),
        db.Index('idx_servicio_ide_tipo', 'tipo'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.nombre,
            'type': self.tipo,
            'url': self.url,
            'layers': self.capas or '',
            'format': self.formato or 'image/png',
            'attribution': self.attribution or '',
            'country': self.pais or '',
            'category': self.categoria or '',
            'opacity': self.opacidad or 0.85,
        }

    def __repr__(self):
        return f"<ServicioIDE {self.tipo} {self.nombre}>"


class CapaGeografica(db.Model):

    """Modelo para almacenar capas geográficas externas (ArcGIS/QGIS)"""
    __tablename__ = "capas_geograficas"
    id = db.Column(db.Integer, primary_key=True)
    proyecto_id = db.Column(db.Integer, db.ForeignKey("proyectos.id", ondelete="CASCADE"), nullable=False)
    nombre = db.Column(db.String(255), nullable=False)
    tipo = db.Column(db.String(50), nullable=False)  # geojson, kml, shapefile
    filename = db.Column(db.String(255), nullable=False)
    visible = db.Column(db.Boolean, default=True)
    color = db.Column(db.String(20), default="#3388ff")
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)

    proyecto = db.relationship("Proyecto", backref=db.backref("capas", cascade="all, delete-orphan", lazy=True))


class MapaHistorico(db.Model):
    """Modelo para mapas históricos georreferenciados mediante GCPs (Ground Control Points)"""
    __tablename__ = "mapas_historicos"
    id = db.Column(db.Integer, primary_key=True)
    proyecto_id = db.Column(db.Integer, db.ForeignKey("proyectos.id", ondelete="CASCADE"), nullable=False)
    nombre = db.Column(db.String(255), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    
    # Puntos de control almacenados como JSON: [{"img": [x, y], "geo": [lat, lon]}, ...]
    gcps = db.Column(db.Text, nullable=True, default='[]')
    
    # Polígono de recorte en coordenadas de imagen: [[x1, y1], [x2, y2], ...]
    crop_polygon = db.Column(db.Text, nullable=True, default=None)
    
    # Configuración de visualización
    opacidad = db.Column(db.Float, default=0.7)
    visible = db.Column(db.Boolean, default=True)
    
    # Metadata adicional
    anio = db.Column(db.Integer, nullable=True)
    autor = db.Column(db.String(255), nullable=True)
    fuente = db.Column(db.String(255), nullable=True)
    escala = db.Column(db.String(100), nullable=True)
    descripcion = db.Column(db.Text, nullable=True)
    licencia = db.Column(db.String(120), nullable=True, default="CC BY 4.0")

    creado_en = db.Column(db.DateTime, default=datetime.utcnow)

    proyecto = db.relationship("Proyecto", backref=db.backref("mapas_historicos", cascade="all, delete-orphan", lazy=True))

    def __repr__(self):
        return f"<MapaHistorico {self.nombre}>"


class VectorLayer(db.Model):
    """Modelo para capas vectoriales GIS digitalizadas sobre el mapa del corpus"""
    __tablename__ = "vector_layers"
    id = db.Column(db.Integer, primary_key=True)
    proyecto_id = db.Column(db.Integer, db.ForeignKey("proyectos.id", ondelete="CASCADE"), nullable=False)
    nombre = db.Column(db.String(255), nullable=False)
    descripcion = db.Column(db.Text, nullable=True)
    
    # Tipo de geometría: 'point', 'line', 'polygon', 'mixed'
    tipo_geometria = db.Column(db.String(20), nullable=False, default='mixed')
    
    # GeoJSON completo con todas las features
    geojson_data = db.Column(db.Text, nullable=False, default='{"type":"FeatureCollection","features":[]}')
    
    # Configuración visual
    color = db.Column(db.String(20), default='#ff9800')
    opacidad = db.Column(db.Float, default=0.7)
    grosor_linea = db.Column(db.Integer, default=3)  # Para líneas y bordes de polígonos
    visible = db.Column(db.Boolean, default=True)
    bloqueada = db.Column(db.Boolean, default=False)  # Prevents interaction and editing
    orden = db.Column(db.Integer, default=0)  # Orden de visualización / Z-index
    
    # Metadatos adicionales
    num_features = db.Column(db.Integer, default=0)
    area_total = db.Column(db.Float, nullable=True)  # En km² (para polígonos)
    longitud_total = db.Column(db.Float, nullable=True)  # En km (para líneas)
    
    # Configuración avanzada
    estilo_personalizado = db.Column(db.Text, nullable=True)  # JSON con estilos avanzados
    etiquetas_visibles = db.Column(db.Boolean, default=False)
    snap_enabled = db.Column(db.Boolean, default=False)  # Snapping a otras geometrías
    
    # Colaboración y versionado
    creado_por = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=True)
    modificado_por = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=True)
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)
    modificado_en = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Vínculo con documentos del corpus (opcional)
    vinculado_noticias = db.Column(db.Text, nullable=True)  # JSON array con IDs de noticias relacionadas
    
    proyecto = db.relationship("Proyecto", backref=db.backref("vector_layers", cascade="all, delete-orphan", lazy=True))
    usuario_creador = db.relationship("Usuario", foreign_keys=[creado_por], backref="capas_creadas")
    usuario_modificador = db.relationship("Usuario", foreign_keys=[modificado_por], backref="capas_modificadas")

    def __repr__(self):
        return f"<VectorLayer {self.nombre} ({self.num_features} features)>"
    
    def to_dict(self):
        """Serializa la capa a diccionario para API"""
        import json
        return {
            'id': self.id,
            'nombre': self.nombre,
            'descripcion': self.descripcion,
            'tipo_geometria': self.tipo_geometria,
            'geojson': json.loads(self.geojson_data) if self.geojson_data else {"type": "FeatureCollection", "features": []},
            'color': self.color,
            'opacidad': self.opacidad,
            'grosor_linea': self.grosor_linea,
            'visible': self.visible,
            'bloqueada': self.bloqueada,
            'orden': self.orden,
            'num_features': self.num_features,
            'area_total': self.area_total,
            'longitud_total': self.longitud_total,
            'etiquetas_visibles': self.etiquetas_visibles,
            'snap_enabled': self.snap_enabled,
            'creado_en': self.creado_en.isoformat() if self.creado_en else None,
            'modificado_en': self.modificado_en.isoformat() if self.modificado_en else None,
            'vinculado_noticias': json.loads(self.vinculado_noticias) if self.vinculado_noticias else []
        }


# ============================================================================
# 15. PROYECTOS COMPARTIDOS (Multi-user collaboration)
# ============================================================================

class ProyectoCompartido(db.Model):
    """
    Tabla intermedia para gestionar proyectos compartidos entre usuarios.
    Permite que múltiples usuarios colaboren en un mismo proyecto.
    """
    __tablename__ = "proyectos_compartidos"

    id = db.Column(db.Integer, primary_key=True)
    proyecto_id = db.Column(db.Integer, db.ForeignKey("proyectos.id", ondelete="CASCADE"), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False)
    compartido_por = db.Column(db.Integer, db.ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True)
    
    # Timestamps
    compartido_en = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    activo_desde = db.Column(db.DateTime, nullable=True)  # NULL = no está usando el proyecto actualmente
    
    # Relationships
    proyecto = db.relationship("Proyecto", backref=db.backref("compartidos", cascade="all, delete-orphan", lazy=True))
    usuario = db.relationship("Usuario", foreign_keys=[usuario_id], backref="proyectos_compartidos")
    compartido_por_usuario = db.relationship("Usuario", foreign_keys=[compartido_por])
    
    # Índices para optimizar queries
    __table_args__ = (
        db.UniqueConstraint('proyecto_id', 'usuario_id', name='uq_proyecto_usuario'),
        db.Index('idx_proyecto_compartido_proyecto', 'proyecto_id'),
        db.Index('idx_proyecto_compartido_usuario', 'usuario_id'),
    )

    def __repr__(self):
        return f"<ProyectoCompartido proyecto_id={self.proyecto_id} usuario_id={self.usuario_id}>"

    def esta_activo(self):
        """Verifica si el usuario tiene el proyecto activo (lock activo en los últimos 5 minutos)"""
        if not self.activo_desde:
            return False
        # Considerar activo si se activó en los últimos 5 minutos
        tiempo_transcurrido = datetime.utcnow() - self.activo_desde
        return tiempo_transcurrido.total_seconds() < 300  # 5 minutos

# ============================================================================
# 16. SIMULACIÓN DE RUTAS E IA ATMOSFÉRICA
# ============================================================================

class SimulationRoute(db.Model):
    """Modelo para guardar configuraciones de rutas del simulador"""
    __tablename__ = "simulation_routes"
    id = db.Column(db.Integer, primary_key=True)
    proyecto_id = db.Column(db.Integer, db.ForeignKey("proyectos.id", ondelete="CASCADE"), nullable=False)
    nombre = db.Column(db.String(255), nullable=False)
    descripcion = db.Column(db.Text, nullable=True)
    
    # Datos de la ruta (waypoints, dates, config) almacenados como JSON
    waypoints = db.Column(db.Text, nullable=False, default='[]')
    cronograma = db.Column(db.Text, nullable=False, default='[]')
    configuracion = db.Column(db.Text, nullable=True, default='{}')
    
    # ID de la capa vectorial asociada (si existe)
    vector_layer_id = db.Column(db.Integer, db.ForeignKey("vector_layers.id", ondelete="SET NULL"), nullable=True)
    
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)
    modificado_en = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    proyecto = db.relationship("Proyecto", backref=db.backref("simulation_routes", cascade="all, delete-orphan", lazy=True))

    def __repr__(self):
        return f"<SimulationRoute {self.nombre}>"

class SimulationLog(db.Model):
    """Logs de análisis de la IA generados durante una simulación"""
    __tablename__ = "simulation_logs"
    id = db.Column(db.Integer, primary_key=True)
    route_id = db.Column(db.Integer, db.ForeignKey("simulation_routes.id", ondelete="CASCADE"), nullable=False)
    
    timestamp = db.Column(db.DateTime, default=datetime.utcnow) # Momento real de la grabación
    sim_time = db.Column(db.DateTime, nullable=False)           # Momento simulado (fecha del mapa)
    
    lat = db.Column(db.Float, nullable=False)
    lon = db.Column(db.Float, nullable=False)
    weather_layer_id = db.Column(db.String(100), nullable=True)
    
    analysis = db.Column(db.Text, nullable=False)
    modifier = db.Column(db.Float, default=1.0)
    
    route = db.relationship("SimulationRoute", backref=db.backref("logs", cascade="all, delete-orphan", lazy=True))

    def __repr__(self):
        return f"<SimulationLog Route={self.route_id} Time={self.sim_time}>"

# ============================================================================
# 17. GESTIÓN DE PASAJEROS (Proyecto Sirio)
# ============================================================================


class PasajeroSirio(db.Model):
    """Modelo para almacenar los datos de los pasajeros del S.S. Sirio"""
    __tablename__ = "pasajeros_sirio"

    id = db.Column(db.Integer, primary_key=True)
    proyecto_id = db.Column(db.Integer, db.ForeignKey("proyectos.id"), nullable=True)
    nombre = db.Column(db.String(255), nullable=True)
    apellidos = db.Column(db.String(255), nullable=True)
    edad = db.Column(db.Float, nullable=True)
    sexo = db.Column(db.String(50), nullable=True)
    pasaje = db.Column(db.String(100), nullable=True) # Clase o Tripulación
    municipio = db.Column(db.String(255), nullable=True)
    provincia = db.Column(db.String(255), nullable=True)
    region = db.Column(db.String(255), nullable=True)
    puerto_embarque = db.Column(db.String(255), nullable=True)
    
    # Fechas (pueden venir vacías)
    fecha_hundimiento = db.Column(db.String(100), nullable=True)
    fecha_destino_final = db.Column(db.String(100), nullable=True)
    fecha_llegada_cartagena = db.Column(db.String(100), nullable=True)
    fecha_salida_cartagena = db.Column(db.String(100), nullable=True)
    
    pais = db.Column(db.String(100), nullable=True)
    foto = db.Column(db.String(255), nullable=True)
    ciudad_destino = db.Column(db.String(255), nullable=True)
    ciudad_destino_final = db.Column(db.String(255), nullable=True)
    estado = db.Column(db.String(100), nullable=True) # Sobreviviente / Desaparecido
    
    lat = db.Column(db.Float, nullable=True)
    lon = db.Column(db.Float, nullable=True)
    
    punto_residencia = db.Column(db.String(255), nullable=True)
    comentarios = db.Column(db.Text, nullable=True)
    
    # Fuentes y marcas de presencia (almacenado como JSON para flexibilidad)
    fuentes_presencia = db.Column(db.JSON, nullable=True)
    
    # Listas de embarque (Retorno / Continuar viaje)
    en_lista_italia_mvd = db.Column(db.Boolean, default=False)
    en_lista_italia_ba = db.Column(db.Boolean, default=False)
    en_lista_ravena_sp = db.Column(db.Boolean, default=False)
    en_lista_diana_bcn = db.Column(db.Boolean, default=False)
    en_lista_orione_ge = db.Column(db.Boolean, default=False)
    
    hospedaje_cartagena = db.Column(db.String(255), nullable=True)
    
    # Detalle del Itinerario
    fecha_emb_napoles = db.Column(db.String(100), nullable=True)
    fecha_emb_genova = db.Column(db.String(100), nullable=True)
    fecha_emb_barcelona = db.Column(db.String(100), nullable=True)
    situacion_post_naufragio = db.Column(db.String(100), nullable=True) # Continúa viaje / Retorno
    puerto_retorno = db.Column(db.String(100), nullable=True)
    fecha_retorno = db.Column(db.String(100), nullable=True)
    
    # Relación con Publicaciones (listas donde aparece)
    publicaciones = db.relationship('Publicacion', 
                                   secondary=pasajero_publicacion, 
                                   backref=db.backref('pasajeros_sirio', lazy='dynamic'))
    
    # Relación con Prensa (menciones en noticias específicas)
    menciones_prensa = db.relationship('Prensa',
                                      secondary=pasajero_prensa,
                                      backref=db.backref('pasajeros_mencionados', lazy='dynamic'))
    
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<PasajeroSirio {self.nombre} {self.apellidos}>"

    def to_dict(self):
        return {
            'id': self.id,
            'nombre': self.nombre,
            'apellidos': self.apellidos,
            'edad': self.edad,
            'sexo': self.sexo,
            'pasaje': self.pasaje,
            'municipio': self.municipio,
            'provincia': self.provincia,
            'region': self.region,
            'puerto_embarque': self.puerto_embarque,
            'estado': self.estado,
            'lat': self.lat,
            'lon': self.lon,
            'en_lista_italia_mvd': self.en_lista_italia_mvd,
            'en_lista_italia_ba': self.en_lista_italia_ba,
            'en_lista_ravena_sp': self.en_lista_ravena_sp,
            'en_lista_orione_ge': self.en_lista_orione_ge,
            'hospedaje_cartagena': self.hospedaje_cartagena,
            'fecha_emb_napoles': self.fecha_emb_napoles,
            'fecha_emb_genova': self.fecha_emb_genova,
            'fecha_emb_barcelona': self.fecha_emb_barcelona,
            'situacion_post_naufragio': self.situacion_post_naufragio,
            'puerto_retorno': self.puerto_retorno,
            'fecha_retorno': self.fecha_retorno
        }

    def get_relaciones_flat(self):
        """Devuelve un dict {id_pariente: rol_del_pariente_para_mi}"""
        rels = {}
        # Caso 1: Yo soy el objeto (Riccardo). Mis parientes son los sujetos (Benigno).
        # El rol de Benigno para mí es el que pone en la relación (Hijo).
        for r in self.relaciones_como_objeto:
            rels[str(r.pasajero_id)] = r.tipo_relacion
            
        # Caso 2: Yo soy el sujeto (Benigno). Mis parientes son los objetos (Riccardo).
        # El rol de Riccardo para mí es el inverso del que pone en la relación.
        # Si yo soy Hijo de Riccardo, Riccardo es mi Padre (si es hombre) o Madre (si es mujer).
        for r in self.relaciones_como_sujeto:
            obj = r.relacionado
            obj_sexo = obj.sexo if obj else 'Hombre'
            tipo = r.tipo_relacion.upper()
            
            rol_inverso = 'Pariente'
            if tipo == 'HIJO' or tipo == 'HIJA':
                rol_inverso = 'PADRE' if obj_sexo == 'Hombre' else 'MADRE'
            elif tipo == 'PADRE' or tipo == 'MADRE':
                rol_inverso = 'HIJO' if obj_sexo == 'Hombre' else 'HIJA'
            elif tipo == 'HERMANO' or tipo == 'HERMANA':
                rol_inverso = 'HERMANO' if obj_sexo == 'Hombre' else 'HERMANA'
            elif tipo == 'ESPOSO':
                rol_inverso = 'ESPOSA'
            elif tipo == 'ESPOSA':
                rol_inverso = 'ESPOSO'
            elif tipo == 'HIJASTRO' or tipo == 'HIJASTRA':
                rol_inverso = 'PADRASTRO' if obj_sexo == 'Hombre' else 'MADRASTRA'
            elif tipo == 'PADRASTRO' or tipo == 'MADRASTRA':
                rol_inverso = 'HIJASTRO' if obj_sexo == 'Hombre' else 'HIJASTRA'
            elif tipo == 'ABUELO' or tipo == 'ABUELA':
                rol_inverso = 'NIETO' if obj_sexo == 'Hombre' else 'NIETA'
            elif tipo == 'NIETO' or tipo == 'NIETA':
                rol_inverso = 'ABUELO' if obj_sexo == 'Hombre' else 'ABUELA'
            elif tipo == 'TÍO' or tipo == 'TÍA' or tipo == 'TIO' or tipo == 'TIA':
                rol_inverso = 'SOBRINO' if obj_sexo == 'Hombre' else 'SOBRINA'
            elif tipo == 'SOBRINO' or tipo == 'SOBRINA':
                rol_inverso = 'TÍO' if obj_sexo == 'Hombre' else 'TÍA'
            
            rels[str(r.relacionado_id)] = rol_inverso
            
        return rels

class PasajeroRelacion(db.Model):
    """Modelo para vincular estructuralmente a pasajeros (Padre, Hijo, Mujer, etc.)"""
    __tablename__ = "pasajero_relaciones"
    
    id = db.Column(db.Integer, primary_key=True)
    # El pasajero que "tiene" la relación (ej: el hijo)
    pasajero_id = db.Column(db.Integer, db.ForeignKey("pasajeros_sirio.id", ondelete="CASCADE"), nullable=False)
    # El pasajero con el que se relaciona (ej: el padre)
    relacionado_id = db.Column(db.Integer, db.ForeignKey("pasajeros_sirio.id", ondelete="CASCADE"), nullable=False)
    
    tipo_relacion = db.Column(db.String(100), nullable=False) # 'Padre', 'Hijo', 'Mujer', 'Hermano', 'Madre'
    comentarios = db.Column(db.Text, nullable=True)
    orden = db.Column(db.Integer, default=0)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)

    # Relaciones para acceder fácilmente
    pasajero = db.relationship("PasajeroSirio", foreign_keys=[pasajero_id], 
                              backref=db.backref("relaciones_como_sujeto", cascade="all, delete-orphan"))
    relacionado = db.relationship("PasajeroSirio", foreign_keys=[relacionado_id], 
                                 backref=db.backref("relaciones_como_objeto", cascade="all, delete-orphan"))

    def __repr__(self):
        return f"<PasajeroRelacion {self.pasajero_id} es {self.tipo_relacion} de {self.relacionado_id}>"


class LloydsFicha(db.Model):
    """
    Ficha técnica exhaustiva del S.S. Sirio basada en el Lloyd's Register Survey Nº 6147 (1883).
    Mapeada a la tabla plana lloyds_register_survey_inspeccion_absoluta.
    """
    __tablename__ = 'lloyds_register_survey_inspeccion_absoluta'
    id = db.Column(db.Integer, primary_key=True)
    proyecto_id = db.Column(db.Integer, db.ForeignKey("proyectos.id"), nullable=True)

    # 1. ENCABEZADO Y DATOS GENERALES
    survey_no_numero_inspeccion = db.Column(db.String(255))
    survey_held_at_inspeccion_en = db.Column(db.String(255))
    date_first_survey_fecha_primera_inspeccion = db.Column(db.String(255))
    last_survey_ultima_inspeccion = db.Column(db.String(255))
    vessel_type_tipo_buque = db.Column(db.String(255))
    master_capitan = db.Column(db.String(255))
    built_at_construido_en = db.Column(db.String(255))
    when_built_cuando_construido = db.Column(db.String(255))
    by_whom_built_por_quien_construido = db.Column(db.String(255))
    owners_propietarios = db.Column(db.String(255))
    port_belonging_puerto_pertenencia = db.Column(db.String(255))
    destined_voyage_viaje_destinado = db.Column(db.String(255))
    launched_lanzado = db.Column(db.String(255))
    owners_residence_residencia_propietarios = db.Column(db.String(255))
    surveyed_while_inspeccionado_mientras = db.Column(db.String(255))

    # 2. TONELAJE Y DIMENSIONES
    gross_tonnage_tonelaje_bruto = db.Column(db.String(255))
    net_tonnage_tonelaje_neto = db.Column(db.String(255))
    tonnage_under_deck_tonelaje_bajo_cubierta = db.Column(db.String(255))
    tonnage_third_deck_tonelaje_tercera_cubierta = db.Column(db.String(255))
    tonnage_houses_on_deck_tonelaje_casetas = db.Column(db.String(255))
    tonnage_forecastle_tonelaje_castillo_proa = db.Column(db.String(255))
    less_crew_space_menos_espacio_tripulacion = db.Column(db.String(255))
    less_engine_room_menos_sala_maquinas = db.Column(db.String(255))
    register_tonnage_tonelaje_registro = db.Column(db.String(255))
    length_overall_eslora_total = db.Column(db.String(255))
    length_between_pp_eslora_entre_pp = db.Column(db.String(255))
    breadth_extreme_manga_maxima = db.Column(db.String(255))
    depth_of_hold_puntal_bodega = db.Column(db.String(255))
    depth_moulded_puntal_de_construccion = db.Column(db.String(255))
    half_breadth_moulded_media_manga = db.Column(db.String(255))
    depth_keel_to_main_deck_puntal_quilla_cubierta = db.Column(db.String(255))
    girth_half_midship_frame_perimetro_media_cuaderna = db.Column(db.String(255))
    first_number_primer_numero = db.Column(db.String(255))
    second_number_segundo_numero = db.Column(db.String(255))
    proportions_breadths_to_length_proporcion_manga_eslora = db.Column(db.String(255))
    proportions_depths_to_length_upper_proporcion_puntal_eslora_sup = db.Column(db.String(255))
    proportions_depths_to_length_main_proporcion_puntal_eslora_ppal = db.Column(db.String(255))

    # 3. ESTRUCTURA (QUILAS, RODA, CUADERNAS)
    keel_material_material_quilla = db.Column(db.String(255))
    keel_size_dimension_quilla = db.Column(db.String(255))
    stem_material_material_roda = db.Column(db.String(255))
    stem_size_dimension_roda = db.Column(db.String(255))
    stern_post_material_material_codaste = db.Column(db.String(255))
    stern_post_size_dimension_codaste = db.Column(db.String(255))
    frames_material_material_cuadernas = db.Column(db.String(255))
    frames_spacing_espaciado_cuadernas = db.Column(db.String(255))
    frames_size_dimension_cuadernas = db.Column(db.String(255))
    reverse_frames_reves_cuadernas = db.Column(db.String(255))
    floors_material_material_varengas = db.Column(db.String(255))
    floors_size_dimension_varengas = db.Column(db.String(255))
    floors_thickness_espesor_varengas = db.Column(db.String(255))

    # 4. SOBREQUILLAS Y PALMEJARES (Keelsons & Stringers)
    keelsons_main_sobrequilla_principal = db.Column(db.String(255))
    keelsons_intercostal_sobrequilla_intercostal = db.Column(db.String(255))
    side_keelsons_sobrequillas_laterales = db.Column(db.String(255))
    bilge_keelsons_sobrequillas_pantoque = db.Column(db.String(255))
    bilge_stringers_palmejares_pantoque = db.Column(db.String(255))
    side_stringers_palmejares_laterales = db.Column(db.String(255))
    keelsons_connected_butts = db.Column(db.String(255)) # Properly connected/shifted

    # 5. DETALLES DE PLANCHAJE Y REMACHADO (Detailed Plating)
    frames_riveted_rivets_size = db.Column(db.String(255))
    plating_garboard_riveting_to_keel = db.Column(db.String(255))
    plating_garboard_edges_riveting = db.Column(db.String(255))
    plating_bilge_butts_thickness = db.Column(db.String(255))
    plating_side_edges_riveting = db.Column(db.String(255))
    plating_side_butts_riveting = db.Column(db.String(255))
    plating_sheerstrake_edges = db.Column(db.String(255))
    plating_sheerstrake_butts = db.Column(db.String(255))
    plating_spar_sheerstrake_butts = db.Column(db.String(255))
    plating_stringer_plate_butts = db.Column(db.String(255))
    plating_spar_stringer_plate_butts = db.Column(db.String(255))
    plating_laps_breadth_double = db.Column(db.String(255))
    plating_laps_breadth_single = db.Column(db.String(255))
    butt_straps_riveted_type = db.Column(db.String(255))
    breasthooks_no = db.Column(db.String(255))
    crutches_no = db.Column(db.String(255))

    # 6. CALIDAD DE OBRA (Workmanship)
    workmanship_plating_butts = db.Column(db.String(255))
    workmanship_carvel_edges = db.Column(db.String(255))
    workmanship_fillings_solid = db.Column(db.String(255))
    workmanship_riveting_holes = db.Column(db.String(255))
    workmanship_riveting_countersunk = db.Column(db.String(255))
    workmanship_rivets_break = db.Column(db.String(255))

    # 7. MÁSTILES Y VELAMEN (Page 2 Original)
    mast_fore_material = db.Column(db.String(255))
    mast_fore_length = db.Column(db.String(255))
    mast_fore_dia = db.Column(db.String(255))
    mast_main_material = db.Column(db.String(255))
    mast_main_length = db.Column(db.String(255))
    mast_main_dia = db.Column(db.String(255))
    mast_mizzen_material = db.Column(db.String(255))
    mast_mizzen_length = db.Column(db.String(255))
    mast_mizzen_dia = db.Column(db.String(255))
    sails_full_set = db.Column(db.String(255))
    rigging_standing_running = db.Column(db.String(255))
    rigging_quality = db.Column(db.String(255))

    # 8. ANCLAS (Pesos en Cwt = 50.8kg)
    anchor_bower_1_weight = db.Column(db.String(255))
    anchor_bower_2_weight = db.Column(db.String(255))
    anchor_bower_3_weight = db.Column(db.String(255))
    anchor_stream_weight = db.Column(db.String(255))
    anchor_kedge_1_weight = db.Column(db.String(255))
    anchor_kedge_2_weight = db.Column(db.String(255))

    # 9. CABLES Y CADENAS (Cables and Chains)
    cable_chain_length = db.Column(db.String(255))
    cable_chain_size = db.Column(db.String(255))
    cable_chain_test = db.Column(db.String(255))
    cable_towline_length = db.Column(db.String(255))
    cable_towline_size = db.Column(db.String(255))
    cable_hawser_length = db.Column(db.String(255))
    cable_hawser_size = db.Column(db.String(255))
    cable_warp_length = db.Column(db.String(255))
    cable_warp_size = db.Column(db.String(255))

    # 10. EQUIPAMIENTO Y MAQUINARIA (Equipment)
    windlass_type = db.Column(db.String(255))
    windlass_maker = db.Column(db.String(255))
    windlass_condition = db.Column(db.String(255))
    capstan_type = db.Column(db.String(255))
    capstan_condition = db.Column(db.String(255))
    rudder_description = db.Column(db.String(255))
    rudder_condition = db.Column(db.String(255))
    pumps_number_type = db.Column(db.String(255))
    pumps_condition = db.Column(db.String(255))
    boats_number = db.Column(db.String(255))
    boats_long_boats_no = db.Column(db.String(255))
    boats_steam_launch_no = db.Column(db.String(255))

    # 11. ESCOTILLAS Y CARBONERAS (Hatchways & Bunkers)
    engine_room_skylights_const = db.Column(db.String(255))
    engine_room_skylights_secured = db.Column(db.String(255))
    deadlights_bad_weather = db.Column(db.String(255))
    coal_bunker_openings_const = db.Column(db.String(255))
    coal_bunker_openings_lids = db.Column(db.String(255))
    coal_bunker_openings_height = db.Column(db.String(255))
    scuppers_arrangements = db.Column(db.String(255))
    cargo_hatchways_formed = db.Column(db.String(255))
    main_hatch_size = db.Column(db.String(255))
    fore_hatch_size = db.Column(db.String(255))
    quarter_hatch_size = db.Column(db.String(255))
    extraordinary_size_framed = db.Column(db.String(255))
    shifting_beams_arrangement = db.Column(db.String(255))
    hatches_strong_efficient = db.Column(db.String(255))

    # 12. CRONOLOGÍA DE CONSTRUCCIÓN (Exhaustive Chronology)
    special_survey_no = db.Column(db.String(255))      # Order for Special Survey No. 1764
    special_survey_date = db.Column(db.String(255))    # Date 14th June 1882
    builders_yard_no = db.Column(db.String(255))       # No. 385 in builder's yard
    survey_1st_frame = db.Column(db.Text)              # 1st. On the several parts of the frame...
    survey_2nd_plating = db.Column(db.Text)            # 2nd. On the plating during riveting...
    survey_3rd_beams = db.Column(db.Text)              # 3rd. When beams were in and fastened...
    survey_4th_complete = db.Column(db.Text)           # 4th. When ship was complete...
    survey_5th_launched = db.Column(db.Text)           # 5th. After launching and equipped
    
    survey_date_1st = db.Column(db.String(255)) # 1st. On the keel
    survey_date_2nd = db.Column(db.String(255)) # 2nd. While building

    # 13. FIRMAS Y FABRICANTES (Makers & Signatures)
    iron_quality = db.Column(db.String(255))
    manufacturers_trade_mark = db.Column(db.String(255))
    builder_signature = db.Column(db.String(255))
    surveyor_signature = db.Column(db.String(255))

    # 5. BAOS Y CUBIERTAS
    upper_deck_beams_baos_cubierta_superior = db.Column(db.String(255))
    main_deck_beams_baos_cubierta_principal = db.Column(db.String(255))
    lower_deck_beams_baos_cubierta_inferior = db.Column(db.String(255))
    deck_material_material_cubiertas = db.Column(db.String(255))
    deck_thickness_espesor_cubiertas = db.Column(db.String(255))

    # 6. PLANCHAJE EXTERIOR
    plating_garboard_strakes_tracas_aparadura = db.Column(db.String(255))
    plating_bottom_strakes_tracas_fondo = db.Column(db.String(255))
    plating_bilge_strakes_tracas_pantoque = db.Column(db.String(255))
    plating_side_strakes_tracas_costado = db.Column(db.String(255))
    plating_sheer_strakes_tracas_cinta = db.Column(db.String(255))
    plating_upper_works_obras_muertas = db.Column(db.String(255))

    # 7. REMACHADO Y FIJACIONES
    riveting_keel_remachado_quilla = db.Column(db.String(255))
    riveting_stem_remachado_roda = db.Column(db.String(255))
    riveting_butts_remachado_topes = db.Column(db.String(255))
    riveting_edges_remachado_costuras = db.Column(db.String(255))
    riveting_size_diametro_remaches = db.Column(db.String(255))

    # 8. MAMPAROS Y ESTANQUEIDAD
    bulkheads_no_numero_mamparos = db.Column(db.String(255))
    bulkheads_height_altura_mamparos = db.Column(db.String(255))
    bulkheads_thickness_espesor_mamparos = db.Column(db.String(255))
    water_tight_doors_puertas_estancas = db.Column(db.String(255))

    # 9. EQUIPAMIENTO (MÁSTILES, ANCLAS, BOTES)
    masts_no_numero_mastiles = db.Column(db.String(255))
    rigging_type_tipo_aparejo = db.Column(db.String(255))
    sails_velas = db.Column(db.String(255))
    boats_no_numero_botes = db.Column(db.String(255))
    anchors_no_numero_anclas = db.Column(db.String(255))
    anchors_weight_peso_anclas = db.Column(db.String(255))
    cables_length_longitud_cadenas = db.Column(db.String(255))
    pumps_no_numero_bombas = db.Column(db.String(255))

    # 10. MÁQUINAS Y CALDERAS
    engine_type_tipo_maquina = db.Column(db.String(255))
    engine_hp_caballos_maquina = db.Column(db.String(255))
    boilers_no_numero_calderas = db.Column(db.String(255))
    boilers_pressure_presion_calderas = db.Column(db.String(255))
    boilers_material_material_calderas = db.Column(db.String(255))
    propeller_type_tipo_helice = db.Column(db.String(255))

    # 11. OBSERVACIONES E INSPECCIÓN
    general_remarks_observaciones_generales = db.Column(db.Text)
    class_assigned_clase_asignada = db.Column(db.String(255))
    date_of_class_fecha_clase = db.Column(db.String(255))
    surveyor_signature_firma_inspector = db.Column(db.String(255))

    ultima_actualizacion = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SirioFicha(db.Model):
    """
    Ficha técnica exhaustiva del S.S. Sirio basada en el Lloyd's Register Survey Nº 6147 (1883).
    Los 150+ campos se agrupan en 6 columnas JSON para mantener la BD compacta.
    """
    __tablename__ = 'sirio_ficha'
    id = db.Column(db.Integer, primary_key=True)
    proyecto_id = db.Column(db.Integer, db.ForeignKey("proyectos.id"), nullable=True)

    # Grupo 1: Encabezado, Tonelaje, Dimensiones
    datos_generales = db.Column(db.JSON)

    # Grupo 2: Quilla, Roda, Cuadernas, Varengas, Baos
    datos_estructura = db.Column(db.JSON)

    # Grupo 3: Sobrequillas, Planchaje, Cubiertas
    datos_planchaje = db.Column(db.JSON)

    # Grupo 4: Timón, Mamparos, Fijaciones/Remaches
    datos_fijaciones = db.Column(db.JSON)

    # Grupo 5: Mano de Obra, Mástiles, Equipamiento
    datos_equipamiento = db.Column(db.JSON)

    # Grupo 6: Escotillas, Inspecciones, Cierre
    datos_inspecciones = db.Column(db.JSON)

    ultima_actualizacion = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SirioPuntoInteractivo(db.Model):
    __tablename__ = 'sirio_puntos_interactivos'
    id = db.Column(db.Integer, primary_key=True)
    proyecto_id = db.Column(db.Integer, db.ForeignKey("proyectos.id"), nullable=True)
    nombre = db.Column(db.String(255), nullable=False)
    categoria = db.Column(db.String(100))
    descripcion = db.Column(db.Text)
    x = db.Column(db.Float, nullable=True)
    y = db.Column(db.Float, nullable=True)
    coordenadas = db.Column(db.JSON, nullable=True) # Lista de puntos [[y1, x1], [y2, x2], ...]
    icono = db.Column(db.String(50), default="fa-circle-info")


class MotoresFicha(db.Model):
    """
    Ficha técnica de los motores del S.S. Sirio basada en el Lloyd's Report on Machinery
    Survey Nº 6147 (1883). Fabricante: R. Napier & Sons, Glasgow.
    """
    __tablename__ = 'motores_ficha_sirio'
    id = db.Column(db.Integer, primary_key=True)
    proyecto_id = db.Column(db.Integer, db.ForeignKey("proyectos.id"), nullable=True)

    # I. ENCABEZADO DEL INFORME
    motor_survey_no = db.Column(db.String(255))
    motor_survey_held_at = db.Column(db.String(255))
    motor_date_first_survey = db.Column(db.String(255))
    motor_last_survey = db.Column(db.String(255))
    motor_vessel_name = db.Column(db.String(255))
    motor_master = db.Column(db.String(255))
    motor_built_at = db.Column(db.String(255))
    motor_when_built = db.Column(db.String(255))
    motor_engineers_by = db.Column(db.String(255))
    motor_boilers_by = db.Column(db.String(255))
    motor_registered_horse_power = db.Column(db.String(255))
    motor_owners = db.Column(db.String(255))
    motor_port = db.Column(db.String(255))

    # II. MOTORES PRINCIPALES
    engine_type_tipo_motor = db.Column(db.String(255))
    engine_cylinder_diameter_diametro_cilindro = db.Column(db.String(255))
    engine_stroke_carrera = db.Column(db.String(255))
    engine_revolutions_revoluciones = db.Column(db.String(255))
    engine_cutoff_punto_corte = db.Column(db.String(255))
    engine_high_pressure_alta_presion = db.Column(db.String(255))
    engine_low_pressure_baja_presion = db.Column(db.String(255))
    engine_crankshaft_eje_cigüenal = db.Column(db.String(255))
    engine_crankpin_munequilla = db.Column(db.String(255))
    engine_journals_cojinetes = db.Column(db.String(255))
    engine_screw_shaft_eje_helice = db.Column(db.String(255))
    engine_pitch_of_screw_paso_helice = db.Column(db.String(255))
    engine_blades_palas = db.Column(db.String(255))
    engine_feathering_palas_articuladas = db.Column(db.String(255))

    # III. BOMBAS
    pump_feed_numero_alimentacion = db.Column(db.String(255))
    pump_feed_diameter_diametro = db.Column(db.String(255))
    pump_feed_stroke_carrera = db.Column(db.String(255))
    pump_bilge_numero_achique = db.Column(db.String(255))
    pump_bilge_diameter_diametro = db.Column(db.String(255))
    pump_separate_overhaul = db.Column(db.String(255))
    pump_bilge_from = db.Column(db.String(255))
    pump_donkey_engine = db.Column(db.String(255))
    pump_circulating_no = db.Column(db.String(255))
    pump_circulating_type = db.Column(db.String(255))

    # IV. SISTEMA DE VAPOR
    steam_pumps_worked_bombas_accionadas = db.Column(db.String(255))
    steam_bilge_injections = db.Column(db.String(255))
    steam_oil_connections = db.Column(db.String(255))
    steam_discharge_pipes = db.Column(db.String(255))
    steam_discharge_valves = db.Column(db.String(255))
    steam_blue_off_cocks = db.Column(db.String(255))
    steam_cargo_steam_pipes = db.Column(db.String(255))
    steam_protected_from = db.Column(db.String(255))
    steam_oil_pipes_connected = db.Column(db.String(255))
    steam_pipes_cocks_valves = db.Column(db.String(255))
    steam_store_tube_propeller = db.Column(db.String(255))
    steam_screw_shaft_watertight = db.Column(db.String(255))
    steam_working_platform = db.Column(db.String(255))

    # V. CALDERAS PRINCIPALES
    boiler_no_numero = db.Column(db.String(255))
    boiler_description_descripcion = db.Column(db.String(512))
    boiler_working_pressure_presion_trabajo = db.Column(db.String(255))
    boiler_hydraulic_test_prueba_hidraulica = db.Column(db.String(255))
    boiler_date_last_test_fecha_prueba = db.Column(db.String(255))
    boiler_superheating_sobrecalentamiento = db.Column(db.String(255))
    boiler_worked_separately = db.Column(db.String(255))
    boiler_superheater_separately = db.Column(db.String(255))
    boiler_grate_surface_area = db.Column(db.String(255))
    boiler_each_boiler_grate = db.Column(db.String(255))
    boiler_safety_valves_description = db.Column(db.String(255))
    boiler_safety_valves_no = db.Column(db.String(255))
    boiler_safety_valves_area = db.Column(db.String(255))
    boiler_safety_valves_with_easing_gear = db.Column(db.String(255))

    # VI. CONSTRUCCIÓN DE CALDERAS
    boiler_shell_distance_distancia = db.Column(db.String(255))
    boiler_shell_diameter_diametro = db.Column(db.String(255))
    boiler_shell_length_longitud = db.Column(db.String(255))
    boiler_riveting_description = db.Column(db.String(512))
    boiler_shell_thickness_espesor_virola = db.Column(db.String(255))
    boiler_shell_riveted_pitch = db.Column(db.String(255))
    boiler_plates_thickness = db.Column(db.String(255))
    boiler_percentage_strength = db.Column(db.String(255))
    boiler_working_pressure_by_rules = db.Column(db.String(255))
    boiler_rings_compressing = db.Column(db.String(255))
    boiler_manhole_size = db.Column(db.String(255))
    boiler_furnaces_no = db.Column(db.String(255))
    boiler_furnaces_outside_diameter = db.Column(db.String(255))

    # VII. TUBOS Y COLECTORES
    tubes_diameter_diametro = db.Column(db.String(255))
    tubes_pitch_paso = db.Column(db.String(255))
    tubes_plate_thickness_front = db.Column(db.String(255))
    tubes_plate_thickness_back = db.Column(db.String(255))
    tubes_water_spaces = db.Column(db.String(255))
    tubes_superheater_steam_chest = db.Column(db.String(255))
    combustion_chamber_stays_tirantes = db.Column(db.String(255))
    stays_in_each_furnace = db.Column(db.String(255))
    stays_diameter_diametro = db.Column(db.String(255))
    stays_length_longitud = db.Column(db.String(255))

    # VIII. HOGAR (FURNACE)
    furnace_length_longitud = db.Column(db.String(255))
    furnace_thickness_espesor = db.Column(db.String(255))
    furnace_pitch_of_rings = db.Column(db.String(255))
    furnace_description_corrugado = db.Column(db.String(255))
    furnace_working_pressure_by_rules = db.Column(db.String(255))
    furnace_working_pressure_shell_by_rules = db.Column(db.String(255))

    # IX. PLACAS FRONTALES Y TRASERAS
    plate_stays_worked_by = db.Column(db.String(255))
    plate_combustion_chamber_thickness = db.Column(db.String(255))
    plate_front_thickness = db.Column(db.String(255))
    plate_back_thickness = db.Column(db.String(255))
    plate_pitch_of_stays = db.Column(db.String(255))
    plate_greatest_pitch_between = db.Column(db.String(255))
    plate_size_stays_at_smallest_part = db.Column(db.String(255))
    plate_working_pressure_by_rules = db.Column(db.String(255))
    plate_stays_are_secured_by = db.Column(db.String(255))

    # X. CALDERA AUXILIAR (DONKEY BOILER)
    donkey_description = db.Column(db.String(512))
    donkey_made_at = db.Column(db.String(255))
    donkey_by_whom = db.Column(db.String(255))
    donkey_when_made = db.Column(db.String(255))
    donkey_working_pressure = db.Column(db.String(255))
    donkey_hydraulic_test = db.Column(db.String(255))
    donkey_certificate_no = db.Column(db.String(255))
    donkey_grate_area = db.Column(db.String(255))
    donkey_safety_valves_no = db.Column(db.String(255))
    donkey_diameter = db.Column(db.String(255))
    donkey_length = db.Column(db.String(255))
    donkey_riveting_description = db.Column(db.String(512))
    donkey_rivet_holes = db.Column(db.String(255))
    donkey_pitch_of_rivets = db.Column(db.String(255))
    donkey_lap_plating = db.Column(db.String(255))
    donkey_furnace_length = db.Column(db.String(255))
    donkey_plates_thickness = db.Column(db.String(255))
    donkey_furnace_description = db.Column(db.String(255))
    donkey_working_pressure_furnace = db.Column(db.String(255))
    donkey_working_pressure_shell = db.Column(db.String(255))

    # XI. REMARQUES GENERALES
    motor_manufacturer_firma = db.Column(db.String(255))
    motor_general_remarks = db.Column(db.Text)
    motor_class_assigned = db.Column(db.String(255))
    motor_certificate_no = db.Column(db.String(255))
    motor_date_certificate = db.Column(db.String(255))
    motor_entry_fee = db.Column(db.String(255))
    motor_surveyor_signature = db.Column(db.String(255))
    motor_surveyor_district = db.Column(db.String(255))

    ultima_actualizacion = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<MotoresFicha S.S. Sirio - Survey {self.motor_survey_no}>"


# ============================================================================
# BLOG — Entradas públicas del proyecto HesiOX
# ============================================================================

class BlogPost(db.Model):
    """Modelo para entradas del blog de HesiOX"""
    __tablename__ = "blog_posts"

    id = db.Column(db.Integer, primary_key=True)

    # Identificador único legible (URL-friendly)
    slug = db.Column(db.String(255), unique=True, nullable=False, index=True)

    titulo = db.Column(db.String(500), nullable=False)
    resumen = db.Column(db.Text, nullable=True)       # Extracto corto para las cards
    contenido = db.Column(db.Text, nullable=False, default='')  # HTML enriquecido

    # Imagen de portada: ruta relativa a /static/ o URL externa
    imagen_portada = db.Column(db.String(500), nullable=True)

    # Categorías y etiquetas
    categoria = db.Column(db.String(100), nullable=True, default='General')
    etiquetas = db.Column(db.Text, nullable=True)     # CSV: "sirio, historia, nautica"

    # Estado de publicación
    publicado = db.Column(db.Boolean, default=False, nullable=False)
    destacado = db.Column(db.Boolean, default=False, nullable=False)

    # Autoría
    autor_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    autor = db.relationship("Usuario", backref=db.backref("blog_posts", lazy=True))

    # Timestamps
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)
    publicado_en = db.Column(db.DateTime, nullable=True)
    modificado_en = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Métricas de engagement
    vistas = db.Column(db.Integer, default=0, nullable=False)
    notificado = db.Column(db.Boolean, default=False, nullable=False)

    __table_args__ = (
        db.Index('idx_blog_publicado', 'publicado'),
        db.Index('idx_blog_autor', 'autor_id'),
        db.Index('idx_blog_categoria', 'categoria'),
        db.Index('idx_blog_creado', 'creado_en'),
    )

    def get_resumen_corto(self, length=200):
        """Genera un resumen limpio (sin HTML) para vistas previas."""
        if self.resumen:
            return self.resumen[:length] + ('...' if len(self.resumen) > length else '')
        
        # Si no hay resumen, limpiar HTML del contenido
        import re
        clean_text = re.sub(r'<[^>]*?>', '', self.contenido or '')
        clean_text = clean_text.replace('&nbsp;', ' ').strip()
        return clean_text[:length] + ('...' if len(clean_text) > length else '')

    def get_etiquetas_list(self):
        """Devuelve la lista de etiquetas como array limpio."""
        if not self.etiquetas:
            return []
        return [t.strip() for t in self.etiquetas.split(',') if t.strip()]

    def get_resumen_corto(self, max_chars=200):
        """Devuelve el resumen o los primeros caracteres del contenido (sin HTML)."""
        import re
        if self.resumen:
            return self.resumen
        texto = re.sub(r'<[^>]+>', '', self.contenido or '')
        return texto[:max_chars] + ('…' if len(texto) > max_chars else '')

    def __repr__(self):
        return f"<BlogPost {self.id}: {self.titulo[:40]}>"


class BlogSubscription(db.Model):
    """Modelo para suscriptores a las publicaciones del blog"""
    __tablename__ = "blog_subscriptions"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    activo = db.Column(db.Boolean, default=True, nullable=False)
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<BlogSubscription {self.email}>"

# ============================================================================
# 18. MENSAJES DE CONTACTO
# ============================================================================

class MensajeContacto(db.Model):
    """Modelo para registrar mensajes enviados a través del formulario de contacto."""
    __tablename__ = "mensajes_contacto"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    asunto = db.Column(db.String(255), nullable=False)
    contenido = db.Column(db.Text, nullable=False)
    
    # Metadata
    fecha_envio = db.Column(db.DateTime, default=datetime.utcnow)
    leido = db.Column(db.Boolean, default=False)
    respondido = db.Column(db.Boolean, default=False)
    ip_address = db.Column(db.String(50), nullable=True)

    def __repr__(self):
        return f"<MensajeContacto de {self.email}: {self.asunto}>"

    def to_dict(self):
        return {
            'id': self.id,
            'nombre': self.nombre,
            'email': self.email,
            'asunto': self.asunto,
            'contenido': self.contenido,
            'fecha_envio': self.fecha_envio.isoformat() if self.fecha_envio else None,
            'leido': self.leido,
            'respondido': self.respondido
        }
