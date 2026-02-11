# app.py
from flask import Flask
from config import Config
from extensions import db, login_manager
from models import User
import os

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Crear carpeta de uploads si no existe
    upload_folder = app.config.get('UPLOAD_FOLDER')
    if upload_folder and not os.path.exists(upload_folder):
        os.makedirs(upload_folder, exist_ok=True)

    # Inicializar extensiones
    db.init_app(app)
    login_manager.init_app(app)

    # Configurar user_loader para Flask-Login
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Registrar Blueprints
    from blueprints.main import bp as main_bp
    app.register_blueprint(main_bp)

    from blueprints.admin import bp as admin_bp
    app.register_blueprint(admin_bp, url_prefix='/admin')

    from blueprints.payment import bp as payment_bp
    app.register_blueprint(payment_bp, url_prefix='/payment')

    # Crear tablas
    with app.app_context():
        db.create_all()

    return app

# LÍNEA CRÍTICA PARA CPANEL: 
# Definimos 'app' en el ámbito global para que Passenger pueda encontrarla.
app = create_app()

# Este bloque se mantiene para que sigas pudiendo ejecutarlo localmente
if __name__ == '__main__':
    app.run(debug=True)