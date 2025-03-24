"""
WhatsApp Agent System for C1DO1

This system simulates a WhatsApp business messaging platform with multiple tiers of agents:
1. Simple Response Agent - handles basic queries and greetings
2. Complex Response Agent - handles detailed queries using vector database knowledge
3. Human Handoff - for queries that can't be answered automatically
4. Learning System - stores human answers in vector database for future use
"""

import os
import asyncio
from dotenv import load_dotenv

# Importar la biblioteca OpenAI Agents de forma estándar
from agents import Agent, Runner, set_default_openai_key

# Importar nuestros agentes personalizados
from c1do1_agents.complex_response_agent import process_complex_query
from c1do1_agents.vector_storage_agent import store_in_vector_database

# Load environment variables
load_dotenv()

# Get OpenAI API key
openai_api_key = os.environ.get("OPENAI_API_KEY")
if not openai_api_key:
    raise ValueError("OPENAI_API_KEY not found in environment variables")

# Set the default OpenAI API key
set_default_openai_key(openai_api_key)

# Create the Simple Response Agent (Tier 1)
simple_response_agent = Agent(
    name="Simple Response Agent",
    instructions="""Eres el primer nivel de atención al cliente para la empresa C1DO1.
Tu trabajo es manejar consultas simples, saludos e información básica.

Debes ser capaz de manejar:
- Saludos y cortesías
- Preguntas simples sobre horarios de atención
- Información básica sobre productos
- Consultas simples de precios
- Información de contacto básica

Si una pregunta es compleja o requiere conocimiento específico sobre productos de C1DO1, 
servicios o información de la empresa, responde con:
"Voy a consultar con nuestro equipo de especialistas para esa pregunta."

Sé amable, profesional y conciso. Responde siempre en español.
""",
    model="gpt-4o"
)

async def process_simple_query(query):
    """
    Process a query through the Simple Response Agent.
    
    Args:
        query: User's message/query
        
    Returns:
        response: Agent's response
        needs_escalation: Boolean indicating if query needs escalation to next tier
    """
    result = await Runner.run(simple_response_agent, input=query)
    response = result.final_output
    
    # Check if the response indicates escalation is needed
    escalation_indicators = [
        # English indicators
        "I'll need to transfer you",
        "specialist team",
        "one of our experts",
        "need more information to assist",
        "let me connect you",
        # Spanish indicators
        "necesitaré transferirte",
        "voy a consultar con nuestro equipo",
        "equipo de especialistas",
        "nuestros expertos",
        "necesito más información",
        "te conectaré",
        "debo transferirte"
    ]
    
    needs_escalation = any(indicator.lower() in response.lower() for indicator in escalation_indicators)
    
    return response, needs_escalation

async def get_human_response(query):
    """
    Simulate getting a response from a human agent (you).
    
    Args:
        query: The user's question
        
    Returns:
        The human's response
    """
    print("\n" + "="*60)
    print("  [INTERFAZ DE ASISTENTE HUMANO - NO VISIBLE PARA EL USUARIO]")
    print("="*60)
    print(f"\n  Consulta del usuario: {query}")
    print("\n  Por favor proporciona tu respuesta de experto:")
    human_response = input("\n  Tu respuesta: ")
    print("\n" + "="*60 + "\n")
    return human_response

def get_context_summary(conversation_history, max_messages=4):
    """
    Generate a summary of the conversation context being passed.
    
    Args:
        conversation_history: The conversation history
        max_messages: Maximum number of messages to include
        
    Returns:
        A summary string of the context
    """
    if not conversation_history or len(conversation_history) == 0:
        return "Sin contexto previo"
    
    recent_messages = conversation_history[-max_messages:] if len(conversation_history) > max_messages else conversation_history
    
    summary = f"{len(recent_messages)} mensajes de contexto | "
    summary += f"{sum(len(msg['content']) for msg in recent_messages)} caracteres totales | "
    summary += f"Último mensaje: '{recent_messages[-1]['content'][:30]}{'...' if len(recent_messages[-1]['content']) > 30 else ''}'"
    
    return summary

def print_system_separator(title):
    """
    Print a visually distinctive separator for system logs.
    
    Args:
        title: The title to display in the separator
    """
    print("\n" + "-"*60)
    print(f"  [SISTEMA - {title}]")
    print("-"*60)

async def main():
    """
    Main function to run the WhatsApp agent system.
    Simulates a chat interface in the terminal.
    """
    print("\n===== Sistema de Soporte WhatsApp C1DO1 =====")
    print("(Escribe 'salir' en cualquier momento para terminar)")
    print("Ingresa tu mensaje como si estuvieras enviando por WhatsApp:\n")
    
    conversation_history = []
    
    while True:
        # Get user input
        user_message = input("Tú: ")
        
        if user_message.lower() in ["salir", "exit"]:
            print("\n¡Gracias por usar el Soporte de C1DO1. ¡Hasta pronto!")
            break
        
        # Add user message to conversation history
        conversation_history.append({"role": "user", "content": user_message})
        
        try:    
            # Process through Simple Response Agent first
            simple_response, needs_escalation = await process_simple_query(user_message)
            
            if needs_escalation:
                # Iniciar proceso de handoff con separador visual
                print_system_separator("INICIO DE HANDOFF INTERNO")
                
                # Mostrar mensaje interno del agente simple (solo para operadores)
                print(f"\n  Agente Simple decidió escalar con respuesta: \n  \"{simple_response}\"")
                
                # Mostrar al usuario un mensaje genérico (sin indicar transferencia)
                print("\n  Mensaje para usuario:", end=" ")
                print("Agente Simple: Un momento por favor, estoy procesando tu consulta.")
                
                # Log del escalado en la terminal (solo para operadores)
                print(f"\n  Escalando al Agente de Conocimiento | Contexto: {get_context_summary(conversation_history)}")
                
                try:
                    # Process through Complex Response Agent
                    complex_response, needs_human_help = await process_complex_query(
                        user_message, 
                        conversation_history
                    )
                    
                    if needs_human_help:
                        # Mostrar mensaje interno del agente de conocimiento (solo para operadores)
                        print(f"\n  Agente de Conocimiento decidió escalar con respuesta: \n  \"{complex_response}\"")
                        print("\n  Escalando al Agente Humano")
                        
                        # Cerrar separador del handoff interno
                        print("-"*60 + "\n")
                        
                        # Get response from human (you)
                        human_response = await get_human_response(user_message)
                        
                        # Store the human response in the vector database for future use
                        print_system_separator("ALMACENAMIENTO")
                        print("\n  Almacenando respuesta humana en la base de datos vectorial...")
                        success, file_id = await store_in_vector_database(
                            user_message, 
                            human_response,
                            {"conversation_history": conversation_history}
                        )
                        
                        if success:
                            print(f"\n  Respuesta almacenada con éxito, ID: {file_id}")
                        else:
                            print("\n  Error al almacenar en la base de datos")
                        
                        print("-"*60 + "\n")
                        
                        # Mostrar respuesta al usuario
                        print("Agente Humano: " + human_response)
                        conversation_history.append({"role": "assistant", "content": human_response})
                    else:
                        # Cerrar separador del handoff interno
                        print("\n  Respuesta encontrada en la base de conocimiento.")
                        print("-"*60 + "\n")
                        
                        # Mostrar respuesta al usuario
                        print("Agente de Conocimiento: " + complex_response)
                        conversation_history.append({"role": "assistant", "content": complex_response})
                except Exception as e:
                    # Cerrar separador del handoff interno
                    print(f"\n  ERROR: No se pudo procesar con el Agente de Conocimiento: {str(e)}")
                    print("-"*60 + "\n")
                    
                    print("Agente Simple: Lo siento, estoy teniendo problemas para conectar con nuestro equipo especializado. Por favor, inténtalo de nuevo más tarde.")
            else:
                print("Agente Simple: " + simple_response)
                conversation_history.append({"role": "assistant", "content": simple_response})
        except Exception as e:
            print(f"[ERROR: {str(e)}]")
            print("Sistema: Lo siento, he encontrado un error. Por favor, inténtalo de nuevo.")

if __name__ == "__main__":
    asyncio.run(main()) 