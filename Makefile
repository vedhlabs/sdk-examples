.PHONY: install engine engine-down test lint check smoke smoke-first smoke-kyc clean-state

install:
	python -m pip install -e ".[dev,alpaca]"

engine:
	docker compose up -d

engine-down:
	docker compose down

test:
	python -m pytest

lint:
	python -m ruff check .

check: lint test

smoke:
	python scripts/smoke.py

smoke-first:
	python scripts/smoke_first_workflow.py

smoke-kyc:
	python scripts/smoke_kyc_parallel.py

clean-state:
	rm -rf .state audit.log
