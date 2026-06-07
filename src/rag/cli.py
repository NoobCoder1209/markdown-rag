"""Typer CLI: ingest, ask, reset, wait. Friendly errors only — no tracebacks."""

from __future__ import annotations

import typer

from .config import CORPUS_DIR, TOP_K, die

app = typer.Typer(
    add_completion=False,
    help="Local RAG over a folder of markdown files.",
    no_args_is_help=True,
)


@app.command()
def ingest(
    directory: str = typer.Option(CORPUS_DIR, "--dir", "-d", help="Path to the markdown corpus."),
) -> None:
    """Chunk, embed, and upsert the corpus into Qdrant."""
    from qdrant_client.http.exceptions import ApiException, UnexpectedResponse

    from .ingest import ingest as run_ingest

    try:
        result = run_ingest(directory)
    except FileNotFoundError as exc:
        die(str(exc))
        return
    except RuntimeError as exc:
        die(f"{exc}. Run `make up` first.")
        return
    except (ApiException, UnexpectedResponse) as exc:
        die(f"Qdrant error: {exc}")
        return
    typer.echo(
        f"ingested {result['chunks']} chunks from {result['files']} files "
        f"(upserted {result['upserted']})"
    )


@app.command()
def ask(
    question: str = typer.Argument(..., help="The question to ask."),
    top_k: int = typer.Option(TOP_K, "--top-k", "-k", help="How many chunks to retrieve."),
) -> None:
    """Retrieve top-k chunks and stream a Claude answer with a Sources footer."""
    from .answer import stream_answer
    from .retrieve import retrieve

    try:
        chunks = retrieve(question, top_k=top_k)
    except RuntimeError as exc:
        die(f"{exc}. Run `make up` first.")
        return
    if not chunks:
        die("no chunks found — has the corpus been ingested? Run `make ingest` first.")
        return
    stream_answer(question, chunks)


@app.command()
def reset() -> None:
    """Drop the Qdrant collection."""
    from .vector_store import VectorStore

    try:
        store = VectorStore()
        store.wait_until_ready()
        store.reset()
    except RuntimeError as exc:
        die(f"{exc}. Run `make up` first.")
        return
    typer.echo("collection dropped")


@app.command()
def wait() -> None:
    """Block until Qdrant is reachable. Used by `make demo`."""
    from .vector_store import VectorStore

    try:
        VectorStore().wait_until_ready()
    except RuntimeError as exc:
        die(str(exc))
        return
    typer.echo("qdrant ready")


if __name__ == "__main__":
    app()
