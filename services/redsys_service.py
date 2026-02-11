# services/redsys_service.py
import base64
import binascii
import hashlib
import hmac
import json
import time
from datetime import datetime
from flask import url_for, request
from Crypto.Cipher import DES3
from services.payment_gateway_service import PaymentGatewayService
from services.payment_service import PaymentService
from models import Payment

class RedsysService:
    """Servicio para integrar pagos con Redsys corregido para evitar SIS0051"""
    
    @staticmethod
    def get_config():
        """Obtiene la configuración activa de Redsys"""
        config = PaymentGatewayService.get_config()
        if not config or config.gateway_name != 'redsys':
            return None
        return config

    @staticmethod
    def generate_merchant_parameters(payment_id, amount, order_id, description, merchant_code, terminal, currency='978', public_base_url=None):
        """Genera el diccionario de parámetros del comercio"""
        if not amount or amount <= 0:
            raise ValueError("El monto debe ser mayor a 0")
        
        if public_base_url:
            base_url = public_base_url.rstrip('/')
        else:
            base_url = request.url_root.rstrip('/')
        
        notification_url = f'{base_url}/payment/redsys/notification'
        url_ok = f'{base_url}/payment/redsys/ok'
        url_ko = f'{base_url}/payment/redsys/ko'
        
        merchant_params = {
            'DS_MERCHANT_AMOUNT': str(int(round(amount * 100))),
            'DS_MERCHANT_ORDER': str(order_id),
            'DS_MERCHANT_MERCHANTCODE': str(merchant_code),
            'DS_MERCHANT_CURRENCY': str(currency),
            'DS_MERCHANT_TRANSACTIONTYPE': '0',
            'DS_MERCHANT_TERMINAL': str(terminal).zfill(3),
            'DS_MERCHANT_MERCHANTURL': notification_url,
            'DS_MERCHANT_URLOK': url_ok,
            'DS_MERCHANT_URLKO': url_ko,
            'DS_MERCHANT_PRODUCTDESCRIPTION': (description[:125] if description else 'Curso'),
            'DS_MERCHANT_MERCHANTNAME': 'Chiangmai Academy'
        }
        
        return merchant_params

    @staticmethod
    def encode_merchant_parameters(params):
        """Codifica los parámetros en Base64 con claves ordenadas"""
        clean_params = {k: str(v) for k, v in params.items() if v is not None and v != ''}
        # sort_keys=True es vital para que la firma no falle nunca
        json_str = json.dumps(clean_params, separators=(',', ':'), ensure_ascii=False, sort_keys=True)
        return base64.b64encode(json_str.encode('utf-8')).decode('utf-8')

    @staticmethod
    def decode_merchant_parameters(encoded_params):
        """Decodifica los parámetros desde Base64"""
        decoded = base64.b64decode(encoded_params.encode('utf-8')).decode('utf-8')
        return json.loads(decoded)

    @staticmethod
    def _derive_hmac_key(secret_key_b64, order_id):
        """Deriva la clave HMAC usando 3DES"""
        try:
            secret_key_b64 = secret_key_b64.strip()
            key = base64.b64decode(secret_key_b64)
            key = DES3.adjust_key_parity(key)
            
            order_bytes = order_id.encode('utf-8')
            pad_len = (8 - (len(order_bytes) % 8)) % 8
            order_padded = order_bytes + (b'\x00' * pad_len)
            
            iv = b'\x00' * 8
            cipher = DES3.new(key, DES3.MODE_CBC, iv=iv)
            return cipher.encrypt(order_padded)
        except Exception as e:
            print(f"ERROR en _derive_hmac_key: {e}")
            raise

    @staticmethod
    def generate_signature(merchant_params_encoded, order_id, secret_key):
        """Genera la firma HMAC_SHA256"""
        try:
            derived_key = RedsysService._derive_hmac_key(secret_key, order_id)
            mac = hmac.new(
                derived_key,
                merchant_params_encoded.encode('utf-8'),
                hashlib.sha256
            ).digest()
            return base64.b64encode(mac).decode('utf-8')
        except Exception as e:
            print(f"ERROR en generate_signature: {e}")
            raise

    @staticmethod
    def verify_signature(merchant_params_encoded, order_id, received_signature, secret_key):
        """Verifica la firma de Redsys"""
        expected = RedsysService.generate_signature(merchant_params_encoded, order_id, secret_key)
        return hmac.compare_digest(expected, received_signature)

    @staticmethod
    def create_payment_form(payment_id, course_title, amount):
        """Crea el formulario de pago con OrderID único para evitar SIS0051"""
        config = RedsysService.get_config()
        if not config or not config.merchant_code or not config.secret_key:
            return None

        # --- SOLUCIÓN PARA SIS0051 (Número repetido en entorno compartido) ---
        # Si estamos en test, creamos un número de pedido basado en el tiempo
        # para no chocar con otros desarrolladores que usen el código 999008881.
        # Formato: [Día][Hora][Minuto][ID_Pago] limitado a 12 caracteres.
        if config.environment == 'test':
            prefix = datetime.now().strftime('%d%H%M') # Ejemplo: 111430 (Día 11, 14:30h)
            # Concatenamos y cogemos los últimos 12 caracteres para cumplir la norma de Redsys
            order_id = (prefix + str(payment_id))[-12:].zfill(12)
        else:
            # En producción usamos el ID normal con ceros a la izquierda
            order_id = str(payment_id).zfill(12)

        merchant_params = RedsysService.generate_merchant_parameters(
            payment_id=payment_id,
            amount=amount,
            order_id=order_id,
            description=course_title,
            merchant_code=config.merchant_code,
            terminal=config.terminal,
            public_base_url=config.public_base_url
        )

        merchant_params_encoded = RedsysService.encode_merchant_parameters(merchant_params)
        signature = RedsysService.generate_signature(merchant_params_encoded, order_id, config.secret_key)

        print(f"\n>>> DEBUG SIS0051: Enviando OrderID '{order_id}' para el Pago ID {payment_id}")

        return {
            'redsys_url': config.get_redsys_url(),
            'Ds_SignatureVersion': 'HMAC_SHA256_V1',
            'Ds_MerchantParameters': merchant_params_encoded,
            'Ds_Signature': signature
        }

    @staticmethod
    def process_notification(merchant_params_encoded, signature):
        """Procesa la notificación y recupera el ID original del pago"""
        config = RedsysService.get_config()
        if not config: return {'error': 'Configuración no encontrada'}

        try:
            params = RedsysService.decode_merchant_parameters(merchant_params_encoded)
            order_id = params.get('Ds_Order') or params.get('DS_MERCHANT_ORDER')
            
            if not RedsysService.verify_signature(merchant_params_encoded, order_id, signature, config.secret_key):
                return {'error': 'Firma inválida'}

            response_code = params.get('Ds_Response', '999')
            response_code_int = int(response_code)

            # Intentamos buscar el pago. Primero por el OrderID completo
            # Si falla, es que usamos el prefijo de TEST, así que lo buscamos por ID de base de datos
            # En Test, el ID real suele estar al final del OrderID.
            
            # 1. Intentar buscar pago directamente (caso producción)
            payment_id_raw = int(order_id.lstrip('0'))
            payment = PaymentService.get_payment_by_id(payment_id_raw)
            
            # 2. Si no existe, es que es un ID con prefijo de TEST
            if not payment and config.environment == 'test':
                # Buscamos el pago que coincida con este OrderID en el campo transaction_id o similar
                # O simplemente intentamos extraer los últimos dígitos del pedido
                # Para simplificar, recorremos los últimos dígitos:
                for i in range(1, 7): # Probamos los últimos 1 a 6 dígitos
                    try:
                        potential_id = int(order_id[-i:])
                        payment = PaymentService.get_payment_by_id(potential_id)
                        if payment: break
                    except: continue

            if response_code_int < 100 and payment:
                PaymentService.complete_payment(payment.id, transaction_id=order_id, payment_method='redsys')
                return {'success': True, 'payment_id': payment.id}
            
            return {'success': False, 'error': f'Pago denegado o pedido no encontrado', 'payment_id': order_id}
        except Exception as e:
            return {'error': f'Error procesando notificación: {str(e)}'}