"""Pure-Python, offline extractive summarizer.

No network access, no model download and no API key: the summarizer scores the
sentences of a document with a TF-IDF style heuristic, keeps the most central
ones, and rebuilds them in the original reading order. Long documents are split
into sentence-boundary chunks first so that every part of the paper is
represented in the final summary.
"""
from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass, field

SUMMARY_ENGINE_VERSION = "extractive-v1"
SUMMARY_METHOD = "extractive"

DEFAULT_MAX_WORDS = 220
DEFAULT_MAX_KEY_POINTS = 6
CHUNK_MAX_CHARS = 3_200
# A line shorter than this that carries no end punctuation is treated as a heading.
HEADING_LINE_CHARS = 62
MIN_SENTENCE_CHARS = 25
MAX_SENTENCE_CHARS = 420
# A summary may reuse at most this fraction of the source sentences.
MAX_SOURCE_REUSE = 0.6

_WORD_RE = re.compile(r"[A-Za-z][A-Za-z'\-]{1,}")
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[\"'(\[A-Z0-9])")

STOPWORDS = frozenset(
    """
a about above after again against all also am an and any are as at be because been before being
below between both but by can cannot could did do does doing down during each few for from further
had has have having he her here hers herself him himself his how i if in into is it its itself
just me more most much must my myself no nor not of off on once one only or other our ours
ourselves out over own same she should so some such than that the their theirs them themselves
then there these they this those through to too under until up very was we were what when where
which while who whom why will with within without would you your yours yourself yourselves it's
don't doesn't isn't aren't can't won't however therefore thus e.g i.e etc via per upon among
""".split()  # noqa: SIM905
)


@dataclass(slots=True)
class SummaryResult:
    """Output of a summarization run."""

    summary_text: str
    key_points: list[str]
    method: str = SUMMARY_METHOD
    engine_version: str = SUMMARY_ENGINE_VERSION
    source_chars: int = 0
    source_sentences: int = 0
    chunk_count: int = 0
    selected_sentences: int = 0
    word_count: int = 0
    warnings: list[str] = field(default_factory=list)


def _split_block(block: str) -> list[str]:
    """Rejoin wrapped PDF lines, keeping short lines (headings) as their own segment."""
    segments: list[str] = []
    buffer: list[str] = []
    for raw_line in block.split("\n"):
        line = raw_line.strip()
        if not line:
            continue
        if buffer and len(buffer[-1]) < HEADING_LINE_CHARS and not buffer[-1].endswith((",", "-")):
            segments.append(" ".join(buffer))
            buffer = []
        buffer.append(line)
    if buffer:
        segments.append(" ".join(buffer))
    return segments


def split_sentences(text: str) -> list[str]:
    """Split raw text into readable sentences, dropping fragments."""
    cleaned = re.sub(r"[ \t\r\f\v]+", " ", text.replace("\r\n", "\n").replace("\r", "\n"))
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    raw_sentences: list[str] = []
    for block in cleaned.split("\n\n"):
        for segment in _split_block(block):
            for candidate in _SENTENCE_SPLIT_RE.split(segment):
                sentence = candidate.strip(" \t-•*")
                if len(sentence) >= MIN_SENTENCE_CHARS and any(ch.isalpha() for ch in sentence):
                    raw_sentences.append(sentence[:MAX_SENTENCE_CHARS])
    return raw_sentences


def tokenize(sentence: str) -> list[str]:
    return [
        word.lower()
        for word in _WORD_RE.findall(sentence)
        if len(word) > 2 and word.lower() not in STOPWORDS
    ]


def chunk_sentences(sentences: list[str], max_chars: int = CHUNK_MAX_CHARS) -> list[list[str]]:
    """Group sentences into chunks that stay under ``max_chars`` without splitting one."""
    chunks: list[list[str]] = []
    current: list[str] = []
    current_size = 0
    for sentence in sentences:
        if current and current_size + len(sentence) > max_chars:
            chunks.append(current)
            current = []
            current_size = 0
        current.append(sentence)
        current_size += len(sentence) + 1
    if current:
        chunks.append(current)
    return chunks


def _score_sentences(
    sentences: list[str],
    document_frequencies: Counter[str],
    chunk_count: int,
    document_position: int,
) -> list[tuple[float, str, int]]:
    max_tf = 1
    token_cache = [tokenize(sentence) for sentence in sentences]
    for tokens in token_cache:
        if tokens:
            max_tf = max(max_tf, max(Counter(tokens).values()))

    scored: list[tuple[float, str, int]] = []
    for offset, (sentence, tokens) in enumerate(zip(sentences, token_cache)):
        if not tokens:
            continue
        counts = Counter(tokens)
        score = 0.0
        for token, count in counts.items():
            idf = math.log((1 + chunk_count) / (1 + document_frequencies.get(token, 0))) + 1.0
            score += idf * (count / max_tf)
        score /= math.sqrt(len(tokens))

        # Earlier sentences carry more of the author's framing.
        if document_position + offset == 0:
            score *= 1.35
        elif offset < 2:
            score *= 1.15
        if len(tokens) < 7:
            score *= 0.7
        if len(tokens) > 45:
            score *= 0.75
        # A sentence that defines a proper noun is usually worth keeping.
        if re.search(r"\b[A-Z][a-z]{2,}\b", sentence):
            score *= 1.08
        # Heading-like fragments carry no full thought.
        if not sentence.endswith((".", "!", "?")):
            score *= 0.55
        scored.append((score, sentence, document_position + offset))
    return scored


def summarize(
    text: str,
    *,
    max_words: int = DEFAULT_MAX_WORDS,
    max_key_points: int = DEFAULT_MAX_KEY_POINTS,
) -> SummaryResult:
    """Build an extractive summary of ``text``.

    Returns a :class:`SummaryResult`; ``summary_text`` is empty when the source
    holds no usable sentence, so callers can turn that into a clear error.
    """
    source_chars = len(text or "")
    sentences = split_sentences(text or "")
    warnings: list[str] = []
    if not sentences:
        return SummaryResult(
            summary_text="",
            key_points=[],
            source_chars=source_chars,
            source_sentences=0,
            chunk_count=0,
            warnings=["No complete sentence could be extracted from this text."],
        )

    chunks = chunk_sentences(sentences)
    chunk_count = len(chunks)

    document_frequencies: Counter[str] = Counter()
    chunk_tokens: list[list[list[str]]] = []
    for chunk in chunks:
        per_sentence = [tokenize(sentence) for sentence in chunk]
        chunk_tokens.append(per_sentence)
        seen: set[str] = set()
        for tokens in per_sentence:
            seen.update(tokens)
        document_frequencies.update(seen)

    # Budget the summary in words, then spread the sentence quota across chunks so
    # that the later pages of a long document are represented too.
    total_words = sum(len(sentence.split()) for sentence in sentences) or 1
    average_words = total_words / len(sentences)
    budget_sentences = max(1, math.floor(max_words / average_words))
    # Never hand back the whole document: cap how much of it may be reused.
    sentence_cap = min(budget_sentences, max(2, math.ceil(len(sentences) * MAX_SOURCE_REUSE)))
    remaining_words = max_words
    remaining_sentences = sentence_cap
    position = 0
    scored_all: list[tuple[float, str, int]] = []
    selected_by_chunk: list[list[str]] = []
    for index, chunk in enumerate(chunks):
        scored = _score_sentences(chunk, document_frequencies, chunk_count, position)
        scored_all.extend(scored)
        chunk_words = sum(len(sentence.split()) for sentence in chunk)
        chunk_quota = max(1, math.ceil(sentence_cap * chunk_words / total_words))
        chunk_quota = min(chunk_quota, len(scored), remaining_sentences)
        if chunk_quota <= 0 or remaining_words <= 0:
            position += len(chunk)
            continue
        best = sorted(scored, key=lambda item: (-item[0], item[2]))[:chunk_quota]
        # Drop the weakest sentences until the chunk fits what is left of the budget.
        while len(best) > 1 and sum(len(item[1].split()) for item in best) > remaining_words:
            best.pop()
        used_words = sum(len(item[1].split()) for item in best)
        remaining_words -= used_words
        remaining_sentences -= len(best)
        best.sort(key=lambda item: item[2])
        selected_by_chunk.append([item[1] for item in best])
        position += len(chunk)

    paragraphs: list[str] = []
    selected: list[str] = []
    seen_keys: set[str] = set()
    for chunk_sentences_selected in selected_by_chunk:
        kept: list[str] = []
        for sentence in chunk_sentences_selected:
            key = re.sub(r"\W+", " ", sentence.lower()).strip()
            if key in seen_keys:
                continue
            seen_keys.add(key)
            kept.append(sentence)
            selected.append(sentence)
        if kept:
            paragraphs.append(" ".join(kept))

    if not paragraphs:
        return SummaryResult(
            summary_text="",
            key_points=[],
            source_chars=source_chars,
            source_sentences=len(sentences),
            chunk_count=chunk_count,
            warnings=["Every candidate sentence was a duplicate of another one."],
        )

    summary_text = "\n\n".join(paragraphs)

    # Key points: short, information-dense sentences that made the cut.
    ranked = sorted(
        scored_all,
        key=lambda item: (-item[0], item[2]),
    )
    key_points: list[str] = []
    seen_points: set[str] = set()
    for _, sentence, _ in ranked:
        words = len(sentence.split())
        if words < 8 or words > 32:
            continue
        key = re.sub(r"\W+", " ", sentence.lower()).strip()
        if key in seen_points:
            continue
        seen_points.add(key)
        key_points.append(sentence if sentence.endswith((".", "!", "?")) else f"{sentence}.")
        if len(key_points) >= max_key_points:
            break
    if not key_points and selected:
        key_points = [selected[0]]

    if len(selected) < 3:
        warnings.append("The source text is short, so the summary keeps most of its sentences.")
    if source_chars > 0 and len(summary_text) / source_chars > 0.75:
        warnings.append("The document is short; the summary is close to the original length.")

    return SummaryResult(
        summary_text=summary_text,
        key_points=key_points,
        source_chars=source_chars,
        source_sentences=len(sentences),
        chunk_count=chunk_count,
        selected_sentences=len(selected),
        word_count=len(summary_text.split()),
        warnings=warnings,
    )
