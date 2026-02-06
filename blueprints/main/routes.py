# blueprints/main/routes.py
from flask import render_template, request, redirect, url_for, flash
from . import bp
from services.course_service import CourseService

@bp.route('/')
def index():
    """Landing page principal"""
    courses = CourseService.get_active_courses()
    return render_template('index.html', courses=courses)

@bp.route('/course/<int:course_id>')
def course_detail(course_id):
    """Detalle del curso y compra"""
    course = CourseService.get_course_by_id(course_id)
    
    if not course or not course.is_active:
        flash('Curso no encontrado.', 'error')
        return redirect(url_for('main.index'))
    
    return render_template('course_detail.html', course=course)

# ========== PÁGINAS LEGALES ==========

@bp.route('/aviso-legal')
def aviso_legal():
    """Aviso Legal"""
    return render_template('legal/aviso_legal.html')

@bp.route('/politica-privacidad')
def politica_privacidad():
    """Política de Privacidad"""
    return render_template('legal/politica_privacidad.html')

@bp.route('/politica-cookies')
def politica_cookies():
    """Política de Cookies"""
    return render_template('legal/politica_cookies.html')

@bp.route('/terminos-condiciones')
def terminos_condiciones():
    """Términos y Condiciones"""
    return render_template('legal/terminos_condiciones.html')

@bp.route('/politica-cancelaciones')
def politica_cancelaciones():
    """Política de Cancelaciones, Devoluciones y Matrículas"""
    return render_template('legal/politica_cancelaciones.html')
