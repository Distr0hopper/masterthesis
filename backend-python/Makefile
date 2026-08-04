.PHONY: run migrate install

run:
	uv run uvicorn app.main:app --reload --port 8000

migrate:
	uv run alembic upgrade head

install:
	uv sync