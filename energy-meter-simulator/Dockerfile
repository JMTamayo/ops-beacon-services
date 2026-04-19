# Build from repository root: docker compose build energy-meter-simulator
FROM python:3.13-slim-bookworm

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

ENV PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy

WORKDIR /app

COPY fred-ops /app/fred-ops
COPY energy-meter-simulator /app/energy-meter-simulator

WORKDIR /app/energy-meter-simulator

RUN if [ ! -f config/config.yml ]; then cp config/config.yml.example config/config.yml; fi

RUN uv sync --frozen --no-dev \
    && chmod +x /app/energy-meter-simulator/docker-entrypoint.sh

ENTRYPOINT ["/app/energy-meter-simulator/docker-entrypoint.sh"]
