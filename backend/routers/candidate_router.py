"""Public + candidate-facing endpoints: candidate auth, public job listings, and applications."""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from bson import ObjectId

from auth import hash_password, verify_password, create_access_token, get_current_user, decode_token
from deps import db, oid_to_str, LoginIn, CandidateRegisterIn, ApplyIn, limiter

router = APIRouter()


# ---------------- Candidate Auth ----------------
@router.post("/candidate/register")
@limiter.limit("5/minute")
async def candidate_register(request: Request, body: CandidateRegisterIn):
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


@router.post("/candidate/login")
@limiter.limit("10/minute")
async def candidate_login(request: Request, body: LoginIn):
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


@router.get("/candidate/me")
async def candidate_me(current=Depends(get_current_user)):
    if current.get("role") != "candidate":
        raise HTTPException(status_code=403, detail="Not a candidate")
    return current


@router.get("/candidate/applications")
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


# ---------------- Public jobs ----------------
def _sanitize_public_job(doc):
    """SEC-002: strip MCQ correct answers, hidden test_code, and internal thresholds
    from any job document returned to a public/unauthenticated caller."""
    if doc.get("assignment"):
        a = doc["assignment"]
        tasks = a.get("coding_tasks") or ([a["coding"]] if a.get("coding") else [])
        doc["assignment_summary"] = {
            "duration_minutes": a.get("duration_minutes", 60),
            "mcq_count": len(a.get("mcqs", [])),
            "sa_count": len(a.get("short_answers", [])),
            "coding_count": len(tasks),
            "has_coding": len(tasks) > 0,
        }
        doc.pop("assignment", None)
    # Also strip internal HR-only fields
    for k in (
        "ai_reject_threshold",
        "auto_shortlist_enabled",
        "auto_shortlist_mcq_min",
        "auto_shortlist_ai_max",
        "auto_shortlist_max_violations",
    ):
        doc.pop(k, None)
    return doc


@router.get("/jobs")
async def list_jobs(status: Optional[str] = "open"):
    q = {"status": status} if status else {}
    docs = await db.jobs.find(q).sort("created_at", -1).to_list(500)
    return [_sanitize_public_job(oid_to_str(d)) for d in docs]


@router.get("/jobs/{job_id}")
async def get_job(job_id: str):
    try:
        doc = await db.jobs.find_one({"_id": ObjectId(job_id)})
    except Exception:
        raise HTTPException(status_code=404, detail="Job not found")
    if not doc:
        raise HTTPException(status_code=404, detail="Job not found")
    return _sanitize_public_job(oid_to_str(doc))


@router.post("/applications")
@limiter.limit("5/minute")
async def apply(request: Request, body: ApplyIn):
    try:
        job = await db.jobs.find_one({"_id": ObjectId(body.job_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid job id")
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    candidate_id = None
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        try:
            payload = decode_token(auth_header[7:])
            user = await db.users.find_one({"_id": ObjectId(payload["sub"])})
            if user and user.get("role") == "candidate":
                candidate_id = str(user["_id"])
        except Exception:
            candidate_id = None

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
        "source": (body.source or "careers_direct").lower()[:40],
        "status": "applied",
        "created_at": now,
    }
    res = await db.applications.insert_one(doc)
    doc["id"] = str(res.inserted_id)
    doc.pop("_id", None)
    return doc
