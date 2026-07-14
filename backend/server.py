from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env", override=True)

import os
import secrets
import logging
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import FastAPI, APIRouter, HTTPException, Depends, Request, UploadFile, File, Response
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, EmailStr, Field
from bson import ObjectId

from auth import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
    seed_admin,
)
from seed_jobs import seed_jobs, default_assignment
from ai_detect import score_text_ai_risk
from email_svc import send_invite_email
from storage_svc import init_storage, upload_resume, get_object
from question_bank import (
    seed_question_bank,
    all_modules,
    get_module,
    get_questions_by_ids,
)

# ---------------- DB ----------------
mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]

app = FastAPI()
api = APIRouter(prefix="/api")


def oid_to_str(doc):
    if not doc:
        return doc
    doc["id"] = str(doc["_id"])
    doc.pop("_id", None)
    doc.pop("password_hash", None)
    return doc


# ---------------- Models ----------------
class LoginIn(BaseModel):
    email: EmailStr
    password: str


class CandidateRegisterIn(BaseModel):
    name: str
    email: EmailStr
    password: str


class JobIn(BaseModel):
    title: str
    department: str
    location: str
    type: str = "Full-Time"
    description: str
    requirements: List[str] = []
    status: str = "open"
    assignment: Optional[dict] = None
    ai_reject_threshold: int = 70  # 0-100; >=X on any short answer -> auto-flag
    calendly_url: Optional[str] = ""
    # Auto-shortlist thresholds (all must be satisfied to auto-schedule interview)
    auto_shortlist_enabled: bool = True
    auto_shortlist_mcq_min: int = 80         # min MCQ % (weighted)
    auto_shortlist_ai_max: int = 10          # max AI-risk (max across answers)
    auto_shortlist_max_violations: int = 0   # max proctoring violations allowed


class ApplyIn(BaseModel):
    job_id: str
    name: str
    email: EmailStr
    phone: Optional[str] = ""
    resume_url: Optional[str] = ""
    cover_letter: Optional[str] = ""


class InviteIn(BaseModel):
    application_id: str


class ViolationIn(BaseModel):
    type: str
    detail: Optional[str] = ""


class SubmitAnswersIn(BaseModel):
    invite_token: str
    mcq_answers: dict  # {mcq_id: option_index}
    short_answers: dict  # {sa_id: text}
    coding_answer: Optional[str] = ""
    violations: List[dict] = []
    webcam_snapshots: List[str] = []  # base64 data URLs
    time_taken_seconds: int = 0


# ---------------- Role guards ----------------
async def require_hr(current=Depends(get_current_user)):
    if current.get("role") not in ("hr_admin", "master_admin"):
        raise HTTPException(status_code=403, detail="HR access required")
    if current.get("is_active") is False:
        raise HTTPException(status_code=403, detail="Account is deactivated")
    return current


async def require_master(current=Depends(get_current_user)):
    if current.get("role") != "master_admin":
        raise HTTPException(status_code=403, detail="Master admin access required")
    if current.get("is_active") is False:
        raise HTTPException(status_code=403, detail="Account is deactivated")
    return current


# ---------------- Startup ----------------
@app.on_event("startup")
async def startup():
    await db.users.create_index("email", unique=True)
    await db.invites.create_index("token", unique=True)
    await db.applications.create_index([("job_id", 1), ("email", 1)])
    await db.applications.create_index([("candidate_id", 1), ("created_at", -1)])
    await seed_admin(db)
    await seed_jobs(db)
    await seed_question_bank(db)
    # Backfill default Calendly URL on any job missing it
    default_calendly = os.environ.get("DEFAULT_CALENDLY_URL", "").strip()
    if default_calendly:
        await db.jobs.update_many(
            {"$or": [{"calendly_url": {"$exists": False}}, {"calendly_url": ""}, {"calendly_url": None}]},
            {"$set": {"calendly_url": default_calendly}},
        )
    try:
        init_storage()
    except Exception as e:
        logging.getLogger(__name__).warning("Storage init failed: %s", e)


@app.on_event("shutdown")
async def shutdown():
    client.close()


# ---------------- Auth ----------------
@api.post("/auth/login")
async def login(body: LoginIn):
    user = await db.users.find_one({"email": body.email.lower()})
    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if user.get("is_active") is False:
        raise HTTPException(status_code=403, detail="Account is deactivated. Contact your master admin.")
    token = create_access_token(str(user["_id"]), user["email"])
    return {
        "token": token,
        "user": {
            "id": str(user["_id"]),
            "email": user["email"],
            "name": user.get("name"),
            "role": user.get("role"),
        },
    }


@api.get("/auth/me")
async def me(current=Depends(get_current_user)):
    return current


# ---------------- Candidate Auth ----------------
@api.post("/candidate/register")
async def candidate_register(body: CandidateRegisterIn):
    email = body.email.lower()
    if len(body.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    existing = await db.users.find_one({"email": email})
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")
    doc = {
        "email": email,
        "password_hash": hash_password(body.password),
        "name": body.name.strip(),
        "role": "candidate",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    res = await db.users.insert_one(doc)
    token = create_access_token(str(res.inserted_id), email)
    return {
        "token": token,
        "user": {"id": str(res.inserted_id), "email": email, "name": doc["name"], "role": "candidate"},
    }


@api.post("/candidate/login")
async def candidate_login(body: LoginIn):
    user = await db.users.find_one({"email": body.email.lower(), "role": "candidate"})
    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_access_token(str(user["_id"]), user["email"])
    return {
        "token": token,
        "user": {
            "id": str(user["_id"]),
            "email": user["email"],
            "name": user.get("name"),
            "role": "candidate",
        },
    }


@api.get("/candidate/me")
async def candidate_me(current=Depends(get_current_user)):
    if current.get("role") != "candidate":
        raise HTTPException(status_code=403, detail="Not a candidate")
    return current


@api.get("/candidate/applications")
async def candidate_applications(current=Depends(get_current_user)):
    if current.get("role") != "candidate":
        raise HTTPException(status_code=403, detail="Not a candidate")
    docs = await db.applications.find({"candidate_id": current["id"]}).sort("created_at", -1).to_list(200)
    result = []
    for d in docs:
        d = oid_to_str(d)
        inv = await db.invites.find_one({"application_id": d["id"]})
        sub = await db.submissions.find_one({"application_id": d["id"]})
        d["invite_token"] = inv["token"] if inv else None
        d["invite_status"] = inv["status"] if inv else None
        d["has_submitted"] = bool(sub)
        result.append(d)
    return result


# ---------------- Public: Jobs & Apply ----------------
@api.get("/jobs")
async def list_jobs(status: Optional[str] = "open"):
    q = {"status": status} if status else {}
    docs = await db.jobs.find(q).sort("created_at", -1).to_list(500)
    return [oid_to_str(d) for d in docs]


@api.get("/jobs/{job_id}")
async def get_job(job_id: str):
    try:
        doc = await db.jobs.find_one({"_id": ObjectId(job_id)})
    except Exception:
        raise HTTPException(status_code=404, detail="Job not found")
    if not doc:
        raise HTTPException(status_code=404, detail="Job not found")
    # Don't leak MCQ correct answers to public
    if doc.get("assignment"):
        a = doc["assignment"]
        public_a = {
            "duration_minutes": a.get("duration_minutes", 60),
            "mcq_count": len(a.get("mcqs", [])),
            "sa_count": len(a.get("short_answers", [])),
            "has_coding": bool(a.get("coding")),
        }
        doc["assignment_summary"] = public_a
        doc.pop("assignment", None)
    return oid_to_str(doc)


@api.post("/applications")
async def apply(body: ApplyIn, request: Request):
    try:
        job = await db.jobs.find_one({"_id": ObjectId(body.job_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid job id")
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Optionally link to a logged-in candidate
    candidate_id = None
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        try:
            from auth import decode_token
            payload = decode_token(auth_header[7:])
            user = await db.users.find_one({"_id": ObjectId(payload["sub"])})
            if user and user.get("role") == "candidate":
                candidate_id = str(user["_id"])
        except Exception:
            candidate_id = None

    # Prevent duplicate application for same candidate + job
    if candidate_id:
        dup = await db.applications.find_one({"job_id": body.job_id, "candidate_id": candidate_id})
        if dup:
            raise HTTPException(status_code=409, detail="You have already applied to this role")

    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "job_id": body.job_id,
        "job_title": job["title"],
        "candidate_id": candidate_id,
        "name": body.name,
        "email": body.email.lower(),
        "phone": body.phone,
        "resume_url": body.resume_url,
        "cover_letter": body.cover_letter,
        "status": "applied",
        "created_at": now,
    }
    res = await db.applications.insert_one(doc)
    doc["id"] = str(res.inserted_id)
    doc.pop("_id", None)
    return doc


# ---------------- HR: Job CRUD ----------------
@api.post("/hr/jobs")
async def create_job(body: JobIn, _user=Depends(require_hr)):
    doc = body.model_dump()
    if not doc.get("assignment"):
        is_eng = doc["department"] == "Tech & Eng" or "Engineer" in doc["title"]
        doc["assignment"] = default_assignment("engineering" if is_eng else "non-engineering")
    doc["created_at"] = datetime.now(timezone.utc).isoformat()
    res = await db.jobs.insert_one(doc)
    return {"id": str(res.inserted_id), **{k: v for k, v in doc.items() if k != "_id"}}


@api.put("/hr/jobs/{job_id}")
async def update_job(job_id: str, body: JobIn, _user=Depends(require_hr)):
    updates = body.model_dump()
    await db.jobs.update_one({"_id": ObjectId(job_id)}, {"$set": updates})
    return {"ok": True}


@api.delete("/hr/jobs/{job_id}")
async def delete_job(job_id: str, _user=Depends(require_hr)):
    await db.jobs.delete_one({"_id": ObjectId(job_id)})
    return {"ok": True}


@api.get("/hr/jobs/{job_id}")
async def hr_get_job(job_id: str, _user=Depends(require_hr)):
    doc = await db.jobs.find_one({"_id": ObjectId(job_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Job not found")
    return oid_to_str(doc)


# ---------------- HR: Applications ----------------
@api.get("/hr/applications")
async def list_applications(job_id: Optional[str] = None, _user=Depends(require_hr)):
    q = {"job_id": job_id} if job_id else {}
    docs = await db.applications.find(q).sort("created_at", -1).to_list(1000)
    # attach invite/submission summary
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
        d["violation_count"] = len(sub.get("violations", [])) if sub else 0
        result.append(d)
    return result


@api.post("/hr/invite")
async def create_invite(body: InviteIn, _user=Depends(require_hr)):
    app_doc = await db.applications.find_one({"_id": ObjectId(body.application_id)})
    if not app_doc:
        raise HTTPException(status_code=404, detail="Application not found")
    job = await db.jobs.find_one({"_id": ObjectId(app_doc["job_id"])})
    duration = (job or {}).get("assignment", {}).get("duration_minutes", 60)
    # If already invited, resend email but return existing token
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

    # Send email (mock if RESEND_API_KEY not configured)
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


@api.get("/hr/submissions/{submission_id}")
async def get_submission(submission_id: str, _user=Depends(require_hr)):
    doc = await db.submissions.find_one({"_id": ObjectId(submission_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Submission not found")
    return oid_to_str(doc)


@api.get("/hr/stats")
async def hr_stats(_user=Depends(require_hr)):
    total_jobs = await db.jobs.count_documents({"status": "open"})
    total_apps = await db.applications.count_documents({})
    total_subs = await db.submissions.count_documents({})
    high_risk = await db.submissions.count_documents({"ai_risk_avg": {"$gte": 60}})
    return {
        "open_jobs": total_jobs,
        "total_applications": total_apps,
        "submissions": total_subs,
        "high_ai_risk": high_risk,
    }


# ---------------- Exam (Candidate) ----------------
@api.get("/exam/{token}")
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
    # Sanitize: strip MCQ correct_index for candidate
    mcqs_public = [
        {"id": m["id"], "question": m["question"], "options": m["options"]}
        for m in a.get("mcqs", [])
    ]
    return {
        "invite_token": token,
        "candidate_name": inv["candidate_name"],
        "job_title": job["title"],
        "duration_minutes": a.get("duration_minutes", 60),
        "mcqs": mcqs_public,
        "short_answers": a.get("short_answers", []),
        "coding": a.get("coding"),
        "status": inv["status"],
    }


@api.post("/exam/start")
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


@api.post("/exam/submit")
async def submit_exam(body: SubmitAnswersIn):
    inv = await db.invites.find_one({"token": body.invite_token})
    if not inv:
        raise HTTPException(status_code=404, detail="Invalid invite")
    if inv["status"] == "submitted":
        raise HTTPException(status_code=410, detail="Already submitted")
    job = await db.jobs.find_one({"_id": ObjectId(inv["job_id"])})
    a = job.get("assignment", {})

    # Score MCQs (weighted)
    mcq_correct = 0  # raw count for backwards compat
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

    # Auto-reject decision
    threshold = int(job.get("ai_reject_threshold", 70))
    auto_flagged = ai_risk_max >= threshold

    # Auto-shortlist decision (only if not auto-flagged)
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
    sub_doc = {
        "invite_token": body.invite_token,
        "application_id": inv["application_id"],
        "job_id": inv["job_id"],
        "candidate_name": inv["candidate_name"],
        "candidate_email": inv["candidate_email"],
        "mcq_answers": body.mcq_answers,
        "short_answers": body.short_answers,
        "coding_answer": body.coding_answer,
        "ai_results": ai_results,
        "ai_risk_avg": ai_risk_avg,
        "ai_risk_max": ai_risk_max,
        "ai_reject_threshold": threshold,
        "auto_flagged": auto_flagged,
        "auto_shortlisted": auto_shortlist,
        "hr_override": False,
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
    update_fields = {"status": app_status}
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
    }


@api.post("/exam/violation")
async def log_violation(body: dict):
    """Optional real-time violation logging (not required, submit collects them)."""
    return {"ok": True}


# ---------------- Resume upload ----------------
MAX_RESUME_BYTES = 5 * 1024 * 1024  # 5MB


@api.post("/resumes/upload")
async def resume_upload(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename")
    data = await file.read()
    if len(data) > MAX_RESUME_BYTES:
        raise HTTPException(status_code=413, detail="File too large (max 5MB)")
    # Extract candidate email if uploaded via candidate portal (best-effort)
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


@api.get("/resumes/{file_id}")
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


# ---------------- Assignment editor ----------------
class MCQItem(BaseModel):
    id: str
    question: str
    options: List[str]
    correct_index: int
    weight: int = 1


class ShortAnswerItem(BaseModel):
    id: str
    question: str
    min_words: int = 40
    weight: int = 1


class CodingItem(BaseModel):
    id: str = "code1"
    prompt: str
    starter_code: str = ""
    weight: int = 1


class AssignmentIn(BaseModel):
    duration_minutes: int = 60
    mcqs: List[MCQItem] = []
    short_answers: List[ShortAnswerItem] = []
    coding: Optional[CodingItem] = None


@api.get("/hr/jobs/{job_id}/assignment")
async def get_assignment(job_id: str, _user=Depends(require_hr)):
    doc = await db.jobs.find_one({"_id": ObjectId(job_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Job not found")
    return doc.get("assignment") or default_assignment("engineering")


@api.put("/hr/jobs/{job_id}/assignment")
async def update_assignment(job_id: str, body: AssignmentIn, _user=Depends(require_hr)):
    # Validate: each MCQ correct_index in range
    for m in body.mcqs:
        if not (0 <= m.correct_index < len(m.options)):
            raise HTTPException(status_code=400, detail=f"MCQ '{m.id}' correct_index out of range")
    if body.duration_minutes < 5 or body.duration_minutes > 240:
        raise HTTPException(status_code=400, detail="Duration must be between 5 and 240 minutes")
    payload = body.model_dump()
    await db.jobs.update_one({"_id": ObjectId(job_id)}, {"$set": {"assignment": payload}})
    return {"ok": True, "assignment": payload}


# ---------------- Master admin: HR user management ----------------
class HRUserIn(BaseModel):
    name: str
    email: EmailStr
    password: str


@api.get("/master/users")
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


@api.post("/master/users")
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


@api.post("/master/users/{user_id}/toggle")
async def toggle_hr_user(user_id: str, _user=Depends(require_master)):
    doc = await db.users.find_one({"_id": ObjectId(user_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="User not found")
    if doc.get("role") == "master_admin":
        raise HTTPException(status_code=400, detail="Cannot deactivate master admin")
    new_state = not doc.get("is_active", True)
    await db.users.update_one({"_id": ObjectId(user_id)}, {"$set": {"is_active": new_state}})
    return {"id": user_id, "is_active": new_state}


# ---------------- Question bank ----------------
@api.get("/hr/question-bank")
async def list_modules(_user=Depends(require_hr)):
    return [
        {"id": m["id"], "title": m["title"], "category": m["category"],
         "description": m["description"], "count": m["count"]}
        for m in all_modules()
    ]


@api.get("/hr/question-bank/{module_id}")
async def get_module_detail(module_id: str, _user=Depends(require_hr)):
    m = get_module(module_id)
    if not m:
        raise HTTPException(status_code=404, detail="Module not found")
    return {
        **m,
        "questions": get_questions_by_ids(m["question_ids"]),
    }


class ImportIn(BaseModel):
    question_ids: List[str]


@api.post("/hr/jobs/{job_id}/assignment/import")
async def import_questions(job_id: str, body: ImportIn, _user=Depends(require_hr)):
    job = await db.jobs.find_one({"_id": ObjectId(job_id)})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    a = job.get("assignment") or default_assignment("engineering")
    a.setdefault("mcqs", [])
    a.setdefault("short_answers", [])
    if not a.get("coding"):
        a["coding"] = None

    existing_ids = (
        {m["id"] for m in a["mcqs"]}
        | {s["id"] for s in a["short_answers"]}
        | ({a["coding"]["id"]} if a.get("coding") else set())
    )
    added_mcq = added_sa = added_code = 0
    for q in get_questions_by_ids(body.question_ids):
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
            # only 1 coding task at a time — replace if empty else skip
            if a.get("coding") is None:
                a["coding"] = {
                    "id": q["id"], "prompt": q["prompt"],
                    "starter_code": q.get("starter_code", ""),
                    "weight": q.get("weight", 1),
                }
                added_code += 1
    await db.jobs.update_one({"_id": ObjectId(job_id)}, {"$set": {"assignment": a}})
    return {"ok": True, "added_mcq": added_mcq, "added_sa": added_sa, "added_code": added_code}


# ---------------- HR override & schedule ----------------
@api.post("/hr/submissions/{submission_id}/override")
async def override_submission(submission_id: str, body: dict, _user=Depends(require_hr)):
    """HR can override an auto-reject decision (or reset it)."""
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


class ScheduleIn(BaseModel):
    application_id: str


@api.post("/hr/schedule-interview")
async def send_schedule_link(body: ScheduleIn, _user=Depends(require_hr)):
    """Mark application ready for interview; candidate's dashboard shows the calendly link."""
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


# ---------------- Register router ----------------
app.include_router(api)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
