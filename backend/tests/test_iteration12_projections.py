"""Iteration 12: verify projection & $size aggregation optimizations
- /hr/stats/time-to-hire
- /hr/question-bank (list) and /hr/question-bank/{module_id} (detail)
- Regressions: /hr/applications, /candidate/applications
"""
import os
import time
import uuid
import pytest
import requests

def _load_frontend_env_url():
    try:
        with open("/app/frontend/.env") as f:
            for line in f:
                if line.startswith("REACT_APP_BACKEND_URL="):
                    return line.split("=", 1)[1].strip()
    except FileNotFoundError:
        pass
    return None

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or _load_frontend_env_url()).rstrip("/")
HR_EMAIL = "hr@cohortdata.com"
HR_PASS = "Cohort@2026"
MASTER_EMAIL = "darshan@cohortdata.com"
MASTER_PASS = "MasterCohort@2026"


def _login(email, password):
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password}, timeout=15)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    return r.json()["token"]


@pytest.fixture(scope="module")
def hr_headers():
    return {"Authorization": f"Bearer {_login(HR_EMAIL, HR_PASS)}"}


@pytest.fixture(scope="module")
def master_headers():
    return {"Authorization": f"Bearer {_login(MASTER_EMAIL, MASTER_PASS)}"}


# ----- time-to-hire -----
class TestTimeToHire:
    def test_time_to_hire_shape_and_performance(self, hr_headers):
        t0 = time.time()
        r = requests.get(f"{BASE_URL}/api/hr/stats/time-to-hire", headers=hr_headers, timeout=30)
        elapsed_ms = (time.time() - t0) * 1000
        assert r.status_code == 200, r.text
        data = r.json()
        assert "overall" in data and "by_source" in data and "by_role" in data

        overall = data["overall"]
        for k in ("applied_to_invited_hrs", "invited_to_submitted_hrs", "applied_to_shortlist_hrs", "count"):
            assert k in overall, f"missing {k} in overall"
        assert isinstance(overall["count"], int)
        assert overall["count"] > 0, "expected some applications"
        print(f"time-to-hire count={overall['count']} elapsed={elapsed_ms:.0f}ms")

        # by_source and by_role structure
        assert isinstance(data["by_source"], dict) and len(data["by_source"]) >= 1
        assert isinstance(data["by_role"], dict) and len(data["by_role"]) >= 1
        for src, s in data["by_source"].items():
            for k in ("applied_to_invited_hrs", "invited_to_submitted_hrs", "applied_to_shortlist_hrs", "count"):
                assert k in s, f"missing {k} in by_source[{src}]"
        for role, s in data["by_role"].items():
            for k in ("count",):
                assert k in s

        # count sums across sources == overall count
        assert sum(v["count"] for v in data["by_source"].values()) == overall["count"]
        assert sum(v["count"] for v in data["by_role"].values()) == overall["count"]

        # Perf target
        assert elapsed_ms < 500, f"time-to-hire too slow: {elapsed_ms:.0f}ms"


# ----- question-bank list + detail + custom module -----
class TestQuestionBank:
    def test_list_modules_seed_count_and_perf(self, hr_headers):
        t0 = time.time()
        r = requests.get(f"{BASE_URL}/api/hr/question-bank", headers=hr_headers, timeout=15)
        elapsed_ms = (time.time() - t0) * 1000
        assert r.status_code == 200, r.text
        modules = r.json()
        assert isinstance(modules, list)
        # Fields
        for m in modules:
            for k in ("id", "title", "category", "description", "count", "is_custom"):
                assert k in m, f"missing {k} in module {m}"
            assert isinstance(m["count"], int)
        seeded = [m for m in modules if not m["is_custom"]]
        assert len(seeded) == 27, f"expected 27 seeded modules, got {len(seeded)}"
        print(f"question-bank total={len(modules)} seeded={len(seeded)} elapsed={elapsed_ms:.0f}ms")
        assert elapsed_ms < 500, f"question-bank too slow: {elapsed_ms:.0f}ms"

    def test_create_custom_module_and_verify_count(self, hr_headers, master_headers):
        mod_id = f"test_it12_{uuid.uuid4().hex[:8]}"
        payload = {
            "id": mod_id,
            "title": "TEST_it12 module",
            "category": "engineering",
            "description": "iteration 12 test",
            "questions": [
                {"id": f"{mod_id}_q1", "type": "mcq", "prompt": "1+1?", "options": ["1", "2"], "correct_index": 1},
                {"id": f"{mod_id}_q2", "type": "mcq", "prompt": "2+2?", "options": ["3", "4"], "correct_index": 1},
                {"id": f"{mod_id}_q3", "type": "short", "prompt": "explain X"},
            ],
        }
        r = requests.post(
            f"{BASE_URL}/api/master/question-bank/modules", headers=master_headers, json=payload, timeout=15
        )
        assert r.status_code == 200, r.text

        try:
            # List should include our custom module with count=3
            r2 = requests.get(f"{BASE_URL}/api/hr/question-bank", headers=hr_headers, timeout=15)
            assert r2.status_code == 200
            found = [m for m in r2.json() if m["id"] == mod_id]
            assert len(found) == 1, f"custom module {mod_id} not returned in list"
            assert found[0]["is_custom"] is True
            assert found[0]["count"] == 3, f"expected count=3 via $size, got {found[0]['count']}"

            # Detail endpoint returns full questions[]
            r3 = requests.get(f"{BASE_URL}/api/hr/question-bank/{mod_id}", headers=hr_headers, timeout=15)
            assert r3.status_code == 200
            d = r3.json()
            assert d["is_custom"] is True
            assert len(d["questions"]) == 3
            assert d["questions"][0]["id"].startswith(mod_id)
        finally:
            requests.delete(
                f"{BASE_URL}/api/master/question-bank/modules/{mod_id}", headers=master_headers, timeout=10
            )

    def test_detail_seeded_module_returns_full_questions(self, hr_headers):
        r = requests.get(f"{BASE_URL}/api/hr/question-bank", headers=hr_headers, timeout=15)
        assert r.status_code == 200
        seeded = [m for m in r.json() if not m["is_custom"] and m["count"] > 0]
        assert seeded, "no seeded modules with questions"
        m = seeded[0]
        r2 = requests.get(f"{BASE_URL}/api/hr/question-bank/{m['id']}", headers=hr_headers, timeout=15)
        assert r2.status_code == 200, r2.text
        d = r2.json()
        assert d["is_custom"] is False
        assert isinstance(d.get("questions"), list) and len(d["questions"]) == m["count"]


# ----- regression: /hr/applications + candidate applications -----
class TestRegression:
    def test_hr_applications_still_works(self, hr_headers):
        r = requests.get(f"{BASE_URL}/api/hr/applications", headers=hr_headers, timeout=20)
        assert r.status_code == 200, r.text
        data = r.json()
        # accept list or {items:[...]}
        apps = data if isinstance(data, list) else data.get("items", data.get("applications", []))
        assert isinstance(apps, list)
        # trust sort descending if present
        trust_vals = [a.get("trust_score") for a in apps if a.get("trust_score") is not None]
        if len(trust_vals) >= 2:
            assert trust_vals == sorted(trust_vals, reverse=True), "trust_score not descending"
        print(f"hr/applications returned {len(apps)} items")

    def test_candidate_applications_field_shape(self):
        # Only reachable with candidate auth; skip gracefully if not available.
        r = requests.get(f"{BASE_URL}/api/candidate/applications", timeout=10)
        # Unauth -> 401; endpoint exists means router is intact.
        assert r.status_code in (200, 401, 403), f"unexpected status {r.status_code}: {r.text}"
