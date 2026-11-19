"""Internal selection of OCR process backends.

The legacy backend preserves the existing PaddleOCR command protocol. Additional
backends must explicitly implement this interface and prove their availability.
"""
from __future__ import annotations

import os
from typing import Callable, Iterator, Protocol


class OCRBackend(Protocol):
    name: str

    def run(self, args: list[str], extra_env: dict[str, str] | None = None) -> Iterator[str]: ...


class LegacyPaddleBackend:
    name = "legacy"

    def __init__(self, stream: Callable[..., Iterator[str]]) -> None:
        self._stream = stream

    def run(self, args: list[str], extra_env: dict[str, str] | None = None) -> Iterator[str]:
        return self._stream(args, "paddleocr_error.log", extra_env)


def discover_backends(paddleocr_path: str, stream: Callable[..., Iterator[str]]) -> dict[str, OCRBackend]:
    """List implemented backends whose prerequisites exist; no GPU probing."""
    if os.path.isfile(paddleocr_path):
        return {"legacy": LegacyPaddleBackend(stream)}
    return {}


def select_backend(backends: dict[str, OCRBackend], requested: str = "auto", *, allow_fallback: bool = False) -> OCRBackend:
    """Select an installed backend before processing; never retry partial jobs."""
    if requested == "auto":
        requested = "legacy"
    if requested in backends:
        return backends[requested]
    if allow_fallback and "legacy" in backends:
        return backends["legacy"]
    raise RuntimeError(f"OCR backend {requested!r} is unavailable; available: {', '.join(sorted(backends)) or 'none'}")
