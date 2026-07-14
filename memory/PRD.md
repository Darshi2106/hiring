# CohortData Hiring Portal — PRD

## Original problem statement
Build a hiring portal for CohortData with proctored, anti-cheat assignments and an HR module to manage applications. Openings reference: https://www.cohortdata.com/careers#careers-open-roles

## User choices
1. Fully admin-managed jobs (HR creates all roles)
2. Assignments include: Coding challenge in monitored editor, MCQ with timer, short answers
3. All anti-cheat measures: fullscreen lock, tab-switch detection, copy/paste disable, webcam snapshots, AI-content detection, one-time unique links + timer
4. AI detection LLM: Claude Sonnet 4.5 via Emergent Universal LLM Key
5. HR authentication: JWT-based email/password

## User personas
- **Candidate**: Public visitor, browses roles, applies with resume, receives invite email, takes proctored assessment
- **HR Admin**: Signs in to dashboard, creates/edits jobs, reviews applications, sends assignment invites, reviews submissions with AI risk scores

## Architecture
- Backend: FastAPI + Motor (MongoDB async) + PyJWT + bcrypt + emergentintegrations (Claude Sonnet 4.5)
- Frontend: React Router 7, Tailwind + Shadcn UI, sonner toasts, lucide-react icons
- Auth: Bearer token in Authorization header (JWT, 8h expiry)
- DB Collections: `users`, `jobs`, `applications`, `invites`, `submissions`

## Implemented (Feb 2026)
- Public careers listing (7 seed jobs from cohortdata.com)
- Job detail page with assessment preview
- Application form with resume upload (PDF/DOC/DOCX, 5MB, object storage)
- Candidate portal: register/login/dashboard, 1-click "Take assessment" / "Schedule interview"
- CohortData brand identity: official logo + teal/petrol/yellow palette
- HR JWT login + role-guarded routes
- HR dashboard with live stats + quick actions
- HR jobs CRUD with per-role config: AI-reject threshold, Calendly URL, **auto-shortlist thresholds** (MCQ%, AI-risk max, max violations)
- Per-job Assignment editor (MCQs with weights, short-answer, coding, duration)
- **Question Library (27 modules, 160+ questions)**:
  - MCQ (12 modules, ~110 Qs): Frontend, Backend, Full-stack, ML, CV, DSA, SQL, Aptitude (Quant/Logical/Verbal), Sales, Operations
  - Short-answer banks (3 modules, ~15 Qs): Behavioral, Tech-scenario, Sales-scenario
  - **Coding tasks (12 modules, 37 tasks)**: Python (Beginner/Intermediate/Advanced), JavaScript/Async, React Components, Data Structures, SQL, Pandas/Data Wrangling, ML Pipeline, Computer Vision (OpenCV), FastAPI/Backend, Debug & Fix
- AI-risk auto-reject (Claude Sonnet 4.5) — per-job threshold, HR override
- **Weighted MCQ grading** — each MCQ has a weight; `mcq_pct_weighted` reported on submissions
- **Auto-shortlist on submit** — if `mcq_pct ≥ 80 AND ai_risk_max < 10 AND violations ≤ 0` (all configurable) → application status auto-flips to `interview_scheduled` and candidate immediately sees the Calendly link
- **Live email delivery via Resend** (`re_XHA2...` configured, sender `onboarding@resend.dev`)
- Startup + new-job creation auto-apply `DEFAULT_CALENDLY_URL` when unset
- Master admin `darshan@cohortdata.com` — creates/deactivates HR users
- Deactivated users blocked at login (403)

## Backlog (P1/P2)
- P1: Email delivery of invite links (currently HR copies link manually)
- P1: Resume file upload via object storage (currently URL only)
- P1: HR to customize assignment per-role (MCQ questions, coding prompts) — currently uses seed template
- P2: Multi-language coding editor with syntax highlighting (Monaco/CodeMirror)
- P2: Bulk actions on applications, filters by status
- P2: Interview scheduling, offer letter generation

## Next tasks
1. Email integration (Resend/SendGrid) for invite links
2. Object storage for resumes
3. Per-job assignment editor UI
