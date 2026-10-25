"""Regression coverage for definition-sparse, numbered, wrapped lecture slides."""

import re

import pytest
from pdf_fixtures import make_pdf

from app.services.quiz_engine import (
    InsufficientContentError,
    _choice_key,
    collect_candidates,
    generate_questions,
)

# Synthetic material: no private lecture file is committed as a fixture.
SLIDE_TEXT = """DATA STRUCTURES
BINARY TREE
BINARY SEARCH TREE
EXPRESSION TREE
AVL Tree
B Tree

1. B-Trees are designed for storage
systems where reading disk blocks is
much more expensive than accessing memory.
2. B-Trees are always height-balanced,
so search and update operations take
logarithmic time in the number of keys.
3. Each node stores multiple keys and child pointers to reduce disk reads.
4. A root must have at least one key unless the tree is empty.
5. Keys in nodes are stored in sorted order so range searches remain efficient.
6. Maintaining balance via node splits adds overhead during insertions and deletions.
"""
GRAPH_TEXT = """GRAPH ALGORITHMS
Depth First Search
Minimum Spanning Tree

The Bellman–Ford algorithm is used to find
shortest paths from a single source vertex
to all other reachable vertices in a weighted graph.
A shortest path in a graph with V vertices can have at most V-1 edges.
Relaxing an edge can improve the current distance estimate for its destination vertex.
The algorithm can detect negative cycles by checking for further distance improvements.
"""


def flatten(text):
    return re.sub(r"\s+", " ", text).strip().casefold()


def test_wrapped_numbered_and_hyphenated_definitions_are_recovered():
    candidates = collect_candidates(SLIDE_TEXT)
    definition = next(c for c in candidates if c.term == "B-Trees")
    assert "much more expensive than accessing memory" in definition.definition
    assert not any(c.term.startswith(("Step", "Insert", "Module")) for c in candidates)


def test_colon_labels_and_unicode_hyphens_are_accepted_without_treating_steps_as_definitions():
    text = """Tree terminology
Binary tree: A hierarchical structure in which nodes have at most two children.
Bellman–Ford algorithm is a method that finds shortest paths from a source vertex.
Step 1: Determine an arbitrary vertex as the starting point of the traversal.
Insert 6: Goes to the right child and then splits the overflowing leaf node.
"""
    terms = {c.term for c in collect_candidates(text)}
    assert "Binary tree" in terms
    assert "Bellman–Ford algorithm" in terms
    assert "Step 1" not in terms
    assert "Insert 6" not in terms


def test_sparse_slides_generate_grounded_deterministic_passage_questions():
    first = generate_questions(SLIDE_TEXT, question_count=5, seed=12)
    second = generate_questions(SLIDE_TEXT, question_count=5, seed=12)
    assert len(first.questions) == 5
    assert first == second
    assert any(q.prompt.startswith("Complete the passage") for q in first.questions)
    assert any("quoted source passages" in warning for warning in first.warnings)
    for question in first.questions:
        assert 3 <= len(question.options) <= 4
        assert len({_choice_key(option) for option in question.options}) == len(question.options)
        assert flatten(question.source_excerpt) in flatten(SLIDE_TEXT)
        assert all(flatten(option) in flatten(SLIDE_TEXT) for option in question.options)
        assert "Source:" in question.explanation
        answer = question.options[question.correct_index]
        if question.prompt.startswith("Complete the passage"):
            assert not re.search(
                rf"(?<!\w){re.escape(answer)}(?!\w)", question.prompt, re.IGNORECASE
            )


def test_page_attribution_survives_wrapped_text_and_bullets():
    first_page = SLIDE_TEXT + "\n"
    result = generate_questions(
        first_page + GRAPH_TEXT, question_count=10, page_offsets=[0, len(first_page)]
    )
    assert {q.source_page for q in result.questions} == {1, 2}
    for question in result.questions:
        source = first_page if question.source_page == 1 else GRAPH_TEXT
        assert flatten(question.source_excerpt) in flatten(source)


@pytest.mark.parametrize(
    "text",
    [
        (
            "#include <stdio.h>\nstruct Node {\nint data;\nstruct Node* left;\n};\n"
            'printf("A tree is a structure that stores related nodes and their children.");\n'
        )
        * 4,
        "BINARY TREE\n[1, 2]\n/ | \\\n[3] [4] [5]\n" * 12,
    ],
)
def test_code_and_diagrams_do_not_become_questions(text):
    with pytest.raises(InsufficientContentError):
        generate_questions(text)


def test_single_statement_without_distinct_choices_still_fails_honestly():
    text = (
        "A hierarchical structure is an arrangement where every stored element has a unique "
        "place determined by its parent and where links connect related elements together "
        "in a consistent and explicitly recorded organization for efficient access."
    )
    with pytest.raises(InsufficientContentError) as error:
        generate_questions(text)
    assert error.value.code == "not_enough_distractors"
    assert "four-option" not in str(error.value)


def test_partial_result_reports_the_actual_count():
    result = generate_questions(SLIDE_TEXT, question_count=20)
    assert 1 <= len(result.questions) < 20
    assert any(f"Only {len(result.questions)} reliable" in warning for warning in result.warnings)


@pytest.mark.asyncio
async def test_slide_pdf_generates_persisted_quiz_and_can_be_graded(client):
    registration = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "slides.regression@studyflow.edu",
            "password": "SlideRegression2026!",
            "display_name": "Slide Student",
        },
    )
    assert registration.status_code == 201
    headers = {"Authorization": "Bearer " + registration.json()["access_token"]}
    upload = await client.post(
        "/api/v1/documents",
        headers=headers,
        data={"title": "Synthetic tree slides"},
        files={"file": ("slides.pdf", make_pdf(SLIDE_TEXT), "application/pdf")},
    )
    assert upload.status_code == 201
    document = upload.json()
    assert document["processing_status"] == "completed"
    response = await client.post(
        f"/api/v1/documents/{document['id']}/quiz", headers=headers, json={"question_count": 5}
    )
    assert response.status_code == 201, response.text
    quiz = response.json()
    assert quiz["engine_version"] == "extractive-cloze-v2"
    assert quiz["question_count"] == 5
    assert all("correct_index" not in q for q in quiz["questions"])
    history = await client.get(f"/api/v1/documents/{document['id']}/quizzes", headers=headers)
    assert history.json()[0]["id"] == quiz["id"]
    submitted = await client.post(
        f"/api/v1/quizzes/{quiz['id']}/attempts",
        headers=headers,
        json={
            "answers": [{"question_id": q["id"], "selected_index": 0} for q in quiz["questions"]],
        },
    )
    assert submitted.status_code == 201
    assert submitted.json()["total_questions"] == 5
    source = (await client.get(f"/api/v1/documents/{document['id']}/text", headers=headers)).json()[
        "text"
    ]
    for answer in submitted.json()["answers"]:
        assert flatten(answer["source_excerpt"]) in flatten(source)
        assert flatten(answer["options"][answer["correct_index"]]) in flatten(source)
        assert answer["source_page"] == 1
