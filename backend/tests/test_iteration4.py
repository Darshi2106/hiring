"""Iteration 4 backend tests: question bank, import, AI auto-reject, HR override, schedule interview."""
import os
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://proctored-jobs.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

HR_EMAIL = "hr@cohortdata.com"
HR_PASSWORD = "Cohort@2026"


# ---------------- Fixtures ----------------
@pytest.fixture(scope="module")
def hr_token():
    r = requests.post(f"{API}/auth/login", json={"email": HR_EMAIL, "password": HR_PASSWORD})
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="module")
def hr_headers(hr_token):
    return {"Authorization": f"Bearer {hr_token}"}


@pytest.fixture(scope="module")
def cand_token():
    email = f"test_cand_it4_{uuid.uuid4().hex[:8]}@example.com"
    r = requests.post(f"{API}/candidate/register", json={"name": "IT4 Cand", "email": email, "password": "secret123"})
    assert r.status_code == 200, r.text
    d = r.json()
    return {"email": email, "token": d["token"], "id": d["user"]["id"]}


def _create_job(hr_headers, threshold=70, calendly_url=""):
    body = {
        "title": f"IT4 Test Job {uuid.uuid4().hex[:6]}",
        "department": "Tech & Eng",
        "location": "Remote",
        "type": "Full-Time",
        "description": "test",
        "requirements": ["python"],
        "status": "open",
        "ai_reject_threshold": threshold,
        "calendly_url": calendly_url,
    }
    r = requests.post(f"{API}/hr/jobs", json=body, headers=hr_headers)
    assert r.status_code == 200, r.text
    return r.json()


# ---------------- Question bank ----------------
class TestQuestionBank:
    def test_list_modules(self, hr_headers):
        r = requests.get(f"{API}/hr/question-bank", headers=hr_headers)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert len(data) >= 20, f"Expected >=20 modules, got {len(data)}"
        for m in data:
            for k in ("id", "title", "category", "description", "count"):
                assert k in m, f"missing {k} in {m}"

    def test_mcq_ml_detail(self, hr_headers):
        r = requests.get(f"{API}/hr/question-bank/mcq_ml", headers=hr_headers)
        assert r.status_code == 200
        data = r.json()
        assert "questions" in data
        mcqs = [q for q in data["questions"] if q["type"] == "mcq"]
        assert len(mcqs) == 10, f"Expected 10 MCQs, got {len(mcqs)}"
        for q in mcqs:
            assert isinstance(q["options"], list) and len(q["options"]) >= 2
            assert isinstance(q["correct_index"], int)
            assert 0 <= q["correct_index"] < len(q["options"])

    def test_invalid_module_id(self, hr_headers):
        r = requests.get(f"{API}/hr/question-bank/nope_missing", headers=hr_headers)
        assert r.status_code == 404

    def test_auth_required(self):
        r = requests.get(f"{API}/hr/question-bank")
        assert r.status_code in (401, 403)


# ---------------- Import ----------------
class TestImport:
    def test_import_appends_unique(self, hr_headers):
        job = _create_job(hr_headers)
        job_id = job["id"]

        # Get some question IDs from mcq_ml + sa_behavioral + code_python_beginner
        r = requests.get(f"{API}/hr/question-bank/mcq_ml", headers=hr_headers)
        mcq_ids = [q["id"] for q in r.json()["questions"][:3]]
        r = requests.get(f"{API}/hr/question-bank/sa_behavioral", headers=hr_headers)
        sa_ids = [q["id"] for q in r.json()["questions"][:2]]
        r = requests.get(f"{API}/hr/question-bank/code_python_beginner", headers=hr_headers)
        code_ids = [q["id"] for q in r.json()["questions"][:1]]

        # Clear coding first so it can be imported
        # Get current assignment
        r = requests.get(f"{API}/hr/jobs/{job_id}/assignment", headers=hr_headers)
        cur = r.json()
        cur["coding"] = None
        rp = requests.put(f"{API}/hr/jobs/{job_id}/assignment", json=cur, headers=hr_headers)
        assert rp.status_code == 200, rp.text

        all_ids = mcq_ids + sa_ids + code_ids
        r = requests.post(f"{API}/hr/jobs/{job_id}/assignment/import",
                          json={"question_ids": all_ids}, headers=hr_headers)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["added_mcq"] == 3
        assert data["added_sa"] == 2
        assert data["added_code"] == 1

        # Re-import same ids: duplicates skipped
        r = requests.post(f"{API}/hr/jobs/{job_id}/assignment/import",
                          json={"question_ids": all_ids}, headers=hr_headers)
        assert r.status_code == 200
        d2 = r.json()
        assert d2["added_mcq"] == 0
        assert d2["added_sa"] == 0
        assert d2["added_code"] == 0


# ---------------- Job model ai_reject_threshold + calendly_url ----------------
class TestJobModel:
    def test_create_and_get_returns_new_fields(self, hr_headers):
        job = _create_job(hr_headers, threshold=42, calendly_url="https://calendly.com/testco/interview")
        job_id = job["id"]
        r = requests.get(f"{API}/hr/jobs/{job_id}", headers=hr_headers)
        assert r.status_code == 200
        d = r.json()
        assert d["ai_reject_threshold"] == 42
        assert d["calendly_url"] == "https://calendly.com/testco/interview"

    def test_update_persists_fields(self, hr_headers):
        job = _create_job(hr_headers)
        job_id = job["id"]
        body = {
            "title": job["title"],
            "department": job["department"],
            "location": job["location"],
            "type": job["type"],
            "description": job["description"],
            "requirements": job["requirements"],
            "status": "open",
            "ai_reject_threshold": 25,
            "calendly_url": "https://calendly.com/x/y",
        }
        r = requests.put(f"{API}/hr/jobs/{job_id}", json=body, headers=hr_headers)
        assert r.status_code == 200
        r = requests.get(f"{API}/hr/jobs/{job_id}", headers=hr_headers)
        d = r.json()
        assert d["ai_reject_threshold"] == 25
        assert d["calendly_url"] == "https://calendly.com/x/y"


# ---------------- Helper: create app+invite+submit ----------------
def _create_app_and_submit(hr_headers, threshold, calendly_url=""):
    """Creates job w/ threshold, submits an exam. Returns (job_id, app_id, submission_id, submit_json)."""
    job = _create_job(hr_headers, threshold=threshold, calendly_url=calendly_url)
    job_id = job["id"]

    # Reduce assignment complexity: single SA question so scoring is fast
    minimal = {
        "duration_minutes": 30,
        "mcqs": [],
        "short_answers": [{
            "id": "sa1", "question": "Describe your recent project.",
            "min_words": 20, "weight": 1,
        }],
        "coding": None,
    }
    r = requests.put(f"{API}/hr/jobs/{job_id}/assignment", json=minimal, headers=hr_headers)
    assert r.status_code == 200, r.text

    # Apply
    email = f"test_it4_app_{uuid.uuid4().hex[:8]}@example.com"
    r = requests.post(f"{API}/applications", json={
        "job_id": job_id, "name": "IT4 App", "email": email,
        "phone": "", "resume_url": "", "cover_letter": "",
    })
    assert r.status_code == 200, r.text
    app_id = r.json()["id"]

    # Invite
    r = requests.post(f"{API}/hr/invite", json={"application_id": app_id}, headers=hr_headers)
    assert r.status_code == 200, r.text
    token = r.json()["token"]

    # Submit with generic AI-sounding text
    ai_text = ("In today's rapidly evolving landscape, it is important to note that "
               "leveraging synergistic paradigms enables scalable innovation. Furthermore, "
               "by harnessing cutting-edge methodologies, one can facilitate optimal outcomes "
               "and drive transformative change across the ecosystem. Additionally, embracing "
               "holistic frameworks fosters collaborative excellence and sustainable growth.")
    r = requests.post(f"{API}/exam/submit", json={
        "invite_token": token,
        "mcq_answers": {},
        "short_answers": {"sa1": ai_text},
        "coding_answer": "",
        "violations": [],
        "webcam_snapshots": [],
        "time_taken_seconds": 60,
    })
    assert r.status_code == 200, r.text
    sd = r.json()
    return job_id, app_id, sd["submission_id"], sd


# ---------------- Auto-reject on submit ----------------
class TestAutoReject:
    def test_low_threshold_triggers_auto_flag(self, hr_headers):
        # threshold=1 → any real ai score max should trip flag deterministically
        job_id, app_id, sub_id, sd = _create_app_and_submit(hr_headers, threshold=1)
        assert "ai_risk_max" in sd
        assert "auto_flagged" in sd
        # Fetch submission to see all fields
        r = requests.get(f"{API}/hr/submissions/{sub_id}", headers=hr_headers)
        assert r.status_code == 200
        s = r.json()
        assert "ai_risk_max" in s
        assert "ai_reject_threshold" in s
        assert s["ai_reject_threshold"] == 1
        assert "auto_flagged" in s
        assert "hr_override" in s
        assert s["hr_override"] is False

        # Application status
        r = requests.get(f"{API}/hr/applications?job_id={job_id}", headers=hr_headers)
        assert r.status_code == 200
        apps = r.json()
        app = next(a for a in apps if a["id"] == app_id)

        # With threshold=1 and ai_risk_max >=1 (almost certainly true), status should be rejected
        if s["ai_risk_max"] >= 1:
            assert s["auto_flagged"] is True
            assert app["status"] == "assignment_rejected_ai"
        else:
            # Very unlikely, but respect fallback
            assert s["auto_flagged"] is False
            assert app["status"] == "assignment_submitted"

    def test_high_threshold_no_auto_flag(self, hr_headers):
        # threshold=100 → never trip (unless max exactly 100)
        job_id, app_id, sub_id, sd = _create_app_and_submit(hr_headers, threshold=100)
        r = requests.get(f"{API}/hr/submissions/{sub_id}", headers=hr_headers)
        s = r.json()
        assert s["ai_reject_threshold"] == 100
        # If max < 100, auto_flagged is False
        if s["ai_risk_max"] < 100:
            assert s["auto_flagged"] is False


# ---------------- HR override ----------------
class TestOverride:
    def test_override_toggle(self, hr_headers):
        job_id, app_id, sub_id, sd = _create_app_and_submit(hr_headers, threshold=1)
        # Force override=true
        r = requests.post(f"{API}/hr/submissions/{sub_id}/override",
                          json={"override": True}, headers=hr_headers)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["hr_override"] is True
        assert d["application_status"] == "assignment_submitted"

        # Verify submission
        r = requests.get(f"{API}/hr/submissions/{sub_id}", headers=hr_headers)
        assert r.json()["hr_override"] is True

        # Verify application status
        apps = requests.get(f"{API}/hr/applications?job_id={job_id}", headers=hr_headers).json()
        app = next(a for a in apps if a["id"] == app_id)
        assert app["status"] == "assignment_submitted"

        # Toggle back to false
        r = requests.post(f"{API}/hr/submissions/{sub_id}/override",
                          json={"override": False}, headers=hr_headers)
        assert r.status_code == 200
        d = r.json()
        assert d["hr_override"] is False
        assert d["application_status"] == "assignment_rejected_ai"

        apps = requests.get(f"{API}/hr/applications?job_id={job_id}", headers=hr_headers).json()
        app = next(a for a in apps if a["id"] == app_id)
        assert app["status"] == "assignment_rejected_ai"


# ---------------- Schedule interview ----------------
class TestScheduleInterview:
    def test_schedule_with_calendly(self, hr_headers):
        cal = "https://calendly.com/testco/interview-30m"
        job_id, app_id, sub_id, _ = _create_app_and_submit(hr_headers, threshold=100, calendly_url=cal)
        r = requests.post(f"{API}/hr/schedule-interview",
                          json={"application_id": app_id}, headers=hr_headers)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["calendly_url"] == cal
        # Verify application status
        apps = requests.get(f"{API}/hr/applications?job_id={job_id}", headers=hr_headers).json()
        app = next(a for a in apps if a["id"] == app_id)
        assert app["status"] == "interview_scheduled"
        assert app.get("calendly_url") == cal

    def test_schedule_without_calendly_400(self, hr_headers):
        job_id, app_id, _, _ = _create_app_and_submit(hr_headers, threshold=100, calendly_url="")
        r = requests.post(f"{API}/hr/schedule-interview",
                          json={"application_id": app_id}, headers=hr_headers)
        assert r.status_code == 400, r.text

    def test_schedule_nonexistent_404(self, hr_headers):
        # Valid ObjectId format that doesn't exist
        fake_id = "507f1f77bcf86cd799439011"
        r = requests.post(f"{API}/hr/schedule-interview",
                          json={"application_id": fake_id}, headers=hr_headers)
        assert r.status_code == 404, r.text
