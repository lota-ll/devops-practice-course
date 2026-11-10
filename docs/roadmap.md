# 🗺️ Roadmap: практичний DevOps-курс (листопад 2026)

> Побудовано на [аналізі ринку](market-analysis-2026-11.md). Навчальний проєкт — [Ціномір (cinomir)](project-cinomir.md): Telegram-бот порівняння цін у супермаркетах Києва.
> Хмара — **AWS**. Обсяг — **11 спринтів по ~10–12 годин** (≈ 2,5–3 місяці при 10–12 год/тиждень).

## Принципи

1. **Спринт = виробничий сценарій**, а не «тема тижня». Є бізнес-задача, критерії приймання (Definition of Done) і обмеження (вартість, безпека).
2. **Теорія — лише мінімум для рішень** (≤ 30% модуля). Основи Linux, Docker, CI/CD, Nginx, AWS core вважаються пройденими.
3. **Цикл кожного спринту:** побудувати → зламати навмисно (*break-it drills*) → полагодити → задокументувати (ADR / runbook / postmortem) → сформулювати історію для співбесіди.
4. **Три шари матеріалу:** `README.md` (завдання) → `hints.md` (підказки, без готового коду) → `solution/` (повний робочий еталон). Еталон відкривати **після** власної спроби.
5. **Порядок спринтів = вага навички на ринку.** Спочатку те, без чого не пройти скринінг.
6. **Не все прив'язуємо до cinomir.** Навичкам рівня застосунку (CI/CD, Kubernetes, GitOps, observability застосунку) потрібен живий сервіс — це cinomir. Навичкам рівня хоста (Ansible, hardening, мережі, віртуалізація) — справжнє залізо, а не штучна прив'язка до застосунку.

## Два треки

| Трек | Модулі | На чому |
|---|---|---|
| **Застосунок** | 00–10 | cinomir |
| **Інфраструктура** | I1, … | Raspberry Pi 5 і робочий сервер; cinomir — максимум як вантаж |

Модулі треку «Інфраструктура» не залежать від хмари і вставляються між спринтами, коли зручно. I1 найкраще робити одразу після Спринту 00: роль `cinomir` з I1 — перший постійний деплой бота.

## Середовища

| Етап | Де працює cinomir | Коли |
|---|---|---|
| Розробка | Docker Compose у WSL (Ubuntu) | Спринт 00 |
| Постійний «прод» | **Raspberry Pi 5 (8 ГБ, arm64)**: Compose через Ansible (I1), пізніше k3s | після 00 / I1 |
| Хмара | рішення відкладено (AWS / Oracle Always Free / інше) — після перевірки, чи пускають мережі з IP датацентру | спринти 01, 06 |

- Домашній IP уже перевірено spike: Сільпо, Фора, Novus відповідають. З IP датацентрів — **ні**, це ризик для будь-якого хмарного варіанту.
- Бот на long polling не потребує вхідних з'єднань → Pi працює без білого IP. Для webhook (Спринт 03) — Cloudflare Tunnel або аналог.
- Образ cinomir збирається для **amd64 і arm64** (CI Спринту 00).
- **Робочий сервер** — лише для треку «Інфраструктура» (доступ через VPN); cinomir туди не розгортаємо.

## Огляд

| # | Спринт | Ключовий результат | Вага в junior-вакансіях | AWS |
|---|---|---|---|---|
| 00 | [cinomir: baseline](../sprints/00-cinomir-baseline/README.md) | Бот + API + воркер, контейнери, Compose, CI з промоутом образу | база | — |
| 01 | Terraform на AWS | Інфраструктура як код, remote state, plan/apply у CI через OIDC | 17 / 25 | 💲 |
| 02 | Kubernetes core + траблшутинг | cinomir у kind, лабораторія поломок | **20 / 25** | — |
| 03 | Helm + Gateway API + TLS | Власний chart, оточення, міграції як hook | основа для 05 | — |
| 04 | Observability: метрики + логи | Prometheus/Grafana/Alertmanager, Loki або OpenSearch, SLO | 15 + 10 / 25 | — |
| 05 | GitOps з ArgoCD | Pull-based delivery, секрети поза Git, фіча «акції» через PR | 6 / 25 (middle: обов'язково) | — |
| 06 | EKS через Terraform | Хмарний кластер, ECR, IRSA/Pod Identity, ALB | 13 / 25 (AWS) | 💲💲 |
| 07 | Jenkins + on-prem лабораторія | Pipeline + Job DSL, Proxmox/KVM, firewall, VPN | 7 + 4 / 25 | — |
| 08 | DevSecOps на рівні платформи | Supply chain, політики допуску, захист бота і egress | диференціація | — |
| 09 | Reliability / game days | Chaos, backup/restore, postmortem, Python-автоматизація | 9–10 / 25 | 💲 |
| 10 | Job readiness | Портфоліо, CV під 3 профілі, mock-інтерв'ю | — | — |
| **I1** | [Ansible: конфігурація власних хостів](../sprints/i1-ansible-hosts/README.md) | Ролі common / docker / node_exporter / cinomir на Pi 5 + сервері, vault, lint, ідемпотентність | 10 / 25 | — |

**Опційні треки** (вмикаються під конкретну вакансію): Azure (AKS, Entra ID, Azure DevOps) · Windows (PowerShell, AD/GPO) · GCP (GKE, Cloud Build).

---

## Спринти детально

### 00 — cinomir: baseline

**Сценарій:** є робочий прототип (spike), який довів, що дані Сільпо, Фори і Novus доступні. Треба перетворити його на сервіс: «запускається однією командою, CI зелений, образ у реєстрі, бот відповідає».

**Будуємо:** api (FastAPI) + worker + bot (aiogram), PostgreSQL з історією цін, Redis (кеш + черга), Alembic-міграції, адаптери мереж з таймаутами і деградацією, JSON-логи, метрики, multi-stage Dockerfile (non-root), Compose з one-shot міграцією і профілем для бота, CI (lint → test → migrations на PostgreSQL → build → Trivy → push → промоут через environment з approval).

**DoD:** `make up` → `make search Q="тунець у власному соку"` повертає товари трьох мереж · бот у Telegram відповідає лише тобі · CI зелений на PR · образ `ghcr.io/<you>/cinomir:sha-xxxxxxx` · промоут у `staging` лише після ручного approve.

---

### 01 — Terraform на AWS

**Сценарій:** cinomir треба запустити в AWS так, щоб середовище відтворювалось з нуля за одну команду, а зміни інфраструктури проходили code review.

**Будуємо:**
- модулі `network` (VPC, публічні/приватні підмережі), `compute` (EC2 + Security Groups + cloud-init з Docker Compose), `registry` (ECR)
- оточення `envs/dev` і `envs/prod` з різними змінними
- remote state у S3 з нативним блокуванням (`use_lockfile = true`, Terraform ≥ 1.10 — DynamoDB для lock більше не потрібен)
- GitHub Actions: `fmt` + `validate` + `tflint` + `plan` як коментар у PR; `apply` на main через environment з approval; доступ до AWS — **OIDC-роль, без ключів**
- нотатка про OpenTofu як open-source альтернативу
- **перевірка egress:** чи відповідають Сільпо / Фора / Novus з IP AWS (EC2 у `eu-central-1`) — результат фіксуємо в ADR, від нього залежить спринт 06

**DoD:** `terraform destroy && terraform apply` відновлює робоче середовище з ботом · у репозиторії немає жодного AWS-ключа · будь-яка зміна інфраструктури видна як `plan` у PR · ADR «чи пускають мережі з AWS».

**Break-it:** ручна зміна SG у консолі → виявити drift через `plan` · конкурентний `apply` → побачити блокування state.

---

### 02 — Kubernetes core + траблшутинг

**Сценарій:** переходимо з Compose на Kubernetes. Перенести cinomir і навчитися діагностувати типові аварії.

**Будуємо (kind у WSL або k3s на Pi 5):** Namespace, Deployment api (HPA) і worker, Deployment bot з `replicas: 1` і `strategy: Recreate` (обговорення: чому RollingUpdate для long polling дає `409 Conflict`), StatefulSet PostgreSQL + PVC, Redis, ConfigMap / Secret (токен бота), міграція як Job, liveness/readiness/startup probes, requests/limits, PodDisruptionBudget, graceful shutdown (`terminationGracePeriodSeconds`).

**Лабораторія поломок:** `CrashLoopBackOff` (немає токена бота) · `ImagePullBackOff` · `OOMKilled` · `Pending` (ресурси / PVC) · `readiness` не проходить → трафіку немає · DNS між сервісами (бот не бачить api) · міграція не пройшла · два поди бота → `409 Conflict`.

**DoD:** `kubectl apply -k` піднімає робочий cinomir · для кожної з 7 поломок є запис «симптом → команди діагностики → причина → фікс».

---

### 03 — Helm + Gateway API + TLS

**Сценарій:** маніфести дублюються між оточеннями — переходимо на chart з параметрами.

**Будуємо:** власний chart (api / worker / bot як окремі шаблони одного образу), `values-dev.yaml` / `values-prod.yaml`, міграції як `pre-install,pre-upgrade` hook, **Gateway API** (Gateway + HTTPRoute) замість Ingress, cert-manager із self-signed / Let's Encrypt staging, `helm upgrade --atomic`, rollback. **Бот переходить на webhook:** Telegram вимагає публічний HTTPS — саме тут Gateway + TLS стають потрібними, а обмеження «лише 1 екземпляр» зникає.

**DoD:** `helm lint` і `helm template` у CI · `helm upgrade` зі зламаною міграцією не ламає робочий реліз · бот працює через webhook з валідним `secret_token` · HTTPS через Gateway.

---

### 04 — Observability: метрики + логи

**Сценарій:** «Як дізнатись, що Сільпо змінило API або Фора нас блокує, раніше, ніж бот почне відповідати порожнечею?»

**Будуємо:** kube-prometheus-stack, ServiceMonitor для трьох процесів, дашборди Grafana як код (JSON у Git): RED для API, успішність і латентність **по кожній мережі**, hit rate кешу, черга воркера. Алерти: мережа повертає 0 товарів або `blocked` довше N хв (зміна API / блокування), частка помилок мережі, ріст черги збагачення. Alertmanager → Telegram (окремий бот-канал для алертів). **Логи: Loki або OpenSearch + Fluent Bit** (ADR з порівнянням — у вакансіях обидва). SLO: 95% пошуків швидше 3 с, multi-window burn-rate алерт. Окремо 2–3 год — знайомство із Zabbix (часто в on-prem вакансіях).

**DoD:** підміна API однієї мережі на заглушку з `500` → алерт у Telegram за ≤ 5 хв · з логу помилки можна за 1 клік перейти до метрик того ж часу · ADR про вибір лог-стеку.

---

### 05 — GitOps з ArgoCD

**Сценарій:** заборонити `kubectl apply` з ноутбуків; стан кластера = стан Git.

**Будуємо:** ArgoCD, app-of-apps, окремий config-репозиторій (або директорія), CI після push образу оновлює тег у config-репо, sync policies (auto-sync, self-heal, prune), rollback через `git revert`, секрети (токен бота, пароль БД) через **External Secrets** (або Sealed Secrets) — без відкритих секретів у Git. **Фіча через GitOps-потік:** збір акцій мереж (CronJob) і кнопка «🏷 лише акції» — від PR до продакшну без жодного `kubectl`.

**DoD:** ручна зміна в кластері автоматично відкочується · деплой нової версії = merge PR · жодного секрету відкритим текстом у Git.

---

### 06 — EKS через Terraform

**Сценарій:** продакшн-кластер у хмарі, керований кодом.

**Будуємо:** модуль EKS (managed node group), ECR, **Pod Identity / IRSA** (без ключів у подах), AWS Load Balancer Controller + ALB (webhook бота), External Secrets → AWS Secrets Manager, RDS PostgreSQL (порівняння з in-cluster PostgreSQL у ADR), ElastiCache або in-cluster Redis (ADR), ArgoCD зі спринту 05 керує застосунком. ADR «EKS vs ECS/Fargate». Якщо в спринті 01 з'ясувалось, що мережі блокують IP AWS, — план egress (ADR).

**DoD:** весь стек піднімається з нуля командою з README · **знищується повністю після кожної сесії** · AWS Budget з алертом налаштований до першого `apply`.

**💲 Вартість:** control plane EKS ≈ $0.10/год, плюс вузли, NAT Gateway (≈ $0.045/год + трафік), ALB. Сесія 3–4 год ≈ $1–2; весь спринт ≈ $10–25 за дисципліни `destroy`.

---

### 07 — Jenkins + on-prem лабораторія

**Сценарій:** клієнт без хмари — власні сервери, Jenkins, віртуалізація.

**Будуємо:** Jenkins у контейнері, declarative `Jenkinsfile` для cinomir, shared library, **Job DSL** seed job (явна вимога в on-prem вакансіях). Proxmox VE (або KVM/libvirt) у nested-віртуалізації чи на вільному залізі: VM через Terraform-провайдер + ролі з I1 (Ansible), firewall-політики (nftables), WireGuard VPN для доступу, бекапи VM, моніторинг хоста.

**DoD:** pipeline у Jenkins еквівалентний GitHub Actions · нова VM з cinomir піднімається з коду · доступ до VM лише через VPN.

---

### 08 — DevSecOps на рівні платформи

**Сценарій:** аудит безпеки: бот приймає довільний текст від користувачів, токен бота дає повний контроль над ботом, а походження образів ніхто не перевіряє.

**Будуємо:**
- **бот:** rate limit на користувача, валідація і обмеження довжини запиту, перевірка екранування HTML (injection у повідомлення), ротація токена бота без простою, `secret_token` для webhook
- **API:** автентифікація між ботом і API (service token або mTLS), API не доступний ззовні кластера
- **egress NetworkPolicy:** api і worker ходять лише до доменів мереж, PostgreSQL і Redis; бот — лише до Telegram і api
- пайплайн: gitleaks, Semgrep (SAST), pip-audit (SCA), Checkov / Trivy config (IaC), Trivy image; **усі GitHub Actions — pin за SHA** (кейс: підміна тегів `trivy-action`, березень 2026)
- supply chain: SBOM (syft), підпис образу cosign (keyless OIDC), перевірка підпису в кластері (Kyverno `verifyImages`)
- кластер: Pod Security Standards (`restricted`), NetworkPolicy default-deny, RBAC least privilege, `readOnlyRootFilesystem`
- DAST: OWASP ZAP baseline проти staging
- мапінг контролів на OWASP Top 10 / CIS Kubernetes Benchmark

**DoD:** непідписаний образ не запускається в кластері · флуд від одного користувача обмежується · под api не може відкрити з'єднання з довільним хостом · звіт сканерів як артефакт CI.

---

### 09 — Reliability / game days

**Сценарій:** серія інцидентів у продакшні — треба навчитися їх переживати і вчитися на них.

**Будуємо:** reliable queue для воркера (BLMOVE + відновлення зависших задач), **circuit breaker** на мережу (лежача мережа не з'їдає таймаут у кожному пошуку), retention / агрегація `price_snapshots`, бекап PostgreSQL у S3 + **перевірене відновлення** (restore drill з виміряним RTO/RPO — історію цін не можна перезібрати), Velero для ресурсів кластера, chaos-сценарії (kill pod, вичерпання з'єднань до БД, заповнений диск, падіння Redis, мережа відповідає за 30 с, мережа змінила формат відповіді), on-call симуляція з таймером, **postmortem за шаблоном** (blameless), runbooks для кожного алерту. Python-автоматизація: CLI-звіт про стан і вартість ресурсів (boto3 + kubernetes-client).

**DoD:** відновлення БД з бекапу виконано і задокументовано з цифрами · 3 postmortem · runbook для кожного алерту спринту 04.

---

### 10 — Job readiness

**Будуємо:** README cinomir з архітектурною діаграмою, індекс ADR, звіт про вартість, 3-хвилинне демо-відео · CV у трьох варіантах під профілі вакансій ([див. аналіз](market-analysis-2026-11.md#три-профілі-джуна)) · коректне формулювання суміжного досвіду (адміністрування Linux / віртуалізації, безпека, мережі) · банк історій STAR зі спринтів · mock-інтерв'ю, частина — англійською (у вакансіях B1–B2).

**DoD:** 20+ історій STAR · CV пройшов перевірку на відповідність 5 реальним вакансіям.

---

## AWS: акаунт і контроль вартості

| Варіант | Плюси | Обмеження |
|---|---|---|
| **AWS Academy Learner Lab** (студентська) | Бюджет від навчального закладу, без картки | **Не можна створювати IAM-ролі та політики** (лише готова `LabRole`) → не працюють OIDC-роль для GitHub Actions (спринт 01), IRSA/Pod Identity і ролі контролерів (спринт 06). Обмежені сесії та регіони. Підходить для частини спринту 01 |
| **Власний акаунт (Free plan)** | Повний IAM; $100 кредитів при реєстрації + до $100 за виконання стартових активностей | Free plan діє до 6 місяців або до вичерпання кредитів і покриває не всі сервіси — **перевір доступність EKS**; перехід на Paid plan незворотний |

**Обов'язково до першого `terraform apply`:** AWS Budgets з алертами на $5 і $20 · MFA на root · робота через IAM Identity Center або окремого IAM-користувача, не root · `terraform destroy` наприкінці кожної сесії · NAT Gateway — лише в спринті 06.

## Як працювати з модулем

1. Прочитай `README.md` спринту, виконай задачі **у власному репозиторії** (`cinomir` для треку «Застосунок», `homelab-ansible` для I1).
2. Застряг більш ніж на 30–40 хв — відкрий `hints.md` (підказки йдуть від загальної до конкретної).
3. Після завершення порівняй своє рішення з `solution/`, зафіксуй відмінності в нотатках.
4. Познач спринт виконаним у [README](../README.md#прогрес).
