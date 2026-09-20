.PHONY: run migrate install openapi

run:
	uv run uvicorn app.main:app --reload --port 8000

migrate:
	uv run alembic upgrade head

install:
	uv sync

# regenerates the checked-in spec from the live app - run after changing any DTO or route
openapi:
	uv run python -c "import json; from app.main import app; json.dump(app.openapi(), open('openapi.json', 'w'))"
