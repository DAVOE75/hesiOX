
from app import app
from extensions import db
from models import SemanticConcept

def seed_sentimental_concepts():
    with app.app_context():
        sentimientos = [
            # Emociones Positivas
            ("Sentimientos y Emociones", "Alegría"),
            ("Sentimientos y Emociones", "Entusiasmo"),
            ("Sentimientos y Emociones", "Esperanza"),
            ("Sentimientos y Emociones", "Gratitud"),
            ("Sentimientos y Emociones", "Satisfacción"),
            ("Sentimientos y Emociones", "Alivio"),
            ("Sentimientos y Emociones", "Orgullo"),
            ("Sentimientos y Emociones", "Admiración"),
            
            # Emociones Negativas
            ("Sentimientos y Emociones", "Miedo"),
            ("Sentimientos y Emociones", "Tristeza"),
            ("Sentimientos y Emociones", "Ira"),
            ("Sentimientos y Emociones", "Ansiedad"),
            ("Sentimientos y Emociones", "Frustración"),
            ("Sentimientos y Emociones", "Culpa"),
            ("Sentimientos y Emociones", "Vergüenza"),
            ("Sentimientos y Emociones", "Desesperación"),
            ("Sentimientos y Emociones", "Rencor"),
            
            # Estados Complejos / Históricos
            ("Sentimientos y Emociones", "Melancolía"),
            ("Sentimientos y Emociones", "Resignación"),
            ("Sentimientos y Emociones", "Indignación"),
            ("Sentimientos y Emociones", "Incertidumbre"),
            ("Sentimientos y Emociones", "Nostalgia"),
            ("Sentimientos y Emociones", "Euforia"),
            ("Sentimientos y Emociones", "Apatía"),
            ("Sentimientos y Emociones", "Soledad"),
            ("Sentimientos y Emociones", "Solidaridad"),
            ("Sentimientos y Emociones", "Optimismo"),
            ("Sentimientos y Emociones", "Pesimismo")
        ]
        
        count = 0
        for tema, concepto in sentimientos:
            # Evitar duplicados exactos
            exists = SemanticConcept.query.filter_by(tema=tema, concepto=concepto).first()
            if not exists:
                new_c = SemanticConcept(tema=tema, concepto=concepto)
                db.session.add(new_c)
                count += 1
        
        db.session.commit()
        print(f"Se han añadido {count} nuevos conceptos de sentimientos.")

if __name__ == "__main__":
    seed_sentimental_concepts()
