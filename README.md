# ops-beacon-services

Monorepo de servicios alrededor de **ops-beacon** (eventos de operación).

## Servicios

- **bot-telegram**: notificador MQTT → Telegram. Ver [`bot-telegram/README.md`](bot-telegram/README.md).
- **portainer**: UI para administrar Docker localmente.
  - versión fijada: `portainer/portainer-ce:2.27.9`.

## Portainer: configuración rápida

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
