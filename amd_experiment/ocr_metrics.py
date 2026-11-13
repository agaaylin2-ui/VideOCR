"""Metrics for comparing subtitle OCR results; no GPU claims are inferred."""
from __future__ import annotations

import unicodedata
from typing import Any


def normalize(text: str) -> str:
    return unicodedata.normalize("NFC", " ".join(text.split()))


def edit_distance(reference: str, hypothesis: str) -> int:
    previous = list(range(len(hypothesis) + 1))
    for i, left in enumerate(reference, 1):
        current = [i]
        for j, right in enumerate(hypothesis, 1):
            current.append(min(current[-1] + 1, previous[j] + 1, previous[j - 1] + (left != right)))
        previous = current
    return previous[-1]


def character_error_rate(reference: str, hypothesis: str) -> float | None:
    reference, hypothesis = normalize(reference), normalize(hypothesis)
    if not reference:
        return None
    return edit_distance(reference, hypothesis) / len(reference)


def bounds(poly: list[list[float]]) -> tuple[float, float, float, float]:
    if len(poly) < 3:
        raise ValueError("A polygon needs at least three points")
    return (min(p[0] for p in poly), min(p[1] for p in poly), max(p[0] for p in poly), max(p[1] for p in poly))


def box_iou(first: list[list[float]], second: list[list[float]]) -> float:
    ax1, ay1, ax2, ay2 = bounds(first)
    bx1, by1, bx2, by2 = bounds(second)
    intersection = max(0.0, min(ax2, bx2) - max(ax1, bx1)) * max(0.0, min(ay2, by2) - max(ay1, by1))
    union = (ax2 - ax1) * (ay2 - ay1) + (bx2 - bx1) * (by2 - by1) - intersection
    return intersection / union if union > 0 else 0.0


def match_boxes(reference: list[dict[str, Any]], candidate: list[dict[str, Any]], threshold: float = 0.5) -> dict[str, Any]:
    """Greedy one-to-one matching by descending axis-aligned IoU."""
    pairs = sorted(((box_iou(a['polygon'], b['polygon']), i, j) for i, a in enumerate(reference) for j, b in enumerate(candidate)), reverse=True)
    used_a: set[int] = set()
    used_b: set[int] = set()
    matches = []
    for overlap, i, j in pairs:
        if overlap < threshold:
            break
        if i not in used_a and j not in used_b:
            used_a.add(i)
            used_b.add(j)
            matches.append({'reference_index': i, 'candidate_index': j, 'iou': overlap, 'text_equal': normalize(reference[i]['text']) == normalize(candidate[j]['text']), 'confidence_delta': candidate[j]['confidence'] - reference[i]['confidence']})
    return {'matches': matches, 'missing_reference': [i for i in range(len(reference)) if i not in used_a], 'extra_candidate': [i for i in range(len(candidate)) if i not in used_b], 'iou_method': 'axis-aligned bounding rectangles', 'iou_threshold': threshold}
