"""
Cliente para la API de WhatsApp Business.

Este módulo proporciona una clase para interactuar con la API de WhatsApp Business
y funciones de utilidad para enviar mensajes.
"""

import os
import json
import logging
import aiohttp
import asyncio
from dotenv import load_dotenv

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("whatsapp_client")

# Cargar variables de entorno
load_dotenv()

class WhatsAppClient:
    """
    Cliente para interactuar con la API de WhatsApp Business.
    
    Attributes:
        client_id: ID de cliente de WhatsApp Business
        client_secret: Clave secreta de WhatsApp Business
        access_token: Token de acceso para la API
        phone_number_id: ID del número de teléfono de WhatsApp Business
        api_version: Versión de la API de WhatsApp
    """
    
    def __init__(self, phone_number_id=None, api_version=None, access_token=None):
        """
        Inicializa el cliente de WhatsApp.
        
        Args:
            phone_number_id: ID del número de teléfono de WhatsApp Business (opcional)
            api_version: Versión de la API de WhatsApp (opcional)
            access_token: Token de acceso para la API (opcional)
        """
        self.client_id = os.environ.get("WHATSAPP_CLIENT_ID")
        self.client_secret = os.environ.get("WHATSAPP_CLIENT_SECRET")
        self.phone_number_id = phone_number_id or os.environ.get("WHATSAPP_PHONE_NUMBER_ID")
        self.api_version = api_version or os.environ.get("WHATSAPP_API_VERSION", "v22.0")
        self.access_token = access_token or os.environ.get("WHATSAPP_ACCESS_TOKEN")
        
        if not self.client_id or not self.client_secret:
            raise ValueError("WHATSAPP_CLIENT_ID y WHATSAPP_CLIENT_SECRET deben estar configurados en .env")
            
        if not self.phone_number_id:
            raise ValueError("WHATSAPP_PHONE_NUMBER_ID debe estar configurado en .env o proporcionado al instanciar")
        
        logger.info(f"Cliente de WhatsApp inicializado con la API versión {self.api_version}")
        logger.info(f"Usando ID de teléfono: {self.phone_number_id}")
        logger.info(f"Token de acceso disponible: {'Sí' if self.access_token else 'No'}")
    
    async def send_message(self, to_phone_number, message_text=None, template_name="hello_world"):
        """
        Envía un mensaje de texto o usando una plantilla a través de WhatsApp.
        
        Args:
            to_phone_number: Número de teléfono del destinatario (con código de país)
            message_text: Texto del mensaje a enviar (opcional, si se proporciona se enviará como texto)
            template_name: Nombre de la plantilla a usar (por defecto "hello_world")
            
        Returns:
            dict: La respuesta de la API de WhatsApp
        """
        # Asegurarse de que el número de teléfono del destinatario tenga el formato correcto
        if to_phone_number.startswith("+"):
            to_phone_number = to_phone_number[1:]
            
        # Construir la URL de la API
        url = f"https://graph.facebook.com/{self.api_version}/{self.phone_number_id}/messages"
        
        # Preparar el payload según el tipo de mensaje
        if message_text:
            # Mensaje de texto
            payload = {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": to_phone_number,
                "type": "text",
                "text": {"body": message_text}
            }
        else:
            # Mensaje con plantilla
            payload = {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": to_phone_number,
                "type": "template",
                "template": {
                    "name": template_name,
                    "language": {"code": "es"}
                }
            }
        
        # Si no hay token de acceso, mostrar solo el ejemplo
        if not self.access_token:
            logger.warning("No se ha configurado un token de acceso en el código.")
            logger.warning("Para enviar mensajes reales necesitas:")
            logger.warning("1. Obtener un token de acceso desde la consola de desarrolladores de Meta")
            logger.warning("2. Usar ese token en la solicitud con el header 'Authorization: Bearer <access_token>'")
            logger.warning(f"3. Enviar una solicitud POST a: {url}")
            
            logger.info("Ejemplo de comando curl:")
            logger.info(f"""
            curl -X POST \\
              '{url}' \\
              -H 'Authorization: Bearer <TU_TOKEN_DE_ACCESO>' \\
              -H 'Content-Type: application/json' \\
              -d '{json.dumps(payload)}'
            """)
            
            return {
                "success": False,
                "message": "Este es solo un ejemplo. Necesitas configurar un token de acceso válido para enviar mensajes reales.",
                "url": url,
                "payload": payload
            }
        
        # Si hay token de acceso, enviar el mensaje real
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.access_token}"
        }
        
        try:
            # Enviar la solicitud a la API
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers) as response:
                    response_text = await response.text()
                    try:
                        response_data = json.loads(response_text)
                    except:
                        response_data = {"text": response_text}
                    
                    if response.status == 200:
                        logger.info(f"Mensaje enviado correctamente: {response_data}")
                        return {"success": True, "data": response_data}
                    else:
                        logger.error(f"Error al enviar mensaje: {response.status} - {response_text}")
                        return {"success": False, "error": f"Error {response.status}", "data": response_data}
        except Exception as e:
            logger.error(f"Error al enviar mensaje: {str(e)}")
            return {"success": False, "error": str(e)}


# Función de utilidad para enviar mensajes sin necesidad de instanciar la clase
async def send_whatsapp_message(to_phone_number, message_text=None, phone_number_id=None, template_name="hello_world", access_token=None):
    """
    Función de utilidad para enviar un mensaje de WhatsApp.
    
    Args:
        to_phone_number: Número de teléfono del destinatario (con código de país)
        message_text: Texto del mensaje a enviar (opcional)
        phone_number_id: ID del número de teléfono de WhatsApp Business (opcional)
        template_name: Nombre de la plantilla a usar si no se proporciona message_text
        access_token: Token de acceso para la API (opcional)
        
    Returns:
        dict: La respuesta de la API de WhatsApp
    """
    # Forzar recarga del archivo .env para asegurar que tenemos el token más reciente
    # Solo si no se proporcionó un token específico
    if not access_token:
        try:
            # Recargar variables de entorno para asegurar token actualizado
            load_dotenv(override=True)
            # Obtener el token recargado
            access_token = os.environ.get("WHATSAPP_ACCESS_TOKEN")
            token_preview = f"{access_token[:5]}...{access_token[-5:]}" if access_token and len(access_token) > 10 else "NO TOKEN"
            logger.info(f"Token recargado desde .env: {token_preview}")
        except Exception as e:
            logger.error(f"Error al recargar variables de entorno: {str(e)}")
    
    client = WhatsAppClient(phone_number_id=phone_number_id, access_token=access_token)
    return await client.send_message(to_phone_number, message_text, template_name)


# Función para uso desde línea de comandos
async def main():
    """
    Función principal para probar el cliente de WhatsApp desde la línea de comandos.
    """
    import sys
    
    if len(sys.argv) < 2:
        print("Uso: python whatsapp_client.py <número_teléfono> [mensaje]")
        print("Ejemplo: python whatsapp_client.py +56957597102 'Hola, esto es una prueba'")
        return
    
    phone_number = sys.argv[1]
    message = sys.argv[2] if len(sys.argv) > 2 else None
    
    result = await send_whatsapp_message(phone_number, message)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    asyncio.run(main()) 