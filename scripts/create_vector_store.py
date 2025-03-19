"""
Script to create a new OpenAI vector store for storing document embeddings.
"""

import os
import sys
import time
from dotenv import load_dotenv
import logging

# Add parent directory to path to allow importing from tools
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.vector_store_admin import (
    create_file,
    create_vector_store,
    add_file_to_vector_store,
    check_vector_store_status,
    list_vector_stores
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def main():
    """
    Main function to demonstrate vector store creation and file upload.
    """
    # Step 1: Create a vector store
    vector_store_name = "knowledge_base"
    logger.info(f"Creating vector store named '{vector_store_name}'...")
    vector_store_id = create_vector_store(vector_store_name)
    logger.info(f"Vector store created with ID: {vector_store_id}")
    
    # Step 2: List all vector stores
    logger.info("Listing all available vector stores...")
    vector_stores = list_vector_stores()
    logger.info(f"Available vector stores: {vector_stores}")
    
    logger.info("Vector store creation completed.")
    logger.info(f"Vector store ID: {vector_store_id}")
    
    # Save the vector store ID to .env file
    update_env_with_vector_store_id(vector_store_id)
    
    return vector_store_id

def update_env_with_vector_store_id(vector_store_id):
    """
    Update the .env file with the vector store ID.
    """
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
    
    # Read existing .env file
    with open(env_path, 'r') as file:
        lines = file.readlines()
    
    # Check if VECTOR_STORE_ID already exists in the file
    vector_store_line_exists = False
    for i, line in enumerate(lines):
        if line.startswith('VECTOR_STORE_ID='):
            lines[i] = f'VECTOR_STORE_ID={vector_store_id}\n'
            vector_store_line_exists = True
            break
    
    # If VECTOR_STORE_ID doesn't exist, add it
    if not vector_store_line_exists:
        lines.append(f'VECTOR_STORE_ID={vector_store_id}\n')
    
    # Write back to .env file
    with open(env_path, 'w') as file:
        file.writelines(lines)
    
    logger.info(f"Updated .env file with VECTOR_STORE_ID={vector_store_id}")

if __name__ == "__main__":
    main() 