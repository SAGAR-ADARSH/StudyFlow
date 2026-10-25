# Stable interactive preview

The interactive preview uses **demo@studyflow.edu** and the demo password already
agreed with the project owner. The password and a stable local JWT signing key live
only in ignored `.env.preview`; there is no default production credential or
hardcoded demo password in application code.

## Start the backend

From the repository root with the API dependencies installed:

```bash
python scripts/run_preview.py
```

On first setup it prompts for the agreed demo password; in a noninteractive setup,
supply `STUDYFLOW_DEMO_PASSWORD` through the environment. Later launches load it from
`.env.preview`. The file is owner-readable/writable only and must not be committed.
The launcher uses `preview.db`, preserves the existing API upload directory, listens
on `0.0.0.0:8000`, and runs an additive seed during startup. Start the web app in a
second terminal with `cd apps/web && npm run dev -- --hostname 0.0.0.0`.

This is a separate development entry point: normal FastAPI/Compose/MySQL startup does
**not** create a demo account. Do not expose the known-credential preview publicly as
a real student-data deployment. Smoke tests can create separate temporary accounts,
but those are not the interactive preview login.

## Sample workspace

- Two demo semesters; three subjects (Operating Systems, Database Management Systems,
  Computer Networks); twelve topics with pending/in-progress/completed examples.
- Three upcoming midterms and one explicitly completed practice exam.
- Two pinned notes and two real text-based sample PDFs, with saved summaries and
  source-grounded quizzes. Two graded note-quiz attempts demonstrate score history.
- Four general tasks, including overdue, upcoming, in-progress and completed examples.
- Six manual flashcards (including reviewed known cards) plus three labeled generated
  cards from the OS note.
- A finished study session and an exam Sprint with saved completed work.

**No invented measured time:** the seed starts and finishes a real session via the
existing API. It may have a zero-second duration. It does not fabricate hours of
historical studying or deterministic quiz scores; the existing grader computes scores
from sample answers. All content is illustrative demo material, not personal records.

## Reruns and recovery

The seed logs in using the same account and adds only missing named records. It does
not reset a password, clear the database, overwrite note content/status/review states,
regenerate existing summaries/quizzes, duplicate measured sessions or erase completed
Sprint work. Edited content is preserved; renaming a default fixture can cause the
missing original named fixture to be created again. Existing exam dates are preserved
rather than silently shifted on every startup. A genuinely new database gets dates
relative to its seed date.

The original historical demo database was **not available** in this workspace. Only
smoke-test accounts and an empty demo account were present. This setup recreates a
complete sample workspace; it is not a recovery of unavailable historical records.
A local SQLite backup (`preview-before-demo-setup.db`, ignored) was taken after the
initial population and before switching the preview to the repeatable launcher.
Back up `preview.db`, upload files, and `.env.preview` for exact future recovery.
If the sandbox loses these files, the launcher can rebuild sample fixtures but cannot
recover unsaved personal edits. Never copy real student records into the demo account.

## Verification

`apps/api/tests/test_preview_seed.py` checks full seed creation, rerun counts, preserved
note edits/pin state/review state/sessions/completed Sprint tasks, and refusal to reset
an existing password. Run:

```bash
python -m pytest apps/api/tests/test_preview_seed.py -q
```

Verified after setup: the fixed demo login works through the web proxy; the saved
workspace contains 2 semesters, 3 subjects, 12 topics, 4 exams, 2 notes, 2 PDFs,
9 flashcards, 4 tasks, 1 finished session and 1 Sprint with completed work.
The two new preview-fixture tests pass; the full backend suite now has **82 passing
tests**. Preview scripts pass Ruff, and `git diff --check` is clean.
