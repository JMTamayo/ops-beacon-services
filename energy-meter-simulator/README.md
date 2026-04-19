# energy-meter-simulator

Simulador de medidor de energía que publica por MQTT en **modo pub** de [fred-ops](../fred-ops): un mensaje JSON cada `interval_seconds` (por defecto 60 s).

## Formato del mensaje

```json
{
  "local_timestamptz": "2026-04-13T13:15:54.735-0500",
  "data": {
    "voltage": 125.5,
    "current": 0,
    "active_power": 0,
    "active_energy": 7.26,
    "frequency": 60,
    "power_factor": 0
  }
}
```

`local_timestamptz` usa zona `America/Bogota`. Los valores numéricos se simulan con variación aleatoria ligera; `active_energy` acumula en kWh según la potencia simulada y el intervalo.

## Configuración local

1. Copia el ejemplo: `cp config/config.yml.example config/config.yml`
2. Edita broker, credenciales y `output.topic` según tu entorno. Si usas `__SIMULATOR_ID__` en el YAML, en local sustitúyelo por un id fijo (p. ej. `dev`); en Docker el entrypoint lo reemplaza al usar `make energy-meter-simulator-up N=…`.
3. Ejecuta (requiere broker MQTT alcanzable):

```bash
cd energy-meter-simulator && uv sync && uv run fred-ops run --config config/config.yml --script app/main.py
```

Opcional: `interval_seconds` en `kwargs` del YAML o `-k interval_seconds=30`.

## Docker (varios contenedores)

Edita `config/config.yml` con el **host MQTT**, usuario y contraseña reales (el compose monta ese archivo en el contenedor). Usa los placeholders `__SIMULATOR_ID__` en `output.topic` y `broker.client_id` si quieres que `make energy-meter-simulator-up N=...` sustituya el consecutivo; el placeholder `your-mqtt-broker.example.com` debe apuntar a un broker alcanzable desde Docker.

En el repo raíz, con consecutivo `N` (nombre del contenedor `energy-meter-simulator-<N>`):

```bash
make energy-meter-simulator-up N=1
```

El entrypoint sustituye `__SIMULATOR_ID__` en `config/config.yml` y escribe `config/config.runtime.yml` para publicar en `/volttio/<SIMULATOR_ID>/energy-stats`, con `broker.client_id` `energy-meter-simulator-<SIMULATOR_ID>`.

Variable de entorno: `SIMULATOR_ID` (la fija el Makefile desde `N`).

Para detener y eliminar un contenedor:

```bash
make energy-meter-simulator-down N=1
```
