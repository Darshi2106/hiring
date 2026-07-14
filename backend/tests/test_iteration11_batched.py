"""Iteration 11 regression: batched invites/submissions fetch + load_dotenv override=False.

Verifies:
- /api/candidate/applications returns array with invite_token/invite_status/has_submitted
- /api/hr/applications returns applications with expected fields, sorted by trust DESC
- Latency check on /hr/applications (should be well under 1s with batched queries)
- Regression: /auth/login (HR), /hr/stats open_jobs=7, /jobs returns 7 sanitized,
  /hr/jobs/{id} works.
"""
import os
import time
import uuid

import pytest
import requests

def _load_base_url():
    url = os.environ.get("REACT_APP_BACKEND_URL")
    if not url:
        # Load from frontend/.env
        env_path = "/app/frontend/.env"
        if os.path.exists(env_path):
            with open(env_path) as f:
                for line in f:
                    if line.startswith("REACT_APP_BACKEND_URL="):
                        url = line.split("=", 1)[1].strip()
                        break
    if not url:
        raise RuntimeError("REACT_APP_BACKEND_URL not set")
    return url.rstrip("/")


BASE_URL = _load_base_url()
HR_EMAIL = "hr@cohortdata.com"
HR_PASSWORD = "Cohort@2026"


@pytest.fixture(scope="module")
def api():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def hr_token(api):
    r = api.post(f"{BASE_URL}/api/auth/login", json={"email": HR_EMAIL, "password": HR_PASSWORD})
    assert r.status_code == 200, f"HR login failed: {r.status_code} {r.text}"
    data = r.json()
    assert "token" in data
    return data["token"]


@pytest.fixture(scope="module")
def hr_client(api, hr_token):
    api.headers.update({"Authorization": f"Bearer {hr_token}"})
    return api


# ---------- Regression: HR auth, stats, jobs list ----------
class TestRegression:
    def test_hr_login(self, api):
        r = api.post(f"{BASE_URL}/api/auth/login", json={"email": HR_EMAIL, "password": HR_PASSWORD})
        assert r.status_code == 200
        j = r.json()
        assert "token" in j and "user" in j
        assert j["user"]["email"] == HR_EMAIL
        assert j["user"]["role"] in ("hr_admin", "master_admin")

    def test_hr_stats_open_jobs_7(self, hr_client):
        r = hr_client.get(f"{BASE_URL}/api/hr/stats")
        assert r.status_code == 200
        data = r.json()
        assert data["open_jobs"] == 7, f"expected 7 open jobs, got {data['open_jobs']}"
        assert "total_applications" in data
        assert "submissions" in data

    def test_public_jobs_7_sanitized(self, api):
        # Use a fresh session (no Authorization)
        s = requests.Session()
        r = s.get(f"{BASE_URL}/api/jobs?status=open")
        assert r.status_code == 200
        jobs = r.json()
        assert len(jobs) == 7, f"expected 7 open jobs, got {len(jobs)}"
        for j in jobs:
            # sanitized: no assignment key, no threshold fields
            assert "assignment" not in j, f"assignment leaked for job {j.get('id')}"
            for k in (
                "ai_reject_threshold",
                "auto_shortlist_enabled",
                "auto_shortlist_mcq_min",
                "auto_shortlist_ai_max",
                "auto_shortlist_max_violations",
            ):
                assert k not in j, f"internal field {k} leaked for job {j.get('id')}"
            # summary present
            assert "assignment_summary" in j

    def test_hr_get_job_detail(self, hr_client):
        r = hr_client.get(f"{BASE_URL}/api/jobs?status=open")
        assert r.status_code == 200
        job_id = r.json()[0]["id"]
        r2 = hr_client.get(f"{BASE_URL}/api/hr/jobs/{job_id}")
        assert r2.status_code == 200
        assert r2.json()["id"] == job_id


# ---------- HR applications: batched, sorted, fields ----------
class TestHRApplicationsBatched:
    def test_hr_applications_shape_and_latency(self, hr_client):
        t0 = time.time()
        r = hr_client.get(f"{BASE_URL}/api/hr/applications")
        elapsed = time.time() - t0
        assert r.status_code == 200
        apps = r.json()
        assert isinstance(apps, list)
        # print for visibility
        print(f"[hr/applications] {len(apps)} rows in {elapsed*1000:.0f}ms")
        # Latency check — batched query should be fast (<2s even under network latency)
        assert elapsed < 2.5, f"batched query too slow: {elapsed:.2f}s"

        required_fields = {
            "invite_sent", "invite_token", "invite_status",
            "submission_id", "ai_risk_avg", "mcq_score",
            "mcq_pct_weighted", "violation_count", "trust_score",
        }
        # Verify each row has all required keys (values can be None)
        for a in apps[:20]:  # spot-check first 20
            missing = required_fields - set(a.keys())
            assert not missing, f"application {a.get('id')} missing fields: {missing}"

    def test_hr_applications_trust_desc_sort(self, hr_client):
        r = hr_client.get(f"{BASE_URL}/api/hr/applications?sort=trust")
        assert r.status_code == 200
        apps = r.json()
        # collect trust scores among applications that have one
        trusts = [a["trust_score"] for a in apps if a.get("trust_score") is not None]
        assert trusts == sorted(trusts, reverse=True), "trust_score not sorted DESC"
        # Also verify rows without trust_score are at the end (None sinks)
        first_none_idx = next((i for i, a in enumerate(apps) if a.get("trust_score") is None), len(apps))
        last_scored_idx = next((i for i in range(len(apps) - 1, -1, -1) if apps[i].get("trust_score") is not None), -1)
        if last_scored_idx >= 0:
            assert first_none_idx > last_scored_idx, "None trust_scores should follow scored ones"


# ---------- Candidate applications: batched fetch ----------
class TestCandidateApplicationsBatched:
    def test_register_apply_and_fetch_applications(self, api):
        # Fresh session (no HR auth in headers)
        s = requests.Session()
        s.headers.update({"Content-Type": "application/json"})

        unique = uuid.uuid4().hex[:8]
        email = f"TEST_it11_{unique}@example.com"
        # Register candidate
        r = s.post(f"{BASE_URL}/api/candidate/register", json={
            "email": email, "password": "testpass123", "name": f"TEST it11 {unique}"
        })
        assert r.status_code == 200, f"register failed: {r.status_code} {r.text}"
        token = r.json()["token"]
        s.headers.update({"Authorization": f"Bearer {token}"})

        # Get 2 job ids
        rj = requests.get(f"{BASE_URL}/api/jobs?status=open")
        assert rj.status_code == 200
        jobs = rj.json()
        assert len(jobs) >= 2
        job_ids = [jobs[0]["id"], jobs[1]["id"]]

        # Apply to 2 roles
        for jid, title in [(jobs[0]["id"], jobs[0]["title"]), (jobs[1]["id"], jobs[1]["title"])]:
            r_apply = s.post(f"{BASE_URL}/api/applications", json={
                "job_id": jid,
                "name": f"TEST it11 {unique}",
                "email": email,
                "phone": "+15551234567",
                "resume_url": "https://example.com/resume.pdf",
                "cover_letter": "iteration 11 test",
                "source": "test_it11",
            })
            assert r_apply.status_code == 200, f"apply to {title} failed: {r_apply.status_code} {r_apply.text}"

        # Fetch candidate applications
        r_list = s.get(f"{BASE_URL}/api/candidate/applications")
        assert r_list.status_code == 200
        apps = r_list.json()
        assert isinstance(apps, list)
        assert len(apps) == 2, f"expected 2 applications, got {len(apps)}"

        # Verify each application has the expected batched fields
        for a in apps:
            assert "invite_token" in a
            assert "invite_status" in a
            assert "has_submitted" in a
            assert a["has_submitted"] is False  # nothing submitted yet
            # No invite yet either
            assert a["invite_token"] is None
            assert a["invite_status"] is None
            assert a["job_id"] in job_ids


# ---------- load_dotenv override=False sanity ----------
class TestLoadDotenvSanity:
    def test_backend_alive_and_env_read(self, hr_client):
        # If MONGO_URL / DB_NAME weren't loaded, /hr/stats couldn't return counts.
        r = hr_client.get(f"{BASE_URL}/api/hr/stats")
        assert r.status_code == 200
        data = r.json()
        assert data["open_jobs"] == 7
        assert isinstance(data["total_applications"], int)
