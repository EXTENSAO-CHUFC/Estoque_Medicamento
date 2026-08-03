# AVISO: uma única imagem atende ao consumer CDC, dashboard e registrador.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir poetry

COPY pyproject.toml poetry.lock* ./
RUN poetry install --only main --no-root

COPY . .

EXPOSE 8501

CMD ["python", "-m", "app.consumers.analytics_consumer"]
