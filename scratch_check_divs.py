import re

with open('/opt/hesiox/templates/new.html', 'r') as f:
    lines = f.readlines()

in_block = False
depth = 0

for i, line in enumerate(lines):
    if '{% block content %}' in line:
        in_block = True
    if '{% endblock %}' in line and in_block:
        in_block = False
        print(f"Endblock at line {i+1}, final depth: {depth}")
        break
    
    if in_block:
        opens = len(re.findall(r'<div[^>]*>', line))
        closes = len(re.findall(r'</div>', line))
        depth += opens - closes
        if depth < 0:
            print(f"Depth went negative at line {i+1}")
            break
