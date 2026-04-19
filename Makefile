COMPOSE := docker compose
COMPOSE_FILE := docker-compose.yml
PORTAINER_ADMIN_PASSWORD_FILE := portainer/config/admin_password
PORTAINER_ADMIN_PASSWORD_EXAMPLE := portainer/config/admin_password.example
POSTGRES_PASSWORD_FILE := postgres/config/postgres_password
POSTGRES_PASSWORD_EXAMPLE := postgres/config/postgres_password.example
POSTGRES_ENV_FILE := postgres/config/.env
POSTGRES_ENV_EXAMPLE := postgres/config/.env.example
ENER_VAULT_ENV_FILE := ener-vault/config/.env
ENER_VAULT_ENV_EXAMPLE := ener-vault/config/.env.example
METER_OPS_CONFIG_FILE := meter-ops/config/config.yml
METER_OPS_CONFIG_EXAMPLE := meter-ops/config/config.yml.example
VICTOR_IA_ENV_FILE := victor-ia/config/.env
VICTOR_IA_ENV_EXAMPLE := victor-ia/config/.env.example
ENERGY_SIM_PROFILE := energy-simulator

.PHONY: help up up-build deploy-services down down-v build logs logs-bot logs-dth11 logs-meter-ops logs-victor-ia logs-portainer logs-postgres logs-ener-vault ps restart restart-portainer stop start pull up-portainer ops-beacon ops-beacon-victor rebuild-ops-beacon portainer-password-check postgres-config-check ener-vault-config-check meter-ops-config-check victor-ia-config-check run-dth11 run-meter-ops energy-meter-simulator-up energy-meter-simulator-down logs-energy-meter-simulator run-energy-meter-simulator

.DEFAULT_GOAL := help

help:
	@printf '%s\n\n' \
		'Docker Compose (usa $(COMPOSE_FILE) en la raíz del repo)'
	@printf '  make %-22s  - %s\n' \
		up                    'Levantar servicios en segundo plano' \
		up-build              'Construir imágenes y levantar' \
		deploy-services       'Construir y levantar dth-11-processor' \
		down                  'Parar y eliminar contenedores' \
		down-v                'down y eliminar volúmenes anónimos declarados' \
		build                 'Solo construir imágenes' \
		logs                  'Seguir logs de todos los servicios' \
		logs-bot              'Seguir logs del servicio bot-telegram' \
		logs-dth11            'Seguir logs del servicio dth-11-processor' \
		logs-meter-ops        'Seguir logs del servicio meter-ops' \
		logs-victor-ia        'Seguir logs del servicio victor-ia' \
		logs-portainer        'Seguir logs del servicio portainer' \
		logs-postgres         'Seguir logs del servicio postgres' \
		logs-ener-vault       'Seguir logs del servicio ener-vault' \
		ps                    'Estado de contenedores' \
		restart               'Reiniciar contenedores' \
		restart-portainer     'Reiniciar solo portainer' \
		stop                  'Parar sin eliminar contenedores' \
		start                 'Arrancar contenedores existentes' \
		up-portainer          'Levantar solo portainer (con build)' \
		portainer-password-check 'Validar presencia de portainer/config/admin_password' \
		ops-beacon            'Levantar portainer, postgres, ener-vault, meter-ops y victor-ia (checks de config)' \
		rebuild-ops-beacon    'Parar, reconstruir y levantar ops-beacon' \
		ops-beacon-victor     'Alias de ops-beacon (compatibilidad)' \
		pull                  'Descargar imágenes base (si aplica)' \
		run-dth11             'Run dth-11 processor (requires MQTT broker at localhost:1883)' \
		run-meter-ops         'Run meter-ops (requires MQTT broker)' \
		energy-meter-simulator-up "Levantar simulador MQTT (N=consecutivo): contenedor energy-meter-simulator-N" \
		energy-meter-simulator-down "Parar y eliminar contenedor energy-meter-simulator-N (requiere N=)" \
		logs-energy-meter-simulator "Seguir logs del contenedor energy-meter-simulator-N (requiere N=)" \
		run-energy-meter-simulator 'Run energy-meter-simulator local (requiere config/config.yml)'

up:
	$(COMPOSE) -f $(COMPOSE_FILE) up -d

up-build:
	$(COMPOSE) -f $(COMPOSE_FILE) up -d --build

deploy-services:
	$(COMPOSE) -f $(COMPOSE_FILE) up -d --build dth-11-processor

down:
	$(COMPOSE) -f $(COMPOSE_FILE) down

down-v:
	$(COMPOSE) -f $(COMPOSE_FILE) down -v

build:
	$(COMPOSE) -f $(COMPOSE_FILE) build

logs:
	$(COMPOSE) -f $(COMPOSE_FILE) logs -f

logs-bot:
	$(COMPOSE) -f $(COMPOSE_FILE) logs -f bot-telegram

logs-dth11:
	$(COMPOSE) -f $(COMPOSE_FILE) logs -f dth-11-processor

logs-meter-ops:
	$(COMPOSE) -f $(COMPOSE_FILE) logs -f meter-ops

logs-victor-ia:
	$(COMPOSE) -f $(COMPOSE_FILE) logs -f victor-ia

logs-portainer:
	$(COMPOSE) -f $(COMPOSE_FILE) logs -f portainer

logs-postgres:
	$(COMPOSE) -f $(COMPOSE_FILE) logs -f postgres

logs-ener-vault:
	$(COMPOSE) -f $(COMPOSE_FILE) logs -f ener-vault

ps:
	$(COMPOSE) -f $(COMPOSE_FILE) ps

restart:
	$(COMPOSE) -f $(COMPOSE_FILE) restart

restart-portainer:
	$(COMPOSE) -f $(COMPOSE_FILE) restart portainer

stop:
	$(COMPOSE) -f $(COMPOSE_FILE) stop

start:
	$(COMPOSE) -f $(COMPOSE_FILE) start

pull:
	$(COMPOSE) -f $(COMPOSE_FILE) pull

up-portainer:
	$(MAKE) portainer-password-check
	$(COMPOSE) -f $(COMPOSE_FILE) up -d --build portainer

ops-beacon:
	$(MAKE) portainer-password-check
	$(MAKE) postgres-config-check
	$(MAKE) ener-vault-config-check
	$(MAKE) meter-ops-config-check
	$(MAKE) victor-ia-config-check
	$(COMPOSE) -f $(COMPOSE_FILE) up -d --build portainer postgres ener-vault meter-ops victor-ia

ops-beacon-victor: ops-beacon

rebuild-ops-beacon:
	$(COMPOSE) -f $(COMPOSE_FILE) down
	$(MAKE) ops-beacon

portainer-password-check:
	@test -f "$(PORTAINER_ADMIN_PASSWORD_FILE)" || (echo "Falta $(PORTAINER_ADMIN_PASSWORD_FILE). Crea uno con: cp $(PORTAINER_ADMIN_PASSWORD_EXAMPLE) $(PORTAINER_ADMIN_PASSWORD_FILE)"; exit 1)

postgres-config-check:
	@test -f "$(POSTGRES_PASSWORD_FILE)" || (echo "Falta $(POSTGRES_PASSWORD_FILE). Crea uno con: cp $(POSTGRES_PASSWORD_EXAMPLE) $(POSTGRES_PASSWORD_FILE)"; exit 1)
	@test -f "$(POSTGRES_ENV_FILE)" || (echo "Falta $(POSTGRES_ENV_FILE). Crea uno con: cp $(POSTGRES_ENV_EXAMPLE) $(POSTGRES_ENV_FILE)"; exit 1)

ener-vault-config-check:
	@test -f "$(ENER_VAULT_ENV_FILE)" || (echo "Falta $(ENER_VAULT_ENV_FILE). Crea uno con: cp $(ENER_VAULT_ENV_EXAMPLE) $(ENER_VAULT_ENV_FILE)"; exit 1)

meter-ops-config-check:
	@test -f "$(METER_OPS_CONFIG_FILE)" || (echo "Falta $(METER_OPS_CONFIG_FILE). Crea uno con: cp $(METER_OPS_CONFIG_EXAMPLE) $(METER_OPS_CONFIG_FILE)"; exit 1)

victor-ia-config-check:
	@test -f "$(VICTOR_IA_ENV_FILE)" || (echo "Falta $(VICTOR_IA_ENV_FILE). Crea uno con: cp $(VICTOR_IA_ENV_EXAMPLE) $(VICTOR_IA_ENV_FILE) y define LLM_API_KEY"; exit 1)

run-dth11:
	cd dth-11-processor && uv run fred-ops run --config config.yml --script processor.py

run-meter-ops:
	cd meter-ops && uv run fred-ops run --config config/config.yml --script app/main.py

energy-meter-simulator-up:
	@test -n "$(N)" || (echo "Uso: make energy-meter-simulator-up N=<consecutivo>"; exit 1)
	$(COMPOSE) -f $(COMPOSE_FILE) --profile $(ENERGY_SIM_PROFILE) build energy-meter-simulator
	$(COMPOSE) -f $(COMPOSE_FILE) --profile $(ENERGY_SIM_PROFILE) run -d --name energy-meter-simulator-$(N) -e SIMULATOR_ID=$(N) energy-meter-simulator

energy-meter-simulator-down:
	@test -n "$(N)" || (echo "Uso: make energy-meter-simulator-down N=<consecutivo>"; exit 1)
	docker rm -f energy-meter-simulator-$(N)

logs-energy-meter-simulator:
	@test -n "$(N)" || (echo "Uso: make logs-energy-meter-simulator N=<consecutivo>"; exit 1)
	docker logs -f energy-meter-simulator-$(N)

run-energy-meter-simulator:
	cd energy-meter-simulator && uv run fred-ops run --config config/config.yml --script app/main.py
