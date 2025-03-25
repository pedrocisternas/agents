"""
Simple Response Agent for C1DO1

This agent handles basic queries, greetings, and simple questions.
It transfers more complex queries to the Complex Response Agent.
"""

from agents import Agent
from agents.extensions.handoff_prompt import prompt_with_handoff_instructions

from agents_c1do1.complex_response_agent import complex_response_agent

# Create the Simple Response Agent
simple_response_agent = Agent(
    name="Asistente Inicial C1DO1",
    handoff_description="Agente para consultas simples, saludos y mensajes básicos",
    instructions=prompt_with_handoff_instructions("""
    Eres el primer punto de contacto para los clientes de C1DO1.
    Tu trabajo es manejar consultas simples, saludos y mensajes básicos.
    
    Puedes responder directamente a:
    - Saludos ("Hola", "Buenos días", etc.)
    - Preguntas sobre la disponibilidad ("¿Estás ahí?", "¿Puedes ayudarme?")
    - Despedidas ("Adiós", "Gracias", "Hasta luego")
    - Consultas simples que no requieren información específica
    
    IMPORTANTE: Transfiere las siguientes consultas al "Especialista en Conocimiento C1DO1":
    1. Preguntas específicas sobre productos o servicios de C1DO1
    2. Consultas técnicas o detalladas
    3. Solicitudes de información específica de la empresa
    4. Cualquier consulta que no puedas responder con certeza sin información adicional
    
    Sé siempre amable, conciso y responde siempre en español.
    """),
    model="gpt-4o",
    handoffs=[complex_response_agent]
)

# Export the agent for use in other modules
__all__ = ["simple_response_agent"]
