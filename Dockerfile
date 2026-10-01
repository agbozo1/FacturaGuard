# FacturaGuard web app. Build: docker build -t facturaguard .
# Run:   docker run -p 8000:8000 --env-file .env facturaguard
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Dependencies first for layer caching. Editable install keeps vendor/, web/ and data/ next to
# the code, where the app looks for them.
COPY pyproject.toml ./
COPY facturaguard ./facturaguard
RUN pip install -e ".[schematron]"

COPY web ./web
COPY vendor ./vendor
COPY data/synthetic ./data/synthetic

RUN useradd --create-home --uid 10001 app
USER app

EXPOSE 8000
# One worker: sessions live in memory. Proxy headers give the rate limiter real client IPs.
# Render sets PORT; locally it defaults to 8000.
CMD ["sh", "-c", "exec uvicorn facturaguard.api.app:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1 --proxy-headers --forwarded-allow-ips='*'"]
