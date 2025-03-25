# Sistema Multiagente de Soporte C1DO1

Un sistema de agentes inteligentes diseñado para proporcionar soporte automatizado con transiciones fluidas a especialistas humanos cuando sea necesario.

## Descripción General

Este proyecto implementa un sistema multiagente basado en las mejores prácticas del SDK de Agentes de OpenAI. El sistema está diseñado para:

1. Responder consultas básicas automáticamente
2. Buscar respuestas específicas en una base de conocimientos vectorial
3. Transferir (handoff) a especialistas humanos cuando no puede encontrar información relevante
4. Almacenar automáticamente las respuestas de los especialistas humanos para mejorar continuamente

Actualmente, el sistema está configurado para la empresa C1DO1, pero puede ser fácilmente adaptado para cualquier otra organización.

## Estructura del Proyecto

```
support-agentic-system/
├── main.py                   # Punto de entrada principal del sistema
├── utility_agents/           # Definiciones de los diferentes agentes
│   ├── simple_response_agent.py  # Agente para consultas simples
│   ├── complex_response_agent.py # Agente para búsqueda en base de conocimientos
│   └── human_support_agent.py    # Agente para simular especialista humano
├── utils/                    # Utilidades y herramientas compartidas
│   └── qa_vector_storage.py  # Funciones para almacenar QA en base de datos vectorial
├── tools/                    # Herramientas administrativas
│   └── vector_store_admin.py # Funciones para administrar la base de datos vectorial
├── scripts/                  # Scripts para configuración y mantenimiento
│   └── create_vector_store.py # Script para crear y configurar almacén vectorial
├── .env                      # Archivo de configuración de variables de entorno
├── docs/                     # Documentación (no incluido en este README)
└── pdfs/                     # Archivos PDF para entrenamiento (no incluido en este README)
```

## Componentes Principales

### Agentes

El sistema implementa un flujo de trabajo con tres agentes principales:

1. **Asistente Inicial (simple_response_agent.py)**: 
   - Maneja saludos, despedidas y consultas muy básicas
   - Transfiere consultas más complejas al Especialista en Conocimiento

2. **Especialista en Conocimiento (complex_response_agent.py)**:
   - Utiliza búsqueda vectorial para encontrar información específica
   - Solo responde cuando encuentra información relevante y precisa
   - Transfiere al especialista humano cuando no encuentra información adecuada

3. **Especialista Humano (human_support_agent.py)**:
   - Representa a un especialista humano llamado "Keisy"
   - En un entorno de producción, notificaría a un agente humano real
   - Sus respuestas se almacenan en la base de datos vectorial para futuras consultas

### Almacenamiento Vectorial

El sistema utiliza la API de OpenAI para crear y gestionar bases de datos vectoriales:

- **qa_vector_storage.py**: Funciones para almacenar pares de preguntas y respuestas
- **vector_store_admin.py**: Funciones administrativas para crear y gestionar almacenes vectoriales

### Configuración y Ejecución

- **main.py**: Script principal que ejecuta el sistema en modo interactivo
- **create_vector_store.py**: Script para configurar el almacén vectorial inicial

## Flujo de Trabajo

1. El usuario hace una consulta al sistema
2. El **Asistente Inicial** recibe la consulta y decide si:
   - Responder directamente (saludos, consultas muy básicas)
   - Transferir al **Especialista en Conocimiento**

3. El **Especialista en Conocimiento**:
   - Busca información relevante en la base de datos vectorial
   - Si encuentra información precisa, responde
   - Si no encuentra información relevante, transfiere al **Especialista Humano**

4. El **Especialista Humano** (Keisy):
   - Recibe las consultas que no pudieron ser respondidas automáticamente
   - En un entorno real, notificaría a un agente humano
   - Sus respuestas se almacenan automáticamente en la base de datos vectorial

## Guía de Instalación

### Requisitos Previos

- Python 3.9+
- Cuenta de OpenAI con acceso a la API
- Acceso a OpenAI Vector Stores

### Pasos de Instalación

1. **Clonar el repositorio**

```bash
git clone https://github.com/tu-usuario/support-agentic-system.git
cd support-agentic-system
```

2. **Crear y activar entorno virtual**

```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

3. **Instalar dependencias**

```bash
pip install openai python-dotenv
```

4. **Configurar variables de entorno**

Crea un archivo `.env` en la raíz del proyecto con la siguiente información:

```
OPENAI_API_KEY=tu_clave_api_openai
VECTOR_STORE_ID=  # Se completará automáticamente al ejecutar el script de creación
```

5. **Crear el almacén vectorial**

```bash
python scripts/create_vector_store.py
```

6. **Iniciar el sistema**

```bash
python main.py
```

## Adaptación para Otras Empresas

Para adaptar este sistema a otra empresa, sigue estos pasos:

1. **Modificar los agentes**:
   - Edita los archivos en `utility_agents/` para cambiar el nombre de la empresa, descripciones y reglas específicas
   - Ajusta los prompts para reflejar la identidad y conocimientos de la nueva empresa

2. **Configurar base de conocimientos**:
   - Crea un nuevo almacén vectorial para la empresa usando el script `create_vector_store.py`
   - Sube los documentos específicos de la empresa al almacén vectorial

3. **Personalizar respuestas**:
   - Ajusta los mensajes predeterminados en los agentes para reflejar el tono y estilo de la nueva empresa

4. **Configurar integración con especialistas humanos**:
   - Modifica `human_support_agent.py` para reflejar el flujo de trabajo de los especialistas de la nueva empresa

## Notas importantes

1. Este sistema requiere una API key de OpenAI con acceso a la funcionalidad de Vector Stores
2. Se recomienda probar exhaustivamente después de cualquier cambio en los agentes
3. La calidad de las respuestas depende directamente de la calidad de la información en la base de conocimientos


## Contacto

Pedro Cisternas - pgcisternas@gmail.com