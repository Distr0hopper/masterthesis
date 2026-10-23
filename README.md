# Masterthesis

Run the whole application with `make docker-up` (`docker compose up -d --build`) and open http://localhost:8080; `make docker-down` stops it. Login codes arrive in Mailhog at http://localhost:8025. The backend needs `backend-python/.env` (copy `backend-python/.env.example` and set `JWT_SECRET`). See [CLAUDE.md](./CLAUDE.md#running-locally) for the development setup with hot reload.

## Components

- [Backend](./backend-python/README.md) — FastAPI REST API for storing and managing CWL-based workflow components
- [Automated Packaging](./automated-packaging/README.md) — CLI tool that packages MoveApps R apps from GitHub as CWL descriptors
