# I1: Ansible — конфігурація власних хостів

> **Сценарій:** є два «голі» Linux-хости різної архітектури: Raspberry Pi 5 удома (ARM) і робочий сервер, доступний через VPN (x86). Їх треба одною командою довести до однакового стану: SSH лише за ключами, автоматичні оновлення безпеки, firewall, Docker, метрики хоста. Повторний запуск нічого не змінює, ручна зміна на хості відкочується, секрети не лежать у Git відкритим текстом. Після Спринту 00 тією ж командою на Pi розгортається cinomir.
> **Чому зараз:** Ansible — у 10 з 25 junior-вакансій (7 обов'язково, 3 — плюс), найчастіше в on-prem / інфраструктурних. Модуль не залежить від хмари.
> **Трек:** «Інфраструктура» (власне залізо). Не вимагає cinomir, крім опційної задачі 6.
> **Вхідний рівень:** Linux-адміністрування, SSH, systemd, YAML.
> **Результат:** репозиторій `homelab-ansible`: inventory з двох хостів, ролі `common`, `docker`, `node_exporter`, `cinomir`, ansible-lint (профіль production) у CI, доведена ідемпотентність.
> **Час:** теорія ~0,5 год · практика ~4 год · break-it ~0,5–1 год
> **Вартість:** $0

## Зміст

- [Мінімум теорії](#-мінімум-теорії)
- [Підготовка хостів](#-підготовка-хостів)
- [Задачі](#-задачі)
  - [1. Control node та inventory](#задача-1-45-хв-control-node-та-inventory)
  - [2. Роль common](#задача-2-15-год-роль-common)
  - [3. Роль docker](#задача-3-45-хв-роль-docker)
  - [4. Роль node_exporter](#задача-4-45-хв-роль-node_exporter)
  - [5. Якість: lint, ідемпотентність, CI](#задача-5-30-хв-якість-lint-ідемпотентність-ci)
  - [6. Роль cinomir на Pi (опційно)](#задача-6-45-хв-опційно-роль-cinomir-на-pi)
- [Break-it drills](#-break-it-drills)
- [Типові помилки](#️-типові-помилки)
- [Definition of Done](#-definition-of-done)
- [Interview Prep](#-interview-prep)

---

## 📚 Мінімум теорії

**Ansible — це опис бажаного стану, а не скрипт.** `apt: name=nftables state=present` означає «пакет має бути», а не «встанови пакет». Якщо він уже є — нічого не відбувається (`ok`, а не `changed`). Звідси головна властивість — **ідемпотентність**: другий запуск на налаштованому хості дає `changed=0`. Якщо ні — у ролі є задача, яка «робить», а не «описує» (зазвичай `shell`/`command`).

**Push без агента.** Control node (твій WSL) підключається по SSH і виконує модулі на хості через Python. На хостах нічого не встановлюється і не працює постійно. Протилежність — pull-модель (Puppet, Chef, а в Kubernetes — ArgoCD зі Спринту 05).

**Terraform vs Ansible.** Terraform *створює* ресурси (VM, мережі, DNS) і пам'ятає їх у state. Ansible *налаштовує* те, що вже існує, і state не має — він щоразу дивиться на хост. Типова пара: Terraform створив EC2 → Ansible налаштував.

**Ролі, handlers, змінні.**
- Роль — перевикористовувана одиниця: `defaults/` (параметри, які легко перевизначити), `vars/` (внутрішні константи), `tasks/`, `handlers/`, `templates/`.
- Handler виконується **один раз наприкінці** і лише якщо його хтось сповістив (`notify`). Тому перезапуск сервісу — у handler, а не окремою задачею.
- Пріоритет змінних (спрощено): `defaults` ролі < `group_vars/all` < `group_vars/<група>` < `host_vars` < `-e`.

**Template + validate.** `template` з `validate: sshd -t -f %s` спочатку перевіряє новий файл і лише потім підміняє старий. Для SSH і firewall це різниця між «помилка в задачі» і «втратив доступ до сервера».

📖 Первинний ресурс: [Ansible Best Practices / Tips and tricks](https://docs.ansible.com/ansible/latest/tips_tricks/ansible_tips_tricks.html).

---

## 🧰 Підготовка хостів

**Raspberry Pi 5:** Raspberry Pi Imager → *Raspberry Pi OS Lite (64-bit)* → у налаштуваннях: hostname, користувач, **SSH лише за публічним ключем** (вставити `~/.ssh/id_ed25519.pub` з WSL), часовий пояс. Зарезервуй IP за Pi у роутері (DHCP reservation).

**Робочий сервер:** чиста Ubuntu Server 24.04, твій користувач із sudo, твій публічний ключ у `~/.ssh/authorized_keys`.

**WSL (control node):** Ubuntu 24.04, `python3-venv`, `make`, `ssh-keygen -t ed25519`. Перше підключення до кожного хоста — **вручну** (`ssh user@host`), щоб звірити й прийняти ключ хоста: `host_key_checking` ми не вимикаємо.

> ⚠️ Якщо WSL не бачить робочий сервер, хоча Windows бачить (VPN на хості Windows), увімкни дзеркальну мережу WSL: `%UserProfile%\.wslconfig` → `[wsl2]` `networkingMode=mirrored`, потім `wsl --shutdown`.

---

## 🔨 Задачі

Створи **окремий репозиторій** `homelab-ansible`.

### Задача 1 (45 хв): Control node та inventory

> 💡 **Навіщо:** inventory — це «карта» інфраструктури. Групи визначають, що на якому хості працює, а змінні груп — чим хости відрізняються.

- venv з `ansible-core` і `ansible-lint` (точні версії), колекції — з `requirements.yml` з точними версіями: `ansible.posix`, `community.general`, `community.docker`
- `ansible.cfg` у корені репозиторію: inventory, roles_path, `pipelining`, YAML-вивід, **без** `host_key_checking = False`
- `inventory/hosts.yml`: група `home` (pi5), група `lab` (work-srv); `inventory/group_vars/all/` — спільні змінні
- `Makefile`: `install`, `lint`, `ping`, `facts`, `check`, `site`, `idempotence`; `LIMIT=` для одного хоста
- playbook `facts.yml`: для кожного хоста ОС, реліз, архітектура, vCPU, RAM, версія Python

✅ **Перевірка:** `make ping` → `pong` від обох; `make facts` → `pi5: Debian … aarch64`, `work-srv: Ubuntu 24.04 … x86_64`.

> 🔑 [hints.md#задача-1](hints.md#задача-1) · Еталон: [ansible.cfg](solution/ansible.cfg), [hosts.yml](solution/inventory/hosts.yml), [Makefile](solution/Makefile)

### Задача 2 (1,5 год): Роль common

> 💡 **Навіщо:** однаковий базовий рівень безпеки на кожному хості — те, що інакше роблять руками і забувають на третьому сервері.

- перевірка ОС (`assert`: лише сімейство Debian) і базові пакети
- часовий пояс
- **спочатку** твій ключ в `authorized_keys`, **потім** вимкнення паролів; `assert`, що не вимкнемо паролі без ключа
- SSH hardening drop-in-файлом у `/etc/ssh/sshd_config.d/` з `validate`; handler `reload` (не `restart`)
- unattended-upgrades: щоденні оновлення безпеки, автоперезавантаження — параметр (за замовчуванням вимкнено)
- nftables: шаблон з `validate: nft -c -f %s`; policy `drop` на input; established/related, `lo`, ICMP; правила з однієї змінної-списку `{port, from?, comment}`; **без** `flush ruleset`
- усі змінні ролі — з префіксом `common_` (вимога ansible-lint)

✅ **Перевірка:** `ssh -o PubkeyAuthentication=no user@pi5` → `Permission denied (publickey)`; `sudo nft list table inet host_filter` показує твої правила; `curl pi5:9100` з мережі поза `admin_networks` не проходить.

> 🔑 [hints.md#задача-2](hints.md#задача-2) · Еталон: [roles/common/](solution/roles/common/)

### Задача 3 (45 хв): Роль docker

> 💡 **Навіщо:** встановлення Docker на хости різних дистрибутивів і архітектур — класичне завдання «для Ansible» і перевірка, що роль не захардкоджена під одну машину.

- архітектура з фактів (`x86_64 → amd64`, `aarch64 → arm64`) через таблицю у `vars/`, а не `if`
- видалення конфліктних пакетів (`docker.io`, `containerd`, `runc`, …)
- репозиторій Docker у форматі **deb822** (`deb822_repository`), ключ прив'язаний лише до цього репозиторію (`signed_by`), дистрибутив і реліз — з фактів (Pi OS → `debian`, сервер → `ubuntu`)
- `daemon.json` з ротацією логів (на Pi — менші ліміти через `group_vars/home`), handler на перезапуск
- `docker_users` за замовчуванням порожній — з коментарем, чому

✅ **Перевірка:** `make site LIMIT=home` → `ssh pi5 docker info` показує `Architecture: aarch64`, `Logging Driver: json-file`; той самий запуск на work-srv — без змін у ролі.

> 🔑 [hints.md#задача-3](hints.md#задача-3) · Еталон: [roles/docker/](solution/roles/docker/)

### Задача 4 (45 хв): Роль node_exporter

> 💡 **Навіщо:** встановлення бінарника з релізу з перевіркою checksum і hardening systemd — типовий спосіб розгортати агенти, яких немає в репозиторіях або там вони застарілі. Метрики знадобляться у Спринті 04.

- версія — змінна; URL і назва архіву збираються з версії й архітектури
- `get_url` з `checksum: sha256:<URL sha256sums.txt>` — без checksum не встановлюємо
- системний користувач без shell; unit-файл із шаблону з hardening (`NoNewPrivileges`, `ProtectSystem=strict`, …)
- зміна версії або unit → handler перезапуску; наприкінці `flush_handlers` і перевірка `/metrics` через `uri` з `retries`
- порт 9100 відкрито лише для `admin_networks` (через змінну ролі `common`)

✅ **Перевірка:** `curl http://pi5:9100/metrics | grep node_exporter_build_info` → `goarch="arm64"`; на work-srv — `goarch="amd64"`; `node_exporter_version` на іншу версію → перезапуск, на ту саму → `changed=0`.

> 🔑 [hints.md#задача-4](hints.md#задача-4) · Еталон: [roles/node_exporter/](solution/roles/node_exporter/)

### Задача 5 (30 хв): Якість: lint, ідемпотентність, CI

> 💡 **Навіщо:** роль, яку не перевіряє CI, ламається тихо. Ідемпотентність — головний критерій якості ролі, і її легко перевірити автоматично.

- `.ansible-lint` з `profile: production` — нуль порушень
- `make idempotence`: прогін, і помилка, якщо хоч на одному хості `changed` ≠ 0
- `make check` (`--check --diff`): що змінилося б, нічого не змінюючи
- GitHub Actions: `ansible-lint` + `--syntax-check` на PR і push (хостів у CI немає — це нормально)

✅ **Перевірка:** `make lint` → `Passed … Profile 'production'`; `make site && make idempotence` → `✅ changed=0 на всіх хостах`.

> 🔑 [hints.md#задача-5](hints.md#задача-5) · Еталон: [.ansible-lint](solution/.ansible-lint), [ansible.yml](solution/.github/workflows/ansible.yml)

### Задача 6 (45 хв, опційно): Роль cinomir на Pi

> 💡 **Навіщо:** перший постійний «прод» для cinomir і чесна відповідь на питання «як ти деплоїш без Kubernetes». Виконується, коли в GHCR уже є arm64-образ зі Спринту 00.

- залежність від ролі `docker` у `meta/main.yml`
- секрети — `inventory/group_vars/home/vault.yml`, зашифрований **ansible-vault**; змінні ролі посилаються на `vault_*`
- **три env-файли** (`app`, `db`, `bot`) з правами `0600`: токен бота не потрапляє в контейнери postgres і api; `no_log: true` на задачах із секретами
- `compose.yaml` з шаблону: образ із GHCR, ліміти пам'яті під Pi, API лише на `127.0.0.1`, `validate: docker compose -f %s config --quiet`
- версія — **лише незмінний тег** `sha-xxxxxxx` (`assert`); `staging`/`latest` відхиляються
- `docker_compose_v2`: змінився тег → контейнери перестворюються; змінились лише env-файли → `recreate: always`
- наприкінці — `uri` на `/readyz` з повторами

✅ **Перевірка:** `make cinomir EXTRA="-e cinomir_version=sha-1a2b3c4"` → бот відповідає з Pi; повторний запуск → `changed=0`; новий тег → оновлення без ручних команд на Pi.

> 🔑 [hints.md#задача-6](hints.md#задача-6) · Еталон: [roles/cinomir/](solution/roles/cinomir/), [cinomir.yml](solution/playbooks/cinomir.yml)

---

## 💥 Break-it drills

| # | Що зламати | Що має статися | Висновок |
|---|---|---|---|
| 1 | Додай у `common` задачу `shell: echo "managed" >> /etc/motd` | `make idempotence` падає; у `/etc/motd` рядок дублюється з кожним запуском | `shell` не знає бажаного стану → `lineinfile` / `template` |
| 2 | Познач у шаблоні sshd `PermitRootLogin maybe` | Задача падає на `validate`, старий файл лишається, доступ є | Що було б без `validate` — запиши, **не перевіряй** |
| 3 | На хості вручну зміни `/etc/ssh/sshd_config.d/10-hardening.conf` | `make check` показує diff, `make site` повертає файл | Drift виявляється і виправляється тим самим кодом |
| 4 | На Pi з Docker: `sudo systemctl restart nftables`, потім `docker run --rm alpine ping -c1 1.1.1.1` | Контейнер втратив інтернет: `ExecStop` юніта робить `nft flush ruleset` і зносить таблиці Docker | Тому handler — `reloaded`; лікується `systemctl restart docker` |
| 5 | (Після задачі 6) У `compose.yaml` зміни `127.0.0.1:8000:8000` на `8000:8000` | `curl http://pi5:8000/healthz` з ноутбука працює, хоча nftables input — `drop` | Опубліковані Docker порти йдуть через DNAT/forward, а не input |
| 6 | Прибери `no_log` із задачі з env-файлами, запусти з `-v` | Токен бота у виводі Ansible (і в логах CI, якби там запускали) | `no_log` — для кожної задачі з секретами |
| 7 | Вимкни VPN і запусти `make site` | work-srv `UNREACHABLE`, pi5 налаштовано; recap показує обидва | `make site LIMIT=home`; недоступний хост не зупиняє інші |
| 8 | Прибери правило ssh з `common_firewall_tcp_rules` і запусти **лише** `make check LIMIT=home` | У diff видно, що правило зникає | Застосувати таке = втратити доступ. Страховка — нижче |

> 🛟 **Як безпечно міняти firewall на віддаленому хості:** перед застосуванням заплануй відкат (`sudo systemd-run --on-active=5min nft delete table inet host_filter`), застосуй, перевір нове SSH-підключення, скасуй таймер (`systemctl stop run-*.timer`). Pi має фізичний доступ — ідеальне місце, щоб потренуватися.

---

## ⚠️ Типові помилки

| Симптом | Причина | Фікс |
|---|---|---|
| `Missing sudo password` | На work-srv sudo з паролем | `make site EXTRA=-K` |
| `Host key verification failed` | Хост новий або перевстановлений | `ssh` вручну, звірити й прийняти ключ; після перевстановлення — `ssh-keygen -R host` |
| `PasswordAuthentication no`, а пароль досі працює | `50-cloud-init.conf` з `yes`, а наш файл читається пізніше | Префікс `10-`: у sshd перемагає **перше** значення |
| `Failed to import the required Python library (debian)` | `deb822_repository` потребує `python3-debian` на хості | Встановити перед задачею з репозиторієм |
| Docker-репозиторій 404 на Pi | Узято `ubuntu` або `raspbian` замість `debian` | `ansible_facts.distribution | lower` (Pi OS 64-bit = `Debian`) |
| Після reload nftables контейнери без мережі | `flush ruleset` у шаблоні | Лише своя таблиця: оголосити → `delete table` → створити |
| `var-naming[no-role-prefix]` в ansible-lint | Змінні ролі без префікса | `common_*`, `docker_*`, `node_exporter_*`, `cinomir_*` |
| `changed` щоразу на `get_url` | Немає `checksum` або dest у тимчасовій директорії, що очищується | `checksum` + стабільний `dest` |
| `cinomir_version` не оновлює контейнери | Тег `staging` змінний, а `pull: missing` не тягне вже наявний | Деплоїти лише `sha-…` |

---

## 📦 Definition of Done

- [ ] `make install && make lint` — зелені, профіль `production`
- [ ] `make facts` показує обидва хости з різними архітектурами
- [ ] `make site` на обох хостах → `make idempotence` → `changed=0`
- [ ] SSH лише за ключами, root-вхід заборонено, unattended-upgrades активні
- [ ] nftables: SSH відкрито, 9100 — лише з `admin_networks`
- [ ] Docker на обох хостах з ротацією логів
- [ ] `node_exporter` на обох, `/metrics` віддається
- [ ] CI: ansible-lint + syntax-check на кожен PR
- [ ] break-it 1–8 виконані, висновки — у `docs/notes/i1.md`
- [ ] (опційно) cinomir працює на Pi, секрети у vault, деплой за тегом `sha-…`

**GitHub deliverable:** репозиторій `homelab-ansible` з README (схема хостів, як запустити), зеленим CI і без жодного секрету відкритим текстом.

---

## 🎤 Interview Prep

| Питання | Де ти це робив | Ключові слова |
|---|---|---|
| Terraform чи Ansible — де межа? | Задача 1, теорія | provisioning vs configuration, state, immutable vs mutable |
| Що таке ідемпотентність і як її перевірити? | Задача 5, break-it #1 | `changed=0`, другий прогін, `shell` vs модулі, `creates` |
| Навіщо handlers? Коли `flush_handlers`? | ssh, nftables, node_exporter | notify, один раз наприкінці, перевірка після перезапуску |
| Як зберігати секрети в Ansible? | Задача 6 | ansible-vault, `vault_*`, `no_log`, External Secrets як наступний крок |
| Як не втратити доступ, змінюючи SSH / firewall? | Задача 2, break-it #2, #8 | `validate`, `reload`, `--check --diff`, таймер відкату |
| Як підтримати різні ОС / архітектури в одній ролі? | Роль docker | факти, таблиці у `vars/`, `assert` |
| Push vs pull конфігурації? | Теорія | агент, SSH, Puppet/Chef, ArgoCD |
| Чому firewall на хості не захищає порт контейнера? | Break-it #5 | DNAT, forward, `DOCKER-USER`, bind на 127.0.0.1 |
| Порядок пріоритету змінних? | defaults vs group_vars | defaults < group_vars < host_vars < extra vars |

**STAR-історія:** *«У мене два хости різної архітектури — ARM і x86 — і різні дистрибутиви. Я написав ролі, які за фактами хоста обирають репозиторій і архітектуру, і довів ідемпотентність: другий прогін — `changed=0`, перевіряється однією командою. SSH і firewall змінюються лише через шаблони з `validate`, тому помилка в конфігурації зупиняє задачу, а не відрізає доступ. Під час тестів знайшов, що рестарт nftables на Docker-хості зносить правила Docker, — тому handler робить `reload`, а шаблон керує лише своєю таблицею.»*

**Питання інтерв'юеру:** як у вас керують конфігурацією серверів поза Kubernetes — Ansible з CI, AWX, чи щось інше? Як відстежуєте drift?

---

## ➡️ Що далі

- **01:** роль `common` + `docker` застосовуються до EC2, створеної Terraform (замість cloud-init)
- **04:** Prometheus збирає `node_exporter` з Pi і сервера — дашборд хостів
- **07:** ті самі ролі — на VM у Proxmox/KVM
