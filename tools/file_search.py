"""
File search tool for searching information in OpenAI vector stores.
This tool enables semantic search on documents stored in vector stores.
"""

import os
from typing import Optional
import logging
from dotenv import load_dotenv
from openai import OpenAI
from c1do1_agents import function_tool, RunContextWrapper

# Configure logging
logger = logging.getLogger("file_search")

# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

async def perform_file_search(vector_store_id: str, query: str, max_results: int = 5) -> str:
    logger.info(f"Searching for '{query}' in vector store {vector_store_id}")
    
    try:
        response = client.responses.create(
            model="gpt-4o",
            input=query,
            tools=[{
                "type": "file_search",
                "vector_store_ids": [vector_store_id],
                "max_num_results": max_results
            }],
            include=["file_search_call.results"]
        )
        
        # Extract and format the search results
        results_text = f"Document search results for '{query}':\n\n"
        
        # Process the response to extract relevant information
        for item in response.output:
            if item.type == "file_search_call" and hasattr(item, "search_results") and item.search_results:
                for i, result in enumerate(item.search_results):
                    results_text += f"{i + 1}. File: {result.file.filename}\n"
                    results_text += f"   Content: {result.text}\n\n"
            elif item.type == "message":
                for content in item.content:
                    if content.type == "output_text":
                        results_text += f"AI Analysis: {content.text}\n\n"
                        # Add file citations if available
                        if hasattr(content, "annotations") and content.annotations:
                            results_text += "Citations:\n"
                            for annotation in content.annotations:
                                if annotation.type == "file_citation":
                                    results_text += f"- {annotation.filename}\n"
        
        return results_text
    
    except Exception as e:
        logger.error(f"Error searching files: {str(e)}")
        return f"Error searching files: {str(e)}"

@function_tool
async def file_search(
    ctx: RunContextWrapper,
    vector_store_id: str,
    query: str,
    max_results: Optional[int] = None,
) -> str:
    """
    Search for information in files stored in a vector database.
    
    Args:
        vector_store_id: The ID of the vector store to search in
        query: The search query to find relevant information
        max_results: Number of results to return (default: 5)
        
    Returns:
        Information found in the files related to the query
    """
    # Apply defaults inside the function
    if max_results is None:
        max_results = 5
    
    return await perform_file_search(
        vector_store_id=vector_store_id,
        query=query,
        max_results=max_results
    ) 