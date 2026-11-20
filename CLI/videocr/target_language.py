"""Choose subtitle regions for bilingual English/Chinese frames in the AMD desktop."""
from __future__ import annotations

import re
import unicodedata
from dataclasses import replace
from functools import lru_cache
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import PredictedText


SUPPORTED_LANGUAGES = ('en', 'ch', 'chinese_cht')
# Boundaries between complete translations. An ordinary space may separate a name.
_BOUNDARY = re.compile(r'\s+[|/／]\s+|\s*[|｜]\s*|\s{2,}|(?<=[.!?。！？])\s*(?=[^\s\d.!?。！？])')
_LABEL = re.compile(r'(?:previously on|previously|next episode preview|episode preview|'
                    r'上集回[顾顧]|前情提要|前情回[顧顾]|下集[预預]告|片尾字幕|'
                    r'[导導]演|制片人|[监監]制|[总總][监監]制|[总總]策[划劃]|出品方)[.!:：。…]*', re.I)
_ROLE = re.compile(r'(?:directed by|produced by|executive producer|animation director|'
                   r'[导導]演|[监監]制|[总總][监監]制|制片人)(?:\s*[:：]\s*|\s+)\S', re.I)


@lru_cache(maxsize=4096)
def script(char: str) -> str:
    name = unicodedata.name(char, '')
    if name.startswith(('CJK UNIFIED IDEOGRAPH', 'CJK COMPATIBILITY IDEOGRAPH')) or char == '〇':
        return 'han'
    if char.isalpha() and 'LATIN' in name:
        return 'latin'
    return ''


@lru_cache(maxsize=2048)
def host(text: str) -> str:
    letters = [kind for ch in text if (kind := script(ch))]
    if not letters:
        return 'other' if any(ch.isalpha() for ch in text) else ''
    if letters[0] == letters[-1]:
        return letters[0]
    # Latin names/acronyms in Chinese vs. an English phrase ending in a Chinese name.
    latin_words = re.findall(r'[^\W\d_]+', ''.join(ch if script(ch) == 'latin' else ' ' for ch in text))
    return 'latin' if len(latin_words) >= 3 else 'han'


def split_long_bilingual_region(text: str) -> list[str]:
    """OCR can join a caption to a long, overlapping title card without a space."""
    letters = [(i, kind) for i, ch in enumerate(text) if (kind := script(ch))]
    changes = [i for i in range(1, len(letters)) if letters[i][1] != letters[i - 1][1]]
    if len(changes) != 1:
        return [text]
    change = changes[0]
    before, after = letters[change - 1][0] + 1, letters[change][0]
    # Keep an opening bracket/quote with the following phrase.
    while after > before and text[after - 1] in ' ([（【“‘':
        after -= 1
    parts = [text[:after].strip(), text[after:].strip()]
    han, latin = parts if letters[0][1] == 'han' else parts[::-1]
    # Short foreign spans, acronyms and names stay in the host sentence.
    if (sum(script(ch) == 'han' for ch in han) >= 7
            and sum(script(ch) == 'latin' for ch in latin) >= 12
            and (len(latin.split()) >= 2 or latin.startswith(('(', '（')))):
        return parts
    return [text]


def is_mixed_script(text: str) -> bool:
    return any(script(ch) == 'han' for ch in text) and any(script(ch) == 'latin' for ch in text)


def select_region(text: str, target: str) -> str:
    text = text.strip()
    if not text or _LABEL.fullmatch(text) or _ROLE.match(text):
        return ''
    if not is_mixed_script(text):
        return text if host(text) == target else ''
    boundaries = list(_BOUNDARY.finditer(text))
    start = 0
    spans = []
    for i, boundary in enumerate(boundaries):
        end = boundaries[i + 1].start() if i + 1 < len(boundaries) else len(text)
        before = text[start:boundary.start()]
        after = text[boundary.end():end]
        first, second = host(before), host(after)
        if {first, second} == {'han', 'latin'}:
            spans.append(before)
            start = boundary.end()
    spans.append(text[start:])
    phrases = [part for span in spans for part in split_long_bilingual_region(span)]
    return ' '.join(span.strip() for span in phrases if host(span) == target
                    and not _LABEL.fullmatch(span.strip()) and not _ROLE.match(span.strip()))


def bounds(word: PredictedText) -> tuple[float, float, float, float]:
    xs, ys = zip(*word.bounding_box)
    return min(xs), min(ys), max(xs), max(ys)


def paired_columns(lines: list[list[PredictedText]]) -> list[tuple[float, float]]:
    """Locate vertically neighboring, horizontally aligned bilingual captions."""
    boxes = [(bounds(word), host(word.text)) for line in lines for word in line
             if not _LABEL.fullmatch(word.text.strip()) and not _ROLE.match(word.text.strip())]
    anchors = []
    for left, top, right, bottom in (box for box, kind in boxes if kind == 'latin'):
        for (x1, y1, x2, y2), kind in boxes:
            if kind != 'han':
                continue
            height = max(bottom - top, y2 - y1, 1)
            gap = max(y1 - bottom, top - y2)
            if (-height / 3 <= gap <= 1.5 * height
                    and abs((left + right - x1 - x2) / 2) <= max(height * 2, (right - left + x2 - x1) / 6)):
                anchors.append((min(left, x1) - height, max(right, x2) + height))
    return anchors


def is_vertical_column(word: PredictedText) -> bool:
    left, top, right, bottom = bounds(word)
    return bottom - top > 2 * max(1, right - left) and sum(c.isalpha() for c in word.text) >= 3


def select_lines(lines: list[list[PredictedText]], lang: str) -> list[list[PredictedText]]:
    target = 'latin' if lang == 'en' else 'han'
    # Scrolling credits can appear as a bank of upright columns. Suppress only those
    # columns and keep horizontal dialogue in the same frame.
    vertical = [word for line in lines for word in line if is_vertical_column(word)]
    if len({bounds(word)[0] for word in vertical}) >= 3:
        lines = [[word for word in line if not is_vertical_column(word)] for line in lines]
    columns = paired_columns(lines)
    selected = []
    for line in lines:
        words = []
        for word in line:
            left, _, right, _ = bounds(word)
            if columns and not any(left <= end and right >= start for start, end in columns):
                continue
            words.append(word)
        texts = [select_region(word.text, target) for word in words]
        kinds = [host(word.text) for word in words]
        # A short name can be recognized as a separate box inside one sentence.
        for i in range(1, len(words) - 1):
            surrounding = kinds[i - 1]
            if (surrounding in ('han', 'latin') and surrounding == kinds[i + 1]
                    and kinds[i] in ('han', 'latin') and kinds[i] != surrounding):
                left, top, right, bottom = bounds(words[i])
                if (max(left - bounds(words[i - 1])[2], bounds(words[i + 1])[0] - right) <= bottom - top
                        and sum(ch.isalpha() for ch in words[i].text) <= 6
                        and not any(ch in '.!?。！？' for ch in words[i].text)):
                    texts[i] = words[i].text if surrounding == target else ''
        for i, word in enumerate(words):
            if kinds[i] or not word.text.strip():
                continue
            # Assign a detached number or punctuation mark to its nearest scripted box.
            left, _, right, _ = bounds(word)
            neighbors = [(max(0, bounds(w)[0] - right, left - bounds(w)[2]), j)
                         for j, w in enumerate(words) if kinds[j]]
            if neighbors:
                if texts[min(neighbors)[1]]:
                    texts[i] = word.text
            elif any(ch.isdigit() for ch in word.text) or word.text in ('…', '……', '...'):
                texts[i] = word.text
        kept = [replace(word, text=text) if word.text != text else word
                for word, text in zip(words, texts) if text]
        if kept:
            selected.append(kept)
    return selected
