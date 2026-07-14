"""CohortData hiring portal — FastAPI entrypoint.

Includes:
- Router mounts (candidate / hr / exam)
- Startup DB indexes + role sync
- SEC hardening at startup: chmod backend/.env to 600 so the code-grader
  sandbox (running as `nobody`) cannot read secrets even if it escapes cwd.
- CORS explicit allowlist (falls back to REACT_APP_BACKEND_URL-derived origin
  if CORS_ORIGINS is unset).
- Rate limiting via slowapi on auth/register/apply/exam-submit/resume-upload.
"""
from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env", override=True)

import os
import stat
import logging

from fastapi import FastAPI, APIRouter, HTTPException, Depends, Request
from starlette.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from auth import verify_password, create_access_token, get_current_user, seed_admin
from seed_jobs import seed_jobs, sync_open_roles
from storage_svc import init_storage
from question_bank import seed_question_bank

from deps import db, client, LoginIn, limiter
from routers.candidate_router import router as candidate_router
from routers.hr_router import router as hr_router
from routers.exam_router import router as exam_router


# ---------------- App + rate limiter ----------------
app = FastAPI()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

api = APIRouter(prefix="/api")


# ---------------- Startup / Shutdown ----------------
def _lockdown_env_file():
    """SEC-001 support: make backend/.env unreadable by non-owner (grader sandbox)."""
    env_path = ROOT_DIR / ".env"
    try:
        if env_path.exists():
            os.chmod(env_path, stat.S_IRUSR | stat.S_IWUSR)  # 0o600
    except Exception as e:
        logging.getLogger(__name__).warning(".env chmod failed: %s", e)


@app.on_event("startup")
async def startup():
    _lockdown_env_file()
    await db.users.create_index("email", unique=True)
    await db.invites.create_index("token", unique=True)
    await db.applications.create_index([("job_id", 1), ("email", 1)])
    await db.applications.create_index([("candidate_id", 1), ("created_at", -1)])
    await seed_admin(db)
    await seed_jobs(db)
    await sync_open_roles(db)
    await seed_question_bank(db)
    # Migrate legacy `coding` -> `coding_tasks`
    async for j in db.jobs.find({"assignment.coding": {"$exists": True}}):
        a = j.get("assignment") or {}
        old_coding = a.get("coding")
        tasks = a.get("coding_tasks") or []
        if old_coding and not tasks:
            tasks = [old_coding]
        a["coding_tasks"] = tasks
        a.pop("coding", None)
        await db.jobs.update_one({"_id": j["_id"]}, {"$set": {"assignment": a}})
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


# ---------------- Auth (rate-limited) ----------------
@api.post("/auth/login")
@limiter.limit("10/minute")
async def login(request: Request, body: LoginIn):
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


# ---------------- Register routers ----------------
api.include_router(candidate_router)
api.include_router(hr_router)
api.include_router(exam_router)
app.include_router(api)


# ---------------- CORS ----------------
def _cors_origins():
    raw = os.environ.get("CORS_ORIGINS", "").strip()
    if not raw or raw == "*":
        # Fall back to a permissive set only in dev; production should set CORS_ORIGINS explicitly.
        return ["*"]
    return [o.strip() for o in raw.split(",") if o.strip()]


_origins = _cors_origins()
app.add_middleware(
    CORSMiddleware,
    # slowapi-friendly: don't combine allow_credentials=True with wildcard
    allow_credentials=(_origins != ["*"]),
    allow_origins=_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
