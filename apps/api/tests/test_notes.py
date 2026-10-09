import pytest
from httpx import AsyncClient


async def register_user(client: AsyncClient, email: str) -> dict[str, str]:
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "SecurePassword123!",
            "display_name": "Notes Student",
        },
    )
    assert response.status_code == 201, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.mark.asyncio
async def test_notes_crud_search_filters_and_owner_isolation(client: AsyncClient):
    owner_headers = await register_user(client, "notes.owner@studyflow.edu")
    other_headers = await register_user(client, "notes.other@studyflow.edu")

    semester_response = await client.post(
        "/api/v1/semesters",
        headers=owner_headers,
        json={"name": "MCA Semester 1"},
    )
    assert semester_response.status_code == 201
    subject_response = await client.post(
        "/api/v1/subjects",
        headers=owner_headers,
        json={"semester_id": semester_response.json()["id"], "name": "Data Structures"},
    )
    assert subject_response.status_code == 201
    subject_id = subject_response.json()["id"]
    topic_response = await client.post(
        "/api/v1/topics",
        headers=owner_headers,
        json={"subject_id": subject_id, "name": "Graph Traversal"},
    )
    assert topic_response.status_code == 201
    topic_id = topic_response.json()["id"]

    create_response = await client.post(
        "/api/v1/notes",
        headers=owner_headers,
        json={
            "title": "Graph traversal review",
            "content": "BFS uses a queue; DFS explores one path deeply first.",
            "subject_id": subject_id,
            "topic_id": topic_id,
            "tags": ["Algorithms", " revision ", "ALGORITHMS"],
            "is_pinned": True,
        },
    )
    assert create_response.status_code == 201, create_response.text
    note = create_response.json()
    note_id = note["id"]
    assert note["tags"] == ["Algorithms", "revision"]
    assert note["subject_name"] == "Data Structures"
    assert note["topic_name"] == "Graph Traversal"

    general_response = await client.post(
        "/api/v1/notes",
        headers=owner_headers,
        json={"title": "Weekly plan", "content": "Review lecture notes on Friday."},
    )
    assert general_response.status_code == 201
    assert general_response.json()["subject_id"] is None

    list_response = await client.get("/api/v1/notes", headers=owner_headers)
    assert list_response.status_code == 200
    assert [item["id"] for item in list_response.json()] == [note_id, general_response.json()["id"]]

    search_response = await client.get(
        "/api/v1/notes?q=queue&pinned=true",
        headers=owner_headers,
    )
    assert [item["id"] for item in search_response.json()] == [note_id]
    tag_search_response = await client.get("/api/v1/notes?q=revision", headers=owner_headers)
    assert [item["id"] for item in tag_search_response.json()] == [note_id]
    subject_search_response = await client.get("/api/v1/notes?q=Data%20Structures", headers=owner_headers)
    assert [item["id"] for item in subject_search_response.json()] == [note_id]
    subject_filter_response = await client.get(
        f"/api/v1/notes?subject_id={subject_id}",
        headers=owner_headers,
    )
    assert [item["id"] for item in subject_filter_response.json()] == [note_id]

    update_response = await client.put(
        f"/api/v1/notes/{note_id}",
        headers=owner_headers,
        json={"title": "BFS and DFS study guide", "tags": [], "is_pinned": False},
    )
    assert update_response.status_code == 200
    assert update_response.json()["title"] == "BFS and DFS study guide"
    assert update_response.json()["tags"] == []
    assert update_response.json()["is_pinned"] is False

    assert (await client.get(f"/api/v1/notes/{note_id}", headers=other_headers)).status_code == 404
    assert (
        await client.put(f"/api/v1/notes/{note_id}", headers=other_headers, json={"title": "stolen"})
    ).status_code == 404
    assert (await client.delete(f"/api/v1/notes/{note_id}", headers=other_headers)).status_code == 404

    delete_response = await client.delete(f"/api/v1/notes/{note_id}", headers=owner_headers)
    assert delete_response.status_code == 204
    assert (await client.get(f"/api/v1/notes/{note_id}", headers=owner_headers)).status_code == 404


@pytest.mark.asyncio
async def test_note_links_must_belong_to_the_user_and_match(client: AsyncClient):
    headers = await register_user(client, "notes.links@studyflow.edu")
    semester_id = (
        await client.post("/api/v1/semesters", headers=headers, json={"name": "Semester"})
    ).json()["id"]
    subject_one = (
        await client.post(
            "/api/v1/subjects",
            headers=headers,
            json={"semester_id": semester_id, "name": "Subject One"},
        )
    ).json()
    subject_two = (
        await client.post(
            "/api/v1/subjects",
            headers=headers,
            json={"semester_id": semester_id, "name": "Subject Two"},
        )
    ).json()
    topic_two = (
        await client.post(
            "/api/v1/topics",
            headers=headers,
            json={"subject_id": subject_two["id"], "name": "Topic Two"},
        )
    ).json()

    mismatch = await client.post(
        "/api/v1/notes",
        headers=headers,
        json={
            "title": "Mismatched references",
            "content": "This topic is from another subject.",
            "subject_id": subject_one["id"],
            "topic_id": topic_two["id"],
        },
    )
    assert mismatch.status_code == 400

    blank_title = await client.post(
        "/api/v1/notes",
        headers=headers,
        json={"title": "  ", "content": "Text"},
    )
    assert blank_title.status_code == 422
