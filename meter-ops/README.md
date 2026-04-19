# meter-ops

Servicio `fred-ops` para procesar lecturas de medidores vía MQTT.

## Configuración

1. Crea el archivo de config local (no versionado):

```bash
cp config/config.yml.example config/config.yml
```

2. Ajusta `broker.host`, `input.topic` y el `schema` si lo necesitas.

## Ejecutar local (sin Docker)

```bash
uv run fred-ops run --config config/config.yml --script app/main.py
```

## Ejecutar en Docker (desde la raíz del repo)

```bash
cp meter-ops/config/config.yml.example meter-ops/config/config.yml
docker compose build meter-ops
docker compose up -d meter-ops
```

