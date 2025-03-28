"""
Script de prueba para el cliente de WhatsApp.

Este script ejecuta una prueba básica del cliente de WhatsApp enviando
un mensaje de prueba al número especificado.
"""

import os
import sys
import asyncio
import logging
from dotenv import load_dotenv

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("whatsapp_test")

# Importar el cliente de WhatsApp
from whatsapp_client import WhatsAppClient, send_whatsapp_message

async def test_send_message(phone_number, message):
    """
    Prueba enviar un mensaje a través de WhatsApp.
    
    Args:
        phone_number: Número de teléfono del destinatario
        message: Mensaje a enviar
    """
    logger.info(f"Enviando mensaje a {phone_number}: {message}")
    
    # Obtener el ID del número de teléfono de WhatsApp Business
    phone_number_id = os.environ.get("WHATSAPP_PHONE_NUMBER_ID")
    if not phone_number_id:
        logger.warning("WHATSAPP_PHONE_NUMBER_ID no está configurado en .env, se usará el client_id como alternativa")
        phone_number_id = os.environ.get("WHATSAPP_CLIENT_ID")
    
    # Imprimir variables de entorno relacionadas con WhatsApp (sin mostrar valores completos)
    client_id = os.environ.get("WHATSAPP_CLIENT_ID")
    client_secret = os.environ.get("WHATSAPP_CLIENT_SECRET")
    logger.info(f"WHATSAPP_CLIENT_ID configurado: {'Sí' if client_id else 'No'}")
    logger.info(f"WHATSAPP_CLIENT_SECRET configurado: {'Sí' if client_secret else 'No'}")
    logger.info(f"WHATSAPP_PHONE_NUMBER_ID configurado: {'Sí' if phone_number_id else 'No'}")
    
    # Enviar mensaje
    result = await send_whatsapp_message(phone_number, message, phone_number_id)
    
    # Mostrar resultado
    if "error" in result:
        logger.error(f"Error al enviar mensaje: {result['error']}")
    else:
        logger.info(f"Mensaje enviado correctamente: {result}")

async def main():
    """
    Función principal para probar el cliente de WhatsApp.
    """
    # Cargar variables de entorno
    load_dotenv()
    
    # Verificar argumentos
    if len(sys.argv) < 3:
        print("Uso: python test_client.py <número_teléfono> <mensaje>")
        print("Ejemplo: python test_client.py +1234567890 'Hola, esto es una prueba'")
        return
    
    # Obtener argumentos
    phone_number = sys.argv[1]
    message = sys.argv[2]
    
    # Ejecutar prueba
    await test_send_message(phone_number, message)

if __name__ == "__main__":
    asyncio.run(main()) 