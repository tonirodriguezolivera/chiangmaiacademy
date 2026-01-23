from app.services.database import db
from app.models.payment import Payment
from app.models.user import User
from datetime import datetime
from flask import current_app

class PaymentService:
    @staticmethod
    def create_payment(user_id, amount):
        """Crea un nuevo pago pendiente"""
        payment = Payment(user_id=user_id, amount=amount, status='pending')
        db.session.add(payment)
        db.session.commit()
        return payment
    
    @staticmethod
    def complete_payment(payment_id, transaction_id=None, payment_method=None):
        """Marca un pago como completado"""
        payment = Payment.query.get(payment_id)
        if payment:
            payment.status = 'completed'
            payment.transaction_id = transaction_id
            payment.payment_method = payment_method
            payment.completed_at = datetime.utcnow()
            db.session.commit()
            return payment
        return None
    
    @staticmethod
    def get_payment_by_id(payment_id):
        """Obtiene un pago por ID"""
        return Payment.query.get(payment_id)
    
    @staticmethod
    def get_payments_by_user(user_id):
        """Obtiene todos los pagos de un usuario"""
        return Payment.query.filter_by(user_id=user_id).order_by(Payment.created_at.desc()).all()
    
    @staticmethod
    def get_all_payments():
        """Obtiene todos los pagos"""
        return Payment.query.order_by(Payment.created_at.desc()).all()
    
    @staticmethod
    def get_course_price():
        """Obtiene el precio del curso desde la configuración"""
        return current_app.config.get('COURSE_PRICE', 299.00)

