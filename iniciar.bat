@echo off
REM =========================================================
REM Iniciar Proyecto S.S. Sirio
REM =========================================================

echo.
echo ========================================
echo   PROYECTO S.S. SIRIO
echo   Plataforma de Analisis de Prensa
echo ========================================
echo.

REM Verificar si existe el entorno virtual
if not exist "venv\Scripts\activate.bat" (
    echo [ERROR] No se encontro el entorno virtual.
    echo Por favor ejecuta: python -m venv venv
    pause
    exit /b 1
)

REM Activar entorno virtual
echo [1/3] Activando entorno virtual...
call venv\Scripts\activate.bat

REM Verificar archivo .env
if not exist ".env" (
    echo [ADVERTENCIA] No se encontro archivo .env
    echo Copiando .env.example...
    copy .env.example .env
    echo.
    echo [IMPORTANTE] Edita el archivo .env con tus credenciales de PostgreSQL
    pause
)

REM Instalar/actualizar dependencias
echo [2/3] Verificando dependencias...
pip install -q -r requirements.txt

REM Iniciar aplicacion
echo [3/3] Iniciando aplicacion Flask...
echo.
echo ========================================
echo   Accede a: http://127.0.0.1:5000
echo   Presiona Ctrl+C para detener
echo ========================================
echo.

python app.py

pause
