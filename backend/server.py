"""CohortData hiring portal — FastAPI entrypoint.

Startup, /auth endpoints, and mounts the three routers:
  - candidate_router : public + candidate self-serve
  - hr_router        : HR + Master admin
  - exam_router      : proctored exam & resume storage
"""
from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env", override=True)

import os
import logging

from fastapi import FastAPI, APIRouter, HTTPException, Depends
from starlette.middleware.cors import CORSMiddleware

from auth import verify_password, create_access_token, get_current_user, seed_admin
from seed_jobs import seed_jobs, sync_open_roles
from storage_svc import init_storage
from question_bank import seed_question_bank

from deps import db, client, LoginIn
from routers.candidate_router import router as candidate_router
from routers.hr_router import router as hr_router
from routers.exam_router import router as exam_router


app = FastAPI()
api = APIRouter(prefix="/api")


# ---------------- Startup / Shutdown ----------------
@app.on_event("startup")
async def startup():
    await db.users.create_index("email", unique=True)
    await db.invites.create_index("token", unique=True)
    await db.applications.create_index([("job_id", 1), ("email", 1)])
    await db.applications.create_index([("candidate_id", 1), ("created_at", -1)])
    await seed_admin(db)
    await seed_jobs(db)
    await sync_open_roles(db)
    await seed_question_bank(db)
    # Migrate legacy `coding` object -> `coding_tasks` array
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


# ---------------- Auth (HR + Master shared) ----------------
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


# ---------------- Register routers ----------------
api.include_router(candidate_router)
api.include_router(hr_router)
api.include_router(exam_router)
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
