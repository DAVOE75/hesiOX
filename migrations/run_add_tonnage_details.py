import sys
sys.path.append('/opt/hesiox')
from app import app, db
from sqlalchemy import text

def add_columns():
    with app.app_context():
        queries = [
            "ALTER TABLE lloyds_register_survey_inspeccion_absoluta ADD COLUMN IF NOT EXISTS tonnage_under_deck_tonelaje_bajo_cubierta VARCHAR(255);",
            "ALTER TABLE lloyds_register_survey_inspeccion_absoluta ADD COLUMN IF NOT EXISTS tonnage_third_deck_tonelaje_tercera_cubierta VARCHAR(255);",
            "ALTER TABLE lloyds_register_survey_inspeccion_absoluta ADD COLUMN IF NOT EXISTS tonnage_houses_on_deck_tonelaje_casetas VARCHAR(255);",
            "ALTER TABLE lloyds_register_survey_inspeccion_absoluta ADD COLUMN IF NOT EXISTS tonnage_forecastle_tonelaje_castillo_proa VARCHAR(255);",
            "ALTER TABLE lloyds_register_survey_inspeccion_absoluta ADD COLUMN IF NOT EXISTS less_crew_space_menos_espacio_tripulacion VARCHAR(255);",
            "ALTER TABLE lloyds_register_survey_inspeccion_absoluta ADD COLUMN IF NOT EXISTS less_engine_room_menos_sala_maquinas VARCHAR(255);",
            "ALTER TABLE lloyds_register_survey_inspeccion_absoluta ADD COLUMN IF NOT EXISTS register_tonnage_tonelaje_registro VARCHAR(255);"
        ]
        try:
            for q in queries:
                db.session.execute(text(q))
            db.session.commit()
            print("Nuevas columnas de tonelaje añadidas exitosamente.")
        except Exception as e:
            db.session.rollback()
            print(f"Error al añadir columnas: {e}")

if __name__ == "__main__":
    add_columns()
