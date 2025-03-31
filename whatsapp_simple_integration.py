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
                        
                        # CASO 3: Procesar confirmaciones de mensajes (para obtener el contenido)
                        # Nota: Esta parte es teórica ya que WhatsApp no proporciona el contenido en los webhooks de status
                        # Se incluye como placeholder para futura implementación si se encontrara una forma alternativa
        
        # Devolver 200 OK para confirmar recepción
        return web.Response(status=200, text="OK")
    
    except Exception as e:
        logger.error(f"Error al procesar webhook: {str(e)}")
        return web.Response(status=500, text=f"Error: {str(e)}")

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
                    
                    # Mostrar en terminal alerta para soporte humano con opción de respuesta inmediata
                    print("\n" + "="*70)
                    print("🔔 ALERTA: SE REQUIERE RESPUESTA HUMANA - RESPONDA DIRECTAMENTE AQUÍ")
                    print("="*70)
                    print(f"• Usuario: {from_number}")
                    print(f"• Consulta: \"{message_text}\"")
                    print(f"• Fecha/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                    print("-"*70)
                    
                    # Solicitar respuesta directamente en la terminal
                    human_response = input("📝 Ingrese su respuesta (o presione Enter para responder más tarde): ")
                    
                    # Si se proporciona una respuesta inmediata
                    if human_response.strip():
                        print("✅ Procesando respuesta...")
                        
                        # Almacenar la respuesta en la base de datos vectorial
                        try:
                            success, message = store_support_answer(
                                message_text,
                                human_response,
                                source="Soporte Humano - Terminal"
                            )
                            if success:
                                print(f"✅ {message}")
                            else:
                                print(f"⚠️ {message}")
                        except Exception as e:
                            print(f"⚠️ Error al almacenar respuesta: {str(e)}")
                        
                        # Enviar respuesta al usuario
                        new_loop.run_until_complete(
                            send_whatsapp_response(from_number, human_response)
                        )
                        
                        # Actualizar historial de conversación
                        conversation_histories.setdefault(from_number, []).append((message_text, human_response))
                        
                        # Eliminar de la lista de pendientes
                        del pending_human_queries[from_number]
                        if from_number in original_questions:
                            del original_questions[from_number]
                        
                        print("✅ Respuesta enviada al usuario correctamente")
                    else:
                        print("⚠️ No se proporcionó respuesta. La consulta queda pendiente.")
                        print("   Ingrese respuesta más tarde cuando esté disponible.")
                        
                        # Informamos al usuario que estamos procesando su consulta
                        new_loop.run_until_complete(
                            send_whatsapp_response(
                                from_number, 
                                "Estamos procesando tu consulta. Un especialista humano te responderá en breve. Gracias por tu paciencia."
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
    
    # Iniciar el servidor
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    
    logger.info(f"Servidor webhook iniciado en http://{host}:{port}")
    
    return runner

async def main():
    """
    Función principal.
    """
    # Imprimir información
    print("\n" + "="*70)
    print("🤖 SISTEMA DE AGENTES C1DO1 CON INTEGRACIÓN WHATSAPP Y SOPORTE HUMANO DIRECTO")
    print("="*70)
    print("Este sistema procesa mensajes de WhatsApp a través del sistema de agentes C1DO1")
    print("y permite respuestas manuales directamente desde la terminal cuando es necesario.")
    
    # Inicializar diccionario para mensajes salientes
    global outgoing_message_ids
    outgoing_message_ids = {}
    
    print("\n📋 IMPORTANTE:")
    print("  • Las consultas que requieran respuesta humana se mostrarán en esta terminal")
    print("  • Puede responder directamente ingresando la respuesta cuando se le solicite")
    print("  • Las respuestas se almacenarán en la base de datos vectorial automáticamente")
    print("  • Este servidor debe ser accesible desde internet")
    print("  • Asegúrate de que ngrok esté corriendo")
    
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
    
    # Iniciar manejador de consultas pendientes
    pending_handler_thread = threading.Thread(target=pending_queries_handler, daemon=True)
    pending_handler_thread.start()
    
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

# Añadir función para manejar consultas pendientes
def pending_queries_handler():
    """
    Hilo para manejar consultas pendientes que no fueron respondidas inmediatamente.
    Permite responder consultas pendientes en cualquier momento.
    """
    logger.info("Iniciando manejador de consultas pendientes")
    
    while True:
        try:
            # Comprobar si hay consultas pendientes cada 30 segundos
            if pending_human_queries:
                print("\n" + "="*70)
                print("🔄 CONSULTAS PENDIENTES DE RESPUESTA:")
                print("="*70)
                
                numbers_to_process = list(pending_human_queries.keys())
                
                for i, number in enumerate(numbers_to_process):
                    query_data = pending_human_queries.get(number)
                    if not query_data:
                        continue
                    
                    print(f"[{i+1}] Usuario: {number}")
                    print(f"    Consulta: \"{query_data['question']}\"")
                    print(f"    Fecha: {datetime.fromisoformat(query_data['timestamp']).strftime('%Y-%m-%d %H:%M:%S')}")
                    print("-"*70)
                
                print("\nPara responder a una consulta, ingrese el número correspondiente")
                print("o presione Enter para continuar sin responder.")
                choice = input("Selección: ")
                
                if choice.strip() and choice.isdigit():
                    idx = int(choice) - 1
                    if 0 <= idx < len(numbers_to_process):
                        selected_number = numbers_to_process[idx]
                        question = pending_human_queries[selected_number]['question']
                        
                        print(f"\n• Respondiendo a {selected_number}")
                        print(f"• Consulta: \"{question}\"")
                        human_response = input("📝 Ingrese su respuesta: ")
                        
                        if human_response.strip():
                            print("✅ Procesando respuesta...")
                            
                            # Almacenar la respuesta en la base de datos vectorial
                            try:
                                success, message = store_support_answer(
                                    question,
                                    human_response,
                                    source="Soporte Humano - Terminal"
                                )
                                if success:
                                    print(f"✅ {message}")
                                else:
                                    print(f"⚠️ {message}")
                            except Exception as e:
                                print(f"⚠️ Error al almacenar respuesta: {str(e)}")
                            
                            # Enviar respuesta al usuario
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            try:
                                loop.run_until_complete(
                                    send_whatsapp_response(selected_number, human_response)
                                )
                            finally:
                                loop.close()
                            
                            # Actualizar historial de conversación
                            conversation_histories.setdefault(selected_number, []).append((question, human_response))
                            
                            # Eliminar de la lista de pendientes
                            del pending_human_queries[selected_number]
                            if selected_number in original_questions:
                                del original_questions[selected_number]
                            
                            print("✅ Respuesta enviada al usuario correctamente")
                        else:
                            print("⚠️ No se proporcionó respuesta. La consulta sigue pendiente.")
            
            # Esperar antes de verificar nuevamente
            time.sleep(30)
        
        except Exception as e:
            logger.error(f"Error en el manejador de consultas pendientes: {str(e)}")
            time.sleep(30)  # Continuar a pesar del error

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n¡Hasta luego! Gracias por usar el sistema de agentes C1DO1.")
        sys.exit(0) 