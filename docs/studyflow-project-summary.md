# StudyFlow — Complete Project and Feature Summary

## 1. What is StudyFlow?

StudyFlow is a web-based study organizer and exam-preparation companion for college
students, including MCA and B.Tech students. It brings academic organization, personal
notes, PDF study material, summaries, practice quizzes, and focused daily preparation
into one application.

Its main workflow is:

**Register → Create semesters → Add subjects → Add syllabus topics → Schedule exams →
Add notes/upload PDFs → Review summaries → Practice quizzes → Use Sprint Mode → Track progress.**

StudyFlow's intelligence is lightweight and explainable: local text-processing
algorithms and rule-based scheduling, not a mandatory external chatbot or paid AI API.

## 2. Features and how they work

### A. Registration, sign-in, and account security

**Purpose:** Give each student a private workspace.

**How it works:**
1. A student registers with an email, display name, and password. College and course
   details can also be stored.
2. Passwords must contain at least 12 characters, including uppercase, lowercase, and
   a number. New passwords are stored as Argon2id hashes, not readable passwords.
3. A successful registration or login returns a signed JWT access token. The frontend
   stores the token and attaches it to authenticated API requests.
4. FastAPI validates the token, expiry, issuer, active account, and password-bound
   signature before returning student data.
5. Changing a password invalidates older sessions and provides a new token for the
   current client. Existing legacy bcrypt hashes can be upgraded on successful login.
6. Signing out removes the locally stored token. Missing or expired sessions return
   the student to sign-in.

The default token lifetime is 60 minutes and is configurable. Browser calls use the
same-origin Next.js API proxy; it translates the app-specific token header to Bearer
authentication for the backend. This avoids hosted preview gateways consuming the
application's standard Authorization header.

**Ownership:** Data queries check the authenticated user. Another student's document,
quiz, note, or Sprint ID is not a way to access their data; protected owner-scoped
lookups return 404 for inaccessible records.

### B. Student profile

**Purpose:** Store identity and academic context.

The account stores the student's display name, email, college, and course. Backend
profile endpoints retrieve and update supported profile fields. The dashboard displays
student information, and its Security dialog supports password changes. Profile data
is not shared automatically between students.

### C. Semester management

**Purpose:** Organize studies into academic terms.

Students create semesters and can store a semester number, dates, and active status.
They can list, update, delete, and activate semesters through the API. The active
semester provides the main context for the overview and adding subjects.

Semesters group subjects and their related academic records. Deleting a semester is
not the same as archiving it: academic child records can cascade according to the
schema. Notes/PDF references that use nullable links are handled by their configured
relationships. This is distinct from the implementation process, which never resets
the database.

### D. Subject management

**Purpose:** Keep each course's syllabus and preparation together.

A subject belongs to a semester and the student. Fields include its name, course code,
color, credits, difficulty, target grade, and description. The API supports CRUD and
semester filtering.

Subject cards show topic-completion progress. Topics, exams, linked notes, PDFs,
quizzes and Sprint preparation use the subject as a common academic context.

### E. Topic and syllabus tracking

**Purpose:** Break a subject into manageable units of learning.

Each topic belongs to a subject and can store a unit number, description, priority
(High/Medium/Low), importance (1–5), estimated hours, completed hours, and order.

Its study status is tracked as **Pending**, **In Progress**, or **Completed**. Changing
topic status updates progress calculations. Completed hours are editable estimates;
they are not automatically measured by a background timer.

Sprint Mode reads these same topics; it does not create a duplicate syllabus.
Completing a Sprint task and marking its topic learned are deliberately separate actions.

### F. Exam scheduling and results

**Purpose:** Know what assessment is next and when preparation is due.

An exam belongs to a subject and stores its title, assessment type, date, optional
start time, duration, marks, location, notes, and status. APIs support adding/updating/
deleting exams, filtering, and recording target/obtained marks.

The dashboard displays upcoming exams and days remaining. Statuses include Upcoming,
Completed, and Cancelled. Sprint Mode can be started for an upcoming exam dated today
or later. An exam record is a scheduled assessment; it is not the same thing as a
content-generated practice quiz.

### G. Dashboard and overview

**Purpose:** Give the student a useful starting point.

The overview displays:
- Active semester and its subjects.
- Total subject count.
- Completed versus total topics and completion percentage.
- Subject-level topic progress.
- Upcoming exams with date/countdown indicators.
- Quick actions for semesters, subjects and exams.
- An opt-in Sprint suggestion when an exam approaches.

Navigation separates semesters, subjects, topics, exams, Notes & PDFs, and Sprint Mode.
Values come from saved academic records, not hardcoded dashboard scores. These are
basic progress indicators, not advanced predictive analytics.

### H. Personal text notes

**Purpose:** Write and organize the student's own material.

Students can create, read, edit and delete plain-text notes, optionally associate them
with a subject/topic, add up to 20 tags, and pin important notes. Server-side search
covers note text, tags and linked academic names; filters and pagination are supported.
Pinned notes sort ahead of other notes.

Deleting a linked subject/topic retains the note and clears the corresponding nullable
reference. Text notes can use the same summary and quiz services as uploaded PDFs.

### I. PDF upload, storage, and extraction

**Purpose:** Turn uploaded lecture material into text that other study tools can reuse.

**Processing flow:**
1. Validate file extension, content type, PDF header/magic bytes, and size. The default
   upload limit is 20 MB.
2. Calculate a content hash to reject byte-identical duplicate uploads for that student.
3. Save the PDF using the existing local upload-storage approach, under a user-specific
   path, and create its database record.
4. Extract text using PyMuPDF in a worker thread. Persist text, page offsets, counts,
   academic links, and any truncation information.
5. Track the lifecycle as pending → processing → completed, or failed.

Corrupt, empty, password-protected, scanned/no-text, and insufficient-text files have
clear error states. Failed extraction is never labelled completed. Failed cards offer
retry/reprocessing. The interface supports search/filtering, extracted-text viewing,
summary/quiz actions, and deletion.

**Limit:** Image-only/scanned PDFs require OCR, which is not implemented. A PDF can
have enough text for extraction but still lack enough reliable content for a quiz.

### J. Automatic summaries

**Purpose:** Make long notes and PDFs easier to revise.

The student chooses a summary action for a specific source. The backend uses the
source's saved text, splits long material into sentence-boundary chunks, scores
sentences with TF-IDF-style heuristics and positional weighting, and selects useful
sentences within the requested word budget. The result includes summary text, key
points, engine information, and relevant warnings.

The frontend offers Short, Standard, and Detailed lengths. A saved summary can be
reviewed after reload; regeneration saves a new version. PDF summary history is also
available through the API.

**Important:** This is extractive summarization: it selects source sentences. It does
not promise human-quality rewriting, translation, or an external AI explanation.
No paid service, API key, or large model download is required.

### K. Quiz generation, taking, scoring, and results

**Purpose:** Practice recall using the actual uploaded or written material.

The existing quiz generator finds definition-style facts, then creates cloze or
term/definition multiple-choice questions. Distractors come from other relevant terms
in the same source. Explanations quote source text; page references are included where
available. Unreliable candidates are skipped rather than replaced with invented facts.

The student selects a question count. The API accepts 1–20; the current UI offers
3, 5, 8, or 10. Actual output may be smaller when the source cannot support enough
reliable questions. Options number varies with available reliable distractors.

The taking screen shows one question at a time, allows option selection and navigation,
and submits to the backend. Correct answers/explanations are omitted from the taking
payload and revealed in the graded result.

**Score:** correct answers ÷ total questions × 100. Skipped questions count as incorrect.
Attempts persist selected answers, correctness, score and timestamp, plus duration
when supplied. Students can retake quizzes and inspect saved results, best score and
average score. Scheduled exam marks and practice-quiz scores remain separate.

### L. Explainable priority engine

**Purpose:** Rank preparation needs using understandable rules.

The base engine gives completed topics a score of zero. Otherwise:

**Base score = importance × 10 + exam urgency bonus.**

| Days to exam | Urgency bonus |
|---|---:|
| 0–2 | +50 |
| 3–7 | +30 |
| 8–14 | +15 |
| More than 14 / no date | +0 |

Sprint Mode consumes this score and adds its documented priority/quiz adjustments.
The engine is a rule-based heuristic, not a trained prediction model, and its urgency
bonus uses stepped thresholds rather than an exponential calculation.

### M. Sprint Mode: focused exam preparation

**Purpose:** Convert the student's available time and existing study data into a focused
plan for a chosen upcoming exam.

**Activation:** Students select an exam, enter daily available minutes, and explicitly
activate. Exams within 14 days may be recommended, but never activate automatically.
Multiple saved sprints are selectable; one sprint is stored per student/exam, including
terminal history.

**Planning:**
- Read the exam's subject, incomplete/completed topics and time estimates.
- Start with the existing priority engine score.
- Boost incomplete High-priority topics by 20 and Medium by 10.
- Read recent quiz attempts. A recent average below 70 adds a 25-point revision signal.
  Use topic-linked note evidence when available; otherwise label the signal subject-level.
- Schedule core study by priority, with small revision/quiz allocations when materials
  exist and independent practice/recall as a fallback.
- Keep completed plus pending task minutes within today's available budget.
- Show outstanding topics and warn when preparation estimates exceed remaining capacity.

**Study actions:** Review linked notes/summaries, open existing quizzes/results or
create a quiz through the existing generator, complete tasks, and explicitly mark
appropriate topics completed. Only the student's relevant subject materials are shown.
PDFs are not automatically mapped to topics because their model has no topic link.

**Adaptation:** Opening the daily plan, closing a quiz, or explicitly recalculating
refreshes relevant priorities. Matching pending tasks keep stable IDs; completed rows
and prior days are preserved. A budget below completed minutes is rejected rather than
silently erasing work. The stored IANA timezone determines daily plan boundaries.

**Controls:** Pause, resume, finish, or exit. Paused plans cannot be edited until resumed;
completed/cancelled sprints retain read-only history. Past exams cannot receive further
active scheduling. The current day is generated lazily; there is no speculative full
multi-week calendar.

**Progress:** The panel shows completed tasks, remaining planned minutes, topic completion,
revision signals, recent quiz average, and overall saved-task completion. That progress
bar is not a prediction of exam readiness. A low score does not prove a topic is unlearned,
and finishing a study block does not automatically prove mastery.

## 3. How the modules connect

```text
Student account
  └─ Semesters
      └─ Subjects
          ├─ Topics → completion + priority + estimated study time
          ├─ Exams → assessment date + countdown
          ├─ Notes / PDFs → source text
          │   ├─ Summaries → saved revision material
          │   └─ Quizzes → questions → attempts → results
          └─ Sprint Mode
              ├─ Chosen exam + topic priorities + quiz signals
              ├─ Daily time budget → persisted study tasks
              └─ Completions + materials + recalculation → updated preparation
```

Summaries and quizzes do not require a Sprint. Sprint Mode reuses them; it does not
replace ordinary notes, PDF study, or academic management.

## 4. Technology and architecture

| Layer | Technology / role |
|---|---|
| Frontend | Next.js App Router, React, TypeScript, Tailwind CSS, Lucide icons |
| Browser API access | Typed API client and same-origin Next.js proxy |
| Backend | Python, FastAPI, Pydantic request validation |
| Business logic | Academic services, DocumentService, InsightService, Sprint service |
| Database access | SQLAlchemy 2 async ORM |
| Target database | MySQL; SQLite used in automated tests and sandbox development |
| PDF processing | PyMuPDF |
| Study intelligence | Local extractive text algorithms and explicit scheduling rules |
| Security | JWT access tokens, Argon2id hashing, ownership-scoped queries |
| File storage | Server-side uploaded PDFs; metadata/text in the database |

The database currently has 15 modeled tables: users, semesters, subjects, topics,
exams, notes, documents, document_summaries, quizzes, quiz_questions, quiz_attempts,
quiz_attempt_answers, sprints, sprint_days, and sprint_tasks.

## 5. Worked example (illustrative, not a hardcoded plan)

A student adds Operating Systems, creates topics for Scheduling, Deadlocks and Memory,
schedules an exam in six days, and uploads lecture PDFs. After reviewing a summary,
the student takes a generated quiz. If recent results suggest revision would help,
Sprint Mode uses that signal alongside incomplete-topic priority.

The student enters a 90-minute daily budget. Study, revision and practice allocations
are calculated from their own records and total at most 90 minutes. Completing a task
updates progress; taking another quiz can change recommendations. Increasing the budget
allows pending work to be recalculated without removing completed work.

## 6. Current implementation status and boundaries

| Area | Status |
|---|---|
| Authentication, security and ownership | Implemented |
| Semesters, subjects, topics and exams | Implemented |
| Overview and basic progress indicators | Implemented |
| Private notes, search, tags and pinning | Implemented |
| PDF validation, extraction and failure reporting | Implemented |
| Persisted summaries and source-generated quizzes | Implemented |
| Quiz attempts, grading, retakes and results | Implemented |
| Rule-based priority scoring | Implemented |
| Sprint activation, daily plans, adaptation and controls | Implemented; core browser workflow verified during the Sprint phase |
| Additive MySQL schema and Sprint migration | Documented/schema-guarded; real MySQL runtime verification outstanding in this environment |
| OCR for scanned PDFs | Not implemented |
| Flashcards, conversational AI tutor, advanced analytics | Not implemented as current features |
| Automatic background exam notifications or calendar sync | Not implemented |
| Automatic syllabus extraction/topic mastery diagnosis from PDFs | Not implemented |

The last completed Sprint implementation verification recorded **60 backend tests
passing**, **24/24 live PDF/quiz smoke checks**, successful auth regression/typecheck/
production build, and a passing browser workflow covering a real PDF summary/quiz,
activation, adaptation, completion, budget changes, reload, pause/resume, exit and
mobile-width overflow. These are prior executed results, not a claim that tests were
rerun merely to prepare this summary. Runtime tests used SQLite, not a live MySQL server.

## 7. One-paragraph project description

StudyFlow is a full-stack academic organization and exam-preparation application that
helps students manage semesters, subjects, syllabus topics, assessments and personal
study material. It extracts text from uploaded PDFs, produces local extractive summaries,
generates source-grounded practice quizzes, and saves attempts and scores. Its Sprint
Mode combines exam urgency, topic priorities, learning-progress signals and the student's
daily time budget into an explainable, persistent study plan. All student data is protected
by authentication and ownership checks, and the core study features work without paid AI
APIs or large mandatory model downloads.
