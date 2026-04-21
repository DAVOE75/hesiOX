from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from flask_login import LoginManager

# Initialize SQLAlchemy with no settings
db = SQLAlchemy()

# Initialize CSRF protection
csrf = CSRFProtect()

# Initialize LoginManager
login_manager = LoginManager()
