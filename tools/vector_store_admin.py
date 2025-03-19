"""
Admin functions for creating and managing vector stores in OpenAI.
These functions are typically used for one-time operations like creating
vector stores and uploading files.
"""

import os
import requests
from io import BytesIO
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv
import logging
from openai import OpenAI

# Configure logging
logger = logging.getLogger("vector_store_admin")

# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

def create_file(file_path: str) -> str:
    """
    Upload a file to OpenAI's File API.
    
    Args:
        file_path: Path to the file (local) or URL
        
    Returns:
        The file ID from OpenAI
    """
    logger.info(f"Uploading file: {file_path}")
    
    try:
        if file_path.startswith("http://") or file_path.startswith("https://"):
            # Download the file content from the URL
            response = requests.get(file_path)
            file_content = BytesIO(response.content)
            file_name = file_path.split("/")[-1]
            file_tuple = (file_name, file_content)
            result = client.files.create(
                file=file_tuple,
                purpose="assistants"
            )
        else:
            # Handle local file path
            with open(file_path, "rb") as file_content:
                result = client.files.create(
                    file=file_content,
                    purpose="assistants"
                )
        
        logger.info(f"File uploaded successfully with ID: {result.id}")
        return result.id
    
    except Exception as e:
        logger.error(f"Error uploading file: {str(e)}")
        raise

def create_vector_store(name: str) -> str:
    """
    Create a new vector store in OpenAI.
    
    Args:
        name: Name of the vector store
        
    Returns:
        The vector store ID
    """
    logger.info(f"Creating vector store: {name}")
    
    try:
        vector_store = client.vector_stores.create(
            name=name
        )
        logger.info(f"Vector store created with ID: {vector_store.id}")
        return vector_store.id
    
    except Exception as e:
        logger.error(f"Error creating vector store: {str(e)}")
        raise

def add_file_to_vector_store(vector_store_id: str, file_id: str) -> Dict[str, Any]:
    """
    Add a file to a vector store.
    
    Args:
        vector_store_id: ID of the vector store
        file_id: ID of the file to add
        
    Returns:
        The response from the API
    """
    logger.info(f"Adding file {file_id} to vector store {vector_store_id}")
    
    try:
        result = client.vector_stores.files.create(
            vector_store_id=vector_store_id,
            file_id=file_id
        )
        logger.info(f"File added successfully: {result}")
        return result
    
    except Exception as e:
        logger.error(f"Error adding file to vector store: {str(e)}")
        raise

def check_vector_store_status(vector_store_id: str) -> Dict[str, Any]:
    """
    Check the status of files in a vector store.
    
    Args:
        vector_store_id: ID of the vector store
        
    Returns:
        List of files and their status
    """
    logger.info(f"Checking status of vector store {vector_store_id}")
    
    try:
        result = client.vector_stores.files.list(
            vector_store_id=vector_store_id
        )
        logger.info(f"Vector store status: {result}")
        return result
    
    except Exception as e:
        logger.error(f"Error checking vector store status: {str(e)}")
        raise

def list_vector_stores() -> List[Dict[str, Any]]:
    """
    List all vector stores available in the account.
    
    Returns:
        List of vector stores
    """
    logger.info("Listing all vector stores")
    
    try:
        result = client.vector_stores.list()
        return result.data
    
    except Exception as e:
        logger.error(f"Error listing vector stores: {str(e)}")
        raise 