COMPOSE := docker compose
COMPOSE_FILE := docker-compose.yml
PORTAINER_ADMIN_PASSWORD_FILE := portainer/config/admin_password
PORTAINER_ADMIN_PASSWORD_EXAMPLE := portainer/config/admin_password.example

.PHONY: help up up-build down down-v build logs logs-bot logs-portainer ps restart restart-portainer stop start pull up-portainer ops-beacon rebuild-ops-beacon portainer-password-check run-dth11

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
	@echo "  make logs-portainer - Seguir logs del servicio portainer"
	@echo "  make ps          - Estado de contenedores"
	@echo "  make restart     - Reiniciar contenedores"
	@echo "  make restart-portainer - Reiniciar solo portainer"
	@echo "  make stop        - Parar sin eliminar contenedores"
	@echo "  make start       - Arrancar contenedores existentes"
	@echo "  make up-portainer - Levantar solo portainer (con build)"
	@echo "  make portainer-password-check - Validar presencia de portainer/config/admin_password"
	@echo "  make ops-beacon  - Levantar servicios base de la app ops-beacon (inicialmente portainer)"
	@echo "  make rebuild-ops-beacon - Parar, reconstruir y levantar ops-beacon"
	@echo "  make pull        - Descargar imágenes base (si aplica)"
	@echo "  make run-dth11   - Run dth-11 processor (requires MQTT broker at localhost:1883)"

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
	cd dth-11-processor && uv run --with ../fred-ops fred-ops run --config config.yml --script processor.py
