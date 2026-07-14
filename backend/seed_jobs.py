"""Seed initial job openings from cohortdata.com/careers."""
from datetime import datetime, timezone

SEED_JOBS = [
    {
        "title": "Senior Product Manager (AI/ML, Intelligent Systems & Enterprise Innovation)",
        "department": "Business & Sales",
        "location": "Hyderabad",
        "type": "Full-Time",
        "description": "Lead product strategy for AI-powered data intelligence and annotation platforms. Drive roadmap for enterprise customers in autonomy, robotics, and conversational AI.",
        "requirements": ["5+ years product management", "Experience with AI/ML products", "Strong analytical skills", "Enterprise SaaS background"],
    },
    {
        "title": "Sales Manager (AI/ML, ADAS, Data Services)",
        "department": "Business & Sales",
        "location": "Hyderabad",
        "type": "Full-Time",
        "description": "Own new-logo acquisition for AI data services across ADAS, robotics, and enterprise AI verticals.",
        "requirements": ["4+ years B2B sales", "AI/data services domain", "Enterprise deal cycles", "Excellent communication"],
    },
    {
        "title": "Director Global Sales (AI/ML, ADAS, Multimodal Data)",
        "department": "Business & Sales",
        "location": "Hyderabad",
        "type": "Full-Time",
        "description": "Build and lead the global sales organization for multimodal AI data infrastructure.",
        "requirements": ["10+ years sales leadership", "Global enterprise sales", "AI/ADAS market expertise"],
    },
    {
        "title": "Visualization Engineer",
        "department": "Tech & Eng",
        "location": "Hyderabad",
        "type": "Full-Time",
        "description": "Build interactive dashboards and 3D visualization tools for multimodal datasets.",
        "requirements": ["React / D3 / Three.js", "Data visualization", "WebGL a plus"],
    },
    {
        "title": "Senior ML / CV Engineer",
        "department": "Tech & Eng",
        "location": "Hyderabad",
        "type": "Full-Time",
        "description": "Develop computer vision models for annotation quality and multimodal understanding.",
        "requirements": ["PyTorch / TensorFlow", "Computer vision", "Production ML deployment"],
    },
    {
        "title": "Platform / Operations Engineer",
        "department": "Operations",
        "location": "Hyderabad",
        "type": "Full-Time",
        "description": "Operate the annotation platform infrastructure at scale.",
        "requirements": ["Kubernetes", "AWS/GCP", "CI/CD", "Observability tools"],
    },
    {
        "title": "Lead Full-Stack Engineer",
        "department": "Tech & Eng",
        "location": "Hyderabad",
        "type": "Full-Time",
        "description": "Lead full-stack development for annotation and data intelligence platforms.",
        "requirements": ["React + Node/Python", "System design", "5+ years experience", "Team leadership"],
    },
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
    """Insert seed jobs if none exist."""
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
