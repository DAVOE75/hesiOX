from app import app, db
from sqlalchemy import text

with app.app_context():
    try:
        db.session.execute(text("ALTER TABLE prensa ADD COLUMN ocr_map JSON;"))
        db.session.commit()
        print("Column ocr_map added to prensa")
    except Exception as e:
        print(f"Error adding ocr_map to prensa: {e}")
        db.session.rollback()

    try:
        db.session.execute(text("ALTER TABLE imagenes_prensa ADD COLUMN ocr_map JSON;"))
        db.session.commit()
        print("Column ocr_map added to imagenes_prensa")
    except Exception as e:
        print(f"Error adding ocr_map to imagenes_prensa: {e}")
        db.session.rollback()
