from agents import Agent, Runner
from dotenv import load_dotenv
from agents import set_default_openai_key
import os

# Import the Tavily search tool
from tools.tavily_search import tavily_search

load_dotenv()

openai_api_key = os.environ.get("OPENAI_API_KEY")
set_default_openai_key(openai_api_key)

agent = Agent(
    name="Assistant",
    instructions="You are a helpful assistant that can search the web for information when needed. Use the search tool when you need to find current or specific information.",
    model="o3-mini",
    tools=[tavily_search]  # Add the Tavily search tool to the agent
)

result = Runner.run_sync(agent, "Search the latest tweets on X about the latest news in technology and AI. We are in the 16/03/2|")

print(result.final_output)
