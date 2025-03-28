"""
Módulo de integración de WhatsApp para el sistema multiagente de C1DO1.
"""

from .whatsapp_client import WhatsAppClient, send_whatsapp_message

__all__ = ["WhatsAppClient", "send_whatsapp_message"] 