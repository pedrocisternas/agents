"""
C1DO1 Knowledge Base Agent that searches information in a vector database.
This agent provides access to the company's internal documents and can
hand off to a web search agent if information is not found.
"""

import os
import asyncio
from dotenv import load_dotenv
from agents import Agent, Runner, set_default_openai_key

from tools.file_search import file_search
from search_web_agent import web_search_agent
# from search_openai_agent import search_openai_agent

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

# Create the C1DO1 knowledge base agent
database_agent = Agent(
    name="C1DO1 Knowledge Base Agent",
    instructions=f"""You are the official knowledge base agent for C1DO1 company. 
Your primary goal is to provide accurate information from the company's internal documents.

Search the company knowledge base for information using the file_search tool.
The vector store ID to use is: {vector_store_id}

If you cannot find information in the knowledge base, say "I need to search the web for this information" 
and hand off to the Web Search Agent.

Always be professional and answer in the question language.
""",
    model="gpt-4o",
    tools=[file_search],
    handoffs=[web_search_agent]
)

async def query_database_async(query):
    """
    Query the C1DO1 internal knowledge base.
    
    Args:
        query: The query to search for
        
    Returns:
        Information found in the knowledge base or a message indicating web search is needed
    """
    result = await Runner.run(database_agent, input=query)
    return result.final_output

async def main():
    # Test with a company-specific query
    kb_question = "Quién es el CEO de C1DO1?"
    print(f"Query for knowledge base: {kb_question}")
    kb_result = await Runner.run(database_agent, input=kb_question)
    print(f"Response: {kb_result.final_output}")
    
    # Test with a query that should trigger web search
    web_question = "Cuáles son las últimas tendencias en marketing digital para 2024?"
    print(f"\nQuery that should need web search: {web_question}")
    web_result = await Runner.run(database_agent, input=web_question)
    print(f"Response: {web_result.final_output}")

if __name__ == "__main__":
    asyncio.run(main()) 