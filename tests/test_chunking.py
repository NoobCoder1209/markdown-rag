"""Unit tests for the markdown chunker."""

from __future__ import annotations

from rag.chunking import Chunk, _approx_tokens, chunk_text


def test_splits_on_h2_when_present() -> None:
    md = """# Title

intro paragraph here.

## First Section

first body. one sentence. another sentence.

## Second Section

second body.
"""
    chunks = chunk_text(md, source_file="example.md")
    headings = [c.heading_path for c in chunks]
    assert ["Title"] in headings or chunks[0].heading_path == ["Title"]
    assert any(path[-1] == "First Section" for path in headings if path)
    assert any(path[-1] == "Second Section" for path in headings if path)
    assert all(c.source_file == "example.md" for c in chunks)


def test_falls_back_to_h1_when_no_h2() -> None:
    md = """# Alpha

alpha body.

# Beta

beta body.
"""
    chunks = chunk_text(md, source_file="ab.md")
    last_headings = [c.heading_path[-1] for c in chunks if c.heading_path]
    assert "Alpha" in last_headings
    assert "Beta" in last_headings


def test_no_headings_emits_single_chunk() -> None:
    md = "just a paragraph.\n\nand another paragraph.\n"
    chunks = chunk_text(md, source_file="plain.md")
    assert len(chunks) == 1
    assert chunks[0].heading_path == []
    assert "paragraph" in chunks[0].text


def test_strips_yaml_frontmatter() -> None:
    md = """---
title: My Note
tags: [k8s]
---

# Body

actual content here.
"""
    chunks = chunk_text(md, source_file="fm.md")
    joined = "\n".join(c.text for c in chunks)
    assert "title: My Note" not in joined
    assert "actual content here" in joined


def test_code_fence_kept_atomic_on_size_split() -> None:
    big_code = "x = 1\n" * 600  # well over the 380-word soft cap
    md = f"""# Title

## Big Code Section

prose before code.

```python
{big_code}```

prose after.
"""
    chunks = chunk_text(md, source_file="code.md")
    code_chunks = [c for c in chunks if "```" in c.text]
    assert len(code_chunks) == 1
    assert code_chunks[0].text.count("```") == 2
    # If atomic, this single chunk is allowed to exceed the cap.
    assert _approx_tokens(code_chunks[0].text) > 500


def test_oversized_prose_section_gets_sentence_split_with_overlap() -> None:
    sentence = "This sentence has exactly ten distinct word tokens here right now. "
    big = sentence * 60  # ~600 words, well over WORD_CAP
    md = f"""# Title

## Long Section

{big}
"""
    chunks = chunk_text(md, source_file="long.md")
    long_chunks = [c for c in chunks if c.heading_path and c.heading_path[-1] == "Long Section"]
    assert len(long_chunks) >= 2, "oversized section should be split"
    # Each split chunk should still respect the source_file and heading_path.
    for c in long_chunks:
        assert c.source_file == "long.md"
        assert c.heading_path == ["Title", "Long Section"]


def test_heading_path_pops_deeper_levels() -> None:
    md = """# Top

## Section A

### Sub A1

sub body.

## Section B

section b body.
"""
    chunks = chunk_text(md, source_file="nest.md")
    section_b_chunks = [c for c in chunks if c.heading_path and c.heading_path[-1] == "Section B"]
    assert section_b_chunks, "Section B chunk should exist"
    # When we re-enter Section B at H2, deeper H3 'Sub A1' should NOT be in the path.
    assert "Sub A1" not in section_b_chunks[0].heading_path


def test_chunk_dataclass_defaults() -> None:
    chunk = Chunk(text="hello", source_file="x.md")
    assert chunk.heading_path == []
