from app.services.database import db
from flask_login import UserMixin
from datetime import datetime

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
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

