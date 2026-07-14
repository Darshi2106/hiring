"""Exam (candidate proctored assignment) + resume upload/download endpoints."""
import logging
import os
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Response
from bson import ObjectId

from ai_detect import score_text_ai_risk
from code_grader import grade_task
from storage_svc import upload_resume, get_object
from deps import db, oid_to_str, require_hr, compute_trust_score, SubmitAnswersIn

router = APIRouter()
logger = logging.getLogger(__name__)

MAX_RESUME_BYTES = 5 * 1024 * 1024  # 5MB


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


@router.post("/exam/submit")
async def submit_exam(body: SubmitAnswersIn):
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

    auto_shortlist = False
    if not auto_flagged and job.get("auto_shortlist_enabled", True):
        mcq_ok = mcq_pct >= int(job.get("auto_shortlist_mcq_min", 80))
        ai_ok = ai_risk_max < int(job.get("auto_shortlist_ai_max", 10))
        viol_ok = len(body.violations) <= int(job.get("auto_shortlist_max_violations", 0))
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

    trust = compute_trust_score(mcq_pct, coding_results, ai_risk_max, body.violations)

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
        "violations": body.violations,
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


@router.post("/exam/violation")
async def log_violation(body: dict):
    return {"ok": True}


# ---------------- Resume upload / download ----------------
@router.post("/resumes/upload")
async def resume_upload(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename")
    data = await file.read()
    if len(data) > MAX_RESUME_BYTES:
        raise HTTPException(status_code=413, detail="File too large (max 5MB)")
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
    file_doc = {
        "storage_path": result["storage_path"],
        "original_filename": result["original_filename"],
        "content_type": result["content_type"],
        "size": result["size"],
        "is_deleted": False,
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
    """HR-protected resume download."""
    try:
        doc = await db.resume_files.find_one({"_id": ObjectId(file_id), "is_deleted": False})
    except Exception:
        raise HTTPException(status_code=404, detail="Not found")
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    data, ct = get_object(doc["storage_path"])
    return Response(
        content=data,
        media_type=doc.get("content_type") or ct,
        headers={"Content-Disposition": f'inline; filename="{doc["original_filename"]}"'},
    )
