import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///thai_massage_school.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Configuración de pagos
    COURSE_PRICE = float(os.environ.get('COURSE_PRICE', '299.00'))
    
    # Configuración de administración
    ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin123')

