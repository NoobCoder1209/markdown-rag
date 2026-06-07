"""Tests for the config module: env-var overrides and defaults."""

from __future__ import annotations

import importlib
import os
import uuid
from pathlib import Path

import pytest


def _reload_config():  # noqa: ANN202
    import rag.config

    return importlib.reload(rag.config)


@pytest.fixture(autouse=True)
def _restore_env():
    saved = dict(os.environ)
    yield
    os.environ.clear()
    os.environ.update(saved)
    # Reload so module-level constants reflect the restored env, otherwise
    # later tests can observe stale values from an earlier override.
    _reload_config()


def test_corpus_dir_defaults_to_repo_root_corpus(monkeypatch) -> None:
    monkeypatch.delenv("RAG_CORPUS_DIR", raising=False)
    config = _reload_config()
    assert Path(config.CORPUS_DIR).is_absolute()
    assert Path(config.CORPUS_DIR).name == "corpus"


def test_corpus_dir_env_override(monkeypatch) -> None:
    monkeypatch.setenv("RAG_CORPUS_DIR", "/tmp/my-notes")
    config = _reload_config()
    assert config.CORPUS_DIR == "/tmp/my-notes"


def test_rag_namespace_default_is_stable(monkeypatch) -> None:
    monkeypatch.delenv("RAG_NAMESPACE", raising=False)
    config = _reload_config()
    assert isinstance(config.RAG_NAMESPACE, uuid.UUID)
    # Stable across runs — pinned to the bootstrap value.
    assert str(config.RAG_NAMESPACE) == "6d4e9a3a-3b1f-4f1b-8b9a-6c1d2c5e7f10"


def test_rag_namespace_env_override(monkeypatch) -> None:
    custom = "11111111-2222-3333-4444-555555555555"
    monkeypatch.setenv("RAG_NAMESPACE", custom)
    config = _reload_config()
    assert str(config.RAG_NAMESPACE) == custom


def test_rag_namespace_invalid_exits_with_friendly_error(monkeypatch, capsys) -> None:
    monkeypatch.setenv("RAG_NAMESPACE", "not-a-uuid")
    with pytest.raises(SystemExit) as excinfo:
        _reload_config()
    assert excinfo.value.code == 1
    captured = capsys.readouterr()
    assert "RAG_NAMESPACE" in captured.err
    assert "not-a-uuid" in captured.err
