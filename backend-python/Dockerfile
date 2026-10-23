# Backend API image - started by the root docker-compose.yml
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.12.18 /uv /usr/local/bin/

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:${PATH}"

WORKDIR /app

# dependencies first, so a code change doesn't reinstall them
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# migrations run on startup (AUTO_MIGRATE) and read alembic.ini from the working directory;
# config/domains.json is read at runtime
COPY alembic.ini ./
COPY alembic ./alembic
COPY config ./config
COPY app ./app

RUN useradd --create-home --uid 1000 api
USER api

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
