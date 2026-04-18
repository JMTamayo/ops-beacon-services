# Build from repository root: docker compose build dth-11-processor
FROM python:3.13-slim-bookworm

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

ENV PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy

WORKDIR /app

# Layout must match pyproject path dependency: fred-ops next to dth-11-processor
COPY fred-ops /app/fred-ops
COPY dth-11-processor /app/dth-11-processor

WORKDIR /app/dth-11-processor

# Imagen usable sin config.yml versionado: se parte del ejemplo si falta.
RUN if [ ! -f config.yml ]; then cp config.yml.example config.yml; fi

RUN uv sync --frozen --no-dev

CMD ["uv", "run", "fred-ops", "run", "--config", "config.yml", "--script", "processor.py"]
