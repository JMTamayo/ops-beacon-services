# Build from repository root: docker compose build victor-ia
FROM python:3.13-slim-bookworm

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

ENV PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy

WORKDIR /app/victor-ia

COPY victor-ia /app/victor-ia

RUN uv sync --frozen --no-dev

EXPOSE 8083

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8083"]
