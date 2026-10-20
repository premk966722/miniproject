from __future__ import annotations

from typing import Dict, Iterable


def reciprocal_rank_fusion(ranked_a: Iterable[str], ranked_b: Iterable[str], k: int = 60) -> Dict[str, float]:
    first = list(ranked_a)
    second = list(ranked_b)
    scores: Dict[str, float] = {}
    first_index = {item: idx for idx, item in enumerate(first)}
    second_index = {item: idx for idx, item in enumerate(second)}

    for rank, item in enumerate(first, start=1):
        scores[item] = scores.get(item, 0.0) + 1.0 / (k + rank)
    for rank, item in enumerate(second, start=1):
        scores[item] = scores.get(item, 0.0) + 0.5 / (k + rank)

    ordered = sorted(
        scores.items(),
        key=lambda item: (
            -item[1],
            first_index.get(item[0], len(first) + 1),
            second_index.get(item[0], len(second) + 1),
        ),
    )
    return dict(ordered)
