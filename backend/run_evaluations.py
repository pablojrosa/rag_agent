"""Run the shared RAG pipeline against a Langfuse dataset."""
import argparse
import os
from datetime import datetime, timezone

from src.app.observability import get_client, flush
from src.app.rag_service import answer_question


def task(*, item, **kwargs):
    data = item.input if hasattr(item, "input") else item["input"]
    expected = item.expected_output if hasattr(item, "expected_output") else item.get("expected_output")
    return answer_question(data["question"], data.get("history", []), mode="offline", expected_output=expected)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", default=os.getenv("LANGFUSE_DATASET_NAME", "statistical-learning"))
    parser.add_argument("--name", default=None)
    parser.add_argument("--concurrency", type=int, default=2)
    parser.add_argument("--limit", type=int, default=None, help="Limit items for a smoke experiment.")
    args = parser.parse_args()
    if not 1 <= args.concurrency <= 20:
        parser.error("concurrency must be between 1 and 20")
    if args.limit is not None and args.limit < 1:
        parser.error("limit must be positive")
    client = get_client()
    if not client:
        parser.error("Configure Langfuse credentials first.")
    dataset = client.get_dataset(args.dataset)
    if not dataset.items:
        parser.error("The dataset is empty. Run create_golden_dataset.py first.")
    try:
        result = client.run_experiment(
            data=dataset.items[:args.limit] if args.limit else dataset.items,
            name=args.name or datetime.now(timezone.utc).strftime("rag-%Y%m%d-%H%M%S"),
            task=task, max_concurrency=args.concurrency,
            metadata={"model": os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
                      "prompt_version": os.getenv("PROMPT_VERSION", "1")})
        print(result.format())
        print("Scores are computed asynchronously by Langfuse observation rules. Refresh the dashboard later.")
    finally:
        flush()


if __name__ == "__main__":
    main()
