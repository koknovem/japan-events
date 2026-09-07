FROM mcr.microsoft.com/playwright/python:v1.62.0-noble

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/src \
    JAPAN_EVENTS_ROOT=/app \
    JAPAN_EVENTS_DOCKER=1

COPY pyproject.toml README.md ./
COPY src ./src
COPY data ./data
COPY tests ./tests

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -e ".[dev]" "playwright==1.62.0"

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=8 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=4)"

CMD ["uvicorn", "japan_events.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
