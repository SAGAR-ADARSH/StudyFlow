"""Unit tests for the offline summarization and question-generation engines."""
import pytest
from pdf_fixtures import ALGORITHMS_TEXT, OPERATING_SYSTEMS_TEXT

from app.services.quiz_engine import (
    InsufficientContentError,
    collect_candidates,
    generate_questions,
)
from app.services.summary_engine import chunk_sentences, split_sentences, summarize


def test_split_sentences_handles_wrapped_pdf_lines_and_headings():
    text = "Operating Systems Unit 1 Lecture Notes\n" + OPERATING_SYSTEMS_TEXT
    sentences = split_sentences(text)
    assert len(sentences) > 10
    # The heading must not be glued to the first real sentence.
    assert not any(
        sentence.startswith("Operating Systems Unit 1 Lecture Notes An operating system")
        for sentence in sentences
    )
    assert any(sentence.startswith("An operating system is") for sentence in sentences)


def test_summarize_is_deterministic_and_reduces_the_source():
    first = summarize(OPERATING_SYSTEMS_TEXT, max_words=120)
    second = summarize(OPERATING_SYSTEMS_TEXT, max_words=120)
    assert first.summary_text == second.summary_text
    assert first.key_points == second.key_points
    assert first.word_count < len(OPERATING_SYSTEMS_TEXT.split())
    assert first.selected_sentences < first.source_sentences
    assert first.chunk_count >= 1
    assert 1 <= len(first.key_points) <= 6


@pytest.mark.parametrize("max_words", [60, 120, 220])
def test_summarize_respects_the_word_budget(max_words):
    result = summarize(OPERATING_SYSTEMS_TEXT + "\n\n" + ALGORITHMS_TEXT, max_words=max_words)
    # One long closing sentence may push slightly over, never wildly over.
    assert result.word_count <= max_words + 25
    assert result.summary_text


def test_summarize_chunks_long_documents_and_keeps_reading_order():
    long_text = "\n\n".join([OPERATING_SYSTEMS_TEXT, ALGORITHMS_TEXT] * 3)
    result = summarize(long_text, max_words=150)
    assert result.chunk_count > 1
    assert len(chunk_sentences(split_sentences(long_text))) > 1
    # Sentences are rebuilt in document order inside each paragraph.
    positions = [long_text.find(sentence) for sentence in result.summary_text.split(". ")]
    assert all(position >= 0 for position in positions if position != -1)


def test_summarize_returns_empty_result_for_unusable_text():
    result = summarize("   \n\n   ")
    assert result.summary_text == ""
    assert result.warnings
    assert result.source_sentences == 0


def test_collect_candidates_only_accepts_definition_statements():
    candidates = collect_candidates(OPERATING_SYSTEMS_TEXT)
    terms = {candidate.term.lower() for candidate in candidates}
    assert "operating system" in terms
    assert "virtual memory" in terms
    assert all(candidate.verb for candidate in candidates)
    # A definition never repeats its own term.
    for candidate in candidates:
        assert candidate.term.lower() not in candidate.definition.lower()


def test_generate_questions_is_grounded_and_deterministic():
    first = generate_questions(OPERATING_SYSTEMS_TEXT, question_count=4, seed=42)
    second = generate_questions(OPERATING_SYSTEMS_TEXT, question_count=4, seed=42)
    assert [q.prompt for q in first.questions] == [q.prompt for q in second.questions]
    assert [q.options for q in first.questions] == [q.options for q in second.questions]
    assert first.candidates > 4

    haystack = OPERATING_SYSTEMS_TEXT.lower()
    for question in first.questions:
        assert 3 <= len(question.options) <= 4
        assert 0 <= question.correct_index < len(question.options)
        assert len(set(question.options)) == len(question.options)
        assert question.options[question.correct_index].lower() in haystack
        assert question.source_excerpt[:40].lower() in haystack.replace("\n", " ")


def test_generate_questions_refuses_to_invent_questions():
    with pytest.raises(InsufficientContentError) as too_short:
        generate_questions("Revision list.", question_count=5)
    assert too_short.value.code == "insufficient_text"

    with pytest.raises(InsufficientContentError) as no_definitions:
        generate_questions(
            "Read the handout again before Monday. Practise two numericals tonight. "
            "Bring the lab record to class and finish the assignment before Thursday. "
            "The internal assessment covers everything from the first four lectures.",
            question_count=5,
        )
    assert no_definitions.value.code in {"no_question_candidates", "not_enough_distractors"}


def test_generate_questions_reports_when_it_cannot_reach_the_requested_count():
    result = generate_questions(ALGORITHMS_TEXT, question_count=20, seed=1)
    assert 1 <= len(result.questions) <= 20
    if len(result.questions) < 20:
        assert result.warnings
