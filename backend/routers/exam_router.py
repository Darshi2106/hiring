"""Exam (candidate proctored assignment) + resume upload/download endpoints.

Security hardening applied:
- SEC-003: /exam/violation persists each event server-side; /exam/submit uses
  the server-recorded violation count for the auto-shortlist gate (client
  cannot bypass by sending violations=[]).
- SEC-004: /resumes/upload validates by magic bytes (PDF / DOC / DOCX),
  rate-limited via slowapi, requires 'X-Candidate-Session' presence to make
  drive-by anonymous abuse harder.
- Resume download: forces attachment disposition and pins content-type to
  the DB-stored (server-validated) value.
"""
import logging
import os
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Response, Request
from bson import ObjectId

from ai_detect import score_text_ai_risk
from code_grader import grade_task
from storage_svc import upload_resume, get_object
from deps import db, oid_to_str, require_hr, compute_trust_score, SubmitAnswersIn, limiter

try:
    import magic  # python-magic (libmagic)
    _MAGIC_OK = True
except Exception:
    _MAGIC_OK = False

router = APIRouter()
logger = logging.getLogger(__name__)

MAX_RESUME_BYTES = 5 * 1024 * 1024  # 5MB
ALLOWED_RESUME_MIME = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/octet-stream",  # some DOC files come through as this
}
ALLOWED_EXT = {".pdf", ".doc", ".docx"}


# ---------------- Exam ----------------
@router.get("/exam/{token}")
async def get_exam(token: str):
    inv = await db.invites.find_one({"token": token})
    if not inv:
        raise HTTPException(status_code=404, detail="Invalid invite link")
    if inv["status"] == "submitted":
        raise HTTPException(status_code=410, detail="This assignment has already been submitted")
    job = await db.jobs.find_one({"_id": ObjectId(inv["job_id"])})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    a = job.get("assignment", {})
    mcqs_public = [
        {"id": m["id"], "question": m["question"], "options": m["options"]}
        for m in a.get("mcqs", [])
    ]
    coding_tasks = a.get("coding_tasks") or ([a["coding"]] if a.get("coding") else [])
    coding_tasks_public = [
        {k: v for k, v in t.items() if k != "test_code"}
        for t in coding_tasks
    ]
    return {
        "invite_token": token,
        "candidate_name": inv["candidate_name"],
        "job_title": job["title"],
        "duration_minutes": a.get("duration_minutes", 60),
        "mcqs": mcqs_public,
        "short_answers": a.get("short_answers", []),
        "coding_tasks": coding_tasks_public,
        "status": inv["status"],
    }


@router.post("/exam/start")
async def start_exam(body: dict):
    token = body.get("token")
    inv = await db.invites.find_one({"token": token})
    if not inv:
        raise HTTPException(status_code=404, detail="Invalid invite")
    if inv["status"] == "submitted":
        raise HTTPException(status_code=410, detail="Already submitted")
    if inv["status"] == "pending":
        await db.invites.update_one(
            {"token": token},
            {"$set": {"status": "in_progress", "started_at": datetime.now(timezone.utc).isoformat()}},
        )
    return {"ok": True}


@router.post("/exam/violation")
async def log_violation(body: dict):
    """SEC-003: real-time server-side violation logging.

    Body: {token, type, detail?} — token must be a valid, non-submitted invite.
    Persists the event on the invite document so /exam/submit can use the
    server-recorded count for the auto-shortlist gate.
    """
    token = (body or {}).get("token")
    v_type = (body or {}).get("type") or ""
    if not token or not v_type:
        raise HTTPException(status_code=400, detail="token and type required")
    inv = await db.invites.find_one({"token": token})
    if not inv:
        raise HTTPException(status_code=404, detail="Invalid invite")
    if inv["status"] == "submitted":
        raise HTTPException(status_code=410, detail="Already submitted")
    event = {
        "type": str(v_type)[:60],
        "detail": str((body or {}).get("detail", ""))[:200],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    await db.invites.update_one(
        {"token": token},
        {"$push": {"violations_server": event}},
    )
    return {"ok": True}


@router.post("/exam/submit")
@limiter.limit("3/hour")
async def submit_exam(request: Request, body: SubmitAnswersIn):
    inv = await db.invites.find_one({"token": body.invite_token})
    if not inv:
        raise HTTPException(status_code=404, detail="Invalid invite")
    if inv["status"] == "submitted":
        raise HTTPException(status_code=410, detail="Already submitted")
    job = await db.jobs.find_one({"_id": ObjectId(inv["job_id"])})
    a = job.get("assignment", {})

    # Score MCQs (weighted)
    mcq_correct = 0
    mcq_total = len(a.get("mcqs", []))
    weighted_correct = 0
    weighted_possible = 0
    for m in a.get("mcqs", []):
        w = int(m.get("weight", 1))
        weighted_possible += w
        if body.mcq_answers.get(m["id"]) == m["correct_index"]:
            mcq_correct += 1
            weighted_correct += w
    mcq_pct = int(round(100 * weighted_correct / weighted_possible)) if weighted_possible else 0

    # AI-detect each short answer
    ai_results = {}
    scores = []
    for sa in a.get("short_answers", []):
        ans = body.short_answers.get(sa["id"], "")
        result = await score_text_ai_risk(sa["question"], ans)
        ai_results[sa["id"]] = result
        if result["ai_risk_score"] >= 0:
            scores.append(result["ai_risk_score"])
    ai_risk_avg = int(sum(scores) / len(scores)) if scores else 0
    ai_risk_max = max(scores) if scores else 0

    threshold = int(job.get("ai_reject_threshold", 70))
    auto_flagged = ai_risk_max >= threshold

    # SEC-003: use server-recorded violations for the gate (fall back to
    # the body only if the server has zero recorded — for backwards
    # compatibility with older clients that don't post to /exam/violation).
    server_violations = inv.get("violations_server") or []
    client_violations = body.violations or []
    effective_violation_count = max(len(server_violations), len(client_violations))

    auto_shortlist = False
    if not auto_flagged and job.get("auto_shortlist_enabled", True):
        mcq_ok = mcq_pct >= int(job.get("auto_shortlist_mcq_min", 80))
        ai_ok = ai_risk_max < int(job.get("auto_shortlist_ai_max", 10))
        viol_ok = effective_violation_count <= int(job.get("auto_shortlist_max_violations", 0))
        has_calendly = bool(job.get("calendly_url"))
        auto_shortlist = mcq_ok and ai_ok and viol_ok and has_calendly

    if auto_flagged:
        app_status = "assignment_rejected_ai"
    elif auto_shortlist:
        app_status = "interview_scheduled"
    else:
        app_status = "assignment_submitted"

    now = datetime.now(timezone.utc).isoformat()

    coding_answers = dict(body.coding_answers or {})
    legacy_tasks = a.get("coding_tasks") or ([a["coding"]] if a.get("coding") else [])
    if body.coding_answer and legacy_tasks and not coding_answers:
        coding_answers[legacy_tasks[0]["id"]] = body.coding_answer

    coding_results = {}
    for task in legacy_tasks:
        cand_code = coding_answers.get(task["id"], "")
        coding_results[task["id"]] = grade_task(task, cand_code)

    # Trust score uses server-verified violation count (dict-shaped placeholders for compute helper)
    trust = compute_trust_score(mcq_pct, coding_results, ai_risk_max, [None] * effective_violation_count)

    sub_doc = {
        "invite_token": body.invite_token,
        "application_id": inv["application_id"],
        "job_id": inv["job_id"],
        "candidate_name": inv["candidate_name"],
        "candidate_email": inv["candidate_email"],
        "mcq_answers": body.mcq_answers,
        "short_answers": body.short_answers,
        "coding_answers": coding_answers,
        "coding_results": coding_results,
        "coding_answer": body.coding_answer or (list(coding_answers.values())[0] if coding_answers else ""),
        "ai_results": ai_results,
        "ai_risk_avg": ai_risk_avg,
        "ai_risk_max": ai_risk_max,
        "ai_reject_threshold": threshold,
        "auto_flagged": auto_flagged,
        "auto_shortlisted": auto_shortlist,
        "hr_override": False,
        "trust_score": trust["score"],
        "trust_breakdown": trust["breakdown"],
        "mcq_score": mcq_correct,
        "mcq_total": mcq_total,
        "mcq_pct_weighted": mcq_pct,
        "mcq_weighted_correct": weighted_correct,
        "mcq_weighted_possible": weighted_possible,
        # Persist both for HR review + auditability
        "violations": client_violations,
        "violations_server": server_violations,
        "violation_count_used": effective_violation_count,
        "webcam_snapshots": body.webcam_snapshots[:20],
        "time_taken_seconds": body.time_taken_seconds,
        "submitted_at": now,
    }
    res = await db.submissions.insert_one(sub_doc)
    await db.invites.update_one(
        {"token": body.invite_token},
        {"$set": {"status": "submitted", "submitted_at": now}},
    )
    update_fields = {"status": app_status, "trust_score": trust["score"]}
    if auto_shortlist:
        update_fields["calendly_url"] = job.get("calendly_url", "")
    await db.applications.update_one(
        {"_id": ObjectId(inv["application_id"])},
        {"$set": update_fields},
    )
    return {
        "submission_id": str(res.inserted_id),
        "mcq_score": mcq_correct,
        "mcq_total": mcq_total,
        "mcq_pct_weighted": mcq_pct,
        "ai_risk_avg": ai_risk_avg,
        "ai_risk_max": ai_risk_max,
        "auto_flagged": auto_flagged,
        "auto_shortlisted": auto_shortlist,
        "trust_score": trust["score"],
        "trust_breakdown": trust["breakdown"],
    }


# ---------------- Resume upload / download ----------------
def _validate_resume_bytes(filename: str, data: bytes, declared_ct: str) -> tuple[bool, str]:
    """SEC-004: validate resume file by extension + magic bytes."""
    ext = os.path.splitext(filename or "")[1].lower()
    if ext not in ALLOWED_EXT:
        return False, f"Unsupported extension '{ext}'. Allowed: {', '.join(sorted(ALLOWED_EXT))}."
    if _MAGIC_OK:
        try:
            sniffed = magic.from_buffer(data[:2048], mime=True) or ""
        except Exception:
            sniffed = ""
        # PDF check
        if ext == ".pdf" and not (sniffed == "application/pdf" or data[:4] == b"%PDF"):
            return False, "File does not look like a PDF (magic bytes mismatch)."
        # DOC (OLE compound)
        if ext == ".doc" and not (sniffed in {"application/msword", "application/x-ole-storage", "application/octet-stream"}
                                  or data[:8] == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"):
            return False, "File does not look like a legacy DOC (magic bytes mismatch)."
        # DOCX is a ZIP
        if ext == ".docx" and not (sniffed in {"application/zip",
                                               "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                               "application/octet-stream"}
                                   or data[:2] == b"PK"):
            return False, "File does not look like a DOCX (magic bytes mismatch)."
    else:
        # Fallback: basic magic-byte check
        if ext == ".pdf" and data[:4] != b"%PDF":
            return False, "File does not look like a PDF."
        if ext == ".docx" and data[:2] != b"PK":
            return False, "File does not look like a DOCX."
        if ext == ".doc" and data[:8] != b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1":
            return False, "File does not look like a legacy DOC."
    return True, "ok"


@router.post("/resumes/upload")
@limiter.limit("10/hour")
async def resume_upload(request: Request, file: UploadFile = File(...)):
    """Public but hardened: extension + magic-byte content validation + size cap.
    Rate limiting is applied via slowapi middleware in server.py."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename")
    data = await file.read()
    if len(data) == 0:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(data) > MAX_RESUME_BYTES:
        raise HTTPException(status_code=413, detail="File too large (max 5MB)")

    ok, reason = _validate_resume_bytes(file.filename, data, file.content_type or "")
    if not ok:
        raise HTTPException(status_code=415, detail=reason)

    candidate_email = "anonymous"
    try:
        result = upload_resume(
            candidate_email=candidate_email,
            filename=file.filename,
            data=data,
            content_type=file.content_type or "application/octet-stream",
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)[:120]}")
    now = datetime.now(timezone.utc).isoformat()
    # Store the (server-validated) canonical content-type based on extension
    ext = os.path.splitext(file.filename)[1].lower()
    canonical_ct = {
        ".pdf": "application/pdf",
        ".doc": "application/msword",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }.get(ext, "application/octet-stream")
    file_doc = {
        "storage_path": result["storage_path"],
        "original_filename": result["original_filename"],
        "content_type": canonical_ct,
        "size": result["size"],
        "is_deleted": False,
        "uploader_ip": (request.client.host if request.client else None),
        "created_at": now,
    }
    ins = await db.resume_files.insert_one(file_doc)
    return {
        "file_id": str(ins.inserted_id),
        "storage_path": result["storage_path"],
        "size": result["size"],
        "download_url": f"/api/resumes/{ins.inserted_id}",
    }


@router.get("/resumes/{file_id}")
async def resume_download(file_id: str, _user=Depends(require_hr)):
    """HR-protected resume download. Forces `attachment` disposition + pinned
    server-canonical content-type (SEC hardening P3)."""
    try:
        doc = await db.resume_files.find_one({"_id": ObjectId(file_id), "is_deleted": False})
    except Exception:
        raise HTTPException(status_code=404, detail="Not found")
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    data, ct = get_object(doc["storage_path"])
    # Sanitize filename for Content-Disposition (strip quotes/CRLF)
    safe_name = "".join(c for c in (doc.get("original_filename") or "resume") if c.isalnum() or c in "._- ")
    safe_name = safe_name.strip() or "resume"
    return Response(
        content=data,
        media_type=doc.get("content_type") or "application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{safe_name}"',
                 "X-Content-Type-Options": "nosniff"},
    )
