"""Sandboxed code grader — runs candidate code + test harness in an isolated subprocess.

Isolation strategy (SEC-001 mitigation):
- Executes as the unprivileged `nobody` user via `sudo -n -u nobody` so the process
  cannot read backend `.env` (chmod 600 on startup, owner=root)
- Runs in a fresh /tmp/grader/<uuid>/ workspace with world-execute + owner-only-write,
  candidate code as a temp file readable by nobody
- Blank environment (only PATH), no cwd inheritance from the FastAPI process
- Resource limits: 256MB memory (RLIMIT_AS), 10s wall clock
- No shell=True; direct argv exec

Supports:
- python (auto-graded via assertion harness)
- javascript (auto-graded via Node subprocess)
- Any other language / missing test_code → manual review
"""
import subprocess
import resource
import tempfile
import os
import stat
import time
import uuid
import logging
import shutil

logger = logging.getLogger("grader")

MEM_LIMIT_BYTES = 256 * 1024 * 1024
DEFAULT_TIMEOUT_S = 10
GRADER_ROOT = "/tmp/grader"
SANDBOX_USER = "nobody"


def _preexec_limit_memory():
    try:
        resource.setrlimit(resource.RLIMIT_AS, (MEM_LIMIT_BYTES, MEM_LIMIT_BYTES))
    except Exception:
        pass


def _make_workspace():
    """Create a fresh workspace directory readable/executable by everyone."""
    os.makedirs(GRADER_ROOT, exist_ok=True)
    os.chmod(GRADER_ROOT, 0o777)
    wd = os.path.join(GRADER_ROOT, uuid.uuid4().hex)
    os.makedirs(wd, exist_ok=True)
    os.chmod(wd, 0o755)  # nobody can enter + read
    return wd


def _write_script(workdir, filename, program):
    path = os.path.join(workdir, filename)
    with open(path, "w") as f:
        f.write(program)
    os.chmod(path, 0o644)  # nobody can read but not modify
    return path


def _cleanup(workdir):
    try:
        shutil.rmtree(workdir, ignore_errors=True)
    except Exception:
        pass


def _sandbox_argv(interpreter, script_path):
    """Wrap interpreter+script in `sudo -n -u nobody` if sudo is available.
    Falls back to plain interpreter if sudo fails (dev environments only)."""
    return ["sudo", "-n", "-u", SANDBOX_USER, interpreter, script_path]


def grade_python(candidate_code: str, test_code: str, timeout_s: int = DEFAULT_TIMEOUT_S) -> dict:
    if not candidate_code or not candidate_code.strip():
        return {"passed": False, "error": "empty submission", "stdout": "", "stderr": "", "duration_ms": 0}

    program = (
        "# --- candidate code ---\n"
        f"{candidate_code}\n\n"
        "# --- test harness ---\n"
        f"{test_code}\n"
        "print('__ALL_TESTS_PASSED__')\n"
    )
    workdir = _make_workspace()
    try:
        script_path = _write_script(workdir, "solution.py", program)
        argv = _sandbox_argv("/usr/bin/python3", script_path)
        env = {"PATH": "/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1", "HOME": "/tmp"}
        t0 = time.perf_counter()
        try:
            result = subprocess.run(
                argv,
                capture_output=True,
                text=True,
                timeout=timeout_s,
                preexec_fn=_preexec_limit_memory,
                env=env,
                cwd=workdir,
            )
            duration_ms = int((time.perf_counter() - t0) * 1000)
        except subprocess.TimeoutExpired:
            return {"passed": False, "error": "timeout",
                    "stdout": "", "stderr": f"Exceeded {timeout_s}s time limit",
                    "duration_ms": timeout_s * 1000}

        passed = (
            result.returncode == 0
            and "__ALL_TESTS_PASSED__" in (result.stdout or "")
        )
        return {
            "passed": passed,
            "returncode": result.returncode,
            "stdout": (result.stdout or "")[:3000],
            "stderr": (result.stderr or "")[:3000],
            "duration_ms": duration_ms,
            "sandbox": SANDBOX_USER,
        }
    except Exception as e:
        return {"passed": False, "error": f"grader_error: {str(e)[:200]}", "stdout": "", "stderr": "", "duration_ms": 0}
    finally:
        _cleanup(workdir)


def grade_javascript(candidate_code: str, test_code: str, timeout_s: int = DEFAULT_TIMEOUT_S) -> dict:
    if not candidate_code or not candidate_code.strip():
        return {"passed": False, "error": "empty submission", "stdout": "", "stderr": "", "duration_ms": 0}

    program = (
        "// candidate code\n"
        f"{candidate_code}\n\n"
        "// test harness\n"
        "const assert = require('assert');\n"
        f"(async () => {{\n{test_code}\n  console.log('__ALL_TESTS_PASSED__');\n}})().catch(e => {{ console.error(e && e.stack || e); process.exit(1); }});\n"
    )
    workdir = _make_workspace()
    try:
        script_path = _write_script(workdir, "solution.js", program)
        argv = ["sudo", "-n", "-u", SANDBOX_USER, "/usr/bin/node", "--max-old-space-size=256", script_path]
        env = {"PATH": "/usr/bin:/bin", "NODE_ENV": "test", "HOME": "/tmp"}
        t0 = time.perf_counter()
        try:
            result = subprocess.run(
                argv,
                capture_output=True,
                text=True,
                timeout=timeout_s,
                env=env,
                cwd=workdir,
            )
            duration_ms = int((time.perf_counter() - t0) * 1000)
        except subprocess.TimeoutExpired:
            return {"passed": False, "error": "timeout",
                    "stdout": "", "stderr": f"Exceeded {timeout_s}s time limit",
                    "duration_ms": timeout_s * 1000}
        passed = result.returncode == 0 and "__ALL_TESTS_PASSED__" in (result.stdout or "")
        return {
            "passed": passed,
            "returncode": result.returncode,
            "stdout": (result.stdout or "")[:3000],
            "stderr": (result.stderr or "")[:3000],
            "duration_ms": duration_ms,
            "sandbox": SANDBOX_USER,
        }
    except Exception as e:
        return {"passed": False, "error": f"grader_error: {str(e)[:200]}", "stdout": "", "stderr": "", "duration_ms": 0}
    finally:
        _cleanup(workdir)


def grade_task(task: dict, candidate_code: str) -> dict:
    lang = (task or {}).get("language", "python").lower()
    tests = (task or {}).get("test_code", "")
    task_id = (task or {}).get("id", "unknown")

    if not tests:
        return {
            "task_id": task_id, "language": lang, "passed": None,
            "needs_manual_review": True,
            "message": "No test harness — manual review required.",
        }
    if lang == "python":
        r = grade_python(candidate_code, tests)
    elif lang in ("javascript", "js", "typescript", "ts"):
        r = grade_javascript(candidate_code, tests)
    else:
        return {
            "task_id": task_id, "language": lang, "passed": None,
            "needs_manual_review": True,
            "message": f"Auto-grading not supported for language '{lang}'.",
        }
    return {"task_id": task_id, "language": lang, "needs_manual_review": False, **r}
