"""Deterministic, dependency-light guardrails for the JoluMate RAG pipeline.

These checks do not call an LLM. They validate inputs and citation references only;
they cannot establish whether an answer is factually faithful to its sources.
"""

import re

MAX_SEARCH_QUERY_LENGTH = 4000

_SOURCE_LINE_RE = re.compile(
    r"^\[Source: (?P<filename>.+?), page (?P<page>\d+|unknown)\]$",
    re.MULTILINE,
)
_CITATION_RE = re.compile(
    r"\[Source: (?P<filename>.+?), page (?P<page>\d+|unknown)\]"
)


def validate_search_query(query: str, max_length: int = MAX_SEARCH_QUERY_LENGTH) -> str:
    """Return a normalized query or raise ValueError for invalid input."""
    if not isinstance(query, str):
        raise ValueError("Search query must be a string.")

    normalized = query.strip()
    if not normalized:
        raise ValueError("Search query cannot be empty.")

    if len(normalized) > max_length:
        raise ValueError(f"Search query cannot exceed {max_length} characters.")

    if any(ord(char) < 32 and char not in "\t\n\r" for char in normalized):
        raise ValueError("Search query contains unsupported control characters.")

    return normalized


def _source_key(filename: str, page: str) -> tuple[str, str]:
    return filename.strip(), page.strip()


def extract_retrieved_sources(context: str) -> set[tuple[str, str]]:
    """Extract source labels emitted by JoluMate's retrieval formatter."""
    if not isinstance(context, str):
        return set()
    return {
        _source_key(match.group("filename"), match.group("page"))
        for match in _SOURCE_LINE_RE.finditer(context)
    }


def validate_answer_citations(answer: str, retrieved_context: str) -> dict:
    """Check that every explicit answer citation exists in retrieved context.

    This is a reference-integrity check, not a semantic faithfulness check.
    """
    if not isinstance(answer, str):
        raise ValueError("Answer must be a string.")

    available = extract_retrieved_sources(retrieved_context)
    cited = {
        _source_key(match.group("filename"), match.group("page"))
        for match in _CITATION_RE.finditer(answer)
    }
    unsupported = sorted(cited - available)

    return {
        "valid": not unsupported,
        "has_citations": bool(cited),
        "cited_sources": sorted(cited),
        "unsupported_sources": unsupported,
    }
