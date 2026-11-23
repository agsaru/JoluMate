import math


def _ranked_unique_sources(results, k):
    if not isinstance(k, int) or isinstance(k, bool) or k < 1:
        raise ValueError("k must be a positive integer")

    ranked_sources = []
    for document in results[:k]:
        metadata = getattr(document, "metadata", {}) or {}
        filename = metadata.get("filename")
        page_number = metadata.get("page_number")
        if filename and page_number is not None:
            source = f"{filename}#{page_number}"
            if source not in ranked_sources:
                ranked_sources.append(source)
    return ranked_sources


def validate_evaluation_case(case, index=None):
    """Validate one JSONL ground-truth record without external/LLM calls."""
    prefix = f"Evaluation case {index}: " if index is not None else "Evaluation case: "
    if not isinstance(case, dict):
        raise ValueError(prefix + "each line must contain a JSON object")

    query = case.get("query")
    if not isinstance(query, str) or not query.strip():
        raise ValueError(prefix + "'query' must be a non-empty string")

    expected_sources = case.get("expected_sources")
    if (
        not isinstance(expected_sources, list)
        or not expected_sources
        or any(not isinstance(source, str) or not source.strip() for source in expected_sources)
    ):
        raise ValueError(prefix + "'expected_sources' must be a non-empty list of source IDs")

    return {
        "query": query.strip(),
        "expected_sources": list(dict.fromkeys(source.strip() for source in expected_sources)),
    }


def calculate_retrieval_metrics(results, expected_sources, k=5):
    """Calculate deterministic ranking metrics using filename/page source IDs."""
    if not expected_sources:
        raise ValueError("Each evaluation case must include at least one expected source")
    if any(not isinstance(source, str) or not source.strip() for source in expected_sources):
        raise ValueError("Expected source IDs must be non-empty strings")

    expected = set(expected_sources)
    ranked_sources = _ranked_unique_sources(results, k)
    relevant_ranks = [
        rank for rank, source in enumerate(ranked_sources, start=1)
        if source in expected
    ]

    relevant_found = len(relevant_ranks)
    recall = relevant_found / len(expected)
    precision = relevant_found / k
    reciprocal_rank = 1 / relevant_ranks[0] if relevant_ranks else 0.0
    hit_rate = 1.0 if relevant_ranks else 0.0

    dcg = sum(1 / math.log2(rank + 1) for rank in relevant_ranks)
    ideal_relevant = min(len(expected), k)
    ideal_dcg = sum(
        1 / math.log2(rank + 1)
        for rank in range(1, ideal_relevant + 1)
    )
    ndcg = dcg / ideal_dcg if ideal_dcg else 0.0

    return {
        "precision_at_k": precision,
        "recall_at_k": recall,
        "hit_rate_at_k": hit_rate,
        "reciprocal_rank": reciprocal_rank,
        "ndcg_at_k": ndcg,
    }
