"""
Agente de Almacenamiento Vectorial para C1DO1

Este módulo maneja el almacenamiento de respuestas proporcionadas por humanos
en la base de datos vectorial para futuras referencias, permitiendo que el sistema
aprenda de la experiencia humana.
"""

import os
import json
import tempfile
import asyncio
from datetime import datetime
from dotenv import load_dotenv

# Add parent directory to path to allow importing from tools
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the vector store admin tools
from tools.vector_store_admin import create_file, add_file_to_vector_store, check_vector_store_status

# Load environment variables
load_dotenv()

# Get vector store ID from environment variables
vector_store_id = os.getenv("VECTOR_STORE_ID")
if not vector_store_id:
    raise ValueError("VECTOR_STORE_ID not found in environment variables. Please run scripts/create_vector_store.py first.")

async def store_in_vector_database(question, answer, metadata=None):
    """
    Store a question-answer pair in the vector database.
    
    Args:
        question: The user's original question
        answer: The human expert's answer
        metadata: Optional metadata about the QA pair
        
    Returns:
        success: Boolean indicating if storage was successful
        file_id: ID of the stored file in OpenAI
    """
    if metadata is None:
        metadata = {}
    
    # Create a unique ID for this QA pair
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    qa_id = f"human_qa_{timestamp}"
    
    # Format the QA pair as a document
    qa_document = {
        "id": qa_id,
        "question": question,
        "answer": answer,
        "source": "human_expert",
        "timestamp": datetime.now().isoformat(),
        "metadata": metadata
    }
    
    print(f"[Almacenamiento] Creando documento QA: {len(question)} caracteres (pregunta) + {len(answer)} caracteres (respuesta)")
    
    # Create a temporary file
    temp_file_path = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as temp_file:
            temp_file_path = temp_file.name
            json.dump(qa_document, temp_file, indent=2)
            
        # Upload the file to OpenAI
        print("[Almacenamiento] Subiendo par Pregunta-Respuesta a la base de datos...")
        file_id = create_file(temp_file_path)
        
        # Add the file to the vector store
        result = add_file_to_vector_store(vector_store_id, file_id)
        
        # Check the status of the vector store files
        status = check_vector_store_status(vector_store_id)
        
        return True, file_id
        
    except Exception as e:
        print(f"[ERROR] Error al almacenar en la base de datos: {str(e)}")
        return False, None
        
    finally:
        # Clean up the temporary file
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)

async def main():
    """
    Test function for the Vector Storage Agent.
    """
    print("=== Prueba del Agente de Almacenamiento Vectorial ===")
    
    test_question = "¿Cuáles son los valores fundamentales de C1DO1?"
    test_answer = """Los valores fundamentales de C1DO1 son:
1. Innovación constante
2. Excelencia en servicio al cliente
3. Integridad en todas las operaciones
4. Colaboración y trabajo en equipo
5. Responsabilidad social y sostenibilidad

Estos valores guían todas nuestras decisiones y operaciones diarias."""
    
    print(f"Probando almacenamiento con pregunta: {test_question}")
    success, file_id = await store_in_vector_database(test_question, test_answer)
    
    if success:
        print(f"Almacenamiento exitoso del par Pregunta-Respuesta con ID: {file_id}")
    else:
        print("Fallo al almacenar el par Pregunta-Respuesta en la base de datos vectorial")

if __name__ == "__main__":
    asyncio.run(main()) 