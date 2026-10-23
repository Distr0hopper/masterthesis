.PHONY: docker-up docker-down docker-infra docker-logs

# the whole app (rebuilds changed images): http://localhost:8080, login codes at http://localhost:8025
docker-up:
	docker compose up -d --build

# stops and removes every container - the database volume stays
docker-down:
	docker compose down

# only what local development needs - then `make run` in backend-python/ and `npm run dev` in frontend/
docker-infra:
	docker compose up -d postgres mailhog packaging-service format-service

# follow the logs of every container, or one: `make docker-logs s=backend`
docker-logs:
	docker compose logs -f $(s)
