from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.services.user_service import UserService
from app.services.payment_service import PaymentService
from wtforms import Form, StringField, EmailField, TelField, validators

main_bp = Blueprint('main', __name__)

class RegistrationForm(Form):
    name = StringField('Nombre Completo', [
        validators.DataRequired(message='El nombre es obligatorio'),
        validators.Length(min=3, max=100, message='El nombre debe tener entre 3 y 100 caracteres')
    ])
    email = EmailField('Email', [
        validators.DataRequired(message='El email es obligatorio'),
        validators.Email(message='Email inválido')
    ])
    phone = TelField('Teléfono', [
        validators.DataRequired(message='El teléfono es obligatorio'),
        validators.Length(min=9, max=20, message='El teléfono debe tener entre 9 y 20 caracteres')
    ])

@main_bp.route('/')
def index():
    """Landing page principal"""
    form = RegistrationForm()
    course_price = PaymentService.get_course_price()
    return render_template('index.html', form=form, course_price=course_price)

@main_bp.route('/register', methods=['POST'])
def register():
    """Procesa el registro del usuario"""
    form = RegistrationForm(request.form)
    
    if form.validate():
        # Verificar si el email ya existe
        existing_user = UserService.get_user_by_email(form.email.data)
        
        if existing_user:
            flash('Este email ya está registrado. Por favor, inicia sesión o usa otro email.', 'error')
            return redirect(url_for('main.index'))
        
        # Crear nuevo usuario
        user = UserService.create_user(
            name=form.name.data,
            email=form.email.data,
            phone=form.phone.data
        )
        
        # Crear pago pendiente
        payment = PaymentService.create_payment(user.id, PaymentService.get_course_price())
        
        flash('Registro exitoso. Por favor, completa el pago para finalizar tu inscripción.', 'success')
        return redirect(url_for('payment.process_payment', payment_id=payment.id))
    else:
        # Mostrar errores de validación
        for field, errors in form.errors.items():
            for error in errors:
                flash(error, 'error')
        return redirect(url_for('main.index'))

