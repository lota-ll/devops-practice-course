# 🛠️ DevOps Practice Course

Практичний курс підготовки до позиції **Junior / Middle DevOps Engineer**, побудований на аналізі реальних вакансій (Djinni, листопад 2026).

Не «теми тижня», а **виробничі сценарії**: кожен спринт — бізнес-задача, критерії приймання, навмисні поломки і історія для співбесіди. Усе відпрацьовується на одному навчальному проєкті — Telegram-боті порівняння цін у супермаркетах Києва [**Ціномір (cinomir)**](docs/project-cinomir.md).

## Документи

| Документ | Що всередині |
|---|---|
| [📊 Аналіз ринку](docs/market-analysis-2026-11.md) | 118 DevOps-вакансій, частота навичок у 25 junior-вакансіях, три профілі «джуна» |
| [🗺️ Roadmap](docs/roadmap.md) | 11 спринтів: сценарій, що будуємо, Definition of Done, вартість AWS |
| [🛒 Проєкт cinomir](docs/project-cinomir.md) | Архітектура, джерела даних, API, метрики, відомі обмеження, як росте репозиторій |
| [🧩 Шаблон модуля](docs/module-template.md) | Структура кожного спринту |

## Прогрес

| # | Спринт | Матеріал | Статус |
|---|---|---|---|
| 00 | [cinomir: baseline](sprints/00-cinomir-baseline/README.md) | ✅ модуль · підказки · еталон | ⬜ |
| 01 | Terraform на AWS | ⏳ | ⬜ |
| 02 | Kubernetes core + траблшутинг | ⏳ | ⬜ |
| 03 | Helm + Gateway API + TLS | ⏳ | ⬜ |
| 04 | Observability: метрики + логи | ⏳ | ⬜ |
| 05 | GitOps з ArgoCD | ⏳ | ⬜ |
| 06 | EKS через Terraform | ⏳ | ⬜ |
| 07 | Jenkins + on-prem лабораторія | ⏳ | ⬜ |
| 08 | DevSecOps на рівні платформи | ⏳ | ⬜ |
| 09 | Reliability / game days | ⏳ | ⬜ |
| 10 | Job readiness | ⏳ | ⬜ |

## Як користуватись

```
sprints/NN-назва/
├── README.md   ← 1. завдання: сценарій, задачі, break-it, DoD, interview prep
├── hints.md    ← 2. застряг > 30–40 хв: підказки від загальної до конкретної
└── solution/   ← 3. після власної спроби: повний робочий еталон + пояснення рішень
```

1. Задачі виконуються **в окремому репозиторії** `cinomir`, а не тут.
2. Підказки не містять готового коду — лише напрямок.
3. Еталон у `solution/` — повний і перевірений; порівнюй своє рішення, а не копіюй.
4. Після спринту — познач статус у таблиці вище (⬜ → ✅).

## Середовище

- Linux (Ubuntu) або WSL2, Docker Engine + Compose v2, Python 3.12+, Git, `make`
- Обліковий запис GitHub (GHCR, Actions, Environments)
- Telegram: бот від [@BotFather](https://t.me/BotFather) (токен) — зі спринту 00
- AWS — зі спринту 01 (див. [вимоги до акаунта і контроль вартості](docs/roadmap.md#aws-акаунт-і-контроль-вартості))

## Публікація цього репозиторію

```bash
cd devops-practice-course
git init -b main
git add .
git commit -m "docs: course roadmap, market analysis, sprint 00"
gh repo create devops-practice-course --public --source=. --push   # або через веб-інтерфейс GitHub
```
