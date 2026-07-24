COMPOSE := docker compose -f tests/integration/docker/docker-compose.yml
DISTRO ?= ubuntu

.PHONY: build run down rebuild

build:
	$(COMPOSE) build $(DISTRO)

run:
	$(COMPOSE) run --rm $(DISTRO)

down:
	$(COMPOSE) down --remove-orphans

rebuild: down
	$(COMPOSE) build --no-cache $(DISTRO)
