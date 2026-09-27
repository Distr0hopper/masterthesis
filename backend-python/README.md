# backend-python

FastAPI REST API for storing and managing CWL-based workflow components. Layered (domain → application → api, outer depends on inner only), modeled on Kotlin/Spring-style architecture rather than a flat feature-module layout.

## Structure

```
app/
  domain/         models/ (SQLModel entities), repository/ (DB CRUD), exception/ (domain-invariant errors)
  application/    service/ (use-case orchestration), exception/ (use-case-level errors)
  api/            dto/, transformer/ (domain <-> dto), routers/, permission/ (authorization checks),
                  exception/ (HTTP handlers), util/ (endpoints.py aggregates all routers)
  infrastructure/ db/ (session, migrations), security/ (JWT, OTP-code hashing),
                  email/ (EmailSender abstraction: SMTP for local dev, Resend for production),
                  cwl/ (CWL parsing), packaging/ (HTTP client for the packaging service)
  config.py, main.py
```

## Setup

```bash
cp .env.example .env   # fill in JWT_SECRET (see comment in .env.example)
docker compose up -d   # postgres + mailhog
(cd .. && docker compose up -d packaging-service)   # packaging service on :8002
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8000
```

API: http://localhost:8000, interactive docs: http://localhost:8000/docs

Packaging (`POST /components/package`, `POST /components/{id}/commands` with `REPACKAGE`) calls the [`automated-packaging`](../automated-packaging) service over HTTP (`PACKAGING_SERVICE_URL`). It runs as a container from the repo-root `docker-compose.yml`; put an optional `GITHUB_TOKEN` in the repo-root `.env` (see `../.env.example`) to avoid GitHub rate limits. If the service is down, packaging requests return 503.

## Authentication (OTP email login)

No passwords are stored. Login works by emailing a 6-digit one-time code:

- `POST /auth/otp/request {email}` — generates a code, emails it, 204 either way (doesn't
  leak whether the email is already registered)
- `POST /auth/otp/verify {email, code}` — verifies the code and returns a JWT. A brand-new
  email is auto-provisioned (bare user, no name/affiliation) on first successful verify —
  fill those in afterward via `PATCH /users/me`.

Codes expire after `OTP_EXPIRES_IN` seconds (default 600), allow `OTP_MAX_ATTEMPTS` wrong
guesses (default 5) before being locked out, and are rate-limited to one request per
`OTP_REQUEST_COOLDOWN` seconds (default 60) per email — all configurable in `.env`.

**Local dev**: `EMAIL_PROVIDER=smtp` (the `.env.example` default) sends mail via Mailhog,
started by `docker compose up -d`. Read the codes at http://localhost:8025 — no real inbox
needed.

**Production**: set `EMAIL_PROVIDER=resend` plus `RESEND_API_KEY`/`RESEND_FROM_EMAIL` to send
through [Resend](https://resend.com) instead.