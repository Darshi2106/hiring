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
- HR jobs CRUD (+ AI-reject threshold and Calendly URL per role)
- **Per-job Assignment editor** — MCQs (2-6 options + correct + weight), short-answer (min-words + weight), coding (prompt + starter + weight), duration slider
- **Question Library (21 modules, ~130+ questions)** across Frontend, Backend, Full-stack, ML, CV, DSA, SQL, Aptitude (Quant/Logical/Verbal), Sales, Operations + short-answer banks + 6 coding tasks. HR imports questions into any job's assignment with 1 click.
- **AI-risk auto-reject**: Claude Sonnet 4.5 scores every short answer; if any score ≥ per-job threshold (default 70%), application auto-flagged as `assignment_rejected_ai`. HR can override with 1 click.
- **Email invite delivery** via Resend (with clean MOCK fallback when key not set). Sender: `onboarding@resend.dev`.
- HR applications table: view resume · send/copy invite · review submission · schedule Calendly interview
- Proctored exam (fullscreen lock, webcam snapshots, tab-switch/copy/paste/violations/auto-submit)
- HR submission review: AI risk per answer, proctoring log, webcam gallery, coding solution, auto-flag banner + override
- **Master admin** `darshan@cohortdata.com` — creates/deactivates HR users, receives CC on invite emails
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
