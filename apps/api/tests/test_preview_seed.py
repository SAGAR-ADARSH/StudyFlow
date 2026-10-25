"""The preview fixture is additive, repeatable, and never resets existing credentials."""

import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[3] / "scripts/seed_preview.py"
spec = importlib.util.spec_from_file_location("studyflow_preview_seed", SCRIPT)
seed_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(seed_module)
pytestmark = pytest.mark.asyncio


async def test_preview_seed_is_complete_repeatable_and_preserves_edits(client):
    password = "PreviewFixturePassword2026!"
    first = await seed_module.seed_preview(client, password)
    assert first == {"subjects": 3, "topics": 12, "exams": 4, "tasks": 4, "flashcards": 9}
    notes = (await client.get("/api/v1/notes")).json()
    assert len(notes) == 2
    note = notes[0]
    edited = note["content"] + "\nPersonal edit to preserve."
    assert (
        await client.put(
            f"/api/v1/notes/{note['id']}", json={"content": edited, "is_pinned": False}
        )
    ).status_code == 200
    cards = (await client.get("/api/v1/flashcards")).json()
    card = next(c for c in cards if not c["is_generated"])
    assert (
        await client.patch(
            f"/api/v1/flashcards/{card['id']}/review", json={"review_status": "needs_revision"}
        )
    ).status_code == 200
    before_sprints = (await client.get("/api/v1/sprints")).json()
    completed = [t for t in before_sprints[0]["tasks"] if t["completed"]]
    assert completed
    documents = (await client.get("/api/v1/documents")).json()["items"]
    assert len(documents) == 2 and all(d["processing_status"] == "completed" for d in documents)
    assert all(d["summary_count"] == 1 and d["quiz_count"] == 1 for d in documents)
    before_sessions = (await client.get("/api/v1/study-sessions")).json()
    second = await seed_module.seed_preview(client, password)
    assert second == first
    assert (await client.get(f"/api/v1/notes/{note['id']}")).json()["content"] == edited
    assert not (await client.get(f"/api/v1/notes/{note['id']}")).json()["is_pinned"]
    assert (await client.get(f"/api/v1/flashcards/{card['id']}")).json()[
        "review_status"
    ] == "needs_revision"
    assert (await client.get("/api/v1/study-sessions")).json() == before_sessions
    after_sprints = (await client.get("/api/v1/sprints")).json()
    assert [t for t in after_sprints[0]["tasks"] if t["completed"]] == completed


async def test_preview_seed_does_not_reset_an_existing_password(client):
    existing = "ExistingPreviewPassword2026!"
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": seed_module.DEMO_EMAIL,
            "password": existing,
            "display_name": "Existing demo",
        },
    )
    assert response.status_code == 201
    with pytest.raises(RuntimeError, match="Existing credentials were not reset"):
        await seed_module.seed_preview(client, "DifferentPreviewPassword2026!")
    assert (
        await client.post(
            "/api/v1/auth/login", json={"email": seed_module.DEMO_EMAIL, "password": existing}
        )
    ).status_code == 200
