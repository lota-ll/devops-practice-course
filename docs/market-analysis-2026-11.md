# 📊 Аналіз ринку: Junior / Middle DevOps (Djinni, 04.11.2026)

> Зріз, на якому побудовано [roadmap](roadmap.md). Повторювати раз на 2–3 місяці — ринок рухається.

## Методика

- **Джерело:** djinni.co, категорія **DevOps**, авторизований перегляд (анонімний ховає частину junior-вакансій).
- **Фільтр:** досвід «Без досвіду» / «1 рік» / «2 роки».
- **Обробка:** відкрито кожну вакансію, повний текст проскановано на ключові технології.
- Поділ «обов'язково / буде плюсом» — автоматичний, за маркерами в тексті (`nice to have`, `буде плюсом`, `перевагою`). **Загальна кількість згадок — точна, поділ — приблизний.**
- 4 з 25 вакансій пограничні (TechOps, Linux Ops support, Support Engineer, SysAdmin) — у вибірці залишені.

## Розмір ринку

| Сегмент | Вакансій | Частка |
|---|---|---|
| Усього DevOps | **118** | 100% |
| Досвід ≤ 2 роки | **25** | 21% |
| Досвід 3 роки | **21** | 18% |
| 4+ років (Senior / Lead) | ~72 | ~61% |

**Конкуренція:** на junior-вакансію приходить **40–100+ відгуків** за дні–тижні (Trainee — 103, Linux Ops — 73, Support Engineer — 65, Middle — 50).

## Частота навичок (25 вакансій ≤ 2 роки)

| Навичка | Обов'язково + плюс | Разом |
|---|---|---|
| CI/CD (будь-яка платформа) | 20 + 1 | **21** |
| Linux | 20 + 0 | **20** |
| **Kubernetes** | **14 + 6** | **20** |
| Python | 17 + 1 | 18 |
| **Terraform** | **14 + 3** | **17** |
| Bash | 15 | 15 |
| Docker | 13 + 2 | 15 |
| **Prometheus / Grafana** | **12 + 3** | **15** |
| AWS | 11 + 2 | 13 |
| Мережі (DNS, TCP/IP, VPN, firewall) | 12 | 12 |
| GitLab CI | 11 + 1 | 12 |
| Ansible | 7 + 3 | 10 |
| **ELK / OpenSearch** | 8 + 2 | **10** |
| Документація / runbooks | 8 + 2 | 10 |
| Incident response / RCA | 9 | 9 |
| GitHub Actions | 9 | 9 |
| GCP | 5 + 3 | 8 |
| Nginx | 7 + 1 | 8 |
| Windows / AD / PowerShell | 8 | 8 |
| Jenkins | 6 + 1 | 7 |
| Zabbix | 6 + 1 | 7 |
| Redis / PostgreSQL | 6–7 | 6–7 |
| Azure | 6 | 6 |
| ArgoCD / Flux | 3 + 3 | 6 |
| AI-інструменти | 4 + 1 | 5 |
| Datadog | 2 + 2 | 4 |
| Proxmox / KVM / bare-metal | 4 | 4 |
| Helm | 1 + 2 | 3 |
| Vault / secrets management | 2 + 1 | 3 |
| Сканери безпеки (Trivy, SAST, Checkov) | 1 | **1** |

## Три профілі «джуна»

| Профіль | Приклади | Обов'язкове | «Плюс» |
|---|---|---|---|
| **Класичний junior** | Rangein, Matoffo, RedCore | Linux, Docker, CI/CD, 1 хмара базово, Bash/Python, DNS/HTTP, концепція IaC, моніторинг | K8s, Terraform/Ansible, Prometheus/Grafana, Helm/ArgoCD, secrets |
| **Junior/Middle в аутсорсі** | GlobalLogic, Sigma Software, DBB Software | **K8s + Terraform**, AWS/GCP, CI/CD, Python/Bash | Datadog, ArgoCD, Helm |
| **On-prem / інфраструктурний** | Panda Team, JetArt, ПриватБанк, Everstake | Linux-адміністрування, **Jenkins (Pipeline + Job DSL)**, Proxmox/KVM, Nagios/Zabbix/Grafana, firewall, VPN, мережі, БД | K8s (bare-metal і хмарний) |

## Що змінюється на рівні «3 роки»

Terraform-модулі з remote state · EKS/ECS/Fargate · **ArgoCD — вимога** · Vault / Secrets Manager · Checkov, SAST, сканування образів · incident response, postmortem · SLI/SLO.

## Тренди із senior-вакансій (горизонт 1–2 роки)

- **Gateway API** замість ingress-nginx (проєкт ingress-nginx знято з підтримки у 2026)
- Karpenter, Cilium
- OpenTelemetry, стек LGTM (Loki / Grafana / Tempo / Mimir), burn-rate алерти
- Platform engineering: golden paths, self-service
- FinOps як інженерна метрика
- AI-асистенти та агенти в операціях — «comfortable with AI tools» майже у кожній вакансії middle+

## Висновки для навчального плану

1. **Kubernetes і Terraform — квиток на співбесіду** (20 і 17 із 25). Без них — відсів на скринінгу.
2. **Observability — третій обов'язковий блок**, причому **логи (ELK/OpenSearch, 10) майже так само часто, як метрики (15)**.
3. **GitLab CI (12) > GitHub Actions (9) > Jenkins (7)** у джун-вакансіях. Jenkins — короткий, але обов'язковий блок.
4. **DevSecOps-інструментів у junior майже немає (1)** — це диференціація, а не фільтр. Іде після обов'язкового ядра.
5. **ArgoCD / Helm у джунів поки «плюс»**, у middle — вимога. Іде після observability.
6. **Ops-навички явно перевіряють:** incident response, RCA, документація — 9–10 вакансій.
7. **Windows / Azure / GCP — опційні треки** під конкретну вакансію.
8. **Не витрачати час зараз:** service mesh, Crossplane, Backstage, multi-cloud, MLOps, CI/CD для mobile.

## Джерела

- [Djinni — DevOps, досвід 0–2 роки](https://djinni.co/jobs/?primary_keyword=DevOps&exp_level=no_exp&exp_level=1y&exp_level=2y)
- [Junior DevOps Engineer — Rangein](https://djinni.co/jobs/854332-junior-devops-engineer/)
- [Junior/Middle DevOps Engineer — GlobalLogic](https://djinni.co/jobs/854245-junior-middle-devops-engineer/)
- [Junior DevOps Engineer — DBB Software](https://djinni.co/jobs/636877-junior-devops-engineer/)
- [Junior / Trainee DevOps Engineer — Matoffo](https://djinni.co/jobs/855155-junior-trainee-devops-engineer/)
- [Middle DevOps Engineer — Sigma Software](https://djinni.co/jobs/856308-middle-devops-engineer/)
