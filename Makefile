SHELL := /bin/sh

.PHONY: install-web install-api seed-demo prepare-demo start-demo dev dev-web dev-api test check smoke-demo smoke-live web-typecheck web-test-e2e web-test-e2e-headed package package-release package-submission

install-web:
	cd apps/web && npm install

install-api:
	cd apps/api && python -m pip install -e ".[dev]"

seed-demo:
	python scripts/generate_demo_data.py

prepare-demo:
	powershell -ExecutionPolicy Bypass -File scripts/prepare_demo.ps1

start-demo:
	powershell -ExecutionPolicy Bypass -File scripts/start_demo.ps1

web-dev:
	cd apps/web && npm run dev

dev:
	docker compose up --build

dev-web:
	cd apps/web && npm run dev

api-dev:
	cd apps/api && python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev-api:
	cd apps/api && python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

test:
	cd apps/api && pytest
	cd apps/web && npm run typecheck

check:
	python scripts/run_checks.py

smoke-demo:
	python scripts/run_smoke.py demo

smoke-live:
	python scripts/run_smoke.py live

web-typecheck:
	cd apps/web && npm run typecheck

web-test-e2e:
	cd apps/web && npm run test:e2e

web-test-e2e-headed:
	cd apps/web && npm run test:e2e:headed

package:
	python scripts/package_release.py

package-release:
	python scripts/package_release.py

package-submission:
	python scripts/package_submission.py
