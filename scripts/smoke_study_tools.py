"""Live study-tools check through the actual same-origin Next.js proxy.

Run API :8000 and web :3000, then `python scripts/smoke_study_tools.py`.
Creates a disposable account; does not print tokens or private document content.
"""
import time

import httpx


def main():
    checks = 0
    with httpx.Client(base_url="http://localhost:3000/api/v1", timeout=30) as client:
        def request(method, path, payload=None, expected=200):
            nonlocal checks
            response = client.request(method, path, json=payload)
            assert response.status_code == expected, f"{method} {path}: HTTP {response.status_code}"
            checks += 1
            return response.json() if response.status_code != 204 else None

        account = request("POST", "/auth/register", {
            "email": f"study-tools.{time.time_ns()}@studyflow.edu",
            "password": "StudyToolsRegression123!", "display_name": "Study Tools Smoke",
        }, 201)
        client.headers["X-StudyFlow-Token"] = account["access_token"]
        report = request("GET", "/analytics")
        assert report["tasks"]["total"] == report["flashcards"]["total"] == 0
        semester = request("POST", "/semesters", {"name": "Smoke Term"}, 201)
        subject = request("POST", "/subjects", {"name": "OS", "semester_id": semester["id"]}, 201)
        card = request("POST", "/flashcards", {"front":"What is a process?", "back":"A program in execution.", "subject_id":subject["id"]}, 201)
        request("PATCH", f"/flashcards/{card['id']}/review", {"review_status":"known"})
        assert request("GET", f"/flashcards/{card['id']}")["review_status"] == "known"
        task_data = {"title":"Review scheduling", "subject_id":subject["id"], "due_date":"2020-01-01"}
        task = request("POST", "/tasks", task_data, 201)
        request("POST", "/tasks", task_data, 409)
        assert request("GET", "/tasks?overdue=true")[0]["id"] == task["id"]
        session = request("POST", "/study-sessions", {"subject_id":subject["id"]}, 201)
        request("POST", f"/study-sessions/{session['id']}/pause")
        assert request("GET", "/study-sessions/active")["status"] == "paused"
        request("POST", "/study-sessions", {"subject_id":subject["id"]}, 400)
        request("POST", f"/study-sessions/{session['id']}/resume")
        request("POST", f"/study-sessions/{session['id']}/finish")
        assert request("GET", "/study-sessions/active") is None
        report = request("GET", "/analytics")
        assert report["tasks"]["overdue"] == 1 and report["flashcards"]["known"] == 1
        assert report["study_time"]["completed_sessions"] == 1
        request("DELETE", f"/tasks/{task['id']}", expected=204)
        request("DELETE", f"/flashcards/{card['id']}", expected=204)
    print(f"PASS: {checks} live HTTP checks plus saved-record assertions through Next.js proxy.")


if __name__ == "__main__":
    main()
