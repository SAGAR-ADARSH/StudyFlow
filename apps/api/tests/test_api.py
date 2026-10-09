from datetime import date, timedelta
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_auth_flow(client: AsyncClient):
    # 1. Register User
    reg_payload = {
        "email": " Student@StudyFlow.edu ",
        "password": "Password123!",
        "display_name": "Adarsh Sagar",
        "college_name": "College of Technology",
        "course_name": "MCA",
    }
    reg_resp = await client.post("/api/v1/auth/register", json=reg_payload)
    assert reg_resp.status_code == 201
    reg_data = reg_resp.json()
    assert "access_token" in reg_data
    assert reg_data["user"]["email"] == "student@studyflow.edu"
    assert reg_data["user"]["display_name"] == "Adarsh Sagar"
    assert reg_data["user"]["course_name"] == "MCA"

    token = reg_data["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Duplicate registration should return 409
    dup_resp = await client.post("/api/v1/auth/register", json=reg_payload)
    assert dup_resp.status_code == 409

    # 2. Login
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "student@studyflow.edu", "password": "Password123!"},
    )
    assert login_resp.status_code == 200
    login_data = login_resp.json()
    assert "access_token" in login_data

    # Invalid login
    invalid_login = await client.post(
        "/api/v1/auth/login",
        json={"email": "student@studyflow.edu", "password": "WrongPassword"},
    )
    assert invalid_login.status_code == 401

    # 3. Get /auth/me
    me_resp = await client.get("/api/v1/auth/me", headers=headers)
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == "student@studyflow.edu"

    # 4. Update Profile
    update_resp = await client.put(
        "/api/v1/users/me",
        headers=headers,
        json={"display_name": "Adarsh S.", "college_name": "Tech University"},
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["display_name"] == "Adarsh S."
    assert update_resp.json()["college_name"] == "Tech University"


@pytest.mark.asyncio
async def test_full_academic_crud_flow(client: AsyncClient):
    # Register student
    reg_resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "mca_student@studyflow.edu",
            "password": "SecurePassword123",
            "display_name": "MCA Student",
            "course_name": "MCA",
        },
    )
    token = reg_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. SEMESTERS CRUD
    # Create Semester 1
    sem1_resp = await client.post(
        "/api/v1/semesters",
        headers=headers,
        json={
            "name": "MCA Semester 1",
            "semester_number": 1,
            "start_date": "2026-08-01",
            "end_date": "2026-12-15",
            "is_active": True,
        },
    )
    assert sem1_resp.status_code == 201
    sem1 = sem1_resp.json()
    assert sem1["name"] == "MCA Semester 1"
    sem1_id = sem1["id"]

    # Create Semester 2
    sem2_resp = await client.post(
        "/api/v1/semesters",
        headers=headers,
        json={
            "name": "MCA Semester 2",
            "semester_number": 2,
            "start_date": "2027-01-10",
            "end_date": "2027-05-20",
            "is_active": False,
        },
    )
    assert sem2_resp.status_code == 201
    sem2_id = sem2_resp.json()["id"]

    # List Semesters
    list_sem = await client.get("/api/v1/semesters", headers=headers)
    assert list_sem.status_code == 200
    assert len(list_sem.json()) == 2

    # Activate Semester 2
    act_resp = await client.post(f"/api/v1/semesters/{sem2_id}/activate", headers=headers)
    assert act_resp.status_code == 200
    assert act_resp.json()["is_active"] is True

    # 2. SUBJECTS CRUD
    # Create Subject in Semester 1
    sub1_resp = await client.post(
        "/api/v1/subjects",
        headers=headers,
        json={
            "semester_id": sem1_id,
            "name": "Data Structures & Algorithms",
            "code": "MCA-101",
            "color": "#4F46E5",
            "credits": 4,
            "difficulty_level": "Hard",
            "target_grade": "A+",
            "description": "Core computer science data structures and complexity analysis",
        },
    )
    assert sub1_resp.status_code == 201
    sub1 = sub1_resp.json()
    assert sub1["code"] == "MCA-101"
    sub1_id = sub1["id"]

    # Create Subject in Semester 2
    sub2_resp = await client.post(
        "/api/v1/subjects",
        headers=headers,
        json={
            "semester_id": sem2_id,
            "name": "Database Management Systems",
            "code": "MCA-201",
            "color": "#10B981",
            "credits": 3,
            "difficulty_level": "Medium",
        },
    )
    assert sub2_resp.status_code == 201
    sub2_id = sub2_resp.json()["id"]

    # List subjects with semester filter
    list_subj_sem1 = await client.get(f"/api/v1/subjects?semester_id={sem1_id}", headers=headers)
    assert len(list_subj_sem1.json()) == 1
    assert list_subj_sem1.json()[0]["name"] == "Data Structures & Algorithms"

    # 3. TOPICS CRUD
    # Create Topics for DSA
    top1_resp = await client.post(
        "/api/v1/topics",
        headers=headers,
        json={
            "subject_id": sub1_id,
            "name": "Binary Search Trees and AVL Trees",
            "description": "Tree balancing rotations and complexity",
            "unit_number": 2,
            "priority": "High",
            "status": "Pending",
            "estimated_hours": 3.5,
            "importance_score": 5,
        },
    )
    assert top1_resp.status_code == 201
    top1 = top1_resp.json()
    assert top1["name"] == "Binary Search Trees and AVL Trees"
    top1_id = top1["id"]

    top2_resp = await client.post(
        "/api/v1/topics",
        headers=headers,
        json={
            "subject_id": sub1_id,
            "name": "Graph Traversal Algorithms (BFS/DFS)",
            "unit_number": 3,
            "priority": "Medium",
            "status": "In Progress",
            "estimated_hours": 2.0,
            "completed_hours": 1.0,
        },
    )
    assert top2_resp.status_code == 201
    top2_id = top2_resp.json()["id"]

    # List Topics for Subject
    list_top = await client.get(f"/api/v1/topics?subject_id={sub1_id}", headers=headers)
    assert len(list_top.json()) == 2

    # Update Topic Status
    patch_top = await client.patch(
        f"/api/v1/topics/{top1_id}/status",
        headers=headers,
        json={"status": "Completed", "completed_hours": 3.5},
    )
    assert patch_top.status_code == 200
    assert patch_top.json()["status"] == "Completed"
    assert patch_top.json()["completed_hours"] == 3.5

    # 4. EXAMS CRUD
    # Create Exam for DSA
    exam_date = (date.today() + timedelta(days=14)).isoformat()
    exam_resp = await client.post(
        "/api/v1/exams",
        headers=headers,
        json={
            "subject_id": sub1_id,
            "semester_id": sem1_id,
            "title": "DSA Midterm Theory Exam",
            "exam_type": "Theory",
            "exam_date": exam_date,
            "start_time": "10:00 AM",
            "duration_minutes": 180,
            "total_marks": 100.0,
            "passing_marks": 40.0,
            "target_marks": 90.0,
            "location": "Exam Hall 3",
            "notes": "Bring non-programmable calculator",
        },
    )
    assert exam_resp.status_code == 201
    exam_data = exam_resp.json()
    assert exam_data["title"] == "DSA Midterm Theory Exam"
    assert exam_data["days_remaining"] == 14
    exam_id = exam_data["id"]

    # Get Single Exam
    get_ex = await client.get(f"/api/v1/exams/{exam_id}", headers=headers)
    assert get_ex.status_code == 200
    assert get_ex.json()["subject_name"] == "Data Structures & Algorithms"

    # Filter upcoming exams
    upcoming_resp = await client.get("/api/v1/exams?upcoming=true", headers=headers)
    assert upcoming_resp.status_code == 200
    assert len(upcoming_resp.json()) >= 1

    # Update Exam
    put_ex = await client.put(
        f"/api/v1/exams/{exam_id}",
        headers=headers,
        json={"obtained_marks": 92.0, "status": "Completed"},
    )
    assert put_ex.status_code == 200
    assert put_ex.json()["obtained_marks"] == 92.0
    assert put_ex.json()["status"] == "Completed"

    # Delete Topic
    del_top = await client.delete(f"/api/v1/topics/{top2_id}", headers=headers)
    assert del_top.status_code == 204

    # Delete Subject (Cascades to remaining topic and exam)
    del_sub = await client.delete(f"/api/v1/subjects/{sub1_id}", headers=headers)
    assert del_sub.status_code == 204

    # Verify Exam deleted
    get_deleted_ex = await client.get(f"/api/v1/exams/{exam_id}", headers=headers)
    assert get_deleted_ex.status_code == 404


@pytest.mark.asyncio
async def test_user_data_isolation(client: AsyncClient):
    # User 1
    u1_resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "u1@test.com", "password": "Password123!", "display_name": "User 1"},
    )
    u1_token = u1_resp.json()["access_token"]
    u1_headers = {"Authorization": f"Bearer {u1_token}"}

    # User 2
    u2_resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "u2@test.com", "password": "Password123!", "display_name": "User 2"},
    )
    u2_token = u2_resp.json()["access_token"]
    u2_headers = {"Authorization": f"Bearer {u2_token}"}

    # User 1 creates semester
    sem_resp = await client.post(
        "/api/v1/semesters",
        headers=u1_headers,
        json={"name": "User 1 Sem"},
    )
    u1_sem_id = sem_resp.json()["id"]

    # User 2 tries to fetch User 1's semester -> 404
    get_res = await client.get(f"/api/v1/semesters/{u1_sem_id}", headers=u2_headers)
    assert get_res.status_code == 404

    # User 2 listing semesters sees 0
    u2_list = await client.get("/api/v1/semesters", headers=u2_headers)
    assert len(u2_list.json()) == 0


@pytest.mark.asyncio
async def test_unauthorized_endpoints(client: AsyncClient):
    endpoints = [
        ("GET", "/api/v1/auth/me"),
        ("GET", "/api/v1/users/me"),
        ("GET", "/api/v1/semesters"),
        ("POST", "/api/v1/semesters"),
        ("GET", "/api/v1/subjects"),
        ("GET", "/api/v1/topics"),
        ("GET", "/api/v1/exams"),
        ("GET", "/api/v1/notes"),
        ("POST", "/api/v1/notes"),
    ]
    for method, url in endpoints:
        if method == "GET":
            resp = await client.get(url)
        else:
            resp = await client.post(url, json={})
        assert resp.status_code == 401
