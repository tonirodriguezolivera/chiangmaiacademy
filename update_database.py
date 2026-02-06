# Script para actualizar la base de datos
import sqlite3
import os

basedir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(basedir, 'instance', 'thai_massage_school.db')

if os.path.exists(db_path):
    print("Actualizando base de datos...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Verificar si la columna course_id existe
        cursor.execute("PRAGMA table_info(payment)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'course_id' not in columns:
            print("Agregando columna course_id a la tabla payment...")
            cursor.execute("ALTER TABLE payment ADD COLUMN course_id INTEGER")
            # Crear tabla Course si no existe
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS course (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title VARCHAR(200) NOT NULL,
                    description TEXT,
                    price FLOAT NOT NULL,
                    image_filename VARCHAR(255),
                    is_active BOOLEAN DEFAULT 1,
                    created_at DATETIME,
                    updated_at DATETIME
                )
            """)
            
        # Verificar si la tabla course existe y agregar columna image_filename si no existe
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='course'")
        if cursor.fetchone():
            cursor.execute("PRAGMA table_info(course)")
            course_columns = [column[1] for column in cursor.fetchall()]
            if 'image_filename' not in course_columns:
                print("Agregando columna image_filename a la tabla course...")
                cursor.execute("ALTER TABLE course ADD COLUMN image_filename VARCHAR(255)")
                conn.commit()
            # Crear tabla payment_gateway_config si no existe
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS payment_gateway_config (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    gateway_name VARCHAR(50) NOT NULL DEFAULT 'stripe',
                    api_key VARCHAR(500),
                    secret_key VARCHAR(500),
                    webhook_secret VARCHAR(500),
                    is_active BOOLEAN DEFAULT 1,
                    created_at DATETIME,
                    updated_at DATETIME
                )
            """)
            conn.commit()
            print("Base de datos actualizada correctamente")
        else:
            print("La base de datos ya esta actualizada")
            
        # Verificar si existe la tabla course
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='course'")
        if not cursor.fetchone():
            print("Creando tabla course...")
            cursor.execute("""
                CREATE TABLE course (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title VARCHAR(200) NOT NULL,
                    description TEXT,
                    price FLOAT NOT NULL,
                    is_active BOOLEAN DEFAULT 1,
                    created_at DATETIME,
                    updated_at DATETIME
                )
            """)
            conn.commit()
            print("Tabla course creada")
            
    except Exception as e:
        print(f"Error: {e}")
        conn.rollback()
    finally:
        conn.close()
else:
    print("Base de datos no encontrada. Se creara automaticamente al iniciar la aplicacion.")

