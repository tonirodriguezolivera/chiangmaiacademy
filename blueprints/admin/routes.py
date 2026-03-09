# blueprints/admin/routes.py
from flask import render_template, request, redirect, url_for, flash, current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from . import bp
from services.course_service import CourseService
from services.payment_gateway_service import PaymentGatewayService
from services.payment_service import PaymentService
from models import User, CourseImage
from extensions import db
from config import Config
from flask_wtf import FlaskForm
from flask_wtf.file import MultipleFileField
from wtforms import StringField, TextAreaField, FloatField, BooleanField, SelectField, validators
import os
import uuid
from werkzeug.datastructures import FileStorage

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
    images = MultipleFileField('Imágenes del Curso')
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
    public_base_url = StringField('URL Base Pública (Opcional)', [
        validators.Optional(),
        validators.URL(message='Debe ser una URL válida')
    ])

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

def save_course_images(files, app):
    """Guarda múltiples imágenes del curso y retorna los nombres guardados."""
    if not files:
        return []

    saved_filenames = []
    for file in files:
        if not isinstance(file, FileStorage):
            continue
        if not file.filename:
            continue
        filename = save_course_image(file, app)
        if filename:
            saved_filenames.append(filename)
    return saved_filenames

def has_selected_uploads(files):
    """Indica si el usuario seleccionó al menos un archivo con nombre."""
    if not files:
        return False
    return any(isinstance(file, FileStorage) and file.filename for file in files)

def ensure_legacy_image_in_gallery(course):
    """Sincroniza image_filename legacy dentro de la galería CourseImage."""
    if not course or not course.image_filename:
        return
    already_exists = any(image.filename == course.image_filename for image in course.images)
    if not already_exists:
        db.session.add(CourseImage(course_id=course.id, filename=course.image_filename))
        db.session.commit()

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
        uploaded_image_filenames = save_course_images(form.images.data, current_app)
        image_filename = uploaded_image_filenames[0] if uploaded_image_filenames else None
        
        course = CourseService.create_course(
            title=form.title.data,
            description=form.description.data,
            price=form.price.data,
            image_filename=image_filename,
            image_filenames=uploaded_image_filenames
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

    ensure_legacy_image_in_gallery(course)
    course = CourseService.get_course_by_id(course_id)

    form = CourseForm(obj=course)
    # Evita conflicto entre campo de formulario "images" y relación ORM "course.images".
    if request.method == 'GET':
        form.images.data = []
    if form.validate_on_submit():
        image_filename = course.image_filename
        had_selected_files = has_selected_uploads(form.images.data)
        uploaded_image_filenames = save_course_images(form.images.data, current_app)
        if uploaded_image_filenames and not image_filename:
            image_filename = uploaded_image_filenames[0]
        if had_selected_files and not uploaded_image_filenames:
            flash('No se pudo subir ninguna imagen. Revisa que el formato sea JPG, PNG, GIF o WEBP.', 'error')
        
        CourseService.update_course(
            course_id,
            title=form.title.data,
            description=form.description.data,
            price=form.price.data,
            is_active=form.is_active.data,
            image_filename=image_filename,
            new_image_filenames=uploaded_image_filenames
        )
        if uploaded_image_filenames:
            flash(f'Se añadieron {len(uploaded_image_filenames)} imagen(es) al curso.', 'success')
        else:
            flash('Curso actualizado exitosamente.', 'success')
        return redirect(url_for('admin.course_edit', course_id=course_id))
    
    return render_template('admin/course_form.html', form=form, course=course, title='Editar Curso')

@bp.route('/courses/<int:course_id>/images/<int:image_id>/delete', methods=['POST'])
@login_required
def course_image_delete(course_id, image_id):
    """Elimina una imagen concreta de un curso."""
    if not current_user.is_admin:
        flash('No tienes permisos para acceder a esta sección.', 'error')
        return redirect(url_for('main.index'))

    course = CourseService.get_course_by_id(course_id)
    if not course:
        flash('Curso no encontrado.', 'error')
        return redirect(url_for('admin.courses_list'))

    image = CourseImage.query.filter_by(id=image_id, course_id=course_id).first()
    if not image:
        flash('Imagen no encontrada.', 'error')
        return redirect(url_for('admin.course_edit', course_id=course_id))

    filename = image.filename
    db.session.delete(image)
    db.session.flush()

    remaining_images = CourseImage.query.filter_by(course_id=course_id).order_by(CourseImage.id.asc()).all()
    if course.image_filename == filename:
        course.image_filename = remaining_images[0].filename if remaining_images else None

    # Solo borra el archivo físico si ya no está referenciado por ningún curso.
    still_used = CourseImage.query.filter_by(filename=filename).first()
    if not still_used:
        image_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        if os.path.exists(image_path):
            os.remove(image_path)

    db.session.commit()
    flash('Imagen eliminada correctamente.', 'success')
    return redirect(url_for('admin.course_edit', course_id=course_id))

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
        
        # 🔧 Limpiar la clave secreta antes de guardar (strip)
        secret_key_clean = secret_key_value.strip() if secret_key_value else None
        
        PaymentGatewayService.update_config(
            gateway_name=form.gateway_name.data,
            merchant_code=form.merchant_code.data or None,
            terminal=form.terminal.data or '001',
            secret_key=secret_key_clean,
            environment=form.environment.data or 'test',
            public_base_url=form.public_base_url.data or None
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
