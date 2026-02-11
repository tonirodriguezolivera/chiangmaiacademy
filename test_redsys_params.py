# test_redsys_params.py
# Script para probar la generación de parámetros de RedSys
import base64
import json

# Simular parámetros como los que se generan
merchant_params = {
    'DS_MERCHANT_AMOUNT': '30000',
    'DS_MERCHANT_ORDER': '000000000001',
    'DS_MERCHANT_MERCHANTCODE': '999008881',
    'DS_MERCHANT_CURRENCY': '978',
    'DS_MERCHANT_TRANSACTIONTYPE': '0',
    'DS_MERCHANT_TERMINAL': '001',
    'DS_MERCHANT_MERCHANTURL': 'http://localhost:5000/payment/redsys/notification',
    'DS_MERCHANT_URLOK': 'http://localhost:5000/payment/redsys/ok',
    'DS_MERCHANT_URLKO': 'http://localhost:5000/payment/redsys/ko',
    'DS_MERCHANT_PRODUCTDESCRIPTION': 'CURSO 1',
    'DS_MERCHANT_MERCHANTNAME': 'Chiangmai Academy'
}

# Codificar como lo hace el servicio
clean_params = {k: str(v) for k, v in merchant_params.items() if v is not None and v != ''}
json_str = json.dumps(clean_params, separators=(',', ':'), ensure_ascii=False, sort_keys=False)
encoded = base64.b64encode(json_str.encode('utf-8')).decode('utf-8')

print("=== PRUEBA DE PARÁMETROS REDSYS ===\n")
print("Parámetros originales:")
for k, v in merchant_params.items():
    print(f"  {k}: {v}")

print(f"\nJSON generado:")
print(json_str)

print(f"\nBase64 generado:")
print(encoded)

print(f"\nBase64 decodificado (verificación):")
decoded = base64.b64decode(encoded).decode('utf-8')
print(decoded)
print(f"\n¿Coincide con el JSON original? {decoded == json_str}")

