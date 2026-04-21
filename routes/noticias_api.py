from flask import Blueprint, request, jsonify
from extensions import db
from models import Prensa

noticias_api_bp = Blueprint('noticias_api', __name__, url_prefix='')

# @noticias_api_bp.route('/api/valores_filtrados', methods=['GET'])
# def valores_filtrados():
#     # Recoge los filtros de la query
#     publicacion = request.args.get('publicacion')
#     autor = request.args.get('autor')
#     ciudad = request.args.get('ciudad')
#     fecha_original = request.args.get('fecha_original')
#     temas = request.args.get('temas')
#     incluido = request.args.get('incluido')
#     busqueda = request.args.get('busqueda')
#     page = int(request.args.get('page', 1))
# 
#     query = Prensa.query
#     if publicacion:
#         query = query.filter(Prensa.publicacion.ilike(f"%{publicacion}%"))
#     if autor:
#         query = query.filter(Prensa.autor.ilike(f"%{autor}%"))
#     if ciudad:
#         query = query.filter(Prensa.ciudad.ilike(f"%{ciudad}%"))
#     if fecha_original:
#         query = query.filter(Prensa.fecha_original.ilike(f"%{fecha_original}%"))
#     if temas:
#         query = query.filter(Prensa.temas.ilike(f"%{temas}%"))
#     if incluido == "si":
#         query = query.filter(Prensa.incluido.is_(True))
#     elif incluido == "no":
#         query = query.filter(Prensa.incluido.is_(False))
#     if busqueda:
#         query = query.filter(Prensa.titulo.ilike(f"%{busqueda}%"))
#     # Paginación simple
#     por_pagina = 25
#     resultados = query.offset((page - 1) * por_pagina).limit(por_pagina).all()
#     # Devuelve solo los campos relevantes
#     data = [
#         {
#             'id': r.id,
#             'titulo': r.titulo,
#             'publicacion': r.publicacion,
#             'autor': r.autor,
#             'ciudad': r.ciudad,
#             'fecha_original': r.fecha_original,
#             'temas': r.temas,
#             'incluido': r.incluido,
#         }
#         for r in resultados
#     ]
#     return jsonify(data)
# 
# @noticias_api_bp.route('/filtrar', methods=['GET'])
# def filtrar():
#     # Reutiliza la lógica de valores_filtrados
#     # return valores_filtrados()
#     return jsonify([]) # Deshabilitado por conflicto con noticias.py
