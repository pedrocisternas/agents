"""
Complex Response Agent for C1DO1

This agent handles more complex queries by searching in the C1DO1 knowledge base.
If it cannot find information, it will hand off to a human specialist.
"""

import os
from dotenv import load_dotenv
from agents import Agent, FileSearchTool
from agents.extensions.handoff_prompt import prompt_with_handoff_instructions

from .human_support_agent import human_support_agent

# Load environment variables to get the vector store ID
load_dotenv()
VECTOR_STORE_ID = os.environ.get("VECTOR_STORE_ID")

if not VECTOR_STORE_ID:
    raise ValueError("VECTOR_STORE_ID not found in environment variables")

# Create the FileSearchTool for vector database search
file_search_tool = FileSearchTool(
    vector_store_ids=[VECTOR_STORE_ID],
    max_num_results=3
)

# Create the Complex Response Agent with handoff to human support
complex_response_agent = Agent(
    name="Especialista en Conocimiento C1DO1",
    handoff_description="Agente que busca respuestas detalladas en la base de conocimientos de C1DO1",
    instructions=prompt_with_handoff_instructions("""
    Eres un agente especializado de soporte para la empresa C1DO1 con acceso a su base de conocimientos.
    Tu trabajo es manejar consultas detalladas sobre los productos, servicios e información de la empresa C1DO1.

    Busca información en la base de conocimientos de la empresa usando la herramienta de búsqueda en vectores.

    REGLAS CRÍTICAS QUE DEBES SEGUIR:

    1. SOLO responde si encuentras información ESPECÍFICA directamente relacionada con la consulta del usuario en la base de conocimientos.
    
    2. NUNCA respondas con "No encontré información específica..." o mensajes similares. En lugar de eso, SIEMPRE haz un handoff al agente "Keisy - Especialista Humano" cuando no tengas información precisa.
    
    3. Si la herramienta de búsqueda no devuelve resultados útiles o si los resultados no responden exactamente a la pregunta, SIEMPRE TRANSFIERE al agente "Keisy - Especialista Humano".
    
    4. NO trates de ser útil proporcionando respuestas genéricas o sugerencias. Tu ÚNICA opción cuando no tienes información específica es TRANSFERIR al agente "Keisy - Especialista Humano".
    
    5. RECUERDA: Si no estás 100% seguro de la respuesta basada en la información encontrada, DEBES TRANSFERIR la consulta.

    Sé siempre profesional, detallado y responde siempre en español cuando SÍ tengas información específica.
    """),
    model="gpt-4o",
    tools=[file_search_tool],
    handoffs=[human_support_agent]
)

# Export the agent for use in other modules
__all__ = ["complex_response_agent"]
