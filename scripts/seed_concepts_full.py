import sys
import os

# Add parent directory to path to import app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from extensions import db
from models import SemanticConcept

CONCEPTS = {
    "Geografía Física": [
        "Orografía", "Hidrografía", "Climatología", "Geomorfología", "Biogeografía", 
        "Relieve", "Cordillera", "Meseta", "Llanura", "Depresión", "Valle", "Cabo", "Golfo", "Bahía", "Península", "Isla", "Archipiélago",
        "Río", "Lago", "Laguna", "Acuífero", "Glaciar", "Océano", "Mar", "Corriente marina",
        "Clima Tropical", "Clima Árido", "Clima Templado", "Clima Continental", "Clima Polar", "Microclima",
        "Tectónica de placas", "Volcanismo", "Sismicidad", "Erosión", "Sedimentación"
    ],
    "Geografía Humana": [
        "Demografía", "Población", "Migración", "Emigración", "Inmigración", "Densidad de población", "Esperanza de vida", "Tasa de natalidad", "Tasa de mortalidad",
        "Urbanismo", "Ciudad", "Área metropolitana", "Megalópolis", "Rural", "Ordenación del territorio",
        "Geopolítica", "Frontera", "Estado", "Nación", "Soberanía", "Territorialidad", "Globalización",
        "Sector Primario", "Sector Secundario", "Sector Terciario", "Turismo", "Transporte", "Comercio internacional"
    ],
    "Geografía Regional (España)": [
        "Andalucía", "Aragón", "Asturias", "Baleares", "Canarias", "Cantabria", "Castilla-La Mancha", "Castilla y León", "Cataluña", "Extremadura", "Galicia", "Madrid", "Murcia", "Navarra", "País Vasco", "La Rioja", "Comunidad Valenciana", "Ceuta", "Melilla",
        "Pirineos", "Sistema Central", "Cordillera Cantábrica", "Sistema Ibérico", "Serranía de Ronda", "Sierra Nevada", "Picos de Europa",
        "Río Ebro", "Río Tajo", "Río Duero", "Río Guadiana", "Río Guadalquivir", "Río Miño", "Río Segura", "Río Júcar"
    ],
    "Historia Universal": [
        "Prehistoria", "Edad Antigua", "Edad Media", "Edad Moderna", "Edad Contemporánea",
        "Revolución Neolítica", "Imperio Romano", "Grecia Clásica", "Antiguo Egipto", "Mesopotamia",
        "Feudalismo", "Cruzadas", "Renacimiento", "Ilustración", "Revolución Industrial", "Revolución Francesa",
        "Imperialismo", "Colonialismo", "Primera Guerra Mundial", "Segunda Guerra Mundial", "Guerra Fría", "Descolonización", "Caída del Muro de Berlín"
    ],
    "Historia de España": [
        "Hispania Romana", "Reino Visigodo", "Al-Ándalus", "Reconquista", "Reyes Católicos", "Descubrimiento de América",
        "Imperio Español", "Siglo de Oro", "Guerra de Sucesión", "Despotismo Ilustrado", 
        "Guerra de la Independencia", "Cortes de Cádiz", "Constitución de 1812", "Guerras Carlistas", "Restauración Borbónica",
        "Segunda República", "Guerra Civil Española", "Franquismo", "Transición Española"
    ],
    "Arqueología": [
        "Yacimiento", "Excavación", "Estratigrafía", "Prospección", "Datación por Radiocarbono", "Dendrocronología",
        "Arte Rupestre", "Megalitismo", "Dólmenes", "Menhires", "Castro", "Villa Romana", "Necrópolis",
        "Cerámica", "Numismática", "Epigrafía", "Restauración", "Conservación", "Patrimonio Histórico"
    ],
    "Ciencias Sociales - Sociología": [
        "Estructura Social", "Clase Social", "Estratificación", "Movilidad Social", "Desigualdad", "Pobreza", "Exclusión Social",
        "Familia", "Género", "Roles de género", "Feminismo", "Raza", "Etnicidad", "Racismo",
        "Socialización", "Control Social", "Desviación", "Crimen", "Conflicto Social", "Cambio Social", "Movimientos Sociales"
    ],
    "Ciencias Sociales - Política": [
        "Democracia", "Dictadura", "Monarquía", "República", "Parlamentarismo", "Presidencialismo",
        "Partidos Políticos", "Sistemas Electorales", "Ideologías", "Liberalismo", "Conservadurismo", "Socialismo", "Comunismo", "Fascismo", "Anarquismo",
        "Poder Legislativo", "Poder Ejecutivo", "Poder Judicial", "Constitución", "Derechos Humanos", "Sociedad Civil"
    ],
    "Ciencias Sociales - Economía": [
        "Microeconomía", "Macroeconomía", "PIB", "Inflación", "Desempleo", "Déficit", "Deuda Pública",
        "Mercado", "Oferta y Demanda", "Precios", "Competencia", "Monopolio", "Oligopolio",
        "Capitalismo", "Comunismo", "Economía de Mercado", "Estado de Bienestar",
        "Finanzas", "Bolsa", "Inversión", "Ahorro", "Banca", "Impuestos", "Política Fiscal", "Política Monetaria"
    ],
    "Humanidades - Filosofía": [
        "Metafísica", "Epistemología", "Ética", "Estética", "Lógica", "Filosofía Política",
        "Idealismo", "Materialismo", "Racionalismo", "Empirismo", "Existencialismo", "Fenomenología", "Estructuralismo", "Posmodernismo",
        "Platón", "Aristóteles", "Descartes", "Kant", "Hegel", "Marx", "Nietzsche", "Heidegger", "Wittgenstein"
    ],
    "Humanidades - Literatura": [
        "Narrativa", "Poesía", "Teatro", "Ensayo", "Novela", "Cuento",
        "Realismo", "Naturalismo", "Romanticismo", "Modernismo", "Generación del 98", "Generación del 27", "Vanguardias",
        "Realismo Mágico", "Boom Latinoamericano", "Literatura Clásica", "Literatura Medieval", "Barroco"
    ],
    "Humanidades - Arte": [
        "Pintura", "Escultura", "Arquitectura", "Fotografía", "Cine",
        "Románico", "Gótico", "Renacimiento", "Barroco", "Neoclasicismo", "Impresionismo", "Expresionismo", "Cubismo", "Surrealismo", "Abstracción",
        "Museología", "Patrimonio Artístico", "Historia del Arte", "Iconografía"
    ],
    "Periodismo y Comunicación": [
        "Noticia", "Reportaje", "Crónica", "Entrevista", "Editorial", "Artículo de Opinión", "Columna",
        "Periodismo de Investigación", "Periodismo de Datos", "Periodismo Deportivo", "Periodismo Cultural", "Periodismo Político",
        "Medios de Comunicación", "Prensa Escrita", "Radio", "Televisión", "Internet", "Redes Sociales",
        "Libertad de Prensa", "Censura", "Ética Periodística", "Deontología", "Fuentes de Información", "Fake News", "Desinformación",
        "Audiencia", "Opinión Pública", "Agenda Setting", "Framing"
    ],
    "Terminología Hesiode (Especifica)": [
        "Cartografía Histórica", "Georeferenciación", "Análisis Espacial", "Toponimia",
        "Hemeroteca Digital", "OCR", "Reconocimiento de Texto", "Metadatos", "Dublin Core",
        "Humanidades Digitales", "Minería de Textos", "Procesamiento de Lenguaje Natural", "Análisis de Sentimiento"
    ]
}

def seed_expansion():
    with app.app_context():
        count_new = 0
        count_existing = 0
        
        for tema, lista_conceptos in CONCEPTS.items():
            print(f"Procesando categoría: {tema}...")
            for concepto in lista_conceptos:
                # Comprobar si existe (case insensitive podría ser mejor, pero empezamos estricto)
                exists = SemanticConcept.query.filter_by(tema=tema, concepto=concepto).first()
                
                # Check cross-theme duplications if necessary, but sticking to tema+concepto unique constraint logic
                # Maybe checking if concept exists in ANY theme? The user said "remove duplicates".
                # Usually duplicates mean exact same concept string in exact same theme.
                # However, if 'Guerra Civil' is in History and Military, that's fine.
                
                if not exists:
                    nuevo = SemanticConcept(tema=tema, concepto=concepto)
                    db.session.add(nuevo)
                    count_new += 1
                else:
                    count_existing += 1
                    
        db.session.commit()
        print(f"\nRESUMEN:")
        print(f"- Conceptos nuevos añadidos: {count_new}")
        print(f"- Conceptos ya existentes (saltados): {count_existing}")
        print(f"- Total procesados: {count_new + count_existing}")

if __name__ == "__main__":
    seed_expansion()
