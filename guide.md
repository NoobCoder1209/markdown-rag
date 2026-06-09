# Guide

This is the "I have never touched this repo, walk me through it" document.
For the user-facing pitch, see [`README.md`](./README.md). For the build
plan that produced this repo, see [`PLAN.md`](./PLAN.md).

> **Last verified:** 2026-06-09 on `feature/guide-and-demo-verification`.
> On macOS (Apple Silicon, Docker Desktop 29.5.2, Python 3.11.15 in
> `.venv`), I ran `make up && make wait && make ingest` end-to-end.
> Result: `points=68 dim=384 distance=Cosine status=green` with the
> `source_file` keyword payload index populated for all 68 points. The
> live `make ask` step needs an Anthropic API key and was **not** run
> by the build session — see "Demo verification status" below.

---

## 1. How to run the demo end-to-end

### Prerequisites

You need three things on the machine before any command below runs:

1. **Python 3.11 or newer.** Check with `python3 --version`. If you do
   not have it, the easiest path on macOS is `brew install python@3.11`
   or use [`uv`](https://docs.astral.sh/uv/) (`brew install uv`) which
   can install Python for you.
2. **Docker, with the daemon running.** Check with `docker info` — you
   should see a `Server: ...` block. If you only see a `Client: ...`
   block, start Docker Desktop / colima / OrbStack and try again.
3. **An Anthropic API key.** Get one at
   <https://console.anthropic.com/>. The free tier is enough for the
   demo (one streamed answer is well under one cent).

### One-time setup

Run these once after cloning. They install the Python dependencies and
plant your API key in a gitignored file.

```bash
git clone https://github.com/NoobCoder1209/markdown-rag.git
cd markdown-rag

# create a virtualenv and install everything
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# put your Anthropic key in .env (gitignored — never committed)
cp .env.example .env
$EDITOR .env       # set ANTHROPIC_API_KEY=sk-ant-...
```

### The demo (one command)

After setup, the whole demo is one Make target — but **load your `.env`
into the shell first** or the `ask` step at the end will fail after
ingest already ran:

```bash
set -a; source .env; set +a   # exports ANTHROPIC_API_KEY into this shell
make demo
```

That target runs four steps in order, each of which you can also run
individually:

| Step | Command | What happens |
| --- | --- | --- |
| 1 | `make up` | `docker compose up -d` — starts Qdrant on `localhost:6333`. |
| 2 | `make wait` | Polls Qdrant until it answers (exponential backoff, max ~63 s). |
| 3 | `make ingest` | First run: downloads the `bge-small-en-v1.5` model (~130 MB). Then chunks, embeds, and upserts the 12-file corpus into Qdrant (~10–15 s on M-series, longer on x86). |
| 4 | `make ask` | Sends the demo question to Claude with the top-5 retrieved chunks as context, streams the answer to your terminal, then prints a `Sources:` footer. |

Pass your own question with `Q=...`:

```bash
make ask Q="My pod is in CrashLoopBackOff with exit code 137. What does that mean?"
```

When you are done, shut Qdrant down with `make down`.

---

## 2. What every meaningful directory and file does

```
markdown-rag/
├── README.md               # User-facing pitch: skills, quick start, flow diagram.
├── PLAN.md                 # Original execution plan — historical / reference.
├── guide.md                # ← you are reading this.
├── LICENSE                 # MIT.
├── .env.example            # Template for your local .env (key=value pairs).
├── .gitignore              # Ignores .venv, .env, qdrant_storage, caches.
├── pyproject.toml          # Project metadata + pytest + setuptools config.
├── requirements.txt        # Pinned, uv-compiled dependency list.
├── ruff.toml               # Lint + format rules.
├── docker-compose.yml      # Single Qdrant service pinned to v1.18.1.
├── Makefile                # The user-facing entrypoints (up/down/wait/ingest/ask/reset/demo/lint/test).
├── rag.py                  # Thin entrypoint: `python rag.py <command>` → src/rag/cli.py.
│
├── corpus/                 # 12 Kubernetes operations notes, ~250–450 words each.
│                           # All sources are attributed at the bottom of each file.
│
├── src/rag/                # The actual package. Imported by the entrypoint.
│   ├── config.py           # Env-var reading, defaults, the friendly `die()` helper.
│   ├── chunking.py         # Markdown-it-py token walker. Splits on H2 (fallback H1),
│   │                       #   keeps fenced code atomic, strips frontmatter.
│   ├── embeddings.py       # `Embedder` wrapping sentence-transformers (BGE-small).
│   ├── vector_store.py     # Qdrant client wrapper. Idempotent ensure-collection,
│   │                       #   exponential-backoff readiness probe, query_points,
│   │                       #   delete-by-source-file (used by ingest).
│   ├── ingest.py           # Walks corpus, chunks each file, embeds in batches,
│   │                       #   deletes prior points for that file, upserts new ones.
│   │                       #   Stable UUIDv5 chunk IDs so re-ingest is idempotent.
│   ├── retrieve.py         # Embed query → query_points → list[ScoredChunk].
│   ├── answer.py           # Builds the strict-grounding prompt, streams Claude's
│   │                       #   reply, prints a deduped `Sources:` footer.
│   └── cli.py              # Typer app. The four subcommands: ingest, ask, reset, wait.
│
├── tests/                  # 59 unit + smoke tests. Run with `make test` or `pytest -q`.
│   ├── test_chunking.py    # H1/H2/no-headings/frontmatter/code-fence/oversize edge cases.
│   ├── test_vector_store.py# Mocked retry loop, dim mismatch, batched upsert, reset, etc.
│   ├── test_ingest.py      # UUIDv5 stability, walk-corpus, batching, delete-then-upsert.
│   ├── test_answer.py      # Prompt construction, dedup logic, prompt-injection resilience.
│   ├── test_config.py      # Env-var defaults + overrides.
│   └── test_smoke.py       # CLI end-to-end with mocked Qdrant + Anthropic.
│
├── docs/screenshots/
│   ├── ingest.gif          # Live GIF of `make up && make wait && make ingest`.
│   ├── ingest.tape         # vhs script that produced ingest.gif (no API key needed).
│   ├── demo.tape           # vhs script for the full demo (requires .env with key).
│   └── _check_collection.py# Helper that prints a one-line Qdrant collection summary.
│
└── .github/workflows/ci.yml# Python 3.11 → ruff → pytest → `python rag.py --help` smoke.
```

After running the demo, two more directories appear locally (both
gitignored):

- `qdrant_storage/` — Qdrant's on-disk data. Safe to delete.
- `~/.cache/huggingface/` — the cached embedding model. ~130 MB.

---

## 3. Env vars and secrets

The only secret is your Anthropic API key. Put it in a local `.env`
file at the repo root:

```bash
cp .env.example .env
# then edit .env so it contains:
ANTHROPIC_API_KEY=sk-ant-...
```

The `.env` file is gitignored. **Never commit it.** If you ever
accidentally commit a real key, rotate it at <https://console.anthropic.com/>
*first*, then clean git history.

The CLI reads `ANTHROPIC_API_KEY` directly from the process environment.
Either:

- `set -a; source .env; set +a` once per shell session (recommended), or
- export it inline: `ANTHROPIC_API_KEY=sk-ant-... make ask Q="..."`.

The Makefile does **not** auto-load `.env` for you. Add `source .env`
to your shell rc file if you want that.

All other configuration is optional and exposed as env vars too:

| Env var | Default | What it does |
| --- | --- | --- |
| `QDRANT_URL` | `http://localhost:6333` | Where Qdrant is. |
| `RAG_COLLECTION` | `markdown-rag` | Qdrant collection name. |
| `RAG_EMBED_MODEL` | `BAAI/bge-small-en-v1.5` | Sentence-transformers model. |
| `RAG_ANTHROPIC_MODEL` | `claude-sonnet-4-6` | Claude model. |
| `RAG_TOP_K` | `5` | How many chunks to retrieve per question. |
| `RAG_BATCH_SIZE` | `32` | Embedding + upsert batch size. |
| `RAG_MAX_TOKENS` | `1024` | Max tokens in Claude's reply. |
| `RAG_CORPUS_DIR` | `<repo>/corpus` | Where ingest reads markdown from. |
| `RAG_NAMESPACE` | `6d4e9a3a-3b1f-4f1b-8b9a-6c1d2c5e7f10` | UUIDv5 namespace for chunk IDs. |

---

## 4. How to verify the demo actually worked

After `make ingest`, run:

```bash
python docs/screenshots/_check_collection.py
```

Expected output:

```
points=68 dim=384 distance=Cosine status=green
payload_index source_file=keyword (68 points)
```

What each field tells you:

- **`points=68`** — all 68 chunks from the 12-file corpus were upserted.
  If you see `0`, ingest never reached Qdrant. If you see fewer, ingest
  was killed mid-run.
- **`dim=384`** — the BGE-small-v1.5 embedding dimension. Different
  numbers mean someone overrode `RAG_EMBED_MODEL` to a different model.
- **`distance=Cosine`** — the configured similarity metric. Should
  always be `Cosine` for this project.
- **`status=green`** — Qdrant's own health.
- **`payload_index source_file=keyword`** — the keyword index that
  makes the per-file delete-then-upsert in `ingest.py` fast. If this
  line is missing entirely (no `payload_index ...` line at all), the
  index was never created. If the count in parentheses is missing or
  zero, the index exists but the points haven't been registered against
  it yet — that can happen briefly right after a fresh ingest.

After `make ask Q="..."`, expected output is:

1. A streamed answer (visible token-by-token) grounded in the corpus.
   For an off-topic question, Claude will respond with the literal
   string `"I don't know based on the provided notes."` — that is the
   strict-grounding system prompt working as intended.
2. A blank line.
3. A `Sources:` block listing 1–5 unique `<file> > <heading>` pairs,
   one per line.

If you see the answer but no `Sources:` footer, the stream errored
mid-flight — re-run.

---

## 5. Common failure modes and their fixes

### `error: ANTHROPIC_API_KEY is not set`

The key is missing from the environment when `make ask` runs.

```bash
set -a; source .env; set +a   # load it from .env into current shell
make ask
```

If your `.env` does not exist yet, create it from `.env.example` first.

### "Qdrant unreachable at http://localhost:6333 after 8 attempts"

Qdrant is not running. Either `docker compose` is not running at all, or
the container died.

```bash
docker info | grep Server || open -a Docker     # macOS — start Docker Desktop
make up
docker logs markdown-rag-qdrant --tail 50       # if it crashes immediately
```

### "no chunks found — has the corpus been ingested?"

The collection exists but has zero points. Run `make ingest`. If ingest
completes but still no points, run the `_check_collection.py` helper —
it will tell you the actual state.

### `Existing collection 'markdown-rag' uses dim X; current model produces dim Y.`

You changed `RAG_EMBED_MODEL` to a model with a different vector
dimension while the old collection was still around. Reset and
re-ingest:

```bash
make reset
make ingest
```

### `error: rate limited by Anthropic API; retry shortly`

You hit the per-minute Anthropic rate limit. Wait 60 s and retry.

### `error: invalid ANTHROPIC_API_KEY`

The key is set but Anthropic rejected it. Double-check you copied the
whole `sk-ant-...` string and that the key is still active in the
Anthropic console.

### Tests pass but `python rag.py --help` errors out

Almost always a Python path problem. The `rag.py` entrypoint inserts
`src/` onto `sys.path`. If you renamed `rag.py` or moved it, that hack
no longer fires. Re-run from the repo root: `python ./rag.py --help`.

### vhs cannot render the GIF

`brew install vhs ffmpeg ttyd`. The two transitive deps (`ffmpeg`,
`ttyd`) are easy to forget if you grabbed `vhs` from a binary release.

---

## Demo verification status

The build session can autonomously verify steps 1–3 of the demo (`up`,
`wait`, `ingest`) but **cannot run step 4 (`ask`) because that requires
your Anthropic API key**. The session will not commit a key, even
temporarily, because real keys leak permanently from git history.

What I (Claude) ran:

```text
$ make up           # qdrant container started OK
$ make wait         # qdrant ready
$ make ingest       # ingested 68 chunks from 12 files (upserted 68)
$ python docs/screenshots/_check_collection.py
points=68 dim=384 distance=Cosine status=green
payload_index source_file=keyword (68 points)
```

What you need to do to verify the *full* demo:

```bash
# 1. Put your key in .env (one-time, never committed)
cp .env.example .env
$EDITOR .env       # set ANTHROPIC_API_KEY=sk-ant-...

# 2. Load it into the shell
set -a; source .env; set +a

# 3. Run the demo
make demo

# 4. (Optional) Capture a full demo GIF for the README:
brew install vhs ffmpeg ttyd        # if not already installed
vhs docs/screenshots/demo.tape      # writes docs/screenshots/demo.gif
```

If the demo succeeds, please update the "Last verified" line at the top
of this file with today's date, the commit SHA (`git rev-parse --short
HEAD`), and a one-line summary.

---

## README screenshot status

The README links to **`docs/screenshots/ingest.gif`**, a real recording
of the autonomous part of the demo (`make up`, `make wait`, `make
ingest`, plus a one-line collection-state verification). It was captured
with `vhs docs/screenshots/ingest.tape` on the same machine on
2026-06-09.

The full demo (with the streamed Claude answer) cannot be captured
autonomously because it needs your API key. The script
`docs/screenshots/demo.tape` is ready to render
`docs/screenshots/demo.gif` once you have a working `.env`:

```bash
set -a; source .env; set +a
vhs docs/screenshots/demo.tape
```

The resulting GIF lives at `docs/screenshots/demo.gif`. After it is
generated, update the README to embed it next to or instead of
`ingest.gif`.
