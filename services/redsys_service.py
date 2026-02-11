# services/redsys_service.py
import base64
import binascii
import hashlib
import hmac
import json
import time
from datetime import datetime
from flask import url_for, request, current_app
from Crypto.Cipher import DES3
from services.payment_gateway_service import PaymentGatewayService
from services.payment_service import PaymentService
from models import Payment
from extensions import db


def _log(message):
    """Envía los mensajes al log estándar (stdout) y, si hay app, al logger."""
    msg = str(message)
    print(msg, flush=True)
    try:
        current_app.logger.info(msg)
    except Exception:
        pass

class RedsysService:
    """
    Servicio para integrar pagos con Redsys.
    Implementa logica determinista de OrderID para evitar colisiones en BDD y errores SIS0051.
    """
    
    @staticmethod
    def get_config():
        """Obtiene la configuracion activa de Redsys"""
        config = PaymentGatewayService.get_config()
        if not config or config.gateway_name != 'redsys':
            return None
        return config

    @staticmethod
    def generate_merchant_parameters(payment_id, amount, order_id, description, merchant_code, terminal, currency='978', public_base_url=None):
        """Genera el diccionario de parametros del comercio para Redsys"""
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
        """Codifica los parametros en Base64 con claves ordenadas"""
        clean_params = {k: str(v) for k, v in params.items() if v is not None and v != ''}
        json_str = json.dumps(clean_params, separators=(',', ':'), ensure_ascii=False, sort_keys=True)
        return base64.b64encode(json_str.encode('utf-8')).decode('utf-8')

    @staticmethod
    def decode_merchant_parameters(encoded_params):
        """Decodifica los parametros desde Base64"""
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
        """Genera la firma HMAC_SHA256 necesaria para Redsys"""
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
        """Verifica que la firma recibida de Redsys sea valida"""
        expected = RedsysService.generate_signature(merchant_params_encoded, order_id, secret_key)
        if not received_signature:
            return False
        normalized = received_signature.replace('-', '+').replace('_', '/')
        # añadir padding si falta
        padding = len(normalized) % 4
        if padding:
            normalized += '=' * (4 - padding)
        return hmac.compare_digest(expected, normalized)

    @staticmethod
    def create_payment_form(payment_id, course_title, amount):
        """Crea el formulario de pago con una estructura de OrderID fija para evitar sustituciones"""
        config = RedsysService.get_config()
        if not config or not config.merchant_code or not config.secret_key:
            return None

        # ESTRUCTURA DE SEGURIDAD:
        # En test usamos: [8 digitos ID_Pago] + [4 digitos timestamp] = 12 caracteres.
        # Esto permite extraer el ID exacto sin ambiguedades y evita el error SIS0051.
        if config.environment == 'test':
            timestamp_suffix = datetime.now().strftime('%M%S') # Minuto y Segundo actual
            order_id = str(payment_id).zfill(8) + timestamp_suffix
        else:
            # En produccion usamos el ID rellenado a 12 digitos
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

        print(f"\n>>> DEBUG REDSYS: Enviando OrderID '{order_id}' para el Pago Real ID {payment_id}")

        return {
            'redsys_url': config.get_redsys_url(),
            'Ds_SignatureVersion': 'HMAC_SHA256_V1',
            'Ds_MerchantParameters': merchant_params_encoded,
            'Ds_Signature': signature
        }

    @staticmethod
    def _extract_payment_id_from_order_id(order_id, config):
        """
        Extrae el ID del pago desde el OrderID de forma determinista.
        """
        try:
            if config.environment == 'test':
                # El ID real son los primeros 8 caracteres segun nuestra nueva logica
                payment_id = int(order_id[:8])
            else:
                # En produccion es el numero completo sin ceros a la izquierda
                payment_id = int(order_id.lstrip('0'))
            
            # Busqueda directa por ID en la base de datos
            return Payment.query.get(payment_id)
        except Exception as e:
            print(f"\n>>> ERROR al extraer ID de '{order_id}': {str(e)}")
            return None

    @staticmethod
    def process_notification(merchant_params_encoded, signature):
        """Procesa la notificacion de pago confirmando que no se sobrescriban registros"""
        config = RedsysService.get_config()
        if not config: 
            return {'error': 'Configuracion no encontrada'}

        try:
            _log(f"[Redsys] Notificacion recibida. MP len={len(merchant_params_encoded)}, signature len={len(signature)}")
            params = RedsysService.decode_merchant_parameters(merchant_params_encoded)
            order_id = params.get('Ds_Order') or params.get('DS_MERCHANT_ORDER')
            _log(f"[Redsys] Merchant params decodificados: {params}")
            
            if not order_id:
                _log("[Redsys] OrderID ausente en la notificacion.")
                return {'error': 'OrderID no encontrado'}
            
            if not RedsysService.verify_signature(merchant_params_encoded, order_id, signature, config.secret_key):
                _log(f"[Redsys] Firma invalida para OrderID {order_id}")
                return {'error': 'Firma invalida'}

            response_code = int(params.get('Ds_Response', '999'))
            _log(f"[Redsys] OrderID {order_id} con Ds_Response {response_code}")

            # Extraemos el ID exacto del pago para no actualizar la fila equivocada
            payment = RedsysService._extract_payment_id_from_order_id(order_id, config)
            
            if not payment:
                print(f"\n>>> DEBUG: No se encontro el pago en la BDD para OrderID '{order_id}'")
                return {'success': False, 'error': 'Registro de pago no encontrado'}
            else:
                _log(f"[Redsys] Coincidencia Payment ID {payment.id} (status actual: {payment.status})")

            # SEGURIDAD: Si el pago ya esta completado, ignoramos para no duplicar ni sustituir
            if payment.status == 'completed':
                print(f"\n>>> DEBUG: El pago {payment.id} ya figuraba como completado. Ignorando.")
                _log(f"[Redsys] Pago {payment.id} ya estaba completado. Notificacion ignorada.")
                return {'success': True, 'payment_id': payment.id}

            if response_code < 100:
                # Marcamos el pago como completado de forma persistente
                PaymentService.complete_payment(payment.id, transaction_id=order_id, payment_method='redsys')
                print(f"\n>>> DEBUG: Pago {payment.id} verificado y guardado correctamente.")
                _log(f"[Redsys] Pago {payment.id} actualizado a completed (order {order_id}).")
                return {'success': True, 'payment_id': payment.id}
            else:
                # Si el pago ha fallado en Redsys, lo marcamos en nuestra BDD
                payment.status = 'failed'
                db.session.commit()
                print(f"\n>>> DEBUG: Pago {payment.id} marcado como fallido (Respuesta Redsys: {response_code})")
                _log(f"[Redsys] Pago {payment.id} marcado como failed (respuesta {response_code}).")
                return {'success': False, 'error': f'Pago denegado: {response_code}'}
                
        except Exception as e:
            print(f"\n>>> ERROR Crítico en process_notification: {str(e)}")
            _log(f"[Redsys] Exception en process_notification: {e}")
            return {'error': str(e)}
