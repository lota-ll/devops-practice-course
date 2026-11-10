# homelab-ansible — еталон модуля I1

Вміст цієї директорії = корінь репозиторію `homelab-ansible`. Відкривай після власної спроби.

## Запуск

```bash
make install                         # .venv, ansible-core 2.22.0, ansible-lint 26.11.0, колекції
# відредагуй inventory/hosts.yml (IP, користувачі) і admin_networks у group_vars/all/main.yml
make ping
make facts
make check LIMIT=pi5                 # що змінилося б
make site                            # обидва хости (EXTRA=-K, якщо sudo з паролем)
make idempotence                     # другий прогін -> changed=0

# cinomir на Pi (після Спринту 00, коли в GHCR є arm64-образ)
cp inventory/group_vars/home/vault.yml.example inventory/group_vars/home/vault.yml
# заповни, потім:
.venv/bin/ansible-vault encrypt inventory/group_vars/home/vault.yml
# і задай cinomir_image у group_vars/home/main.yml
make cinomir EXTRA="-e cinomir_version=sha-1a2b3c4"
```

## Структура

```
ansible.cfg, requirements.yml, Makefile, .ansible-lint
inventory/
├── hosts.yml                  # home: pi5 · lab: work-srv
└── group_vars/
    ├── all/main.yml           # часовий пояс, ключ, admin_networks, правила firewall
    └── home/main.yml          # Pi: менші логи Docker (+ vault.yml для cinomir)
playbooks/
├── facts.yml                  # що за хости
├── site.yml                   # common + docker + node_exporter на всі хости
└── cinomir.yml                # cinomir на home
roles/
├── common/                    # пакети, час, SSH hardening, unattended-upgrades, nftables
├── docker/                    # Docker CE (deb822, amd64/arm64), daemon.json
├── node_exporter/             # реліз + checksum, systemd з hardening, перевірка /metrics
└── cinomir/                   # env-файли (vault), compose.yaml, docker_compose_v2, /readyz
```

## Чому саме так

| Рішення | Чому |
|---|---|
| `host_key_checking = True` | Вимкнення = MITM на першому підключенні непомітний. Ключ хоста приймаємо вручну один раз |
| `pipelining = True` + ControlPersist | Менше SSH-з'єднань на задачу — відчутно через VPN |
| SSH drop-in `10-hardening.conf` + `validate` | Не чіпаємо файл дистрибутива; перемагаємо `50-cloud-init.conf`; зламаний конфіг не потрапляє на диск |
| `reload`, а не `restart` (ssh, nftables) | Сесії не рвуться; `restart nftables` на Docker-хості робить `flush ruleset` |
| nftables: своя таблиця, без `flush ruleset` | Таблиці Docker лишаються недоторканими |
| Порти — одна змінна в `group_vars/all` | Роль `node_exporter` не знає про firewall, `common` не знає про node_exporter |
| `docker_users: []` | Група docker = root; рішення має бути явним |
| node_exporter з релізу, не з apt | Актуальна версія однакова на обох дистрибутивах, перевірка checksum, повний контроль над unit |
| cinomir: три env-файли | Токен бота бачить лише контейнер бота, пароль БД — лише postgres і застосунок |
| cinomir: лише `sha-…` | Що працює на Pi, видно з команди деплою / Git; `pull: missing` коректний для незмінних тегів |
| Molecule не використано | Для двох реальних хостів `make idempotence` дає той самий сигнал простіше. Molecule — коли ролі стануть спільними для команди |

## Що перевірено, а що ні (10.11.2026)

| Перевірка | Результат |
|---|---|
| `ansible-lint` (профіль **production**) | ✅ 0 порушень |
| `ansible-playbook --syntax-check` усіх playbook | ✅ |
| Ролі `common` + `node_exporter` — справжній прогін на Ubuntu 24.04 (x86_64) | ✅ 20 задач, потім повторний прогін `changed=0`. Перевірено: таблиця nftables застосована з правильними правилами, `sshd -t` проходить з drop-in, `node_exporter 1.12.1` віддає метрики |
| Шаблони ролі `cinomir` + `docker compose config` | ✅ на тестових значеннях; знайдено і виправлено: `urlencode` не кодує `/` у паролі |
| Роль `docker` | ⚠️ не виконувалась: у середовищі, де писався еталон, `download.docker.com` заблоковано. Lint і синтаксис — ✅ |
| Raspberry Pi OS (arm64) і робочий сервер | ⚠️ еталон тестувався на одному x86-хості без systemd-PID 1 (systemctl-емулятор). Перший прогін на Pi — частина твоєї роботи |
| Роль `cinomir` повністю | ⚠️ потрібні Docker і образ у GHCR |

Знайдеш розбіжність — запиши в `docs/notes/i1.md`: це і є матеріал для історії «як я дебажив роль на ARM».
