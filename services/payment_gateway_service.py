# services/payment_gateway_service.py
from extensions import db
from models import PaymentGatewayConfig

class PaymentGatewayService:
    @staticmethod
    def get_config():
        """Obtiene la configuración activa de la pasarela de pago"""
        config = PaymentGatewayConfig.query.filter_by(is_active=True).first()
        if config:
            print(f"DEBUG get_config - ID: {config.id}, MerchantCode: {config.merchant_code}, Terminal: {config.terminal}, Gateway: {config.gateway_name}")
        else:
            print("DEBUG get_config - No se encontró configuración activa")
        return config
    
    @staticmethod
    def update_config(gateway_name, merchant_code=None, terminal=None, secret_key=None, environment=None, public_base_url=None):
        """Actualiza o crea la configuración de la pasarela de pago (Redsys)"""
        # Desactivar todas las configuraciones existentes para asegurar solo una activa
        PaymentGatewayConfig.query.update({PaymentGatewayConfig.is_active: False})
        
        # Buscar o crear configuración
        config = PaymentGatewayConfig.query.filter_by(gateway_name=gateway_name).first()
        
        if not config:
            config = PaymentGatewayConfig(gateway_name=gateway_name)
            db.session.add(config)
        
        # Actualizar todos los campos
        config.gateway_name = gateway_name
        config.is_active = True  # Asegurar que esté activa
        
        if merchant_code is not None:
            config.merchant_code = merchant_code
        if terminal is not None:
            config.terminal = terminal
        if secret_key is not None:
            # 🔧 Limpiar la clave secreta (strip) para eliminar espacios/retornos de línea
            config.secret_key = secret_key.strip() if secret_key else None
        if environment is not None:
            config.environment = environment
        if public_base_url is not None:
            config.public_base_url = public_base_url.strip() if public_base_url else None
        
        from datetime import datetime
        config.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        # Debug: verificar qué se guardó
        print(f"DEBUG update_config - Guardado ID: {config.id}, MerchantCode: {config.merchant_code}, Terminal: {config.terminal}, PublicURL: {config.public_base_url or 'No configurada'}")
        
        return config

