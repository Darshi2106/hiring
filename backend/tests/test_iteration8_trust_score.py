"""Trust Score feature tests (iteration 8).

Covers:
- POST /api/exam/submit returns trust_score (int 0-100) and trust_breakdown
- GET /api/hr/applications returns trust_score field, sorted DESC with nulls last
- Edge cases: perfect submission -> high trust; violations + zero MCQ -> low trust
- No 500/KeyError/ZeroDivisionError in any branch
"""
import os
import time
import uuid
import pytest
import requests

# Load frontend .env if not injected
if "REACT_APP_BACKEND_URL" not in os.environ:
    try:
        with open("/app/frontend/.env") as f:
            for line in f:
                if line.startswith("REACT_APP_BACKEND_URL="):
                    os.environ["REACT_APP_BACKEND_URL"] = line.split("=", 1)[1].strip()
                    break
    except Exception:
        pass
BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
HR_EMAIL = "hr@cohortdata.com"
HR_PASS = "Cohort@2026"

# Extra tolerance because AI risk (Claude) can be slow
TIMEOUT = 180


# --------- helpers ---------

@pytest.fixture(scope="module")
def hr_token():
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": HR_EMAIL, "password": HR_PASS}, timeout=30)
    assert r.status_code == 200, f"HR login failed: {r.status_code} {r.text}"
    return r.json()["token"]


@pytest.fixture(scope="module")
def hr_headers(hr_token):
    return {"Authorization": f"Bearer {hr_token}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def open_job(hr_headers):
    r = requests.get(f"{BASE_URL}/api/jobs?status=open", timeout=30)
    assert r.status_code == 200
    jobs = r.json()
    assert len(jobs) > 0, "No open jobs seeded"
    # Fetch full assignment via HR route
    for j in jobs:
        rj = requests.get(f"{BASE_URL}/api/hr/jobs/{j['id']}", headers=hr_headers, timeout=30)
        if rj.status_code != 200:
            continue
        full = rj.json()
        a = full.get("assignment") or {}
        if a.get("mcqs"):
            return full
    pytest.fail("No open job with MCQ assignment found")


def _create_candidate_and_apply(job):
    """Register a new candidate + apply. Returns application_id."""
    uid = uuid.uuid4().hex[:10]
    email = f"trust_{uid}@example.com"
    r = requests.post(f"{BASE_URL}/api/candidate/register", json={
        "email": email, "password": "Passw0rd!", "name": f"Trust {uid}"
    }, timeout=30)
    assert r.status_code == 200, f"register: {r.status_code} {r.text}"
    tok = r.json()["token"]
    r2 = requests.post(f"{BASE_URL}/api/applications",
                       headers={"Authorization": f"Bearer {tok}"},
                       json={
                           "job_id": job["id"],
                           "name": f"Trust {uid}",
                           "email": email,
                           "phone": "1234567890",
                           "resume_url": "",
                           "cover_letter": "test",
                           "source": "test",
                       }, timeout=30)
    assert r2.status_code == 200, f"apply: {r2.status_code} {r2.text}"
    return r2.json()["id"], email


def _create_invite(hr_headers, application_id):
    r = requests.post(f"{BASE_URL}/api/hr/invite",
                      headers=hr_headers,
                      json={"application_id": application_id}, timeout=30)
    assert r.status_code == 200, f"invite: {r.status_code} {r.text}"
    return r.json().get("token") or r.json().get("invite_token")


def _build_answers(job, all_correct=True):
    """Return (mcq_answers, short_answers, coding_answers) for the job assignment."""
    a = job.get("assignment", {})
    mcqs = a.get("mcqs", [])
    if all_correct:
        mcq_answers = {m["id"]: m["correct_index"] for m in mcqs}
    else:
        # deliberately wrong
        mcq_answers = {m["id"]: (m["correct_index"] + 1) % max(1, len(m.get("options", [1]))) for m in mcqs}
    # Short answers: keep empty to avoid slow AI calls; ai_risk defaults to 0
    short_answers = {sa["id"]: "" for sa in a.get("short_answers", [])}
    coding_tasks = a.get("coding_tasks") or ([a["coding"]] if a.get("coding") else [])
    # For high-trust path we don't need coding to pass; leaving blank means
    # results may be needs_manual_review or failed. To keep the test focused
    # on trust score presence + range, leave blank; branch weights adapt.
    coding_answers = {t["id"]: "" for t in coding_tasks}
    return mcq_answers, short_answers, coding_answers


# --------- Tests ---------

class TestTrustScoreSubmit:
    def test_high_trust_submission(self, hr_headers, open_job):
        """Full MCQ correct + no violations -> should yield a non-null int 0..100."""
        app_id, _ = _create_candidate_and_apply(open_job)
        token = _create_invite(hr_headers, app_id)
        mcq, sa, coding = _build_answers(open_job, all_correct=True)

        r = requests.post(f"{BASE_URL}/api/exam/submit", json={
            "invite_token": token,
            "mcq_answers": mcq,
            "short_answers": sa,
            "coding_answers": coding,
            "violations": [],
            "webcam_snapshots": [],
            "time_taken_seconds": 900,
        }, timeout=TIMEOUT)
        assert r.status_code == 200, f"submit: {r.status_code} {r.text}"
        data = r.json()
        assert "trust_score" in data
        ts = data["trust_score"]
        assert isinstance(ts, int), f"trust_score should be int, got {type(ts)}"
        assert 0 <= ts <= 100
        # Store for the ranking test
        pytest.high_app_id = app_id
        pytest.high_trust_score = ts

        assert "trust_breakdown" in data
        br = data["trust_breakdown"]
        for key in ("mcq", "coding", "ai_safety", "proctoring"):
            assert key in br, f"missing {key} in trust_breakdown"
        assert br["mcq"] == 100 or br["mcq"] >= 90  # all correct MCQs
        assert br["proctoring"] == 100
        # AI safety should be 100 for empty short answers
        assert br["ai_safety"] == 100
        # Expect high trust score
        assert ts >= 60, f"Expected high trust >=60, got {ts}"

    def test_low_trust_submission(self, hr_headers, open_job):
        """0 MCQ correct + many violations -> low trust, no 500."""
        app_id, _ = _create_candidate_and_apply(open_job)
        token = _create_invite(hr_headers, app_id)
        mcq, sa, coding = _build_answers(open_job, all_correct=False)
        violations = [
            {"type": "tab-switch", "detail": ""},
            {"type": "copy-paste", "detail": ""},
            {"type": "fullscreen-exit", "detail": ""},
            {"type": "webcam-lost", "detail": ""},
            {"type": "tab-switch", "detail": ""},
        ]
        r = requests.post(f"{BASE_URL}/api/exam/submit", json={
            "invite_token": token,
            "mcq_answers": mcq,
            "short_answers": sa,
            "coding_answers": coding,
            "violations": violations,
            "webcam_snapshots": [],
            "time_taken_seconds": 120,
        }, timeout=TIMEOUT)
        assert r.status_code == 200, f"submit: {r.status_code} {r.text}"
        data = r.json()
        ts = data["trust_score"]
        assert isinstance(ts, int)
        assert 0 <= ts <= 100
        assert data["trust_breakdown"]["proctoring"] == 0  # 5+ violations clamp to 0
        assert ts < pytest.high_trust_score, "Low submission should score less than high one"
        pytest.low_app_id = app_id
        pytest.low_trust_score = ts


class TestHRApplicationsTrust:
    def test_list_has_trust_and_sorted_desc(self, hr_headers, open_job):
        r = requests.get(f"{BASE_URL}/api/hr/applications?job_id={open_job['id']}",
                         headers=hr_headers, timeout=30)
        assert r.status_code == 200, r.text
        items = r.json()
        assert isinstance(items, list) and len(items) >= 2

        # Every item has trust_score key (may be None for legacy)
        for a in items:
            assert "trust_score" in a

        # Verify default sort: non-null items descending, nulls at end
        scores = [a.get("trust_score") for a in items]
        non_null_prefix_ended = False
        last_val = None
        for s in scores:
            if s is None:
                non_null_prefix_ended = True
            else:
                assert not non_null_prefix_ended, f"Null appeared before non-null in sort: {scores}"
                if last_val is not None:
                    assert s <= last_val, f"Not DESC sorted: {scores}"
                last_val = s

        # Our two apps should both appear with correct scores
        by_id = {a["id"]: a for a in items}
        assert pytest.high_app_id in by_id
        assert pytest.low_app_id in by_id
        assert by_id[pytest.high_app_id]["trust_score"] == pytest.high_trust_score
        assert by_id[pytest.low_app_id]["trust_score"] == pytest.low_trust_score

    def test_default_sort_is_trust(self, hr_headers):
        """Global (no job_id) call should also be sorted by trust DESC by default."""
        r = requests.get(f"{BASE_URL}/api/hr/applications", headers=hr_headers, timeout=30)
        assert r.status_code == 200
        items = r.json()
        assert isinstance(items, list)
        scores = [a.get("trust_score") for a in items]
        non_null = [s for s in scores if s is not None]
        assert non_null == sorted(non_null, reverse=True), f"Global list not DESC: {non_null[:10]}"
        # Nulls at end
        if None in scores:
            first_null = scores.index(None)
            assert all(s is None for s in scores[first_null:]), "Nulls not at the end"
