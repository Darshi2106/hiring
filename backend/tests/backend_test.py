"""Backend tests for CohortData hiring portal - candidate auth + existing HR flows."""
import os
import time
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://proctored-jobs.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

HR_EMAIL = "hr@cohortdata.com"
HR_PASSWORD = "Cohort@2026"


@pytest.fixture(scope="session")
def hr_token():
    r = requests.post(f"{API}/auth/login", json={"email": HR_EMAIL, "password": HR_PASSWORD})
    assert r.status_code == 200, f"HR login failed: {r.status_code} {r.text}"
    data = r.json()
    assert data["user"]["role"] == "hr_admin"
    return data["token"]


@pytest.fixture(scope="session")
def candidate():
    email = f"test_cand_{uuid.uuid4().hex[:8]}@example.com"
    password = "secret123"
    r = requests.post(f"{API}/candidate/register", json={"name": "Test Cand", "email": email, "password": password})
    assert r.status_code == 200, f"register failed: {r.status_code} {r.text}"
    d = r.json()
    return {"email": email, "password": password, "token": d["token"], "id": d["user"]["id"]}


@pytest.fixture(scope="session")
def a_job_id():
    r = requests.get(f"{API}/jobs")
    assert r.status_code == 200
    jobs = r.json()
    assert len(jobs) > 0, "No seeded jobs"
    return jobs[0]["id"]


# ---------- Candidate Register ----------
class TestCandidateRegister:
    def test_register_success(self):
        email = f"test_reg_{uuid.uuid4().hex[:8]}@example.com"
        r = requests.post(f"{API}/candidate/register", json={"name": "Reg", "email": email, "password": "abc123"})
        assert r.status_code == 200
        d = r.json()
        assert "token" in d and d["user"]["role"] == "candidate"
        assert d["user"]["email"] == email

    def test_register_duplicate_409(self, candidate):
        r = requests.post(f"{API}/candidate/register", json={"name": "x", "email": candidate["email"], "password": "abcdef"})
        assert r.status_code == 409

    def test_register_short_password_400(self):
        # NOTE: server checks duplicate BEFORE length; fresh email required
        email = f"TEST_short_{uuid.uuid4().hex[:8]}@example.com"
        r = requests.post(f"{API}/candidate/register", json={"name": "s", "email": email, "password": "12345"})
        assert r.status_code == 400


# ---------- Candidate Login ----------
class TestCandidateLogin:
    def test_login_success(self, candidate):
        r = requests.post(f"{API}/candidate/login", json={"email": candidate["email"], "password": candidate["password"]})
        assert r.status_code == 200
        assert r.json()["user"]["role"] == "candidate"

    def test_login_wrong_password_401(self, candidate):
        r = requests.post(f"{API}/candidate/login", json={"email": candidate["email"], "password": "wrongwrong"})
        assert r.status_code == 401

    def test_hr_cannot_login_via_candidate(self):
        r = requests.post(f"{API}/candidate/login", json={"email": HR_EMAIL, "password": HR_PASSWORD})
        assert r.status_code == 401, f"HR should not be able to login via candidate route, got {r.status_code}"


# ---------- Candidate /me ----------
class TestCandidateMe:
    def test_me_with_candidate_token(self, candidate):
        r = requests.get(f"{API}/candidate/me", headers={"Authorization": f"Bearer {candidate['token']}"})
        assert r.status_code == 200
        assert r.json()["role"] == "candidate"
        assert r.json()["email"] == candidate["email"]

    def test_me_with_hr_token_403(self, hr_token):
        r = requests.get(f"{API}/candidate/me", headers={"Authorization": f"Bearer {hr_token}"})
        assert r.status_code == 403

    def test_me_no_token_401(self):
        r = requests.get(f"{API}/candidate/me")
        assert r.status_code == 401


# ---------- Applications ----------
class TestApplications:
    def test_apply_with_candidate_attaches_id(self, candidate, a_job_id):
        payload = {"job_id": a_job_id, "name": "Test Cand", "email": candidate["email"], "phone": "1", "resume_url": "", "cover_letter": ""}
        r = requests.post(f"{API}/applications", json=payload, headers={"Authorization": f"Bearer {candidate['token']}"})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d.get("candidate_id") == candidate["id"]

    def test_apply_duplicate_409(self, candidate, a_job_id):
        payload = {"job_id": a_job_id, "name": "Test Cand", "email": candidate["email"]}
        r = requests.post(f"{API}/applications", json=payload, headers={"Authorization": f"Bearer {candidate['token']}"})
        assert r.status_code == 409

    def test_anonymous_apply_works(self, a_job_id):
        payload = {"job_id": a_job_id, "name": "Anon", "email": f"TEST_anon_{uuid.uuid4().hex[:6]}@example.com"}
        r = requests.post(f"{API}/applications", json=payload)
        assert r.status_code == 200
        assert r.json().get("candidate_id") is None

    def test_candidate_applications_list(self, candidate):
        r = requests.get(f"{API}/candidate/applications", headers={"Authorization": f"Bearer {candidate['token']}"})
        assert r.status_code == 200
        apps = r.json()
        assert isinstance(apps, list) and len(apps) >= 1
        a = apps[0]
        for k in ("invite_token", "invite_status", "has_submitted"):
            assert k in a
        # candidate isolation - all apps belong to this candidate
        assert all(x.get("candidate_id") == candidate["id"] for x in apps)

    def test_hr_cannot_use_candidate_applications(self, hr_token):
        r = requests.get(f"{API}/candidate/applications", headers={"Authorization": f"Bearer {hr_token}"})
        assert r.status_code == 403


# ---------- Existing HR flows ----------
class TestHRExisting:
    def test_hr_login(self):
        r = requests.post(f"{API}/auth/login", json={"email": HR_EMAIL, "password": HR_PASSWORD})
        assert r.status_code == 200
        assert r.json()["user"]["role"] == "hr_admin"

    def test_hr_me(self, hr_token):
        r = requests.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {hr_token}"})
        assert r.status_code == 200
        assert r.json()["role"] == "hr_admin"

    def test_hr_applications(self, hr_token):
        r = requests.get(f"{API}/hr/applications", headers={"Authorization": f"Bearer {hr_token}"})
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_invite_and_submit_flow(self, hr_token, candidate, a_job_id):
        # Ensure an application exists for this candidate (xdist workers have separate sessions)
        r = requests.get(f"{API}/candidate/applications", headers={"Authorization": f"Bearer {candidate['token']}"})
        assert r.status_code == 200
        apps = r.json()
        if not apps:
            payload = {"job_id": a_job_id, "name": "Test Cand", "email": candidate["email"]}
            ar = requests.post(f"{API}/applications", json=payload, headers={"Authorization": f"Bearer {candidate['token']}"})
            assert ar.status_code == 200, ar.text
            r = requests.get(f"{API}/candidate/applications", headers={"Authorization": f"Bearer {candidate['token']}"})
            apps = r.json()
        assert apps, "No app found for candidate"
        app_id = apps[0]["id"]

        # send invite
        r = requests.post(f"{API}/hr/invite", json={"application_id": app_id}, headers={"Authorization": f"Bearer {hr_token}"})
        assert r.status_code == 200
        token = r.json()["token"]
        assert token

        # exam GET
        r = requests.get(f"{API}/exam/{token}")
        assert r.status_code == 200
        exam = r.json()
        assert "mcqs" in exam

        # submit exam - claude scoring
        payload = {
            "invite_token": token,
            "mcq_answers": {m["id"]: 0 for m in exam["mcqs"]},
            "short_answers": {sa["id"]: "This is my own honest answer written from scratch." for sa in exam["short_answers"]},
            "coding_answer": "def x(): return 1",
            "violations": [],
            "webcam_snapshots": [],
            "time_taken_seconds": 100,
        }
        r = requests.post(f"{API}/exam/submit", json=payload, timeout=90)
        assert r.status_code == 200, r.text
        d = r.json()
        assert "submission_id" in d and "ai_risk_avg" in d and "mcq_score" in d
