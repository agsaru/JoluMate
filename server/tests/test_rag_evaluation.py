import pytest
from langchain_core.documents import Document

from rag.evaluation import calculate_retrieval_metrics, validate_evaluation_case
from rag.guardrails import (
    extract_retrieved_sources,
    validate_answer_citations,
    validate_search_query,
)


def test_retrieval_metrics_use_unique_filename_and_page_sources():
    results = [
        Document(page_content="First chunk", metadata={"filename": "biology_notes.pdf", "page_number": 4}),
        Document(page_content="Second chunk from same page", metadata={"filename": "biology_notes.pdf", "page_number": 4}),
        Document(page_content="Another source", metadata={"filename": "chemistry_notes.pdf", "page_number": 2}),
    ]

    metrics = calculate_retrieval_metrics(
        results,
        expected_sources=["biology_notes.pdf#4", "chemistry_notes.pdf#2"],
        k=5,
    )

    assert metrics["recall_at_k"] == 1.0
    assert metrics["reciprocal_rank"] == 1.0
    assert metrics["hit_rate_at_k"] == 1.0
    assert metrics["ndcg_at_k"] == 1.0
    assert metrics["precision_at_k"] == pytest.approx(0.4)


def test_retrieval_metrics_return_zero_when_no_expected_source_is_found():
    results = [
        Document(page_content="Unrelated chunk", metadata={"filename": "biology_notes.pdf", "page_number": 1})
    ]

    metrics = calculate_retrieval_metrics(results, ["biology_notes.pdf#8"], k=5)

    assert metrics["recall_at_k"] == 0.0
    assert metrics["reciprocal_rank"] == 0.0
    assert metrics["hit_rate_at_k"] == 0.0
    assert metrics["ndcg_at_k"] == 0.0


def test_retrieval_metrics_require_ground_truth_sources():
    with pytest.raises(ValueError, match="expected source"):
        calculate_retrieval_metrics([], [], k=5)


@pytest.mark.parametrize("k", [0, -1, True, 1.5])
def test_retrieval_metrics_reject_invalid_k(k):
    with pytest.raises(ValueError, match="positive integer"):
        calculate_retrieval_metrics(
            [Document(page_content="x", metadata={"filename": "a.pdf", "page_number": 1})],
            ["a.pdf#1"],
            k=k,
        )


def test_evaluation_case_validation_normalizes_and_deduplicates_sources():
    case = validate_evaluation_case(
        {"query": "  explain osmosis  ", "expected_sources": ["bio.pdf#1", "bio.pdf#1"]}
    )
    assert case == {"query": "explain osmosis", "expected_sources": ["bio.pdf#1"]}


@pytest.mark.parametrize(
    "case",
    [
        {},
        {"query": " ", "expected_sources": ["a.pdf#1"]},
        {"query": "question", "expected_sources": []},
        {"query": "question", "expected_sources": [" "]},
    ],
)
def test_evaluation_case_validation_rejects_bad_ground_truth(case):
    with pytest.raises(ValueError):
        validate_evaluation_case(case)


def test_search_query_validation_normalizes_input():
    assert validate_search_query("  explain this  ") == "explain this"


@pytest.mark.parametrize("query", ["", "  ", "a" * 4001, "bad\x00query", None])
def test_search_query_validation_rejects_invalid_input(query):
    with pytest.raises(ValueError):
        validate_search_query(query)


def test_citation_validation_accepts_only_sources_present_in_retrieved_context():
    context = (
        "[Source: biology.pdf, page 3]\nCell structure...\n"
        "[Source: chemistry.pdf, page 2]\nChemical bonds..."
    )
    result = validate_answer_citations(
        "Cells have membranes [Source: biology.pdf, page 3]. "
        "Atoms bond [Source: chemistry.pdf, page 2].",
        context,
    )
    assert result["valid"] is True
    assert result["has_citations"] is True
    assert result["unsupported_sources"] == []


def test_citation_validation_flags_fabricated_or_unretrieved_sources():
    result = validate_answer_citations(
        "Claim [Source: invented.pdf, page 99].",
        "[Source: biology.pdf, page 3]\nRetrieved text",
    )
    assert result["valid"] is False
    assert result["unsupported_sources"] == [("invented.pdf", "99")]


def test_citation_validation_reports_when_answer_has_no_citations():
    result = validate_answer_citations("An uncited answer.", "[Source: biology.pdf, page 3]")
    assert result["valid"] is True
    assert result["has_citations"] is False


def test_required_citation_is_rejected_when_retrieved_sources_exist():
    result = validate_answer_citations(
        "An uncited answer.",
        "[Source: biology.pdf, page 3]",
        require_citations=True,
    )
    assert result["valid"] is False
    assert result["missing_citations"] is True


def test_source_extraction_ignores_unrelated_lines():
    assert extract_retrieved_sources("ordinary text\n[Source: notes.pdf, page 8]") == {
        ("notes.pdf", "8")
    }



def test_citation_validation_does_not_accept_sources_from_earlier_turns():
    # The caller must pass only the latest ToolMessage, not the full conversation.
    previous_turn_context = "[Source: biology.pdf, page 3]\nCell structure..."
    current_turn_context = "[Source: chemistry.pdf, page 2]\nChemical bonds..."

    result = validate_answer_citations(
        "Cells have membranes [Source: biology.pdf, page 3].",
        current_turn_context,
        require_citations=True,
    )

    assert result["valid"] is False
    assert result["unsupported_sources"] == [("biology.pdf", "3")]


def test_empty_retrieval_has_no_verifiable_sources():
    assert extract_retrieved_sources("") == set()
    assert extract_retrieved_sources(
        "No relevant information was found in the uploaded study materials."
    ) == set()
