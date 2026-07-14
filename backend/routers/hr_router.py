"""HR + Master admin endpoints: jobs, applications, invites, submissions, question bank, users."""
import os
import secrets
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from bson import ObjectId

from auth import hash_password
from email_svc import send_invite_email
from seed_jobs import default_assignment
from question_bank import all_modules, get_module, get_questions_by_ids
from deps import (
    db, oid_to_str, require_hr, require_master,
    JobIn, InviteIn, AssignmentIn, HRUserIn, ModuleIn, ImportIn, ScheduleIn,
)

router = APIRouter()


# ---------------- HR: Job CRUD ----------------
@router.post("/hr/jobs")
async def create_job(body: JobIn, _user=Depends(require_hr)):
    doc = body.model_dump()
    if not doc.get("assignment"):
        is_eng = doc["department"] == "Tech & Eng" or "Engineer" in doc["title"]
        doc["assignment"] = default_assignment("engineering" if is_eng else "non-engineering")
    if not doc.get("calendly_url"):
        doc["calendly_url"] = os.environ.get("DEFAULT_CALENDLY_URL", "").strip()
    doc["created_at"] = datetime.now(timezone.utc).isoformat()
    res = await db.jobs.insert_one(doc)
    return {"id": str(res.inserted_id), **{k: v for k, v in doc.items() if k != "_id"}}


@router.put("/hr/jobs/{job_id}")
async def update_job(job_id: str, body: JobIn, _user=Depends(require_hr)):
    updates = body.model_dump()
    await db.jobs.update_one({"_id": ObjectId(job_id)}, {"$set": updates})
    return {"ok": True}


@router.delete("/hr/jobs/{job_id}")
async def delete_job(job_id: str, _user=Depends(require_hr)):
    await db.jobs.delete_one({"_id": ObjectId(job_id)})
    return {"ok": True}


@router.get("/hr/jobs/{job_id}")
async def hr_get_job(job_id: str, _user=Depends(require_hr)):
    doc = await db.jobs.find_one({"_id": ObjectId(job_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Job not found")
    return oid_to_str(doc)


# ---------------- HR: Applications ----------------
@router.get("/hr/applications")
async def list_applications(job_id: Optional[str] = None, sort: str = "trust", _user=Depends(require_hr)):
    q = {"job_id": job_id} if job_id else {}
    docs = await db.applications.find(q).sort("created_at", -1).to_list(1000)
    result = []
    for d in docs:
        d = oid_to_str(d)
        inv = await db.invites.find_one({"application_id": d["id"]})
        sub = await db.submissions.find_one({"application_id": d["id"]})
        d["invite_sent"] = bool(inv)
        d["invite_token"] = inv["token"] if inv else None
        d["invite_status"] = inv["status"] if inv else None
        d["submission_id"] = str(sub["_id"]) if sub else None
        d["ai_risk_avg"] = sub.get("ai_risk_avg") if sub else None
        d["mcq_score"] = sub.get("mcq_score") if sub else None
        d["mcq_pct_weighted"] = sub.get("mcq_pct_weighted") if sub else None
        d["violation_count"] = len(sub.get("violations", [])) if sub else 0
        d["trust_score"] = sub.get("trust_score") if sub else d.get("trust_score")
        result.append(d)
    if sort == "trust":
        result.sort(key=lambda a: (a.get("trust_score") is None, -(a.get("trust_score") or 0)))
    return result


# ---------------- HR: Invites & Submissions ----------------
@router.post("/hr/invite")
async def create_invite(body: InviteIn, _user=Depends(require_hr)):
    app_doc = await db.applications.find_one({"_id": ObjectId(body.application_id)})
    if not app_doc:
        raise HTTPException(status_code=404, detail="Application not found")
    job = await db.jobs.find_one({"_id": ObjectId(app_doc["job_id"])})
    duration = ((job or {}).get("assignment") or {}).get("duration_minutes", 60)

    existing = await db.invites.find_one({"application_id": body.application_id})
    if existing:
        token = existing["token"]
        existing_flag = True
    else:
        token = secrets.token_urlsafe(24)
        doc = {
            "token": token,
            "application_id": body.application_id,
            "job_id": app_doc["job_id"],
            "candidate_email": app_doc["email"],
            "candidate_name": app_doc["name"],
            "status": "pending",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        await db.invites.insert_one(doc)
        await db.applications.update_one(
            {"_id": ObjectId(body.application_id)}, {"$set": {"status": "assignment_sent"}}
        )
        existing_flag = False

    app_url = os.environ.get("APP_URL", "http://localhost:3000")
    exam_url = f"{app_url.rstrip('/')}/exam/{token}"
    email_result = await send_invite_email(
        to_email=app_doc["email"],
        candidate_name=app_doc["name"],
        job_title=app_doc["job_title"],
        exam_url=exam_url,
        duration=duration,
    )
    return {"token": token, "existing": existing_flag, "email": email_result, "exam_url": exam_url}


@router.get("/hr/submissions/{submission_id}")
async def get_submission(submission_id: str, _user=Depends(require_hr)):
    doc = await db.submissions.find_one({"_id": ObjectId(submission_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Submission not found")
    return oid_to_str(doc)


@router.post("/hr/submissions/{submission_id}/override")
async def override_submission(submission_id: str, body: dict, _user=Depends(require_hr)):
    override = bool(body.get("override", True))
    sub = await db.submissions.find_one({"_id": ObjectId(submission_id)})
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")
    new_status = "assignment_submitted" if override else "assignment_rejected_ai"
    await db.submissions.update_one({"_id": ObjectId(submission_id)}, {"$set": {"hr_override": override}})
    await db.applications.update_one(
        {"_id": ObjectId(sub["application_id"])}, {"$set": {"status": new_status}}
    )
    return {"ok": True, "hr_override": override, "application_status": new_status}


@router.post("/hr/schedule-interview")
async def send_schedule_link(body: ScheduleIn, _user=Depends(require_hr)):
    app_doc = await db.applications.find_one({"_id": ObjectId(body.application_id)})
    if not app_doc:
        raise HTTPException(status_code=404, detail="Not found")
    if app_doc.get("status") not in ("assignment_submitted", "interview_scheduled"):
        raise HTTPException(
            status_code=400,
            detail="Candidate must have submitted the assessment and passed HR review first.",
        )
    job = await db.jobs.find_one({"_id": ObjectId(app_doc["job_id"])})
    calendly_url = (job or {}).get("calendly_url", "")
    if not calendly_url:
        raise HTTPException(status_code=400, detail="No Calendly URL set for this role. Edit the job to add one.")
    await db.applications.update_one(
        {"_id": ObjectId(body.application_id)},
        {"$set": {"status": "interview_scheduled", "calendly_url": calendly_url}},
    )
    return {"ok": True, "calendly_url": calendly_url}


# ---------------- HR: Stats & Time-to-Hire ----------------
@router.get("/hr/stats")
async def hr_stats(_user=Depends(require_hr)):
    total_jobs = await db.jobs.count_documents({"status": "open"})
    total_apps = await db.applications.count_documents({})
    total_subs = await db.submissions.count_documents({})
    high_risk = await db.submissions.count_documents({"ai_risk_avg": {"$gte": 60}})
    shortlisted = await db.applications.count_documents({"status": "interview_scheduled"})
    return {
        "open_jobs": total_jobs,
        "total_applications": total_apps,
        "submissions": total_subs,
        "high_ai_risk": high_risk,
        "interview_scheduled": shortlisted,
    }


@router.get("/hr/stats/time-to-hire")
async def time_to_hire(_user=Depends(require_hr)):
    def _hrs(a_iso, b_iso):
        if not a_iso or not b_iso:
            return None
        try:
            a = datetime.fromisoformat(a_iso.replace("Z", "+00:00"))
            b = datetime.fromisoformat(b_iso.replace("Z", "+00:00"))
            return max(0, (b - a).total_seconds() / 3600.0)
        except Exception:
            return None

    def _median(values):
        vs = sorted(v for v in values if v is not None)
        if not vs:
            return None
        n = len(vs)
        mid = n // 2
        if n % 2 == 1:
            return round(vs[mid], 1)
        return round((vs[mid - 1] + vs[mid]) / 2, 1)

    apps = await db.applications.find({}).to_list(5000)
    invites = {i["application_id"]: i async for i in db.invites.find({})}
    subs = {s["application_id"]: s async for s in db.submissions.find({})}

    per_app_stages = []
    by_source = {}
    by_role = {}
    for a in apps:
        aid = str(a["_id"])
        inv = invites.get(aid)
        sub = subs.get(aid)
        applied = a.get("created_at")
        invited = inv.get("created_at") if inv else None
        submitted = sub.get("submitted_at") if sub else None
        s_applied_to_invited = _hrs(applied, invited)
        s_invited_to_submitted = _hrs(invited, submitted)
        s_applied_to_shortlist = _hrs(applied, submitted) if a.get("status") == "interview_scheduled" else None
        row = {
            "applied_to_invited": s_applied_to_invited,
            "invited_to_submitted": s_invited_to_submitted,
            "applied_to_shortlist": s_applied_to_shortlist,
        }
        per_app_stages.append(row)
        src = a.get("source", "unknown")
        by_source.setdefault(src, []).append(row)
        role = a.get("job_title", "unknown")
        by_role.setdefault(role, []).append(row)

    def _summarize(rows):
        return {
            "applied_to_invited_hrs": _median([r["applied_to_invited"] for r in rows]),
            "invited_to_submitted_hrs": _median([r["invited_to_submitted"] for r in rows]),
            "applied_to_shortlist_hrs": _median([r["applied_to_shortlist"] for r in rows]),
            "count": len(rows),
        }

    return {
        "overall": _summarize(per_app_stages),
        "by_source": {k: _summarize(v) for k, v in by_source.items()},
        "by_role": {k: _summarize(v) for k, v in by_role.items()},
    }


# ---------------- HR: Assignment editor ----------------
@router.get("/hr/jobs/{job_id}/assignment")
async def get_assignment(job_id: str, _user=Depends(require_hr)):
    doc = await db.jobs.find_one({"_id": ObjectId(job_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Job not found")
    return doc.get("assignment") or default_assignment("engineering")


@router.put("/hr/jobs/{job_id}/assignment")
async def update_assignment(job_id: str, body: AssignmentIn, _user=Depends(require_hr)):
    for m in body.mcqs:
        if not (0 <= m.correct_index < len(m.options)):
            raise HTTPException(status_code=400, detail=f"MCQ '{m.id}' correct_index out of range")
    if body.duration_minutes < 5 or body.duration_minutes > 240:
        raise HTTPException(status_code=400, detail="Duration must be between 5 and 240 minutes")
    payload = body.model_dump()
    await db.jobs.update_one({"_id": ObjectId(job_id)}, {"$set": {"assignment": payload}})
    return {"ok": True, "assignment": payload}


# ---------------- HR: Question bank (read) ----------------
async def _custom_modules():
    docs = await db.custom_modules.find({"is_deleted": {"$ne": True}}).to_list(500)
    result = []
    for d in docs:
        result.append({
            "id": d["id"],
            "title": d["title"],
            "category": d["category"],
            "description": d.get("description", ""),
            "count": len(d.get("questions", [])),
            "questions": d.get("questions", []),
            "is_custom": True,
        })
    return result


@router.get("/hr/question-bank")
async def list_modules(_user=Depends(require_hr)):
    seed = [
        {"id": m["id"], "title": m["title"], "category": m["category"],
         "description": m["description"], "count": m["count"], "is_custom": False}
        for m in all_modules()
    ]
    custom = [{k: v for k, v in m.items() if k != "questions"} for m in await _custom_modules()]
    return seed + custom


@router.get("/hr/question-bank/{module_id}")
async def get_module_detail(module_id: str, _user=Depends(require_hr)):
    m = get_module(module_id)
    if m:
        return {**m, "questions": get_questions_by_ids(m["question_ids"]), "is_custom": False}
    doc = await db.custom_modules.find_one({"id": module_id, "is_deleted": {"$ne": True}})
    if doc:
        return {
            "id": doc["id"], "title": doc["title"], "category": doc["category"],
            "description": doc.get("description", ""),
            "questions": doc.get("questions", []),
            "count": len(doc.get("questions", [])),
            "is_custom": True,
        }
    raise HTTPException(status_code=404, detail="Module not found")


async def _resolve_questions(question_ids):
    resolved = list(get_questions_by_ids(question_ids))
    resolved_ids = {q["id"] for q in resolved}
    missing = [q for q in question_ids if q not in resolved_ids]
    if missing:
        for doc in await db.custom_modules.find({"is_deleted": {"$ne": True}}).to_list(500):
            for q in doc.get("questions", []):
                if q.get("id") in missing:
                    resolved.append(q)
    return resolved


@router.post("/hr/jobs/{job_id}/assignment/import")
async def import_questions(job_id: str, body: ImportIn, _user=Depends(require_hr)):
    job = await db.jobs.find_one({"_id": ObjectId(job_id)})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    a = job.get("assignment") or default_assignment("engineering")
    a.setdefault("mcqs", [])
    a.setdefault("short_answers", [])
    if a.get("coding") and not a.get("coding_tasks"):
        a["coding_tasks"] = [a["coding"]]
    a.setdefault("coding_tasks", [])
    a.pop("coding", None)

    existing_ids = (
        {m["id"] for m in a["mcqs"]}
        | {s["id"] for s in a["short_answers"]}
        | {c["id"] for c in a["coding_tasks"]}
    )
    added_mcq = added_sa = added_code = 0
    resolved = await _resolve_questions(body.question_ids)
    for q in resolved:
        if q["id"] in existing_ids:
            continue
        if q["type"] == "mcq":
            a["mcqs"].append({
                "id": q["id"], "question": q["question"],
                "options": q["options"], "correct_index": q["correct_index"],
                "weight": q.get("weight", 1),
            })
            added_mcq += 1
        elif q["type"] == "sa":
            a["short_answers"].append({
                "id": q["id"], "question": q["question"],
                "min_words": q.get("min_words", 40),
                "weight": q.get("weight", 1),
            })
            added_sa += 1
        elif q["type"] == "code":
            a["coding_tasks"].append({
                "id": q["id"],
                "prompt": q["prompt"],
                "starter_code": q.get("starter_code", ""),
                "weight": q.get("weight", 1),
                "language": q.get("language", "python"),
                "test_code": q.get("test_code", ""),
            })
            added_code += 1
    await db.jobs.update_one({"_id": ObjectId(job_id)}, {"$set": {"assignment": a}})
    return {"ok": True, "added_mcq": added_mcq, "added_sa": added_sa, "added_code": added_code}


# ---------------- Master admin: HR user management ----------------
@router.get("/master/users")
async def list_hr_users(_user=Depends(require_master)):
    docs = await db.users.find({"role": {"$in": ["hr_admin", "master_admin"]}}).to_list(200)
    return [
        {
            "id": str(d["_id"]),
            "email": d["email"],
            "name": d.get("name"),
            "role": d.get("role"),
            "is_active": d.get("is_active", True),
            "created_at": d.get("created_at"),
        }
        for d in docs
    ]


@router.post("/master/users")
async def create_hr_user(body: HRUserIn, _user=Depends(require_master)):
    if len(body.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    email = body.email.lower()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=409, detail="Email already registered")
    doc = {
        "email": email,
        "password_hash": hash_password(body.password),
        "name": body.name.strip(),
        "role": "hr_admin",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    res = await db.users.insert_one(doc)
    return {"id": str(res.inserted_id), "email": email, "name": doc["name"], "role": "hr_admin"}


@router.post("/master/users/{user_id}/toggle")
async def toggle_hr_user(user_id: str, _user=Depends(require_master)):
    doc = await db.users.find_one({"_id": ObjectId(user_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="User not found")
    if doc.get("role") == "master_admin":
        raise HTTPException(status_code=400, detail="Cannot deactivate master admin")
    new_state = not doc.get("is_active", True)
    await db.users.update_one({"_id": ObjectId(user_id)}, {"$set": {"is_active": new_state}})
    return {"id": user_id, "is_active": new_state}


# ---------------- Master admin: Question-bank CRUD ----------------
@router.post("/master/question-bank/modules")
async def create_custom_module(body: ModuleIn, _user=Depends(require_master)):
    if get_module(body.id):
        raise HTTPException(status_code=409, detail="Module id collides with a seeded module")
    if await db.custom_modules.find_one({"id": body.id}):
        raise HTTPException(status_code=409, detail="Module id already exists")
    doc = {
        **body.model_dump(),
        "is_deleted": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.custom_modules.insert_one(doc)
    return {"ok": True, "id": body.id}


@router.put("/master/question-bank/modules/{module_id}")
async def update_custom_module(module_id: str, body: ModuleIn, _user=Depends(require_master)):
    doc = await db.custom_modules.find_one({"id": module_id, "is_deleted": {"$ne": True}})
    if not doc:
        raise HTTPException(status_code=404, detail="Custom module not found")
    updates = body.model_dump()
    updates["id"] = module_id
    await db.custom_modules.update_one({"id": module_id}, {"$set": updates})
    return {"ok": True}


@router.delete("/master/question-bank/modules/{module_id}")
async def delete_custom_module(module_id: str, _user=Depends(require_master)):
    r = await db.custom_modules.update_one({"id": module_id}, {"$set": {"is_deleted": True}})
    if r.matched_count == 0:
        raise HTTPException(status_code=404, detail="Custom module not found")
    return {"ok": True}
