def calculate_retrieval_metrics(results, expected_sources, k=5):
    """Calculate recall@k and reciprocal rank using filename/page source IDs."""
    expected = set(expected_sources)
    if not expected:
        raise ValueError("Each evaluation case must include at least one expected source")

    ranked_sources = []
    for document in results[:k]:
        filename = document.metadata.get("filename")
        page_number = document.metadata.get("page_number")
        if filename and page_number is not None:
            source = f"{filename}#{page_number}"
            if source not in ranked_sources:
                ranked_sources.append(source)

    relevant_found = expected.intersection(ranked_sources)
    recall = len(relevant_found) / len(expected)

    reciprocal_rank = 0.0
    for rank, source in enumerate(ranked_sources, start=1):
        if source in expected:
            reciprocal_rank = 1 / rank
            break

    return {"recall_at_k": recall, "reciprocal_rank": reciprocal_rank}
