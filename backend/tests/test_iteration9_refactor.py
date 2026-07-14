"""Iteration 9: regression after router refactor + open-roles sync verification."""
import os
import uuid
import pytest
import requests

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or "https://proctored-jobs.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

HR_EMAIL = "hr@cohortdata.com"
HR_PASSWORD = "Cohort@2026"
MASTER_EMAIL = "darshan@cohortdata.com"
MASTER_PASSWORD = "MasterCohort@2026"

CANONICAL_OPEN = {
    "Quality Analyst",
    "Annotator / Associate",
    "Project Coordinator",
    "Project Associate",
    "Global Sales Director",
}


@pytest.fixture(scope="module")
def hr_token():
    r = requests.post(f"{API}/auth/login", json={"email": HR_EMAIL, "password": HR_PASSWORD})
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="module")
def master_token():
    r = requests.post(f"{API}/auth/login", json={"email": MASTER_EMAIL, "password": MASTER_PASSWORD})
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="module")
def hr_headers(hr_token):
    return {"Authorization": f"Bearer {hr_token}"}


# ---------- Open Roles Sync ----------
class TestOpenRolesSync:
    def test_open_jobs_are_exactly_5_canonical(self):
        r = requests.get(f"{API}/jobs", params={"status": "open"})
        assert r.status_code == 200
        jobs = r.json()
        titles = {j["title"] for j in jobs}
        assert titles == CANONICAL_OPEN, f"Expected {CANONICAL_OPEN}, got {titles}"
        assert len(jobs) == 5

    def test_closed_jobs_include_legacy_and_test(self, hr_headers):
        r = requests.get(f"{API}/jobs", params={"status": "closed"}, headers=hr_headers)
        assert r.status_code == 200
        closed = r.json()
        assert len(closed) > 20, f"Expected many closed jobs, got {len(closed)}"

    def test_total_jobs_count(self, hr_headers):
        r_open = requests.get(f"{API}/jobs", params={"status": "open"})
        r_closed = requests.get(f"{API}/jobs", params={"status": "closed"}, headers=hr_headers)
        total = len(r_open.json()) + len(r_closed.json())
        # Expected ~191-193
        assert 150 <= total <= 250, f"Total jobs {total} outside expected range"


# ---------- Router refactor regression ----------
class TestRefactorRegression:
    def test_auth_login_hr(self):
        r = requests.post(f"{API}/auth/login", json={"email": HR_EMAIL, "password": HR_PASSWORD})
        assert r.status_code == 200
        assert r.json()["user"]["role"] == "hr_admin"

    def test_auth_me(self, hr_headers):
        r = requests.get(f"{API}/auth/me", headers=hr_headers)
        assert r.status_code == 200
        assert r.json()["role"] == "hr_admin"

    def test_candidate_register_login_me(self):
        email = f"TEST_it9_{uuid.uuid4().hex[:8]}@example.com"
        r = requests.post(f"{API}/candidate/register", json={"name": "IT9", "email": email, "password": "abc123"})
        assert r.status_code == 200
        tok = r.json()["token"]
        r = requests.post(f"{API}/candidate/login", json={"email": email, "password": "abc123"})
        assert r.status_code == 200
        r = requests.get(f"{API}/candidate/me", headers={"Authorization": f"Bearer {tok}"})
        assert r.status_code == 200
        r = requests.get(f"{API}/candidate/applications", headers={"Authorization": f"Bearer {tok}"})
        assert r.status_code == 200

    def test_jobs_endpoints(self):
        r = requests.get(f"{API}/jobs", params={"status": "open"})
        assert r.status_code == 200
        jobs = r.json()
        assert len(jobs) > 0
        jid = jobs[0]["id"]
        r = requests.get(f"{API}/jobs/{jid}")
        assert r.status_code == 200
        assert r.json()["id"] == jid

    def test_applications_endpoint(self):
        r = requests.get(f"{API}/jobs", params={"status": "open"})
        jid = r.json()[0]["id"]
        email = f"TEST_it9app_{uuid.uuid4().hex[:8]}@example.com"
        r = requests.post(f"{API}/applications", json={"job_id": jid, "name": "IT9", "email": email})
        assert r.status_code == 200

    def test_hr_jobs_crud(self, hr_headers):
        # create
        payload = {"title": f"TEST_IT9_{uuid.uuid4().hex[:6]}", "location": "Remote", "department": "Eng",
                   "description": "d", "requirements": ["r"], "status": "open"}
        r = requests.post(f"{API}/hr/jobs", json=payload, headers=hr_headers)
        assert r.status_code == 200, r.text
        jid = r.json()["id"]
        # read
        r = requests.get(f"{API}/hr/jobs/{jid}", headers=hr_headers)
        assert r.status_code == 200
        # update
        r = requests.put(f"{API}/hr/jobs/{jid}", json={"title": payload["title"], "location": "NY",
                         "department": "Eng", "description": "d2", "requirements": ["r"], "status": "closed"},
                         headers=hr_headers)
        assert r.status_code == 200
        # delete
        r = requests.delete(f"{API}/hr/jobs/{jid}", headers=hr_headers)
        assert r.status_code == 200

    def test_hr_applications_default_sort(self, hr_headers):
        r = requests.get(f"{API}/hr/applications", headers=hr_headers)
        assert r.status_code == 200
        apps = r.json()
        assert isinstance(apps, list)
        assert len(apps) > 0
        # trust-sorted DESC (nulls last)
        scored = [a.get("trust_score") for a in apps if a.get("trust_score") is not None]
        if len(scored) >= 2:
            assert scored == sorted(scored, reverse=True), "apps not sorted by trust DESC"

    def test_hr_stats(self, hr_headers):
        r = requests.get(f"{API}/hr/stats", headers=hr_headers)
        assert r.status_code == 200
        d = r.json()
        assert d["open_jobs"] == 5
        assert "total_applications" in d and "submissions" in d

    def test_hr_time_to_hire(self, hr_headers):
        r = requests.get(f"{API}/hr/stats/time-to-hire", headers=hr_headers)
        assert r.status_code == 200

    def test_hr_question_bank(self, hr_headers):
        r = requests.get(f"{API}/hr/question-bank", headers=hr_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_hr_job_assignment(self, hr_headers):
        r = requests.get(f"{API}/jobs", params={"status": "open"})
        jid = r.json()[0]["id"]
        r = requests.get(f"{API}/hr/jobs/{jid}/assignment", headers=hr_headers)
        assert r.status_code == 200

    def test_master_endpoints(self, master_token):
        h = {"Authorization": f"Bearer {master_token}"}
        r = requests.get(f"{API}/master/users", headers=h)
        assert r.status_code == 200
        assert isinstance(r.json(), list)


# ---------- Idempotency of sync ----------
class TestSyncIdempotent:
    def test_open_roles_stable_after_multiple_calls(self):
        # simulate re-check: results should be identical
        r1 = requests.get(f"{API}/jobs", params={"status": "open"})
        r2 = requests.get(f"{API}/jobs", params={"status": "open"})
        t1 = {j["title"] for j in r1.json()}
        t2 = {j["title"] for j in r2.json()}
        assert t1 == t2 == CANONICAL_OPEN
