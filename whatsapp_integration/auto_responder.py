"""
Script de respuesta automática para WhatsApp.

Este script inicia un servidor webhook que recibe mensajes de WhatsApp
y responde automáticamente con un mensaje predefinido.
"""

import os
import json
import asyncio
import logging
from aiohttp import web
from dotenv import load_dotenv
from whatsapp_client import send_whatsapp_message

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("whatsapp_auto")

# Cargar variables de entorno
load_dotenv()

# Configurar mensaje de respuesta automática
AUTO_REPLY_MESSAGE = "Gracias por tu mensaje. Esta es una respuesta automática del sistema."

async def verify_webhook(request):
    """
    Verifica el webhook de WhatsApp cuando Meta intenta verificarlo.
    """
    # Token de verificación definido en Meta Developer Portal
    verify_token = os.environ.get("WHATSAPP_VERIFY_TOKEN", "c1d01-whatsapp-verify")
    
    # Parámetros de la solicitud de verificación
    mode = request.query.get("hub.mode")
    token = request.query.get("hub.verify_token")
    challenge = request.query.get("hub.challenge")
    
    logger.info(f"Recibida solicitud de verificación: mode={mode}, token={token}")
    
    # Verificar que sea una solicitud de suscripción y que el token coincida
    if mode == "subscribe" and token == verify_token:
        logger.info("Webhook verificado correctamente")
        return web.Response(text=challenge)
    else:
        logger.warning("Verificación de webhook fallida")
        return web.Response(status=403, text="Forbidden")

async def send_auto_reply(to_number):
    """
    Envía una respuesta automática al número especificado.
    
    Args:
        to_number: Número al que se enviará la respuesta automática
    """
    try:
        # Obtener ID del teléfono de WhatsApp Business
        phone_number_id = os.environ.get("WHATSAPP_PHONE_NUMBER_ID")
        
        # Enviar mensaje automático
        result = await send_whatsapp_message(to_number, AUTO_REPLY_MESSAGE, phone_number_id)
        
        # Verificar resultado
        if "success" in result and result["success"]:
            logger.info(f"Respuesta automática enviada a {to_number}")
            return True
        else:
            logger.error(f"Error al enviar respuesta automática: {json.dumps(result)}")
            return False
    
    except Exception as e:
        logger.error(f"Excepción al enviar respuesta automática: {str(e)}")
        return False

async def process_webhook(request):
    """
    Procesa los mensajes entrantes del webhook de WhatsApp y responde automáticamente.
    """
    try:
        # Obtener el cuerpo de la solicitud
        body = await request.json()
        
        # Verificar que sea un webhook de WhatsApp
        if 'object' in body and body['object'] == 'whatsapp_business_account':
            # Procesar cada entrada
            for entry in body.get('entry', []):
                # Procesar cada cambio en la entrada
                for change in entry.get('changes', []):
                    # Verificar que sea un cambio de valor en mensajes
                    if change.get('field') == 'messages':
                        value = change.get('value', {})
                        
                        # Procesar cada mensaje
                        for message in value.get('messages', []):
                            # Obtener información del mensaje
                            from_number = message.get('from')
                            message_id = message.get('id')
                            message_type = message.get('type')
                            
                            # Obtener el contenido del mensaje si es de texto
                            if message_type == 'text':
                                message_text = message.get('text', {}).get('body', '')
                                
                                # Registrar mensaje recibido
                                logger.info(f"Mensaje recibido de {from_number}: {message_text}")
                                
                                # Mostrar información en consola
                                print("\n" + "="*50)
                                print("📱 MENSAJE RECIBIDO")
                                print("="*50)
                                print(f"De: {from_number}")
                                print(f"Mensaje: \"{message_text}\"")
                                print("-"*50)
                                
                                # Enviar respuesta automática
                                print(f"Enviando respuesta automática: \"{AUTO_REPLY_MESSAGE}\"")
                                await send_auto_reply(from_number)
                                print("-"*50)
                            else:
                                logger.info(f"Mensaje de tipo {message_type} no soportado")
        
        # Devolver 200 OK para confirmar recepción
        return web.Response(status=200, text="OK")
    
    except Exception as e:
        logger.error(f"Error al procesar webhook: {str(e)}")
        return web.Response(status=500, text=f"Error: {str(e)}")

async def start_webhook_server(host='0.0.0.0', port=8080):
    """
    Inicia el servidor de webhook de WhatsApp.
    """
    app = web.Application()
    
    # Rutas del webhook
    app.router.add_get('/webhook', verify_webhook)
    app.router.add_post('/webhook', process_webhook)
    
    # Iniciar el servidor
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    
    logger.info(f"Servidor de webhook iniciado en http://{host}:{port}")
    
    return runner

async def main():
    """
    Función principal.
    """
    # Imprimir información
    print("\n" + "="*70)
    print("🤖 RESPONDEDOR AUTOMÁTICO DE WHATSAPP")
    print("="*70)
    print("Este script inicia un servidor para recibir mensajes de WhatsApp")
    print("y responde automáticamente con un mensaje predefinido.")
    print("\nMensaje automático:")
    print(f"  \"{AUTO_REPLY_MESSAGE}\"")
    print("\nIMPORTANTE:")
    print("  Este servidor debe ser accesible desde internet")
    print("  (asegúrate de que ngrok esté corriendo)")
    print("\nPresiona Ctrl+C para detener el servidor")
    print("="*70 + "\n")
    
    # Iniciar servidor webhook
    runner = await start_webhook_server()
    
    try:
        # Mantener el servidor en ejecución
        while True:
            await asyncio.sleep(3600)  # Dormir por una hora
    finally:
        # Cerrar el servidor correctamente
        await runner.cleanup()

if __name__ == "__main__":
    asyncio.run(main()) 