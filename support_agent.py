"""
C1DO1 Support Agent with triage capabilities.
This agent coordinates between internal knowledge base searches and web searches
based on the type of query and availability of information.
"""

import os
import asyncio
from dotenv import load_dotenv
from agents import Agent, Runner, set_default_openai_key

# Import the file search tool and web search agent
from tools.file_search import file_search
from search_web_agent import web_search_agent
from search_database_agent import database_agent

# Load environment variables
load_dotenv()

# Get OpenAI API key
openai_api_key = os.environ.get("OPENAI_API_KEY")
if not openai_api_key:
    raise ValueError("OPENAI_API_KEY not found in environment variables")

# Set the default OpenAI API key
set_default_openai_key(openai_api_key)

# Create a triage agent that coordinates between knowledge base and web search
triage_agent = Agent(
    name="C1DO1 Support Assistant",
    instructions="""You are the official support assistant for C1DO1 company.
Your primary goal is to help customers and employees with questions about C1DO1 products, services, and company information.

You have two specialized assistants at your disposal:
1. C1DO1 Knowledge Base Agent - searches the company's internal vector database
2. Web Search Agent - searches the internet for general information

Decision process:
- First, always try using the C1DO1 Knowledge Base Agent for any company-specific information.
- If the Knowledge Base Agent says they don't have the requested information or need to search the web, 
  hand off to the Web Search Agent.
- For questions that are clearly about general information or current events not specific to C1DO1,
  you can hand off directly to the Web Search Agent.

Always be professional and respond in the same language as the question.
""",
    model="gpt-4o",
    handoffs=[database_agent, web_search_agent]
)

async def query_support(query):
    """
    Query the C1DO1 support system through the triage agent.
    The triage agent will decide whether to use the knowledge base or web search.
    
    Args:
        query: The query to search for
        
    Returns:
        Response from either the knowledge base or web search
    """
    result = await Runner.run(triage_agent, input=query)
    return result.final_output

async def main():
    # Test a query that should be in the knowledge base
    kb_question = "Quién es el CEO?"
    print(f"Query about C1DO1: {kb_question}")
    kb_result = await query_support(kb_question)
    print(f"Response: {kb_result}")
    
    # Test a query that should trigger web search
    web_question = "Cuántas rondas de financiación ha recibido C1DO1?"
    print(f"\nQuery requiring web search: {web_question}")
    web_result = await query_support(web_question)
    print(f"Response: {web_result}")

if __name__ == "__main__":
    asyncio.run(main()) 