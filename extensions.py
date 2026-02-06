# extensions.py
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

db = SQLAlchemy()
login_manager = LoginManager()

# Configuración para Flask-Login
login_manager.login_view = 'admin.login'
login_manager.login_message_category = 'info'
login_manager.login_message = "Por favor, inicia sesión para acceder a esta página."

