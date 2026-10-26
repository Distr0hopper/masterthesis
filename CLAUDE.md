# CLAUDE.md

Master's thesis mono-repo: a **Component Repository** for CWL-based workflow components (MoveApps R apps packaged as CWL tools, composed into workflows).

| Directory              | What it is                                                                 | Stack                                              |
| ---------------------- | -------------------------------------------------------------------------- | -------------------------------------------------- |
| `backend-python/`      | REST API: components, tools, workflows, auth, builder drafts               | FastAPI, SQLModel, Alembic, Postgres, `uv`         |
| `frontend/`            | Web UI: browse/upload components, workflow builder, "My Components"         | React 19, Vite, TS, TanStack Query, zod, shadcn/Tailwind, React Flow |
| `automated-packaging/` | CLI + HTTP service that packages a MoveApps GitHub repo into a CWL tool     | Python, FastAPI, Docker (R wrapper image)          |
| `docs/masterarbeit/`   | Thesis text                                                                 |                                                    |
| `openapi.json`         | Checked-in API spec, generated from the backend (`make openapi`)            |                                                    |

Each sub-project has its own README with more detail; `backend-python/docs/` holds the domain model and port-compatibility docs.

## Running locally

One `docker-compose.yml` in the repo root holds every container. The backend reads its settings from `backend-python/.env` (copy `.env.example`, set `JWT_SECRET`).

```bash
# the whole app: http://localhost:8080 (nginx serves the SPA and proxies /api/ to the backend)
make docker-up        # docker compose up -d --build; `make docker-down` stops it, `make docker-logs s=backend` follows logs
```

For development with hot reload, start only the infrastructure and run backend and frontend locally:

```bash
# repo root: Postgres :5433, Mailhog :1025 / UI :8025 (login codes land there),
# format service :8001, packaging service :8002 (optional GITHUB_TOKEN in ./.env)
make docker-infra     # docker compose up -d postgres mailhog packaging-service format-service

cd backend-python && make install && make migrate && make run   # API on :8000, docs at /docs
cd frontend && npm install && npm run dev                       # :5173, needs VITE_API_BASE_URL=http://localhost:8000 in .env
```

The `backend` container also binds `:8000`, so stop it (`docker compose stop backend`) before `make run`.

The backend calls the SOS File Format Service on `:8001` (`FORMAT_SERVICE_URL`) to resolve parameter format labels and check port compatibility. Formats come from the SOS EO formats ontology (`$schemas: https://dfg-sos.github.io/ontologies/eo-formats.owl`, `eo: https://dfg-sos.github.io/ontologies/eo-formats#`), which the service fetches itself. Packaging returns 503 if the packaging service is down.

## Commands

| Where                  | Test                                | Other                                                       |
| ---------------------- | ----------------------------------- | ----------------------------------------------------------- |
| `backend-python/`      | `make test` (`uv run pytest`); the DB tests need `make docker-infra`, recreate their own `component_repository_test` DB and are skipped without Postgres | `make openapi` — regenerate `../openapi.json`; run after changing any DTO or route |
| `frontend/`            | `npm test` (vitest); `npm run e2e` (Playwright, needs `make docker-infra`: starts its own backend :8100 on a fresh `component_repository_e2e` DB and Vite :5180) | `npm run lint` (oxlint), `npm run build` (`tsc -b` + vite)  |
| `automated-packaging/` | `pip install -e ".[service,dev]" && pytest` | `bash build-sdk.sh` builds the shared R wrapper image |

## Backend architecture (`backend-python/app/`)

Kotlin/Spring-style layers with strict inward dependencies: `api` → `application` → `domain`; `infrastructure` holds adapters (DB, JWT, email, CWL parsing, packaging + format-service HTTP clients).

- **domain/**: SQLModel entities (`models/`), repositories (`repository/`), domain-invariant exceptions, `composite/` (tree operations, `lifecycle.py`), `compatibility/` (port matching).
- **application/**: use-case services, application exceptions, `commands/` (command registry), `unit_of_work.py`.
- **api/**: DTOs (camelCase via `CamelModel`), transformers (explicit domain ↔ DTO functions, no `model_validate(orm_obj)`), routers, `permission/` validators, `link/` (HATEOAS link builders), exception handlers.
- **jobs/**: scheduled entry points (`python -m app.jobs.<name>`), the scheduler's counterpart to a router: one call into an application service, exit code 0/1. `purge_login_codes` runs hourly via the `login-code-purge` compose service (see `docs/deployment.md`).

Conventions:

- **Unit of Work:** repositories never commit. Only router-facing service methods open `async with self.uow:` and commit once. Nesting units, writing outside a unit, or exiting a unit with uncommitted writes all raise. A shared writer that another service calls gets a public name; `_` prefixes are for helpers used inside one class only. No HTTP call inside a unit: format labels are fetched before it opens (`ToolsService.prepare`, `ComponentsService.read_ports`).
- **Authorization is in the router.** The router fetches the entity, checks the permission validator, then passes the already-fetched entity to the service. Services take no `user_id` for auth.
- **Commands + HATEOAS:** state-changing actions (publish, deprecate, repackage, …) are declared once in a command registry. Dispatch, permission checks and the response `links` all loop over that registry, so adding a command means one enum member plus one registry entry. The frontend decides which actions to show by looking at the link rels.
  - `allowed` answers *who* may run a command (refused: 403). `available` answers whether it applies to the component's current state (e.g. unpublish window, superseded); it only hides the link, and the service refuses with its own 409 that says why.
- **Exceptions:** business rules raise custom domain/application exceptions, and `api/exception/handlers.py` maps them to HTTP. Don't raise `HTTPException` from services. Infrastructure code raises stdlib exceptions. Unexpected failures are left uncaught so they surface as a 500.
- **FastAPI parameters:** always use `Annotated[T, Depends()/Query()/Form()]`. Multipart endpoints take one DTO: `Annotated[Dto, Form(media_type="multipart/form-data")]`, never one parameter per field.
- **DI:** each repository/service has its own `get_*` staticmethod factory. There is no central `dependencies.py`.
- **Migrations** are hand-written, never `--autogenerate`. The dev DB contains real data, so never drop tables. Take a `pg_dump` to `backend-python/tmp/db-snapshots/` before touching the schema. Create the file with `uv run alembic revision -m "..."`, so it gets the date-prefixed name (`YYYY_MM_DD_HHMM-<rev>_<slug>.py`, `file_template` in `alembic.ini`) that lists the versions in the order they run.

### Domain model

- **Component composite** (modelled on CWL `Process`): `components` is the shared base table (name+version lineage, CWL, ports, domains, files, status), discriminated by `kind`. `tools` and `workflows` are 1:1 detail rows. This uses composition because SQLModel can't map table inheritance. A `workflow_steps` row is an edge, and its child can be a tool or a nested workflow.
  - `/components` handles the shared operations polymorphically; `/tools` and `/workflows` handle only what is specific to one kind.
  - Load trees through `ComponentsRepository.find_by_id` / `load_tree`. Lazy access on the recursive path raises `MissingGreenlet`.
  - Loaded `kind`/`status` values are plain `str`: wrap them as `ComponentKind(...)` and never call `.value` on them.
- **Status lifecycle** (DRAFT / PUBLISHED / DEPRECATED): only `domain/composite/lifecycle.py` writes status or step matches, through its transition tables.
  - `PUBLIC_STATUSES` = {PUBLISHED, DEPRECATED} controls who can read a component. `LISTED_STATUSES` = {PUBLISHED} controls browse and search.
  - Check for drafts with `== DRAFT`, never `!= PUBLISHED`.
  - A published version can be unpublished (back to a normal draft) only within `UNPUBLISH_WINDOW_SECONDS` (default 24h) after `first_published_at`; after that it is only ever deprecated. Only drafts can be deleted. A public version's content never changes: changes go into a new version. Publishing vN supersedes (deprecates) the older published versions.
- **Auth:** passwordless. An email OTP is exchanged for a JWT with a sliding refresh, and new emails are auto-provisioned.

## Frontend (`frontend/src/`)

- `api/<feature>/` has `service.ts` (axios calls), `queries.ts` (TanStack Query hooks), `types.ts`, `schema.ts` (zod) and `transformer.ts`. Shared parts are `api/client.ts` (JWT interceptor; repeated-key array params for FastAPI) and `useCommandMutation.ts`.
- `pages/` holds route components and `components/<feature>/` holds feature UI. `components/ui/` contains the shadcn primitives.
- `store/auth.store.ts` is a zustand store. `lib/` holds helpers. Import paths use the `@/` alias for `src/`.
- Components are polymorphic here too. Keep the frontend types in sync with `openapi.json` when the backend changes.
