# Guía para Crear Agentes con OpenAI Agents SDK

Crear un proyecto en Python con un entorno virtual e instalar el SDK de OpenAI Agents es un proceso sencillo que te permitirá desarrollar aplicaciones de inteligencia artificial de manera organizada y eficiente. A continuación, se presenta una guía paso a paso orientada a principiantes:

## 1. ¿Qué es un entorno virtual?

Un **entorno virtual** es una herramienta que permite aislar las dependencias y paquetes de Python para cada proyecto. Esto evita conflictos entre diferentes versiones de librerías utilizadas en distintos proyectos y garantiza que cada aplicación funcione con las versiones específicas que requiere.

## 2. ¿Qué es un SDK?

Un **SDK** (Software Development Kit) es un conjunto de herramientas, bibliotecas y documentación que facilitan el desarrollo de aplicaciones en una plataforma específica. En este caso, el SDK de OpenAI Agents proporciona los recursos necesarios para crear y gestionar agentes de inteligencia artificial.

## 3. Creación del proyecto y configuración del entorno virtual

Sigue estos pasos para configurar tu proyecto en macOS:

- **a. Abrir la Terminal:**
    
    Accede a la aplicación Terminal desde "Aplicaciones" > "Utilidades" > "Terminal".
    
- **b. Crear un directorio para el proyecto:**
    
    Decide dónde deseas ubicar tu proyecto y crea una carpeta para él. Por ejemplo, para crear una carpeta llamada `mi_proyecto` en el escritorio:
    
    ```bash
    cd ~/Escritorio
    mkdir mi_proyecto
    cd mi_proyecto
    ```
    
- **c. Crear y activar el entorno virtual:**
    
    Dentro del directorio del proyecto, crea un entorno virtual utilizando el módulo `venv`:
    
    ```bash
    python3 -m venv venv
    ```
    
    Esto creará una carpeta llamada `venv` que contendrá una instalación aislada de Python.
    
    Para activar el entorno virtual, ejecuta:
    
    ```bash
    source venv/bin/activate
    ```
    
    Al activarse, notarás que el prompt de la terminal muestra el nombre del entorno virtual, indicando que estás trabajando dentro de él.

## 4. Instalación de las dependencias necesarias

Con el entorno virtual activo, instala las dependencias necesarias utilizando `pip`:

```bash
pip install openai-agents python-dotenv
```

Este comando descargará e instalará:
- El SDK de OpenAI Agents para trabajar con agentes de IA
- Python-dotenv para gestionar variables de entorno desde un archivo .env

## 5. Configuración de la clave de API de OpenAI

Para interactuar con los servicios de OpenAI, necesitas una clave de API. Si aún no la tienes, regístrate en la plataforma de OpenAI y genera una clave desde tu panel de control.

Una vez obtenida, crea un archivo `.env` en la raíz de tu proyecto con el siguiente contenido:

```
OPENAI_API_KEY=tu_clave_de_api_aquí
```

Reemplaza `tu_clave_de_api_aquí` con la clave que obtuviste de OpenAI.

## 6. Creación de un agente básico

Con todo configurado, puedes crear un agente sencillo. Crea un archivo llamado `most_basic_agent.py` con el siguiente contenido:

```python
from agents import Agent, Runner
from dotenv import load_dotenv
from agents import set_default_openai_key
import os

# Cargar variables de entorno desde el archivo .env
load_dotenv()

# Obtener la clave de API de OpenAI y configurarla
openai_api_key = os.environ.get("OPENAI_API_KEY")
set_default_openai_key(openai_api_key)

# Definir el agente con instrucciones específicas
agent = Agent(
    name="Assistant",
    instructions="Eres un instructor de código con actitud",
    model="o3-mini"  # Puedes usar "gpt-4o" para un modelo más potente
)

# Ejecutar el agente con una solicitud
result = Runner.run_sync(agent, "Escribe un haiku sobre la recursión en programación.")

# Imprimir el resultado
print(result.final_output)
```

Este script define un agente y le solicita que genere un haiku sobre la recursión en programación.

## 7. Ejecutando tu primer agente

Para ejecutar el agente, asegúrate de que tu entorno virtual esté activado y ejecuta:

```bash
python most_basic_agent.py
```

Deberías ver un haiku sobre recursión en programación generado por el modelo de IA.

## 8. Entendiendo los componentes clave

### ¿Qué es un Agente?

Un **Agente** en el contexto de OpenAI Agents SDK es una entidad de IA que puede recibir instrucciones, procesar información y generar respuestas. Los componentes principales de un agente son:

- **name**: El nombre del agente, útil para identificarlo.
- **instructions**: Las instrucciones que definen el comportamiento y personalidad del agente.
- **model**: El modelo de lenguaje que utilizará el agente (por ejemplo, "o3-mini" o "gpt-4o").

### ¿Qué es un Runner?

Un **Runner** es el componente que se encarga de ejecutar el agente. El método `run_sync` ejecuta el agente de manera sincrónica, lo que significa que el programa esperará hasta que el agente complete su tarea antes de continuar.

## 9. Desactivación del entorno virtual

Una vez que hayas terminado de trabajar, puedes desactivar el entorno virtual con el comando:

```bash
deactivate
```

Esto restablecerá tu terminal al entorno Python global del sistema.

## 10. Creando un agente creador de contenido

Ahora que entendemos los conceptos básicos, vamos a crear un agente más avanzado que pueda generar contenido y guardarlo en archivos. Este ejemplo muestra cómo crear un agente especializado en la creación de contenido.

### ¿Qué son las herramientas (Tools)?

Las **herramientas** son funciones que permiten a los agentes interactuar con el mundo exterior. Pueden realizar acciones como guardar archivos, buscar información en bases de datos, o interactuar con APIs externas. Las herramientas amplían significativamente las capacidades de los agentes.

### Ejemplo de un agente creador de contenido

Crea un archivo llamado `content_creator_agent.py` con el siguiente contenido:

```python
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

# Definir herramientas para el agente

def save_content(content, content_type="blog"):
    """
    Guarda el contenido generado en un archivo.
    
    Args:
        content (str): El contenido a guardar
        content_type (str): El tipo de contenido (blog, tweet, etc.)
    
    Returns:
        dict: Información sobre el archivo guardado
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{content_type}_{timestamp}.txt"
    
    with open(filename, "w", encoding="utf-8") as file:
        file.write(content)
    
    return {
        "status": "success",
        "filename": filename,
        "message": f"Contenido guardado en {filename}"
    }

# Crear herramienta para guardar contenido
save_content_tool = Tool(
    name="save_content",
    description="Guarda el contenido generado en un archivo de texto",
    function=save_content
)

# Definir el agente creador de contenido
content_creator = Agent(
    name="CreadorDeContenido",
    instructions="""Eres un creador de contenido experto. Tu especialidad es crear contenido 
    atractivo, informativo y optimizado para SEO sobre temas de tecnología y programación.
    
    Cuando se te pida crear contenido:
    1. Analiza el tema solicitado
    2. Investiga los puntos clave que deben incluirse
    3. Crea un contenido estructurado con introducción, desarrollo y conclusión
    4. Incluye subtítulos relevantes para mejorar la legibilidad
    5. Utiliza un tono conversacional pero profesional
    
    Puedes crear diferentes tipos de contenido como blogs, tweets, o guiones para videos.""",
    model="o3-mini",  # Puedes usar "gpt-4o" para un modelo más potente
    tools=[save_content_tool]
)

# Solicitar al agente que cree contenido
tema = "Introducción a la Inteligencia Artificial para principiantes"
prompt = f"""Crea un artículo de blog sobre el tema: "{tema}".
El artículo debe tener aproximadamente 500 palabras y estar dirigido a principiantes
que no tienen conocimientos previos de programación o matemáticas avanzadas.
Incluye una introducción atractiva, 3-4 secciones principales, y una conclusión.
Cuando termines, guarda el contenido usando la herramienta save_content."""

# Ejecutar el agente
result = Runner.run_sync(content_creator, prompt)

# Imprimir el resultado final
print("\n--- Resultado de la ejecución del agente ---\n")
print(result.final_output)
```

### Explicación del código:

1. **Definición de herramientas**: Creamos una función `save_content` que guarda el contenido generado en un archivo de texto.

2. **Creación de la herramienta**: Utilizamos la clase `Tool` para convertir nuestra función en una herramienta que el agente puede utilizar.

3. **Configuración del agente**: Creamos un agente especializado en la creación de contenido y le proporcionamos acceso a la herramienta que hemos definido.

4. **Instrucciones detalladas**: Las instrucciones del agente son más específicas, indicándole exactamente cómo debe abordar la creación de contenido.

5. **Ejecución con un prompt específico**: Le pedimos al agente que cree un artículo sobre un tema específico y que utilice la herramienta para guardar el resultado.

## 11. Entendiendo las herramientas (Tools)

Las herramientas son una parte fundamental de los agentes avanzados. Permiten que los agentes realicen acciones concretas más allá de simplemente generar texto. Algunos aspectos importantes sobre las herramientas:

### Componentes de una herramienta:

- **name**: Un nombre único que identifica la herramienta.
- **description**: Una descripción que ayuda al agente a entender cuándo y cómo usar la herramienta.
- **function**: La función de Python que se ejecutará cuando el agente utilice la herramienta.

### Tipos de herramientas que puedes crear:

1. **Herramientas de almacenamiento**: Para guardar información en archivos o bases de datos.
2. **Herramientas de búsqueda**: Para buscar información en fuentes externas.
3. **Herramientas de API**: Para interactuar con servicios web externos.
4. **Herramientas de procesamiento**: Para realizar cálculos o transformaciones de datos.

### Beneficios de usar herramientas:

- Permiten que los agentes interactúen con el mundo exterior.
- Amplían significativamente las capacidades de los agentes.
- Facilitan la creación de aplicaciones prácticas y útiles.

## 12. Próximos pasos

A medida que te familiarices con los conceptos básicos de los agentes y las herramientas, podrás crear sistemas más complejos y potentes. Algunos posibles próximos pasos incluyen:

1. **Crear agentes con memoria**: Implementar agentes que puedan recordar conversaciones anteriores.
2. **Integrar con APIs externas**: Conectar tus agentes con servicios web como bases de datos, APIs de noticias, o servicios de clima.
3. **Crear interfaces de usuario**: Desarrollar interfaces web o de línea de comandos para interactuar con tus agentes.
4. **Implementar sistemas multiagente**: Crear sistemas donde varios agentes colaboren para resolver problemas complejos.

## Recursos adicionales

Para profundizar en el uso del SDK de OpenAI Agents y la gestión de entornos virtuales, puedes consultar los siguientes recursos:

- [Documentación oficial del SDK de OpenAI Agents](https://platform.openai.com/docs/guides/agents-sdk)
- [Repositorio de GitHub del SDK de OpenAI Agents](https://github.com/openai/openai-agents-python)
- [Guía de entornos virtuales en Python](https://docs.python.org/es/3.13/tutorial/venv.html)

Además, este video proporciona una introducción práctica al uso de entornos virtuales en Python:

[Configurando OpenAI con ambiente virtual en Python, usando venv](https://www.youtube.com/watch?v=y1IkrPORySc)

## 13. Añadiendo capacidades de búsqueda web con Tavily

Una de las limitaciones de los modelos de lenguaje es que su conocimiento está limitado a la información con la que fueron entrenados. Para superar esta limitación, podemos dotar a nuestros agentes con la capacidad de buscar información actualizada en la web utilizando APIs de búsqueda como Tavily.

### ¿Qué es Tavily?

Tavily es una API de búsqueda diseñada específicamente para aplicaciones de IA. Proporciona resultados de búsqueda web relevantes y actualizados que pueden ser utilizados por agentes de IA para responder preguntas con información actual.

### Configuración de Tavily

Para utilizar Tavily, necesitas seguir estos pasos:

1. **Registrarse en Tavily**: Visita [Tavily](https://tavily.com/) y crea una cuenta.
2. **Obtener una clave de API**: Una vez registrado, obtén tu clave de API desde el panel de control.
3. **Instalar el SDK de Tavily**: Instala el SDK de Python para Tavily:

```bash
pip install tavily-python
```

4. **Añadir la clave de API a tu archivo .env**:

```
OPENAI_API_KEY=tu_clave_de_openai_aquí
TAVILY_API_KEY=tu_clave_de_tavily_aquí
```

### Creando una herramienta de búsqueda con Tavily

A continuación, crearemos una herramienta de búsqueda utilizando Tavily. Crea un archivo llamado `tools/tavily_search.py`.

### Beneficios de añadir capacidades de búsqueda web:

1. **Información actualizada**: El agente puede acceder a información actualizada más allá de su fecha de corte de entrenamiento.
2. **Respuestas más precisas**: Puede proporcionar respuestas basadas en hechos verificables en lugar de depender únicamente de su conocimiento interno.
3. **Mayor utilidad**: El agente se vuelve más útil para consultas sobre eventos actuales, tecnologías emergentes, o información específica.

### Consideraciones importantes:

1. **Uso de API**: El uso de la API de Tavily puede tener costos asociados según tu plan.
2. **Privacidad**: Las consultas se envían a servidores externos, por lo que debes considerar la privacidad de la información.
3. **Fiabilidad**: Aunque Tavily proporciona resultados de alta calidad, la información de la web puede no ser siempre precisa o confiable.

## 14. Próximos pasos avanzados

Ahora que has aprendido a crear agentes básicos y a dotarlos de capacidades de búsqueda web, puedes explorar funcionalidades más avanzadas:

1. **Agentes con múltiples herramientas**: Combina la herramienta de búsqueda con otras herramientas como generación de imágenes, análisis de datos, o interacción con APIs específicas.
2. **Agentes con memoria persistente**: Implementa sistemas de almacenamiento para que los agentes recuerden conversaciones e información entre sesiones.
3. **Interfaces de usuario**: Desarrolla interfaces web o de aplicación para interactuar con tus agentes de manera más amigable.
4. **Sistemas multiagente**: Crea sistemas donde varios agentes especializados colaboren para resolver problemas complejos.

## Recursos adicionales

Para profundizar en el uso de herramientas de búsqueda y otras capacidades avanzadas:

- [Documentación oficial de Tavily](https://docs.tavily.com/)
- [Guía avanzada de OpenAI Agents](https://platform.openai.com/docs/guides/agents-sdk/advanced-usage)
- [Ejemplos de implementación de agentes con herramientas](https://github.com/openai/openai-agents-python/tree/main/examples)

Con estas herramientas y conocimientos, estás listo para crear agentes de IA potentes y útiles que puedan interactuar con el mundo real y proporcionar información actualizada y relevante. 