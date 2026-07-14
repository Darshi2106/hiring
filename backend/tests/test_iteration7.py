"""Iteration 7 backend tests:
- JS auto-grader (Node subprocess) for correct/broken/timeout submissions
- Python grader regression
- Application `source` field attribution
- Time-to-hire HR endpoint
- Master admin CRUD for custom question-bank modules
- Import from custom module into job assignment
"""
import os
import uuid
import pytest
import requests

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL")
            or "https://proctored-jobs.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

HR_EMAIL = "hr@cohortdata.com"
HR_PASSWORD = "Cohort@2026"
MASTER_EMAIL = "darshan@cohortdata.com"
MASTER_PASSWORD = "MasterCohort@2026"

JS_Q2_ID = "code_javascript_async::q2"       # promisePool
PY_Q1_ID = "code_python_beginner::q1"        # count_duplicates

PROMISE_POOL_CORRECT = """
async function promisePool(items, worker, concurrency = 5) {
  const results = new Array(items.length);
  let i = 0;
  async function run() {
    while (true) {
      const idx = i++;
      if (idx >= items.length) return;
      results[idx] = await worker(items[idx]);
    }
  }
  const runners = Array.from({length: Math.min(concurrency, items.length)}, () => run());
  await Promise.all(runners);
  return results;
}
"""

PROMISE_POOL_BROKEN = """
async function promisePool(items, worker, concurrency = 5) {
  // wrong: returns nothing meaningful
  return items.map(() => null);
}
"""

PROMISE_POOL_INFINITE = """
async function promisePool(items, worker, concurrency = 5) {
  while (true) { /* infinite loop */ }
}
"""

COUNT_DUPLICATES_CORRECT = """
def count_duplicates(arr):
    from collections import Counter
    c = Counter(arr)
    return sum(1 for v in c.values() if v > 1)
"""


# ---------------- Fixtures ----------------
@pytest.fixture(scope="module")
def hr_headers():
    r = requests.post(f"{API}/auth/login", json={"email": HR_EMAIL, "password": HR_PASSWORD})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


@pytest.fixture(scope="module")
def master_headers():
    r = requests.post(f"{API}/auth/login", json={"email": MASTER_EMAIL, "password": MASTER_PASSWORD})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


def _new_candidate():
    email = f"test_cand_it7_{uuid.uuid4().hex[:8]}@example.com"
    r = requests.post(f"{API}/candidate/register",
                      json={"name": "IT7 Cand", "email": email, "password": "secret123"})
    assert r.status_code == 200, r.text
    d = r.json()
    return {"email": email, "token": d["token"], "id": d["user"]["id"]}


def _create_job(hr_headers, **overrides):
    body = {
        "title": f"IT7 Job {uuid.uuid4().hex[:6]}",
        "department": "Tech & Eng",
        "location": "Remote",
        "type": "Full-Time",
        "description": "test",
        "requirements": ["python"],
        "status": "open",
        "auto_shortlist_enabled": False,
    }
    body.update(overrides)
    r = requests.post(f"{API}/hr/jobs", json=body, headers=hr_headers)
    assert r.status_code == 200, r.text
    return r.json()


def _put_assignment(hr_headers, job_id, payload):
    r = requests.put(f"{API}/hr/jobs/{job_id}/assignment", json=payload, headers=hr_headers)
    assert r.status_code == 200, r.text
    return r.json()


def _apply_and_invite(hr_headers, job_id, cand, source=None):
    body = {"job_id": job_id, "name": "IT7 Cand", "email": cand["email"], "phone": "555"}
    if source is not None:
        body["source"] = source
    r = requests.post(f"{API}/applications", json=body,
                      headers={"Authorization": f"Bearer {cand['token']}"})
    assert r.status_code == 200, r.text
    app_id = r.json()["id"]
    r = requests.post(f"{API}/hr/invite", json={"application_id": app_id}, headers=hr_headers)
    assert r.status_code == 200, r.text
    return app_id, r.json()["token"]


def _submit_code(token, task_id, code):
    r = requests.post(f"{API}/exam/submit", json={
        "invite_token": token,
        "mcq_answers": {},
        "short_answers": {},
        "coding_answers": {task_id: code},
        "coding_answer": "",
        "violations": [],
        "webcam_snapshots": [],
        "time_taken_seconds": 100,
    })
    assert r.status_code == 200, r.text
    return r.json()


def _get_sub(hr_headers, sub_id):
    r = requests.get(f"{API}/hr/submissions/{sub_id}", headers=hr_headers)
    assert r.status_code == 200, r.text
    return r.json()


def _setup_js_task_job(hr_headers):
    """Create job with one JS coding task = promisePool (with test_code)."""
    job = _create_job(hr_headers)
    task = {
        "id": JS_Q2_ID, "prompt": "promisePool",
        "starter_code": "async function promisePool(){}",
        "weight": 4, "language": "javascript",
        "test_code": ("const out = await promisePool([1,2,3,4,5],"
                      " async (n) => { await new Promise(r=>setTimeout(r,5)); return n*n; }, 2);\n"
                      "assert.deepStrictEqual(out, [1,4,9,16,25]);\n"
                      "const empty = await promisePool([], async (x)=>x, 3);\n"
                      "assert.deepStrictEqual(empty, []);\n"),
    }
    _put_assignment(hr_headers, job["id"], {
        "duration_minutes": 30, "mcqs": [], "short_answers": [], "coding_tasks": [task],
    })
    return job


# ---------------- JS auto-grader ----------------
class TestJSGrader:
    def test_correct_promise_pool_passes(self, hr_headers):
        job = _setup_js_task_job(hr_headers)
        cand = _new_candidate()
        _, token = _apply_and_invite(hr_headers, job["id"], cand)
        sub = _submit_code(token, JS_Q2_ID, PROMISE_POOL_CORRECT)
        sub_id = sub["submission_id"] if "submission_id" in sub else sub.get("id")
        # fetch via HR for details
        full = _get_sub(hr_headers, sub_id) if sub_id else sub
        cr = full["coding_results"][JS_Q2_ID]
        assert cr["language"] == "javascript"
        assert cr["passed"] is True, cr
        assert "duration_ms" in cr and isinstance(cr["duration_ms"], int)
        assert cr["duration_ms"] > 0

    def test_broken_promise_pool_fails(self, hr_headers):
        job = _setup_js_task_job(hr_headers)
        cand = _new_candidate()
        _, token = _apply_and_invite(hr_headers, job["id"], cand)
        sub = _submit_code(token, JS_Q2_ID, PROMISE_POOL_BROKEN)
        sub_id = sub.get("submission_id") or sub.get("id")
        full = _get_sub(hr_headers, sub_id) if sub_id else sub
        cr = full["coding_results"][JS_Q2_ID]
        assert cr["language"] == "javascript"
        assert cr["passed"] is False, cr

    def test_infinite_loop_timeout(self, hr_headers):
        job = _setup_js_task_job(hr_headers)
        cand = _new_candidate()
        _, token = _apply_and_invite(hr_headers, job["id"], cand)
        sub = _submit_code(token, JS_Q2_ID, PROMISE_POOL_INFINITE)
        sub_id = sub.get("submission_id") or sub.get("id")
        full = _get_sub(hr_headers, sub_id) if sub_id else sub
        cr = full["coding_results"][JS_Q2_ID]
        assert cr["passed"] is False, cr
        assert cr.get("error") == "timeout", cr


# ---------------- Python regression ----------------
class TestPythonGraderRegression:
    def test_count_duplicates_correct_passes(self, hr_headers):
        job = _create_job(hr_headers)
        task = {
            "id": PY_Q1_ID, "prompt": "count_duplicates",
            "starter_code": "def count_duplicates(arr):\n    pass",
            "weight": 3, "language": "python",
            "test_code": ("assert count_duplicates([1,2,2,3]) == 1\n"
                          "assert count_duplicates([1,1,2,2,3]) == 2\n"
                          "assert count_duplicates([1,2,3]) == 0\n"
                          "assert count_duplicates([]) == 0\n"
                          "assert count_duplicates([5,5,5,5]) == 1\n"),
        }
        _put_assignment(hr_headers, job["id"], {
            "duration_minutes": 30, "mcqs": [], "short_answers": [], "coding_tasks": [task],
        })
        cand = _new_candidate()
        _, token = _apply_and_invite(hr_headers, job["id"], cand)
        sub = _submit_code(token, PY_Q1_ID, COUNT_DUPLICATES_CORRECT)
        sub_id = sub.get("submission_id") or sub.get("id")
        full = _get_sub(hr_headers, sub_id) if sub_id else sub
        cr = full["coding_results"][PY_Q1_ID]
        assert cr["passed"] is True, cr
        assert cr["language"] == "python"


# ---------------- Application source ----------------
class TestApplicationSource:
    def test_source_stored(self, hr_headers):
        job = _create_job(hr_headers)
        cand = _new_candidate()
        r = requests.post(f"{API}/applications", json={
            "job_id": job["id"], "name": "IT7 Src", "email": cand["email"],
            "phone": "555", "source": "linkedin"
        }, headers={"Authorization": f"Bearer {cand['token']}"})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d.get("source") == "linkedin"

    def test_source_defaults_when_missing(self, hr_headers):
        job = _create_job(hr_headers)
        cand = _new_candidate()
        r = requests.post(f"{API}/applications", json={
            "job_id": job["id"], "name": "IT7 Src2", "email": cand["email"], "phone": "555"
        }, headers={"Authorization": f"Bearer {cand['token']}"})
        assert r.status_code == 200, r.text
        assert r.json().get("source") == "careers_direct"


# ---------------- Time-to-hire ----------------
class TestTimeToHire:
    def test_time_to_hire_shape(self, hr_headers):
        r = requests.get(f"{API}/hr/stats/time-to-hire", headers=hr_headers)
        assert r.status_code == 200, r.text
        d = r.json()
        for key in ("overall", "by_source", "by_role"):
            assert key in d, d
        overall = d["overall"]
        for k in ("applied_to_invited_hrs", "invited_to_submitted_hrs",
                  "applied_to_shortlist_hrs", "count"):
            assert k in overall
        assert isinstance(overall["count"], int)
        # by_source and by_role are dicts of {label: summary}
        assert isinstance(d["by_source"], dict)
        assert isinstance(d["by_role"], dict)
        for lbl, summary in d["by_source"].items():
            for k in ("applied_to_invited_hrs", "invited_to_submitted_hrs",
                      "applied_to_shortlist_hrs", "count"):
                assert k in summary, (lbl, summary)

    def test_time_to_hire_requires_auth(self):
        r = requests.get(f"{API}/hr/stats/time-to-hire")
        assert r.status_code in (401, 403), r.text


# ---------------- Master QB CRUD ----------------
@pytest.fixture
def custom_module_id():
    return f"mcq_custom_probe_{uuid.uuid4().hex[:6]}"


class TestMasterQBCRUD:
    def test_full_crud_and_visibility(self, master_headers, hr_headers, custom_module_id):
        mcq_item = {
            "id": "qc1", "type": "mcq", "weight": 1,
            "question": "2+2=?", "options": ["3", "4", "5", "22"],
            "correct_index": 1,
        }
        body = {
            "id": custom_module_id,
            "title": "Custom Probe",
            "category": "Tech & Eng",
            "description": "iter7 probe",
            "questions": [mcq_item],
        }
        # CREATE
        r = requests.post(f"{API}/master/question-bank/modules", json=body, headers=master_headers)
        assert r.status_code == 200, r.text
        assert r.json().get("ok") is True

        # Duplicate id -> 409
        r2 = requests.post(f"{API}/master/question-bank/modules", json=body, headers=master_headers)
        assert r2.status_code == 409, r2.text

        # Seeded id collision -> 409
        seeded_body = {**body, "id": "mcq_frontend"}
        r3 = requests.post(f"{API}/master/question-bank/modules", json=seeded_body, headers=master_headers)
        assert r3.status_code == 409, r3.text

        # Non-master token -> 403
        r4 = requests.post(f"{API}/master/question-bank/modules",
                           json={**body, "id": f"{custom_module_id}_x"},
                           headers=hr_headers)
        assert r4.status_code == 403, r4.text

        # GET list (via HR)
        r5 = requests.get(f"{API}/hr/question-bank", headers=hr_headers)
        assert r5.status_code == 200, r5.text
        listing = r5.json()
        found = [m for m in listing if m["id"] == custom_module_id]
        assert found, "custom module not listed"
        assert found[0].get("is_custom") is True

        # GET detail
        r6 = requests.get(f"{API}/hr/question-bank/{custom_module_id}", headers=hr_headers)
        assert r6.status_code == 200, r6.text
        detail = r6.json()
        assert detail["is_custom"] is True
        assert len(detail["questions"]) == 1
        assert detail["questions"][0]["id"] == "qc1"

        # PUT edit
        edited = {**body, "title": "Custom Probe v2",
                  "questions": [mcq_item, {**mcq_item, "id": "qc2", "question": "3+3=?", "correct_index": 1, "options": ["5", "6", "7", "8"]}]}
        # correct answer for qc2 is index 1 -> "6"
        edited["questions"][1]["correct_index"] = 1
        r7 = requests.put(f"{API}/master/question-bank/modules/{custom_module_id}",
                          json=edited, headers=master_headers)
        assert r7.status_code == 200, r7.text
        r8 = requests.get(f"{API}/hr/question-bank/{custom_module_id}", headers=hr_headers)
        assert r8.status_code == 200
        assert r8.json()["title"] == "Custom Probe v2"
        assert len(r8.json()["questions"]) == 2

        # DELETE
        r9 = requests.delete(f"{API}/master/question-bank/modules/{custom_module_id}",
                             headers=master_headers)
        assert r9.status_code == 200, r9.text
        # No longer in list
        r10 = requests.get(f"{API}/hr/question-bank", headers=hr_headers)
        assert r10.status_code == 200
        assert not [m for m in r10.json() if m["id"] == custom_module_id]
        # GET detail should 404
        r11 = requests.get(f"{API}/hr/question-bank/{custom_module_id}", headers=hr_headers)
        assert r11.status_code == 404


# ---------------- Import from custom module ----------------
class TestImportFromCustom:
    def test_import_custom_mcq_appends(self, master_headers, hr_headers):
        module_id = f"mcq_custom_import_{uuid.uuid4().hex[:6]}"
        qid = "qi1"
        mcq_item = {
            "id": qid, "type": "mcq", "weight": 2,
            "question": "Capital of France?",
            "options": ["Berlin", "Paris", "Madrid", "Rome"],
            "correct_index": 1,
        }
        r = requests.post(f"{API}/master/question-bank/modules", json={
            "id": module_id, "title": "Custom Import", "category": "General",
            "description": "iter7 import", "questions": [mcq_item],
        }, headers=master_headers)
        assert r.status_code == 200, r.text

        job = _create_job(hr_headers)
        # Import custom question id
        r2 = requests.post(f"{API}/hr/jobs/{job['id']}/assignment/import",
                           json={"question_ids": [qid]}, headers=hr_headers)
        assert r2.status_code == 200, r2.text
        # Confirm assignment now has this mcq
        r3 = requests.get(f"{API}/hr/jobs/{job['id']}/assignment", headers=hr_headers)
        assert r3.status_code == 200
        a = r3.json()
        mcq_ids = [m["id"] for m in a.get("mcqs", [])]
        assert qid in mcq_ids, f"Custom mcq not appended. Got: {mcq_ids}"

        # Cleanup
        requests.delete(f"{API}/master/question-bank/modules/{module_id}", headers=master_headers)
