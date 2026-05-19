"""RAGAS offline evaluation script for RAG quality assessment."""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.core.config import settings
from app.core.rag_chain import retrieve_documents, rag_query


SAMPLE_QA_PAIRS = [
    {"question": "请概述本文档的主要内容", "ground_truth": ""},
]


async def evaluate(kb_id: int, qa_file: str | None = None):
    """Run RAGAS evaluation on a knowledge base."""
    try:
        from ragas import evaluate as ragas_evaluate
        from ragas.metrics import faithfulness, answer_relevancy, context_precision, context_recall
        from datasets import Dataset
    except ImportError:
        print("Please install ragas and datasets: pip install ragas datasets")
        return

    if qa_file and Path(qa_file).exists():
        with open(qa_file, "r", encoding="utf-8") as f:
            qa_pairs = json.load(f)
    else:
        qa_pairs = SAMPLE_QA_PAIRS
        print("Using sample QA pairs. Provide a JSON file for real evaluation.")

    questions = []
    answers = []
    contexts = []
    ground_truths = []

    for pair in qa_pairs:
        question = pair["question"]
        ground_truth = pair.get("ground_truth", "")

        print(f"\nProcessing: {question}")
        result = await rag_query(kb_id, question)
        retrieved_docs = retrieve_documents(kb_id, question)

        questions.append(question)
        answers.append(result["answer"])
        contexts.append([doc.page_content for doc in retrieved_docs])
        ground_truths.append(ground_truth)

    dataset = Dataset.from_dict({
        "question": questions,
        "answer": answers,
        "contexts": contexts,
        "ground_truth": ground_truths,
    })

    metrics = [faithfulness, answer_relevancy, context_precision]
    if any(ground_truths):
        metrics.append(context_recall)

    print("\nRunning RAGAS evaluation...")
    result = ragas_evaluate(dataset, metrics=metrics)

    print("\n=== RAGAS Evaluation Results ===")
    for metric_name, score in result.items():
        print(f"  {metric_name}: {score:.4f}")

    output_path = Path("data") / f"ragas_report_kb{kb_id}.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(dict(result), f, ensure_ascii=False, indent=2)
    print(f"\nReport saved to {output_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run_ragas_eval.py <kb_id> [qa_pairs.json]")
        sys.exit(1)

    target_kb_id = int(sys.argv[1])
    qa_file_path = sys.argv[2] if len(sys.argv) > 2 else None
    asyncio.run(evaluate(target_kb_id, qa_file_path))
