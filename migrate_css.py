import os
import re

files_to_migrate = [
    "admin_panel.html",
    "analisis.html",
    "articulos_lista.html",
    "articulo_colaboradores.html",
    "articulo_editor.html",
    "articulo_figuras.html",
    "bibliografia.html",
    "buscador_semantico.html",
    "cita.html",
    "config_red_v2.html",
    "config_red_v3.html",
    "consistencia.html",
    "editar.html",
    "editar_publicacion.html",
    "estadisticas.html",
    "hemerotecas.html",
    "hemeroteca_form.html",
    "manual_viewer.html",
    "mapa.html",
    "migrar_hemeroteca.html",
    "new.html",
    "nueva_publicacion.html",
    "nuevo_proyecto.html",
    "proyectos.html",
    "publicaciones.html",
    "redes.html",
    "timeline.html"
]

base_dir = r"c:\Users\David\Desktop\app_bibliografia\templates"

for filename in files_to_migrate:
    path = os.path.join(base_dir, filename)
    if not os.path.exists(path):
        print(f"File not found: {filename}")
        continue
        
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
        
    # Check for style-proyecto.css
    if "style-proyecto.css" not in content:
        print(f"Skipping {filename} (no style-proyecto.css found)")
        continue
        
    # Regex to replace the link
    # We look for the link tag. It might be inside a block or standalone.
    # Pattern: <link.*href=.*style-proyecto.css.*>
    
    # We want to replace it with the block.
    # Note: If it's already inside {% block extra_css %}, we might be nesting blocks or leaving empty blocks.
    # Simpler approach: Replace the line containing style-proyecto.css with the new block.
    
    # Check if extra_css block is used around it?
    # Many files have:
    # {% block extra_css %}
    # <link ... style-proyecto.css ...>
    # {% endblock %}
    
    # If we replace the link with a BLOCK, we can't nest blocks in jinja2 (usually).
    # So we should be careful.
    # If the link is inside extra_css, we should probably remove the link from extra_css and ADD the new block AFTER extra_css (or just override main_css).
    
    # Let's simple check:
    # If we find:
    # {% block extra_css %}\s*<link.*style-proyecto.css.*>\s*{% endblock %}
    # We replace the WHOLE thing.
    
    new_block = """{% block main_css %}
<link href="{{ url_for('static', filename='css/app.css') }}" rel="stylesheet">
{% endblock %}"""

    # Strategy 1: strict block replacement
    pattern_block = r"{% block extra_css %}\s*<link[^>]*style-proyecto\.css[^>]*>\s*{% endblock %}"
    
    match_block = re.search(pattern_block, content, re.DOTALL)
    
    if match_block:
        new_content = content.replace(match_block.group(0), new_block)
        print(f"Replaciong block in {filename}")
    else:
        # Strategy 2: Just the link replacement
        # If the link is standalone or inside a complex block
        pattern_link = r"<link[^>]*style-proyecto\.css[^>]*>"
        match_link = re.search(pattern_link, content)
        if match_link:
             # We need to be careful not to put {% block %} inside another {% block %} if it's not allowed (it IS allowed to nest if defining, but here we are overriding from base).
             # Override blocks must be at top level of template (direct child of extends).
             # If the file extends base.html, the blocks must be top level.
             
             # If the link is just floating there, we verify if it is inside a block.
             # This script is simple, so let's just swap it and warn.
             
             print(f"Direct link replacement in {filename}. PLEASE CHECK resulting nesting.")
             new_content = re.sub(pattern_link, new_block, content)
        else:
            print(f"Could not match regex in {filename}")
            continue

    with open(path, "w", encoding="utf-8") as f:
        f.write(new_content)
        
    if "<style>" in new_content:
        print(f"WARNING: {filename} contains <style> tags. Manual check required.")
