from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

import os
import secrets
import logging
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import FastAPI, APIRouter, HTTPException, Depends, Request
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


# ---------------- Startup ----------------
@app.on_event("startup")
async def startup():
    await db.users.create_index("email", unique=True)
    await db.invites.create_index("token", unique=True)
    await db.applications.create_index([("job_id", 1), ("email", 1)])
    await seed_admin(db)
    await seed_jobs(db)


@app.on_event("shutdown")
async def shutdown():
    client.close()


# ---------------- Auth ----------------
@api.post("/auth/login")
async def login(body: LoginIn):
    user = await db.users.find_one({"email": body.email.lower()})
    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
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
    existing = await db.users.find_one({"email": email})
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")
    if len(body.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
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
async def create_job(body: JobIn, _user=Depends(get_current_user)):
    doc = body.model_dump()
    if not doc.get("assignment"):
        is_eng = doc["department"] == "Tech & Eng" or "Engineer" in doc["title"]
        doc["assignment"] = default_assignment("engineering" if is_eng else "non-engineering")
    doc["created_at"] = datetime.now(timezone.utc).isoformat()
    res = await db.jobs.insert_one(doc)
    return {"id": str(res.inserted_id), **{k: v for k, v in doc.items() if k != "_id"}}


@api.put("/hr/jobs/{job_id}")
async def update_job(job_id: str, body: JobIn, _user=Depends(get_current_user)):
    updates = body.model_dump()
    await db.jobs.update_one({"_id": ObjectId(job_id)}, {"$set": updates})
    return {"ok": True}


@api.delete("/hr/jobs/{job_id}")
async def delete_job(job_id: str, _user=Depends(get_current_user)):
    await db.jobs.delete_one({"_id": ObjectId(job_id)})
    return {"ok": True}


@api.get("/hr/jobs/{job_id}")
async def hr_get_job(job_id: str, _user=Depends(get_current_user)):
    doc = await db.jobs.find_one({"_id": ObjectId(job_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Job not found")
    return oid_to_str(doc)


# ---------------- HR: Applications ----------------
@api.get("/hr/applications")
async def list_applications(job_id: Optional[str] = None, _user=Depends(get_current_user)):
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
async def create_invite(body: InviteIn, _user=Depends(get_current_user)):
    app_doc = await db.applications.find_one({"_id": ObjectId(body.application_id)})
    if not app_doc:
        raise HTTPException(status_code=404, detail="Application not found")
    # If already invited, return existing
    existing = await db.invites.find_one({"application_id": body.application_id})
    if existing:
        return {"token": existing["token"], "existing": True}
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
    return {"token": token, "existing": False}


@api.get("/hr/submissions/{submission_id}")
async def get_submission(submission_id: str, _user=Depends(get_current_user)):
    doc = await db.submissions.find_one({"_id": ObjectId(submission_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Submission not found")
    return oid_to_str(doc)


@api.get("/hr/stats")
async def hr_stats(_user=Depends(get_current_user)):
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

    # Score MCQs
    mcq_correct = 0
    mcq_total = len(a.get("mcqs", []))
    for m in a.get("mcqs", []):
        if body.mcq_answers.get(m["id"]) == m["correct_index"]:
            mcq_correct += 1

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
        "mcq_score": mcq_correct,
        "mcq_total": mcq_total,
        "violations": body.violations,
        "webcam_snapshots": body.webcam_snapshots[:20],  # cap
        "time_taken_seconds": body.time_taken_seconds,
        "submitted_at": now,
    }
    res = await db.submissions.insert_one(sub_doc)
    await db.invites.update_one(
        {"token": body.invite_token},
        {"$set": {"status": "submitted", "submitted_at": now}},
    )
    await db.applications.update_one(
        {"_id": ObjectId(inv["application_id"])},
        {"$set": {"status": "assignment_submitted"}},
    )
    return {
        "submission_id": str(res.inserted_id),
        "mcq_score": mcq_correct,
        "mcq_total": mcq_total,
        "ai_risk_avg": ai_risk_avg,
    }


@api.post("/exam/violation")
async def log_violation(body: dict):
    """Optional real-time violation logging (not required, submit collects them)."""
    return {"ok": True}


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
