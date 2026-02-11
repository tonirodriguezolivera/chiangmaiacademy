# models.py
from extensions import db
from flask_login import UserMixin
from datetime import datetime

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_admin = db.Column(db.Boolean, default=False)
    
    # Relación con pagos
    payments = db.relationship('Payment', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<User {self.email}>'
    
    def has_paid(self):
        """Verifica si el usuario tiene un pago completado"""
        return any(payment.status == 'completed' for payment in self.payments)
    
    def get_id(self):
        """Necesario para Flask-Login"""
        return str(self.id)


class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False)
    image_filename = db.Column(db.String(255))  # Nombre del archivo de imagen
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relación con pagos
    payments = db.relationship('Payment', backref='course', lazy=True)
    
    def __repr__(self):
        return f'<Course {self.title}>'
    
    def get_image_url(self):
        """Retorna la URL de la imagen del curso"""
        if self.image_filename:
            return f'/static/uploads/courses/{self.image_filename}'
        return '/static/images/default-course.jpg'  # Imagen por defecto


class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, completed, failed
    payment_method = db.Column(db.String(50))
    transaction_id = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    
    def __repr__(self):
        return f'<Payment {self.id} - {self.status}>'


class PaymentGatewayConfig(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    gateway_name = db.Column(db.String(50), nullable=False, default='redsys')  # redsys, stripe, paypal, etc.
    # Campos específicos de Redsys
    merchant_code = db.Column(db.String(9))  # Código de comercio (Ds_Merchant_MerchantCode)
    terminal = db.Column(db.String(3), default='001')  # Terminal (Ds_Merchant_Terminal)
    secret_key = db.Column(db.String(500))  # Clave secreta para firmar
    environment = db.Column(db.String(10), default='test')  # test o production
    # URLs de Redsys
    redsys_url_test = db.Column(db.String(200), default='https://sis-t.redsys.es:25443/sis/realizarPago')
    redsys_url_production = db.Column(db.String(200), default='https://sis.redsys.es/sis/realizarPago')
    # URL base pública para notificaciones (opcional, si está vacío usa request.url_root)
    public_base_url = db.Column(db.String(200))  # Ej: https://tudominio.com
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<PaymentGatewayConfig {self.gateway_name}>'
    
    def get_redsys_url(self):
        """Retorna la URL de Redsys según el entorno"""
        if self.environment == 'production':
            return self.redsys_url_production or 'https://sis.redsys.es/sis/realizarPago'
        return self.redsys_url_test or 'https://sis-t.redsys.es:25443/sis/realizarPago'

