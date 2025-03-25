"""
Main execution file for the C1DO1 agent system.

This script demonstrates the agent workflow with proper handoffs
according to the OpenAI Agents SDK best practices.
It accepts user input from the terminal in an interactive loop.
"""

import os
import asyncio
import sys
import json
from dotenv import load_dotenv

# Add the parent directory to the path so we can import the agents_c1do1 package
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents import Runner, set_default_openai_key, HandoffSpanData
from agents_c1do1.simple_response_agent import simple_response_agent
from agents_c1do1.human_support_agent import human_support_agent

# Load environment variables
load_dotenv()

# Get OpenAI API key
openai_api_key = os.environ.get("OPENAI_API_KEY")

if not openai_api_key:
    raise ValueError("OPENAI_API_KEY not found in environment variables")

# Set the default OpenAI API key
set_default_openai_key(openai_api_key)

# Custom run result handler to gather logs
class RunTracker:
    def __init__(self):
        self.handoffs = []
        self.vector_results = []
        self.agent_names = []
        self.contexts = []
    
    def reset(self):
        self.handoffs = []
        self.vector_results = []
        self.agent_names = []
        self.contexts = []
    
    def format_internal_logs(self):
        """Format internal logs for display"""
        logs = []
        
        # Add context
        if self.contexts:
            logs.append("Contexto: " + "\n".join(self.contexts))
        
        # Add handoffs
        if self.handoffs:
            logs.append("Handoffs: " + " -> ".join(self.handoffs))
        
        # Add agent names
        if self.agent_names:
            logs.append("Agentes utilizados: " + ", ".join(self.agent_names))
        
        # Add vector search results
        if self.vector_results:
            logs.append("Resultados de búsqueda en vectores: ")
            for result in self.vector_results:
                logs.append(f"- {result}")
        
        return "\n".join(logs)

# Create tracker
tracker = RunTracker()

async def process_query(query, conversation_history=None):
    """
    Process a user query through the agent workflow.
    
    Args:
        query: The user's message/query
        conversation_history: List of previous conversation messages
        
    Returns:
        The final response from the agent workflow
    """
    # Reset tracker
    tracker.reset()
    
    # Prepare context if available
    if conversation_history:
        context = "\n\nHistorial de conversación anterior:\n"
        for i, (user_msg, assistant_msg) in enumerate(conversation_history[-3:]):  # Show last 3 exchanges
            context += f"Usuario: {user_msg}\nAsistente: {assistant_msg}\n"
        context += f"\nConsulta actual: {query}"
        tracker.contexts.append("Conversación previa incluida")
        result = await Runner.run(simple_response_agent, input=context)
    else:
        context = query
        result = await Runner.run(simple_response_agent, input=query)
    
    # Extract handoffs and tool results from the run result
    handoff_to_keisy = False
    vector_search_results = []
    
    # Track the initial agent
    tracker.agent_names.append(simple_response_agent.name)
    
    # Go through the items in the run result
    for item in result.new_items:
        # Track handoffs
        if hasattr(item, 'to_agent') and hasattr(item, 'from_agent'):
            handoff_from = getattr(item.from_agent, 'name', 'Unknown')
            handoff_to = getattr(item.to_agent, 'name', 'Unknown')
            
            # Check specifically for handoff to Keisy
            if handoff_to == human_support_agent.name:
                handoff_to_keisy = True
                
            tracker.handoffs.append(f"{handoff_from} → {handoff_to}")
            tracker.agent_names.append(handoff_to)
        
        # Track file search results
        if hasattr(item, 'type') and item.type == 'file_search_call':
            try:
                if hasattr(item, 'results') and item.results:
                    for result_item in item.results:
                        if hasattr(result_item, 'text') and result_item.text:
                            # Get a snippet (first 100 chars)
                            text_snippet = result_item.text[:100] + "..." if len(result_item.text) > 100 else result_item.text
                            filename = getattr(result_item, 'filename', 'unknown')
                            score = getattr(result_item, 'score', 0)
                            vector_search_results.append(f"Archivo: {filename}, Relevancia: {score:.2f}, Extracto: {text_snippet}")
            except Exception as e:
                vector_search_results.append(f"Error al procesar resultados: {str(e)}")
    
    # Store vector search results
    tracker.vector_results = vector_search_results
    
    # If there was a handoff to Keisy, prompt for human input
    if handoff_to_keisy:
        print("\n------")
        print("TERMINAL DE KEISY")
        print("-------")
        keisy_response = input("Respuesta de Keisy: ")
        print("--------")
        return keisy_response
    
    # The result will contain the final response after all handoffs (if any)
    return result.final_output

async def interactive_mode():
    """
    Run the agent in interactive mode, accepting input from the terminal.
    """
    print("=== Sistema de Agentes C1DO1 - Modo Interactivo ===")
    print("Este sistema sigue las mejores prácticas del SDK de Agentes de OpenAI")
    print("implementando handoffs apropiados entre agentes.\n")
    print("Escribe 'salir', 'exit' o 'quit' para terminar la conversación.\n")
    
    conversation_history = []
    
    while True:
        try:
            # Get user input
            user_input = input("\nUsuario: ")
            
            # Check if the user wants to exit
            if user_input.lower() in ['salir', 'exit', 'quit']:
                print("\n¡Hasta luego! Gracias por usar el sistema de agentes C1DO1.")
                break
            
            print("\n-------")
            print("Procesando...")
            
            # Process the user's query
            response = await process_query(user_input, conversation_history)
            
            # Display internal logs
            internal_logs = tracker.format_internal_logs()
            print(internal_logs)
            print("---------")
            
            # Display the response to the user
            print(f"Agente: {response}")
            
            # Store the conversation
            conversation_history.append((user_input, response))
            
        except KeyboardInterrupt:
            print("\n\n¡Hasta luego! Gracias por usar el sistema de agentes C1DO1.")
            break
        except Exception as e:
            print(f"\n❌ Error: {str(e)}")
            print("Por favor, intenta nuevamente.")

async def main():
    """
    Main function to run the interactive mode.
    """
    await interactive_mode()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n¡Hasta luego! Gracias por usar el sistema de agentes C1DO1.")
        sys.exit(0)