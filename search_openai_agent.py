from agents import Agent, Runner
from agents import WebSearchTool  # Import the built-in web search tool
from dotenv import load_dotenv
from agents import set_default_openai_key
import os

load_dotenv()

openai_api_key = os.environ.get("OPENAI_API_KEY")
set_default_openai_key(openai_api_key)

# Create a web search tool instance
web_search = WebSearchTool()

# Create an agent with the web search tool
search_openai_agent = Agent(
    name="Assistant",
    instructions="You are a helpful assistant that can search the web for information when needed. Use the web search tool when you need to find current or specific information.",
    model="gpt-4o",
    tools=[web_search]  # Use OpenAI's built-in web search tool
)