import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from extensions import db
from app import app
from models import VectorLayer

def fix_db():
    print("Fixing database schema...")
    with app.app_context():
        try:
            # 1. Add the missing column
            db.session.execute(db.text("ALTER TABLE vector_layers ADD COLUMN IF NOT EXISTS orden INTEGER DEFAULT 0"))
            db.session.commit()
            print("Successfully added 'orden' column to 'vector_layers'.")
            
            # 2. Test query to see if 500 would still occur
            layers = VectorLayer.query.all()
            print(f"Test query successful! Total layers found: {len(layers)}")
            
        except Exception as e:
            db.session.rollback()
            print(f"Error during migration: {e}")

if __name__ == '__main__':
    fix_db()
