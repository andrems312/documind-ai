import pytest

from app.processing.chunker import chunk_pages, count_tokens
from app.processing.extractor import PageText


def _paragraphs(n: int, words: int = 40) -> str:
    return "\n\n".join(" ".join(f"palavra{p}_{w}" for w in range(words)) + "." for p in range(n))


def test_small_pages_become_one_chunk_each() -> None:
    pages = [PageText(1, "Texto curto da página um."), PageText(2, "Outro texto curto.")]
    chunks = chunk_pages(pages, max_tokens=200, overlap_tokens=20)
    assert [(c.page_number, c.chunk_index) for c in chunks] == [(1, 0), (2, 1)]
    assert chunks[0].content == "Texto curto da página um."


def test_chunks_respect_token_limit_and_never_cross_pages() -> None:
    pages = [PageText(1, _paragraphs(12)), PageText(2, _paragraphs(9))]
    chunks = chunk_pages(pages, max_tokens=150, overlap_tokens=30)
    assert len(chunks) > 4
    for chunk in chunks:
        assert chunk.token_count <= 150 + 5  # pequena folga pelos separadores
        source = pages[chunk.page_number - 1].text
        for paragraph in chunk.content.split("\n\n"):
            assert paragraph in source  # cada trecho vem integralmente da própria página
    assert [c.chunk_index for c in chunks] == list(range(len(chunks)))


def test_consecutive_chunks_overlap() -> None:
    pages = [PageText(1, _paragraphs(10, words=8))]
    chunks = chunk_pages(pages, max_tokens=120, overlap_tokens=60)
    assert len(chunks) > 2
    for previous, current in zip(chunks, chunks[1:], strict=False):
        last_paragraph = previous.content.split("\n\n")[-1]
        assert current.content.startswith(last_paragraph)


def test_very_long_sentence_is_split_on_word_boundaries() -> None:
    words = [f"termo{i}" for i in range(1500)]
    chunks = chunk_pages([PageText(1, " ".join(words))], max_tokens=200, overlap_tokens=0)
    assert len(chunks) >= 5
    assert all(c.token_count <= 205 for c in chunks)
    rebuilt = " ".join(c.content for c in chunks).split()
    assert rebuilt == words  # nenhuma palavra cortada ao meio ou perdida


def test_empty_pages_produce_no_chunks() -> None:
    assert chunk_pages([PageText(1, ""), PageText(2, "   ")]) == []


def test_invalid_overlap_raises() -> None:
    with pytest.raises(ValueError):
        chunk_pages([PageText(1, "x")], max_tokens=100, overlap_tokens=100)


def test_count_tokens_is_positive() -> None:
    assert count_tokens("Olá, mundo!") > 0
