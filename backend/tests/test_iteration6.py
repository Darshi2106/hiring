"""Iteration 6 backend tests: coding_tasks array, auto-grader, task migration, import multi-code."""
import os
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://proctored-jobs.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

HR_EMAIL = "hr@cohortdata.com"
HR_PASSWORD = "Cohort@2026"

PY_Q1_ID = "code_python_beginner::q1"  # count_duplicates - Python auto-gradable
PY_Q2_ID = "code_python_beginner::q2"  # is_palindrome
PY_Q3_ID = "code_python_beginner::q3"  # word_frequency
JS_Q1_ID = "code_javascript_async::q1"  # JS - manual review
SQL_Q1_ID = "code_sql::q1"  # SQL - manual review
PY_ADV_Q1_ID = "code_python_advanced::q1"  # Python but no test_code - manual review


# ---------------- Fixtures ----------------
@pytest.fixture(scope="module")
def hr_headers():
    r = requests.post(f"{API}/auth/login", json={"email": HR_EMAIL, "password": HR_PASSWORD})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


def _new_candidate():
    email = f"test_cand_it6_{uuid.uuid4().hex[:8]}@example.com"
    r = requests.post(f"{API}/candidate/register", json={"name": "IT6 Cand", "email": email, "password": "secret123"})
    assert r.status_code == 200, r.text
    d = r.json()
    return {"email": email, "token": d["token"], "id": d["user"]["id"]}


def _create_job(hr_headers, **overrides):
    body = {
        "title": f"IT6 Job {uuid.uuid4().hex[:6]}",
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
    return r


def _apply_and_invite(hr_headers, job_id, cand):
    r = requests.post(f"{API}/applications", json={
        "job_id": job_id, "name": "IT6 Cand", "email": cand["email"], "phone": "555",
    }, headers={"Authorization": f"Bearer {cand['token']}"})
    assert r.status_code == 200, r.text
    app_id = r.json()["id"]
    r = requests.post(f"{API}/hr/invite", json={"application_id": app_id}, headers=hr_headers)
    assert r.status_code == 200, r.text
    return app_id, r.json()["token"]


def _submit(token, coding_answers=None, coding_answer="", mcq_answers=None):
    r = requests.post(f"{API}/exam/submit", json={
        "invite_token": token,
        "mcq_answers": mcq_answers or {},
        "short_answers": {},
        "coding_answers": coding_answers or {},
        "coding_answer": coding_answer,
        "violations": [],
        "webcam_snapshots": [],
        "time_taken_seconds": 100,
    })
    assert r.status_code == 200, r.text
    return r.json()


def _get_submission(hr_headers, sub_id):
    r = requests.get(f"{API}/hr/submissions/{sub_id}", headers=hr_headers)
    assert r.status_code == 200, r.text
    return r.json()


# ---------------- Startup migration ----------------
class TestMigration:
    def test_no_seeded_job_has_legacy_coding_key(self, hr_headers):
        """After startup migration, no job.assignment should have `coding` key; every one must have coding_tasks list."""
        r = requests.get(f"{API}/jobs")
        assert r.status_code == 200
        jobs = r.json()
        assert len(jobs) > 0
        for j in jobs:
            rr = requests.get(f"{API}/hr/jobs/{j['id']}", headers=hr_headers)
            assert rr.status_code == 200, rr.text
            full = rr.json()
            a = full.get("assignment") or {}
            assert "coding" not in a, f"Job {j['title']} still has legacy 'coding' key: {a.get('coding')}"
            # coding_tasks must be a list (or absent for empty assignments)
            ct = a.get("coding_tasks")
            assert ct is None or isinstance(ct, list), f"Job {j['title']} coding_tasks wrong type: {type(ct)}"

    def test_default_assignment_has_coding_tasks_list(self, hr_headers):
        job = _create_job(hr_headers)
        r = requests.get(f"{API}/hr/jobs/{job['id']}/assignment", headers=hr_headers)
        assert r.status_code == 200
        a = r.json()
        assert isinstance(a.get("coding_tasks"), list)
        assert "coding" not in a


# ---------------- AssignmentIn shape ----------------
class TestAssignmentEditor:
    def test_accepts_coding_tasks_array(self, hr_headers):
        job = _create_job(hr_headers)
        payload = {
            "duration_minutes": 30,
            "mcqs": [],
            "short_answers": [],
            "coding_tasks": [
                {"id": "task_a", "prompt": "P1", "starter_code": "def a():pass",
                 "weight": 2, "language": "python", "test_code": "assert 1==1"},
                {"id": "task_b", "prompt": "P2", "starter_code": "def b():pass",
                 "weight": 3, "language": "javascript", "test_code": ""},
            ],
        }
        r = _put_assignment(hr_headers, job["id"], payload)
        assert r.status_code == 200, r.text
        # Read back
        r = requests.get(f"{API}/hr/jobs/{job['id']}/assignment", headers=hr_headers)
        assert r.status_code == 200
        a = r.json()
        assert len(a["coding_tasks"]) == 2
        ids = {t["id"] for t in a["coding_tasks"]}
        assert ids == {"task_a", "task_b"}
        task_a = next(t for t in a["coding_tasks"] if t["id"] == "task_a")
        assert task_a["language"] == "python"
        assert task_a["test_code"] == "assert 1==1"
        assert task_a["weight"] == 2

    def test_old_shape_coding_single_object_ignored(self, hr_headers):
        """Legacy body with `coding: {..}` should NOT populate coding_tasks (Pydantic ignores unknowns)."""
        job = _create_job(hr_headers)
        payload = {
            "duration_minutes": 30,
            "mcqs": [],
            "short_answers": [],
            "coding": {"id": "old", "prompt": "legacy", "starter_code": "", "weight": 1},
        }
        r = _put_assignment(hr_headers, job["id"], payload)
        # Either 200 with `coding` ignored (unknown-field policy), or 422
        assert r.status_code in (200, 422), r.text
        if r.status_code == 200:
            rr = requests.get(f"{API}/hr/jobs/{job['id']}/assignment", headers=hr_headers)
            a = rr.json()
            # coding_tasks stays empty (unknown "coding" field silently ignored)
            assert a.get("coding_tasks") == []
            assert "coding" not in a


# ---------------- Exam GET (candidate) ----------------
class TestExamGetStripsTestCode:
    def test_test_code_stripped_from_candidate_view(self, hr_headers):
        job = _create_job(hr_headers)
        payload = {
            "duration_minutes": 30,
            "mcqs": [],
            "short_answers": [],
            "coding_tasks": [
                {"id": "t1", "prompt": "Add two numbers", "starter_code": "def add(a,b):pass",
                 "weight": 1, "language": "python",
                 "test_code": "assert add(1,2)==3\nassert add(0,0)==0"},
            ],
        }
        _put_assignment(hr_headers, job["id"], payload)
        cand = _new_candidate()
        _, token = _apply_and_invite(hr_headers, job["id"], cand)
        # candidate fetches exam
        r = requests.get(f"{API}/exam/{token}")
        assert r.status_code == 200
        exam = r.json()
        assert "coding_tasks" in exam
        assert "coding" not in exam
        assert len(exam["coding_tasks"]) == 1
        t = exam["coding_tasks"][0]
        assert "test_code" not in t, f"test_code leaked to candidate: {t}"
        # But other fields should be present
        assert t["id"] == "t1"
        assert t["prompt"] == "Add two numbers"
        assert t["starter_code"] == "def add(a,b):pass"
        assert t.get("language") == "python"


# ---------------- Auto-grader correctness ----------------
class TestAutoGrader:
    @pytest.fixture(scope="class")
    def python_job(self):
        # Set up job with count_duplicates task
        r = requests.post(f"{API}/auth/login", json={"email": HR_EMAIL, "password": HR_PASSWORD})
        headers = {"Authorization": f"Bearer {r.json()['token']}"}
        job = _create_job(headers)
        payload = {
            "duration_minutes": 30, "mcqs": [], "short_answers": [],
            "coding_tasks": [{
                "id": "count_dup", "prompt": "count_duplicates",
                "starter_code": "", "weight": 1, "language": "python",
                "test_code": (
                    "assert count_duplicates([1,2,2,3]) == 1\n"
                    "assert count_duplicates([1,1,2,2,3]) == 2\n"
                    "assert count_duplicates([1,2,3]) == 0\n"
                    "assert count_duplicates([]) == 0\n"
                ),
            }],
        }
        _put_assignment(headers, job["id"], payload)
        return {"job": job, "headers": headers}

    def _new_invite(self, python_job):
        cand = _new_candidate()
        app_id, token = _apply_and_invite(python_job["headers"], python_job["job"]["id"], cand)
        return app_id, token

    def test_correct_solution_passes(self, python_job):
        _, token = self._new_invite(python_job)
        correct = (
            "def count_duplicates(arr):\n"
            "    from collections import Counter\n"
            "    return sum(1 for _,c in Counter(arr).items() if c>1)\n"
        )
        r = _submit(token, coding_answers={"count_dup": correct})
        sub = _get_submission(python_job["headers"], r["submission_id"])
        cr = sub["coding_results"]["count_dup"]
        assert cr["needs_manual_review"] is False
        assert cr["passed"] is True, f"Expected pass, got: {cr}"
        assert cr["language"] == "python"
        assert "duration_ms" in cr
        assert cr["duration_ms"] >= 0

    def test_broken_solution_fails(self, python_job):
        _, token = self._new_invite(python_job)
        broken = "def count_duplicates(arr):\n    return 42\n"
        r = _submit(token, coding_answers={"count_dup": broken})
        sub = _get_submission(python_job["headers"], r["submission_id"])
        cr = sub["coding_results"]["count_dup"]
        assert cr["needs_manual_review"] is False
        assert cr["passed"] is False
        # stderr should contain assertion traceback
        assert cr.get("stderr", ""), "Expected stderr with error"

    def test_infinite_loop_times_out(self, python_job):
        _, token = self._new_invite(python_job)
        infinite = "def count_duplicates(arr):\n    while True:\n        pass\n"
        r = _submit(token, coding_answers={"count_dup": infinite})
        sub = _get_submission(python_job["headers"], r["submission_id"])
        cr = sub["coding_results"]["count_dup"]
        assert cr["passed"] is False
        assert cr.get("error") == "timeout", f"Expected error=timeout, got {cr}"


# ---------------- Manual-review routing ----------------
class TestManualReviewRouting:
    def test_js_task_needs_manual_review(self, hr_headers):
        job = _create_job(hr_headers)
        payload = {
            "duration_minutes": 30, "mcqs": [], "short_answers": [],
            "coding_tasks": [{
                "id": "js_task", "prompt": "JS", "starter_code": "",
                "weight": 1, "language": "javascript", "test_code": ""}],
        }
        _put_assignment(hr_headers, job["id"], payload)
        cand = _new_candidate()
        _, token = _apply_and_invite(hr_headers, job["id"], cand)
        r = _submit(token, coding_answers={"js_task": "console.log('x')"})
        sub = _get_submission(hr_headers, r["submission_id"])
        cr = sub["coding_results"]["js_task"]
        assert cr["needs_manual_review"] is True
        assert cr["passed"] is None
        assert cr["language"] == "javascript"

    def test_python_without_testcode_needs_manual_review(self, hr_headers):
        job = _create_job(hr_headers)
        payload = {
            "duration_minutes": 30, "mcqs": [], "short_answers": [],
            "coding_tasks": [{
                "id": "py_no_tests", "prompt": "P", "starter_code": "",
                "weight": 1, "language": "python", "test_code": ""}],
        }
        _put_assignment(hr_headers, job["id"], payload)
        cand = _new_candidate()
        _, token = _apply_and_invite(hr_headers, job["id"], cand)
        r = _submit(token, coding_answers={"py_no_tests": "print('hi')"})
        sub = _get_submission(hr_headers, r["submission_id"])
        cr = sub["coding_results"]["py_no_tests"]
        assert cr["needs_manual_review"] is True
        assert cr["passed"] is None


# ---------------- Import from library ----------------
class TestImportLibrary:
    def test_import_multiple_coding_tasks_all_appended(self, hr_headers):
        job = _create_job(hr_headers)
        # Import 3 coding tasks
        r = requests.post(f"{API}/hr/jobs/{job['id']}/assignment/import",
                          json={"question_ids": [PY_Q1_ID, PY_Q2_ID, PY_Q3_ID]},
                          headers=hr_headers)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["added_code"] == 3, f"Expected 3 coding tasks added, got {data}"
        # Read back
        r = requests.get(f"{API}/hr/jobs/{job['id']}/assignment", headers=hr_headers)
        a = r.json()
        ids = {t["id"] for t in a["coding_tasks"]}
        assert PY_Q1_ID in ids and PY_Q2_ID in ids and PY_Q3_ID in ids
        # Each imported task has test_code populated
        imported = [t for t in a["coding_tasks"] if t["id"] in {PY_Q1_ID, PY_Q2_ID, PY_Q3_ID}]
        for t in imported:
            assert t.get("test_code"), f"Task {t['id']} missing test_code after import"
            assert t.get("language") == "python"

    def test_duplicate_import_skips(self, hr_headers):
        job = _create_job(hr_headers)
        r = requests.post(f"{API}/hr/jobs/{job['id']}/assignment/import",
                          json={"question_ids": [PY_Q1_ID]}, headers=hr_headers)
        assert r.status_code == 200
        assert r.json()["added_code"] == 1
        # second time - dup
        r = requests.post(f"{API}/hr/jobs/{job['id']}/assignment/import",
                          json={"question_ids": [PY_Q1_ID]}, headers=hr_headers)
        assert r.status_code == 200
        assert r.json()["added_code"] == 0


# ---------------- Backwards-compat single coding_answer ----------------
class TestLegacySubmit:
    def test_legacy_coding_answer_populates_dict_and_grades(self, hr_headers):
        job = _create_job(hr_headers)
        payload = {
            "duration_minutes": 30, "mcqs": [], "short_answers": [],
            "coding_tasks": [{
                "id": "legacy_task", "prompt": "count_duplicates",
                "starter_code": "", "weight": 1, "language": "python",
                "test_code": "assert count_duplicates([1,2,2,3])==1\nassert count_duplicates([])==0\n",
            }],
        }
        _put_assignment(hr_headers, job["id"], payload)
        cand = _new_candidate()
        _, token = _apply_and_invite(hr_headers, job["id"], cand)
        legacy_code = (
            "def count_duplicates(a):\n"
            "    from collections import Counter\n"
            "    return sum(1 for _,c in Counter(a).items() if c>1)\n"
        )
        r = _submit(token, coding_answers={}, coding_answer=legacy_code)
        sub = _get_submission(hr_headers, r["submission_id"])
        assert sub["coding_answer"] == legacy_code
        # dict is populated with legacy code under first task id
        assert sub["coding_answers"].get("legacy_task") == legacy_code
        cr = sub["coding_results"]["legacy_task"]
        assert cr["passed"] is True, cr
