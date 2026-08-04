# backend-python

FastAPI REST API for storing and managing CWL-based workflow components. Layered (domain → application → api, outer depends on inner only), modeled on Kotlin/Spring-style architecture rather than a flat feature-module layout.

## Structure

```
app/
  domain/         models/ (SQLModel entities), repository/ (DB CRUD), exception/ (domain-invariant errors)
  application/    service/ (use-case orchestration), exception/ (use-case-level errors)
  api/            dto/, transformer/ (domain <-> dto), routers/, permission/ (authorization checks),
                  exception/ (HTTP handlers), util/ (endpoints.py aggregates all routers)
  infrastructure/ db/ (session, migrations), security/ (JWT, password hashing), cwl/ (CWL parsing),
                  packaging/ (moveapps-cwl-package subprocess wrapper)
  config.py, main.py
```

## Setup

```bash
cp .env.example .env   # fill in JWT_SECRET (see comment in .env.example), PACKAGING_EXECUTABLE, GITHUB_TOKEN
docker compose up -d
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8000
```

API: http://localhost:8000, interactive docs: http://localhost:8000/docs

Packaging (`POST /components/package`, `POST /components/{id}/versions/package`) shells out to the [`automated-packaging`](../automated-packaging) CLI — build it first and point `PACKAGING_EXECUTABLE` in `.env` at its executable.