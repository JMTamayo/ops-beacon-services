# dth-11-processor

Procesador MQTT en modo `sub` (fred-ops): recibe lecturas del sensor DHT11 y las registra en consola.

## Requisitos

- [uv](https://docs.astral.sh/uv/)
- Python ≥ 3.13 (alineado con `fred-ops`)

## Configuración

`config.yml` no se versiona (contiene broker y credenciales). Parte del ejemplo:

```bash
cp config.yml.example config.yml
# edita config.yml
```

## Ejecutar

Desde este directorio:

```bash
uv sync
uv run fred-ops run --config config.yml --script processor.py
```

Con `dashboard.enabled: true` en `config.yml`, el procesador levanta Streamlit en segundo plano: abre **http://localhost:8501** para ver series y tabla (se van llenando cuando llegan mensajes al topic).

O desde la raíz del monorepo: `make run-dth11`.

Si `config.yml` ya estaba en git y pasas a ignorarlo: `git rm --cached config.yml` (una vez) y conserva tu copia local.

## Dashboard (Streamlit, opcional)

Sin sección `dashboard` en el YAML (o con `dashboard: null`), no se inicia la UI. Si añades `dashboard`, todos los campos son opcionales salvo que quieras cambiar valores por defecto; solo `enabled: true` activa Streamlit.

```yaml
dashboard:
  enabled: true
  # port: 8501
  # host: "0.0.0.0"
```

Dependencias: `fred-ops[dashboard]`. En Docker, Compose expone **8501** → `http://localhost:8501`.

## Docker (Compose en la raíz del monorepo)

La imagen se construye con contexto en la raíz del repositorio (incluye `fred-ops` y este paquete).

```bash
# Solo este servicio
docker compose build dth-11-processor
docker compose up -d dth-11-processor
```

Para construir y levantar solo este servicio: `make deploy-services`.

Crea `config.yml` en el host a partir de `config.yml.example` antes de levantar el servicio. Compose monta ese archivo en solo lectura; reinicia el contenedor si cambias broker o credenciales.
