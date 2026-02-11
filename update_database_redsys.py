# update_database_redsys.py
# Script para actualizar la base de datos con los campos de Redsys
import sys
import sqlite3
import os

# Configurar encoding UTF-8 para la salida
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

def update_payment_gateway_table():
    """Actualiza la tabla payment_gateway_config para incluir campos de Redsys"""
    db_path = os.path.join('instance', 'thai_massage_school.db')
    
    if not os.path.exists(db_path):
        print(f"❌ Error: No se encontró la base de datos en {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Obtener información de la tabla actual
        cursor.execute("PRAGMA table_info(payment_gateway_config)")
        columns = [row[1] for row in cursor.fetchall()]
        
        print("📋 Columnas actuales en payment_gateway_config:")
        for col in columns:
            print(f"   - {col}")
        
        # Campos a añadir si no existen
        new_columns = {
            'merchant_code': 'TEXT',
            'terminal': 'TEXT DEFAULT "001"',
            'environment': 'TEXT DEFAULT "test"',
            'redsys_url_test': 'TEXT',
            'redsys_url_production': 'TEXT'
        }
        
        # Eliminar columnas antiguas si existen (api_key, webhook_secret)
        columns_to_remove = ['api_key', 'webhook_secret']
        for col in columns_to_remove:
            if col in columns:
                print(f"⚠️  Nota: La columna '{col}' existe pero no se eliminará automáticamente.")
                print(f"   Puedes eliminarla manualmente si no la necesitas.")
        
        # Añadir nuevas columnas
        added_columns = []
        for col_name, col_type in new_columns.items():
            if col_name not in columns:
                try:
                    alter_sql = f"ALTER TABLE payment_gateway_config ADD COLUMN {col_name} {col_type}"
                    cursor.execute(alter_sql)
                    added_columns.append(col_name)
                    print(f"✅ Columna '{col_name}' añadida correctamente")
                except sqlite3.OperationalError as e:
                    print(f"❌ Error al añadir columna '{col_name}': {e}")
            else:
                print(f"ℹ️  La columna '{col_name}' ya existe")
        
        # Actualizar gateway_name por defecto si no está configurado
        cursor.execute("SELECT COUNT(*) FROM payment_gateway_config")
        count = cursor.fetchone()[0]
        
        if count == 0:
            # Insertar configuración por defecto
            cursor.execute("""
                INSERT INTO payment_gateway_config 
                (gateway_name, terminal, environment, is_active, created_at, updated_at)
                VALUES ('redsys', '001', 'test', 1, datetime('now'), datetime('now'))
            """)
            print("✅ Configuración por defecto de Redsys creada")
        
        conn.commit()
        conn.close()
        
        if added_columns:
            print(f"\n✅ Actualización completada. Se añadieron {len(added_columns)} columnas nuevas.")
        else:
            print("\n✅ La base de datos ya está actualizada.")
        
        return True
        
    except sqlite3.Error as e:
        print(f"❌ Error de SQLite: {e}")
        return False
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        return False

if __name__ == '__main__':
    print("🔄 Actualizando base de datos para Redsys...")
    print("=" * 60)
    
    success = update_payment_gateway_table()
    
    print("=" * 60)
    if success:
        print("✅ Proceso completado exitosamente")
    else:
        print("❌ El proceso falló. Revisa los errores arriba.")
        sys.exit(1)



