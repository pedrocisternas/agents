"""
Simple web search agent using Tavily search API.
This agent is designed to be used as a handoff target for other agents.
"""

from agents import Agent, Runner
import asyncio
from dotenv import load_dotenv
import os
from agents import set_default_openai_key

# Import the Tavily search tool
from tools.tavily_search import tavily_search

# Load environment variables to get API keys
load_dotenv()
openai_api_key = os.environ.get("OPENAI_API_KEY")
set_default_openai_key(openai_api_key)

# Create a web search agent
web_search_agent = Agent(
    name="Web Search Agent",
    instructions="You are a helpful assistant that searches the web for information. Use the search tool to find up-to-date information on any topic when needed.",
    model="gpt-4o",
    tools=[tavily_search]
)

async def search_web(query):
    """
    Search the web for information using the web search agent.
    
    Args:
        query: Query to search for
        
    Returns:
        Response from the web search agent
    """
    result = await Runner.run(web_search_agent, input=query)
    return result.final_output

# Example usage when running this script directly
async def main():
    query = "What is the latest news about artificial intelligence?"
    print(f"Searching for: {query}")
    response = await search_web(query)
    print(f"Response: {response}")

if __name__ == "__main__":
    asyncio.run(main()) 