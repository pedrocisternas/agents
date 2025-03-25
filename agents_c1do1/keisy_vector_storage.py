"""
Keisy Vector Storage for C1DO1

This module provides a single function to store Keisy's answers in the vector database.
It is designed to be minimally invasive and not affect other system functionality.
"""

import os
import json
import tempfile
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv()

# Get vector store ID and API key
VECTOR_STORE_ID = os.environ.get("VECTOR_STORE_ID")
API_KEY = os.environ.get("OPENAI_API_KEY")

# Initialize OpenAI client
client = OpenAI(api_key=API_KEY)

def store_keisy_answer(question, answer):
    """
    Store a question-answer pair from Keisy in the vector database.
    
    Args:
        question: The user's original question
        answer: Keisy's response
        
    Returns:
        success: Boolean indicating if the operation was successful
        message: A message describing the result or error
    """
    if not VECTOR_STORE_ID:
        print("⚠️ Vector store ID not found. Keisy's answer was not stored.")
        return False, "Vector store ID not found"
    
    temp_file_path = None
    try:
        # Create a temporary JSON file with the QA pair
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
            # Format the data as a JSON object
            qa_data = {
                "question": question,
                "answer": answer,
                "source": "Keisy - Especialista Humano",
                "date_added": datetime.now().isoformat()
            }
            
            json.dump(qa_data, temp_file, ensure_ascii=False, indent=2)
            temp_file_path = temp_file.name
        
        print(f"✓ Created QA document file: {temp_file_path}")
        
        # Upload the file to OpenAI
        with open(temp_file_path, "rb") as file_content:
            file_response = client.files.create(
                file=file_content,
                purpose="assistants"
            )
        
        file_id = file_response.id
        print(f"✓ Uploaded file with ID: {file_id}")
        
        # Add the file to the vector store
        result = client.vector_stores.files.create(
            vector_store_id=VECTOR_STORE_ID,
            file_id=file_id
        )
        
        print(f"✓ Added file to vector store: {result}")
        
        # Clean up temporary file
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)
            
        return True, f"Successfully stored Keisy's answer in the vector database"
        
    except Exception as e:
        error_message = str(e)
        print(f"❌ Error storing Keisy's answer: {error_message}")
        
        # Clean up temporary file if it exists
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except:
                pass
                
        return False, f"Error: {error_message}" 