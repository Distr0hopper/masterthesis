# backend-python

FastAPI port of `backend/` (NestJS). Currently covers `auth` + `users`; `components`/`domains` not yet ported.

Own Postgres instance, independent from `backend/`'s DB (port 5433 vs 5432).

## Structure

Layered (domain → application → api, outer depends on inner only):

```
app/
  domain/       models/ (SQLModel entities), repository/ (DB CRUD), exception/ (domain-invariant errors)
  application/  service/ (use-case orchestration), exception/ (use-case-level errors)
  api/          dto/, transformer/ (domain -> dto), routers/, exception/ (HTTP handlers), util/ (DI wiring + endpoints.py)
  config.py, database.py, main.py
```

## Setup

```bash
cp .env.example .env   # fill in JWT_SECRET, e.g.: python3 -c "import secrets; print(secrets.token_hex(64))"
docker compose up -d
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8000
```

API: http://localhost:8000, interactive docs: http://localhost:8000/docs
