# Sistema de Soporte Agentic C1DO1

Un sistema de agentes inteligentes diseñado para proporcionar soporte automatizado con transiciones fluidas a especialistas humanos cuando sea necesario, integrado con WhatsApp Business y Notion para una gestión completa de tickets de soporte.

## Descripción General

Este proyecto implementa un sistema multiagente basado en el SDK de Agentes de OpenAI, con integración completa con WhatsApp Business API y Notion para:

1. Recibir consultas de usuarios a través de WhatsApp
2. Responder automáticamente a preguntas básicas usando IA
3. Buscar respuestas específicas en una base de conocimientos vectorial cuando sea necesario
4. Derivar consultas complejas a especialistas humanos a través de Notion
5. Almacenar todas las respuestas en una base de datos vectorial para mejorar continuamente

El sistema está configurado para la empresa C1DO1, pero puede ser adaptado fácilmente para cualquier organización que requiera un sistema de soporte híbrido que combine IA y especialistas humanos.

## Estructura del Proyecto

```
support-agentic-system/
├── whatsapp_simple_integration.py  # Componente principal de integración WhatsApp-Notion
├── main.py                         # Punto de entrada para modo interactivo (sin WhatsApp)
├── .env                            # Archivo de configuración de variables de entorno
├── whatsapp_integration/           # Módulos para la API de WhatsApp Business
│   ├── whatsapp_client.py          # Cliente para enviar mensajes de WhatsApp
│   ├── auto_responder.py           # Sistema de respuesta automática para mensajes de WhatsApp (uso independiente)
│   ├── test_client.py              # Herramientas de prueba para la integración
│   └── __init__.py                 # Inicializador del paquete
├── utility_agents/                 # Definiciones de los diferentes agentes
│   ├── simple_response_agent.py    # Agente para consultas simples
│   ├── complex_response_agent.py   # Agente para búsqueda en base de conocimientos
│   ├── human_support_agent.py      # Agente para derivación a especialista humano
│   └── __init__.py                 # Inicializador del paquete
├── utils/                          # Utilidades y herramientas compartidas
│   ├── qa_vector_storage.py        # Funciones para almacenar Q&A en base vectorial
│   └── __init__.py                 # Inicializador del paquete
├── tools/                          # Herramientas administrativas
│   └── vector_store_admin.py       # Funciones para gestionar base de datos vectorial
├── scripts/                        # Scripts para configuración y mantenimiento
│   ├── create_vector_store.py      # Script para crear y configurar almacén vectorial
│   └── __init__.py                 # Inicializador del paquete
├── docs/                           # Documentación adicional
└── pdfs/                           # Archivos PDF para entrenamiento
```

## Componentes Principales

### 1. Integración con WhatsApp Business API

El sistema utiliza la API de WhatsApp Business para recibir y enviar mensajes:

- **whatsapp_simple_integration.py**: Servidor principal que maneja webhooks de WhatsApp y orquesta todo el sistema
- **whatsapp_client.py**: Cliente para enviar mensajes a través de la API de WhatsApp Business
- **auto_responder.py**: Sistema automático de respuesta para mensajes de WhatsApp (uso independiente)

El sistema implementa:
- Recepción de webhooks desde Meta para mensajes entrantes
- Procesamiento asíncrono de mensajes a través de colas
- Detección de mensajes salientes para identificar respuestas manuales
- Mantenimiento de historiales de conversación por número de teléfono

### 2. Integración con Notion para Especialistas Humanos

Cuando una consulta requiere atención humana, el sistema:

1. Crea un ticket en una base de datos de Notion con:
   - La pregunta original
   - El número de teléfono del usuario
   - Un campo para la respuesta
   - Un ID único para seguimiento

2. Recibe la respuesta del especialista humano a través de un webhook desde Notion
3. Envía automáticamente la respuesta al usuario por WhatsApp
4. Almacena la respuesta en la base de datos vectorial para futuras consultas

### 3. Sistema de Agentes Inteligentes

El sistema implementa un flujo de trabajo con tres agentes principales:

1. **Asistente Inicial (simple_response_agent.py)**: 
   - Maneja saludos, despedidas y consultas muy básicas
   - Transfiere consultas más complejas al Especialista en Conocimiento

2. **Especialista en Conocimiento (complex_response_agent.py)**:
   - Utiliza búsqueda vectorial para encontrar información específica
   - Solo responde cuando encuentra información relevante y precisa
   - Transfiere al especialista humano cuando no encuentra información adecuada

3. **Especialista Humano (human_support_agent.py)**:
   - Gestiona consultas que requieren intervención humana
   - Crea tickets en Notion para que los especialistas respondan
   - Conecta las respuestas de los especialistas con el usuario

### 4. Almacenamiento Vectorial

El sistema utiliza la API de OpenAI para crear y gestionar bases de datos vectoriales:

- **qa_vector_storage.py**: Funciones para almacenar pares pregunta-respuesta
- **vector_store_admin.py**: Funciones administrativas para gestionar almacenes vectoriales
- Las respuestas de los especialistas humanos se almacenan automáticamente para mejorar el sistema

## Flujo de Trabajo Completo

1. **Recepción de mensaje por WhatsApp**:
   - El webhook de WhatsApp recibe el mensaje y lo pone en cola para procesar
   - Se mantiene historial de conversaciones por número de teléfono

2. **Procesamiento con agentes**:
   - El mensaje se procesa con el Asistente Inicial
   - Si es necesario, se transfiere al Especialista en Conocimiento
   - Si no se encuentra información, se deriva al Especialista Humano

3. **Flujo con intervención humana**:
   - Se crea un ticket en Notion con la consulta y datos del usuario
   - El especialista humano responde a través de Notion usando el botón "Enviar"
   - El webhook de Notion recibe la respuesta
   - La respuesta se envía al usuario vía WhatsApp
   - La respuesta se almacena en la base de datos vectorial

4. **Mejora continua**:
   - Todas las respuestas de especialistas humanos se almacenan automáticamente
   - El sistema mejora con cada interacción gracias al almacenamiento vectorial

## Guía de Instalación

### Requisitos Previos

- Python 3.9+
- Cuenta de OpenAI con acceso a la API y Vector Stores
- Cuenta de desarrollador en Meta para la API de WhatsApp Business
- Cuenta en Notion con permisos para crear bases de datos
- Servidor accesible desde internet (para webhooks) o ngrok

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
pip install openai python-dotenv aiohttp requests
```

4. **Configurar variables de entorno**

Crea un archivo `.env` en la raíz del proyecto con la siguiente información:

```
# OpenAI
OPENAI_API_KEY=tu_clave_api_openai
VECTOR_STORE_ID=tu_vector_store_id  # Se genera al ejecutar create_vector_store.py

# WhatsApp Business API
WHATSAPP_ACCESS_TOKEN=tu_token_whatsapp
WHATSAPP_PHONE_NUMBER_ID=tu_phone_number_id
WHATSAPP_VERIFY_TOKEN=tu_verify_token  # Define un token personalizado para verificación
WHATSAPP_API_VERSION=v22.0

# Notion
NOTION_API_KEY=tu_api_key_notion
NOTION_DATABASE_ID=tu_database_id_notion
```

5. **Crear el almacén vectorial**

```bash
python scripts/create_vector_store.py
```

6. **Configurar Notion**

Crea una base de datos en Notion con las siguientes propiedades:
- Pregunta (título): Pregunta del usuario
- Respuesta (texto enriquecido): Campo para la respuesta del especialista
- Celular (texto enriquecido): Número de teléfono del usuario
- ID (texto enriquecido): Identificador único del ticket

Añade un botón "Enviar" que active una automatización para enviar un webhook al servidor.

7. **Configurar Webhooks de WhatsApp**

En el panel de desarrolladores de Meta:
- Configura un webhook para apuntar a tu servidor: `https://tu-servidor.com/webhook`
- Configura el "Verify Token" con el mismo valor que usaste en WHATSAPP_VERIFY_TOKEN

8. **Iniciar el servidor**

```bash
python whatsapp_simple_integration.py
```

Para desarrollo local, usa ngrok para exponer el puerto 8080:

```bash
ngrok http 8080
```

## Adaptación para Otras Empresas

Para adaptar este sistema a otra empresa:

1. **Modificar los agentes**:
   - Edita los archivos en `utility_agents/` para cambiar el nombre, descripciones y reglas
   - Ajusta los prompts para reflejar la identidad y conocimientos de la nueva empresa

2. **Configurar base de conocimientos**:
   - Crea un nuevo almacén vectorial usando `create_vector_store.py`
   - Sube los documentos específicos de la empresa al almacén vectorial

3. **Personalizar plantillas de Notion**:
   - Adapta la estructura de la base de datos de Notion según necesidades específicas
   - Ajusta las automatizaciones en Notion para funcionar con tu sistema

4. **Configurar WhatsApp Business**:
   - Obtén credenciales para la API de WhatsApp Business para la nueva empresa
   - Actualiza el archivo `.env` con las nuevas credenciales

## Notas Importantes

1. El sistema requiere acceso a la API de OpenAI con funcionalidad de Vector Stores
2. Para recibir webhooks, el servidor debe ser accesible desde internet
3. El secreto del webhook de Notion está configurado como 'soporte123' en el código, asegúrate de cambiarlo en producción
4. La calidad de las respuestas depende directamente de la calidad de la información en la base de conocimientos
5. Asegúrate de cumplir con regulaciones de protección de datos al manejar información de usuarios

## Contacto

Pedro Cisternas - pgcisternas@gmail.com