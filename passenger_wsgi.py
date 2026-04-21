import sys, os

# Switch to the virtual environment interpreter if not already running
INTERP = "/opt/hesiox/venv/bin/python"
if sys.executable != INTERP:
    os.execl(INTERP, INTERP, *sys.argv)

# Append current directory to path
sys.path.append(os.getcwd())

from app import app as application, inicializar_buscador

# Inicializar el buscador semántico al arrancar la aplicación
# with application.app_context():
#    try:
#        inicializar_buscador()
#    except Exception as e:
#        print(f"[ERROR] No se pudo inicializar el buscador semántico: {e}")
# restart: 2026-03-15T23:10:00