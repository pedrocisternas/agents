"""
Agente de Respuestas Complejas para C1DO1

Este agente maneja consultas más complejas buscando en la base de conocimiento de C1DO1
en la base de datos vectorial. Si no puede encontrar información, indicará
que se necesita asistencia humana.
"""

import os
import asyncio
from dotenv import load_dotenv

# Importar la biblioteca OpenAI Agents de forma estándar
from agents import Agent, Runner, set_default_openai_key

# Import the file search tool
from tools.file_search import file_search

# Load environment variables
load_dotenv()

# Get OpenAI API key and vector store ID
openai_api_key = os.environ.get("OPENAI_API_KEY")
vector_store_id = os.environ.get("VECTOR_STORE_ID")

if not openai_api_key:
    raise ValueError("OPENAI_API_KEY not found in environment variables")
if not vector_store_id:
    raise ValueError("VECTOR_STORE_ID not found in environment variables. Please run scripts/create_vector_store.py first.")

# Set the default OpenAI API key
set_default_openai_key(openai_api_key)

# Create the Complex Response Agent
complex_response_agent = Agent(
    name="C1DO1 Knowledge Specialist",
    instructions=f"""You are a specialist support agent for C1DO1 company with access to the company knowledge base.
Your job is to handle detailed queries about C1DO1's products, services, and company information.

Search the company knowledge base for information using the file_search tool.
The vector store ID to use is: {vector_store_id}

IMPORTANT: Be extremely strict about when you can answer:

1. ONLY answer if you find SPECIFIC information directly related to the user's query in the knowledge base.
2. If you find general information that is not specifically related to the user's exact question, DO NOT attempt to answer.
3. If you need to make assumptions or provide generic advice, DO NOT answer.
4. If you use phrases like "I don't have specific information", "I couldn't find", "I don't have details", you MUST transfer to a human.

If you CANNOT find SPECIFIC information in the knowledge base after searching, ALWAYS respond with:
"I apologize, but I don't have the specific information to answer your question accurately. Let me transfer you to a human specialist who can assist you better."

Never provide general troubleshooting steps or generic advice if you don't have specific information.

Always be professional, thorough, and respond in the same language as the question.
""",
    model="gpt-4o",
    tools=[file_search]
)

def format_context_info(input_message, conversation_history):
    """
    Generate a formatted string with information about the context being used.
    
    Args:
        input_message: The message being sent to the agent
        conversation_history: The full conversation history
        
    Returns:
        A string with information about the context
    """
    if not conversation_history:
        return "Contexto: Solo pregunta actual"
    
    num_messages = len(conversation_history)
    total_chars = sum(len(msg['content']) for msg in conversation_history)
    final_input_chars = len(input_message)
    
    return f"Contexto: {num_messages} mensajes | {total_chars} caracteres históricos | {final_input_chars} caracteres en consulta final"

async def process_complex_query(query, conversation_history=None):
    """
    Process a query through the Complex Response Agent using the vector database.
    
    Args:
        query: User's message/query
        conversation_history: Optional list of previous conversation messages
        
    Returns:
        response: Agent's response
        needs_human_help: Boolean indicating if query needs human assistance
    """
    # Add conversation context if available
    input_message = query
    if conversation_history and len(conversation_history) > 0:
        # Format conversation history for context
        context = "Conversación previa:\n"
        for msg in conversation_history[-4:]:  # Last 4 messages for context
            role = "Usuario" if msg["role"] == "user" else "Agente"
            context += f"{role}: {msg['content']}\n"
        input_message = f"{context}\n\nConsulta actual: {query}"
    
    context_info = format_context_info(input_message, conversation_history)
    print(f"[Agente de Conocimiento | {context_info}]")
    
    result = await Runner.run(complex_response_agent, input=input_message)
    response = result.final_output
    
    # Check if the response indicates human help is needed
    human_help_indicators = [
        # English indicators
        "transfer you to a human",
        "human specialist",
        "don't have enough information",
        "don't have the specific information",
        "cannot find information",
        "couldn't find",
        "don't have specific",
        "don't have details",
        "not found specific",
        "unable to find",
        "no specific information",
        # Spanish indicators
        "no tengo suficiente información",
        "no tengo la información específica",
        "no tengo información específica",
        "no puedo encontrar",
        "no he encontrado",
        "no encontré información específica",
        "no encontré",
        "transferirte a un especialista humano",
        "transferirte a un humano",
        "especialista humano",
        "no tengo la información",
        "no dispongo de información",
        "no encuentro información",
        "sin información específica",
        "no hay información específica"
    ]
    
    # Also force human help if the agent admits lack of information  
    lack_info_indicators = [
        "parece que no encontré",
        "no he podido encontrar",
        "no pude encontrar",
        "it seems I couldn't find",
        "I haven't been able to find",
        "I wasn't able to find",
        "I could not find"
    ]
    
    needs_human_help = any(indicator.lower() in response.lower() for indicator in human_help_indicators + lack_info_indicators)
    
    # If the agent admits lack of information but isn't explicitly stating a transfer,
    # replace the response with a standard transfer message
    if any(indicator.lower() in response.lower() for indicator in lack_info_indicators) and not any(indicator.lower() in response.lower() for indicator in human_help_indicators):
        if "spanish" in response.lower() or any(spanish_word in response.lower() for spanish_word in ["gracias", "ayuda", "información", "específica"]):
            response = "Lo siento, no tengo la información específica para responder a tu pregunta. Voy a transferirte a un especialista humano que podrá ayudarte mejor."
        else:
            response = "I apologize, but I don't have the specific information to answer your question accurately. Let me transfer you to a human specialist who can assist you better."
        needs_human_help = True
    
    return response, needs_human_help

async def main():
    """
    Test function for the Complex Response Agent.
    """
    print("=== Prueba del Agente de Respuestas Complejas ===")
    
    test_query = "¿Cuáles son los productos principales de C1DO1?"
    print(f"Probando consulta: {test_query}")
    response, needs_human = await process_complex_query(test_query)
    print(f"Respuesta: {response}")
    print(f"¿Necesita ayuda humana?: {needs_human}")
    
    human_test_query = "¿Cuántos empleados tiene la empresa en el departamento de innovación?"
    print(f"\nProbando consulta que probablemente necesite ayuda humana: {human_test_query}")
    response, needs_human = await process_complex_query(human_test_query)
    print(f"Respuesta: {response}")
    print(f"¿Necesita ayuda humana?: {needs_human}")

if __name__ == "__main__":
    asyncio.run(main()) 