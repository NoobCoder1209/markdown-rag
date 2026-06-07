.PHONY: up down wait ingest ask reset demo lint test install

Q ?= How do I lock down a namespace so pods can only talk to each other on explicit ports?

install:
	pip install -r requirements.txt

up:
	docker compose up -d

down:
	docker compose down

wait:
	python rag.py wait

ingest:
	python rag.py ingest

ask:
	python rag.py ask "$(Q)"

reset:
	python rag.py reset

demo: up wait
	@$(MAKE) ingest
	@$(MAKE) ask

lint:
	ruff check .
	ruff format --check .

test:
	pytest -q
