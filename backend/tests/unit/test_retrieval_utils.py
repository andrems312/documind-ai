import uuid

from app.ai.retrieval import RRF_K, RetrievedChunk, fit_to_budget, reciprocal_rank_fusion


def test_rrf_rewards_items_ranked_by_both_strategies() -> None:
    a, b, c = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    scores = reciprocal_rank_fusion([[a, b], [b, c]])
    assert scores[b] > scores[a] > scores[c] or scores[b] > scores[c]
    assert scores[b] == 1 / (RRF_K + 2) + 1 / (RRF_K + 1)
    assert max(scores, key=lambda k: scores[k]) == b


def test_rrf_with_empty_rankings() -> None:
    assert reciprocal_rank_fusion([[], []]) == {}


def _chunk(tokens: int) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        document_title="Doc",
        page_number=1,
        chunk_index=0,
        content="x",
        token_count=tokens,
        similarity=0.9,
        text_rank=None,
        score=0.1,
    )


def test_fit_to_budget_keeps_order_and_stops_at_limit() -> None:
    chunks = [_chunk(300), _chunk(300), _chunk(300)]
    assert fit_to_budget(chunks, 700) == chunks[:2]


def test_fit_to_budget_always_keeps_the_best_chunk() -> None:
    chunks = [_chunk(900)]
    assert fit_to_budget(chunks, 500) == chunks
