.PHONY: install install-backend install-frontend dev backend frontend build clean

install: install-backend install-frontend

install-backend:
	cd backend && python3 -m venv .venv && .venv/bin/pip install -q -e .

install-frontend:
	cd frontend && npm install

dev:
	@make -j2 backend frontend

backend:
	cd backend && .venv/bin/python serve.py

frontend:
	cd frontend && npm run dev

build:
	cd frontend && npm run build

clean:
	rm -rf backend/.venv backend/__pycache__ backend/src/__pycache__ backend/*.egg-info
	rm -rf frontend/.next frontend/node_modules
