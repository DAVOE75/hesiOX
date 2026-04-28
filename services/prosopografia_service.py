import json
import sys
from models import db, EntidadFiltro, AutorBio
from services.ai_service import AIService
from utils import get_nlp

class ProsopografiaService:
    def __init__(self, proyecto_id, user=None):
        self.proyecto_id = proyecto_id
        self.user = user
        self.nlp = get_nlp()
        self.ai_service = AIService(provider='gemini', model='flash', user=user)

    def analizar_completo(self, texto, context=None):
        """
        Análisis híbrido: SpaCy + Filtros Globales + IA (LLM)
        """
        # 1. Análisis Base (SpaCy)
        entidades_raw = self._analizar_spacy(texto)
        
        # 2. Aplicar Filtros Globales (Diccionario que aprende)
        entidades_filtradas = self._aplicar_filtros(entidades_raw)
        
        # 3. Enriquecimiento con IA (PROSOGRAF-IA)
        # Solo si el texto es lo suficientemente largo para valer la pena
        if len(texto) > 100:
            entidades_finales = self._enriquecer_con_ia(texto, entidades_filtradas, context)
        else:
            entidades_finales = entidades_filtradas
            
        # 4. Auto-vinculación con AutorBio
        self._auto_vincular(entidades_finales)
        
        return entidades_finales

    def _analizar_spacy(self, texto):
        if not self.nlp:
            return []
        doc = self.nlp(texto)
        entidades = []
        for ent in doc.ents:
            # Solo nos interesan Personas, Lugares y Organizaciones para prosopografía
            if ent.label_ in ['PER', 'LOC', 'ORG', 'MISC']:
                entidades.append({
                    "texto": ent.text,
                    "label": ent.label_,
                    "start": ent.start_char,
                    "end": ent.end_char,
                    "fuente": "spacy"
                })
        return entidades

    def _aplicar_filtros(self, entidades):
        filtros = EntidadFiltro.query.filter_by(proyecto_id=self.proyecto_id).all()
        blacklist = {(f.texto, f.label): f for f in filtros if f.accion == 'ignorar'}
        correcciones = {(f.texto, f.label): f for f in filtros if f.accion == 'corregir'}
        vinculos = {(f.texto, f.label): f for f in filtros if f.accion == 'vincular_siempre'}
        
        resultado = []
        for ent in entidades:
            key = (ent['texto'], ent['label'])
            
            # Si está en blacklist, descartar
            if key in blacklist:
                continue
                
            # Si tiene corrección, aplicar
            if key in correcciones:
                ent['texto'] = correcciones[key].valor_corregido
                
            # Si tiene vínculo permanente, aplicar
            if key in vinculos:
                ent['autor_bio_id'] = vinculos[key].autor_bio_id
                
            resultado.append(ent)
        return resultado

    def _enriquecer_con_ia(self, texto, entidades_existentes, context=None):
        """
        Usa LLM para descubrir entidades que SpaCy omitió y desambiguar.
        """
        prompt = f"""
        Actúa como un experto en análisis prosopográfico e histórico.
        Tu tarea es extraer personas, lugares y organizaciones de un texto de prensa histórica.
        
        HEMOS DETECTADO ESTAS ENTIDADES PREVIAMENTE (SpaCy):
        {json.dumps([e['texto'] for e in entidades_existentes], ensure_ascii=False)}
        
        OBJETIVOS:
        1. Identifica PERSONAS (PER) que faltan, especialmente nombres completos o cargos.
        2. Identifica LUGARES (LOC) y ORGANIZACIONES (ORG).
        3. DESAMBIGUA: Si 'Mar' es una persona o un lugar, indícalo.
        4. NORMALIZA: Si dice 'D. Benito Pérez', el nombre normalizado es 'Benito Pérez Galdós' si el contexto lo confirma.
        
        CONTEXTO ADICIONAL: {json.dumps(context or {}, ensure_ascii=False)}
        TEXTO: \"\"\"{texto[:15000]}\"\"\"
        
        Responde ÚNICAMENTE con un JSON:
        {{
            "entidades": [
                {{
                    "texto": "nombre original en texto",
                    "normalizado": "nombre completo/correcto",
                    "label": "PER|LOC|ORG",
                    "descripcion": "breve contexto de quién es o qué es",
                    "confianza": 0.0-1.0
                }}
            ]
        }}
        """
        try:
            raw_res = self.ai_service.generate_content(prompt, temperature=0.1)
            data = self.ai_service._extract_json_from_text(raw_res)
            
            nuevas_entidades = data.get('entidades', [])
            
            # Combinar manteniendo unicidad por texto normalizado
            combinadas = {e['texto']: e for e in entidades_existentes}
            
            for ne in nuevas_entidades:
                txt = ne['texto']
                if txt in combinadas:
                    # Enriquecer la existente
                    combinadas[txt].update({
                        "texto_normalizado": ne.get('normalizado'),
                        "descripcion": ne.get('descripcion'),
                        "label": ne.get('label', combinadas[txt]['label']),
                        "fuente": "hibrido"
                    })
                else:
                    # Añadir nueva
                    combinadas[txt] = {
                        "texto": txt,
                        "texto_normalizado": ne.get('normalizado'),
                        "label": ne.get('label', 'PER'),
                        "descripcion": ne.get('descripcion'),
                        "fuente": "ia"
                    }
            
            return list(combinadas.values())
        except Exception as e:
            print(f"[ProsopografiaService] Error en enriquecimiento IA: {e}", file=sys.stderr)
            return entidades_existentes

    def _auto_vincular(self, entidades):
        """
        Busca coincidencias en la tabla AutorBio para vinculación automática.
        """
        for ent in entidades:
            if ent.get('autor_bio_id'):
                continue # Ya vinculado por filtro
            
            search_name = ent.get('texto_normalizado') or ent['texto']
            if ent['label'] != 'PER':
                continue
                
            # Búsqueda simple por nombre/apellido
            # En un futuro usar embeddings para búsqueda semántica
            autor = AutorBio.query.filter(
                (AutorBio.nombre + " " + AutorBio.apellido).ilike(f"%{search_name}%") |
                (AutorBio.seudonimo.ilike(f"%{search_name}%"))
            ).first()
            
            if autor:
                ent['autor_bio_id'] = autor.id
                ent['auto_vinculado'] = True

    def aprender_ignorada(self, texto, label):
        """
        Añade una entidad al diccionario de 'ignoradas' para que no vuelva a aparecer.
        """
        try:
            filtro = EntidadFiltro(
                proyecto_id=self.proyecto_id,
                texto=texto,
                label=label,
                accion='ignorar'
            )
            db.session.add(filtro)
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            print(f"[ProsopografiaService] Error aprendiendo ignorada: {e}")
            return False
