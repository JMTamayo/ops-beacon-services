# Build from repository root: docker compose build meter-ops
FROM python:3.13-slim-bookworm

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

ENV PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy

WORKDIR /app

# Layout must match pyproject path dependency: fred-ops next to meter-ops
COPY fred-ops /app/fred-ops
COPY meter-ops /app/meter-ops

WORKDIR /app/meter-ops

# Imagen usable sin config.yml versionado: se parte del ejemplo si falta.
RUN if [ ! -f config/config.yml ]; then cp config/config.yml.example config/config.yml; fi

RUN uv sync --frozen --no-dev \
    && chmod +x /app/meter-ops/docker-entrypoint.sh

ENTRYPOINT ["/app/meter-ops/docker-entrypoint.sh"]
CMD ["uv", "run", "fred-ops", "run", "--config", "config/config.yml", "--script", "app/main.py"]

