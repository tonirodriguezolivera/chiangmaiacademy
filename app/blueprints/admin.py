from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from app.services.user_service import UserService
from app.services.payment_service import PaymentService
from app.models.user import User
from app.services.database import db
from config import Config

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Página de login para administradores"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Verificar credenciales de admin
        if username == Config.ADMIN_USERNAME and password == Config.ADMIN_PASSWORD:
            # Crear o obtener usuario admin
            admin_user = User.query.filter_by(is_admin=True).first()
            if not admin_user:
                admin_user = User(
                    name='Administrador',
                    email=Config.ADMIN_USERNAME + '@admin.com',
                    phone='000000000',
                    is_admin=True
                )
                db.session.add(admin_user)
                db.session.commit()
            
            login_user(admin_user)
            flash('Sesión iniciada correctamente.', 'success')
            return redirect(url_for('admin.dashboard'))
        else:
            flash('Credenciales incorrectas.', 'error')
    
    return render_template('admin/login.html')

@admin_bp.route('/logout')
@login_required
def logout():
    """Cerrar sesión"""
    logout_user()
    flash('Sesión cerrada correctamente.', 'info')
    return redirect(url_for('admin.login'))

@admin_bp.route('/dashboard')
@login_required
def dashboard():
    """Panel de administración"""
    # Verificar que el usuario es admin
    if not current_user.is_admin:
        flash('No tienes permisos para acceder a esta sección.', 'error')
        return redirect(url_for('main.index'))
    
    # Obtener usuarios con pagos completados
    users_with_payments = UserService.get_users_with_payments()
    
    # Obtener todos los usuarios registrados
    all_users = UserService.get_all_users()
    
    # Estadísticas
    total_users = len(all_users)
    paid_users = len(users_with_payments)
    pending_payments = len([u for u in all_users if not u.has_paid()])
    
    return render_template('admin/dashboard.html',
                         users_with_payments=users_with_payments,
                         all_users=all_users,
                         total_users=total_users,
                         paid_users=paid_users,
                         pending_payments=pending_payments)

