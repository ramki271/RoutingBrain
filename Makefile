.PHONY: backend frontend install-backend install-frontend env up down

# Start backend dev server
backend:
	cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Start frontend dev server
frontend:
	cd frontend && npm run dev

# Install backend dependencies (Phase 1 & 2 — no DB/Redis needed yet)
install-backend:
	cd backend && pip install -e ".[dev]"

# Install frontend dependencies
install-frontend:
	cd frontend && npm install

# Copy .env.example to .env (first time setup)
env:
	cp backend/.env.example backend/.env
	@echo "Edit backend/.env and add your API keys"

# Phase 3+ only: full docker stack with postgres + redis
up:
	docker compose up --build

down:
	docker compose down
