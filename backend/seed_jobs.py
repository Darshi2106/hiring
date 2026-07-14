"""Seed & sync live open roles from https://www.cohortdata.com/careers.

The `SEED_JOBS` list mirrors the CohortData careers page. `sync_open_roles` runs
on every startup: it keeps only these titles marked `status="open"` and closes
any legacy jobs whose title is no longer live. Existing applications and
submissions are preserved.
"""
from datetime import datetime, timezone


# ---- Canonical live openings from cohortdata.com/careers ----
SEED_JOBS = [
    {
        "title": "Quality Analyst",
        "department": "Operations",
        "location": "Hyderabad / Ahmedabad",
        "type": "Full-Time",
        "description": "Own annotation quality across multimodal datasets. Design QA rubrics, run second-pass audits, and coach annotators. 1+ year of annotation/QA experience required.",
        "requirements": [
            "1+ years annotation or QA experience",
            "Sharp eye for edge cases and dataset drift",
            "Familiarity with bounding boxes, polygons, 3D cuboids or LiDAR annotation is a plus",
            "Excellent written communication for issue reporting",
        ],
    },
    {
        "title": "Annotator / Associate",
        "department": "Operations",
        "location": "Hyderabad / Ahmedabad",
        "type": "Full-Time",
        "description": "Label multimodal datasets (image, video, 3D, audio, text) that power ADAS, robotics, and conversational AI systems. Immediate joiners preferred.",
        "requirements": [
            "Track record in data labeling / annotation",
            "Attention to detail and consistency at scale",
            "Comfort with structured annotation tools (CVAT, Label Studio or similar)",
            "Willingness to work in shifts if the project requires it",
        ],
    },
    {
        "title": "Project Coordinator",
        "department": "Operations",
        "location": "Hyderabad / Ahmedabad",
        "type": "Full-Time",
        "description": "Coordinate annotation projects end-to-end: planning, resource allocation, quality checkpoints, and client delivery cadences.",
        "requirements": [
            "Project planning & resource coordination",
            "Quality control oversight across teams",
            "Client-facing communication",
            "Comfort with spreadsheets, JIRA, Slack",
        ],
    },
    {
        "title": "Project Associate",
        "department": "Operations",
        "location": "Madhapur, Hyderabad",
        "type": "Full-Time",
        "description": "Support project delivery on US/UK-facing engagements. Voice-process experience is a plus. Advanced English required.",
        "requirements": [
            "Advanced spoken and written English",
            "Basic AI/ML understanding",
            "US/UK voice-process experience is a plus",
            "Availability for evening/night shifts on rotational basis",
        ],
    },
    {
        "title": "Global Sales Director",
        "department": "Business & Sales",
        "location": "Hyderabad",
        "type": "Full-Time",
        "description": "Own new-logo acquisition for AI data services across ADAS, robotics, and enterprise AI. Ideal candidates have closed $100K–$1M+ deals in AI/ML, SaaS, or ADAS.",
        "requirements": [
            "10+ years enterprise sales, ideally in AI/ML, SaaS, or ADAS",
            "Closed deals in the $100K–$1M+ range",
            "Global buying-committee experience",
            "Comfort building pipeline from scratch",
        ],
    },
]


# Titles that used to be seeded but are no longer live — we close them on startup.
LEGACY_TITLES_TO_CLOSE = [
    "Senior Product Manager (AI/ML, Intelligent Systems & Enterprise Innovation)",
    "Sales Manager (AI/ML, ADAS, Data Services)",
    "Director Global Sales (AI/ML, ADAS, Multimodal Data)",
    "Visualization Engineer",
    "Senior ML / CV Engineer",
    "Platform / Operations Engineer",
    "Lead Full-Stack Engineer",
]


def default_assignment(job_type: str = "engineering"):
    """Return default assignment template for a job."""
    is_engineering = job_type == "engineering"
    return {
        "duration_minutes": 60,
        "mcqs": [
            {
                "id": "mcq1",
                "question": "Which principle best describes 'DRY' in software engineering?",
                "options": [
                    "Design for Reuse Yearly",
                    "Don't Repeat Yourself",
                    "Debug, Refactor, Yield",
                    "Data Reduction Yardstick",
                ],
                "correct_index": 1,
            },
            {
                "id": "mcq2",
                "question": "In data annotation, inter-annotator agreement is primarily used to measure:",
                "options": [
                    "Model accuracy",
                    "Annotation consistency",
                    "Dataset size",
                    "Annotator speed",
                ],
                "correct_index": 1,
            },
            {
                "id": "mcq3",
                "question": "Which of these is NOT a supervised ML task?",
                "options": ["Classification", "Regression", "K-means clustering", "Object detection"],
                "correct_index": 2,
            },
        ],
        "short_answers": [
            {
                "id": "sa1",
                "question": "In 3-5 sentences, describe a time you delivered a project under a tight deadline. Focus on your specific role and the tradeoffs you made.",
                "min_words": 40,
            },
            {
                "id": "sa2",
                "question": "How would you approach quality control for a multimodal annotation pipeline handling 100k+ items per week?",
                "min_words": 40,
            },
        ],
        "coding_tasks": [
            {
                "id": "code1",
                "prompt": "Write a function `count_duplicates(arr)` that returns the count of duplicate values in an integer array. Provide the solution in any language.",
                "starter_code": "def count_duplicates(arr):\n    # your code here\n    pass\n",
                "language": "python",
                "weight": 3,
            }
        ] if is_engineering else [],
    }


async def seed_jobs(db):
    """Insert seed jobs on very first startup only (when DB is empty)."""
    count = await db.jobs.count_documents({})
    if count > 0:
        return
    now = datetime.now(timezone.utc).isoformat()
    docs = []
    for j in SEED_JOBS:
        is_eng = j["department"] == "Tech & Eng" or "Engineer" in j["title"]
        doc = {
            **j,
            "assignment": default_assignment("engineering" if is_eng else "non-engineering"),
            "status": "open",
            "created_at": now,
        }
        docs.append(doc)
    await db.jobs.insert_many(docs)


async def sync_open_roles(db):
    """Ensure the DB reflects the live cohortdata.com/careers open roles.

    - Close every job whose title is NOT one of the canonical live titles
      (this includes both LEGACY_TITLES_TO_CLOSE and stale test-created jobs)
    - Ensure each canonical role exists with status='open' (insert if missing,
      update department/location/type/description/requirements if present)
    Applications and submissions on closed jobs are preserved.
    """
    now = datetime.now(timezone.utc).isoformat()
    canonical_titles = [j["title"] for j in SEED_JOBS]

    # 1) Close everything that isn't a canonical live role
    await db.jobs.update_many(
        {"title": {"$nin": canonical_titles}, "status": {"$ne": "closed"}},
        {"$set": {"status": "closed", "closed_at": now}},
    )

    # 2) Upsert canonical live roles
    for j in SEED_JOBS:
        existing = await db.jobs.find_one({"title": j["title"]})
        if existing:
            # Refresh light metadata; keep assignment + calendly + thresholds untouched
            await db.jobs.update_one(
                {"_id": existing["_id"]},
                {"$set": {
                    "department": j["department"],
                    "location": j["location"],
                    "type": j["type"],
                    "description": j["description"],
                    "requirements": j["requirements"],
                    "status": "open",
                }},
            )
        else:
            is_eng = j["department"] == "Tech & Eng" or "Engineer" in j["title"]
            await db.jobs.insert_one({
                **j,
                "assignment": default_assignment("engineering" if is_eng else "non-engineering"),
                "status": "open",
                "created_at": now,
            })
