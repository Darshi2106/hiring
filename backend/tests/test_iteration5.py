"""Iteration 5 backend tests: weighted MCQ, auto-shortlist, calendly backfill, real Resend."""
import os
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://proctored-jobs.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

HR_EMAIL = "hr@cohortdata.com"
HR_PASSWORD = "Cohort@2026"
MASTER_EMAIL = "darshan@cohortdata.com"
DEFAULT_CALENDLY = "https://calendly.com/darshan-yys"


# ---------------- Fixtures ----------------
@pytest.fixture(scope="module")
def hr_headers():
    r = requests.post(f"{API}/auth/login", json={"email": HR_EMAIL, "password": HR_PASSWORD})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


def _new_candidate():
    email = f"test_cand_it5_{uuid.uuid4().hex[:8]}@example.com"
    r = requests.post(f"{API}/candidate/register", json={"name": "IT5 Cand", "email": email, "password": "secret123"})
    assert r.status_code == 200, r.text
    d = r.json()
    return {"email": email, "token": d["token"], "id": d["user"]["id"]}


def _create_job(hr_headers, **overrides):
    body = {
        "title": f"IT5 Job {uuid.uuid4().hex[:6]}",
        "department": "Tech & Eng",
        "location": "Remote",
        "type": "Full-Time",
        "description": "test",
        "requirements": ["python"],
        "status": "open",
        "ai_reject_threshold": 70,
        "calendly_url": DEFAULT_CALENDLY,
        "auto_shortlist_enabled": True,
        "auto_shortlist_mcq_min": 80,
        "auto_shortlist_ai_max": 10,
        "auto_shortlist_max_violations": 0,
    }
    body.update(overrides)
    r = requests.post(f"{API}/hr/jobs", json=body, headers=hr_headers)
    assert r.status_code == 200, r.text
    return r.json()


def _set_assignment(hr_headers, job_id, mcqs, short_answers=None, coding=None):
    payload = {
        "duration_minutes": 30,
        "mcqs": mcqs,
        "short_answers": short_answers or [],
        "coding": coding,
    }
    r = requests.put(f"{API}/hr/jobs/{job_id}/assignment", json=payload, headers=hr_headers)
    assert r.status_code == 200, r.text
    return r.json()


def _apply_and_invite(hr_headers, job_id, cand):
    r = requests.post(f"{API}/applications", json={
        "job_id": job_id, "name": "IT5 Cand", "email": cand["email"], "phone": "555",
    }, headers={"Authorization": f"Bearer {cand['token']}"})
    assert r.status_code == 200, r.text
    app_id = r.json()["id"]
    r = requests.post(f"{API}/hr/invite", json={"application_id": app_id}, headers=hr_headers)
    assert r.status_code == 200, r.text
    return app_id, r.json()["token"], r.json()


def _submit(token, mcq_answers, violations=None, short_answers=None):
    r = requests.post(f"{API}/exam/submit", json={
        "invite_token": token,
        "mcq_answers": mcq_answers,
        "short_answers": short_answers or {},
        "coding_answer": "",
        "violations": violations or [],
        "webcam_snapshots": [],
        "time_taken_seconds": 100,
    })
    assert r.status_code == 200, r.text
    return r.json()


def _get_app(hr_headers, app_id):
    r = requests.get(f"{API}/hr/applications", headers=hr_headers)
    assert r.status_code == 200
    for a in r.json():
        if a["id"] == app_id:
            return a
    raise AssertionError(f"app {app_id} not found")


# ---------------- Calendly backfill ----------------
class TestCalendlyBackfill:
    def test_all_seeded_jobs_have_calendly_url(self):
        # Backfill semantics: at startup, jobs missing calendly_url get DEFAULT_CALENDLY.
        # Newly-created HR jobs may still have empty calendly_url (not backfilled post-startup).
        r = requests.get(f"{API}/jobs")
        assert r.status_code == 200
        jobs = r.json()
        assert len(jobs) > 0
        # Filter to seeded jobs (they don't have "IT" prefix from test runs)
        seeded = [j for j in jobs if not j["title"].startswith("IT")]
        assert len(seeded) > 0, "No seeded jobs found"
        missing = [j for j in seeded if not j.get("calendly_url")]
        assert len(missing) == 0, f"Seeded jobs missing calendly_url: {[j['title'] for j in missing]}"

    def test_default_calendly_on_seeded_jobs(self):
        # Seeded jobs (not user-edited) should have the default URL
        r = requests.get(f"{API}/jobs")
        assert r.status_code == 200
        jobs = r.json()
        # At least one job should have the default URL
        has_default = any(j.get("calendly_url") == DEFAULT_CALENDLY for j in jobs)
        assert has_default, "Expected at least one job with default calendly URL"


# ---------------- Real Resend email ----------------
class TestResendEmail:
    def test_invite_delivers_real_email(self, hr_headers):
        # Send to master (Resend account owner) to conserve quota - only ONE real send
        job = _create_job(hr_headers)
        # apply as master via public apply endpoint (unauthenticated to skip candidate dup check)
        r = requests.post(f"{API}/applications", json={
            "job_id": job["id"], "name": "Darshan", "email": MASTER_EMAIL, "phone": "555",
        })
        assert r.status_code == 200, r.text
        app_id = r.json()["id"]
        r = requests.post(f"{API}/hr/invite", json={"application_id": app_id}, headers=hr_headers)
        assert r.status_code == 200, r.text
        data = r.json()
        email = data["email"]
        assert email.get("mocked") is not True, f"Email is mocked - RESEND_API_KEY not set? {email}"
        assert email.get("delivered") is True, f"Expected delivered=true, got {email}"
        assert email.get("email_id"), f"Expected email_id in response, got {email}"


# ---------------- Weighted MCQ scoring ----------------
class TestWeightedMCQ:
    def _setup_job(self, hr_headers):
        job = _create_job(hr_headers, auto_shortlist_enabled=False)
        mcqs = [
            {"id": "q1", "question": "1+1?", "options": ["1", "2", "3"], "correct_index": 1, "weight": 1},
            {"id": "q2", "question": "2+2?", "options": ["3", "4", "5"], "correct_index": 1, "weight": 3},
        ]
        _set_assignment(hr_headers, job["id"], mcqs)
        return job

    def test_weight3_correct_only_gives_75(self, hr_headers):
        job = self._setup_job(hr_headers)
        cand = _new_candidate()
        _, token, _ = _apply_and_invite(hr_headers, job["id"], cand)
        # weight-3 correct, weight-1 wrong
        result = _submit(token, {"q1": 0, "q2": 1})
        assert result["mcq_pct_weighted"] == 75, f"Expected 75, got {result}"

    def test_both_correct_gives_100(self, hr_headers):
        job = self._setup_job(hr_headers)
        cand = _new_candidate()
        _, token, _ = _apply_and_invite(hr_headers, job["id"], cand)
        result = _submit(token, {"q1": 1, "q2": 1})
        assert result["mcq_pct_weighted"] == 100

    def test_none_correct_gives_0(self, hr_headers):
        job = self._setup_job(hr_headers)
        cand = _new_candidate()
        _, token, _ = _apply_and_invite(hr_headers, job["id"], cand)
        result = _submit(token, {"q1": 0, "q2": 0})
        assert result["mcq_pct_weighted"] == 0


# ---------------- Auto-shortlist ----------------
class TestAutoShortlist:
    def _job_with_mcqs(self, hr_headers, **overrides):
        defaults = dict(auto_shortlist_mcq_min=50, auto_shortlist_ai_max=100,
                        auto_shortlist_max_violations=999, calendly_url=DEFAULT_CALENDLY)
        defaults.update(overrides)
        job = _create_job(hr_headers, **defaults)
        mcqs = [
            {"id": "q1", "question": "1+1?", "options": ["1", "2"], "correct_index": 1, "weight": 1},
            {"id": "q2", "question": "2+2?", "options": ["3", "4"], "correct_index": 1, "weight": 1},
        ]
        _set_assignment(hr_headers, job["id"], mcqs)
        return job

    def test_happy_path_auto_shortlist(self, hr_headers):
        job = self._job_with_mcqs(hr_headers)
        cand = _new_candidate()
        app_id, token, _ = _apply_and_invite(hr_headers, job["id"], cand)
        result = _submit(token, {"q1": 1, "q2": 1}, violations=[])
        assert result["auto_shortlisted"] is True, result
        assert result["auto_flagged"] is False
        app = _get_app(hr_headers, app_id)
        assert app["status"] == "interview_scheduled", app
        assert app.get("calendly_url") == DEFAULT_CALENDLY

    def test_mcq_below_min_no_shortlist(self, hr_headers):
        # mcq_min=80 default requires >=80%; with only 1 of 2 correct = 50%
        job = self._job_with_mcqs(hr_headers, auto_shortlist_mcq_min=80,
                                   auto_shortlist_ai_max=100, auto_shortlist_max_violations=999)
        cand = _new_candidate()
        app_id, token, _ = _apply_and_invite(hr_headers, job["id"], cand)
        result = _submit(token, {"q1": 1, "q2": 0}, violations=[])
        assert result["mcq_pct_weighted"] == 50
        assert result["auto_shortlisted"] is False
        app = _get_app(hr_headers, app_id)
        assert app["status"] == "assignment_submitted", app

    def test_violations_exceed_max(self, hr_headers):
        job = self._job_with_mcqs(hr_headers, auto_shortlist_max_violations=0)
        cand = _new_candidate()
        app_id, token, _ = _apply_and_invite(hr_headers, job["id"], cand)
        result = _submit(token, {"q1": 1, "q2": 1},
                          violations=[{"type": "tab_switch", "detail": "x"}])
        assert result["auto_shortlisted"] is False
        app = _get_app(hr_headers, app_id)
        assert app["status"] == "assignment_submitted"

    def test_auto_reject_wins_over_shortlist(self, hr_headers):
        # threshold=1 => any ai risk trips it; include a short answer to generate ai score
        job = self._job_with_mcqs(hr_headers, ai_reject_threshold=1,
                                   auto_shortlist_mcq_min=50, auto_shortlist_ai_max=100)
        # add a short-answer to the assignment so ai scorer runs
        mcqs = [
            {"id": "q1", "question": "1+1?", "options": ["1", "2"], "correct_index": 1, "weight": 1},
            {"id": "q2", "question": "2+2?", "options": ["3", "4"], "correct_index": 1, "weight": 1},
        ]
        sas = [{"id": "sa1", "question": "Explain X", "min_words": 5, "weight": 1}]
        _set_assignment(hr_headers, job["id"], mcqs, short_answers=sas)
        cand = _new_candidate()
        app_id, token, _ = _apply_and_invite(hr_headers, job["id"], cand)
        result = _submit(token, {"q1": 1, "q2": 1},
                          short_answers={"sa1": "Because it is important and matters a lot."},
                          violations=[])
        assert result["auto_flagged"] is True, result
        assert result["auto_shortlisted"] is False
        app = _get_app(hr_headers, app_id)
        assert app["status"] == "assignment_rejected_ai", app


# ---------------- JobIn round-trip ----------------
class TestJobInNewFields:
    def test_create_and_read_new_fields(self, hr_headers):
        job = _create_job(hr_headers, auto_shortlist_enabled=False,
                          auto_shortlist_mcq_min=65, auto_shortlist_ai_max=25,
                          auto_shortlist_max_violations=2)
        assert job["auto_shortlist_enabled"] is False
        assert job["auto_shortlist_mcq_min"] == 65
        assert job["auto_shortlist_ai_max"] == 25
        assert job["auto_shortlist_max_violations"] == 2
        # GET via HR endpoint
        r = requests.get(f"{API}/hr/jobs/{job['id']}", headers=hr_headers)
        assert r.status_code == 200
        d = r.json()
        assert d["auto_shortlist_enabled"] is False
        assert d["auto_shortlist_mcq_min"] == 65
        assert d["auto_shortlist_ai_max"] == 25
        assert d["auto_shortlist_max_violations"] == 2

    def test_defaults_applied_when_omitted(self, hr_headers):
        body = {
            "title": f"IT5 Defaults {uuid.uuid4().hex[:6]}",
            "department": "Tech & Eng",
            "location": "Remote",
            "type": "Full-Time",
            "description": "test",
            "requirements": [],
            "status": "open",
        }
        r = requests.post(f"{API}/hr/jobs", json=body, headers=hr_headers)
        assert r.status_code == 200, r.text
        job = r.json()
        assert job["auto_shortlist_enabled"] is True
        assert job["auto_shortlist_mcq_min"] == 80
        assert job["auto_shortlist_ai_max"] == 10
        assert job["auto_shortlist_max_violations"] == 0
        assert job["ai_reject_threshold"] == 70
