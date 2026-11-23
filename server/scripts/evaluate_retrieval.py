import asyncio
import json
import os
from pathlib import Path

from dotenv import load_dotenv

from rag.evaluation import calculate_retrieval_metrics, validate_evaluation_case
from rag.utils import retrieve_documents

load_dotenv()

EVAL_DATASET = Path(os.getenv("RAG_EVAL_DATASET", "evaluation/rag_golden_set.jsonl"))
EVAL_USER_ID = os.getenv("RAG_EVAL_USER_ID")
EVAL_CONVERSATION_ID = os.getenv("RAG_EVAL_CONVERSATION_ID")
TOP_K = 5
METRIC_NAMES = (
    "precision_at_k",
    "recall_at_k",
    "hit_rate_at_k",
    "reciprocal_rank",
    "ndcg_at_k",
)


def load_evaluation_dataset(path):
    """Load and validate JSONL cases before running any retrieval queries."""
    cases = []
    with path.open(encoding="utf-8") as dataset_file:
        for line_number, line in enumerate(dataset_file, start=1):
            if not line.strip():
                continue
            try:
                raw_case = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"Invalid JSON on dataset line {line_number}: {error}") from error
            cases.append(validate_evaluation_case(raw_case, index=line_number))

    if not cases:
        raise ValueError("The retrieval evaluation dataset is empty")
    return cases


async def evaluate():
    if not EVAL_USER_ID or not EVAL_CONVERSATION_ID:
        raise RuntimeError(
            "Set RAG_EVAL_USER_ID and RAG_EVAL_CONVERSATION_ID to a conversation "
            "containing the documents used by the evaluation dataset."
        )

    if not EVAL_DATASET.is_file():
        raise FileNotFoundError(f"Evaluation dataset not found: {EVAL_DATASET}")

    cases = load_evaluation_dataset(EVAL_DATASET)
    scores = []

    for case in cases:
        results = await retrieve_documents(
            case["query"],
            EVAL_USER_ID,
            EVAL_CONVERSATION_ID,
            limit=TOP_K,
        )
        scores.append(
            calculate_retrieval_metrics(results, case["expected_sources"], TOP_K)
        )

    print(f"Queries evaluated: {len(scores)}")
    for metric_name in METRIC_NAMES:
        mean_score = sum(score[metric_name] for score in scores) / len(scores)
        printable_name = metric_name.replace("_at_k", f"@{TOP_K}")
        print(f"{printable_name}: {mean_score:.3f}")


if __name__ == "__main__":
    asyncio.run(evaluate())
