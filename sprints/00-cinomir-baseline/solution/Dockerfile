# syntax=docker/dockerfile:1
# Один образ — три процеси (api / worker / bot). Різниться лише команда запуску.

# ---------- builder: компілятори і pip лишаються тут ----------
FROM python:3.13-slim AS builder
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
WORKDIR /build

# Шар залежностей перебудовується лише коли змінився pyproject.toml
COPY pyproject.toml .
RUN python -c "import tomllib; print('\n'.join(tomllib.load(open('pyproject.toml','rb'))['project']['dependencies']))" > requirements.txt \
 && pip install -r requirements.txt

COPY src ./src
RUN pip install --no-deps .

# ---------- runtime: лише venv і міграції ----------
FROM python:3.13-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PATH="/opt/venv/bin:$PATH"
RUN useradd --system --uid 10001 --no-create-home --shell /usr/sbin/nologin cinomir
WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
COPY alembic.ini .
COPY migrations ./migrations

USER 10001
EXPOSE 8000
# Kubernetes використовуватиме власні probes; цей healthcheck — для docker / compose
HEALTHCHECK --interval=15s --timeout=3s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=2).status == 200 else 1)"
CMD ["uvicorn", "--factory", "cinomir.api:create_app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--no-access-log"]
