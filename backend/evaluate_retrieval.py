from __future__ import annotations

import argparse
import json
import statistics
import time
from pathlib import Path
from typing import Any, Callable, Dict, List

from app.db import init_db, list_index_documents
from app.retrieval.bm25_retriever import BM25Retriever
from app.retrieval.hybrid_retriever import HybridRetriever
from app.retrieval.vector_retriever import VectorRetriever


def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if line.strip():
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON on line {line_number} of {path}") from exc
    return rows


def _score(
    questions: List[Dict[str, Any]],
    retrieve: Callable[[str, str | None], List[Dict[str, Any]]],
    k: int = 5,
) -> Dict[str, Any]:
    recalls: List[float] = []
    reciprocal_ranks: List[float] = []
    latencies: List[float] = []
    covered = 0
    for case in questions:
        relevant = set(case.get("relevant_chunk_ids", []))
        if not relevant:
            continue
        started = time.perf_counter()
        hits = retrieve(case["question"], case.get("tax_period"))[:k]
        latencies.append((time.perf_counter() - started) * 1000)
        ids = [hit.get("chunk_id") for hit in hits]
        found = relevant.intersection(ids)
        recalls.append(len(found) / len(relevant))
        covered += bool(found)
        rank = next((i for i, chunk_id in enumerate(ids, start=1) if chunk_id in relevant), None)
        reciprocal_ranks.append(1.0 / rank if rank else 0.0)
    count = len(recalls)
    if not count:
        return {"annotated_questions": 0, "recall_at_5": None, "mrr": None, "mean_latency_ms": None, "questions_with_relevant_evidence_pct": None}
    return {
        "annotated_questions": count,
        "recall_at_5": sum(recalls) / count,
        "mrr": sum(reciprocal_ranks) / count,
        "mean_latency_ms": statistics.mean(latencies),
        "questions_with_relevant_evidence_pct": 100 * covered / count,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare TAX-SHIELD retrievers using manually annotated chunk IDs.")
    parser.add_argument("--benchmark", type=Path, default=Path(__file__).parent / "evaluation" / "benchmark.jsonl")
    parser.add_argument("--documents", type=Path, help="Optional JSONL corpus; otherwise use persisted indexed chunks.")
    args = parser.parse_args()
    questions = _read_jsonl(args.benchmark) if args.benchmark.exists() else []
    if args.documents:
        documents = _read_jsonl(args.documents)
    else:
        init_db()
        documents = list_index_documents()
    hybrid = HybridRetriever(documents)
    bm25 = BM25Retriever()
    bm25.index_documents(documents)
    vector = VectorRetriever()
    vector.index_documents(documents)

    methods = {
        "bm25_only": lambda question, period: bm25.search(question, top_k=5, tax_year=period),
        "vector_only": lambda question, period: vector.search(question, top_k=5, tax_year=period),
        "hybrid_rrf": lambda question, period: hybrid.search(question, tax_year=period, top_k=5),
        "hybrid_heuristic_rerank": lambda question, period: hybrid.search(question, tax_year=period, top_k=5, rerank=True),
    }
    output = {
        "benchmark_cases": len(questions),
        "documents": len(documents),
        "labelled_questions": sum(bool(row.get("relevant_chunk_ids")) for row in questions),
        "methods": {name: _score(questions, run) for name, run in methods.items()},
        "limitations": [
            "Metrics are meaningful only with independently reviewed relevant_chunk_ids and an actual indexed corpus.",
            "The vector implementation in this version uses a deterministic hash vector, not a trained semantic embedding model.",
            "The optional reranker is a lexical substring heuristic, not a learned cross-encoder.",
        ],
    }
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
