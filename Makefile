COMPOSE := docker compose
COMPOSE_FILE := docker-compose.yml

.PHONY: help up up-build down down-v build logs logs-bot ps restart stop start pull

.DEFAULT_GOAL := help

help:
	@echo "Docker Compose (usa $(COMPOSE_FILE) en la raíz del repo)"
	@echo ""
	@echo "  make up          - Levantar servicios en segundo plano"
	@echo "  make up-build    - Construir imágenes y levantar"
	@echo "  make down        - Parar y eliminar contenedores"
	@echo "  make down-v      - down y eliminar volúmenes anónimos declarados"
	@echo "  make build       - Solo construir imágenes"
	@echo "  make logs        - Seguir logs de todos los servicios"
	@echo "  make logs-bot    - Seguir logs del servicio bot-telegram"
	@echo "  make ps          - Estado de contenedores"
	@echo "  make restart     - Reiniciar contenedores"
	@echo "  make stop        - Parar sin eliminar contenedores"
	@echo "  make start       - Arrancar contenedores existentes"
	@echo "  make pull        - Descargar imágenes base (si aplica)"

up:
	$(COMPOSE) -f $(COMPOSE_FILE) up -d

up-build:
	$(COMPOSE) -f $(COMPOSE_FILE) up -d --build

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
