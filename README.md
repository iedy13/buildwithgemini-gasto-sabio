# GastoSabio 🇲🇽 — Gestor Inteligente de Gastos y Finanzas Personales

GastoSabio es un asistente de finanzas personales diseñado específicamente para usuarios en México. Permite registrar transacciones y gastos cotidianos (efectivo, tarjeta de débito/crédito, Tarjeta de Movilidad Integrada), consultar y gestionar el historial financiero en Firestore, calcular conversiones de divisas en tiempo real, ejecutar cálculos analíticos en un sandbox seguro de Python, recordar el contexto financiero a largo plazo y generar contenido visual con modelos generativos de Google en Vertex AI.

![GastoSabio Demo](demo.gif)

---

## 🚀 Capacidades y Herramientas Implementadas

A diferencia de un simple chatbot, GastoSabio implementa herramientas funcionales conectadas a servicios reales de Google Cloud y APIs públicas:

### 1. Gestión de Gastos en Base de Datos (Cloud Firestore)
- **`log_expense`**: Registra un nuevo gasto con monto, categoría (alimentos, transporte, servicios, despensa, etc.), método de pago, fecha y notas detalladas en la colección `expenses` de Firestore (`qwiklabs-gcp-04-efabffc82211`).
- **`list_expenses`**: Consulta y recupera los registros de gastos almacenados en Firestore para auditoría y visualización de resúmenes.
- **`edit_expense`**: Modifica campos de una transacción existente (monto, categoría, método de pago, fecha, notas).
- **`delete_expense`**: Elimina transacciones específicas de Firestore cuando el usuario lo solicita.

### 2. Conversión de Divisas en Tiempo Real (API Financiera)
- **`get_exchange_rate`**: Consulta cotizaciones y tasas de cambio en vivo entre divisas (ej. USD/MXN, EUR/MXN) mediante la API pública de tipos de cambio de libre acceso (`open.er-api.com`), permitiendo al agente convertir compras en moneda extranjera a pesos mexicanos de forma automática.

### 3. Generación Visual de Insignias (Vertex AI & Cloud Storage)
- **`generate_savings_badge`**: Genera insignias personalizadas de metas de ahorro y control de gastos utilizando el modelo **`gemini-3.1-flash-lite-image`** en la región `global`. Guarda la imagen generada en la memoria del agente (`tool_context.save_artifact`) y la sube al bucket público de Cloud Storage (`gasto-sabio-media-qwiklabs-gcp-04-efabffc82211`), devolviendo una URL pública HTTPS accesible directamente en las respuestas del chat.

### 4. Generación de Video Educativo (Google Omni Model)
- **`generate_financial_tip_video`**: Genera clips de video explicativos o de animación 3D con consejos de finanzas utilizando el modelo Omni multimodal **`gemini-omni-flash-preview`** en la región `global`. Guarda el artefacto en el contexto y sube el archivo resultante en formato MP4 a Google Cloud Storage.

### 5. Memoria de Largo Plazo (Vertex AI Memory Bank)
- Integrado con **`PreloadMemoryTool`** y **`VertexAiMemoryBankService`** (`shared://memory`).
- Mediante un callback automático `after_agent_callback`, el agente almacena y recuerda de manera persistente las preferencias financieras del usuario (rutas habituales como Metro Taxqueña, tiendas de conveniencia preferidas, metas de ahorro) a través de distintas sesiones.

### 6. Ejecución de Código en Entorno Seguro (Agent Engine Code Sandbox)
- Provisto con **`AgentEngineSandboxCodeExecutor`** vinculado a un entorno de ejecución seguro en Agent Platform (`projects/1095643609675/locations/us-central1/reasoningEngines/2669147489554137088/sandboxEnvironments/7181707037179379712`).
- Ejecuta código Python aislado para proyecciones matemáticas, cálculos de interés compuesto y desviaciones presupuestarias.

### 7. Interfaz Visual A2UI (Agent-to-User Interface)
- Configurado con **`A2uiSchemaManager` (v0.8)** y el **Basic Catalog**.
- Devuelve tarjetas visuales estructuradas (`Card`, `Column`, `Row`, `Text`, `Image`) procesadas por el callback `after_model_callback`.

---

## 📌 Estado de Funcionalidades Planificadas

- [x] Registro y persistencia de gastos en Firestore (`log_expense`, `list_expenses`, `edit_expense`, `delete_expense`)
- [x] Memoria a largo plazo con Vertex AI Memory Bank
- [x] Consulta de divisas en tiempo real (`get_exchange_rate`)
- [x] Generación de medallas visuales de ahorro con Gemini Flash Lite Image
- [x] Generación de video con modelo Omni (`gemini-omni-flash-preview`)
- [x] Ejecución de cálculos financieros en Sandbox seguro de Agent Engine
- [x] Interfaz y proxy web en FastAPI con soporte A2UI
- [ ] *Planificado (no implementado):* Extracción multimodal automática de tickets/facturas físicas mediante OCR y visión continua (`parse_receipt`).

---

## 🛠️ Arquitectura del Proyecto

```
gasto-sabio/
├── app/
│   ├── agent.py               # Definición del agente principal (root_agent), prompts y herramientas
│   ├── a2ui_utils.py          # Utilidades para serialización del protocolo A2UI v0.8
│   ├── fast_api_app.py        # Backend FastAPI de servicio
│   └── app_utils/
│       └── services.py        # Configuración de servicios compartidos (Memory Bank, Sessions, Artifacts)
├── frontend/
│   ├── main.py                # Proxy FastAPI ligero que habla el protocolo A2A con el agente
│   ├── requirements.txt       # Dependencias del proxy y frontend
│   └── static/
│       └── index.html         # Interfaz de chat web interactiva con renderizador A2UI integrado
├── demo.gif                   # Grabación GIF optimizada del flujo de la demo
├── agents-cli-manifest.yaml   # Manifiesto de despliegue para Agent Runtime
└── pyproject.toml             # Dependencias del proyecto ADK
```

---

## 💻 Instrucciones de Ejecución Local

### Prerrequisitos
- Python 3.11+
- Administrador de paquetes `uv`
- Google Cloud SDK (`gcloud`) autenticado con Application Default Credentials:
  ```bash
  gcloud auth application-default login
  ```

### 1. Ejecutar el Agente en el Playground Local
Para correr el agente localmente con recarga en vivo y conectado al Memory Bank:

```bash
cd gasto-sabio
uv run adk web . --port 8080 --reload_agents --memory_service_uri=agentengine://2669147489554137088
```

### 2. Ejecutar la Interfaz Web (Frontend de Chat)
Para iniciar el servidor proxy y la interfaz de usuario:

```bash
cd gasto-sabio/frontend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export AGENT_ENGINE_RESOURCE_NAME="projects/1095643609675/locations/us-central1/reasoningEngines/4997508496904683520"
export AGENT_DIRECTORY="app"
export PORT="8080"

python main.py
```

---

## ☁️ Despliegue en Google Cloud Agent Platform

El agente está configurado para desplegarse como un servicio A2A administrado en **Vertex AI Agent Runtime**:

```bash
agents-cli deploy --project <PROJECT_ID> --region us-central1 --update-env-vars "GCS_BUCKET_NAME=<BUCKET_NAME>"
```
