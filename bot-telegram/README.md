# bot-telegram

Service that subscribes to MQTT, filters **ERROR** events (ops-beacon model), and sends HTML table notifications to Telegram.

## Configuration

Copy `config/config.example.yaml` to `config/config.yaml` and fill MQTT and Telegram credentials.

Only **`level: ERROR`** events trigger Telegram. The MQTT payload must be a JSON object with (at least) these fields:

`id`, `source`, `metadata`, `level`, `timestamp`, `status`

`id` accepts any JSON value (string, number, boolean, object, array, or `null`).

Example (note `level` and `status` in uppercase, as in ops-beacon):

```json
{
  "id": 1,
  "source": "my-service",
  "metadata": {"detail": "timeout"},
  "level": "ERROR",
  "timestamp": "2025-03-21T12:00:00Z",
  "status": "NEW"
}
```

The `timestamp` field is kept as-is (string) and shown in Telegram without parsing.

Set `LOG_LEVEL=DEBUG` for more verbose logs.

## Run locally

```bash
cd bot-telegram
uv sync --all-groups --no-editable
CONFIG_PATH=config/config.yaml uv run python -m bot_telegram.presentation.main
```

After editing code under `src/`, reinstall the package (`uv pip install . --force-reinstall --no-deps`) or use `uv sync --reinstall-package bot-telegram --no-editable` so imports pick up changes.

## Docker

Compose lives at the monorepo root. From the repository root:

```bash
cp bot-telegram/config/config.example.yaml bot-telegram/config/config.yaml
# edit bot-telegram/config/config.yaml
docker compose up --build
```

The API exposes `GET /health` (204 when MQTT is connected), `GET /config` (JSON with secrets masked), and `POST /telegram/example` to send a sample Telegram message using the configured bot and chat.

If the app crashes with `IsADirectoryError: ... '/app/config/config.yaml'`, the bind mount is pointing at a **directory** on the host. Remove it (`rm -rf bot-telegram/config/config.yaml`) and recreate **`config.yaml` as a file** (copy from `config.example.yaml`).
