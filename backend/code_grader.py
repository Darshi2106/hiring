"""Sandboxed code grader — runs candidate code + test harness in a subprocess with timeout.

Supports:
- python: full auto-grade with pytest-style assertions
- javascript: skipped (marked for manual review)
- sql: skipped (marked for manual review)
- Any language without `test_code`: skipped (manual review)

Safety:
- Subprocess with 10-second timeout
- Memory limit (256 MB) via resource.setrlimit
- No shell=True
- Only stdlib + numpy/pandas/sklearn/opencv available in the container
"""
import subprocess
import resource
import tempfile
import os
import logging

logger = logging.getLogger("grader")

MEM_LIMIT_BYTES = 256 * 1024 * 1024
DEFAULT_TIMEOUT_S = 10


def _preexec_limit_memory():
    """Called in child before exec."""
    try:
        resource.setrlimit(resource.RLIMIT_AS, (MEM_LIMIT_BYTES, MEM_LIMIT_BYTES))
    except Exception:
        pass


def grade_python(candidate_code: str, test_code: str, timeout_s: int = DEFAULT_TIMEOUT_S) -> dict:
    """Run candidate_code followed by test_code in a fresh subprocess.
    Returns {passed, stdout, stderr, error?, duration_ms}.
    """
    if not candidate_code or not candidate_code.strip():
        return {"passed": False, "error": "empty submission", "stdout": "", "stderr": "", "duration_ms": 0}

    program = (
        "# --- candidate code ---\n"
        f"{candidate_code}\n\n"
        "# --- test harness ---\n"
        f"{test_code}\n"
        "print('__ALL_TESTS_PASSED__')\n"
    )
    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, dir="/tmp"
    )
    try:
        tmp.write(program)
        tmp.flush()
        tmp.close()

        import time
        t0 = time.perf_counter()
        try:
            result = subprocess.run(
                ["python3", tmp.name],
                capture_output=True,
                text=True,
                timeout=timeout_s,
                preexec_fn=_preexec_limit_memory,
                env={"PATH": os.environ.get("PATH", ""), "PYTHONDONTWRITEBYTECODE": "1"},
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
        }
    except Exception as e:
        return {"passed": False, "error": f"grader_error: {str(e)[:200]}", "stdout": "", "stderr": "", "duration_ms": 0}
    finally:
        try:
            os.unlink(tmp.name)
        except Exception:
            pass


def grade_task(task: dict, candidate_code: str) -> dict:
    """Grade one coding task.
    Task fields: id, prompt, starter_code, language, test_code (optional).
    """
    lang = (task or {}).get("language", "python").lower()
    tests = (task or {}).get("test_code", "")
    task_id = (task or {}).get("id", "unknown")

    if not tests or lang != "python":
        return {
            "task_id": task_id,
            "language": lang,
            "passed": None,
            "needs_manual_review": True,
            "message": "Automated grading unavailable for this task.",
        }
    result = grade_python(candidate_code, tests)
    return {"task_id": task_id, "language": lang, "needs_manual_review": False, **result}
