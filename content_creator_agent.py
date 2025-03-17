from agents import Agent, Runner, Tool
from dotenv import load_dotenv
from agents import set_default_openai_key
import os
import json
from datetime import datetime

# Cargar variables de entorno desde el archivo .env
load_dotenv()

# Obtener la clave de API de OpenAI y configurarla
openai_api_key = os.environ.get("OPENAI_API_KEY")
set_default_openai_key(openai_api_key)
