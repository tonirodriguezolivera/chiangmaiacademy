# services/course_service.py
from extensions import db
from models import Course

class CourseService:
    @staticmethod
    def create_course(title, description, price, image_filename=None):
        """Crea un nuevo curso"""
        course = Course(title=title, description=description, price=price, image_filename=image_filename)
        db.session.add(course)
        db.session.commit()
        return course
    
    @staticmethod
    def get_course_by_id(course_id):
        """Obtiene un curso por ID"""
        return Course.query.get(course_id)
    
    @staticmethod
    def get_active_courses():
        """Obtiene todos los cursos activos"""
        return Course.query.filter_by(is_active=True).order_by(Course.created_at.desc()).all()
    
    @staticmethod
    def get_all_courses():
        """Obtiene todos los cursos"""
        return Course.query.order_by(Course.created_at.desc()).all()
    
    @staticmethod
    def update_course(course_id, title=None, description=None, price=None, is_active=None, image_filename=None):
        """Actualiza un curso"""
        course = Course.query.get(course_id)
        if not course:
            return None
        
        if title is not None:
            course.title = title
        if description is not None:
            course.description = description
        if price is not None:
            course.price = price
        if is_active is not None:
            course.is_active = is_active
        if image_filename is not None:
            course.image_filename = image_filename
        
        from datetime import datetime
        course.updated_at = datetime.utcnow()
        db.session.commit()
        return course
    
    @staticmethod
    def delete_course(course_id):
        """Elimina un curso (soft delete)"""
        course = Course.query.get(course_id)
        if course:
            course.is_active = False
            from datetime import datetime
            course.updated_at = datetime.utcnow()
            db.session.commit()
        return course

