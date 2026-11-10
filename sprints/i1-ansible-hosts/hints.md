# I1: підказки

Відкривай, якщо застряг більш ніж на 30–40 хвилин. Підказки йдуть від загальної до конкретної. Готовий код — у [solution/](solution/).

---

## Задача 1

<details><summary>1. ansible-core чи ansible?</summary>

`ansible` — це `ansible-core` плюс ~100 колекцій. Для свого репозиторію краще `ansible-core` + лише потрібні колекції в `requirements.yml` з точними версіями: менше, швидше, відтворювано.
</details>

<details><summary>2. Де Ansible шукає конфігурацію</summary>

`ANSIBLE_CONFIG` → `./ansible.cfg` у поточній директорії → `~/.ansible.cfg` → `/etc/ansible/ansible.cfg`. Тому `ansible.cfg` у корені репозиторію і команди — з кореня (через `make`). У WSL є пастка: якщо репозиторій лежить на `/mnt/c/...` (world-writable), Ansible **ігнорує** `ansible.cfg` з міркувань безпеки. Тримай репозиторій у файловій системі WSL (`~/...`).
</details>

<details><summary>3. Різні користувачі / sudo з паролем</summary>

`ansible_user` — у inventory на рівні хоста. Якщо sudo просить пароль — `-K` (`--ask-become-pass`), а не пароль у файлі.
</details>

---

## Задача 2

<details><summary>1. Порядок задач, щоб не втратити SSH</summary>

Ключ в `authorized_keys` → `assert` (ключ не порожній, якщо паролі вимикаються) → лише тоді конфіг sshd. І `reload`, а не `restart`: наявні сесії живуть, а нову ти перевіряєш у другому терміналі.
</details>

<details><summary>2. Чому drop-in і чому <code>10-</code></summary>

У Debian/Ubuntu `sshd_config` на самому початку має `Include /etc/ssh/sshd_config.d/*.conf`. Для більшості параметрів sshd бере **перше** знайдене значення. cloud-init кладе `50-cloud-init.conf` (інколи з `PasswordAuthentication yes`) — твій файл має йти раніше за алфавітом. Перевірити фактичну конфігурацію: `sudo sshd -T | grep -i passwordauth`.
</details>

<details><summary>3. Як тримати правила firewall в одному місці</summary>

Одна змінна-список словників `{port, from?, comment}`. Роль `common` її рендерить, а інші ролі *нічого* не знають про firewall — порт node_exporter додається в `group_vars/all`. Мережі з `from` розділи на IPv4 і IPv6 (`ip saddr` / `ip6 saddr`) — фільтр `select('search', ':')`.
</details>

<details><summary>4. nftables поруч із Docker</summary>

Docker створює свої таблиці (`ip filter`, `ip nat`). `flush ruleset` у твоєму файлі їх знесе. Ідіома «перестворити лише свою таблицю» в одному файлі:
оголосити порожню таблицю (щоб `delete` не впав на першому запуску) → `delete table` → описати таблицю повністю. Усе в одній транзакції `nft -f`.
</details>

---

## Задача 3

<details><summary>1. Як дізнатися правильний репозиторій</summary>

`ansible -m setup pi5 -a 'filter=ansible_distribution*'`. На Raspberry Pi OS 64-bit це `Debian` + `trixie`/`bookworm` → `download.docker.com/linux/debian`. На сервері — `Ubuntu` + `noble`.
</details>

<details><summary>2. deb822 замість <code>apt_key</code></summary>

`apt_key` застарів (глобальний trusted.gpg = ключ довіряється для всіх репозиторіїв). `deb822_repository` з `signed_by: <URL ключа>` сам завантажить ключ і прив'яже його лише до цього репозиторію. Модулю потрібен `python3-debian` на хості.
</details>

<details><summary>3. Чому <code>docker_users</code> порожній</summary>

Член групи `docker` може запустити контейнер з `-v /:/host` і отримати root на хості. На власному Pi — зручно, на спільному сервері — ні. Рішення має бути свідомим, тому за замовчуванням — нікого.
</details>

---

## Задача 4

<details><summary>1. Checksum без копіювання хешів вручну</summary>

`get_url` приймає `checksum: "sha256:https://…/sha256sums.txt"` — сам завантажить файл сум і знайде рядок за назвою архіву.
</details>

<details><summary>2. Як оновлювати версію без зайвих перезапусків</summary>

Розпакування — з `creates:` (кожна версія — своя директорія в `/opt`). Копіювання бінарника в `/usr/local/bin` — `copy` з `remote_src: true`: `changed` лише коли вміст інший → `notify` перезапуску. Та сама версія → `changed=0`.
</details>

<details><summary>3. Перевірка після перезапуску</summary>

Handlers виконуються наприкінці play. Щоб перевірити `/metrics` уже з новою версією — `meta: flush_handlers` перед `uri`, а в `uri` — `until` + `retries`, бо сервісу треба секунда, щоб піднятися.
</details>

---

## Задача 5

<details><summary>1. Як автоматично перевірити ідемпотентність</summary>

Запусти playbook, збережи вивід, знайди рядки `PLAY RECAP` (`host : ok=…`) і переконайся, що в кожному `changed=0`. Повноцінний варіант — Molecule (`converge` → `idempotence`) з тестовими контейнерами; для двох ролей і реальних хостів вистачить `make`.
</details>

<details><summary>2. Чого <code>--check</code> не покаже</summary>

Check mode не виконує команди і не завантажує файли, тому задачі, що залежать від результату попередніх (наприклад, `unarchive` після `get_url`), можуть падати або показувати неповну картину. Це підказка, а не гарантія.
</details>

---

## Задача 6

<details><summary>1. Організація секретів</summary>

У `group_vars/home/` два файли: `main.yml` (відкритий) і `vault.yml` (зашифрований, лише змінні `vault_*`). У `defaults` ролі: `cinomir_postgres_password: "{{ vault_cinomir_postgres_password }}"`. Так `grep` по репозиторію показує, звідки береться секрет, без розшифрування.
</details>

<details><summary>2. Пароль у URL бази</summary>

Пароль потрапляє в `DATABASE_URL` → спецсимволи треба кодувати (`urlencode`, і окремо `/` → `%2F`, бо `urlencode` його лишає). А ще простіше — генерувати лише hex: `openssl rand -hex 24`. Символ `$` в env-файлі Compose може бути інтерпольований.
</details>

<details><summary>3. Коли контейнери мають перестворитись</summary>

Compose бачить зміну образу чи `compose.yaml`, але **не** вміст env-файлів. Зареєструй результат шаблонів (`register`) і передай `recreate: always`, якщо вони змінились, інакше `auto`.
</details>

<details><summary>4. Приватний пакет у GHCR</summary>

Або зроби пакет публічним (Package settings → Change visibility), або Personal Access Token з `read:packages` у vault + `community.docker.docker_login` з `no_log: true`.
</details>
