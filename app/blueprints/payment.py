from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from app.services.payment_service import PaymentService
from app.services.user_service import UserService

payment_bp = Blueprint('payment', __name__)

@payment_bp.route('/process/<int:payment_id>')
def process_payment(payment_id):
    """Página de procesamiento de pago"""
    payment = PaymentService.get_payment_by_id(payment_id)
    
    if not payment:
        flash('Pago no encontrado.', 'error')
        return redirect(url_for('main.index'))
    
    if payment.status == 'completed':
        flash('Este pago ya ha sido completado.', 'info')
        return redirect(url_for('main.index'))
    
    user = UserService.get_user_by_id(payment.user_id)
    course_price = PaymentService.get_course_price()
    
    return render_template('payment/process.html', 
                         payment=payment, 
                         user=user, 
                         course_price=course_price)

@payment_bp.route('/complete/<int:payment_id>', methods=['POST'])
def complete_payment(payment_id):
    """Completa el pago (simulado)"""
    payment = PaymentService.get_payment_by_id(payment_id)
    
    if not payment:
        flash('Pago no encontrado.', 'error')
        return redirect(url_for('main.index'))
    
    if payment.status == 'completed':
        flash('Este pago ya ha sido completado.', 'info')
        return redirect(url_for('main.index'))
    
    # Simular procesamiento de pago
    # En producción, aquí se integraría con una pasarela de pagos real
    payment_method = request.form.get('payment_method', 'card')
    transaction_id = f"TXN-{payment_id}-{payment.user_id}"
    
    PaymentService.complete_payment(payment_id, transaction_id, payment_method)
    
    flash('¡Pago completado exitosamente! Tu inscripción está confirmada.', 'success')
    return redirect(url_for('payment.success', payment_id=payment_id))

@payment_bp.route('/success/<int:payment_id>')
def success(payment_id):
    """Página de confirmación de pago exitoso"""
    payment = PaymentService.get_payment_by_id(payment_id)
    
    if not payment:
        flash('Pago no encontrado.', 'error')
        return redirect(url_for('main.index'))
    
    user = UserService.get_user_by_id(payment.user_id)
    
    return render_template('payment/success.html', payment=payment, user=user)


