# `markdown-rag` — Execution Plan

## How to use this plan

You are the build session for this repo. Read this whole file before doing anything else, then start executing immediately — no kickoff prompt needed.

**Working agreement:**

1. **Start without waiting.** Read this file end-to-end, then begin Phase 1 in the *Subagent playbook* section below.
2. **Always ask the user about business decisions and business logic.** Corpus topic, copy, screenshot framing, brand voice. The "Business decisions to ask the user about" section below lists the open questions for this repo.
3. **Ask the user when you are genuinely blocked.**
4. **Do not ask the user about engineering details.** Library choice, file structure, function naming — make the call yourself.
5. **Use subagents aggressively.** Default to the playbook below. Multiple subagents in a single message whenever they're independent.
6. **TaskCreate / TaskUpdate everything.**
7. **Pattern 3 only.** No live deployed demo. README ships GIF/screenshots; user supplies their own key locally. Never commit a key.
8. **Follow the master plan's shared standards.** MIT, README structure, CI baseline, GitHub topics, repo stays private until verification passes.
9. **All `Agent` tool calls must pass `model: "opus"`.**
10. **Off-limits forever:** SAP-internal sources, `~/.claude/` material, RCA/runbook content.

## Subagent playbook (this repo)

Higher parallelism than the agent starter — RAG has more moving parts (chunking, embeddings, vector DB, prompt). Aim for 3–4 subagents per phase.

**Phase 1 — Research (parallel, single message):**
- `Explore` (Opus): "Find the canonical `qdrant-client` Python usage for create-collection + upsert + search with payload, against Qdrant local Docker. Return ≤80-line skeleton."
- `Explore` (Opus): "Find best-practice markdown chunking strategies for RAG that respect heading boundaries, with overlap. Return decision factors + a small Python sketch."
- `Explore` (Opus): "Find the recommended `sentence-transformers` model for English semantic search at small scale (CPU). Return model name, dim, license, latency."
- `Explore` (Opus): "Find the canonical Anthropic Python SDK streaming + system-prompt + citation-style answer pattern. Return a 60-line skeleton."

**Phase 2 — Design (single agent):**
- `Plan` (Opus): "Given the research above and this PLAN.md, propose the exact file tree, Makefile targets, and a 6-step build order. Return as a checklist."

**Phase 3 — Build:** main session writes the code. Dispatch `Explore` on demand for specific Qdrant / sentence-transformers / Anthropic API questions.

**Phase 4 — Review (parallel):**
- `code-reviewer` (Opus): "Review for chunking correctness, embedding dim handling, idempotent re-ingest, prompt construction, citation accuracy, README accuracy. High effort."
- `tester` (Opus): "Write unit tests for the chunker (H2 split, max-token, no-headings file) and a smoke test that mocks Qdrant + Anthropic SDK end-to-end."

**Phase 5 — Polish:** main session captures GIF of `make demo`, applies review feedback, ticks verification, asks user before flipping public.

---

## Goal

A small Python CLI that does **retrieval-augmented generation** over a local
folder of markdown files. Visitor runs `python rag.py ask "your question"`,
the tool retrieves the most relevant chunks from a Qdrant index and asks
Anthropic Claude to answer using them as context.

This proves the RAG line on the Upwork bio. End-to-end, runs locally, no cloud
cost. Pattern 3 — README has screenshots/GIF only, no hosted demo.

**Sells:** RAG, Vector Databases (Qdrant), Embeddings, Python, Anthropic Claude API.

## Business decisions to ask the user about

- **Sample corpus topic** — recommend "Practical PostgreSQL — short notes" (DB skill ties in, "postgres" is a high-volume Upwork keyword), but the user may prefer Kubernetes notes, Helm tips, or something else aligned to their brand.
- **Number of files in corpus** (8 vs 10 vs 12) — recommend 10.
- **Demo question used in README + GIF** — should be one whose answer is genuinely in the corpus and shows multi-chunk retrieval.
- **Whether to show citations inline in the streamed answer** or only at the end — recommend "at the end" for cleaner UX.

## Scope (must-haves)

1. **Ingest pipeline**: chunk markdown files, embed each chunk, upsert into Qdrant.
2. **Retrieve + answer pipeline**: embed the question, query Qdrant top-k, build a prompt with retrieved chunks, ask Claude, stream the answer.
3. **CLI**:
   - `rag.py ingest [--dir ./corpus]` — re-builds the index
   - `rag.py ask "question"` — answers using existing index
   - `rag.py reset` — drops the collection
4. **Local Qdrant** via Docker Compose (one-command run).
5. **Sample corpus** of 8–12 markdown files on a coherent topic.
6. README with full flow diagram, ingest screenshot, ask screenshot, "Skills demonstrated" section.

## Out of scope

- No web UI, no API server.
- No hybrid search / re-ranking (retrieval = pure cosine similarity).
- No multi-tenant / per-user collections.
- No PDF / HTML / DOCX support — markdown only.
- No agent loop (that's `claude-agent-starter`'s job).
- No alternative vector DBs (no Pinecone, no Weaviate, no pgvector).

## Tech stack

- **Language:** Python 3.11+
- **Package manager:** `uv` with `requirements.txt` fallback
- **Embeddings:** `sentence-transformers` with `all-MiniLM-L6-v2`
- **Vector DB:** Qdrant via `qdrant-client`
- **LLM:** `anthropic` SDK, model `claude-sonnet-4-6`
- **CLI parsing:** `typer`
- **Markdown parsing:** `markdown-it-py`
- **Linting:** `ruff`
- **Testing:** `pytest`
- **CI:** GitHub Actions

## File tree

```
markdown-rag/
  README.md
  PLAN.md
  LICENSE                   ← MIT
  .gitignore                ← __pycache__, .venv, .env*, qdrant_storage/
  .env.example              ← ANTHROPIC_API_KEY=
  pyproject.toml
  requirements.txt
  ruff.toml
  docker-compose.yml        ← single Qdrant service
  Makefile                  ← make up / make ingest / make ask / make demo
  corpus/                   ← 8-12 sample .md files
  src/
    rag/
      __init__.py
      cli.py                ← typer app
      config.py
      ingest.py             ← chunking + embedding + upsert
      retrieve.py           ← embed query + Qdrant search
      answer.py             ← build prompt, call Claude, stream
      chunking.py           ← markdown-aware chunker
      embeddings.py
      vector_store.py
  tests/
    test_chunking.py
    test_smoke.py
  rag.py                    ← thin entrypoint
  .github/workflows/ci.yml
  docs/
    architecture.md
    screenshots/
      demo.gif
      ingest.png
      ask.png
```

## Step-by-step build

### 1. Bootstrap

```bash
uv init
uv add anthropic qdrant-client sentence-transformers typer markdown-it-py
uv add --dev pytest ruff
uv pip compile pyproject.toml -o requirements.txt
```

Pin Python `>=3.11` in `pyproject.toml`.

### 2. Sample corpus

Topic decided with user. 8–12 files, 200–500 words each, headings + prose.
Cite sources at the bottom of each file.

### 3. `chunking.py`

Walk `markdown-it-py` token stream, emit chunks bounded on H2. Each chunk:
`text`, `source_file`, `heading_path`. Cap ~500 tokens. 1-sentence overlap on
H2 boundaries. Unit-test this.

### 4. `embeddings.py`

```python
class Embedder:
    def __init__(self, model_name="all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)
        self.dim = self.model.get_sentence_embedding_dimension()
    def encode(self, texts):
        return self.model.encode(texts, show_progress_bar=False).tolist()
```

README note: first run downloads ~90 MB.

### 5. `vector_store.py`

`QdrantClient`, `QDRANT_URL` default `http://localhost:6333`, collection
`markdown-rag`. Methods: `ensure_collection(dim)`, `upsert(chunks)`,
`search(vector, top_k) -> list[Chunk]`, `reset()`.

### 6. `ingest.py`

Walks `corpus/`, reads `.md`, chunks, embeds in batches of 32, upserts.
Print summary table.

### 7. `retrieve.py`

`retrieve(query, top_k=5) -> list[Chunk]`.

### 8. `answer.py`

Build context (`[file > heading]\nbody`), system prompt: "Answer ONLY using
provided context. If not found, say so." Stream from Claude. Print citations
at end (or per business decision).

### 9. `cli.py` (typer)

`ingest`, `ask`, `reset`. Good `--help`. Defaults: `--dir corpus`, `--top-k 5`.

### 10. Makefile

```makefile
.PHONY: up down ingest ask demo lint test
up:    ; docker compose up -d
down:  ; docker compose down
ingest:; python rag.py ingest
ask:   ; python rag.py ask "What does an index do in PostgreSQL?"
demo: up
	@sleep 3 && $(MAKE) ingest && $(MAKE) ask
lint:  ; ruff check . && ruff format --check .
test:  ; pytest -q
```

### 11. `docker-compose.yml`

```yaml
services:
  qdrant:
    image: qdrant/qdrant:latest
    ports: ["6333:6333"]
    volumes: ["./qdrant_storage:/qdrant/storage"]
```

### 12. CI

Setup Python 3.11; `pip install -r requirements.txt`; `ruff check .` +
`ruff format --check .`; `pytest -q`. No Docker in CI.

### 13. README

1. Title — *markdown-rag — Local RAG over a folder of markdown in one command*
2. Demo — `docs/screenshots/demo.gif` of `make demo`
3. What it shows
4. Skills demonstrated — RAG, Qdrant, Vector Databases, Embeddings, Python, Anthropic Claude API, Docker Compose
5. Quick start: `pip install -r requirements.txt && cp .env.example .env && make demo`
6. How it works (flow diagram)
7. Customisation — point at your own corpus dir
8. License — MIT

### 14. Polish + flip public

GIF of `make demo`. Topics: `rag`, `retrieval-augmented-generation`, `qdrant`,
`vector-database`, `embeddings`, `claude-api`, `anthropic`, `python`. Ask user
before flipping public.

## Verification

- [ ] Fresh clone → `make up && make ingest && make ask` works on macOS and Linux
- [ ] First ingest downloads embedding model with progress hint
- [ ] Demo GIF shows citation block at the end
- [ ] Chunking unit test covers H2-split, max-token, no-headings file
- [ ] Smoke test does NOT hit real Anthropic API or real Qdrant
- [ ] `.env*` ignored, no API keys in history
- [ ] `qdrant_storage/` ignored
- [ ] CI green on Python 3.11
- [ ] Topics + description set
- [ ] At least 8 corpus files, all attributed

## Stretch (defer)

- Hybrid search (BM25 + vector)
- Re-ranking pass with cross-encoder
- Streamlit / Gradio UI
- PDF ingest
