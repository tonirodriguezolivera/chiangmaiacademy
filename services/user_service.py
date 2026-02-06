# services/user_service.py
from extensions import db
from models import User, Payment

class UserService:
    @staticmethod
    def create_user(name, email, phone):
        """Crea un nuevo usuario o retorna el existente si el email ya está registrado"""
        # Buscar si ya existe un usuario con ese email
        existing_user = User.query.filter_by(email=email).first()
        
        if existing_user:
            # Actualizar datos si han cambiado
            if existing_user.name != name:
                existing_user.name = name
            if existing_user.phone != phone:
                existing_user.phone = phone
            db.session.commit()
            return existing_user
        
        # Crear nuevo usuario
        user = User(name=name, email=email, phone=phone)
        db.session.add(user)
        db.session.commit()
        return user
    
    @staticmethod
    def get_user_by_email(email):
        """Obtiene un usuario por email"""
        return User.query.filter_by(email=email).first()
    
    @staticmethod
    def get_user_by_id(user_id):
        """Obtiene un usuario por ID"""
        return User.query.get(user_id)
    
    @staticmethod
    def get_all_users():
        """Obtiene todos los usuarios"""
        return User.query.order_by(User.created_at.desc()).all()
    
    @staticmethod
    def get_users_with_payments():
        """Obtiene usuarios que han completado el pago"""
        return User.query.join(Payment).filter(
            Payment.status == 'completed'
        ).distinct().order_by(User.created_at.desc()).all()
    
    @staticmethod
    def is_admin(user_id):
        """Verifica si un usuario es administrador"""
        user = User.query.get(user_id)
        return user and user.is_admin

