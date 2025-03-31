"""
Integración de WhatsApp con el sistema de agentes C1DO1.

Este script maneja webhooks de WhatsApp y utiliza el sistema de agentes
OpenAI para procesar consultas y generar respuestas automatizadas,
con derivación a especialista humano cuando es necesario.
"""

import os
import sys
import json
import asyncio
import logging
from aiohttp import web
from datetime import datetime
from dotenv import load_dotenv
import threading
import queue
import time
import requests
import uuid

# Añadir el directorio raíz al path para importar los módulos
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Importar funciones y clases necesarias
from agents import Runner, set_default_openai_key
from utility_agents.simple_response_agent import simple_response_agent
from utility_agents.human_support_agent import human_support_agent
from whatsapp_integration.whatsapp_client import send_whatsapp_message
from utils.qa_vector_storage import store_support_answer

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("whatsapp_c1do1")

# Cargar variables de entorno
load_dotenv()

# Configuración inicial
openai_api_key = os.environ.get("OPENAI_API_KEY")
if not openai_api_key:
    raise ValueError("OPENAI_API_KEY no encontrada en variables de entorno")

# Configuración Notion
NOTION_API_KEY = os.environ.get("NOTION_API_KEY")
NOTION_DATABASE_ID = os.environ.get("NOTION_DATABASE_ID")
if not NOTION_API_KEY or not NOTION_DATABASE_ID:
    logger.warning("Credenciales de Notion no encontradas, la integración con Notion no estará disponible")

# Establecer la API key por defecto
set_default_openai_key(openai_api_key)

# Estructuras de datos para gestión de conversaciones
conversation_histories = {}  # Historiales por número
message_queue = queue.Queue()  # Cola de mensajes entrantes
pending_human_queries = {}  # Diccionario de consultas pendientes de respuesta humana
original_questions = {}  # Almacenamiento de consultas originales
our_phone_number_id = os.environ.get("WHATSAPP_PHONE_NUMBER_ID")  # ID de nuestro teléfono para identificar mensajes salientes

# Custom run result handler para recopilar datos de ejecución
class RunTracker:
    def __init__(self):
        self.reset()
    
    def reset(self):
        self.handoffs = []
        self.vector_results = []
        self.agent_names = []
        self.contexts = []
    
    def format_logs(self):
        """Formatea logs internos para visualización"""
        logs = []
        
        if self.contexts:
            logs.append("Contexto: " + "\n".join(self.contexts))
        
        if self.handoffs:
            logs.append("Handoffs: " + " -> ".join(self.handoffs))
        
        if self.agent_names:
            logs.append("Agentes utilizados: " + ", ".join(self.agent_names))
        
        if self.vector_results:
            logs.append("Resultados de búsqueda en vectores: ")
            for result in self.vector_results:
                logs.append(f"- {result}")
        
        return "\n".join(logs)

# Crear tracker
tracker = RunTracker()

async def verify_webhook(request):
    """Verifica el webhook de WhatsApp cuando Meta intenta verificarlo."""
    # Token de verificación definido en Meta Developer Portal
    verify_token = os.environ.get("WHATSAPP_VERIFY_TOKEN", "c1d01-whatsapp-verify")
    
    # Parámetros de la solicitud de verificación
    mode = request.query.get("hub.mode")
    token = request.query.get("hub.verify_token")
    challenge = request.query.get("hub.challenge")
    
    logger.info(f"Solicitud de verificación recibida: mode={mode}, token={token}")
    
    # Verificar que sea una solicitud de suscripción y que el token coincida
    if mode == "subscribe" and token == verify_token:
        logger.info("Webhook verificado correctamente")
        return web.Response(text=challenge)
    else:
        logger.warning("Verificación de webhook fallida")
        return web.Response(status=403, text="Forbidden")

async def process_webhook(request):
    """Procesa los mensajes entrantes del webhook de WhatsApp."""
    try:
        # Obtener el cuerpo de la solicitud
        body = await request.json()
        
        # Verificar que sea un webhook de WhatsApp
        if 'object' in body and body['object'] == 'whatsapp_business_account':
            # Procesar cada entrada
            for entry in body.get('entry', []):
                # Procesar cada cambio en la entrada
                for change in entry.get('changes', []):
                    # Verificar tipo de cambio (mensajes o estados)
                    if change.get('field') == 'messages':
                        value = change.get('value', {})
                        
                        # CASO 1: Procesar mensajes entrantes
                        if 'messages' in value:
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
                                    print(f"📱 MENSAJE RECIBIDO de {from_number}: \"{message_text}\"")
                                    print("="*50)
                                    
                                    # Crear objeto de mensaje
                                    message_data = {
                                        'from': from_number,
                                        'id': message_id,
                                        'text': message_text,
                                        'timestamp': datetime.now().isoformat()
                                    }
                                    
                                    # Agregar a la cola de mensajes para procesar
                                    message_queue.put(message_data)
                                else:
                                    logger.info(f"Mensaje de tipo {message_type} no soportado")
                        
                        # CASO 2: Procesar mensajes salientes (para detectar respuestas manuales desde nuestro número)
                        elif 'statuses' in value:
                            for status in value.get('statuses', []):
                                # Solo nos interesan los mensajes salientes enviados
                                if status.get('status') == 'sent':
                                    recipient_id = status.get('recipient_id')
                                    message_id = status.get('id')
                                    
                                    logger.info(f"Mensaje saliente detectado hacia {recipient_id} con ID {message_id}")
                                    print("\n" + "="*50)
                                    print(f"📤 MENSAJE SALIENTE detectado hacia {recipient_id}")
                                    print("="*50)
                                    
                                    # Verificar si este número está esperando respuesta humana
                                    if recipient_id in pending_human_queries:
                                        # Necesitamos obtener el contenido del mensaje, pero el webhook no lo proporciona
                                        # La solución es que verificaremos este ID de mensaje cuando llegue una confirmación de entrega
                                        
                                        # Almacenar el ID del mensaje para verificarlo después
                                        outgoing_message_ids[message_id] = {
                                            'recipient': recipient_id,
                                            'timestamp': datetime.now().isoformat()
                                        }
        
        # Devolver 200 OK para confirmar recepción
        return web.Response(status=200, text="OK")
    
    except Exception as e:
        logger.error(f"Error al procesar webhook: {str(e)}")
        return web.Response(status=500, text=f"Error: {str(e)}")

# Agregar endpoint para recibir webhooks desde Notion
async def process_notion_webhook(request):
    """
    Procesa los webhooks recibidos desde Notion cuando se responde a un ticket.
    """
    try:
        # Verificar el header de seguridad
        notion_secret = request.headers.get('X-Notion-Secret')
        if notion_secret != 'soporte123':
            logger.warning(f"Intento de acceso no autorizado al webhook de Notion: header incorrecto")
            return web.Response(status=403, text="Acceso no autorizado")
        
        # Obtener el cuerpo de la solicitud
        body = await request.json()
        logger.info(f"Webhook recibido desde Notion: {json.dumps(body)}")
        
        # Extraer los datos necesarios del payload
        try:
            # Acceder a las propiedades directamente de los datos de Notion
            properties = body.get('data', {}).get('properties', {})
            if not properties:
                # Si no se encuentra en data.properties, intentar acceder directamente a properties
                properties = body.get('properties', {})
            
            # Mostrar información de todos los datos recibidos para depuración
            print("\n" + "="*70)
            print("📑 DATOS RECIBIDOS DE NOTION:")
            print(f"• Estructura de datos: {body.keys()}")
            
            if 'data' in body:
                print(f"• Estructura de data: {body['data'].keys()}")
                if 'properties' in body['data']:
                    print(f"• Campos en data.properties: {body['data']['properties'].keys()}")
            
            print(f"• Campos en properties: {properties.keys()}")
            print("-"*70)
            
            # Buscar el número de teléfono
            telefono = ""
            
            # Primero intentar con el nuevo campo Celular
            celular_field = properties.get('Celular', {})
            if celular_field and 'rich_text' in celular_field and celular_field['rich_text']:
                telefono = celular_field['rich_text'][0].get('text', {}).get('content', '')
                print(f"• Valor de celular extraído: {telefono}")
            
            # Si no se encuentra, intentar con el campo Teléfono antiguo
            if not telefono:
                # Lista de posibles variantes del campo Teléfono
                telefono_variants = ["Teléfono", "Telefono", "teléfono", "telefono", "Tel\u00e9fono"]
                for variant in telefono_variants:
                    if variant in properties:
                        telefono_field = properties[variant]
                        if 'rich_text' in telefono_field and telefono_field['rich_text']:
                            telefono = telefono_field['rich_text'][0].get('text', {}).get('content', '')
                            print(f"• Valor de teléfono extraído desde '{variant}': {telefono}")
                            break
            
            # Si aún no se encuentra, buscar por formato de número
            if not telefono:
                print("• Buscando número por patrón numérico...")
                for field_name, field_value in properties.items():
                    if isinstance(field_value, dict) and 'rich_text' in field_value and field_value['rich_text']:
                        content = field_value['rich_text'][0].get('text', {}).get('content', '')
                        if content and len(content) > 8 and all(c.isdigit() or c == '+' for c in content):
                            telefono = content
                            print(f"• Encontrado número en campo '{field_name}': {telefono}")
                            break
            
            # Intentar extraer dato del teléfono del cuerpo completo si aún no se encuentra
            if not telefono:
                print("• Buscando teléfono en el cuerpo JSON completo...")
                json_str = json.dumps(body)
                import re
                phone_patterns = [
                    r'"content"\s*:\s*"(5\d{10})"',  # Número chileno
                    r'"content"\s*:\s*"(\+?\d{8,15})"'  # Cualquier número de teléfono
                ]
                for pattern in phone_patterns:
                    matches = re.findall(pattern, json_str)
                    if matches:
                        telefono = matches[0]
                        print(f"• Encontrado número mediante expresión regular: {telefono}")
                        break
            
            # Obtener respuesta
            respuesta = ""
            respuesta_field = properties.get('Respuesta', {})
            if respuesta_field and 'rich_text' in respuesta_field and respuesta_field['rich_text']:
                respuesta = respuesta_field['rich_text'][0].get('text', {}).get('content', '')
                print(f"• Respuesta extraída: \"{respuesta}\"")
            
            # Si no se encuentra la respuesta, buscarla en el cuerpo completo
            if not respuesta:
                print("• Buscando respuesta en el cuerpo JSON completo...")
                json_str = json.dumps(body)
                import re
                resp_match = re.search(r'"content"\s*:\s*"([^"]{2,100})"', json_str)
                if resp_match:
                    respuesta = resp_match.group(1)
                    # Evitar IDs o números de teléfono
                    if not respuesta.startswith(("id", "ID")) and not all(c.isdigit() or c == '-' for c in respuesta):
                        print(f"• Posible respuesta encontrada: \"{respuesta}\"")
            
            # Obtener pregunta
            pregunta = ""
            pregunta_field = properties.get('Pregunta', {})
            if pregunta_field and 'title' in pregunta_field and pregunta_field['title']:
                pregunta = pregunta_field['title'][0].get('text', {}).get('content', '')
                print(f"• Pregunta extraída: \"{pregunta}\"")
            
            print("="*70 + "\n")
            
            # Verificar si tenemos los datos mínimos necesarios
            if not telefono:
                logger.error("No se encontró número de teléfono en el webhook de Notion")
                # Último recurso: sacar de los pending_queries
                if 'data' in body and 'id' in body['data']:
                    page_id = body['data']['id']
                    print(f"• Buscando página por ID: {page_id} en consultas pendientes...")
                    
                    # Buscar si hay algún número pendiente
                    if pending_human_queries:
                        print(f"• Números pendientes: {list(pending_human_queries.keys())}")
                        # Si solo hay uno pendiente, usarlo
                        if len(pending_human_queries) == 1:
                            telefono = list(pending_human_queries.keys())[0]
                            print(f"• Usando único número pendiente: {telefono}")
                    
                # Si todavía no hay teléfono, error
                if not telefono:
                    return web.Response(status=400, text="No se pudo identificar el número de teléfono")
            
            if not respuesta:
                logger.error("No se encontró respuesta en el webhook de Notion")
                return web.Response(status=400, text="No se encontró la respuesta en el webhook")
            
            # Procesar la respuesta
            logger.info(f"Procesando respuesta de Notion para {telefono}: {respuesta}")
            await process_notion_response(telefono, pregunta, respuesta)
            
            return web.Response(status=200, text="OK")
        
        except Exception as e:
            logger.error(f"Error al procesar datos del webhook de Notion: {str(e)}")
            # Imprimir el traceback completo
            import traceback
            print(f"❌ ERROR EN WEBHOOK DE NOTION: {str(e)}")
            print(traceback.format_exc())
            return web.Response(status=400, text=f"Error: {str(e)}")
    
    except Exception as e:
        logger.error(f"Error al procesar webhook de Notion: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return web.Response(status=500, text=f"Error interno: {str(e)}")

async def process_notion_response(telefono, pregunta, respuesta):
    """
    Procesa una respuesta recibida desde Notion.
    
    Args:
        telefono: Número de teléfono del usuario
        pregunta: La pregunta original
        respuesta: La respuesta proporcionada en Notion
    """
    try:
        # Verificar si el número está en los pendientes
        if telefono in pending_human_queries:
            logger.info(f"Procesando respuesta de Notion para usuario {telefono}")
            print("\n" + "="*70)
            print(f"📥 RECIBIDA RESPUESTA DE NOTION PARA {telefono}")
            print("="*70)
            print(f"• Pregunta original: \"{pregunta}\"")
            print(f"• Respuesta: \"{respuesta}\"")
            print("-"*70)
            
            # Si la pregunta está vacía, intentar recuperarla de pending_human_queries
            if not pregunta and telefono in pending_human_queries:
                pregunta = pending_human_queries[telefono].get('question', '')
                print(f"ℹ️ Recuperada pregunta original de historial: \"{pregunta}\"")
            
            # Almacenar la respuesta en la base de datos vectorial
            try:
                print(f"📊 Almacenando respuesta de Notion en base de datos vectorial...")
                success, message = store_support_answer(
                    pregunta,
                    respuesta,
                    source="Soporte Humano - Notion"
                )
                if success:
                    print(f"✅ {message}")
                else:
                    print(f"⚠️ {message}")
            except Exception as e:
                logger.error(f"Error al almacenar respuesta: {str(e)}")
                print(f"❌ Error al almacenar respuesta: {str(e)}")
            
            try:
                # Enviar la respuesta al usuario
                print(f"📤 Enviando respuesta al usuario {telefono}...")
                success = await send_whatsapp_response(telefono, respuesta)
                
                if success:
                    # Actualizar historial de conversación
                    conversation_histories.setdefault(telefono, []).append((pregunta, respuesta))
                    
                    # Eliminar de la lista de pendientes
                    del pending_human_queries[telefono]
                    if telefono in original_questions:
                        del original_questions[telefono]
                    
                    print(f"✅ Respuesta de Notion enviada al usuario {telefono} correctamente")
                else:
                    logger.error(f"Error al enviar respuesta de Notion a {telefono}")
                    print(f"❌ Error al enviar respuesta de Notion a {telefono}")
            
            except Exception as e:
                logger.error(f"Error al enviar respuesta de Notion: {str(e)}")
                print(f"❌ Error al enviar respuesta de Notion: {str(e)}")
                
            print("="*70 + "\n")
        else:
            logger.warning(f"Recibida respuesta para número no pendiente: {telefono}")
            print(f"⚠️ Recibida respuesta para usuario no pendiente: {telefono}")
    
    except Exception as e:
        logger.error(f"Error al procesar respuesta de Notion: {str(e)}")
        print(f"❌ Error al procesar respuesta de Notion: {str(e)}")

def create_notion_ticket(phone_number, question):
    """
    Crea un ticket en la base de datos de Notion.
    
    Args:
        phone_number: Número de teléfono del usuario
        question: Pregunta o consulta del usuario
        
    Returns:
        str: ID de la página creada en Notion o None si hay un error
    """
    if not NOTION_API_KEY or not NOTION_DATABASE_ID:
        logger.error("No se puede crear ticket en Notion: credenciales no configuradas")
        print("❌ No se puede crear ticket en Notion: API key o Database ID no configurados")
        return None
    
    if not phone_number or not question:
        logger.error("No se puede crear ticket en Notion: faltan datos (teléfono o pregunta)")
        print("❌ No se puede crear ticket en Notion: faltan datos necesarios")
        return None
    
    try:
        # Generar ID único para el ticket
        ticket_id = str(uuid.uuid4())
        
        # Configurar cabeceras y URL
        headers = {
            "Authorization": f"Bearer {NOTION_API_KEY}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }
        url = f"https://api.notion.com/v1/pages"
        
        # Preparar datos para la creación del ticket
        data = {
            "parent": {"database_id": NOTION_DATABASE_ID},
            "properties": {
                "Pregunta": {
                    "title": [
                        {
                            "text": {
                                "content": question
                            }
                        }
                    ]
                },
                "Respuesta": {
                    "rich_text": []
                },
                "Celular": {  # Cambiado de "Teléfono" a "Celular"
                    "rich_text": [
                        {
                            "text": {
                                "content": phone_number
                            }
                        }
                    ]
                },
                "ID": {
                    "rich_text": [
                        {
                            "text": {
                                "content": ticket_id
                            }
                        }
                    ]
                }
            }
        }
        
        # Realizar solicitud a la API de Notion
        response = requests.post(url, headers=headers, json=data)
        
        # Verificar respuesta
        if response.status_code == 200:
            page_id = response.json().get("id")
            logger.info(f"Ticket creado en Notion con ID: {page_id}")
            print(f"✅ Ticket creado en Notion para {phone_number}")
            return page_id
        else:
            logger.error(f"Error al crear ticket en Notion: {response.status_code} - {response.text}")
            print(f"❌ Error al crear ticket en Notion: respuesta {response.status_code}")
            print(f"   Detalle: {response.text[:200]}...")
            return None
    
    except Exception as e:
        logger.error(f"Excepción al crear ticket en Notion: {str(e)}")
        print(f"❌ Excepción al crear ticket en Notion: {str(e)}")
        return None

def process_message_with_agents(message_data):
    """
    Procesa un mensaje a través del sistema de agentes.
    
    Args:
        message_data: Diccionario con datos del mensaje
    """
    try:
        from_number = message_data['from']
        message_text = message_data['text']
        phone_number_id = os.environ.get("WHATSAPP_PHONE_NUMBER_ID")
        
        # CASO 1: Es un mensaje desde nuestro propio número (soporte manual)
        # Buscar si hay una consulta pendiente para el número al que se envió y guardar en vectores
        # Esto se maneja ahora en el webhook de statuses
        
        # CASO 2: Es un usuario esperando respuesta de soporte humano
        if from_number in pending_human_queries:
            logger.info(f"Usuario {from_number} está esperando respuesta humana")
            
            # Informar al usuario que su consulta sigue en proceso
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            try:
                new_loop.run_until_complete(
                    send_whatsapp_response(
                        from_number, 
                        "Tu consulta ha sido transferida a un especialista humano. " +
                        "En breve recibirás una respuesta. Gracias por tu paciencia."
                    )
                )
            finally:
                new_loop.close()
            return
        
        # CASO 3: Es un mensaje normal que debe procesarse con los agentes
        else:
            # Obtener historial de conversación
            conversation_history = conversation_histories.get(from_number, [])
            
            logger.info(f"Procesando mensaje de {from_number} a través del sistema de agentes")
            
            # Crear un nuevo evento loop para procesar el mensaje
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            
            try:
                # Reiniciar el tracker para esta ejecución
                tracker.reset()
                
                # Preparar contexto si hay historial de conversación
                if conversation_history:
                    context = "\n\nHistorial de conversación anterior:\n"
                    for i, (user_msg, assistant_msg) in enumerate(conversation_history[-3:]):
                        context += f"Usuario: {user_msg}\nAsistente: {assistant_msg}\n"
                    context += f"\nConsulta actual: {message_text}"
                    tracker.contexts.append("Conversación previa incluida")
                    result = new_loop.run_until_complete(Runner.run(simple_response_agent, input=context))
                else:
                    result = new_loop.run_until_complete(Runner.run(simple_response_agent, input=message_text))
                
                # Registrar el último agente utilizado
                last_agent_name = getattr(result.last_agent, 'name', 'Unknown')
                print(f"🤖 Agente actual: '{last_agent_name}'")
                
                # Registrar el agente inicial
                tracker.agent_names.append(simple_response_agent.name)
                
                # Extraer detalles de la ejecución
                for item in result.new_items:        
                    # Registrar handoffs
                    if hasattr(item, 'to_agent') and hasattr(item, 'from_agent'):
                        handoff_from = getattr(item.from_agent, 'name', 'Unknown')
                        handoff_to = getattr(item.to_agent, 'name', 'Unknown')
                        tracker.handoffs.append(f"{handoff_from} → {handoff_to}")
                        tracker.agent_names.append(handoff_to)
                    
                    # Registrar resultados de búsqueda
                    if hasattr(item, 'type') and item.type == 'file_search_call':
                        try:
                            if hasattr(item, 'results') and item.results:
                                for result_item in item.results:
                                    if hasattr(result_item, 'text') and result_item.text:
                                        # Obtener un extracto
                                        text_snippet = result_item.text[:100] + "..." if len(result_item.text) > 100 else result_item.text
                                        filename = getattr(result_item, 'filename', 'unknown')
                                        score = getattr(result_item, 'score', 0)
                                        tracker.vector_results.append(f"Archivo: {filename}, Relevancia: {score:.2f}, Extracto: {text_snippet}")
                        except Exception as e:
                            tracker.vector_results.append(f"Error al procesar resultados: {str(e)}")
                
                # Verificar si se ha derivado a soporte humano
                if hasattr(result.last_agent, 'name') and result.last_agent.name == human_support_agent.name:
                    # Guardar la pregunta original
                    original_questions[from_number] = message_text
                    
                    # Marcar que está esperando respuesta humana
                    pending_human_queries[from_number] = {
                        'question': message_text,
                        'timestamp': datetime.now().isoformat()
                    }
                    
                    # Mostrar en terminal alerta para soporte humano
                    print("\n" + "="*70)
                    print("🔔 ALERTA: SE REQUIERE RESPUESTA HUMANA - DERIVANDO A NOTION")
                    print("="*70)
                    print(f"• Usuario: {from_number}")
                    print(f"• Consulta: \"{message_text}\"")
                    print(f"• Fecha/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                    print("-"*70)
                    
                    # Crear ticket en Notion
                    notion_page_id = create_notion_ticket(from_number, message_text)
                    
                    if notion_page_id:
                        print("✅ Se ha creado un ticket en Notion para responder a esta consulta")
                        print("   Un agente humano responderá a través de Notion")
                        
                    else:
                        print("⚠️ No se pudo crear el ticket en Notion")
                        print("   La consulta queda pendiente de respuesta manual")
                        
                        # Informamos al usuario con un mensaje diferente en caso de error
                        new_loop.run_until_complete(
                            send_whatsapp_response(
                                from_number, 
                                "Tu consulta requiere asistencia especializada. Un humano revisará tu caso y te responderá lo antes posible. Gracias por tu paciencia."
                            )
                        )
                    
                    print("="*70 + "\n")
                else:
                    # Respuesta normal del sistema de agentes
                    response = result.final_output
                    
                    # Enviar respuesta al usuario
                    new_loop.run_until_complete(send_whatsapp_response(from_number, response))
                    
                    # Mostrar logs internos en la consola (versión reducida)
                    internal_logs = tracker.format_logs()
                    if internal_logs:
                        print("\n📋 Detalles de ejecución:")
                        print(internal_logs)
                    
                    # Actualizar historial de conversación
                    conversation_histories.setdefault(from_number, []).append((message_text, response))
            
            finally:
                # Cerrar el evento loop
                new_loop.close()
    
    except Exception as e:
        logger.error(f"Error al procesar mensaje: {str(e)}")
        # Enviar mensaje de error al usuario
        try:
            error_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(error_loop)
            try:
                error_loop.run_until_complete(
                    send_whatsapp_response(
                        message_data['from'], 
                        "Lo siento, ha ocurrido un error al procesar tu mensaje. Por favor, intenta nuevamente más tarde."
                    )
                )
            finally:
                error_loop.close()
        except Exception as inner_e:
            logger.error(f"Error al enviar mensaje de error: {str(inner_e)}")

# Añadir función para detectar y procesar los mensajes salientes manuales
def process_manual_response(to_number, message_text):
    """
    Procesa respuestas manuales de soporte enviadas a un usuario.
    
    Args:
        to_number: Número del destinatario
        message_text: Texto del mensaje enviado
    """
    try:
        # Verificar si el número está esperando respuesta humana
        if to_number in pending_human_queries:
            original_question = pending_human_queries[to_number]['question']
            
            print(f"🔄 Procesando respuesta manual a {to_number}")
            
            # Almacenar la respuesta en la base de datos vectorial
            try:
                print("📊 Almacenando respuesta humana en base de datos vectorial...")
                success, _ = store_support_answer(
                    original_question,
                    message_text,
                    source="Soporte Humano - Manual"
                )
                if success:
                    print("✅ Respuesta almacenada correctamente")
            except Exception as e:
                logger.error(f"Error al almacenar respuesta: {str(e)}")
            
            # Actualizar historial de conversación del usuario
            if to_number in conversation_histories:
                conversation_histories[to_number].append(
                    (original_question, message_text)
                )
            
            # Eliminar de la lista de pendientes
            del pending_human_queries[to_number]
            if to_number in original_questions:
                del original_questions[to_number]
            
            print(f"✅ Consulta de {to_number} marcada como respondida")
            return True
        else:
            return False
    except Exception as e:
        logger.error(f"Error al procesar respuesta manual: {str(e)}")
        return False

async def send_whatsapp_response(to_number, message_text):
    """
    Envía una respuesta de WhatsApp.
    
    Args:
        to_number: Número de destino
        message_text: Texto del mensaje
        
    Returns:
        bool: True si el mensaje se envió correctamente, False en caso contrario
    """
    try:
        # Obtener ID del teléfono de WhatsApp Business
        phone_number_id = os.environ.get("WHATSAPP_PHONE_NUMBER_ID")
        
        # Mostrar en consola lo que se va a enviar
        print(f"\n📤 Enviando a {to_number}:\n\"{message_text}\"")
        
        # Enviar mensaje
        result = await send_whatsapp_message(to_number, message_text, phone_number_id)
        
        # Verificar resultado
        if "success" in result and result["success"]:
            logger.info(f"Respuesta enviada a {to_number}")
            return True
        else:
            logger.error(f"Error al enviar respuesta: {json.dumps(result)}")
            return False
    
    except Exception as e:
        logger.error(f"Excepción al enviar respuesta: {str(e)}")
        return False

def message_processor_thread():
    """
    Hilo para procesar mensajes de forma continua.
    """
    logger.info("Iniciando procesador de mensajes")
    
    while True:
        try:
            # Obtener mensaje de la cola (bloqueante)
            message = message_queue.get()
            
            # Procesar mensaje con agentes
            process_message_with_agents(message)
            
            # Marcar como completado
            message_queue.task_done()
        
        except Exception as e:
            logger.error(f"Error en el procesador de mensajes: {str(e)}")
            # Continuar procesando mensajes aunque haya un error

async def start_webhook_server(host='0.0.0.0', port=8080):
    """
    Inicia el servidor de webhook de WhatsApp.
    """
    app = web.Application()
    
    # Rutas del webhook
    app.router.add_get('/webhook', verify_webhook)
    app.router.add_post('/webhook', process_webhook)
    
    # Ruta para webhook de Notion
    app.router.add_post('/notion-webhook', process_notion_webhook)
    
    # Iniciar el servidor
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    
    logger.info(f"Servidor webhook iniciado en http://{host}:{port}")
    print(f"Endpoint de Notion disponible en: http://{host}:{port}/notion-webhook")
    
    return runner

async def main():
    """
    Función principal.
    """
    # Imprimir información
    print("\n" + "="*70)
    print("🤖 SISTEMA DE AGENTES C1DO1 CON INTEGRACIÓN WHATSAPP Y NOTION")
    print("="*70)
    print("Este sistema procesa mensajes de WhatsApp a través del sistema de agentes C1DO1")
    print("y crea tickets en Notion para respuestas humanas cuando es necesario.")
    
    # Inicializar diccionario para mensajes salientes
    global outgoing_message_ids
    outgoing_message_ids = {}
    
    print("\n📋 IMPORTANTE:")
    print("  • Las consultas que requieran respuesta humana se registrarán en Notion")
    print("  • Responda desde Notion usando el botón 'Enviar Respuesta'")
    print("  • Las respuestas se almacenarán en la base de datos vectorial automáticamente")
    print("  • Este servidor debe ser accesible desde internet")
    print("  • Asegúrate de que ngrok esté corriendo")
    
    # Verificar integración con Notion
    if not NOTION_API_KEY or not NOTION_DATABASE_ID:
        print("\n⚠️ ADVERTENCIA: Integración con Notion no configurada")
        print("  • Comprueba que las variables NOTION_API_KEY y NOTION_DATABASE_ID")
        print("    estén correctamente establecidas en tu archivo .env")
    else:
        print("\n✅ Integración con Notion configurada correctamente")
    
    # Verificar si hay consultas pendientes para mostrar
    if pending_human_queries:
        print("\n🔄 CONSULTAS PENDIENTES DE RESPUESTA:")
        for number, query_data in pending_human_queries.items():
            print(f"  • Usuario: {number}")
            print(f"    Consulta: \"{query_data['question']}\"")
            print(f"    Fecha: {datetime.fromisoformat(query_data['timestamp']).strftime('%Y-%m-%d %H:%M:%S')}")
            print()
    
    print("\nPresiona Ctrl+C para detener el servidor")
    print("="*70 + "\n")
    
    # Iniciar procesador de mensajes en hilo separado
    processor_thread = threading.Thread(target=message_processor_thread, daemon=True)
    processor_thread.start()
    
    # Iniciar servidor webhook
    runner = await start_webhook_server()
    
    try:
        # Mantener el servidor en ejecución
        while True:
            await asyncio.sleep(3600)  # Dormir por una hora
    except asyncio.CancelledError:
        logger.info("Tarea principal cancelada")
    except Exception as e:
        logger.error(f"Error en la tarea principal: {str(e)}")
    finally:
        # Cerrar el servidor correctamente
        await runner.cleanup()
        logger.info("Servidor detenido correctamente")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n¡Hasta luego! Gracias por usar el sistema de agentes C1DO1.")
        sys.exit(0) 