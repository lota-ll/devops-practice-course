.DEFAULT_GOAL := help
PY ?= python3
VENV := .venv
BIN := $(VENV)/bin
LIMIT ?=
EXTRA ?=
L := $(if $(LIMIT),--limit $(LIMIT),)

.PHONY: help install lint ping facts check site idempotence cinomir vault-edit

help: ## Показати команди
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

$(BIN)/activate:
	$(PY) -m venv $(VENV)

install: $(BIN)/activate ## venv + ansible-core + ansible-lint + колекції
	$(BIN)/pip install "ansible-core==2.22.0" "ansible-lint==26.11.0"
	$(BIN)/ansible-galaxy collection install -r requirements.yml

lint: ## ansible-lint (профіль production) + syntax-check
	$(BIN)/ansible-lint
	$(BIN)/ansible-playbook --syntax-check playbooks/*.yml

ping: ## Чи бачить Ansible хости: make ping LIMIT=pi5
	$(BIN)/ansible all -m ansible.builtin.ping $(L)

facts: ## ОС, архітектура, ресурси хостів
	$(BIN)/ansible-playbook playbooks/facts.yml $(L)

check: ## Що змінилося б (нічого не змінює)
	$(BIN)/ansible-playbook playbooks/site.yml --check --diff $(L) $(EXTRA)

site: ## Застосувати базову конфігурацію
	$(BIN)/ansible-playbook playbooks/site.yml $(L) $(EXTRA)

idempotence: ## Другий прогін має дати changed=0
	$(BIN)/ansible-playbook playbooks/site.yml $(L) | tee .last-run.log
	@grep -E '^\S+\s+: ok=' .last-run.log | grep -v ' changed=0 ' && { echo "❌ НЕ ідемпотентно"; exit 1; } || echo "✅ changed=0 на всіх хостах"

cinomir: ## Розгорнути cinomir на Pi: make cinomir EXTRA="-e cinomir_version=sha-1a2b3c4"
	$(BIN)/ansible-playbook playbooks/cinomir.yml --ask-vault-pass $(EXTRA)

vault-edit: ## Редагувати зашифровані секрети
	$(BIN)/ansible-vault edit inventory/group_vars/home/vault.yml
