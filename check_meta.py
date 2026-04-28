import sys
import os
sys.path.append('/opt/hesiox')
from app import app
from models import MetadataOption, db

with app.app_context():
    for cat in ['tipo_recurso', 'tipo_publicacion', 'frecuencia']:
        opts = MetadataOption.query.filter_by(categoria=cat).all()
        print(f"Category: {cat}, Count: {len(opts)}")
        for opt in opts[:3]:
            print(f"  - {opt.etiqueta} ({opt.valor})")
