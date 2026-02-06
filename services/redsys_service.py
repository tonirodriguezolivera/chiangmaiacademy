# services/redsys_service.py
import base64
import hashlib
import hmac
from datetime import datetime
from flask import url_for, request
from Crypto.Cipher import DES3
from Crypto.Util.Padding import pad
from services.payment_gateway_service import PaymentGatewayService
from services.payment_service import PaymentService
from models import Payment

class RedsysService:
    """Servicio para integrar pagos con Redsys"""
    
    @staticmethod
    def get_config():
        """Obtiene la configuración de Redsys"""
        config = PaymentGatewayService.get_config()
        if not config or config.gateway_name != 'redsys':
            return None
        return config
    
    
    @staticmethod
    def generate_merchant_parameters(payment_id, amount, order_id, description, merchant_code, terminal, currency='978'):
        """
        Genera los parámetros del comercio para Redsys
        currency: 978 = EUR, 840 = USD, etc.
        """
        from flask import current_app
        
        # Validar amount
        if not amount or amount <= 0:
            raise ValueError("El monto debe ser mayor a 0")
        
        # Obtener URL base para las URLs de retorno
        base_url = request.url_root.rstrip('/')
        
        # Parámetros del comercio (todos los campos requeridos)
        # IMPORTANTE: Los nombres deben ser en mayúsculas según documentación Redsys
        merchant_params = {
            'DS_MERCHANT_AMOUNT': str(int(round(amount * 100))),  # Monto en céntimos
            'DS_MERCHANT_ORDER': str(order_id).zfill(12),  # Número de pedido (12 dígitos)
            'DS_MERCHANT_MERCHANTCODE': str(merchant_code),  # Código de comercio
            'DS_MERCHANT_CURRENCY': str(currency),
            'DS_MERCHANT_TRANSACTIONTYPE': '0',  # 0 = Autorización
            'DS_MERCHANT_TERMINAL': str(terminal).zfill(3),  # Terminal (3 dígitos)
            'DS_MERCHANT_MERCHANTURL': f'{base_url}/payment/redsys/notification',
            'DS_MERCHANT_URLOK': f'{base_url}/payment/redsys/ok',
            'DS_MERCHANT_URLKO': f'{base_url}/payment/redsys/ko',
            'DS_MERCHANT_PRODUCTDESCRIPTION': description[:125] if description else 'Curso',  # Máximo 125 caracteres
            'DS_MERCHANT_MERCHANTNAME': 'Chiangmai Academy'
        }
        
        return merchant_params
    
    @staticmethod
    def encode_merchant_parameters(params):
        """Codifica los parámetros del comercio en Base64 normal (según documentación Redsys)"""
        import json
        # Eliminar campos vacíos y asegurar que todos los valores sean strings
        clean_params = {k: str(v) for k, v in params.items() if v is not None and v != ''}
        # JSON sin espacios y sin ensure_ascii para mantener caracteres especiales
        json_str = json.dumps(clean_params, separators=(',', ':'), ensure_ascii=False)
        # Base64 NORMAL (con +, / y =) - NO Base64URL
        encoded = base64.b64encode(json_str.encode('utf-8')).decode('utf-8')
        return encoded
    
    @staticmethod
    def decode_merchant_parameters(encoded_params):
        """Decodifica los parámetros del comercio desde Base64 normal"""
        import json
        decoded = base64.b64decode(encoded_params.encode('utf-8')).decode('utf-8')
        return json.loads(decoded)
    
    @staticmethod
    def _zero_pad_8(data):
        """Redsys: padding con 0x00 hasta múltiplo de 8"""
        pad_len = (8 - (len(data) % 8)) % 8
        return data + (b'\x00' * pad_len)
    
    @staticmethod
    def _derive_hmac_key(secret_key_b64, order_id):
        """
        Deriva la clave HMAC usando 3DES según especificación Redsys HMAC_SHA512_V2
        Usa zero padding (no ISO7816) como requiere Redsys
        """
        # Clave del comercio viene en Base64
        key = base64.b64decode(secret_key_b64)
        # Ajustar paridad de la clave (importante para 3DES)
        key = base64.b64decode(secret_key_b64)
        
        # order_id en bytes y padding con zero padding
        order_bytes = order_id.encode('utf-8')
        order_padded = RedsysService._zero_pad_8(order_bytes)
        
        # 3DES CBC con IV=0
        iv = b'\x00' * 8
        cipher = DES3.new(key, DES3.MODE_CBC, iv=iv)
        derived_key = cipher.encrypt(order_padded)
        
        return derived_key
    
    @staticmethod
    def generate_signature(merchant_params_encoded, order_id, secret_key):
        """
        Genera la firma para Redsys usando HMAC_SHA512_V2 (según documentación oficial)
        Proceso: 3DES(order_id, secret_key) -> HMAC_SHA512(derived_key, merchant_params)
        """
        # Derivar clave usando 3DES
        derived_key = RedsysService._derive_hmac_key(secret_key, order_id)
        
        # Calcular HMAC SHA512 con la clave derivada
        mac = hmac.new(
            derived_key,
            merchant_params_encoded.encode('utf-8'),
            hashlib.sha512
        ).digest()
        
        # Codificar en Base64 NORMAL (con +, / y =)
        signature_encoded = base64.b64encode(mac).decode('utf-8')
        
        return signature_encoded
    
    @staticmethod
    def verify_signature(merchant_params_encoded, order_id, received_signature, secret_key):
        """Verifica la firma recibida de Redsys usando HMAC_SHA512_V2"""
        expected = RedsysService.generate_signature(merchant_params_encoded, order_id, secret_key)
        # Comparación segura para evitar timing attacks
        return hmac.compare_digest(expected, received_signature)
    
    @staticmethod
    def create_payment_form(payment_id, course_title, amount):
        """
        Crea el formulario de pago para Redsys
        Retorna un diccionario con los datos del formulario
        """
        config = RedsysService.get_config()
        if not config:
            print("ERROR: No se encontró configuración de Redsys")
            return None
        
        # Debug: verificar qué se está leyendo
        print(f"CONFIG REDSYS - ID: {config.id}, MerchantCode: {config.merchant_code}, Terminal: {config.terminal}, SecretKey: {'Configurada' if config.secret_key else 'VACÍA'}")
        
        # Validar configuración
        if not config.merchant_code or not config.terminal:
            print(f"ERROR: Configuración incompleta - MerchantCode: {config.merchant_code}, Terminal: {config.terminal}")
            return None
        
        # Validar amount
        if not amount or amount <= 0:
            return None
        
        # Generar número de pedido único (12 dígitos)
        order_id = str(payment_id).zfill(12)
        
        # Generar parámetros del comercio (con merchant_code y terminal incluidos)
        merchant_params = RedsysService.generate_merchant_parameters(
            payment_id=payment_id,
            amount=amount,
            order_id=order_id,
            description=course_title or 'Curso',
            merchant_code=config.merchant_code,
            terminal=config.terminal,
            currency='978'  # EUR
        )
        
        # Codificar parámetros
        merchant_params_encoded = RedsysService.encode_merchant_parameters(merchant_params)
        
        # Generar firma
        signature = RedsysService.generate_signature(
            merchant_params_encoded,
            order_id,
            config.secret_key
        )
        
        # Obtener URL de Redsys
        redsys_url = config.get_redsys_url()
        
        return {
            'redsys_url': redsys_url,
            'Ds_SignatureVersion': 'HMAC_SHA512_V2',
            'Ds_MerchantParameters': merchant_params_encoded,
            'Ds_Signature': signature
        }
    
    @staticmethod
    def process_notification(merchant_params_encoded, signature):
        """
        Procesa la notificación recibida de Redsys
        Retorna un diccionario con el resultado
        """
        config = RedsysService.get_config()
        if not config:
            return {'error': 'Configuración de Redsys no encontrada'}
        
        try:
            # Decodificar parámetros
            params = RedsysService.decode_merchant_parameters(merchant_params_encoded)
            
            # Extraer datos importantes
            order_id = params.get('Ds_Order', '')
            response_code = params.get('Ds_Response', '')
            amount = params.get('Ds_Amount', '0')
            
            # Verificar firma
            if not RedsysService.verify_signature(
                merchant_params_encoded,
                order_id,
                signature,
                config.secret_key
            ):
                return {'error': 'Firma inválida'}
            
            # Convertir código de respuesta
            # 0-99 = Transacción autorizada
            # 100+ = Error
            response_code_int = int(response_code) if response_code.isdigit() else 999
            
            # Obtener payment_id del order_id (eliminar ceros a la izquierda)
            payment_id = int(order_id.lstrip('0')) if order_id.lstrip('0') else 0
            
            if response_code_int < 100:
                # Pago autorizado
                payment = PaymentService.get_payment_by_id(payment_id)
                if payment and payment.status != 'completed':
                    PaymentService.complete_payment(
                        payment_id,
                        transaction_id=order_id,
                        payment_method='redsys'
                    )
                    return {
                        'success': True,
                        'payment_id': payment_id,
                        'order_id': order_id,
                        'amount': float(amount) / 100
                    }
                return {'error': 'Pago ya procesado o no encontrado'}
            else:
                # Error en el pago
                payment = PaymentService.get_payment_by_id(payment_id)
                if payment:
                    payment.status = 'failed'
                    from extensions import db
                    db.session.commit()
                return {
                    'success': False,
                    'error': f'Error en el pago. Código: {response_code}',
                    'payment_id': payment_id
                }
                
        except Exception as e:
            return {'error': f'Error procesando notificación: {str(e)}'}

