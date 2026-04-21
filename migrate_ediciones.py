
from app import app
from extensions import db
from models import EdicionTipoRecurso

def migrate():
    with app.app_context():
        print("🚀 Iniciando migración de opciones de edición...")
        
        # Crear tablas si no existen
        db.create_all()
        
        # Datos iniciales para Prensa
        prensa_options = [
            ('diaria', 'Diaria', 1),
            ('mañana', 'Mañana', 2),
            ('tarde', 'Tarde', 3),
            ('noche', 'Noche', 4),
            ('semanal', 'Semanal', 5),
            ('quincenal', 'Quincenal', 6),
            ('mensual', 'Mensual', 7),
            ('bimensual', 'Bimensual', 8),
            ('semestral', 'Semestral', 9),
            ('anual', 'Anual', 10)
        ]
        
        # Datos iniciales para Libros
        libro_options = [
            ('principe', 'Príncipe o 1ª Edición', 1),
            ('bolsillo', 'De Bolsillo', 2),
            ('lujo', 'De Lujo/Bibliófilo', 3),
            ('critica', 'Crítica', 4),
            ('facsimilar', 'Facsimilar', 5),
            ('ilustrada', 'Ilustrada', 6),
            ('bilingue', 'Bilingüe', 7),
            ('abreviada', 'Abreviada', 8)
        ]
        
        # Datos iniciales para Artículos
        articulo_options = [
            ('autor', 'Versión de Autor (Pre-print)', 1),
            ('aceptada', 'Versión Aceptada (Post-print)', 2),
            ('editorial', 'Versión de la Editorial', 3),
            ('suplemento', 'Suplemento / Anexo', 4)
        ]
        
        # Datos iniciales para Tesis
        tesis_options = [
            ('original', 'Versión Original', 1),
            ('publicada', 'Edición Publicada', 2),
            ('resumen', 'Resumen / Abstract', 3)
        ]
        
        # Datos iniciales para Fotografía
        foto_options = [
            ('original', 'Original', 1),
            ('epoca', 'Copia de Época', 2),
            ('reproduccion', 'Reproducción Posterior', 3),
            ('digital', 'Archivo Digital', 4)
        ]
        
        # Datos iniciales para Otros
        otros_options = [
            ('unica', 'Edición Única', 1),
            ('especial', 'Edición Especial', 2),
            ('limitada', 'Edición Limitada', 3)
        ]
        
        # Limpiar datos existentes para evitar duplicados en re-ejecución
        # EdicionTipoRecurso.query.delete()
        
        all_options = {
            'prensa': prensa_options,
            'libro': libro_options,
            'articulo': articulo_options,
            'tesis': tesis_options,
            'fotografia': foto_options,
            'otros': otros_options
        }
        
        for tipo, options in all_options.items():
            for valor, etiqueta, orden in options:
                exists = EdicionTipoRecurso.query.filter_by(tipo_recurso=tipo, valor=valor).first()
                if not exists:
                    db.session.add(EdicionTipoRecurso(
                        tipo_recurso=tipo,
                        valor=valor,
                        etiqueta=etiqueta,
                        orden=orden
                    ))
        
        db.session.commit()
        print("✅ Migración completada con éxito.")

if __name__ == "__main__":
    migrate()
