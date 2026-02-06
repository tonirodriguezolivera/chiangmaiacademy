# blueprints/admin/routes.py
from flask import render_template, request, redirect, url_for, flash, current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from . import bp
from services.course_service import CourseService
from services.payment_gateway_service import PaymentGatewayService
from services.payment_service import PaymentService
from models import User
from extensions import db
from config import Config
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, TextAreaField, FloatField, BooleanField, SelectField, validators
import os
import uuid

class CourseForm(FlaskForm):
    title = StringField('Título del Curso', [
        validators.DataRequired(message='El título es obligatorio'),
        validators.Length(min=3, max=200)
    ])
    description = TextAreaField('Descripción')
    price = FloatField('Precio', [
        validators.DataRequired(message='El precio es obligatorio'),
        validators.NumberRange(min=0, message='El precio debe ser mayor a 0')
    ])
    image = FileField('Imagen del Curso', [
        FileAllowed(['jpg', 'jpeg', 'png', 'gif', 'webp'], 'Solo se permiten imágenes (JPG, PNG, GIF, WEBP)')
    ])
    is_active = BooleanField('Curso Activo')

class PaymentGatewayForm(FlaskForm):
    gateway_name = StringField('Pasarela de Pago', [
        validators.DataRequired(message='El nombre de la pasarela es obligatorio')
    ])
    # Campos específicos de Redsys
    merchant_code = StringField('Código de Comercio (Merchant Code)', [
        validators.DataRequired(message='El código de comercio es obligatorio'),
        validators.Length(max=9, message='El código de comercio debe tener máximo 9 caracteres')
    ])
    terminal = StringField('Terminal', [
        validators.DataRequired(message='El terminal es obligatorio'),
        validators.Length(max=3, message='El terminal debe tener máximo 3 caracteres')
    ])
    secret_key = StringField('Clave Secreta (Secret Key)', [
        validators.DataRequired(message='La clave secreta es obligatoria')
    ])
    environment = SelectField('Entorno', [
        validators.DataRequired(message='El entorno es obligatorio')
    ], choices=[('test', 'Test (Pruebas)'), ('production', 'Production (Producción)')])

# Funciones auxiliares para manejo de imágenes
def allowed_file(filename, app):
    """Verifica si el archivo tiene una extensión permitida"""
    allowed_extensions = app.config.get('ALLOWED_EXTENSIONS', {'png', 'jpg', 'jpeg', 'gif', 'webp'})
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions

def save_course_image(file, app):
    """Guarda la imagen del curso y retorna el nombre del archivo"""
    if file and file.filename and allowed_file(file.filename, app):
        # Crear carpeta si no existe
        upload_folder = app.config.get('UPLOAD_FOLDER')
        if upload_folder:
            os.makedirs(upload_folder, exist_ok=True)
            
            # Generar nombre único para el archivo
            filename = secure_filename(file.filename)
            ext = filename.rsplit('.', 1)[1].lower()
            unique_filename = f"{uuid.uuid4().hex}.{ext}"
            filepath = os.path.join(upload_folder, unique_filename)
            
            file.save(filepath)
            return unique_filename
    return None

@bp.route('/login', methods=['GET', 'POST'])
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

@bp.route('/logout')
@login_required
def logout():
    """Cerrar sesión"""
    logout_user()
    flash('Sesión cerrada correctamente.', 'info')
    return redirect(url_for('admin.login'))

@bp.route('/dashboard')
@login_required
def dashboard():
    """Panel de administración principal"""
    if not current_user.is_admin:
        flash('No tienes permisos para acceder a esta sección.', 'error')
        return redirect(url_for('main.index'))
    
    # Estadísticas
    courses = CourseService.get_all_courses()
    active_courses = [c for c in courses if c.is_active]
    payments = PaymentService.get_payments_with_users()
    
    total_revenue = sum(p.amount for p in payments)
    
    return render_template('admin/dashboard.html',
                         courses=active_courses,
                         total_courses=len(active_courses),
                         total_payments=len(payments),
                         total_revenue=total_revenue)

# ========== GESTIÓN DE CURSOS ==========

@bp.route('/courses')
@login_required
def courses_list():
    """Lista de cursos"""
    if not current_user.is_admin:
        flash('No tienes permisos para acceder a esta sección.', 'error')
        return redirect(url_for('main.index'))
    
    courses = CourseService.get_all_courses()
    return render_template('admin/courses_list.html', courses=courses)

@bp.route('/courses/new', methods=['GET', 'POST'])
@login_required
def course_new():
    """Crear nuevo curso"""
    if not current_user.is_admin:
        flash('No tienes permisos para acceder a esta sección.', 'error')
        return redirect(url_for('main.index'))
    
    form = CourseForm()
    if form.validate_on_submit():
        image_filename = None
        if form.image.data:
            image_filename = save_course_image(form.image.data, current_app)
        
        course = CourseService.create_course(
            title=form.title.data,
            description=form.description.data,
            price=form.price.data,
            image_filename=image_filename
        )
        flash('Curso creado exitosamente.', 'success')
        return redirect(url_for('admin.courses_list'))
    
    return render_template('admin/course_form.html', form=form, title='Nuevo Curso')

@bp.route('/courses/<int:course_id>/edit', methods=['GET', 'POST'])
@login_required
def course_edit(course_id):
    """Editar curso"""
    if not current_user.is_admin:
        flash('No tienes permisos para acceder a esta sección.', 'error')
        return redirect(url_for('main.index'))
    
    course = CourseService.get_course_by_id(course_id)
    if not course:
        flash('Curso no encontrado.', 'error')
        return redirect(url_for('admin.courses_list'))
    
    form = CourseForm(obj=course)
    if form.validate_on_submit():
        image_filename = course.image_filename  # Mantener la imagen actual por defecto
        
        # Si se sube una nueva imagen, guardarla
        if form.image.data:
            # Eliminar imagen anterior si existe
            if course.image_filename:
                old_image_path = os.path.join(current_app.config['UPLOAD_FOLDER'], course.image_filename)
                if os.path.exists(old_image_path):
                    os.remove(old_image_path)
            
            image_filename = save_course_image(form.image.data, current_app)
        
        CourseService.update_course(
            course_id,
            title=form.title.data,
            description=form.description.data,
            price=form.price.data,
            is_active=form.is_active.data,
            image_filename=image_filename
        )
        flash('Curso actualizado exitosamente.', 'success')
        return redirect(url_for('admin.courses_list'))
    
    return render_template('admin/course_form.html', form=form, course=course, title='Editar Curso')

@bp.route('/courses/<int:course_id>/delete', methods=['POST'])
@login_required
def course_delete(course_id):
    """Eliminar curso (soft delete)"""
    if not current_user.is_admin:
        flash('No tienes permisos para acceder a esta sección.', 'error')
        return redirect(url_for('main.index'))
    
    CourseService.delete_course(course_id)
    flash('Curso eliminado exitosamente.', 'success')
    return redirect(url_for('admin.courses_list'))

# ========== CONFIGURACIÓN DE PASARELA DE PAGO ==========

@bp.route('/payment-gateway', methods=['GET', 'POST'])
@login_required
def payment_gateway():
    """Configuración de pasarela de pago (Redsys)"""
    if not current_user.is_admin:
        flash('No tienes permisos para acceder a esta sección.', 'error')
        return redirect(url_for('main.index'))
    
    config = PaymentGatewayService.get_config()
    form = PaymentGatewayForm(obj=config) if config else PaymentGatewayForm()
    
    # Establecer valores por defecto si no hay configuración
    if not config:
        form.gateway_name.data = 'redsys'
        form.terminal.data = '001'
        form.environment.data = 'test'
    
    if form.validate_on_submit():
        # Si secret_key está vacío pero ya existe una config, mantener el valor existente
        secret_key_value = form.secret_key.data
        if not secret_key_value and config and config.secret_key:
            secret_key_value = config.secret_key  # Mantener el valor existente
        
        PaymentGatewayService.update_config(
            gateway_name=form.gateway_name.data,
            merchant_code=form.merchant_code.data or None,
            terminal=form.terminal.data or '001',
            secret_key=secret_key_value or None,
            environment=form.environment.data or 'test'
        )
        flash('Configuración de Redsys actualizada exitosamente.', 'success')
        return redirect(url_for('admin.payment_gateway'))
    
    return render_template('admin/payment_gateway.html', form=form, config=config)

# ========== COMPRADORES ==========

@bp.route('/buyers')
@login_required
def buyers_list():
    """Lista de compradores"""
    if not current_user.is_admin:
        flash('No tienes permisos para acceder a esta sección.', 'error')
        return redirect(url_for('main.index'))
    
    payments = PaymentService.get_payments_with_users()
    return render_template('admin/buyers_list.html', payments=payments)
