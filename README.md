# ops-beacon-services

Monorepo de servicios alrededor de **ops-beacon** (eventos de operación).

## Servicios

- **bot-telegram**: notificador MQTT → Telegram. Ver [`bot-telegram/README.md`](bot-telegram/README.md).
- **dth-11-processor**: procesador MQTT (fred-ops). Ver [`dth-11-processor/README.md`](dth-11-processor/README.md).
- **meter-ops**: procesador MQTT (fred-ops) para lecturas de medidores. Ver [`meter-ops/README.md`](meter-ops/README.md).
- **portainer**: UI para administrar Docker localmente.
  - versión fijada: `portainer/portainer-ce:2.27.9`.
- **postgres**: PostgreSQL para datos persistentes del API **ener-vault** (esquema `energy_meters`).
- **ener-vault**: API FastAPI para medidores, mediciones, catálogo de **entidades** (tipos de carga) y **asignaciones** medidor–entidad con ventanas de tiempo y restricción de solapes por dispositivo.
- **victor-ia**: agente HTTP (FastAPI + LangGraph) con herramientas extensibles para consultar **ener-vault** y otras integraciones futuras. Ver [`victor-ia/README.md`](victor-ia/README.md). Puerto por defecto en Compose: **8083**.

## Stack ops-beacon (Portainer + Postgres + ener-vault + meter-ops + victor-ia)

Objetivo: levantar Portainer, la base de datos y el API de mediciones con un solo objetivo de Make.

### 1. Credenciales y variables

**Portainer** (igual que antes):

1. `cp portainer/config/admin_password.example portainer/config/admin_password`
2. Editar `portainer/config/admin_password`.

**Postgres**:

1. `cp postgres/config/postgres_password.example postgres/config/postgres_password` y definir la contraseña del superusuario configurado en `.env`.
2. `cp postgres/config/.env.example postgres/config/.env` y ajustar `POSTGRES_USER`, `POSTGRES_DB`, etc.

**ener-vault**:

1. `cp ener-vault/config/.env.example ener-vault/config/.env`
2. Definir `DATABASE_URL` apuntando al Postgres del compose (por ejemplo host `postgres`, puerto `5432`, usuario/clave y base alineados con `postgres/config/.env`).

**meter-ops**:

1. `cp meter-ops/config/config.yml.example meter-ops/config/config.yml`
2. Ajustar `broker.host` y `input.topic` (patrón esperado: `/volttio/<uuid>/energy-stats`; suele usarse `generic_event_log: true` para recibir el topic exacto y validar el payload en código).
3. El servicio envía mediciones a **ener-vault** (`POST /v1/measurements`); el UUID del topic se usa como `device_id` (debe existir en `/v1/devices`).
4. **Dashboard Streamlit** (fred-ops): opcional; en `meter-ops/config/config.yml` pon `dashboard.enabled: true`. En Docker el mapeo es **8502 → 8501** del contenedor: abre **http://localhost:8502**.

**victor-ia**:

1. `cp victor-ia/config/.env.example victor-ia/config/.env`
2. Definir `LLM_API_KEY` y `SERVER_API_KEY_VALUE_HASHED` (ver [`victor-ia/README.md`](victor-ia/README.md)).

### 2. Arranque

```bash
make ops-beacon
```

Esto valida los archivos anteriores y ejecuta `docker compose up -d --build portainer postgres ener-vault meter-ops victor-ia`.

- **ener-vault** (HTTP): `http://localhost:8080`
- **Postgres**: `localhost:5432`
- **Portainer**: `http://localhost:9000` o `https://localhost:9443`
- **meter-ops dashboard** (solo si `dashboard.enabled: true` en `meter-ops/config/config.yml`): `http://localhost:8502`
- **victor-ia** (HTTP): `http://localhost:8083`

`meter-ops` arranca después de que **ener-vault** esté sano (dependencia en Compose + espera al API en el entrypoint de la imagen).

Logs útiles: `make logs-postgres`, `make logs-ener-vault`, `make logs-meter-ops`, `make logs-victor-ia`.

### 3. Migraciones (ener-vault)

Las revisiones Alembic están en `ener-vault/alembic/versions/`. Al arrancar el contenedor **ener-vault**, el script de entrada ejecuta `alembic upgrade head` antes de levantar Uvicorn.

Para aplicar migraciones manualmente (desarrollo local sin Docker):

```bash
cd ener-vault && uv run alembic upgrade head
```

### 4. API ener-vault (resumen)

Prefijo común: `/v1/…`. Documentación interactiva: `GET /docs` en el mismo host/puerto del servicio.

| Recurso | Listado | Notas |
|--------|---------|--------|
| **devices** | `GET /v1/devices` | Paginación `page` / `size` (pygination); orden `sort_date` (`created_at`, `updated_at`) y `sort_order` (`asc` / `desc`). |
| **measurements** | `GET /v1/measurements` | Filtros por `device_id`, rango `local_time_*`; misma paginación y orden (`created_at`, `updated_at`, `local_time`). |
| **entities** | `GET /v1/entities` | Catálogo con seed inicial en migración; CRUD completo. |
| **device-entity-assignments** | `GET /v1/device-entity-assignments` | Filtros `device_id`, `entity_id`, ventana temporal, `description_like` (ILIKE); paginación y orden por fechas del modelo. |

Los listados devuelven un objeto paginado (`items`, `page`, `size`, `total`, `pages`, etc.). Las tablas bajo `energy_meters` incluyen `updated_at` con triggers `BEFORE UPDATE` en PostgreSQL.

### 5. Pruebas (ener-vault)

Requieren `DATABASE_URL` (por ejemplo el Postgres local del compose) y esquema migrado:

```bash
cd ener-vault && uv run --group dev pytest tests/ -q
```

## Portainer: configuración rápida (solo UI)

1. Crear archivo real de credenciales:
   - `cp portainer/config/admin_password.example portainer/config/admin_password`
   - editar `portainer/config/admin_password`.
2. Levantar Portainer:
   - `make up-portainer` (o `make up-build` para todo el stack).
3. Acceder:
   - `http://localhost:9000` o `https://localhost:9443`
   - usuario inicial: `admin`
   - contraseña: valor definido en `portainer/config/admin_password`.

## Verificación recomendada

- **Login inicial**: iniciar sesión con `admin` y la contraseña configurada.
- **Persistencia**:
  1. Crear algún recurso desde Portainer (por ejemplo, un endpoint local).
  2. Reiniciar servicio: `make restart-portainer`.
  3. Confirmar que la sesión/datos siguen disponibles (volumen `portainer_data`).
- **ener-vault**: tras `make ops-beacon`, comprobar `GET http://localhost:8080/health` y `GET http://localhost:8080/docs`.
