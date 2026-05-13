import pytest
from app.services.chunking_service import chunk_text, CHUNK_SIZE, CHUNK_OVERLAP


def test_empty_text_returns_no_chunks():
    assert chunk_text("") == []


def test_short_text_returns_single_chunk():
    chunks = chunk_text("Hello world. This is a short document.")
    assert len(chunks) == 1
    assert chunks[0].chunk_index == 0
    assert chunks[0].token_count > 0
    assert "Hello" in chunks[0].text


def test_chunk_indices_are_sequential():
    long_text = " ".join(["word"] * 2000)
    chunks = chunk_text(long_text)
    for i, chunk in enumerate(chunks):
        assert chunk.chunk_index == i


def test_large_text_produces_multiple_chunks():
    long_text = " ".join(["word"] * 2000)
    chunks = chunk_text(long_text)
    assert len(chunks) > 1


def test_each_chunk_within_size_limit():
    long_text = " ".join(["word"] * 2000)
    chunks = chunk_text(long_text)
    for chunk in chunks:
        assert chunk.token_count <= CHUNK_SIZE


def test_overlap_means_adjacent_chunks_share_content():
    long_text = " ".join([f"word{i}" for i in range(1200)])
    chunks = chunk_text(long_text)
    if len(chunks) >= 2:
        words_first = set(chunks[0].text.split())
        words_second = set(chunks[1].text.split())
        assert words_first & words_second, "Adjacent chunks should share overlapping tokens"


def test_whitespace_only_text_returns_no_chunks():
    assert chunk_text("   \n\t  ") == []
