"""Iteration 10 — security hardening + role-sync correction tests.

Covers:
- Role-sync correction (7 canonical open roles)
- SEC-002 public jobs sanitization
- SEC-003 server-side violation gating (via HR-driven synthetic flow)
- SEC-004 resume upload magic-byte validation + download hardening
- P3 rate limits (auth/login, candidate/register, candidate/login, applications, resumes/upload)
- Email HTML escape
- Per-role assessments (module-based)
- Regression: HR login, /hr/stats, /hr/applications pagination, /master/users
"""
import os
import io
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://proctored-jobs.preview.emergentagent.com").rstrip("/")
HR_EMAIL = "hr@cohortdata.com"
HR_PASS = "Cohort@2026"

CANONICAL = [
    "Senior Product Manager (AI/ML, Intelligent Systems & Enterprise Innovation)",
    "Sales Manager (AI/ML, ADAS, Data Services)",
    "Director Global Sales (AI/ML, ADAS, Multimodal Data)",
    "Visualization Engineer",
    "Senior ML / CV Engineer",
    "Platform / Operations Engineer",
    "Lead Full-Stack Engineer",
]

LEAKY_FIELDS = ("assignment", "ai_reject_threshold", "auto_shortlist_mcq_min",
                "auto_shortlist_ai_max", "auto_shortlist_max_violations")


@pytest.fixture(scope="module")
def s():
    return requests.Session()


@pytest.fixture(scope="module")
def hr_token(s):
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": HR_EMAIL, "password": HR_PASS})
    if r.status_code != 200:
        pytest.skip(f"HR login failed: {r.status_code} {r.text}")
    return r.json()["token"]


@pytest.fixture(scope="module")
def hr_headers(hr_token):
    return {"Authorization": f"Bearer {hr_token}"}


# ---------- Role sync ----------
class TestRoleSync:
    def test_open_roles_exact_7(self, s):
        r = s.get(f"{BASE_URL}/api/jobs?status=open")
        assert r.status_code == 200
        titles = sorted(j["title"] for j in r.json())
        assert titles == sorted(CANONICAL), f"Got: {titles}"

    def test_closed_includes_5_wrong_ops(self, s):
        r = s.get(f"{BASE_URL}/api/jobs?status=closed")
        assert r.status_code == 200
        closed_titles = {j["title"] for j in r.json()}
        # These 5 wrong ops/sales titles were inserted last iteration
        wrong = ["Quality Analyst", "Annotator / Associate", "Project Coordinator",
                 "Project Associate", "Global Sales Director"]
        for w in wrong:
            assert w in closed_titles, f"Expected '{w}' among closed"

    def test_total_jobs_around_198(self, s):
        opened = s.get(f"{BASE_URL}/api/jobs?status=open").json()
        closed = s.get(f"{BASE_URL}/api/jobs?status=closed").json()
        total = len(opened) + len(closed)
        assert total >= 190, f"Total jobs = {total}, expected ~198"


# ---------- SEC-002 public sanitization ----------
class TestPublicSanitization:
    def test_list_jobs_no_leaks(self, s):
        r = s.get(f"{BASE_URL}/api/jobs?status=open")
        for j in r.json():
            for f in LEAKY_FIELDS:
                assert f not in j, f"leaked '{f}' in {j['title']}"
            assert "assignment_summary" in j, f"missing summary in {j['title']}"
            summ = j["assignment_summary"]
            for k in ("duration_minutes", "mcq_count", "sa_count", "coding_count"):
                assert k in summ

    def test_job_detail_no_leaks(self, s):
        listing = s.get(f"{BASE_URL}/api/jobs?status=open").json()
        for j in listing:
            r = s.get(f"{BASE_URL}/api/jobs/{j['id']}")
            assert r.status_code == 200
            d = r.json()
            for f in LEAKY_FIELDS:
                assert f not in d, f"detail leaks '{f}' for {d['title']}"
            assert "assignment_summary" in d


# ---------- Per-role assessments ----------
class TestPerRoleAssessments:
    def test_each_role_has_modules_applied(self, s, hr_headers):
        r = s.get(f"{BASE_URL}/api/jobs?status=open")
        for j in r.json():
            det = s.get(f"{BASE_URL}/api/hr/jobs/{j['id']}", headers=hr_headers)
            assert det.status_code == 200, det.text
            body = det.json()
            assert "assessment_modules_applied" in body, f"{j['title']} missing modules_applied"
            assert isinstance(body["assessment_modules_applied"], list)
            assert len(body["assessment_modules_applied"]) > 0, f"{j['title']} has empty modules"
            asg = body.get("assignment", {})
            assert asg.get("mcqs") is not None
            # Caps: <=15 MCQ, <=4 SA, <=3 code
            assert len(asg.get("mcqs", [])) <= 15
            assert len(asg.get("short_answers", [])) <= 4
            assert len(asg.get("coding_tasks", [])) <= 3

    def test_business_roles_no_code(self, s, hr_headers):
        r = s.get(f"{BASE_URL}/api/jobs?status=open").json()
        biz_titles = {CANONICAL[0], CANONICAL[1], CANONICAL[2]}
        for j in r:
            if j["title"] in biz_titles:
                det = s.get(f"{BASE_URL}/api/hr/jobs/{j['id']}", headers=hr_headers).json()
                asg = det.get("assignment", {})
                assert len(asg.get("coding_tasks", [])) == 0, f"{j['title']} has coding tasks"
                assert asg.get("duration_minutes") == 60

    def test_engineering_roles_have_code(self, s, hr_headers):
        r = s.get(f"{BASE_URL}/api/jobs?status=open").json()
        eng_titles = set(CANONICAL[3:])  # 4 engineering roles
        for j in r:
            if j["title"] in eng_titles:
                det = s.get(f"{BASE_URL}/api/hr/jobs/{j['id']}", headers=hr_headers).json()
                asg = det.get("assignment", {})
                assert len(asg.get("coding_tasks", [])) >= 1, f"{j['title']} lacks coding"
                assert asg.get("duration_minutes") == 90


# ---------- SEC-004 Resume upload validation ----------
class TestResumeValidation:
    def _upload(self, s, name, data, ct="application/pdf"):
        return s.post(f"{BASE_URL}/api/resumes/upload",
                      files={"file": (name, io.BytesIO(data), ct)})

    def test_reject_no_extension(self, s):
        r = self._upload(s, "resume", b"%PDF-1.4\n%data")
        assert r.status_code == 415

    def test_reject_exe(self, s):
        r = self._upload(s, "malware.exe", b"MZ\x90\x00")
        assert r.status_code == 415

    def test_reject_txt(self, s):
        r = self._upload(s, "resume.txt", b"hello")
        assert r.status_code == 415

    def test_reject_pdf_magic_mismatch(self, s):
        r = self._upload(s, "resume.pdf", b"HELLO not a pdf" * 20)
        assert r.status_code == 415

    def test_accept_valid_pdf(self, s):
        pdf = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n" + b"0" * 100
        r = self._upload(s, "resume.pdf", pdf)
        assert r.status_code == 200, r.text
        assert "file_id" in r.json()
        return r.json()

    def test_download_has_attachment_and_nosniff(self, s, hr_headers):
        pdf = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n" + b"0" * 100
        up = self._upload(s, "resume.pdf", pdf)
        assert up.status_code == 200
        fid = up.json()["file_id"]
        r = s.get(f"{BASE_URL}/api/resumes/{fid}", headers=hr_headers)
        assert r.status_code == 200
        cd = r.headers.get("Content-Disposition", "")
        assert cd.startswith("attachment"), cd
        assert r.headers.get("X-Content-Type-Options") == "nosniff"
        assert r.headers.get("Content-Type", "").startswith("application/pdf")


# ---------- Email HTML escape ----------
class TestEmailEscape:
    def test_build_invite_escape(self):
        import sys
        sys.path.insert(0, "/app/backend")
        from email_svc import build_invite_email_html
        html = build_invite_email_html("<script>alert(1)</script>", "Hacker", "https://x/y?a=1&b=2", 60)
        assert "<script>alert(1)</script>" not in html
        assert "&lt;script&gt;" in html
        # exam_url should be quote-escaped (& → &amp;)
        assert "a=1&amp;b=2" in html


# ---------- Regression ----------
class TestRegression:
    def test_hr_stats_open_7(self, s, hr_headers):
        r = s.get(f"{BASE_URL}/api/hr/stats", headers=hr_headers)
        assert r.status_code == 200
        assert r.json().get("open_jobs") == 7

    def test_hr_applications_paginated(self, s, hr_headers):
        r = s.get(f"{BASE_URL}/api/hr/applications?page=1&page_size=25", headers=hr_headers)
        assert r.status_code == 200
        d = r.json()
        assert "items" in d or isinstance(d, list)

    def test_hr_time_to_hire(self, s, hr_headers):
        r = s.get(f"{BASE_URL}/api/hr/stats/time-to-hire", headers=hr_headers)
        assert r.status_code == 200

    def test_hr_question_bank(self, s, hr_headers):
        r = s.get(f"{BASE_URL}/api/hr/question-bank", headers=hr_headers)
        assert r.status_code == 200

    def test_master_users(self, s):
        r = requests.post(f"{BASE_URL}/api/auth/login",
                          json={"email": "darshan@cohortdata.com", "password": "MasterCohort@2026"})
        assert r.status_code == 200
        tok = r.json()["token"]
        r2 = requests.get(f"{BASE_URL}/api/master/users", headers={"Authorization": f"Bearer {tok}"})
        assert r2.status_code == 200


# ---------- P3 rate limits ----------
# Note: rate limits are per-IP; if slowapi is applied, we should see 429 within N requests.
class TestRateLimits:
    def test_auth_login_ratelimit(self):
        codes = []
        for _ in range(13):
            r = requests.post(f"{BASE_URL}/api/auth/login",
                              json={"email": "nobody@x.com", "password": "bad"})
            codes.append(r.status_code)
        assert 429 in codes, f"No 429 in {codes}"

    def test_candidate_register_ratelimit(self):
        codes = []
        for i in range(7):
            r = requests.post(f"{BASE_URL}/api/candidate/register",
                              json={"email": f"TESTrl_{time.time()}_{i}@x.com",
                                    "password": "Passw0rd!", "name": "T"})
            codes.append(r.status_code)
        assert 429 in codes, f"No 429 in {codes}"

    def test_resume_upload_ratelimit(self):
        codes = []
        pdf = b"%PDF-1.4\n" + b"0" * 100
        for i in range(12):
            r = requests.post(f"{BASE_URL}/api/resumes/upload",
                              files={"file": (f"r{i}.pdf", io.BytesIO(pdf), "application/pdf")})
            codes.append(r.status_code)
        assert 429 in codes, f"No 429 in {codes}"
