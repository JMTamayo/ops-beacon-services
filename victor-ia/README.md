# Victor IA

Agente HTTP (FastAPI) con herramientas extensibles para operar sobre **ener-vault** y, más adelante, otros servicios del monorepo.

## Variables de entorno

Copia `config/.env.example` a `config/.env` y define al menos:

| Variable | Descripción |
|----------|-------------|
| `LLM_API_KEY` | Clave del proveedor LLM (p. ej. Google AI Studio para `google_genai`). |
| `LLM_PROVIDER` | Proveedor para `init_chat_model` (p. ej. `google_genai`, `openai`). |
| `LLM_MODEL` | Nombre del modelo (p. ej. `gemini-2.0-flash`, `gpt-4o-mini`). |
| `ENER_VAULT_BASE_URL` | Base URL del API (en Docker: `http://ener-vault:8080`). |

Opcional:

| Variable | Descripción |
|----------|-------------|
| `SERVER_API_KEY_NAME` | Nombre de la cabecera (por defecto `X-API-Key`), igual que en [aura](https://github.com/JMTamayo/aura). |
| `SERVER_API_KEY_VALUE_HASHED` | Hash **bcrypt** de la clave en texto plano; el cliente envía la clave en la cabecera y el servidor valida con `bcrypt.checkpw`. |
| `PROBLEM_TYPE_URI_PREFIX` | (Opcional) Prefijo de URIs para el campo `type` en errores **RFC 7807** (`application/problem+json`). Por defecto: `https://ops-beacon.invalid/problems`. |
| `TEAMS_WEBHOOK_URL` | (Opcional) URL del disparador HTTP de **Power Automate** hacia el **canal de operación** en Teams (equipo de operación / alertas; incluye `sig=…`, secreto). Habilita `teams_send_notification` (MessageCard con destino “Canal de operación”). Ajusta el flujo si tu esquema JSON difiere. |

## Desarrollo local

```bash
cd victor-ia
cp config/.env.example config/.env
# editar config/.env
uv sync
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8083
```

Documentación interactiva: `http://localhost:8083/docs`

## Docker

Desde la raíz del monorepo (con `ener-vault` levantado o en el mismo compose):

```bash
docker compose up -d --build victor-ia
```

Puerto publicado: **8083** → servicio interno **8083**.

## Añadir una nueva tool

1. Crea `app/tools/<integración>.py` y define funciones con `@tool` de LangChain, más una lista `TOOLS_<NOMBRE>`.
2. Importa esa lista en [`app/tools/registry.py`](app/tools/registry.py) y concaténala en `build_tools()`.
3. Reinicia el servicio para cargar el nuevo código.

## API

- `GET /health` — salud del servicio victor-ia.
- `POST /victor-ia/` — cuerpo JSON `{"message": "..."}` (campo **`message`**, no `request`). Cabecera **`X-API-Key`** con la clave en texto plano.

**Éxito (HTTP 200, `Content-Type: application/json`):**

```json
{ "role": "assistant", "content": "…" }
```

En **Atajos (Shortcuts)** de Apple: acción *Obtener contenidos de URL* → método POST → cabeceras `Content-Type: application/json` y `X-API-Key` → cuerpo de solicitud JSON como arriba → usa *Obtener valor de diccionario* sobre `content` para el texto. Comprueba el **código de estado** (200 vs 4xx/5xx).

**Errores ([RFC 7807](https://datatracker.ietf.org/doc/html/rfc7807)):** `Content-Type: application/problem+json` con campos `type`, `title`, `status`, `detail`, `instance` (ruta solicitada). El **422** incluye además `errors` (detalles de validación Pydantic). Los fallos del agente o del modelo suelen responder **502** (`bad-gateway`).
