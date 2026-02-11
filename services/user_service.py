# services/user_service.py
from extensions import db
from models import User, Payment

class UserService:
    @staticmethod
    def create_user(name, email, phone):
        """
        Crea SIEMPRE un nuevo registro de usuario, aunque el email se repita.
        Necesario para que cada compra preserve los datos exactos que introdujo
        el comprador en ese pedido.
        """
        user = User(name=name, email=email, phone=phone)
        db.session.add(user)
        db.session.commit()
        return user
    
    @staticmethod
    def get_user_by_email(email):
        """Obtiene un usuario por su direccion de correo electronico"""
        return User.query.filter_by(email=email).first()
    
    @staticmethod
    def get_user_by_id(user_id):
        """Obtiene un usuario por su ID unico"""
        return User.query.get(user_id)
    
    @staticmethod
    def get_all_users():
        """Obtiene la lista de todos los usuarios registrados"""
        return User.query.order_by(User.created_at.desc()).all()
    
    @staticmethod
    def get_users_with_payments():
        """Obtiene los usuarios que tienen al menos un pago con estado 'completed'"""
        return User.query.join(Payment).filter(
            Payment.status == 'completed'
        ).distinct().order_by(User.created_at.desc()).all()
    
    @staticmethod
    def is_admin(user_id):
        """Verifica si un usuario tiene permisos de administrador"""
        user = User.query.get(user_id)
        return user and user.is_admin
