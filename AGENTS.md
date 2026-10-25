# ChatGPT project context

This directory is a local mirror of the ChatGPT project “PRD of studyflow”.

- Treat every file under `sources/` as read-only reference material.
- Do not edit, rename, move, or delete synced project files.
- These files may be replaced the next time a task is created from this ChatGPT project.


## Project instructions

This project has no custom instructions.

## Interactive preview convention

- Use `demo@studyflow.edu` as the interactive preview account, not a randomly named
  smoke-test account. Its agreed demo password is stored in ignored `.env.preview`
  (`STUDYFLOW_DEMO_PASSWORD`); never print it, change it automatically, or commit it.
- Start the preview backend with `python scripts/run_preview.py`. This explicitly
  selects the existing `preview.db` and uploads location, preserves a local JWT key,
  and adds any missing demo fixtures. It does not modify production API startup/MySQL.
- Never wipe the preview database to repopulate the demo. The seed must preserve
  existing notes, edits, review states, and completed Sprint progress. See
  `docs/preview-demo.md`. Disposable automated-test accounts may remain separate.
