# check_redsys_config.py
# Script para verificar y actualizar la configuración de RedSys con datos de prueba
import sys
import sqlite3
import os

# Configurar encoding UTF-8 para la salida
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

def check_redsys_config():
    """Verifica la configuración actual de RedSys"""
    db_path = os.path.join('instance', 'thai_massage_school.db')
    
    if not os.path.exists(db_path):
        print(f"❌ Error: No se encontró la base de datos en {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Verificar configuración actual
        cursor.execute("""
            SELECT id, gateway_name, merchant_code, terminal, secret_key, environment, is_active
            FROM payment_gateway_config
            WHERE gateway_name = 'redsys'
            ORDER BY id DESC
            LIMIT 1
        """)
        
        config = cursor.fetchone()
        
        if config:
            config_id, gateway_name, merchant_code, terminal, secret_key, environment, is_active = config
            print("📋 Configuración actual de RedSys:")
            print(f"   ID: {config_id}")
            print(f"   Gateway: {gateway_name}")
            print(f"   Código de Comercio: {merchant_code if merchant_code else '❌ NO CONFIGURADO'}")
            print(f"   Terminal: {terminal if terminal else '❌ NO CONFIGURADO'}")
            print(f"   Clave Secreta: {'✅ Configurada' if secret_key else '❌ NO CONFIGURADA'}")
            print(f"   Entorno: {environment if environment else '❌ NO CONFIGURADO'}")
            print(f"   Activa: {'✅ Sí' if is_active else '❌ No'}")
            
            # Verificar si usa datos de prueba
            test_merchant_code = '999008881'
            test_terminal = '001'
            test_secret_key = 'sq7HjrUOBfKmC576ILgskD5srU870gJ7'
            
            is_test_config = (
                merchant_code == test_merchant_code and
                terminal == test_terminal and
                secret_key == test_secret_key and
                environment == 'test'
            )
            
            if is_test_config:
                print("\n✅ La configuración usa los datos de prueba de RedSys correctamente.")
            else:
                print("\n⚠️  La configuración NO usa los datos de prueba estándar de RedSys.")
                print("\n¿Deseas actualizar con los datos de prueba? (s/n): ", end='')
                response = input().strip().lower()
                
                if response == 's':
                    cursor.execute("""
                        UPDATE payment_gateway_config
                        SET merchant_code = ?,
                            terminal = ?,
                            secret_key = ?,
                            environment = 'test',
                            is_active = 1
                        WHERE id = ?
                    """, (test_merchant_code, test_terminal, test_secret_key, config_id))
                    conn.commit()
                    print("✅ Configuración actualizada con datos de prueba de RedSys.")
                else:
                    print("❌ No se actualizó la configuración.")
        else:
            print("❌ No se encontró configuración de RedSys.")
            print("\n¿Deseas crear una configuración con datos de prueba? (s/n): ", end='')
            response = input().strip().lower()
            
            if response == 's':
                cursor.execute("""
                    INSERT INTO payment_gateway_config 
                    (gateway_name, merchant_code, terminal, secret_key, environment, is_active, created_at, updated_at)
                    VALUES ('redsys', '999008881', '001', 'sq7HjrUOBfKmC576ILgskD5srU870gJ7', 'test', 1, datetime('now'), datetime('now'))
                """)
                conn.commit()
                print("✅ Configuración de prueba creada exitosamente.")
            else:
                print("❌ No se creó la configuración.")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == '__main__':
    print("🔍 Verificando configuración de RedSys...\n")
    check_redsys_config()



