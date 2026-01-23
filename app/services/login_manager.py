from flask_login import LoginManager

login_manager = LoginManager()
login_manager.login_view = 'admin.login'
login_manager.login_message = 'Por favor, inicia sesión para acceder al panel de administración.'

