"""
Script to upload files to an existing OpenAI vector store.
This allows you to add documents to your knowledge base for searching with a search_database_agent.
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
    add_file_to_vector_store,
    check_vector_store_status
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Get vector store ID from environment variables
VECTOR_STORE_ID = os.getenv("VECTOR_STORE_ID")
if not VECTOR_STORE_ID:
    raise ValueError("VECTOR_STORE_ID not found in environment variables. Please run create_vector_store.py first.")

def upload_file(file_path):
    """
    Upload a file to the vector store.
    
    Args:
        file_path: Path to the file (local) or URL
        
    Returns:
        The file ID from OpenAI
    """
    # Adjust path for files in parent directory
    adjusted_path = file_path
    if not file_path.startswith(('http://', 'https://')):
        # Check if the path is relative, and adjust it if needed
        if not os.path.isabs(file_path):
            adjusted_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), file_path)
    
    # Step 1: Upload the file
    logger.info(f"Uploading file from {file_path}...")
    file_id = create_file(adjusted_path)
    logger.info(f"File uploaded with ID: {file_id}")
    
    # Step 2: Add the file to the vector store
    logger.info(f"Adding file to vector store {VECTOR_STORE_ID}...")
    result = add_file_to_vector_store(VECTOR_STORE_ID, file_id)
    logger.info(f"File added to vector store: {result}")
    
    # Step 3: Check the status of the vector store files
    logger.info("Checking vector store status...")
    max_retries = 5
    for i in range(max_retries):
        status = check_vector_store_status(VECTOR_STORE_ID)
        logger.info(f"Status (attempt {i+1}/{max_retries}): {status}")
        
        # Check if all files are processed
        all_completed = all(file.status == "completed" for file in status.data)
        if all_completed:
            logger.info("All files have been processed successfully!")
            break
        
        if i < max_retries - 1:
            logger.info("Files are still being processing. Waiting for 5 seconds...")
            time.sleep(5)
    
    return file_id

def main():
    """
    Main function to upload files to the vector store.
    """
    # Using the example.pdf file from the pdfs directory
    files_to_upload = [
        "pdfs/example3.pdf"
    ]
    
    uploaded_file_ids = []
    for file_path in files_to_upload:
        try:
            file_id = upload_file(file_path)
            uploaded_file_ids.append(file_id)
            logger.info(f"Successfully uploaded file {file_path} with ID {file_id}")
        except Exception as e:
            logger.error(f"Failed to upload file {file_path}: {str(e)}")
            logger.error("Continuing with next file...")
    
    if uploaded_file_ids:
        logger.info("File upload completed successfully.")
        logger.info(f"Uploaded {len(uploaded_file_ids)} files to vector store {VECTOR_STORE_ID}")
        logger.info(f"File IDs: {uploaded_file_ids}")
    else:
        logger.error("No files were successfully uploaded.")
    
    return uploaded_file_ids

if __name__ == "__main__":
    main() 