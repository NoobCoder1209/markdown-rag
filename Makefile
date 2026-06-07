.PHONY: up down wait ingest ask reset demo lint test install

Q ?= How do I lock down a namespace so pods can only talk to each other on explicit ports?

install:
	pip install -r requirements.txt

up:
	docker compose up -d

down:
	docker compose down

wait:
	python -m rag.cli wait

ingest:
	python -m rag.cli ingest

ask:
	python -m rag.cli ask "$(Q)"

reset:
	python -m rag.cli reset

demo: up wait
	@$(MAKE) ingest
	@$(MAKE) ask

lint:
	ruff check .
	ruff format --check .

test:
	pytest -q
