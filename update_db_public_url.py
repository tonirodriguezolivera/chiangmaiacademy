# update_db_public_url.py
# Script para añadir el campo public_base_url a la tabla payment_gateway_config
import sys
import sqlite3
import os

# Configurar encoding UTF-8 para la salida
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

def update_payment_gateway_table():
    """Añade el campo public_base_url a la tabla payment_gateway_config"""
    db_path = os.path.join('instance', 'thai_massage_school.db')
    
    if not os.path.exists(db_path):
        print(f"❌ Error: No se encontró la base de datos en {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Verificar si la columna ya existe
        cursor.execute("PRAGMA table_info(payment_gateway_config)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'public_base_url' in columns:
            print("✅ La columna 'public_base_url' ya existe en la tabla.")
            conn.close()
            return True
        
        # Añadir la nueva columna
        print("🔄 Añadiendo columna 'public_base_url' a payment_gateway_config...")
        cursor.execute("""
            ALTER TABLE payment_gateway_config
            ADD COLUMN public_base_url TEXT
        """)
        
        conn.commit()
        print("✅ Columna 'public_base_url' añadida exitosamente.")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == '__main__':
    print("🔄 Actualizando base de datos para añadir campo public_base_url...\n")
    update_payment_gateway_table()



