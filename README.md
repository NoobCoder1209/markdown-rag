# markdown-rag

Local retrieval-augmented generation over a folder of markdown files —
in one command. Qdrant for vector storage, sentence-transformers for
embeddings, Anthropic Claude for the answer.

```
$ make demo
[ingests 12 markdown files into a local Qdrant]
[asks: "How do I lock down a namespace so pods can only talk to each other on explicit ports?"]
[Claude streams an answer grounded in your notes]

Sources:
- 10-network-policies.md > A default-deny baseline
- 10-network-policies.md > Allowing specific flows
- 06-services-and-endpoints.md > How selectors map to endpoints
```

## What it shows

- **Markdown-aware chunking** that respects heading boundaries and keeps
  fenced code blocks atomic.
- **Vector search with Qdrant** — idempotent ensure-collection, payload
  index for fast metadata filtering, batched upsert with stable UUIDs.
- **Strict-grounding prompt** — Claude answers only from retrieved context
  and says so when the answer isn't in the notes.
- **Streaming answer + post-stream citation footer** so the user always
  sees which files the answer came from.
- **Production hygiene** — friendly errors, exponential-backoff readiness
  probe, no tracebacks at the CLI surface, no secrets in git history.

## Skills demonstrated

RAG · Vector Databases (Qdrant) · Embeddings (sentence-transformers,
BGE) · Python · Anthropic Claude API · Docker Compose · Typer CLI ·
GitHub Actions CI

## Quick start

You need Docker, Python ≥ 3.11, and an Anthropic API key.

```bash
git clone <this repo>
cd markdown-rag
cp .env.example .env
# put your Anthropic API key in .env, e.g.:
#   ANTHROPIC_API_KEY=sk-ant-...

pip install -r requirements.txt
make demo
```

`make demo` brings up Qdrant in Docker, waits for it to be ready, ingests
the sample corpus (12 Kubernetes ops notes), and asks the demo question.
First run downloads the embedding model (~130 MB) into the Hugging Face
cache.

You can also run the steps individually:

```bash
make up          # docker compose up -d (qdrant)
make wait        # block until qdrant answers
make ingest      # chunk + embed + upsert the corpus
make ask Q="What is the difference between a readiness and liveness probe?"
make reset       # drop the collection
make down        # docker compose down
```

## How it works

```
   ┌────────────┐    ┌─────────────────┐    ┌──────────────────┐    ┌────────┐
   │ corpus/*.md│───▶│  chunk on H2    │───▶│ embed (BGE-small)│───▶│ Qdrant │
   └────────────┘    │  keep code      │    │  384-dim, cosine │    │        │
                     │  atomic         │    └──────────────────┘    └────────┘
                     └─────────────────┘                                 ▲
                                                                         │
   ┌────────────┐    ┌─────────────────┐    ┌──────────────────┐         │
   │  question  │───▶│  embed query    │───▶│  top-k search    │─────────┘
   └────────────┘    └─────────────────┘    └──────────────────┘
                                                     │
                                                     ▼
                                          ┌──────────────────┐
                                          │ Claude messages. │
                                          │ stream(...)      │
                                          │  + Sources footer│
                                          └──────────────────┘
```

**Chunking** (`src/rag/chunking.py`) walks the `markdown-it-py` token
stream, splits each file on H2 headings (or H1 if a file has no H2),
preserves the heading path as metadata, keeps fenced code blocks
atomic, and applies a soft size cap with one-sentence overlap on
size-driven splits.

**Embeddings** (`src/rag/embeddings.py`) use `BAAI/bge-small-en-v1.5`
— MIT-licensed, 384-dim, retrieval-trained. Qdrant's `Distance.COSINE`
normalizes server-side, so the client just hands over the raw vectors.

**Vector store** (`src/rag/vector_store.py`) wraps `qdrant-client`'s
sync API. `ensure_collection` is idempotent. A keyword payload index on
`source_file` is created at first ingest so `filter by file` queries are
fast — even though the demo doesn't use it, the design choice is there
for when the corpus grows. The connection probe uses exponential
backoff so `make demo` survives Docker startup latency without a
hard-coded `sleep`.

**Stable chunk IDs** are deterministic UUIDv5s of
`(source_file, heading_path, chunk_index)`. To stay in sync with edits,
ingest deletes all points for each file before re-upserting it — so
adding or removing a section never leaves orphan vectors behind.

**Answer** (`src/rag/answer.py`) builds a context block delimited by
distinctive `<<<RAG_CONTEXT_BEGIN>>>` / `<<<RAG_CONTEXT_END>>>` markers so
corpus content can't accidentally close the boundary. Each excerpt is
tagged `[file > heading]`. Claude receives a strict-grounding system
prompt, streams the response token-by-token, and we then print a deduped
`Sources:` footer.

## Customisation

Point the CLI at your own folder of markdown:

```bash
python rag.py ingest --dir ~/notes/k8s
python rag.py ask "what does that thing do again" --top-k 8
```

Override defaults with env vars (see `src/rag/config.py`):

| Env var | Default | What it does |
| --- | --- | --- |
| `ANTHROPIC_API_KEY` | (required) | Anthropic API key |
| `QDRANT_URL` | `http://localhost:6333` | Qdrant endpoint |
| `RAG_COLLECTION` | `markdown-rag` | Qdrant collection name |
| `RAG_EMBED_MODEL` | `BAAI/bge-small-en-v1.5` | Sentence-transformers model |
| `RAG_ANTHROPIC_MODEL` | `claude-sonnet-4-6` | Claude model |
| `RAG_TOP_K` | `5` | Chunks retrieved per question |
| `RAG_CORPUS_DIR` | `<repo>/corpus` | Where ingest reads markdown from |
| `RAG_NAMESPACE` | (fixed UUID) | UUIDv5 namespace for chunk IDs |

## Development

```bash
pip install -r requirements.txt
pip install pytest ruff
pytest -q
ruff check . && ruff format --check .
```

CI runs ruff + pytest on every PR (`.github/workflows/ci.yml`). The
smoke test mocks Qdrant and Anthropic — no network, no Docker required
in CI.

## License

MIT
