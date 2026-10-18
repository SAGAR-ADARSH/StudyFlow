"""Summaries, quizzes, attempts, results, and the privacy rules around them."""
import re

import pytest
from httpx import AsyncClient
from pdf_fixtures import ALGORITHMS_TEXT, OPERATING_SYSTEMS_TEXT, make_pdf


async def register_user(client: AsyncClient, email: str) -> dict[str, str]:
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "SecurePassword123!",
            "display_name": "Insight Student",
        },
    )
    assert response.status_code == 201, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def flatten(text: str) -> str:
    """Collapse whitespace so extracted text can be compared sentence by sentence."""
    return re.sub(r"\s+", " ", text).strip().lower()


async def upload_document(
    client: AsyncClient,
    headers: dict[str, str],
    *,
    title: str = "Operating Systems Unit 1",
    subject: bool = True,
) -> dict:
    data: dict[str, str] = {"title": title}
    if subject:
        semester = await client.post(
            "/api/v1/semesters", headers=headers, json={"name": "MCA Semester 3"}
        )
        assert semester.status_code == 201, semester.text
        subject_response = await client.post(
            "/api/v1/subjects",
            headers=headers,
            json={"semester_id": semester.json()["id"], "name": "Operating Systems"},
        )
        assert subject_response.status_code == 201, subject_response.text
        data["subject_id"] = str(subject_response.json()["id"])
        data["semester_id"] = str(semester.json()["id"])

    response = await client.post(
        "/api/v1/documents",
        headers=headers,
        files={"file": ("unit1.pdf", make_pdf(OPERATING_SYSTEMS_TEXT), "application/pdf")},
        data=data,
    )
    assert response.status_code == 201, response.text
    document = response.json()
    assert document["processing_status"] == "completed", document
    return document


@pytest.mark.asyncio
async def test_summary_generation_persists_and_can_be_regenerated(client: AsyncClient):
    headers = await register_user(client, "insight.summary@studyflow.edu")
    document = await upload_document(client, headers)

    first = await client.post(
        f"/api/v1/documents/{document['id']}/summary",
        headers=headers,
        json={"max_words": 120, "max_key_points": 4},
    )
    assert first.status_code == 201, first.text
    summary = first.json()
    assert summary["document_id"] == document["id"]
    assert summary["method"] == "extractive"
    assert summary["engine_version"]
    assert len(summary["summary_text"].split()) <= 135
    assert 1 <= len(summary["key_points"]) <= 4
    assert summary["source_chars"] == document["extracted_chars"]
    assert summary["source_sentences"] > 5
    assert summary["source_title"] == "Operating Systems Unit 1"
    # The summary really is a reduction of the source, not a copy of it.
    assert summary["word_count"] < document["word_count"]
    # Extractive guarantee: every summary sentence exists verbatim in the PDF text.
    extracted = flatten(
        (await client.get(f"/api/v1/documents/{document['id']}/text", headers=headers)).json()["text"]
    )
    for sentence in re.split(r"(?<=[.!?])\s+", summary["summary_text"]):
        candidate = flatten(sentence)
        if candidate:
            assert candidate in extracted, candidate

    fetched = await client.get(f"/api/v1/documents/{document['id']}/summary", headers=headers)
    assert fetched.status_code == 200
    assert fetched.json()["id"] == summary["id"]
    assert fetched.json()["summary_text"] == summary["summary_text"]

    regenerated = await client.post(
        f"/api/v1/documents/{document['id']}/summary",
        headers=headers,
        json={"max_words": 60, "max_key_points": 2},
    )
    assert regenerated.status_code == 201
    assert regenerated.json()["id"] != summary["id"]
    assert regenerated.json()["word_count"] <= summary["word_count"]

    history = await client.get(f"/api/v1/documents/{document['id']}/summaries", headers=headers)
    assert history.status_code == 200
    assert next(item["id"] for item in history.json()) == regenerated.json()["id"]
    assert len(history.json()) == 2

    latest = await client.get(f"/api/v1/documents/{document['id']}/summary", headers=headers)
    assert latest.json()["id"] == regenerated.json()["id"]

    detail = await client.get(f"/api/v1/documents/{document['id']}", headers=headers)
    assert detail.json()["summary_count"] == 2
    assert detail.json()["latest_summary_id"] == regenerated.json()["id"]


@pytest.mark.asyncio
async def test_quiz_generation_uses_document_content_and_grades_attempts(client: AsyncClient):
    headers = await register_user(client, "insight.quiz@studyflow.edu")
    document = await upload_document(client, headers)
    text = (
        await client.get(f"/api/v1/documents/{document['id']}/text", headers=headers)
    ).json()["text"]

    created = await client.post(
        f"/api/v1/documents/{document['id']}/quiz",
        headers=headers,
        json={"question_count": 5},
    )
    assert created.status_code == 201, created.text
    quiz = created.json()
    assert quiz["document_id"] == document["id"]
    assert quiz["question_count"] >= 1
    assert len(quiz["questions"]) == quiz["question_count"]
    assert quiz["subject_name"] == "Operating Systems"
    assert quiz["semester_name"] == "MCA Semester 3"
    assert quiz["attempt_count"] == 0
    assert quiz["best_score_percent"] is None

    for question in quiz["questions"]:
        # Every question hides its answer while the quiz is being taken.
        assert "correct_index" not in question
        assert "explanation" not in question
        assert 3 <= len(question["options"]) <= 4
        assert len(set(question["options"])) == len(question["options"])
        assert question["prompt"].startswith("Fill in the blank") or question["prompt"].startswith(
            "Which statement best describes"
        )

    taken = await client.get(f"/api/v1/quizzes/{quiz['id']}", headers=headers)
    assert taken.status_code == 200
    assert len(taken.json()["questions"]) == quiz["question_count"]
    assert all("correct_index" not in q for q in taken.json()["questions"])

    listing = await client.get(f"/api/v1/documents/{document['id']}/quizzes", headers=headers)
    assert listing.status_code == 200
    assert [item["id"] for item in listing.json()] == [quiz["id"]]

    # Answer every question with its first option, so the score is genuinely computed.
    submission = {
        "answers": [
            {"question_id": question["id"], "selected_index": 0} for question in quiz["questions"]
        ],
        "duration_seconds": 95,
    }
    attempt = await client.post(f"/api/v1/quizzes/{quiz['id']}/attempts", headers=headers, json=submission)
    assert attempt.status_code == 201, attempt.text
    graded = attempt.json()
    assert graded["total_questions"] == quiz["question_count"]
    expected_correct = sum(
        1
        for answer in graded["answers"]
        if answer["selected_index"] == answer["correct_index"]
    )
    assert graded["correct_count"] == expected_correct
    assert graded["score_percent"] == pytest.approx(
        round(expected_correct / graded["total_questions"] * 100, 1)
    )
    normalized_text = flatten(text)
    for answer in graded["answers"]:
        assert answer["is_correct"] == (answer["selected_index"] == answer["correct_index"])
        # Explanations quote the source document.
        assert "Source:" in answer["explanation"]
        assert answer["source_excerpt"]
        assert flatten(answer["source_excerpt"]) in normalized_text
        # The correct option is content from the uploaded PDF, never an invention.
        correct_option = answer["options"][answer["correct_index"]]
        assert flatten(correct_option) in normalized_text

    results = await client.get(f"/api/v1/quizzes/{quiz['id']}/results", headers=headers)
    assert results.status_code == 200
    body = results.json()
    assert len(body["attempts"]) == 1
    assert body["attempts"][0]["id"] == graded["id"]
    assert body["best_score_percent"] == graded["score_percent"]
    assert body["average_score_percent"] == graded["score_percent"]

    # A second attempt with the revealed answers must score 100%.
    perfect = {
        "answers": [
            {"question_id": answer["question_id"], "selected_index": answer["correct_index"]}
            for answer in graded["answers"]
        ]
    }
    second = await client.post(f"/api/v1/quizzes/{quiz['id']}/attempts", headers=headers, json=perfect)
    assert second.status_code == 201
    assert second.json()["correct_count"] == second.json()["total_questions"]
    assert second.json()["score_percent"] == 100.0

    results_again = await client.get(f"/api/v1/quizzes/{quiz['id']}/results", headers=headers)
    assert len(results_again.json()["attempts"]) == 2
    assert results_again.json()["best_score_percent"] == 100.0
    assert results_again.json()["average_score_percent"] == pytest.approx(
        round((graded["score_percent"] + 100.0) / 2, 1)
    )

    single = await client.get(
        f"/api/v1/quizzes/{quiz['id']}/attempts/{graded['id']}", headers=headers
    )
    assert single.status_code == 200
    assert single.json()["score_percent"] == graded["score_percent"]

    detail = await client.get(f"/api/v1/documents/{document['id']}", headers=headers)
    assert detail.json()["quiz_count"] == 1
    assert detail.json()["latest_quiz_id"] == quiz["id"]


@pytest.mark.asyncio
async def test_partial_and_invalid_submissions_are_handled(client: AsyncClient):
    headers = await register_user(client, "insight.partial@studyflow.edu")
    document = await upload_document(client, headers)
    quiz = (
        await client.post(
            f"/api/v1/documents/{document['id']}/quiz", headers=headers, json={"question_count": 3}
        )
    ).json()

    skipped = await client.post(
        f"/api/v1/quizzes/{quiz['id']}/attempts",
        headers=headers,
        json={"answers": []},
    )
    assert skipped.status_code == 201
    assert skipped.json()["correct_count"] == 0
    assert skipped.json()["score_percent"] == 0.0
    assert all(answer["selected_index"] is None for answer in skipped.json()["answers"])

    bogus = await client.post(
        f"/api/v1/quizzes/{quiz['id']}/attempts",
        headers=headers,
        json={"answers": [{"question_id": quiz["questions"][0]["id"], "selected_index": 5}]},
    )
    assert bogus.status_code == 400
    assert bogus.json()["detail"]["code"] == "invalid_option"

    # Out-of-range option indexes are rejected by request validation.
    out_of_range = await client.post(
        f"/api/v1/quizzes/{quiz['id']}/attempts",
        headers=headers,
        json={"answers": [{"question_id": quiz["questions"][0]["id"], "selected_index": 99}]},
    )
    assert out_of_range.status_code == 422

    foreign = await client.post(
        f"/api/v1/quizzes/{quiz['id']}/attempts",
        headers=headers,
        json={"answers": [{"question_id": 987_654, "selected_index": 0}]},
    )
    assert foreign.status_code == 400
    assert foreign.json()["detail"]["code"] == "unknown_question"

    duplicate = await client.post(
        f"/api/v1/quizzes/{quiz['id']}/attempts",
        headers=headers,
        json={
            "answers": [
                {"question_id": quiz["questions"][0]["id"], "selected_index": 0},
                {"question_id": quiz["questions"][0]["id"], "selected_index": 1},
            ]
        },
    )
    assert duplicate.status_code == 400
    assert duplicate.json()["detail"]["code"] == "duplicate_answer"


@pytest.mark.asyncio
async def test_insufficient_text_returns_a_helpful_message(client: AsyncClient):
    headers = await register_user(client, "insight.thin@studyflow.edu")
    thin_text = (
        "Revision list for Monday. Read the handout again. Practise two numericals. "
        "Bring the lab record to class and finish the assignment before Thursday evening."
    )
    created = await client.post(
        "/api/v1/documents",
        headers=headers,
        files={"file": ("thin.pdf", make_pdf(thin_text), "application/pdf")},
        data={"title": "Thin handout"},
    )
    assert created.status_code == 201
    document = created.json()
    assert document["processing_status"] == "completed"
    document_text = (
        await client.get(f"/api/v1/documents/{document['id']}/text", headers=headers)
    ).json()["text"]

    quiz = await client.post(
        f"/api/v1/documents/{document['id']}/quiz", headers=headers, json={"question_count": 5}
    )
    assert quiz.status_code == 422
    assert quiz.json()["detail"]["code"] in {
        "insufficient_text",
        "no_question_candidates",
        "not_enough_distractors",
    }
    assert len(quiz.json()["detail"]["message"]) > 20

    summary = await client.post(
        f"/api/v1/documents/{document['id']}/summary", headers=headers, json={}
    )
    # A couple of sentences may still be summarised, but nothing is invented.
    assert summary.status_code in (201, 422)
    if summary.status_code == 201:
        extracted = flatten(document_text)
        for sentence in re.split(r"(?<=[.!?])\s+", summary.json()["summary_text"]):
            if flatten(sentence):
                assert flatten(sentence) in extracted


@pytest.mark.asyncio
async def test_generated_data_is_private_to_its_owner(client: AsyncClient):
    owner = await register_user(client, "insight.owner@studyflow.edu")
    intruder = await register_user(client, "insight.intruder@studyflow.edu")
    document = await upload_document(client, owner)

    summary = (
        await client.post(f"/api/v1/documents/{document['id']}/summary", headers=owner, json={})
    ).json()
    quiz = (
        await client.post(
            f"/api/v1/documents/{document['id']}/quiz",
            headers=owner,
            json={"question_count": 4},
        )
    ).json()
    attempt = (
        await client.post(
            f"/api/v1/quizzes/{quiz['id']}/attempts",
            headers=owner,
            json={
                "answers": [
                    {"question_id": question["id"], "selected_index": 0}
                    for question in quiz["questions"]
                ]
            },
        )
    ).json()

    private_urls = [
        f"/api/v1/documents/{document['id']}",
        f"/api/v1/documents/{document['id']}/text",
        f"/api/v1/documents/{document['id']}/summary",
        f"/api/v1/documents/{document['id']}/summaries",
        f"/api/v1/documents/{document['id']}/quizzes",
        f"/api/v1/quizzes/{quiz['id']}",
        f"/api/v1/quizzes/{quiz['id']}/results",
        f"/api/v1/quizzes/{quiz['id']}/attempts/{attempt['id']}",
    ]
    for url in private_urls:
        response = await client.get(url, headers=intruder)
        assert response.status_code == 404, f"{url} leaked with {response.status_code}"

    for url in [
        f"/api/v1/documents/{document['id']}/summary",
        f"/api/v1/documents/{document['id']}/quiz",
        f"/api/v1/documents/{document['id']}/reprocess",
    ]:
        posted = await client.post(url, headers=intruder, json={})
        assert posted.status_code == 404, url

    submitted = await client.post(
        f"/api/v1/quizzes/{quiz['id']}/attempts",
        headers=intruder,
        json={"answers": []},
    )
    assert submitted.status_code == 404

    assert (await client.get("/api/v1/documents", headers=intruder)).json()["total"] == 0
    assert summary["user_id"] != (await client.get("/api/v1/auth/me", headers=intruder)).json()["id"]


@pytest.mark.asyncio
async def test_summaries_and_quizzes_also_work_for_plain_text_notes(client: AsyncClient):
    headers = await register_user(client, "insight.notes@studyflow.edu")
    note = (
        await client.post(
            "/api/v1/notes",
            headers=headers,
            json={
                "title": "Algorithms quick sheet",
                "content": ALGORITHMS_TEXT,
                "tags": ["unit-2"],
            },
        )
    ).json()

    summary = await client.post(
        f"/api/v1/notes/{note['id']}/summary",
        headers=headers,
        json={"max_words": 90, "max_key_points": 3},
    )
    assert summary.status_code == 201, summary.text
    assert summary.json()["note_id"] == note["id"]
    assert summary.json()["document_id"] is None
    assert summary.json()["source_title"] == "Algorithms quick sheet"

    fetched = await client.get(f"/api/v1/notes/{note['id']}/summary", headers=headers)
    assert fetched.status_code == 200
    assert fetched.json()["id"] == summary.json()["id"]

    quiz = await client.post(
        f"/api/v1/notes/{note['id']}/quiz", headers=headers, json={"question_count": 5}
    )
    assert quiz.status_code == 201, quiz.text
    assert quiz.json()["note_id"] == note["id"]
    assert quiz.json()["question_count"] >= 1

    attempt = await client.post(
        f"/api/v1/quizzes/{quiz.json()['id']}/attempts",
        headers=headers,
        json={
            "answers": [
                {"question_id": question["id"], "selected_index": 1}
                for question in quiz.json()["questions"]
            ]
        },
    )
    assert attempt.status_code == 201

    other = await register_user(client, "insight.notes.other@studyflow.edu")
    assert (
        await client.post(f"/api/v1/notes/{note['id']}/summary", headers=other, json={})
    ).status_code == 404
    assert (await client.get(f"/api/v1/notes/{note['id']}/summary", headers=other)).status_code == 404


@pytest.mark.asyncio
async def test_quiz_request_validation(client: AsyncClient):
    headers = await register_user(client, "insight.validation@studyflow.edu")
    document = await upload_document(client, headers)

    too_many = await client.post(
        f"/api/v1/documents/{document['id']}/quiz",
        headers=headers,
        json={"question_count": 250},
    )
    assert too_many.status_code == 422

    bad_summary = await client.post(
        f"/api/v1/documents/{document['id']}/summary",
        headers=headers,
        json={"max_words": 5},
    )
    assert bad_summary.status_code == 422

    missing_document = await client.post(
        "/api/v1/documents/999999/quiz", headers=headers, json={"question_count": 5}
    )
    assert missing_document.status_code == 404
