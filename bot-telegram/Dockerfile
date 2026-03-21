FROM python:3.12-slim-bookworm

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

ENV PYTHONUNBUFFERED=1 \
    CONFIG_PATH=/app/config/config.yaml

WORKDIR /app

COPY pyproject.toml uv.lock ./
COPY src ./src

RUN uv sync --frozen --no-dev --no-editable

EXPOSE 8000

CMD ["uv", "run", "--no-dev", "python", "-m", "bot_telegram.presentation.main"]
