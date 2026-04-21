
import os

filepath = 'c:/Users/David/Desktop/app_bibliografia/app.py'
search_terms = ['/api/map-data', '/api/map-distribution', '/api/valores_filtrados']

try:
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        for i, line in enumerate(lines):
            for term in search_terms:
                if term in line:
                    print(f"Found '{term}' at line {i+1}: {line.strip()}")
except Exception as e:
    print(f"Error: {e}")
