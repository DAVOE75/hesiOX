import sys
sys.path.append('/opt/hesiox')
from app import app, db
from sqlalchemy import text

def add_columns():
    with app.app_context():
        queries = [
            # Proportion and numbers
            "ALTER TABLE lloyds_register_survey_inspeccion_absoluta ADD COLUMN IF NOT EXISTS half_breadth_moulded_media_manga VARCHAR(255);",
            "ALTER TABLE lloyds_register_survey_inspeccion_absoluta ADD COLUMN IF NOT EXISTS depth_keel_to_main_deck_puntal_quilla_cubierta VARCHAR(255);",
            "ALTER TABLE lloyds_register_survey_inspeccion_absoluta ADD COLUMN IF NOT EXISTS girth_half_midship_frame_perimetro_media_cuaderna VARCHAR(255);",
            "ALTER TABLE lloyds_register_survey_inspeccion_absoluta ADD COLUMN IF NOT EXISTS first_number_primer_numero VARCHAR(255);",
            "ALTER TABLE lloyds_register_survey_inspeccion_absoluta ADD COLUMN IF NOT EXISTS second_number_segundo_numero VARCHAR(255);",
            "ALTER TABLE lloyds_register_survey_inspeccion_absoluta ADD COLUMN IF NOT EXISTS proportions_breadths_to_length_proporcion_manga_eslora VARCHAR(255);",
            "ALTER TABLE lloyds_register_survey_inspeccion_absoluta ADD COLUMN IF NOT EXISTS proportions_depths_to_length_upper_proporcion_puntal_eslora_sup VARCHAR(255);",
            "ALTER TABLE lloyds_register_survey_inspeccion_absoluta ADD COLUMN IF NOT EXISTS proportions_depths_to_length_main_proporcion_puntal_eslora_ppal VARCHAR(255);",
            
            # Additional Header stats
            "ALTER TABLE lloyds_register_survey_inspeccion_absoluta ADD COLUMN IF NOT EXISTS launched_lanzado VARCHAR(255);",
            "ALTER TABLE lloyds_register_survey_inspeccion_absoluta ADD COLUMN IF NOT EXISTS owners_residence_residencia_propietarios VARCHAR(255);",
            "ALTER TABLE lloyds_register_survey_inspeccion_absoluta ADD COLUMN IF NOT EXISTS surveyed_while_inspeccionado_mientras VARCHAR(255);"
        ]
        try:
            for q in queries:
                db.session.execute(text(q))
            db.session.commit()
            print("Nuevas columnas añadidas exitosamente.")
        except Exception as e:
            db.session.rollback()
            print(f"Error al añadir columnas: {e}")

if __name__ == "__main__":
    add_columns()
