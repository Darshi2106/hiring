"""Iteration 3 backend tests: master admin, role guards, master user CRUD,
deactivation flow, assignment editor, resume upload/download, invite email mock."""
import io
import os
import uuid
import pytest
import requests

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"

HR_EMAIL = "hr@cohortdata.com"
HR_PASSWORD = "Cohort@2026"
MASTER_EMAIL = "darshan@cohortdata.com"
MASTER_PASSWORD = "MasterCohort@2026"


def _login(email, password):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password})
    return r


@pytest.fixture(scope="session")
def hr_token():
    r = _login(HR_EMAIL, HR_PASSWORD)
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="session")
def master_token():
    r = _login(MASTER_EMAIL, MASTER_PASSWORD)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["user"]["role"] == "master_admin"
    return data["token"]


@pytest.fixture(scope="session")
def candidate_token():
    email = f"test_cand_it3_{uuid.uuid4().hex[:6]}@example.com"
    r = requests.post(f"{API}/candidate/register",
                      json={"name": "It3 Cand", "email": email, "password": "abc123"})
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="session")
def a_job_id():
    r = requests.get(f"{API}/jobs")
    assert r.status_code == 200
    return r.json()[0]["id"]


def _h(tok):
    return {"Authorization": f"Bearer {tok}"}


# ---------------- Master admin seed ----------------
class TestMasterSeed:
    def test_master_login_ok(self):
        r = _login(MASTER_EMAIL, MASTER_PASSWORD)
        assert r.status_code == 200
        d = r.json()
        assert d["user"]["role"] == "master_admin"
        assert d["user"]["email"] == MASTER_EMAIL
        assert isinstance(d["token"], str) and d["token"]


# ---------------- Role guards ----------------
class TestRoleGuards:
    def test_master_users_forbidden_for_hr(self, hr_token):
        r = requests.get(f"{API}/master/users", headers=_h(hr_token))
        assert r.status_code == 403

    def test_master_users_ok_for_master(self, master_token):
        r = requests.get(f"{API}/master/users", headers=_h(master_token))
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_hr_jobs_ok_for_hr(self, hr_token):
        r = requests.get(f"{API}/hr/applications", headers=_h(hr_token))
        assert r.status_code == 200

    def test_hr_jobs_ok_for_master(self, master_token):
        r = requests.get(f"{API}/hr/applications", headers=_h(master_token))
        assert r.status_code == 200

    def test_hr_jobs_forbidden_for_candidate(self, candidate_token):
        r = requests.get(f"{API}/hr/applications", headers=_h(candidate_token))
        assert r.status_code == 403


# ---------------- Master user CRUD ----------------
class TestMasterUserCRUD:
    def test_list_users(self, master_token):
        r = requests.get(f"{API}/master/users", headers=_h(master_token))
        assert r.status_code == 200
        users = r.json()
        emails = [u["email"] for u in users]
        assert HR_EMAIL in emails
        assert MASTER_EMAIL in emails

    def test_create_hr_user(self, master_token):
        email = f"test_hr_{uuid.uuid4().hex[:6]}@cohortdata.com"
        r = requests.post(f"{API}/master/users", headers=_h(master_token),
                          json={"name": "New HR", "email": email, "password": "abcdef1"})
        assert r.status_code in (200, 201), r.text
        d = r.json()
        assert d["email"] == email
        assert d["role"] == "hr_admin"
        # login works
        lr = _login(email, "abcdef1")
        assert lr.status_code == 200
        assert lr.json()["user"]["role"] == "hr_admin"

    def test_create_duplicate_409(self, master_token):
        r = requests.post(f"{API}/master/users", headers=_h(master_token),
                          json={"name": "Dup", "email": HR_EMAIL, "password": "abcdef1"})
        assert r.status_code == 409

    def test_create_short_password_400(self, master_token):
        email = f"test_hr_{uuid.uuid4().hex[:6]}@cohortdata.com"
        r = requests.post(f"{API}/master/users", headers=_h(master_token),
                          json={"name": "Short", "email": email, "password": "abc"})
        assert r.status_code == 400

    def test_toggle_hr_user(self, master_token):
        email = f"test_hr_{uuid.uuid4().hex[:6]}@cohortdata.com"
        cr = requests.post(f"{API}/master/users", headers=_h(master_token),
                           json={"name": "Toggle", "email": email, "password": "abcdef1"})
        assert cr.status_code in (200, 201)
        uid = cr.json()["id"]
        # toggle off
        r = requests.post(f"{API}/master/users/{uid}/toggle", headers=_h(master_token))
        assert r.status_code == 200
        assert r.json()["is_active"] is False
        # toggle on
        r = requests.post(f"{API}/master/users/{uid}/toggle", headers=_h(master_token))
        assert r.status_code == 200
        assert r.json()["is_active"] is True

    def test_toggle_master_forbidden(self, master_token):
        users = requests.get(f"{API}/master/users", headers=_h(master_token)).json()
        master_id = next(u["id"] for u in users if u["email"] == MASTER_EMAIL)
        r = requests.post(f"{API}/master/users/{master_id}/toggle", headers=_h(master_token))
        assert r.status_code == 400


# ---------------- Deactivated HR flow ----------------
class TestDeactivatedHR:
    def test_deactivated_hr_blocked_on_hr_endpoints(self, master_token):
        email = f"test_hr_deact_{uuid.uuid4().hex[:6]}@cohortdata.com"
        password = "abcdef1"
        cr = requests.post(f"{API}/master/users", headers=_h(master_token),
                           json={"name": "Deact", "email": email, "password": password})
        assert cr.status_code in (200, 201)
        uid = cr.json()["id"]
        # login while active
        lr = _login(email, password)
        assert lr.status_code == 200
        tok = lr.json()["token"]
        # HR endpoints ok
        r = requests.get(f"{API}/hr/applications", headers=_h(tok))
        assert r.status_code == 200
        # deactivate
        r = requests.post(f"{API}/master/users/{uid}/toggle", headers=_h(master_token))
        assert r.json()["is_active"] is False
        # login STILL succeeds (per spec)
        lr2 = _login(email, password)
        assert lr2.status_code == 200
        tok2 = lr2.json()["token"]
        # but HR endpoint returns 403 with deactivated message
        r = requests.get(f"{API}/hr/applications", headers=_h(tok2))
        assert r.status_code == 403
        assert "deactivated" in r.text.lower()
        # cleanup: reactivate
        requests.post(f"{API}/master/users/{uid}/toggle", headers=_h(master_token))


# ---------------- Assignment editor ----------------
class TestAssignmentEditor:
    def test_get_assignment(self, hr_token, a_job_id):
        r = requests.get(f"{API}/hr/jobs/{a_job_id}/assignment", headers=_h(hr_token))
        assert r.status_code == 200
        a = r.json()
        assert "duration_minutes" in a
        assert "mcqs" in a
        assert "short_answers" in a
        # correct_index present on MCQs
        if a["mcqs"]:
            assert "correct_index" in a["mcqs"][0]

    def test_put_assignment_persists(self, hr_token, a_job_id):
        cur = requests.get(f"{API}/hr/jobs/{a_job_id}/assignment", headers=_h(hr_token)).json()
        cur["duration_minutes"] = 45
        # ensure at least 1 mcq
        if not cur["mcqs"]:
            cur["mcqs"] = [{"id": "m1", "question": "Q?", "options": ["A", "B"], "correct_index": 1, "weight": 1}]
        r = requests.put(f"{API}/hr/jobs/{a_job_id}/assignment", headers=_h(hr_token), json=cur)
        assert r.status_code == 200, r.text
        # verify persistence
        r2 = requests.get(f"{API}/hr/jobs/{a_job_id}/assignment", headers=_h(hr_token))
        assert r2.json()["duration_minutes"] == 45

    def test_put_invalid_correct_index_400(self, hr_token, a_job_id):
        cur = requests.get(f"{API}/hr/jobs/{a_job_id}/assignment", headers=_h(hr_token)).json()
        cur["mcqs"] = [{"id": "bad", "question": "Q?", "options": ["A", "B"], "correct_index": 5, "weight": 1}]
        r = requests.put(f"{API}/hr/jobs/{a_job_id}/assignment", headers=_h(hr_token), json=cur)
        assert r.status_code == 400

    def test_put_duration_too_low_400(self, hr_token, a_job_id):
        cur = requests.get(f"{API}/hr/jobs/{a_job_id}/assignment", headers=_h(hr_token)).json()
        cur["duration_minutes"] = 2
        r = requests.put(f"{API}/hr/jobs/{a_job_id}/assignment", headers=_h(hr_token), json=cur)
        assert r.status_code == 400

    def test_put_duration_too_high_400(self, hr_token, a_job_id):
        cur = requests.get(f"{API}/hr/jobs/{a_job_id}/assignment", headers=_h(hr_token)).json()
        cur["duration_minutes"] = 999
        r = requests.put(f"{API}/hr/jobs/{a_job_id}/assignment", headers=_h(hr_token), json=cur)
        assert r.status_code == 400


# ---------------- Resume upload & download ----------------
class TestResume:
    def _pdf_bytes(self, size=1024):
        # minimal PDF header + padding
        head = b"%PDF-1.4\n%TEST\n"
        return head + b"0" * (size - len(head))

    def test_upload_pdf_ok(self, hr_token):
        data = self._pdf_bytes(2048)
        files = {"file": ("resume.pdf", io.BytesIO(data), "application/pdf")}
        r = requests.post(f"{API}/resumes/upload", files=files)
        if r.status_code == 500:
            pytest.skip(f"Object storage unavailable: {r.text[:200]}")
        assert r.status_code == 200, r.text
        d = r.json()
        assert "file_id" in d and "storage_path" in d and "download_url" in d
        # download requires HR
        no_auth = requests.get(f"{BASE_URL}{d['download_url']}")
        assert no_auth.status_code in (401, 403)
        # HR auth
        auth = requests.get(f"{BASE_URL}{d['download_url']}", headers=_h(hr_token))
        assert auth.status_code == 200
        assert auth.headers.get("Content-Type", "").startswith("application/pdf") or auth.content

    def test_upload_bad_extension_400(self):
        files = {"file": ("resume.txt", io.BytesIO(b"hello"), "text/plain")}
        r = requests.post(f"{API}/resumes/upload", files=files)
        if r.status_code == 500:
            pytest.skip("Object storage unavailable")
        assert r.status_code == 400

    def test_upload_too_large_413(self):
        big = b"0" * (5 * 1024 * 1024 + 100)
        files = {"file": ("resume.pdf", io.BytesIO(big), "application/pdf")}
        r = requests.post(f"{API}/resumes/upload", files=files)
        assert r.status_code == 413


# ---------------- Invite email mock ----------------
class TestInviteEmail:
    def test_invite_returns_mocked_email(self, hr_token, candidate_token, a_job_id):
        # create an application for a fresh candidate
        email = f"test_inv_{uuid.uuid4().hex[:6]}@example.com"
        rr = requests.post(f"{API}/candidate/register",
                           json={"name": "Inv Cand", "email": email, "password": "abc123"})
        assert rr.status_code == 200
        tok = rr.json()["token"]
        ar = requests.post(f"{API}/applications",
                           json={"job_id": a_job_id, "name": "Inv", "email": email},
                           headers=_h(tok))
        assert ar.status_code == 200
        app_id = ar.json()["id"]
        # send invite
        r = requests.post(f"{API}/hr/invite", json={"application_id": app_id}, headers=_h(hr_token))
        assert r.status_code == 200, r.text
        d = r.json()
        assert "token" in d and d["token"]
        assert "email" in d
        em = d["email"]
        # RESEND_API_KEY is empty -> mocked
        assert em.get("mocked") is True
        assert em.get("delivered") is False
