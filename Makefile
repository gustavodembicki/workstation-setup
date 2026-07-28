PLATFORM ?= linux
DISTRO ?= ubuntu
PYTHON ?= python

LINUX_COMPOSE := docker compose -p workstation-setup-linux \
	-f tests/integration/docker/linux/docker-compose.yml
WINDOWS_COMPOSE := docker compose -p workstation-setup-windows \
	-f tests/integration/docker/windows/docker-compose.yml
DAEMON_CHECK := $(PYTHON) tests/integration/docker/check_daemon.py

# Support both conventional targets (`make build-windows`) and the requested
# positional form (`make build windows`).
ifneq ($(filter windows,$(MAKECMDGOALS)),)
override PLATFORM := windows
endif
ifneq ($(filter linux,$(MAKECMDGOALS)),)
override PLATFORM := linux
endif
ifneq ($(and $(filter windows,$(MAKECMDGOALS)),$(filter linux,$(MAKECMDGOALS))),)
$(error Choose exactly one platform: linux or windows)
endif

ifeq ($(PLATFORM),windows)
COMPOSE := $(WINDOWS_COMPOSE)
SERVICE := windows
else ifeq ($(PLATFORM),linux)
COMPOSE := $(LINUX_COMPOSE)
SERVICE := $(DISTRO)
else
$(error Unsupported PLATFORM=$(PLATFORM); use linux or windows)
endif

.PHONY: help validate validate-linux validate-windows check-daemon \
	build run test down rebuild \
	build-linux run-linux test-linux down-linux rebuild-linux \
	build-windows run-windows test-windows down-windows rebuild-windows \
	linux windows

help:
	@echo "Linux:  make build-linux [DISTRO=ubuntu|fedora|arch]"
	@echo "        make run-linux | test-linux | rebuild-linux | down-linux"
	@echo "Windows: make build-windows | run-windows | test-windows | rebuild-windows | down-windows"
	@echo "Aliases: make build linux   or   make build windows"
	@echo "Config:  make validate"

validate: validate-linux validate-windows

validate-linux:
	$(LINUX_COMPOSE) config --quiet

validate-windows:
	$(WINDOWS_COMPOSE) config --quiet

check-daemon:
	@$(DAEMON_CHECK) --expect $(PLATFORM)

build: check-daemon
	$(COMPOSE) build $(SERVICE)

run: check-daemon
	$(COMPOSE) run --rm $(SERVICE)

test: check-daemon
ifeq ($(PLATFORM),windows)
	$(COMPOSE) run --rm $(SERVICE) powershell.exe -NoLogo -Command \
		"pytest tests/unit; if ($$LASTEXITCODE -ne 0) { exit $$LASTEXITCODE }; \
		ruff check .; if ($$LASTEXITCODE -ne 0) { exit $$LASTEXITCODE }; \
		pyinstaller --clean -y packaging/pyinstaller.spec; \
		if ($$LASTEXITCODE -ne 0) { exit $$LASTEXITCODE }; \
		.\dist\workstation-setup.exe --version"
else
	$(COMPOSE) run --rm $(SERVICE) /bin/bash -lc \
		"source .venv/bin/activate && pytest tests/unit && ruff check ."
endif

down: check-daemon
	$(COMPOSE) down --remove-orphans

rebuild: check-daemon
	$(COMPOSE) down --remove-orphans
	$(COMPOSE) build --no-cache $(SERVICE)

build-linux:
	$(MAKE) build PLATFORM=linux DISTRO=$(DISTRO)

run-linux:
	$(MAKE) run PLATFORM=linux DISTRO=$(DISTRO)

test-linux:
	$(MAKE) test PLATFORM=linux DISTRO=$(DISTRO)

down-linux:
	$(MAKE) down PLATFORM=linux DISTRO=$(DISTRO)

rebuild-linux:
	$(MAKE) rebuild PLATFORM=linux DISTRO=$(DISTRO)

build-windows:
	$(MAKE) build PLATFORM=windows

run-windows:
	$(MAKE) run PLATFORM=windows

test-windows:
	$(MAKE) test PLATFORM=windows

down-windows:
	$(MAKE) down PLATFORM=windows

rebuild-windows:
	$(MAKE) rebuild PLATFORM=windows

# Positional selectors are intentionally no-ops; their presence in
# MAKECMDGOALS selects PLATFORM above.
linux windows:
	@:
