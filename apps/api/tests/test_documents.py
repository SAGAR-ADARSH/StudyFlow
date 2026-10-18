"""PDF upload, text extraction, and document lifecycle (the PDF Intelligence phase)."""
import pytest
from httpx import AsyncClient
from pdf_fixtures import (
    ALGORITHMS_TEXT,
    OPERATING_SYSTEMS_TEXT,
    make_blank_pdf,
    make_pdf,
    make_scanned_pdf,
)


async def register_user(client: AsyncClient, email: str) -> dict[str, str]:
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "SecurePassword123!",
            "display_name": "PDF Student",
        },
    )
    assert response.status_code == 201, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def create_subject(client: AsyncClient, headers: dict[str, str]) -> tuple[int, int]:
    semester = await client.post(
        "/api/v1/semesters", headers=headers, json={"name": "MCA Semester 3"}
    )
    assert semester.status_code == 201, semester.text
    subject = await client.post(
        "/api/v1/subjects",
        headers=headers,
        json={"semester_id": semester.json()["id"], "name": "Operating Systems"},
    )
    assert subject.status_code == 201, subject.text
    return semester.json()["id"], subject.json()["id"]


def upload(files: bytes, **data):
    return {"files": {"file": ("notes.pdf", files, "application/pdf")}, "data": data}


@pytest.mark.asyncio
async def test_upload_extracts_text_and_links_academic_context(client: AsyncClient):
    headers = await register_user(client, "docs.owner@studyflow.edu")
    semester_id, subject_id = await create_subject(client, headers)

    response = await client.post(
        "/api/v1/documents",
        headers=headers,
        **upload(make_pdf(OPERATING_SYSTEMS_TEXT, ALGORITHMS_TEXT), subject_id=str(subject_id)),
    )
    assert response.status_code == 201, response.text
    document = response.json()
    assert document["processing_status"] == "completed"
    assert document["error_code"] is None
    assert document["page_count"] == 2
    assert document["extracted_chars"] > 500
    assert document["word_count"] > 100
    assert document["subject_id"] == subject_id
    assert document["subject_name"] == "Operating Systems"
    assert document["semester_id"] == semester_id
    assert document["semester_name"] == "MCA Semester 3"
    assert document["summary_count"] == 0
    assert document["quiz_count"] == 0

    listing = await client.get("/api/v1/documents", headers=headers)
    assert listing.status_code == 200
    body = listing.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == document["id"]
    # The listing must not ship the whole extracted text.
    assert "extracted_text" not in body["items"][0]

    text_response = await client.get(f"/api/v1/documents/{document['id']}/text", headers=headers)
    assert text_response.status_code == 200
    text_body = text_response.json()
    assert text_body["processing_status"] == "completed"
    assert "operating system" in text_body["text"].lower()
    assert "Dijkstra algorithm" in text_body["text"]

    filtered = await client.get("/api/v1/documents?status=failed", headers=headers)
    assert filtered.json()["total"] == 0
    searched = await client.get("/api/v1/documents?q=Operating Systems", headers=headers)
    assert searched.json()["total"] == 1


@pytest.mark.asyncio
async def test_upload_rejects_non_pdf_before_creating_a_record(client: AsyncClient):
    headers = await register_user(client, "docs.typecheck@studyflow.edu")

    response = await client.post(
        "/api/v1/documents",
        headers=headers,
        files={"file": ("notes.txt", b"just some plain text", "text/plain")},
    )
    assert response.status_code == 400, response.text
    assert response.json()["detail"]["code"] == "unsupported_file_type"

    listing = await client.get("/api/v1/documents", headers=headers)
    assert listing.json()["total"] == 0


@pytest.mark.asyncio
async def test_corrupt_pdf_is_recorded_as_failed_and_never_completed(client: AsyncClient):
    headers = await register_user(client, "docs.corrupt@studyflow.edu")

    response = await client.post(
        "/api/v1/documents",
        headers=headers,
        **upload(b"%PDF-1.7\nthis is not a real pdf body\x00\x01\x02"),
    )
    assert response.status_code == 201, response.text
    document = response.json()
    assert document["processing_status"] == "failed"
    assert document["error_code"] == "corrupt_pdf"
    assert document["error_message"]
    assert document["extracted_chars"] == 0

    text_response = await client.get(f"/api/v1/documents/{document['id']}/text", headers=headers)
    assert text_response.json()["text"] is None

    # Nothing can be generated from a document that failed extraction.
    summary = await client.post(
        f"/api/v1/documents/{document['id']}/summary", headers=headers, json={}
    )
    assert summary.status_code == 400
    assert summary.json()["detail"]["code"] == "corrupt_pdf"

    quiz = await client.post(
        f"/api/v1/documents/{document['id']}/quiz", headers=headers, json={"question_count": 5}
    )
    assert quiz.status_code == 400


@pytest.mark.asyncio
async def test_empty_and_scanned_pdfs_report_their_own_error_codes(client: AsyncClient):
    headers = await register_user(client, "docs.empty@studyflow.edu")

    blank = await client.post("/api/v1/documents", headers=headers, **upload(make_blank_pdf()))
    assert blank.status_code == 201
    assert blank.json()["processing_status"] == "failed"
    assert blank.json()["error_code"] == "empty_document"
    assert "no text" in blank.json()["error_message"].lower()

    scanned = await client.post(
        "/api/v1/documents", headers=headers, **upload(make_scanned_pdf())
    )
    assert scanned.status_code == 201
    assert scanned.json()["processing_status"] == "failed"
    assert scanned.json()["error_code"] == "scanned_pdf"
    assert "ocr" in scanned.json()["error_message"].lower()

    tiny = await client.post(
        "/api/v1/documents",
        headers=headers,
        **upload(make_pdf("Revision checklist for Monday.")),
    )
    assert tiny.status_code == 201
    assert tiny.json()["processing_status"] == "failed"
    assert tiny.json()["error_code"] == "insufficient_text"


@pytest.mark.asyncio
async def test_duplicate_upload_is_rejected_with_409(client: AsyncClient):
    headers = await register_user(client, "docs.duplicate@studyflow.edu")
    payload = make_pdf(OPERATING_SYSTEMS_TEXT)

    first = await client.post("/api/v1/documents", headers=headers, **upload(payload))
    assert first.status_code == 201

    second = await client.post("/api/v1/documents", headers=headers, **upload(payload))
    assert second.status_code == 409
    assert second.json()["detail"]["code"] == "duplicate_document"
    assert first.json()["title"] in second.json()["detail"]["message"]

    listing = await client.get("/api/v1/documents", headers=headers)
    assert listing.json()["total"] == 1


@pytest.mark.asyncio
async def test_oversized_upload_is_rejected(client: AsyncClient, monkeypatch):
    from app.core.config import get_settings

    monkeypatch.setattr(get_settings(), "max_upload_size_mb", 1)
    headers = await register_user(client, "docs.size@studyflow.edu")

    response = await client.post(
        "/api/v1/documents", headers=headers, **upload(make_pdf("x" * 100) + b"0" * (1024 * 1024))
    )
    assert response.status_code == 413
    assert response.json()["detail"]["code"] == "file_too_large"

    listing = await client.get("/api/v1/documents", headers=headers)
    assert listing.json()["total"] == 0


@pytest.mark.asyncio
async def test_reprocess_retries_a_failed_document(client: AsyncClient, isolated_upload_dir):
    headers = await register_user(client, "docs.reprocess@studyflow.edu")

    created = await client.post(
        "/api/v1/documents", headers=headers, **upload(b"%PDF-1.5\nbroken stream")
    )
    assert created.json()["processing_status"] == "failed"
    document_id = created.json()["id"]

    retried = await client.post(f"/api/v1/documents/{document_id}/reprocess", headers=headers)
    assert retried.status_code == 200
    assert retried.json()["processing_status"] == "failed"
    assert retried.json()["error_code"] == "corrupt_pdf"

    # A missing stored file is reported instead of crashing the request.
    for path in isolated_upload_dir.rglob("*.pdf"):
        path.unlink()
    missing = await client.post(f"/api/v1/documents/{document_id}/reprocess", headers=headers)
    assert missing.status_code == 200
    assert missing.json()["processing_status"] == "failed"
    assert missing.json()["error_code"] == "file_missing"


@pytest.mark.asyncio
async def test_delete_document_removes_file_and_generated_data(
    client: AsyncClient, isolated_upload_dir
):
    headers = await register_user(client, "docs.delete@studyflow.edu")
    created = await client.post(
        "/api/v1/documents",
        headers=headers,
        **upload(make_pdf(OPERATING_SYSTEMS_TEXT), title="Unit 1 notes"),
    )
    document = created.json()
    await client.post(f"/api/v1/documents/{document['id']}/summary", headers=headers, json={})
    await client.post(
        f"/api/v1/documents/{document['id']}/quiz", headers=headers, json={"question_count": 4}
    )

    stored_files = list(isolated_upload_dir.rglob("*.pdf"))
    assert len(stored_files) == 1

    deleted = await client.delete(f"/api/v1/documents/{document['id']}", headers=headers)
    assert deleted.status_code == 204
    assert not list(isolated_upload_dir.rglob("*.pdf"))

    assert (await client.get(f"/api/v1/documents/{document['id']}", headers=headers)).status_code == 404
    assert (
        await client.get(f"/api/v1/documents/{document['id']}/summary", headers=headers)
    ).status_code == 404

    other = await register_user(client, "docs.delete.other@studyflow.edu")
    assert (
        await client.delete(f"/api/v1/documents/{document['id']}", headers=other)
    ).status_code == 404


@pytest.mark.asyncio
async def test_documents_require_authentication(client: AsyncClient):
    assert (await client.get("/api/v1/documents")).status_code in (401, 403)
    response = await client.post(
        "/api/v1/documents", **upload(make_pdf(OPERATING_SYSTEMS_TEXT))
    )
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_subject_from_another_account_is_rejected(client: AsyncClient):
    owner = await register_user(client, "docs.subject.owner@studyflow.edu")
    intruder = await register_user(client, "docs.subject.intruder@studyflow.edu")
    _, subject_id = await create_subject(client, owner)

    response = await client.post(
        "/api/v1/documents",
        headers=intruder,
        **upload(make_pdf(OPERATING_SYSTEMS_TEXT), subject_id=str(subject_id)),
    )
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "subject_not_found"
