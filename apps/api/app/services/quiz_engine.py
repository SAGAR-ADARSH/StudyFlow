"""Offline multiple-choice question generation from study text.

Every question is built from a sentence that actually appears in the source
document, so nothing is invented:

* ``cloze`` — the defined term is blanked out and the distractors are other
  terms defined in the same document.
* ``definition`` — the term is named and the options are definitions taken from
  the document, only one of which belongs to that term.

A candidate is skipped when it cannot be turned into a well-formed question with
at least ``min_options`` distinct, grounded options.
"""
from __future__ import annotations

import random
import re
from dataclasses import dataclass, field

from app.services.summary_engine import STOPWORDS, split_sentences, tokenize

QUIZ_ENGINE_VERSION = "extractive-cloze-v1"
QUIZ_METHOD = "extractive-cloze"

MIN_SOURCE_CHARS = 200
MIN_OPTIONS = 3
MAX_OPTIONS = 4
MAX_DEFINITION_CHARS = 220
MAX_EXPLANATION_CHARS = 320

_LEAD_ARTICLES = re.compile(r"^(a|an|the)\s+", re.IGNORECASE)
_ACRONYM_RE = re.compile(r"^[A-Z]{2,}(?:s)?$")
_WORD_RE = re.compile(r"[A-Za-z][A-Za-z'\-]{1,}")

# "Breadth First Search is a graph traversal algorithm that ..."
_DEFINITION_RE = re.compile(
    r"^\s*(?P<term>[A-Z][A-Za-z0-9][A-Za-z0-9\-'&]*(?:\s+[A-Za-z0-9][A-Za-z0-9\-'&]*){0,5}?)\s+"
    r"(?P<verb>is defined as|is known as|is called|refers to|denotes|represents|describes|"
    r"measures|consists of|contains|includes|provides|supports|enables|uses|is|are)\s+"
    r"(?P<definition>.+)$",
    re.IGNORECASE,
)

_REJECTED_TERMS = frozenset(
    """
it this that these those there here he she they we you i figure table chapter section note
example above below following first second third however therefore also thus one two three
""".split()  # noqa: SIM905
)


class InsufficientContentError(ValueError):
    """Raised when the source text cannot support a quiz."""

    def __init__(self, message: str, code: str = "insufficient_content") -> None:
        super().__init__(message)
        self.code = code


@dataclass(slots=True)
class CandidateQuestion:
    term: str
    verb: str
    definition: str
    sentence: str
    frequency: int
    score: float
    page: int | None = None


@dataclass(slots=True)
class GeneratedQuestion:
    question_type: str
    prompt: str
    options: list[str]
    correct_index: int
    explanation: str
    source_excerpt: str
    source_page: int | None


@dataclass(slots=True)
class QuizResult:
    questions: list[GeneratedQuestion] = field(default_factory=list)
    candidates: int = 0
    source_chars: int = 0
    skipped: int = 0
    warnings: list[str] = field(default_factory=list)


def _clean_term(term: str) -> str | None:
    term = _LEAD_ARTICLES.sub("", term.strip())
    term = term.strip(" ,:;()\"'")
    if len(term) < 3 or len(term) > 60:
        return None
    if term.lower() in STOPWORDS or term.lower() in _REJECTED_TERMS:
        return None
    if not re.search(r"[A-Za-z]{3,}", term):
        return None
    # Reject fragments such as "In this" or "For example".
    first_word = term.split()[0].lower()
    if first_word in {"in", "on", "at", "by", "for", "with", "from", "as", "of", "to", "if", "when"}:
        return None
    return term


def _clean_verb(verb: str) -> str:
    """Normalize the linking verb so the cloze reads like the source sentence."""
    verb = verb.strip().lower()
    return "is" if verb in {"is defined as", "is known as", "is called", "is"} else verb


def _clean_definition(definition: str) -> str | None:
    definition = definition.strip().strip('"')
    # Keep only the leading clause of the sentence.
    definition = re.split(r"(?<=[a-z0-9])\s+[;:]\s+", definition)[0]
    if len(definition) > MAX_DEFINITION_CHARS:
        cut = definition[:MAX_DEFINITION_CHARS].rsplit(" ", 1)[0]
        definition = f"{cut}…"
    words = definition.split()
    if len(words) < 5:
        return None
    return definition.rstrip(".")


def _page_for(page_offsets: list[int] | None, index: int) -> int | None:
    if not page_offsets:
        return None
    page = 1
    for position, offset in enumerate(page_offsets):
        if offset <= index:
            page = position + 1
        else:
            break
    return page


def collect_candidates(
    text: str,
    *,
    page_offsets: list[int] | None = None,
) -> list[CandidateQuestion]:
    """Find term/definition pairs worth turning into questions."""
    if not text or len(text.strip()) < MIN_SOURCE_CHARS:
        return []

    sentences = split_sentences(text)
    frequencies: dict[str, int] = {}
    for token in tokenize(text):
        frequencies[token] = frequencies.get(token, 0) + 1

    candidates: list[CandidateQuestion] = []
    seen_terms: set[str] = set()
    offset = 0
    for sentence in sentences:
        position = text.find(sentence[:60], offset)
        if position != -1:
            offset = position
        match = _DEFINITION_RE.match(sentence)
        if not match:
            continue
        term = _clean_term(match.group("term"))
        definition = _clean_definition(match.group("definition"))
        if not term or not definition:
            continue

        key = term.casefold()
        if key in seen_terms:
            continue
        # A definition that repeats the term gives the answer away.
        if re.search(rf"\b{re.escape(key)}\b", definition, re.IGNORECASE):
            continue
        if re.search(rf"\b{re.escape(term)}\b", definition, re.IGNORECASE):
            continue

        seen_terms.add(key)
        verb = _clean_verb(match.group("verb"))
        frequency = frequencies.get(key.split()[0].lower(), 1)
        score = float(min(frequency, 12))
        if _ACRONYM_RE.match(term):
            score += 3.0
        if 8 <= len(definition.split()) <= 26:
            score += 2.0
        if term[:1].isupper():
            score += 0.5
        candidates.append(
            CandidateQuestion(
                term=term,
                verb=verb,
                definition=definition,
                sentence=sentence,
                frequency=frequency,
                score=score,
                page=_page_for(page_offsets, position if position != -1 else 0),
            )
        )
    return candidates


def _similar_shape(reference: str, option: str) -> bool:
    reference_acronym = bool(_ACRONYM_RE.match(reference))
    option_acronym = bool(_ACRONYM_RE.match(option))
    if reference_acronym != option_acronym:
        return False
    return abs(len(reference) - len(option)) <= max(12, len(reference))


def _pick_distractors(
    answer: str,
    pool: list[str],
    sentence: str,
    *,
    count: int,
) -> list[str]:
    sentence_lower = sentence.lower()
    answer_words = {word for word in _WORD_RE.findall(answer.lower()) if len(word) > 3}
    scored: list[tuple[float, str]] = []
    for option in pool:
        if option.casefold() == answer.casefold():
            continue
        if option.casefold() in sentence_lower:
            continue
        option_words = {word for word in _WORD_RE.findall(option.lower()) if len(word) > 3}
        # Never offer an option that is a substring of (or contains) the answer.
        if option.casefold() in answer.casefold() or answer.casefold() in option.casefold():
            continue
        if option_words & answer_words:
            continue
        score = 1.0 if _similar_shape(answer, option) else 0.0
        score += 0.25 if len(option.split()) == len(answer.split()) else 0.0
        scored.append((score, option))

    scored.sort(key=lambda item: (-item[0], item[1]))
    return [option for _, option in scored[:count]]


def _shuffle_options(correct: str, distractors: list[str], *, seed: str) -> tuple[list[str], int]:
    options = [correct, *distractors]
    rng = random.Random(seed)
    rng.shuffle(options)
    return options, options.index(correct)


def _trim_explanation(sentence: str) -> str:
    if len(sentence) <= MAX_EXPLANATION_CHARS:
        return sentence
    return f"{sentence[:MAX_EXPLANATION_CHARS].rsplit(' ', 1)[0]}…"


def generate_questions(
    text: str,
    *,
    question_count: int = 5,
    page_offsets: list[int] | None = None,
    seed: int = 0,
) -> QuizResult:
    """Generate up to ``question_count`` grounded multiple-choice questions."""
    source_chars = len(text or "")
    candidates = collect_candidates(text, page_offsets=page_offsets)
    result = QuizResult(candidates=len(candidates), source_chars=source_chars)

    if source_chars < MIN_SOURCE_CHARS:
        raise InsufficientContentError(
            "This document has too little readable text to build a quiz. "
            "Upload a text-based PDF with at least a couple of paragraphs.",
            code="insufficient_text",
        )
    if not candidates:
        raise InsufficientContentError(
            "No clear definition-style statements were found in this document, so a reliable "
            "quiz cannot be generated without inventing facts.",
            code="no_question_candidates",
        )

    ranked = sorted(candidates, key=lambda item: (-item.score, item.term.casefold()))
    term_pool = [candidate.term for candidate in ranked]
    definition_pool = {candidate.term: candidate.definition for candidate in ranked}
    warnings: list[str] = []

    for index, candidate in enumerate(ranked):
        if len(result.questions) >= question_count:
            break

        distractors = _pick_distractors(
            candidate.term,
            term_pool,
            candidate.sentence,
            count=MAX_OPTIONS - 1,
        )
        if len(distractors) >= MIN_OPTIONS - 1:
            options, correct_index = _shuffle_options(
                candidate.term,
                distractors[: MAX_OPTIONS - 1],
                seed=f"{seed}:cloze:{index}",
            )
            result.questions.append(
                GeneratedQuestion(
                    question_type="cloze",
                    prompt=(
                        f"Fill in the blank: ________ {candidate.verb} "
                        f"{candidate.definition}."
                    ),
                    options=options,
                    correct_index=correct_index,
                    explanation=(
                        f"{candidate.term} {candidate.verb} {candidate.definition}. "
                        f"Source: “{_trim_explanation(candidate.sentence)}”"
                    ),
                    source_excerpt=_trim_explanation(candidate.sentence),
                    source_page=candidate.page,
                )
            )
            continue

        # Not enough comparable terms: fall back to a definition-matching question.
        other_definitions = [
            definition
            for term, definition in definition_pool.items()
            if term != candidate.term
            and definition.casefold() not in candidate.sentence.lower()
            and not _same_first_words(definition, candidate.definition)
        ]
        if len(other_definitions) >= MIN_OPTIONS - 1:
            picked = sorted(other_definitions, key=lambda item: (abs(len(item) - len(candidate.definition)), item))
            options, correct_index = _shuffle_options(
                candidate.definition,
                picked[: MAX_OPTIONS - 1],
                seed=f"{seed}:definition:{index}",
            )
            result.questions.append(
                GeneratedQuestion(
                    question_type="definition",
                    prompt=f"Which statement best describes {candidate.term}?",
                    options=options,
                    correct_index=correct_index,
                    explanation=(
                        f"{candidate.term} {candidate.verb} {candidate.definition}. "
                        f"Source: “{_trim_explanation(candidate.sentence)}”"
                    ),
                    source_excerpt=_trim_explanation(candidate.sentence),
                    source_page=candidate.page,
                )
            )
            continue

        result.skipped += 1

    if not result.questions:
        raise InsufficientContentError(
            "The document mentions too few comparable terms to build four-option questions. "
            "Upload a longer or more definition-rich PDF.",
            code="not_enough_distractors",
        )

    if len(result.questions) < question_count:
        warnings.append(
            f"Only {len(result.questions)} reliable question(s) could be generated "
            f"from this document instead of {question_count}."
        )
    result.warnings = warnings
    return result


def _same_first_words(left: str, right: str, count: int = 3) -> bool:
    return left.split()[:count] == right.split()[:count]
