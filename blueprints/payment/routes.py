# blueprints/payment/routes.py
from flask import render_template, request, redirect, url_for, flash, jsonify
from . import bp
from services.payment_service import PaymentService
from services.user_service import UserService
from services.course_service import CourseService
from services.offer_service import OfferService
from services.redsys_service import RedsysService
from flask_wtf import FlaskForm
from wtforms import StringField, EmailField, TelField, validators

class PurchaseForm(FlaskForm):
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

@bp.route('/buy/<int:course_id>', methods=['GET', 'POST'])
def buy_course(course_id):
    """Página de compra del curso"""
    course = CourseService.get_course_by_id(course_id)
    
    if not course or not course.is_active:
        flash('Curso no encontrado.', 'error')
        return redirect(url_for('main.index'))
    
    form = PurchaseForm()
    
    if request.method == 'POST' and form.validate():
        # Crear usuario con los datos del formulario
        user = UserService.create_user(
            name=form.name.data,
            email=form.email.data,
            phone=form.phone.data
        )
        
        # Crear pago pendiente (importe = precio del curso individual)
        payment = PaymentService.create_payment(user.id, course.id, course.price)
        
        return redirect(url_for('payment.process_payment', payment_id=payment.id))
    
    return render_template('payment/buy.html', course=course, form=form)

@bp.route('/process/<int:payment_id>')
def process_payment(payment_id):
    """Página de procesamiento de pago con Redsys"""
    payment = PaymentService.get_payment_by_id(payment_id)
    
    if not payment:
        flash('Pago no encontrado.', 'error')
        return redirect(url_for('main.index'))
    
    if payment.status == 'completed':
        flash('Este pago ya ha sido completado.', 'info')
        return redirect(url_for('payment.success', payment_id=payment_id))
    
    user = UserService.get_user_by_id(payment.user_id)
    course = CourseService.get_course_by_id(payment.course_id) if payment.course_id else None
    
    # Verificar configuración de Redsys
    redsys_config = RedsysService.get_config()
    
    # Verificar si está configurado correctamente
    if not redsys_config or not redsys_config.merchant_code or not redsys_config.secret_key:
        flash('La pasarela de pago no está configurada correctamente. Por favor, contacte con el administrador.', 'error')
        return redirect(url_for('main.index'))
    
    # Generar formulario de pago para Redsys
    course_title = course.title if course else "Pack de cursos Chiangmai Academy"
    payment_form_data = RedsysService.create_payment_form(
        payment_id=payment_id,
        course_title=course_title,
        amount=payment.amount
    )
    
    if not payment_form_data:
        flash('Error al generar el formulario de pago.', 'error')
        return redirect(url_for('main.index'))
    
    # Debug: loguear parámetros para verificar
    mp = payment_form_data['Ds_MerchantParameters']
    sig = payment_form_data['Ds_Signature']
    print(f"[Redsys] MP raw: {mp}", flush=True)
    print(f"[Redsys] SIG raw: {sig}", flush=True)
    
    # Decodificar y verificar contenido
    try:
        decoded = RedsysService.decode_merchant_parameters(mp)
        print(f"[Redsys] MP decoded: {decoded}", flush=True)
    except Exception as e:
        print(f"[Redsys] Error decodificando MP: {e}", flush=True)
    
    return render_template('payment/process_redsys.html',
                           payment=payment,
                           user=user,
                           course=course,
                           payment_form=payment_form_data,
                           config=redsys_config)


@bp.route('/cart', methods=['GET', 'POST'])
def cart_checkout():
    """
    Checkout para varios cursos seleccionados desde la sección emergente.
    Los IDs de curso llegan en el parámetro "ids" separados por comas.
    """
    ids_param = request.args.get('ids') if request.method == 'GET' else request.form.get('course_ids')
    if not ids_param:
        flash('No se han seleccionado cursos para el pago.', 'error')
        return redirect(url_for('main.index'))

    try:
        course_ids = [int(x) for x in ids_param.split(',') if x.strip()]
    except ValueError:
        flash('Selección de cursos no válida.', 'error')
        return redirect(url_for('main.index'))

    courses = CourseService.get_courses_by_ids(course_ids)
    if not courses:
        flash('No se han encontrado cursos válidos para el pago.', 'error')
        return redirect(url_for('main.index'))

    # Asumimos que todos los cursos tienen el mismo precio base.
    unit_price = courses[0].price
    offers = OfferService.get_active_offers()
    calc = OfferService.calculate_total_with_offers(len(courses), unit_price, offers)
    total_amount = calc["total"]

    form = PurchaseForm()

    if request.method == 'POST' and form.validate():
        # Crear usuario
        user = UserService.create_user(
            name=form.name.data,
            email=form.email.data,
            phone=form.phone.data
        )

        # Creamos un pago genérico de pack: guardamos el primer curso solo como referencia.
        main_course_id = courses[0].id if courses else None
        payment = PaymentService.create_payment(user.id, main_course_id, total_amount)

        # En un futuro se podría guardar el detalle de cursos del pack en otra tabla.
        return redirect(url_for('payment.process_payment', payment_id=payment.id))

    return render_template(
        'payment/cart_buy.html',
        courses=courses,
        total_amount=total_amount,
        form=form,
    )

# ========== RUTAS DE REDSYS ==========

@bp.route('/redsys/notification', methods=['POST'])
def redsys_notification():
    """
    Recibe la notificación de Redsys después del pago
    Esta ruta debe ser accesible públicamente (sin autenticación)
    """
    try:
        payload = request.form.to_dict()
        print(f"[Redsys] POST /notification payload: {payload} | IP={request.remote_addr}", flush=True)
        merchant_params = request.form.get('Ds_MerchantParameters', '')
        signature = request.form.get('Ds_Signature', '')
        
        if not merchant_params or not signature:
            print("[Redsys] Notificación sin parámetros obligatorios.", flush=True)
            return jsonify({'error': 'Parámetros faltantes'}), 400
        
        # Procesar notificación
        result = RedsysService.process_notification(merchant_params, signature)
        print(f"[Redsys] Resultado notificación: {result}", flush=True)
        
        if result.get('success'):
            # Pago exitoso
            return jsonify({'status': 'ok'}), 200
        else:
            # Error en el pago
            return jsonify({'status': 'error', 'message': result.get('error')}), 200
            
    except Exception as e:
        print(f"[Redsys] Error general en /notification: {e}", flush=True)
        return jsonify({'error': str(e)}), 500

@bp.route('/redsys/ok')
def redsys_ok():
    """Página de éxito después del pago en Redsys"""
    # Obtener parámetros de la URL si están disponibles
    merchant_params = request.args.get('Ds_MerchantParameters', '')
    
    if merchant_params:
        try:
            params = RedsysService.decode_merchant_parameters(merchant_params)
            order_id = params.get('Ds_Order', '').lstrip('0')
            payment_id = int(order_id) if order_id else None
            
            if payment_id:
                payment = PaymentService.get_payment_by_id(payment_id)
                if payment and payment.status == 'completed':
                    user = UserService.get_user_by_id(payment.user_id)
                    course = CourseService.get_course_by_id(payment.course_id)
                    flash('¡Pago completado exitosamente! Tu inscripción está confirmada.', 'success')
                    return redirect(url_for('payment.success', payment_id=payment_id))
        except:
            pass
    
    flash('Pago procesado correctamente.', 'success')
    return redirect(url_for('main.index'))

@bp.route('/redsys/ko')
def redsys_ko():
    """Página de error después del pago en Redsys"""
    merchant_params = request.args.get('Ds_MerchantParameters', '')
    
    if merchant_params:
        try:
            params = RedsysService.decode_merchant_parameters(merchant_params)
            order_id = params.get('Ds_Order', '').lstrip('0')
            response_code = params.get('Ds_Response', '')
            payment_id = int(order_id) if order_id else None
            
            if payment_id:
                payment = PaymentService.get_payment_by_id(payment_id)
                if payment:
                    payment.status = 'failed'
                    from extensions import db
                    db.session.commit()
        except:
            pass
    
    flash('El pago no se pudo completar. Por favor, inténtelo de nuevo o contacte con nosotros.', 'error')
    return redirect(url_for('main.index'))


@bp.route('/success/<int:payment_id>')
def success(payment_id):
    """Página de confirmación de pago exitoso"""
    payment = PaymentService.get_payment_by_id(payment_id)
    
    if not payment:
        flash('Pago no encontrado.', 'error')
        return redirect(url_for('main.index'))
    
    user = UserService.get_user_by_id(payment.user_id)
    course = CourseService.get_course_by_id(payment.course_id)
    
    return render_template('payment/success.html', payment=payment, user=user, course=course)
