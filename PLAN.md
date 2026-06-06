# `markdown-rag` — Execution Plan

> Self-contained build plan. Inherits shared standards from the master plan.

## Goal

A small Python CLI that does **retrieval-augmented generation** over a local
folder of markdown files. Visitor runs `python rag.py ask "your question"`,
the tool retrieves the most relevant chunks from a Qdrant index and asks
Anthropic Claude to answer using them as context.

This proves the RAG line on the Upwork bio. End-to-end, runs locally, no cloud
cost. Pattern 3 — README has screenshots/GIF only, no hosted demo.

**Sells:** RAG, Vector Databases (Qdrant), Embeddings, Python, Anthropic Claude API.

## Scope (must-haves)

1. **Ingest pipeline**: chunk markdown files, embed each chunk, upsert into Qdrant.
2. **Retrieve + answer pipeline**: embed the question, query Qdrant top-k,
   build a prompt with retrieved chunks, ask Claude, stream the answer.
3. **CLI**:
   - `rag.py ingest [--dir ./corpus]` — re-builds the index
   - `rag.py ask "question"` — answers using existing index
   - `rag.py reset` — drops the collection
4. **Local Qdrant** via Docker Compose (one-command run).
5. **Sample corpus** of 8–12 markdown files about a coherent topic (e.g.
   "PostgreSQL operational notes", "TypeScript handbook excerpts" — pick
   something defensible). Real-feeling content, not lorem ipsum.
6. README with full flow diagram, ingest screenshot, ask screenshot,
   "Skills demonstrated" section.

## Out of scope

- No web UI, no API server.
- No hybrid search / re-ranking (retrieval = pure cosine similarity).
- No multi-tenant / per-user collections.
- No PDF / HTML / DOCX support — markdown only.
- No agent loop (that's `claude-agent-starter`'s job).
- No alternative vector DBs (no Pinecone, no Weaviate, no pgvector).

## Tech stack

- **Language:** Python 3.11+
- **Package manager:** `uv` (fast, modern, PEP 582-friendly) — fallback to `pip` if `uv` not available; the project ships a `requirements.txt` either way.
- **Embeddings:** `sentence-transformers` with `all-MiniLM-L6-v2` (small, free, runs on CPU)
- **Vector DB:** Qdrant via the official Python client (`qdrant-client`)
- **LLM:** `anthropic` SDK, model `claude-sonnet-4-6`
- **CLI parsing:** `typer` (clean, type-hinted)
- **Markdown parsing:** `markdown-it-py` for chunking
- **Linting:** `ruff` (lint + format)
- **Testing:** `pytest` with one smoke test
- **CI:** GitHub Actions

## File tree

```
markdown-rag/
  README.md
  PLAN.md
  LICENSE                   ← MIT
  .gitignore                ← __pycache__, .venv, .env*, qdrant_storage/
  .env.example              ← ANTHROPIC_API_KEY=
  pyproject.toml            ← uv-compatible
  requirements.txt          ← pip-compatible fallback
  ruff.toml
  docker-compose.yml        ← single Qdrant service
  Makefile                  ← make up / make ingest / make ask / make demo
  corpus/                   ← 8-12 sample .md files (one cohesive topic)
    01-intro.md
    02-…
  src/
    rag/
      __init__.py
      cli.py                ← typer app, entrypoint
      config.py             ← env, model name, collection name
      ingest.py             ← chunking + embedding + upsert
      retrieve.py           ← embed query + Qdrant search
      answer.py             ← build prompt, call Claude, stream
      chunking.py           ← markdown-aware chunker (split on headings, max ~500 tokens)
      embeddings.py         ← sentence-transformers wrapper
      vector_store.py       ← qdrant-client wrapper
  tests/
    test_chunking.py        ← unit test for the chunker
    test_smoke.py            ← end-to-end with mocked SDK + in-memory qdrant
  rag.py                    ← thin script: from rag.cli import app; app()
  .github/
    workflows/
      ci.yml
  docs/
    architecture.md         ← flow diagram (ingest + ask)
    screenshots/
      demo.gif
      ingest.png
      ask.png
```

## Step-by-step build

### 1. Bootstrap

```bash
cd <repo>
uv init                         # or: python -m venv .venv && source .venv/bin/activate
uv add anthropic qdrant-client sentence-transformers typer markdown-it-py
uv add --dev pytest ruff
```

`pyproject.toml` should pin Python `>=3.11`. Generate `requirements.txt`
alongside (`uv pip compile pyproject.toml -o requirements.txt`) so users
without `uv` can still `pip install -r requirements.txt`.

### 2. Sample corpus

Pick **one** cohesive topic. Suggested: "Practical PostgreSQL — short notes"
(your DB skill ties in, and 'postgres' is a high-volume Upwork keyword).
Eight to twelve files of 200–500 words each. Headings and prose, no code blocks
unless they're tiny. Make the content real-feeling — a curious reader should
think "hm, this is useful." Cite sources at the bottom of each file.

### 3. `chunking.py`

Use `markdown-it-py` to tokenise. Walk the token stream and emit chunks
boundaried on heading levels (default: split on H2). Each chunk carries:
- `text`
- `source_file`
- `heading_path` (e.g. `["Indexes", "B-tree"]`)

Hard cap: ~500 tokens per chunk (rough char count fine — `len(text) // 4`).
Overlap: small (1 sentence) on H2 boundaries.

Unit-test this — gives the repo a real test, not a smoke-only.

### 4. `embeddings.py`

```python
from sentence_transformers import SentenceTransformer

class Embedder:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)
        self.dim = self.model.get_sentence_embedding_dimension()

    def encode(self, texts: list[str]) -> list[list[float]]:
        return self.model.encode(texts, show_progress_bar=False).tolist()
```

Note: first run downloads ~90 MB of weights. Add to README ("first ingest takes
~30s on first run while downloading the embedding model").

### 5. `vector_store.py`

Wraps `QdrantClient`. Connects to `QDRANT_URL` (default `http://localhost:6333`).
Collection name: `markdown-rag`. Methods:
- `ensure_collection(dim: int)` — recreate if dim mismatch
- `upsert(chunks: list[Chunk])` — payload: `text`, `source_file`, `heading_path`
- `search(vector: list[float], top_k: int) → list[Chunk]`
- `reset() → None`

### 6. `ingest.py`

Walks `corpus/` (configurable via `--dir`), reads each `.md`, chunks, embeds
in batches of 32, upserts. Prints a summary table at the end.

### 7. `retrieve.py`

`retrieve(query: str, top_k: int = 5) → list[Chunk]`. Embeds the query,
searches Qdrant, returns top-k.

### 8. `answer.py`

```python
def answer(question: str, chunks: list[Chunk]) -> Iterator[str]:
    context = "\n\n".join(
        f"[{c.source_file} > {' > '.join(c.heading_path)}]\n{c.text}"
        for c in chunks
    )
    system = "You are a helpful assistant. Answer ONLY using the provided context. " \
             "If the context does not contain the answer, say so."
    user = f"Context:\n{context}\n\nQuestion: {question}"
    with anthropic_client.messages.stream(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=system,
        messages=[{"role": "user", "content": user}],
    ) as stream:
        for text in stream.text_stream:
            yield text
```

CLI prints citations (`source_file > heading_path`) at the end.

### 9. `cli.py` (typer)

Commands: `ingest`, `ask`, `reset`. Each is one short function calling the
modules above. Good `--help` text. Sensible defaults (`--dir corpus`, `--top-k 5`).

### 10. `Makefile`

```makefile
.PHONY: up down ingest ask demo lint test

up:
	docker compose up -d

down:
	docker compose down

ingest:
	python rag.py ingest

ask:
	python rag.py ask "What does an index do in PostgreSQL?"

demo: up
	@echo "Waiting for Qdrant..." && sleep 3
	$(MAKE) ingest
	$(MAKE) ask

lint:
	ruff check .
	ruff format --check .

test:
	pytest -q
```

### 11. `docker-compose.yml`

Just the Qdrant service:
```yaml
services:
  qdrant:
    image: qdrant/qdrant:latest
    ports: ["6333:6333"]
    volumes: ["./qdrant_storage:/qdrant/storage"]
```

### 12. CI

Triggers on push and PR. Steps:
- Checkout, setup Python 3.11
- Install deps via `pip install -r requirements.txt` (CI doesn't need `uv`)
- `ruff check .` + `ruff format --check .`
- `pytest -q` (smoke test mocks both Qdrant and the Anthropic SDK)

No Docker in CI to keep runtime fast.

### 13. README

1. Title — **markdown-rag** — *Local RAG over a folder of markdown files in a single command.*
2. Demo — `docs/screenshots/demo.gif` showing `make demo` from cold cache to streamed answer
3. What it shows:
   - Heading-aware chunking
   - Local embeddings (free, CPU-only)
   - Qdrant via Docker Compose
   - Anthropic Claude with citation-aware prompting
4. Skills demonstrated — RAG, Qdrant, Vector Databases, Embeddings, Python, Anthropic Claude API, Docker Compose
5. Quick start:
   ```bash
   pip install -r requirements.txt
   cp .env.example .env   # add ANTHROPIC_API_KEY
   make demo
   ```
6. How it works — flow diagram (corpus → chunker → embedder → qdrant; query → embedder → qdrant top-k → prompt → claude → stream)
7. Customisation — point at your own corpus dir
8. License — MIT

### 14. Polish + flip public

Record GIF showing `make demo` end-to-end. Confirm verification list. Set topics:
`rag`, `retrieval-augmented-generation`, `qdrant`, `vector-database`,
`embeddings`, `claude-api`, `anthropic`, `python`. Flip public.

## Verification (tick before going public)

- [ ] Fresh clone → `make up && make ingest && make ask` works on macOS and Linux
- [ ] First ingest downloads embedding model with a clear progress hint
- [ ] Demo GIF in README shows the citation block at the end of the answer
- [ ] Chunking unit test covers H2-split, max-token, and a no-headings file
- [ ] Smoke test does NOT hit real Anthropic API or real Qdrant
- [ ] `.env*` ignored, no API keys in history
- [ ] `qdrant_storage/` ignored
- [ ] CI green on Python 3.11
- [ ] Topics + description set on the repo
- [ ] At least 8 corpus files, all attributed at the bottom

## Stretch (defer to v2)

- Hybrid search (BM25 + vector) via Qdrant 1.10+ sparse vectors
- Re-ranking pass with a cross-encoder
- Web UI (Streamlit / Gradio)
- PDF ingest

Captured for future planning — do not pull into v1.
