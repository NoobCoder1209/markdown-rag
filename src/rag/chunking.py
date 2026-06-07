"""Markdown-aware chunker that walks the markdown-it-py token stream.

Splits on H2 headings (or H1 if a file has no H2), preserves heading_path
context, keeps fenced code blocks atomic, and applies a soft size cap with
1-sentence overlap on size-driven secondary splits.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from markdown_it import MarkdownIt

WORD_CAP = 380  # ≈ 500 tokens via *1.3 heuristic
SENTENCE_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9])")


@dataclass
class Chunk:
    """A single retrievable unit of a markdown file."""

    text: str
    source_file: str
    heading_path: list[str] = field(default_factory=list)


def _strip_frontmatter(src: str) -> str:
    """Remove a leading YAML/TOML frontmatter block delimited by --- ... ---."""
    if not src.startswith("---\n"):
        return src
    end = src.find("\n---", 4)
    if end == -1:
        return src
    return src[end + 4 :].lstrip("\n")


def _approx_tokens(text: str) -> int:
    return int(len(text.split()) * 1.3)


def _walk_tokens(tokens, source_file: str, split_tag: str) -> list[Chunk]:
    """Walk markdown-it-py tokens and emit one chunk per `split_tag` section."""
    chunks: list[Chunk] = []
    buf: list[str] = []
    heading_stack: list[tuple[int, str]] = []

    def current_path() -> list[str]:
        return [text for _, text in heading_stack]

    def flush() -> None:
        text = "\n\n".join(piece for piece in buf if piece).strip()
        if text:
            chunks.append(Chunk(text=text, source_file=source_file, heading_path=current_path()))
        buf.clear()

    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if tok.type == "heading_open":
            level = int(tok.tag[1])
            inline_text = tokens[i + 1].content if i + 1 < len(tokens) else ""
            if tok.tag == split_tag and (buf or chunks):
                flush()
            while heading_stack and heading_stack[-1][0] >= level:
                heading_stack.pop()
            heading_stack.append((level, inline_text))
            buf.append(("#" * level) + " " + inline_text)
            i += 3  # skip heading_open, inline, heading_close
            continue
        if tok.type in ("fence", "code_block"):
            lang = tok.info or ""
            buf.append(f"```{lang}\n{tok.content.rstrip()}\n```")
        elif tok.type == "inline":
            buf.append(tok.content)
        elif tok.type == "html_block":
            buf.append(tok.content.strip())
        i += 1
    flush()
    return chunks


def _size_split(chunks: list[Chunk]) -> list[Chunk]:
    """Secondary pass: split chunks above WORD_CAP on sentence boundaries.

    Skip any chunk that contains a fenced code block to keep code atomic.
    Carry one sentence of overlap from the previous slice into the next.
    """
    out: list[Chunk] = []
    for ch in chunks:
        if _approx_tokens(ch.text) <= 500 or "```" in ch.text:
            out.append(ch)
            continue
        sentences = SENTENCE_RE.split(ch.text)
        cur: list[str] = []
        cur_words = 0
        for sentence in sentences:
            words = len(sentence.split())
            if cur_words + words > WORD_CAP and cur:
                out.append(
                    Chunk(
                        text=" ".join(cur),
                        source_file=ch.source_file,
                        heading_path=list(ch.heading_path),
                    )
                )
                tail = cur[-1]
                cur = [tail, sentence]
                cur_words = len(tail.split()) + words
            else:
                cur.append(sentence)
                cur_words += words
        if cur:
            out.append(
                Chunk(
                    text=" ".join(cur),
                    source_file=ch.source_file,
                    heading_path=list(ch.heading_path),
                )
            )
    return out


def chunk_text(text: str, source_file: str) -> list[Chunk]:
    """Chunk a markdown string. `source_file` is stored on every chunk."""
    src = _strip_frontmatter(text)
    md = MarkdownIt("commonmark")
    tokens = md.parse(src)
    has_h2 = any(t.type == "heading_open" and t.tag == "h2" for t in tokens)
    split_tag = "h2" if has_h2 else "h1"
    primary = _walk_tokens(tokens, source_file=source_file, split_tag=split_tag)
    return _size_split(primary)


def chunk_file(path: Path) -> list[Chunk]:
    """Chunk a markdown file by path. Stores the file's basename as source_file."""
    return chunk_text(path.read_text(encoding="utf-8"), source_file=path.name)
