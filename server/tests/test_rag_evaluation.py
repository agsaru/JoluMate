from langchain_core.documents import Document

from rag.evaluation import calculate_retrieval_metrics


def test_retrieval_metrics_use_unique_filename_and_page_sources():
    results = [
        Document(
            page_content="First chunk",
            metadata={"filename": "policy.pdf", "page_number": 4},
        ),
        Document(
            page_content="Second chunk from same page",
            metadata={"filename": "policy.pdf", "page_number": 4},
        ),
        Document(
            page_content="Another source",
            metadata={"filename": "handbook.pdf", "page_number": 2},
        ),
    ]

    metrics = calculate_retrieval_metrics(
        results,
        expected_sources=["policy.pdf#4", "handbook.pdf#2"],
        k=5,
    )

    assert metrics == {"recall_at_k": 1.0, "reciprocal_rank": 1.0}


def test_retrieval_metrics_return_zero_when_no_expected_source_is_found():
    results = [
        Document(
            page_content="Unrelated chunk",
            metadata={"filename": "policy.pdf", "page_number": 1},
        )
    ]

    metrics = calculate_retrieval_metrics(
        results,
        expected_sources=["policy.pdf#8"],
        k=5,
    )

    assert metrics == {"recall_at_k": 0.0, "reciprocal_rank": 0.0}


def test_retrieval_metrics_require_ground_truth_sources():
    try:
        calculate_retrieval_metrics([], [], k=5)
    except ValueError as error:
        assert "expected source" in str(error)
    else:
        raise AssertionError("Expected empty ground truth to be rejected")
