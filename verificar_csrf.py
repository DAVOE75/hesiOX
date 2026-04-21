"""
Script de diagnóstico para verificar CSRF en hesiOX
Ejecutar: python verificar_csrf.py
"""

def verificar_csrf():
    print("=" * 60)
    print("🔍 DIAGNÓSTICO DE CSRF - hesiOX")
    print("=" * 60)
    print()
    
    # 1. Verificar que Flask-WTF está instalado
    print("1. Verificando Flask-WTF...")
    try:
        import flask_wtf
        print(f"   ✅ Flask-WTF instalado (versión: {flask_wtf.__version__})")
    except ImportError:
        print("   ❌ Flask-WTF NO está instalado")
        print("   → Ejecuta: pip install Flask-WTF")
        return
    
    # 2. Verificar templates con CSRF token
    print("\n2. Verificando templates...")
    import os
    templates_dir = os.path.join(os.path.dirname(__file__), 'templates')
    
    templates_criticos = [
        'login.html',
        'registro.html',
        'new.html',
        'editar.html',
        'nueva_publicacion.html',
        'nuevo_proyecto.html'
    ]
    
    for template in templates_criticos:
        template_path = os.path.join(templates_dir, template)
        if os.path.exists(template_path):
            with open(template_path, 'r', encoding='utf-8') as f:
                content = f.read()
                if '{{ csrf_token() }}' in content or '{{csrf_token()}}' in content:
                    print(f"   ✅ {template} - Token CSRF presente")
                else:
                    print(f"   ❌ {template} - Token CSRF FALTA")
        else:
            print(f"   ⚠️  {template} - Archivo no encontrado")
    
    # 3. Verificar configuración en app.py
    print("\n3. Verificando configuración en app.py...")
    app_path = os.path.join(os.path.dirname(__file__), 'app.py')
    with open(app_path, 'r', encoding='utf-8') as f:
        app_content = f.read()
        
        if 'CSRFProtect' in app_content:
            print("   ✅ CSRFProtect importado")
        else:
            print("   ❌ CSRFProtect NO importado")
        
        if 'csrf = CSRFProtect(app)' in app_content:
            print("   ✅ CSRFProtect inicializado")
        else:
            print("   ❌ CSRFProtect NO inicializado")
        
        if 'WTF_CSRF_ENABLED' in app_content:
            print("   ✅ WTF_CSRF_ENABLED configurado")
        else:
            print("   ⚠️  WTF_CSRF_ENABLED no configurado (usará default)")
    
    # 4. Instrucciones para el usuario
    print("\n" + "=" * 60)
    print("📋 INSTRUCCIONES PARA SOLUCIONAR EL ERROR")
    print("=" * 60)
    print()
    print("Si ves el error 'The CSRF token is missing', haz lo siguiente:")
    print()
    print("1. CIERRA COMPLETAMENTE EL NAVEGADOR (todas las pestañas)")
    print("2. Abre el navegador de nuevo")
    print("3. Ve a: http://127.0.0.1:5000/login")
    print("4. Presiona Ctrl + Shift + R (hard refresh)")
    print("5. Intenta hacer login")
    print()
    print("Alternativa:")
    print("- Abre el navegador en modo incógnito/privado")
    print("- Ve a: http://127.0.0.1:5000/login")
    print("- Intenta hacer login")
    print()
    print("Para verificar que el token está presente:")
    print("1. En la página de login, presiona F12 (abrir DevTools)")
    print("2. Ve a la pestaña 'Elements' o 'Inspector'")
    print("3. Busca en el código HTML: <input name=\"csrf_token\"")
    print("4. Debería aparecer un campo oculto con el token")
    print()
    print("=" * 60)


if __name__ == "__main__":
    verificar_csrf()
