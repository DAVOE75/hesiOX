
import sys
import os
from flask import Flask
from dotenv import load_dotenv

sys.path.append(os.getcwd())

from extensions import db
from models import Usuario

def create_app():
    app = Flask(__name__)
    load_dotenv()
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("DATABASE_URL no encontrado en .env")
        sys.exit(1)
        
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    
    db.init_app(app)
    return app

def main():
    app = create_app()
    with app.app_context():
        if len(sys.argv) < 2:
            print("Usuarios existentes:")
            users = Usuario.query.all()
            for u in users:
                print(f" - {u.nombre} ({u.rol})")
            print("\nUso: python3 change_password.py <usuario> <nueva_contraseña>")
            return

        username_or_email = sys.argv[1]
        
        # Intentar buscar por nombre de usuario
        user = Usuario.query.filter_by(nombre=username_or_email).first()
        
        # Si no se encuentra, intentar por email
        if not user:
            user = Usuario.query.filter_by(email=username_or_email).first()
        
        if not user:
            print(f"Usuario o Email '{username_or_email}' no encontrado.")
            return

        if len(sys.argv) < 3:
            print(f"Usuario '{user.nombre}' ({user.email}) encontrado.")
            print("Proporcione la contraseña como segundo argumento para cambiarla.")
            return
            
        new_pass = sys.argv[2]
        user.set_password(new_pass)
        db.session.commit()
        print(f"Contraseña actualizada para '{user.nombre}' ({user.email}).")

if __name__ == "__main__":
    main()
