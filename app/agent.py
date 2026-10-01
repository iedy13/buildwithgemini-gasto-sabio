# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime
import json
import os
from pathlib import Path
from zoneinfo import ZoneInfo

from a2ui.basic_catalog.provider import BasicCatalog
from a2ui.schema.manager import A2uiSchemaManager
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.code_executors import AgentEngineSandboxCodeExecutor
from google.adk.models import Gemini
from google.adk.tools import ToolContext
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.genai import types

from app.a2ui_utils import a2ui_callback


MODEL = "gemini-3.6-flash"
EXPENSES_FILE = Path("/tmp/expenses.json")


def log_expense(
    amount: float,
    description: str,
    category: str,
    payment_method: str = "efectivo",
) -> str:
    """Registra un nuevo gasto financiero del usuario.

    Args:
        amount: El monto monetario gastado en pesos (ej. 45.0, 5.0).
        description: Breve descripcion del producto o servicio (ej. 'café', '4 taquitos de canasta', 'pasaje metro Taxqueña a Aquiles').
        category: Categoria del gasto (ej. 'Alimentos y Bebidas', 'Transporte', 'Entretenimiento', 'Servicios', 'Otros').
        payment_method: Medio de pago utilizado (ej. 'efectivo', 'tarjeta de movilidad', 'tarjeta de debito', 'tarjeta de credito').

    Returns:
        Un mensaje confirmando el registro exitoso con el ID y resumen del gasto.
    """
    expenses = []
    if EXPENSES_FILE.exists():
        try:
            with open(EXPENSES_FILE, "r", encoding="utf-8") as f:
                expenses = json.load(f)
        except Exception:
            expenses = []

    now_str = datetime.datetime.now(ZoneInfo("America/Mexico_City")).strftime("%Y-%m-%d %H:%M:%S")
    expense_entry = {
        "id": len(expenses) + 1,
        "amount": amount,
        "description": description,
        "category": category,
        "payment_method": payment_method,
        "timestamp": now_str,
    }
    expenses.append(expense_entry)

    with open(EXPENSES_FILE, "w", encoding="utf-8") as f:
        json.dump(expenses, f, ensure_ascii=False, indent=2)

    return (
        f"Gasto registrado exitosamente: #{expense_entry['id']} - ${amount:.2f} MXN "
        f"en '{description}' (Categoría: {category}, Método: {payment_method}) el {now_str}."
    )


def list_expenses() -> str:
    """Devuelve la lista completa de todos los gastos registrados por el usuario.

    Returns:
        Un resumen detallado con cada gasto, su ID, monto, descripción, categoría y fecha.
    """
    if not EXPENSES_FILE.exists():
        return "No hay ningún gasto registrado todavía."

    try:
        with open(EXPENSES_FILE, "r", encoding="utf-8") as f:
            expenses = json.load(f)
    except Exception:
        expenses = []

    if not expenses:
        return "No hay gastos registrados en el sistema."

    lines = ["**Historial de Gastos Registrados:**"]
    total = 0.0
    for exp in expenses:
        amt = exp.get("amount", 0.0)
        total += amt
        lines.append(
            f"- **#{exp.get('id')}**: ${amt:.2f} MXN | {exp.get('description')} "
            f"({exp.get('category')}, pago: {exp.get('payment_method')}) - {exp.get('timestamp')}"
        )
    lines.append(f"\n**Total acumulado:** ${total:.2f} MXN ({len(expenses)} transacciones).")
    return "\n".join(lines)


def edit_expense(
    expense_id: int,
    amount: float | None = None,
    description: str | None = None,
    category: str | None = None,
    payment_method: str | None = None,
) -> str:
    """Modifica o actualiza los datos de un gasto registrado previamente a partir de su ID.

    Args:
        expense_id: El número ID del gasto que se desea modificar.
        amount: Nuevo monto en pesos (opcional).
        description: Nueva descripción del gasto (opcional).
        category: Nueva categoría (opcional).
        payment_method: Nuevo método de pago (opcional).

    Returns:
        Mensaje confirmando la actualización del gasto o informando si no se encontró.
    """
    if not EXPENSES_FILE.exists():
        return f"No se encontró el gasto con ID #{expense_id} porque no hay registros."

    try:
        with open(EXPENSES_FILE, "r", encoding="utf-8") as f:
            expenses = json.load(f)
    except Exception:
        expenses = []

    found = False
    for exp in expenses:
        if exp.get("id") == expense_id:
            if amount is not None:
                exp["amount"] = amount
            if description is not None:
                exp["description"] = description
            if category is not None:
                exp["category"] = category
            if payment_method is not None:
                exp["payment_method"] = payment_method
            found = True
            break

    if not found:
        return f"No se encontró ningún gasto con el ID #{expense_id}."

    with open(EXPENSES_FILE, "w", encoding="utf-8") as f:
        json.dump(expenses, f, ensure_ascii=False, indent=2)

    return f"Gasto #{expense_id} modificado exitosamente."


def delete_expense(expense_id: int) -> str:
    """Elimina permanentemente un registro de gasto por su ID.

    Args:
        expense_id: El número ID del gasto a eliminar.

    Returns:
        Mensaje confirmando la eliminación del gasto o informando si no existía.
    """
    if not EXPENSES_FILE.exists():
        return f"No se pudo eliminar el gasto #{expense_id}: no hay registros."

    try:
        with open(EXPENSES_FILE, "r", encoding="utf-8") as f:
            expenses = json.load(f)
    except Exception:
        expenses = []

    initial_len = len(expenses)
    new_expenses = [exp for exp in expenses if exp.get("id") != expense_id]

    if len(new_expenses) == initial_len:
        return f"No se encontró ningún gasto con ID #{expense_id} para eliminar."

    with open(EXPENSES_FILE, "w", encoding="utf-8") as f:
        json.dump(new_expenses, f, ensure_ascii=False, indent=2)

    return f"Gasto #{expense_id} eliminado exitosamente del registro."


def get_exchange_rate(from_currency: str = "USD", to_currency: str = "MXN") -> str:
    """Consulta el tipo de cambio actual entre dos divisas utilizando una API financiera en tiempo real.

    Args:
        from_currency: Código ISO de la moneda base (ej. 'USD', 'EUR'). Por defecto 'USD'.
        to_currency: Código ISO de la moneda de destino (ej. 'MXN', 'USD'). Por defecto 'MXN'.

    Returns:
        Información del tipo de cambio actual y fecha de actualización.
    """
    import urllib.request

    base = from_currency.strip().upper()
    target = to_currency.strip().upper()
    api_url = os.environ.get("EXCHANGE_RATE_API_URL", f"https://open.er-api.com/v6/latest/{base}")

    try:
        req = urllib.request.Request(
            api_url,
            headers={"User-Agent": "GastoSabio-FinanceAgent/1.0"},
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))

        if data.get("result") != "success":
            return f"No se pudo obtener el tipo de cambio para {base}."

        rate = data.get("rates", {}).get(target)
        if rate is None:
            return f"Moneda destino '{target}' no encontrada en el catálogo."

        last_update = data.get("time_last_update_utc", "reciente")
        return (
            f"Tipo de cambio actual: 1 {base} = {rate:.4f} {target} "
            f"(Actualizado: {last_update})."
        )
    except Exception as e:
        return f"Error consultando el tipo de cambio: {e}"


def generate_savings_badge(
    title: str,
    prompt: str,
    tool_context: ToolContext,
) -> str:
    """Genera una imagen/insignia visual personalizada de ahorro o finanzas utilizando gemini-3.1-flash-lite-image en la región global.
    Guarda la imagen generada en los artefactos del Playground y la sube al bucket público de Cloud Storage, devolviendo su URL pública HTTPS.

    Args:
        title: Título o nombre de la insignia/logro (ej. 'Insignia Ahorrador del Metro', 'Medalla Control de Gastos Hormiga').
        prompt: Descripción detallada para generar la imagen visual con estilo de insignia o icono 3D atractivo.
        tool_context: Contexto de ejecución inyectado por ADK para guardar artefactos.

    Returns:
        La URL pública HTTPS de la imagen alojada en Cloud Storage y confirmación de guardado de artefacto.
    """
    import uuid
    from google import genai
    from google.cloud import storage

    bucket_name = "gasto-sabio-media-qwiklabs-gcp-04-efabffc82211"
    project_id = "qwiklabs-gcp-04-efabffc82211"

    # Generar imagen con gemini-3.1-flash-lite-image en global
    client = genai.Client(vertexai=True, project=project_id, location="global")
    response = client.models.generate_content(
        model="gemini-3.1-flash-lite-image",
        contents=prompt,
    )

    image_bytes = None
    mime_type = "image/jpeg"
    for part in response.candidates[0].content.parts:
        if part.inline_data:
            image_bytes = part.inline_data.data
            mime_type = part.inline_data.mime_type or "image/jpeg"
            break

    if not image_bytes:
        return "No se pudo generar la imagen para la insignia."

    # 1. Guardar en Playground Artifacts con tool_context.save_artifact
    filename = f"{uuid.uuid4().hex[:8]}_badge.jpg"
    artifact_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
    tool_context.save_artifact(filename=filename, artifact=artifact_part)

    # 2. Subir a Cloud Storage bucket público
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(filename)
    blob.upload_from_string(image_bytes, content_type=mime_type)

    public_url = f"https://storage.googleapis.com/{bucket_name}/{filename}"
    return (
        f"Insignia '{title}' generada exitosamente.\n"
        f"Artefacto guardado en Playground: {filename}\n"
        f"URL pública: {public_url}"
    )


def generate_financial_tip_video(
    title: str,
    prompt: str,
    tool_context: ToolContext,
) -> str:
    """Genera un video corto animado o explicativo sobre finanzas o tips de ahorro utilizando el modelo Omni (gemini-omni-flash-preview) en la región global.
    Guarda el video generado en los artefactos del Playground y sube los bytes al bucket público de Cloud Storage, devolviendo su URL pública HTTPS.

    Args:
        title: Título o concepto del video (ej. 'Video Tip Regla 50-30-20', 'Video Ahorro Gastos Hormiga').
        prompt: Descripción del video a generar (ej. 'Animación 3D de monedas y alcancía con consejos de ahorro').
        tool_context: Contexto de ejecución inyectado por ADK para guardar artefactos.

    Returns:
        La URL pública HTTPS del video en Cloud Storage y confirmación de guardado de artefacto.
    """
    import base64
    import uuid
    from google import genai
    from google.cloud import storage

    bucket_name = "gasto-sabio-media-qwiklabs-gcp-04-efabffc82211"
    project_id = "qwiklabs-gcp-04-efabffc82211"

    client = genai.Client(vertexai=True, project=project_id, location="global")
    interaction = client.interactions.create(
        model="gemini-omni-flash-preview",
        input=prompt,
    )

    if not interaction.output_video or not interaction.output_video.data:
        return "No se pudo generar el video a través del modelo Omni."

    video_bytes = base64.b64decode(interaction.output_video.data)
    mime_type = getattr(interaction.output_video, "mime_type", None) or "video/mp4"

    # 1. Guardar en Playground Artifacts con tool_context.save_artifact
    filename = f"{uuid.uuid4().hex[:8]}_tip.mp4"
    artifact_part = types.Part.from_bytes(data=video_bytes, mime_type=mime_type)
    tool_context.save_artifact(filename=filename, artifact=artifact_part)

    # 2. Subir directamente los bytes al bucket público de Cloud Storage
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(filename)
    blob.upload_from_string(video_bytes, content_type=mime_type)

    public_url = f"https://storage.googleapis.com/{bucket_name}/{filename}"
    return (
        f"Video '{title}' generado exitosamente.\n"
        f"Artefacto guardado en Playground: {filename}\n"
        f"URL pública: {public_url}"
    )


SANDBOX_RESOURCE_NAME = "projects/1095643609675/locations/us-central1/reasoningEngines/2669147489554137088/sandboxEnvironments/7181707037179379712"
AGENT_ENGINE_RESOURCE_NAME = "projects/1095643609675/locations/us-central1/reasoningEngines/2669147489554137088"

code_executor = AgentEngineSandboxCodeExecutor(
    sandbox_resource_name=SANDBOX_RESOURCE_NAME,
    agent_engine_resource_name=AGENT_ENGINE_RESOURCE_NAME,
)

async def generate_memories_callback(callback_context: CallbackContext):
    """Guarda automáticamente la conversación en el Memory Bank para recordar preferencias entre sesiones."""
    await callback_context.add_session_to_memory()
    return None


schema_manager = A2uiSchemaManager(
    version="0.8",
    catalogs=[BasicCatalog.get_config("0.8")],
)

instruction = schema_manager.generate_system_prompt(
    role_description=(
        "Eres 'GastoSabio', un asistente inteligente de finanzas personales para usuarios en México. "
        "Llevas el control de gastos cotidianos, conversiones de divisas con get_exchange_rate, "
        "registro y consulta de gastos con log_expense, list_expenses, edit_expense, delete_expense, "
        "insignias de ahorro con generate_savings_badge, videos educativos de finanzas con generate_financial_tip_video, "
        "y cálculos en sandbox seguro de Python. "
        "Recuerdas hechos y preferencias duraderas del usuario a través de Memory Bank."
    ),
    workflow_description="Analiza la solicitud y devuelve interfaces interactivas estructuradas en A2UI siempre que muestres resúmenes de gastos, recibos, insignias o cálculos.",
    ui_description=(
        "Keep every surface tiny and flat: ONE Card > ONE Column > a few Text rows. "
        "Never nest a Card inside a Card. "
        "Use ONLY these components: Card, Column, Row, Text, and Image. Do not use "
        "Table or Heading (unsupported), or Buttons, actions, or forms (they do "
        "nothing in adk web). "
        "You may include one Image component, but only when you have a public https "
        "URL for the image (for example the URL an image tool returns after uploading "
        "to a public bucket). Set the Image url to that exact https link, for example "
        '{"Image": {"url": {"literalString": "https://..."}}}. Never point an '
        "Image at a bare filename, an artifact name, or a non-http(s) path. If you do "
        "not have a public URL, add a short Text line noting the image instead. "
        "No markdown in text; use the usageHint property ('h1', 'h2', 'body') for "
        "headings and emphasis. "
        "Output ONLY the raw A2UI JSON array — no prose, and never wrap it in "
        "<a2a_datapart_json> tags or 'kind'/'data'/'metadata' objects."
    ),
    include_schema=True,
    include_examples=True,
)

root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model=MODEL,
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=instruction,
    tools=[
        PreloadMemoryTool(),
        log_expense,
        list_expenses,
        edit_expense,
        delete_expense,
        get_exchange_rate,
        generate_savings_badge,
        generate_financial_tip_video,
    ],
    after_agent_callback=generate_memories_callback,
    after_model_callback=a2ui_callback,
    code_executor=code_executor,
)

app = App(
    root_agent=root_agent,
    name="app",
)


