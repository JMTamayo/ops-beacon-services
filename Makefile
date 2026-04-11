COMPOSE := docker compose
COMPOSE_FILE := docker-compose.yml

.PHONY: help up up-build deploy-services down down-v build logs logs-bot logs-dth11 ps restart stop start pull run-dth11

.DEFAULT_GOAL := help

help:
	@printf '%s\n\n' \
		'Docker Compose (usa $(COMPOSE_FILE) en la raíz del repo)'
	@printf '  make %-18s  - %s\n' \
		up               'Levantar servicios en segundo plano' \
		up-build         'Construir imágenes y levantar' \
		deploy-services  'Construir y levantar dth-11-processor' \
		down             'Parar y eliminar contenedores' \
		down-v           'down y eliminar volúmenes anónimos declarados' \
		build            'Solo construir imágenes' \
		logs             'Seguir logs de todos los servicios' \
		logs-bot         'Seguir logs del servicio bot-telegram' \
		logs-dth11       'Seguir logs del servicio dth-11-processor' \
		ps               'Estado de contenedores' \
		restart          'Reiniciar contenedores' \
		stop             'Parar sin eliminar contenedores' \
		start            'Arrancar contenedores existentes' \
		pull             'Descargar imágenes base (si aplica)' \
		run-dth11        'Run dth-11 processor (requires MQTT broker at localhost:1883)'

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

ps:
	$(COMPOSE) -f $(COMPOSE_FILE) ps

restart:
	$(COMPOSE) -f $(COMPOSE_FILE) restart

stop:
	$(COMPOSE) -f $(COMPOSE_FILE) stop

start:
	$(COMPOSE) -f $(COMPOSE_FILE) start

pull:
	$(COMPOSE) -f $(COMPOSE_FILE) pull

run-dth11:
	cd dth-11-processor && uv run fred-ops run --config config.yml --script processor.py
