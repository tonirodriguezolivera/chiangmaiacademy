# config.py
import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///' + os.path.join(basedir, 'instance', 'thai_massage_school.db'))
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Configuración de pagos
    COURSE_PRICE = float(os.getenv('COURSE_PRICE', '299.00'))
    
    # Configuración de administración
    ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin')
    ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'admin123')
    
    # Configuración de uploads
    UPLOAD_FOLDER = os.path.join(basedir, 'static', 'uploads', 'courses')
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5 MB máximo
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}



