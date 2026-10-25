# Quiz generation for lecture slides

## Failure and scope

The uploaded Trees slides had readable text, but the old parser recognized only one
usable definition. It treated short wrapped lines as headings, missed numbered bullets
and Unicode/hyphenated terms, and relied on a pool of other definitions for choices.
Generation returned HTTP 422 (`not_enough_distractors`). The message also incorrectly
said four options were mandatory although the engine accepts three or four.

## Fix

`quiz_engine.py` now uses version `extractive-cloze-v2`:

- Reconstructs wrapped prose, strips common bullet/number prefixes, handles descriptive
  `Term: A description ...` labels and Unicode dashes, and preserves PDF page boundaries.
- Uses named source headings as additional choices for definition cloze questions.
- When definitions alone cannot supply the requested count, completes quoted factual
  passages, masking an actual word and selecting alternatives from this source's prose.
- Excludes common executable-code lines, diagram fragments, instructions and unbalanced
  formula fragments from the passage fallback. Steps/formula headers are not silently
  converted into invented definitions.
- Filters equivalent hyphen/spacing/plural choices; returns three or four options.
- Keeps correct answers hidden until grading, retains page-linked excerpts and reports
  partial results. Content with no supported statements/choices still gets an honest
  actionable error; it is not forced into a fabricated quiz.

The quiz modal and current README/architecture descriptions reflect this behavior.
Summary splitting remains unchanged. Flashcard generation still uses definition pairs,
not arbitrary masked words. Auth, API contracts, storage tables, existing quizzes,
answers, attempts, uploaded files and completed progress are preserved. No migration,
external API, trained model or new dependency is required.

This is heuristic text recall, **not** semantic document understanding, interpretation
of diagram images, code execution, or OCR. Some questions may be simple passage recall.
It can legitimately return fewer than requested questions, or refuse diagram-only,
code-only or otherwise insufficient material.

## Actual verification

- **91 backend tests passed**, including nine new cases in `test_quiz_slides.py` for
  wrapped/numbered text, Unicode terms, labels versus steps, deterministic grounded
  choices, page attribution, code/diagram rejection, insufficient choices, partial
  counts, PDF upload → saved quiz → graded attempt.
- Frontend type checking, production build, existing jsdom interaction checks and Ruff
  on the engine/new tests passed. `git diff --check` passed.
- Through the running web proxy, both original uploaded Trees and Graphs documents
  returned **HTTP 201 with five saved questions**, version v2. Answer indices remained
  hidden in the taking response. No fake attempts were added to the user's uploads.
- The production preview dashboard and its eleven referenced Next assets returned
  successful responses. These HTTP/jsdom checks are not a claim of browser E2E coverage.

Refresh the preview and reopen **Practice quiz**. A new five-question quiz is already
available under **Saved quizzes** for each original upload; generating again also uses
the fixed engine. Existing login credentials and uploaded files are unchanged.
