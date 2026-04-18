COMPOSE := docker compose
COMPOSE_FILE := docker-compose.yml
PORTAINER_ADMIN_PASSWORD_FILE := portainer/config/admin_password
PORTAINER_ADMIN_PASSWORD_EXAMPLE := portainer/config/admin_password.example

.PHONY: help up up-build deploy-services down down-v build logs logs-bot logs-dth11 logs-portainer ps restart restart-portainer stop start pull up-portainer ops-beacon rebuild-ops-beacon portainer-password-check run-dth11

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
		logs-portainer        'Seguir logs del servicio portainer' \
		ps                    'Estado de contenedores' \
		restart               'Reiniciar contenedores' \
		restart-portainer     'Reiniciar solo portainer' \
		stop                  'Parar sin eliminar contenedores' \
		start                 'Arrancar contenedores existentes' \
		up-portainer          'Levantar solo portainer (con build)' \
		portainer-password-check 'Validar presencia de portainer/config/admin_password' \
		ops-beacon            'Levantar servicios base de la app ops-beacon (inicialmente portainer)' \
		rebuild-ops-beacon    'Parar, reconstruir y levantar ops-beacon' \
		pull                  'Descargar imágenes base (si aplica)' \
		run-dth11             'Run dth-11 processor (requires MQTT broker at localhost:1883)'

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

logs-portainer:
	$(COMPOSE) -f $(COMPOSE_FILE) logs -f portainer

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
	$(COMPOSE) -f $(COMPOSE_FILE) up -d --build portainer

rebuild-ops-beacon:
	$(COMPOSE) -f $(COMPOSE_FILE) down
	$(MAKE) ops-beacon

portainer-password-check:
	@test -f "$(PORTAINER_ADMIN_PASSWORD_FILE)" || (echo "Falta $(PORTAINER_ADMIN_PASSWORD_FILE). Crea uno con: cp $(PORTAINER_ADMIN_PASSWORD_EXAMPLE) $(PORTAINER_ADMIN_PASSWORD_FILE)"; exit 1)

run-dth11:
	cd dth-11-processor && uv run fred-ops run --config config.yml --script processor.py
