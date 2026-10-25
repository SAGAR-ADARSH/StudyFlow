"""Offline multiple-choice question generation from study text.

Every question is built from a sentence that actually appears in the source
document, so nothing is invented:

* ``cloze`` — a defined term or a content word in a quoted factual passage is
  blanked out. Alternatives come from definitions, named headings or prose in this source.
* ``definition`` — the term is named and the options are definitions taken from
  the document, only one of which belongs to that term.

A candidate is skipped when it cannot be turned into a well-formed question with
at least ``min_options`` distinct, grounded options.
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass, field
from itertools import pairwise

from app.services.summary_engine import STOPWORDS, tokenize

QUIZ_ENGINE_VERSION = "extractive-cloze-v2"
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
    r"^\s*(?P<term>[A-Z][A-Za-z0-9\-'&–—’]*(?:\s+[A-Za-z0-9][A-Za-z0-9\-'&–—’]*){0,5}?)\s+"
    r"(?P<verb>is defined as|is known as|is called|refers to|denotes|represents|describes|"
    r"measures|consists of|contains|includes|provides|supports|enables|uses|is|are)\s+"
    r"(?P<definition>.+)$",
    re.IGNORECASE,
)

# Slide text often has numbered bullets, Unicode dashes, and short wrapped lines.
_BULLET_RE = re.compile(r"^\s*(?:[•●▪◦*]\s*|\d{1,3}[.)]\s*(?=[A-Za-z]))")
_LABEL_RE = re.compile(
    r"^(?P<term>[A-Za-z][A-Za-z0-9’'&()–— -]{1,59}?)(?::\s+|\s+[–—-]\s+)(?P<definition>.+)$"
)
_FACT_VERBS = """
is are has have contains includes provides supports enables uses consists
represents describes measures denotes refers can must takes take stores store
requires require gives give keeps keep handles handle minimizes minimize ensures ensure
""".split()  # noqa: SIM905
_FACT_RE = re.compile(r"^.{2,80}?\b(?:" + "|".join(_FACT_VERBS) + r")\b\s+", re.IGNORECASE)
_CODE_RE = re.compile(
    r"^(?:#|//|/\*|\*/|[{}]|(?:struct|int|void|return)\b|(?:if|printf|scanf)\s*\()"
    r"|->|\w+\s*\([^)]*\)\s*;\s*$"
)
_ANSWER_RE = re.compile(r"\b[A-Za-z][A-Za-z0-9]*(?:[-–—’'][A-Za-z0-9]+)*\b")
_NOT_ANSWERS = (
    STOPWORDS
    | frozenset(_FACT_VERBS)
    | frozenset(
        """
always usually each every either neither least most much many several
some any only all then than such same more less known defined called used
following example figure table step determine follow find add return read
write program sample below above starting during overall therefore
because since unlike they this that these those there here
""".split()  # noqa: SIM905
    )
)


@dataclass(slots=True)
class SourceStatement:
    text: str
    position: int


def _source_statements(text: str, page_offsets: list[int] | None = None) -> list[SourceStatement]:
    """Rejoin wrapped prose without treating every short PDF line as a heading.

    Retain original offsets for page attribution. Never join across PDF pages or
    executable code, and never use code as a distractor pool.
    """
    boundaries = sorted({0, len(text), *(page_offsets or [])})
    statements = []

    def flush(buffer: list[str], position: int) -> None:
        if buffer:
            joined = " ".join(buffer)
            for sentence in re.split(r'(?<=[.!?])\s+(?=[A-Z"(\[])', joined):
                if 25 <= len(sentence) <= 600:
                    statements.append(SourceStatement(sentence, position))
            buffer.clear()

    for start, end in pairwise(boundaries):
        buffer = []
        buffer_start = start
        offset = start
        for raw in text[start:end].splitlines(keepends=True):
            stripped = raw.strip()
            line = _BULLET_RE.sub("", stripped).strip()
            position = offset
            offset += len(raw)
            if (
                not line
                or _CODE_RE.search(line)
                or re.search(r"https?://", line)
                or re.match(r"^[\[\]\\/|+]", line)
            ):
                flush(buffer, buffer_start)
                continue
            begins_fact = line[:1].isupper() and bool(_FACT_RE.match(line) or _LABEL_RE.match(line))
            if _BULLET_RE.match(stripped) or begins_fact or line.isupper():
                flush(buffer, buffer_start)
            if not buffer:
                buffer_start = position
            buffer.append(line)
            if line.endswith((".", "!", "?")):
                flush(buffer, buffer_start)
        flush(buffer, buffer_start)
    return statements


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
    if first_word in {
        "in",
        "on",
        "at",
        "by",
        "for",
        "with",
        "from",
        "as",
        "of",
        "to",
        "if",
        "when",
    }:
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

    statements = _source_statements(text, page_offsets)
    frequencies: dict[str, int] = {}
    for token in tokenize(text):
        frequencies[token] = frequencies.get(token, 0) + 1

    candidates: list[CandidateQuestion] = []
    seen_terms: set[str] = set()
    for statement in statements:
        sentence = statement.text
        match = _DEFINITION_RE.match(sentence)
        if not match:
            match = _LABEL_RE.match(sentence)
            # Labels must introduce a description, not steps, code, or formula headers.
            if match and not re.match(
                r"^(?:a|an|the|each|every)\b", match.group("definition"), re.IGNORECASE
            ):
                continue
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
        verb = _clean_verb(match.groupdict().get("verb") or "is")
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
                page=_page_for(page_offsets, statement.position),
            )
        )
    return candidates


def _heading_terms(text: str) -> list[str]:
    """Short, named slide headings may supply choices, never unproven questions."""
    terms = []
    for raw in text.splitlines():
        line = _BULLET_RE.sub("", raw.strip()).strip()
        if not re.fullmatch(r"[A-Za-z][A-Za-z’'&()–— -]{2,59}", line):
            continue
        words = line.split()
        if len(words) > 6 or _FACT_RE.match(line):
            continue
        if not all(w.isupper() or w.istitle() or w.lower() in STOPWORDS for w in words):
            continue
        term = _clean_term(line)
        if not term or term.split()[0].lower() in {
            "module",
            "chapter",
            "section",
            "working",
            "step",
            "program",
            "structure",
            "properties",
            "some",
            "final",
            "original",
            "sample",
            "graphs",
            "merits",
            "demerits",
        }:
            continue
        terms.append(term)
    return terms


def _similar_shape(reference: str, option: str) -> bool:
    reference_acronym = bool(_ACRONYM_RE.match(reference))
    option_acronym = bool(_ACRONYM_RE.match(option))
    if reference_acronym != option_acronym:
        return False
    return abs(len(reference) - len(option)) <= max(12, len(reference))


def _choice_key(value: str) -> str:
    """Avoid offering spelling/plural variants of the same term as alternatives."""
    key = re.sub(r"[^a-z0-9]", "", value.casefold())
    if len(key) > 4 and key.endswith("s") and not key.endswith(("ss", "is", "us")):
        key = key[:-1]
    return key


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
    seen_choices = {_choice_key(answer)}
    for option in pool:
        choice_key = _choice_key(option)
        if choice_key in seen_choices:
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
        seen_choices.add(choice_key)
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


def _passage_questions(
    text: str,
    *,
    page_offsets: list[int] | None,
    seed: int,
    used_sentences: set[str],
    used_answers: set[str],
    limit: int,
) -> tuple[list[GeneratedQuestion], int]:
    statements = [
        item
        for item in _source_statements(text, page_offsets)
        if _FACT_RE.match(item.text)
        and len(item.text) <= MAX_EXPLANATION_CHARS
        and item.text.count("(") == item.text.count(")")
        and "[" not in item.text
        and "]" not in item.text
        and len(item.text.split()) >= 8
        and item.text.split()[0].casefold().strip(",.:") not in _REJECTED_TERMS
        and item.text.split()[0].casefold().strip(",.:")
        not in {
            "this",
            "that",
            "they",
            "it",
            "since",
            "unlike",
            "so",
            "if",
            "when",
            "while",
            "step",
            "read",
            "write",
            "use",
            "follow",
            "determine",
            "find",
            "add",
            "return",
        }
    ]
    # Only extract options from usable prose, not code, titles, URLs or other students' data.
    frequencies = {}
    spellings = {}
    for statement in statements:
        for match in _ANSWER_RE.finditer(statement.text):
            token = match.group()
            key = token.casefold()
            if (
                len(token) >= 4
                and key not in _NOT_ANSWERS
                and not re.fullmatch(r"log[A-Za-z0-9]*", token)
            ):
                frequencies[key] = frequencies.get(key, 0) + 1
                spellings.setdefault(key, token)
    pool = list(spellings.values())
    statements.sort(
        key=lambda item: (
            not bool(_DEFINITION_RE.match(item.text)),
            not (8 <= len(item.text.split()) <= 50),
            -min(len(tokenize(item.text)), 28),
            item.position,
        )
    )
    questions = []
    for index, statement in enumerate(statements):
        if len(questions) >= limit:
            break
        if statement.text in used_sentences:
            continue
        words = {m.group().casefold() for m in _ANSWER_RE.finditer(statement.text)}
        answers = sorted(
            (word for word in words if word in spellings and word not in used_answers),
            key=lambda word: (-frequencies[word], -len(word), word),
        )
        for key in answers:
            answer = spellings[key]
            alternatives = _pick_distractors(answer, pool, statement.text, count=MAX_OPTIONS - 1)
            if len(alternatives) < MIN_OPTIONS - 1:
                continue
            # Mask every occurrence; never leave the answer visible in the prompt.
            prompt = re.sub(
                rf"(?<!\w){re.escape(answer)}(?!\w)",
                "________",
                statement.text,
                flags=re.IGNORECASE,
            )
            if prompt == statement.text:
                continue
            options, correct = _shuffle_options(
                answer, alternatives, seed=f"{seed}:passage:{index}"
            )
            questions.append(
                GeneratedQuestion(
                    question_type="cloze",
                    prompt=f"Complete the passage from the material: “{prompt}”",
                    options=options,
                    correct_index=correct,
                    explanation=f"Source: “{statement.text}”",
                    source_excerpt=statement.text,
                    source_page=_page_for(page_offsets, statement.position),
                )
            )
            used_sentences.add(statement.text)
            used_answers.add(key)
            break
    return questions, len(statements)


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
    ranked = sorted(candidates, key=lambda item: (-item.score, item.term.casefold()))
    term_pool = list(dict.fromkeys([candidate.term for candidate in ranked] + _heading_terms(text)))
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
                        f"Fill in the blank: ________ {candidate.verb} {candidate.definition}."
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
            picked = sorted(
                other_definitions,
                key=lambda item: (abs(len(item) - len(candidate.definition)), item),
            )
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

    if len(result.questions) < question_count:
        passages, passage_count = _passage_questions(
            text,
            page_offsets=page_offsets,
            seed=seed,
            used_sentences={q.source_excerpt for q in result.questions},
            used_answers={q.options[q.correct_index].casefold() for q in result.questions},
            limit=question_count - len(result.questions),
        )
        result.questions.extend(passages)
        result.candidates += passage_count
        if passages:
            warnings.append(
                "Some questions complete quoted source passages; their answer choices "
                "are terms found in this material, not generated facts."
            )

    if not result.questions:
        raise InsufficientContentError(
            "The readable text does not contain enough clear statements and distinct answer "
            "choices for a reliable quiz. Diagram-only or code-only slides cannot be interpreted "
            "by this local text-based generator. Try adding explanatory notes or a text-based handout.",
            code="not_enough_distractors" if candidates else "no_question_candidates",
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
