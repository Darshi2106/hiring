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
- Application form
- HR JWT login + protected routes
- HR dashboard with stats (open jobs, applications, submissions, high AI risk)
- HR jobs CRUD (create/edit/delete/close)
- HR applications table with send-invite action (generates one-time link)
- Proctored exam page with: fullscreen lock, webcam snapshots (30s interval), tab-switch/blur/copy/paste/right-click/devtools/shortcut detection, 5-violation auto-submit, countdown timer with auto-submit
- Server-side MCQ scoring
- Server-side AI content detection on short answers via Claude Sonnet 4.5 (returns risk 0-100 + reasoning + signals)
- HR submission review page with AI risk per answer, proctoring log, webcam gallery, coding solution

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
