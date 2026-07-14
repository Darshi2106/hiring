"""Seed & sync live open roles from https://www.cohortdata.com/careers.

The 7 SEED_JOBS below mirror the live careers page (verified against a rendered
DOM screenshot from the site on 2026-02-14). `sync_open_roles` runs on every
startup: it keeps only these 7 titles as `status="open"` and closes any
non-canonical jobs (legacy titles, test-created jobs, etc.). Applications on
closed jobs are preserved for auditability.

Each SEED_JOB also declares `assessment_modules` — a list of question-bank
module ids used to auto-populate the assessment for that role on first insert.
"""
from datetime import datetime, timezone


# ---- Canonical live openings from cohortdata.com/careers ----
SEED_JOBS = [
    {
        "title": "Senior Product Manager (AI/ML, Intelligent Systems & Enterprise Innovation)",
        "department": "Business & Sales",
        "location": "Hyderabad",
        "type": "Full-Time",
        "description": "Lead product strategy for AI-powered data intelligence and annotation platforms. Drive roadmap for enterprise customers in autonomy, robotics, and conversational AI.",
        "requirements": [
            "5+ years product management",
            "Experience with AI/ML products",
            "Strong analytical skills",
            "Enterprise SaaS background",
        ],
        "assessment_modules": ["mcq_ml", "mcq_aptitude_quant", "mcq_aptitude_logical", "sa_behavioral", "sa_tech"],
    },
    {
        "title": "Sales Manager (AI/ML, ADAS, Data Services)",
        "department": "Business & Sales",
        "location": "Hyderabad",
        "type": "Full-Time",
        "description": "Own new-logo acquisition for AI data services across ADAS, robotics, and enterprise AI verticals.",
        "requirements": [
            "4+ years B2B sales",
            "AI/data services domain",
            "Enterprise deal cycles",
            "Excellent communication",
        ],
        "assessment_modules": ["mcq_sales", "mcq_aptitude_quant", "mcq_aptitude_verbal", "sa_sales", "sa_behavioral"],
    },
    {
        "title": "Director Global Sales (AI/ML, ADAS, Multimodal Data)",
        "department": "Business & Sales",
        "location": "Hyderabad",
        "type": "Full-Time",
        "description": "Build and lead the global sales organization for multimodal AI data infrastructure.",
        "requirements": [
            "10+ years sales leadership",
            "Global enterprise sales",
            "AI/ADAS market expertise",
        ],
        "assessment_modules": ["mcq_sales", "mcq_aptitude_logical", "mcq_aptitude_verbal", "sa_sales", "sa_behavioral"],
    },
    {
        "title": "Visualization Engineer",
        "department": "Tech & Eng",
        "location": "Hyderabad",
        "type": "Full-Time",
        "description": "Build interactive dashboards and 3D visualization tools for multimodal datasets.",
        "requirements": ["React / D3 / Three.js", "Data visualization", "WebGL a plus"],
        "assessment_modules": [
            "mcq_frontend", "mcq_dsa", "sa_tech", "sa_behavioral",
            "code_react", "code_javascript_async",
        ],
    },
    {
        "title": "Senior ML / CV Engineer",
        "department": "Tech & Eng",
        "location": "Hyderabad",
        "type": "Full-Time",
        "description": "Develop computer vision models for annotation quality and multimodal understanding.",
        "requirements": ["PyTorch / TensorFlow", "Computer vision", "Production ML deployment"],
        "assessment_modules": [
            "mcq_ml", "mcq_cv", "mcq_dsa", "sa_tech", "sa_behavioral",
            "code_python_intermediate", "code_ml_pipeline", "code_cv_opencv",
        ],
    },
    {
        "title": "Platform / Operations Engineer",
        "department": "Operations",
        "location": "Hyderabad",
        "type": "Full-Time",
        "description": "Operate the annotation platform infrastructure at scale.",
        "requirements": ["Kubernetes", "AWS/GCP", "CI/CD", "Observability tools"],
        "assessment_modules": [
            "mcq_backend", "mcq_operations", "mcq_sql", "sa_tech", "sa_behavioral",
            "code_python_intermediate", "code_fastapi", "code_debug_fix",
        ],
    },
    {
        "title": "Lead Full-Stack Engineer",
        "department": "Tech & Eng",
        "location": "Hyderabad",
        "type": "Full-Time",
        "description": "Lead full-stack development for annotation and data intelligence platforms.",
        "requirements": ["React + Node/Python", "System design", "5+ years experience", "Team leadership"],
        "assessment_modules": [
            "mcq_fullstack", "mcq_frontend", "mcq_backend", "mcq_dsa", "sa_tech", "sa_behavioral",
            "code_python_intermediate", "code_react", "code_dsa",
        ],
    },
]


def default_assignment(job_type: str = "engineering"):
    """Return a small default assignment used when we can't populate from the question bank."""
    is_engineering = job_type == "engineering"
    return {
        "duration_minutes": 60,
        "mcqs": [
            {"id": "mcq1", "question": "Which principle best describes 'DRY' in software engineering?",
             "options": ["Design for Reuse Yearly", "Don't Repeat Yourself", "Debug, Refactor, Yield", "Data Reduction Yardstick"],
             "correct_index": 1},
            {"id": "mcq2", "question": "In data annotation, inter-annotator agreement is primarily used to measure:",
             "options": ["Model accuracy", "Annotation consistency", "Dataset size", "Annotator speed"],
             "correct_index": 1},
            {"id": "mcq3", "question": "Which of these is NOT a supervised ML task?",
             "options": ["Classification", "Regression", "K-means clustering", "Object detection"],
             "correct_index": 2},
        ],
        "short_answers": [
            {"id": "sa1", "question": "Describe a project you delivered under a tight deadline — your role and tradeoffs.", "min_words": 40},
            {"id": "sa2", "question": "How would you approach quality control for a multimodal annotation pipeline handling 100k+ items per week?", "min_words": 40},
        ],
        "coding_tasks": [
            {"id": "code1",
             "prompt": "Write a function `count_duplicates(arr)` that returns the count of duplicate values in an integer array.",
             "starter_code": "def count_duplicates(arr):\n    # your code here\n    pass\n",
             "language": "python", "weight": 3}
        ] if is_engineering else [],
    }


def _build_assignment_from_modules(module_ids):
    """Assemble an assignment dict from question-bank module ids.

    Caps per-role totals so each role's assessment fits a 60-90 min slot:
      - up to 3 MCQs sampled per module, capped at 15 total
      - up to 2 SAs sampled per module, capped at 4 total
      - up to 1 coding task sampled per module, capped at 3 total
    HR can further customize via the /hr/jobs/{id}/assignment editor.

    Returns None if question_bank isn't importable.
    """
    try:
        from question_bank import get_module, get_questions_by_ids
    except Exception:
        return None
    MCQ_PER_MODULE, MCQ_TOTAL = 3, 15
    SA_PER_MODULE, SA_TOTAL = 2, 4
    CODE_PER_MODULE, CODE_TOTAL = 1, 3

    mcqs, short_answers, coding_tasks = [], [], []
    for mid in module_ids:
        m = get_module(mid)
        if not m:
            continue
        picked_mcq = picked_sa = picked_code = 0
        for q in get_questions_by_ids(m.get("question_ids", [])):
            qtype = q.get("type")
            if qtype == "mcq" and picked_mcq < MCQ_PER_MODULE and len(mcqs) < MCQ_TOTAL:
                mcqs.append({
                    "id": q["id"], "question": q["question"],
                    "options": q["options"], "correct_index": q["correct_index"],
                    "weight": q.get("weight", 1),
                })
                picked_mcq += 1
            elif qtype == "sa" and picked_sa < SA_PER_MODULE and len(short_answers) < SA_TOTAL:
                short_answers.append({
                    "id": q["id"], "question": q["question"],
                    "min_words": q.get("min_words", 40), "weight": q.get("weight", 1),
                })
                picked_sa += 1
            elif qtype == "code" and picked_code < CODE_PER_MODULE and len(coding_tasks) < CODE_TOTAL:
                coding_tasks.append({
                    "id": q["id"], "prompt": q["prompt"],
                    "starter_code": q.get("starter_code", ""),
                    "weight": q.get("weight", 1),
                    "language": q.get("language", "python"),
                    "test_code": q.get("test_code", ""),
                })
                picked_code += 1
    return {
        "duration_minutes": 90 if coding_tasks else 60,
        "mcqs": mcqs, "short_answers": short_answers, "coding_tasks": coding_tasks,
    }


async def seed_jobs(db):
    """Insert seed jobs on very first startup only (when DB is empty)."""
    count = await db.jobs.count_documents({})
    if count > 0:
        return
    now = datetime.now(timezone.utc).isoformat()
    docs = []
    for j in SEED_JOBS:
        modules = j.get("assessment_modules") or []
        assignment = _build_assignment_from_modules(modules) if modules else None
        if not assignment:
            is_eng = j["department"] == "Tech & Eng" or "Engineer" in j["title"]
            assignment = default_assignment("engineering" if is_eng else "non-engineering")
        job_doc = {k: v for k, v in j.items() if k != "assessment_modules"}
        job_doc.update({"assignment": assignment, "status": "open", "created_at": now})
        docs.append(job_doc)
    await db.jobs.insert_many(docs)


async def sync_open_roles(db):
    """Ensure DB reflects the live cohortdata.com/careers open roles.

    - Close every job whose title is NOT one of the canonical live titles
    - Ensure each canonical role exists with status='open'.
      * If the role already has an assignment (with mcqs OR short_answers OR coding_tasks),
        leave the assignment untouched — HR customization is preserved.
      * If the role's assignment is missing/empty, populate from assessment_modules.
    """
    now = datetime.now(timezone.utc).isoformat()
    canonical_titles = [j["title"] for j in SEED_JOBS]

    # 1) Close everything that isn't a canonical live role
    await db.jobs.update_many(
        {"title": {"$nin": canonical_titles}, "status": {"$ne": "closed"}},
        {"$set": {"status": "closed", "closed_at": now}},
    )

    # 2) Upsert canonical live roles + apply module-based assessments (once per role)
    for j in SEED_JOBS:
        modules = j.get("assessment_modules") or []
        base = {k: v for k, v in j.items() if k != "assessment_modules"}
        existing = await db.jobs.find_one({"title": j["title"]})
        if existing:
            update = {
                "department": base["department"],
                "location": base["location"],
                "type": base["type"],
                "description": base["description"],
                "requirements": base["requirements"],
                "status": "open",
            }
            # Populate the module-based assessment exactly once per role (idempotent
            # via `assessment_modules_applied` flag). If HR then customizes the
            # assignment via the HR editor, subsequent restarts won't clobber it.
            if modules and not existing.get("assessment_modules_applied"):
                built = _build_assignment_from_modules(modules)
                if built and (built["mcqs"] or built["short_answers"] or built["coding_tasks"]):
                    update["assignment"] = built
                    update["assessment_modules_applied"] = list(modules)
            await db.jobs.update_one({"_id": existing["_id"]}, {"$set": update})
        else:
            assignment = _build_assignment_from_modules(modules) if modules else None
            if not assignment:
                is_eng = base["department"] == "Tech & Eng" or "Engineer" in base["title"]
                assignment = default_assignment("engineering" if is_eng else "non-engineering")
            await db.jobs.insert_one({
                **base,
                "assignment": assignment,
                "assessment_modules_applied": list(modules) if modules else [],
                "status": "open",
                "created_at": now,
            })
