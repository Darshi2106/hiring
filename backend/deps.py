"""Shared dependencies, models, and helpers for all routers."""
import os
from typing import List, Optional

from fastapi import Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, EmailStr, Field

from auth import get_current_user

# ---------------- DB (singleton) ----------------
mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]


# ---------------- Helpers ----------------
def oid_to_str(doc):
    if not doc:
        return doc
    doc["id"] = str(doc["_id"])
    doc.pop("_id", None)
    doc.pop("password_hash", None)
    return doc


def compute_trust_score(mcq_pct: int, coding_results: dict, ai_risk_max: int, violations: list) -> dict:
    """0-100 composite trust score. Higher = stronger, more trustworthy candidate.
    Weights adapt: if no coding tasks auto-graded, redistribute weight to MCQ + AI safety.
    """
    auto_tasks = [r for r in coding_results.values() if r.get("needs_manual_review") is False]
    coding_pct = None
    if auto_tasks:
        passed = sum(1 for r in auto_tasks if r.get("passed") is True)
        coding_pct = int(round(100 * passed / len(auto_tasks)))

    ai_safety = max(0, 100 - int(ai_risk_max or 0))
    proctoring = max(0, 100 - min(100, len(violations or []) * 20))
    mcq = max(0, min(100, int(mcq_pct or 0)))

    if coding_pct is not None:
        total = mcq * 0.30 + coding_pct * 0.30 + ai_safety * 0.25 + proctoring * 0.15
        breakdown = {"mcq": mcq, "coding": coding_pct, "ai_safety": ai_safety, "proctoring": proctoring}
    else:
        total = mcq * 0.45 + ai_safety * 0.30 + proctoring * 0.25
        breakdown = {"mcq": mcq, "coding": None, "ai_safety": ai_safety, "proctoring": proctoring}
    return {"score": int(round(total)), "breakdown": breakdown}


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
    ai_reject_threshold: int = 70
    calendly_url: Optional[str] = ""
    auto_shortlist_enabled: bool = True
    auto_shortlist_mcq_min: int = 80
    auto_shortlist_ai_max: int = 10
    auto_shortlist_max_violations: int = 0


class ApplyIn(BaseModel):
    job_id: str
    name: str
    email: EmailStr
    phone: Optional[str] = ""
    resume_url: Optional[str] = ""
    cover_letter: Optional[str] = ""
    source: Optional[str] = "careers_direct"


class InviteIn(BaseModel):
    application_id: str


class SubmitAnswersIn(BaseModel):
    invite_token: str
    mcq_answers: dict
    short_answers: dict
    coding_answers: dict = {}
    coding_answer: Optional[str] = ""
    violations: List[dict] = []
    webcam_snapshots: List[str] = []
    time_taken_seconds: int = 0


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
    language: str = "python"
    test_code: str = ""


class AssignmentIn(BaseModel):
    duration_minutes: int = 60
    mcqs: List[MCQItem] = []
    short_answers: List[ShortAnswerItem] = []
    coding_tasks: List[CodingItem] = []


class HRUserIn(BaseModel):
    name: str
    email: EmailStr
    password: str


class ModuleIn(BaseModel):
    id: str = Field(..., pattern=r"^[a-z0-9_]+$")
    title: str
    category: str
    description: str = ""
    questions: List[dict] = []


class ImportIn(BaseModel):
    question_ids: List[str]


class ScheduleIn(BaseModel):
    application_id: str
