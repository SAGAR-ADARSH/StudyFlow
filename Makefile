.PHONY: up down logs test api web setup-db

up:
	docker compose up --build

down:
	docker compose down

logs:
	docker compose logs -f

api:
	cd apps/api && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

web:
	cd apps/web && npm run dev

test:
	PYTHONPATH=apps/api pytest apps/api/tests -v
