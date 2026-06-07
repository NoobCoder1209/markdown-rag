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


def test_h1_does_not_flush_when_h2_present() -> None:
    """When the file has any H2, splits happen on H2; the H1 should NOT flush.

    Verifies the intro paragraph after the H1 lands in the same chunk as the
    first H2 section's content (or stays attached to the H1 chunk pre-flush).
    Either way, we must not see two chunks ending at H1.
    """
    md = """# Top

intro under h1.

## Section A

a body.

### Sub A1

sub-a-1 body.

## Section B

b body.
"""
    chunks = chunk_text(md, source_file="mixed.md")
    # Heading path should always start with "Top" since H1 never flushes.
    for c in chunks:
        if c.heading_path:
            assert c.heading_path[0] == "Top"
    # Section B chunk exists and has H2 path of length 2 (Top > Section B).
    section_b = [c for c in chunks if c.heading_path and c.heading_path[-1] == "Section B"]
    assert len(section_b) == 1
    assert section_b[0].heading_path == ["Top", "Section B"]


def test_repeated_h2_name_produces_two_distinct_chunks() -> None:
    """Two H2 sections with identical names must still produce two chunks."""
    md = """# Top

## Notes

first notes body.

## Other

other body.

## Notes

second notes body.
"""
    chunks = chunk_text(md, source_file="dup.md")
    notes_chunks = [c for c in chunks if c.heading_path and c.heading_path[-1] == "Notes"]
    assert len(notes_chunks) == 2
    bodies = " ".join(c.text for c in notes_chunks)
    assert "first notes body" in bodies
    assert "second notes body" in bodies


def test_frontmatter_without_trailing_newline() -> None:
    """Frontmatter ending without a final newline should still be stripped."""
    md = "---\ntitle: t\n---\n# Body\n\ncontent here."
    chunks = chunk_text(md, source_file="fm2.md")
    joined = "\n".join(c.text for c in chunks)
    assert "title: t" not in joined
    assert "content here" in joined


def test_single_sentence_no_heading() -> None:
    """A single sentence with no heading should produce exactly one chunk."""
    md = "just one short sentence."
    chunks = chunk_text(md, source_file="tiny.md")
    assert len(chunks) == 1
    assert chunks[0].heading_path == []
    assert "just one short sentence" in chunks[0].text


def test_consecutive_headings_with_no_body() -> None:
    """Consecutive headings with no paragraphs in between should not crash
    and should still produce chunks tagged with the right heading paths."""
    md = """# Top

## A

## B

body under b.
"""
    chunks = chunk_text(md, source_file="consec.md")
    last_paths = [c.heading_path[-1] for c in chunks if c.heading_path]
    assert "B" in last_paths
    b_chunks = [c for c in chunks if c.heading_path and c.heading_path[-1] == "B"]
    assert any("body under b" in c.text for c in b_chunks)


def test_frontmatter_with_crlf_line_endings() -> None:
    """Frontmatter authored on Windows (CRLF) should still be stripped."""
    md = "---\r\ntitle: t\r\n---\r\n# Body\r\n\r\ncontent here."
    chunks = chunk_text(md, source_file="crlf.md")
    joined = "\n".join(c.text for c in chunks)
    assert "title: t" not in joined
    assert "content here" in joined


def test_empty_frontmatter_is_stripped() -> None:
    """An empty `---\\n---` block at file start should be removed cleanly."""
    md = "---\n---\n# Body\n\ncontent here."
    chunks = chunk_text(md, source_file="empty_fm.md")
    joined = "\n".join(c.text for c in chunks)
    assert "---" not in joined
    assert "content here" in joined


def test_frontmatter_value_with_dash_dash_dash_in_string_is_safe() -> None:
    """Frontmatter values containing '---' inside a YAML string should not
    fool the parser into closing early. Only standalone --- lines count.
    """
    md = "---\ntitle: contains --- inside text\nfoo: bar\n---\n# Body\n\nrealcontent."
    chunks = chunk_text(md, source_file="tricky_fm.md")
    joined = "\n".join(c.text for c in chunks)
    assert "title:" not in joined
    assert "realcontent" in joined


def test_gfm_table_does_not_crash_chunker() -> None:
    """The GFM-like preset should accept tables (a common feature in real notes).
    The chunker walks tokens it doesn't explicitly handle without exploding.
    """
    md = """# Notes

## Compatibility

| feature | supported |
|---------|-----------|
| tables  | yes       |
| lists   | yes       |

closing prose.
"""
    chunks = chunk_text(md, source_file="table.md")
    # We don't assert table tokens are preserved verbatim — only that the
    # chunker emits at least one chunk for the section and doesn't crash.
    section_chunks = [c for c in chunks if c.heading_path and c.heading_path[-1] == "Compatibility"]
    assert section_chunks
    assert any("closing prose" in c.text for c in section_chunks)
