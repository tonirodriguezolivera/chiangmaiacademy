# services/payment_service.py
from extensions import db
from models import Payment, User, Course
from datetime import datetime
from sqlalchemy.orm import joinedload

class PaymentService:
    @staticmethod
    def create_payment(user_id, course_id, amount):
        """Crea un nuevo registro de pago con estado pendiente"""
        payment = Payment(user_id=user_id, course_id=course_id, amount=amount, status='pending')
        db.session.add(payment)
        db.session.commit()
        return payment
    
    @staticmethod
    def complete_payment(payment_id, transaction_id=None, payment_method=None):
        """
        Marca un pago existente como completado.
        Este metodo actua sobre la fila especifica de la base de datos,
        asegurando que no se dupliquen ni se borren registros.
        """
        # Usamos db.session.get para obtener la instancia mas fresca de la BDD
        payment = db.session.get(Payment, payment_id)
        if not payment:
            print(f"\n>>> ERROR: No se encontro el pago con ID {payment_id}")
            return None
        
        # Actualizamos el estado del registro que ya existe
        payment.status = 'completed'
        if transaction_id:
            payment.transaction_id = transaction_id
        if payment_method:
            payment.payment_method = payment_method
        payment.completed_at = datetime.utcnow()
        
        try:
            db.session.commit()
            print(f"\n>>> OK: Pago {payment_id} actualizado a 'completed'.")
            return payment
        except Exception as e:
            db.session.rollback()
            print(f"\n>>> ERROR al confirmar pago {payment_id}: {str(e)}")
            raise
    
    @staticmethod
    def get_payment_by_id(payment_id):
        """Obtiene un pago por su ID unico"""
        return db.session.get(Payment, payment_id)
    
    @staticmethod
    def get_payments_by_user(user_id):
        """Obtiene el historial de pagos de un usuario especifico"""
        return Payment.query.filter_by(user_id=user_id).order_by(Payment.created_at.desc()).all()
    
    @staticmethod
    def get_all_payments():
        """Obtiene todos los pagos registrados en el sistema"""
        return Payment.query.order_by(Payment.created_at.desc()).all()
    
    @staticmethod
    def get_payments_with_users():
        """
        Obtiene TODOS los pagos completados con sus relaciones (Usuario y Curso).
        Utilizamos joinedload para evitar que desaparezcan registros si hay inconsistencias
        en los nombres o estados de los cursos/usuarios vinculados.
        """
        # joinedload asegura que la data de User y Course se traiga en una sola consulta
        # y que el registro del PAGO sea el eje principal, evitando que se oculte.
        payments = Payment.query.filter_by(status='completed')\
            .options(joinedload(Payment.user), joinedload(Payment.course))\
            .order_by(Payment.completed_at.desc())\
            .all()
        
        print(f"\n>>> DEBUG DB: Se han recuperado {len(payments)} compras exitosas para el listado.")
        return payments
    
    @staticmethod
    def get_pending_payment_by_id(payment_id):
        """Busca un pago que todavia este en estado pendiente"""
        return Payment.query.filter_by(id=payment_id, status='pending').first()
    
    @staticmethod
    def get_pending_payments_by_ids(payment_ids):
        """Obtiene una lista de pagos pendientes a partir de un conjunto de IDs"""
        return Payment.query.filter(
            Payment.id.in_(payment_ids),
            Payment.status == 'pending'
        ).all()