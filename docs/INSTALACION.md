# 📦 Guía de Instalación - hesiOX v1.4.5

**Sistema de Gestión de Referencias Bibliográficas para Humanidades Digitales**

Esta guía te llevará paso a paso por la instalación completa de hesiOX en tu sistema local.

---

## 📋 Requisitos Previos

### Software Necesario

Antes de comenzar, asegúrate de tener instalado:

- **Python 3.10 o superior** ([Descargar Python](https://www.python.org/downloads/))
- **PostgreSQL 15 o superior** ([Descargar PostgreSQL](https://www.postgresql.org/download/))
- **Git** (opcional, para clonar el repositorio) ([Descargar Git](https://git-scm.com/downloads))
- **Editor de texto** (recomendado: VS Code, Sublime Text, Notepad++)

### Verificar Instalaciones

Abre una terminal (CMD, PowerShell o Bash) y verifica las versiones:

```bash
python --version
# Debe mostrar: Python 3.10.x o superior

psql --version
# Debe mostrar: psql (PostgreSQL) 15.x o superior

git --version
# Debe mostrar: git version 2.x.x
```

---

## 🚀 Instalación Paso a Paso

### 1️⃣ Clonar el Repositorio

**Opción A - Con Git**:
```bash
cd C:\Users\TuUsuario\Desktop
git clone https://github.com/tuusuario/app_bibliografia.git
cd app_bibliografia
```

**Opción B - Sin Git (descarga manual)**:
1. Ve a la página del repositorio
2. Haz clic en **Code** → **Download ZIP**
3. Descomprime el archivo en `C:\Users\TuUsuario\Desktop\app_bibliografia`
4. Abre CMD y navega a la carpeta:
   ```bash
   cd C:\Users\TuUsuario\Desktop\app_bibliografia
   ```

---

### 2️⃣ Crear Entorno Virtual

Crea un entorno virtual de Python para aislar las dependencias:

```bash
python -m venv venv
```

**Activar el entorno virtual**:

**En Windows (CMD)**:
```bash
venv\Scripts\activate
```

**En Windows (PowerShell)**:
```bash
venv\Scripts\Activate.ps1
```

**En Linux/Mac**:
```bash
source venv/bin/activate
```

Deberías ver `(venv)` al inicio de tu línea de comandos.

---

### 3️⃣ Instalar Dependencias

Con el entorno virtual activado, instala todas las librerías necesarias:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

Esto instalará:
- **Backend**: Flask 3.0, SQLAlchemy 2.0, psycopg2-binary
- **NLP**: spaCy 3.8, scikit-learn 1.3
- **Visualización**: matplotlib 3.7, wordcloud 1.9, pandas 2.0
- **Utilidades**: Werkzeug, python-dotenv

**Tiempo estimado**: 2-5 minutos (depende de tu conexión).

---

### 4️⃣ Instalar Modelo de Lenguaje spaCy

⚠️ **Paso crítico**: El análisis NLP requiere el modelo en español.

```bash
python -m spacy download es_core_news_md
```

**Verificar instalación**:
```bash
python -c "import spacy; nlp = spacy.load('es_core_news_md'); print('✅ spaCy OK')"
```

Debe mostrar: `✅ spaCy OK`

**Si falla**:
- Asegúrate de que el entorno virtual esté activado
- Verifica tu conexión a internet (descarga ~40 MB)
- Prueba con `python -m spacy download es_core_news_sm` (modelo más pequeño)

---

### 5️⃣ Configurar PostgreSQL

#### Crear Base de Datos

1. Abre **pgAdmin** o **psql** (terminal de PostgreSQL)

**Con pgAdmin**:
- Haz clic derecho en **Databases** → **Create** → **Database**
- Nombre: `bibliografia_db`
- Owner: `postgres` (o tu usuario)
- Haz clic en **Save**

**Con psql** (CMD):
```bash
psql -U postgres
```
```sql
CREATE DATABASE bibliografia_db;
\q
```

#### Crear Usuario (opcional pero recomendado)

```sql
CREATE USER bibliografia_user WITH PASSWORD 'tu_password_seguro';
GRANT ALL PRIVILEGES ON DATABASE bibliografia_db TO bibliografia_user;
```

---

### 6️⃣ Configurar Variables de Entorno

Crea un archivo `.env` en la raíz del proyecto (`C:\Users\TuUsuario\Desktop\app_bibliografia\.env`):

**Con CMD**:
```bash
type nul > .env
notepad .env
```

**Con PowerShell**:
```bash
New-Item -Path .env -ItemType File
notepad .env
```

**Pega este contenido en `.env`**:

```env
# Configuración de Base de Datos
DATABASE_URL=postgresql://postgres:tu_password@localhost/bibliografia_db

# Clave Secreta (cambia esto por una cadena aleatoria)
SECRET_KEY=tu_clave_secreta_super_aleatoria_cambiame_123456

# Configuración de Flask
FLASK_APP=app.py
FLASK_ENV=development

# Puerto del servidor (opcional)
PORT=5000
```

⚠️ **Importante**:
- Reemplaza `tu_password` con la contraseña de tu usuario PostgreSQL
- Cambia `SECRET_KEY` por una cadena aleatoria única
- Si usaste un usuario personalizado: `postgresql://bibliografia_user:tu_password@localhost/bibliografia_db`

**Generar SECRET_KEY segura**:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

---

### 7️⃣ Inicializar la Base de Datos

Con el entorno virtual activado y las variables configuradas:

```bash
python app.py
```

**Primera ejecución**:
- Flask detectará que la base de datos está vacía
- Creará automáticamente todas las tablas necesarias:
  - `usuarios`
  - `proyectos`
  - `articulos_prensa`
  - `publicaciones_academicas`
  - `hemerotecas`
  - `articulos_cientificos`
  - Y más...

Verás en la consola:
```
 * Running on http://127.0.0.1:5000
Press CTRL+C to quit
```

✅ **¡Instalación completa!**

---

## 🌐 Acceder a la Aplicación

1. Abre tu navegador
2. Ve a: [http://localhost:5000](http://localhost:5000)
3. Deberías ver la página de **Login**

### Crear Primera Cuenta

1. Haz clic en **"Registrarse"**
2. Completa:
   - **Nombre de usuario**: tu_usuario
   - **Email**: tu@email.com
   - **Contraseña**: Mínimo 8 caracteres
3. Haz clic en **Registrarse**
4. Inicia sesión con tus credenciales

---

## 🛠️ Comandos Útiles

### Iniciar el Servidor

**Cada vez que quieras usar hesiOX**:

```bash
# 1. Activar entorno virtual
cd C:\Users\TuUsuario\Desktop\app_bibliografia
venv\Scripts\activate

# 2. Ejecutar aplicación
python app.py
```

**Acceder**: [http://localhost:5000](http://localhost:5000)

### Detener el Servidor

- Presiona `Ctrl + C` en la terminal donde está corriendo Flask

### Backup de la Base de Datos

**Con pgAdmin**:
- Haz clic derecho en `bibliografia_db` → **Backup**
- Guarda el archivo `.backup`

**Con pg_dump** (CMD):
```bash
pg_dump -U postgres -d bibliografia_db -f backup_bibliografia.sql
```

### Restaurar Base de Datos

```bash
psql -U postgres -d bibliografia_db -f backup_bibliografia.sql
```

---

## 🔧 Solución de Problemas

### Error: "No module named 'flask'"

**Solución**: El entorno virtual no está activado.
```bash
venv\Scripts\activate
pip install -r requirements.txt
```

### Error: "Could not connect to database"

**Solución**: PostgreSQL no está corriendo o las credenciales son incorrectas.
1. Verifica que PostgreSQL esté iniciado (busca el servicio en Windows)
2. Revisa el archivo `.env` (usuario, contraseña, nombre de BD)

### Error: "Secret key not found"

**Solución**: Falta el archivo `.env` o está mal configurado.
```bash
# Verifica que el archivo existe
dir .env

# Si no existe, créalo con el contenido de la sección 6
```

### Error: "spaCy model not found"

**Solución**: El modelo NLP no está instalado.
```bash
python -m spacy download es_core_news_md
```

### El servidor no arranca en el puerto 5000

**Solución**: Otro programa está usando el puerto.

**Opción 1 - Cambiar puerto en `.env`**:
```env
PORT=5001
```

**Opción 2 - Ejecutar en otro puerto**:
```bash
python app.py --port 5001
```

### Imágenes OCR no se procesan

**Solución**: Tesseract.js corre en el navegador (frontend), no requiere instalación. Si falla:
1. Verifica que JavaScript esté habilitado
2. Prueba con otro navegador (Chrome recomendado)
3. Revisa la consola del navegador (F12 → Console)

---

## 🚀 Próximos Pasos

Una vez instalado y corriendo:

1. **Lee el Manual de Usuario**: `MANUAL_USUARIO.md` para aprender a usar todas las funciones
2. **Crea tu primer proyecto**: Menú **Proyectos** → **Nuevo Proyecto**
3. **Sube tu primera hemeroteca**: Menú **Hemerotecas** → **Nueva Hemeroteca**
4. **Añade artículos**: Menú **Artículos** → **Nuevo Artículo**
5. **Prueba el OCR**: Sube imágenes de periódicos escaneados
6. **Explora análisis NLP**: Menú **Análisis** → **Red de Entidades**

---

## 📚 Documentación Adicional

- **Manual de Usuario**: `MANUAL_USUARIO.md` - Guía completa de todas las funciones
- **Changelog**: `CHANGELOG.md` - Historial de versiones y mejoras
- **README**: `README.md` - Descripción del proyecto y stack técnico
- **Contribuir**: `CONTRIBUTING.md` - Guía para desarrolladores

---

## 🆘 Soporte

Si encuentras problemas:

1. **Revisa la sección de Solución de Problemas** arriba
2. **Lee el archivo `MANUAL_USUARIO.md`** sección "Solución de Problemas"
3. **Abre un issue** en GitHub describiendo el error con capturas de pantalla
4. **Contacta al desarrollador**: [tu@email.com]

---

## 📝 Notas Finales

- **Uso Offline**: hesiOX funciona completamente offline después de instalar las dependencias (Bootstrap 5.3.3 y Choices.js son locales)
- **Backups Regulares**: Recomendamos hacer backup de la base de datos semanalmente
- **Actualizaciones**: Ejecuta `git pull` y `pip install -r requirements.txt` para actualizar
- **Rendimiento**: Con corpus >5000 artículos, considera optimizar PostgreSQL (índices, vacuum)

---

**hesiOX v1.4.5** - Gestión de Referencias Bibliográficas para Humanidades Digitales

Licencia GPL v3 | 2025
