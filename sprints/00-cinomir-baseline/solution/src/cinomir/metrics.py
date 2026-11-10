"""Prometheus-метрики. Кожен процес (api / worker / bot) оновлює лише свої."""

from prometheus_client import Counter, Gauge, Histogram

# --- API: HTTP ---
HTTP_REQUESTS = Counter(
    "cinomir_http_requests_total", "HTTP requests handled by the API", ["method", "path", "status"]
)
HTTP_LATENCY = Histogram(
    "cinomir_http_request_duration_seconds", "API request latency", ["method", "path"]
)

# --- API: мережі ---
CHAIN_REQUESTS = Counter(
    "cinomir_chain_requests_total",
    "Requests to supermarket chains",
    ["chain", "outcome"],  # ok | timeout | blocked | error
)
CHAIN_LATENCY = Histogram(
    "cinomir_chain_request_duration_seconds",
    "Latency of chain search requests",
    ["chain"],
    buckets=(0.1, 0.25, 0.5, 1, 2, 4, 8),
)
# Раптові 0 товарів при успішній відповіді = мережа змінила API. Алерт — у спринті 04.
CHAIN_LAST_ITEMS = Gauge(
    "cinomir_chain_last_items", "Items returned by the last successful search", ["chain"]
)
SEARCHES = Counter("cinomir_searches_total", "Searches served", ["cache"])  # hit | miss

# --- Worker ---
ENRICH = Counter(
    "cinomir_enrich_total", "Barcode enrichment jobs", ["result"]
)  # found | none | skipped | error

# --- Bot ---
BOT_UPDATES = Counter("cinomir_bot_updates_total", "Telegram updates handled", ["kind"])
