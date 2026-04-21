#!/usr/bin/env python3
"""Debug script para verificar el conteo de noticias"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import Prensa, Proyecto
from sqlalchemy import func

with app.app_context():
    # Obtener primer proyecto
    proyecto = Proyecto.query.first()
    print(f"📂 Proyecto: {proyecto.nombre} (ID: {proyecto.id})")
    
    # Contar noticias del proyecto
    total = db.session.query(func.count(Prensa.id)).filter(
        Prensa.proyecto_id == proyecto.id,
        Prensa.incluido == True
    ).scalar()
    
    print(f"   Total noticias incluidas: {total}")
    
    # Contar con embeddings
    con_embeddings = db.session.query(func.count(Prensa.id)).filter(
        Prensa.proyecto_id == proyecto.id,
        Prensa.incluido == True,
        Prensa.embedding_vector.isnot(None)
    ).scalar()
    
    print(f"   Con embeddings: {con_embeddings}")
    
    # Contar sin embeddings
    sin_embeddings = db.session.query(func.count(Prensa.id)).filter(
        Prensa.proyecto_id == proyecto.id,
        Prensa.incluido == True,
        Prensa.embedding_vector.is_(None)
    ).scalar()
    
    print(f"   Sin embeddings: {sin_embeddings}")
