import asyncio
import json
import os
from pathlib import Path

from dotenv import load_dotenv

from rag.evaluation import calculate_retrieval_metrics
from rag.utils import retrieve_documents

load_dotenv()

EVAL_DATASET = Path(os.getenv("RAG_EVAL_DATASET", "evaluation/rag_golden_set.jsonl"))
EVAL_USER_ID = os.getenv("RAG_EVAL_USER_ID")
EVAL_CONVERSATION_ID = os.getenv("RAG_EVAL_CONVERSATION_ID")
TOP_K = 5


async def evaluate():
    if not EVAL_USER_ID or not EVAL_CONVERSATION_ID:
        raise RuntimeError(
            "Set RAG_EVAL_USER_ID and RAG_EVAL_CONVERSATION_ID to a conversation "
            "containing the documents used by the evaluation dataset."
        )

    if not EVAL_DATASET.is_file():
        raise FileNotFoundError(f"Evaluation dataset not found: {EVAL_DATASET}")

    with EVAL_DATASET.open(encoding="utf-8") as dataset_file:
        cases = [json.loads(line) for line in dataset_file if line.strip()]

    if not cases:
        raise ValueError("The retrieval evaluation dataset is empty")

    scores = []
    for case in cases:
        query = case["query"]
        expected_sources = case["expected_sources"]
        results = await retrieve_documents(
            query,
            EVAL_USER_ID,
            EVAL_CONVERSATION_ID,
            limit=TOP_K,
        )
        scores.append(calculate_retrieval_metrics(results, expected_sources, TOP_K))

    recall = sum(score["recall_at_k"] for score in scores) / len(scores)
    mrr = sum(score["reciprocal_rank"] for score in scores) / len(scores)

    print(f"Queries evaluated: {len(scores)}")
    print(f"Recall@{TOP_K}: {recall:.3f}")
    print(f"MRR@{TOP_K}: {mrr:.3f}")


if __name__ == "__main__":
    asyncio.run(evaluate())
