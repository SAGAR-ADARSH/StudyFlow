"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import {
  FileText,
  Pin,
  Pencil,
  Plus,
  Search,
  StickyNote,
  Trash2,
  X,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  createNote,
  deleteNote,
  getNotes,
  Note,
  Subject,
  Topic,
  updateNote,
} from "@/lib/api";

type NoteDraft = {
  title: string;
  content: string;
  subject_id: string;
  topic_id: string;
  tags: string;
  is_pinned: boolean;
};

const PAGE_SIZE = 50;

const emptyDraft = (): NoteDraft => ({
  title: "",
  content: "",
  subject_id: "",
  topic_id: "",
  tags: "",
  is_pinned: false,
});

type NotesPanelProps = {
  subjects: Subject[];
  topics: Topic[];
};

export function NotesPanel({ subjects, topics }: NotesPanelProps) {
  const [notes, setNotes] = useState<Note[]>([]);
  const [query, setQuery] = useState("");
  const [pinnedOnly, setPinnedOnly] = useState(false);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [hasMore, setHasMore] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [editorOpen, setEditorOpen] = useState(false);
  const [editingNote, setEditingNote] = useState<Note | null>(null);
  const [draft, setDraft] = useState<NoteDraft>(emptyDraft);
  const [formError, setFormError] = useState<string | null>(null);

  const refreshNotes = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const firstPage = await getNotes({
        q: query.trim() || undefined,
        pinned: pinnedOnly,
        limit: PAGE_SIZE,
        offset: 0,
      });
      setNotes(firstPage);
      setHasMore(firstPage.length === PAGE_SIZE);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to load notes.");
    } finally {
      setLoading(false);
    }
  }, [pinnedOnly, query]);

  useEffect(() => {
    const timeout = window.setTimeout(() => void refreshNotes(), query.trim() ? 250 : 0);
    return () => window.clearTimeout(timeout);
  }, [query, refreshNotes]);

  async function loadMoreNotes() {
    setLoadingMore(true);
    setError(null);
    try {
      const nextPage = await getNotes({
        q: query.trim() || undefined,
        pinned: pinnedOnly,
        limit: PAGE_SIZE,
        offset: notes.length,
      });
      setNotes((current) => [...current, ...nextPage]);
      setHasMore(nextPage.length === PAGE_SIZE);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to load more notes.");
    } finally {
      setLoadingMore(false);
    }
  }

  const visibleNotes = notes;

  function openEditor(note?: Note) {
    setEditingNote(note || null);
    setFormError(null);
    setDraft(
      note
        ? {
            title: note.title,
            content: note.content,
            subject_id: note.subject_id?.toString() || "",
            topic_id: note.topic_id?.toString() || "",
            tags: note.tags.join(", "),
            is_pinned: note.is_pinned,
          }
        : emptyDraft(),
    );
    setEditorOpen(true);
  }

  async function handleSave(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFormError(null);
    const payload = {
      title: draft.title.trim(),
      content: draft.content.trim(),
      subject_id: draft.subject_id ? Number(draft.subject_id) : null,
      topic_id: draft.topic_id ? Number(draft.topic_id) : null,
      tags: draft.tags
        .split(",")
        .map((tag) => tag.trim())
        .filter(Boolean),
      is_pinned: draft.is_pinned,
    };
    if (!payload.title || !payload.content) {
      setFormError("Add a title and some note text before saving.");
      return;
    }

    setSaving(true);
    try {
      if (editingNote) {
        await updateNote(editingNote.id, payload);
      } else {
        await createNote(payload);
      }
      setEditorOpen(false);
      await refreshNotes();
    } catch (cause) {
      setFormError(cause instanceof Error ? cause.message : "Unable to save this note.");
    } finally {
      setSaving(false);
    }
  }

  async function handleTogglePin(note: Note) {
    try {
      await updateNote(note.id, { is_pinned: !note.is_pinned });
      await refreshNotes();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to update the pin.");
    }
  }

  async function handleDelete(note: Note) {
    if (!window.confirm(`Delete “${note.title}”? This cannot be undone.`)) return;
    try {
      await deleteNote(note.id);
      await refreshNotes();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to delete this note.");
    }
  }

  const selectedSubjectId = Number(draft.subject_id) || null;
  const availableTopics = selectedSubjectId
    ? topics.filter((topic) => topic.subject_id === selectedSubjectId)
    : [];

  return (
    <section className="space-y-6" aria-labelledby="notes-heading">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-indigo-600">Study library</p>
          <h1 id="notes-heading" className="mt-1 text-2xl font-bold tracking-tight text-slate-900">
            Notes <span className="text-slate-400">({hasMore ? `${notes.length}+` : notes.length})</span>
          </h1>
          <p className="mt-1 text-sm text-slate-500">Keep class notes, quick ideas, and revision points together.</p>
        </div>
        <Button onClick={() => openEditor()} className="gap-2 self-start sm:self-auto">
          <Plus className="h-4 w-4" /> New note
        </Button>
      </div>

      <div className="flex flex-col gap-3 sm:flex-row">
        <label className="relative block flex-1">
          <span className="sr-only">Search notes</span>
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search titles, note text, subjects, or tags…"
            className="w-full rounded-xl border border-slate-200 bg-white py-2.5 pl-10 pr-3 text-sm text-slate-900 outline-none transition focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100"
          />
        </label>
        <Button
          type="button"
          variant={pinnedOnly ? "default" : "ghost"}
          onClick={() => setPinnedOnly((value) => !value)}
          aria-pressed={pinnedOnly}
          className={`gap-2 border border-slate-200 ${pinnedOnly ? "" : "bg-white text-slate-600 hover:bg-slate-100"}`}
        >
          <Pin className="h-4 w-4" /> Pinned only
        </Button>
      </div>

      {error && (
        <div role="alert" className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
          {error}
        </div>
      )}

      {loading ? (
        <div className="rounded-2xl border border-slate-200 bg-white px-6 py-12 text-center text-sm text-slate-500">
          Loading your notes…
        </div>
      ) : visibleNotes.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-slate-300 bg-white px-6 py-14 text-center">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-indigo-50 text-indigo-600">
            {query || pinnedOnly ? <Search className="h-5 w-5" /> : <StickyNote className="h-5 w-5" />}
          </div>
          <h2 className="mt-4 text-base font-semibold text-slate-900">
            {query || pinnedOnly ? "No notes match this view" : "Your study library is ready"}
          </h2>
          <p className="mx-auto mt-1 max-w-md text-sm text-slate-500">
            {query || pinnedOnly
              ? "Try a different search or turn off the pinned filter."
              : "Create your first note and link it to a subject or syllabus topic."}
          </p>
          {!query && !pinnedOnly && (
            <Button onClick={() => openEditor()} className="mt-5 gap-2">
              <Plus className="h-4 w-4" /> Create a note
            </Button>
          )}
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {visibleNotes.map((note) => (
            <article key={note.id} className="flex min-h-64 flex-col rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md">
              <div className="flex items-start justify-between gap-3">
                <div className="flex min-w-0 items-start gap-3">
                  <div className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-indigo-50 text-indigo-600">
                    <FileText className="h-4 w-4" />
                  </div>
                  <div className="min-w-0">
                    <h2 className="break-words text-sm font-semibold text-slate-900">{note.title}</h2>
                    <p className="mt-1 text-[11px] text-slate-500">
                      {note.subject_name || "General note"}
                      {note.topic_name ? ` · ${note.topic_name}` : ""}
                    </p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => void handleTogglePin(note)}
                  aria-label={note.is_pinned ? `Unpin ${note.title}` : `Pin ${note.title}`}
                  title={note.is_pinned ? "Unpin note" : "Pin note"}
                  className={`rounded-lg p-2 transition ${note.is_pinned ? "bg-amber-50 text-amber-600" : "text-slate-400 hover:bg-slate-100 hover:text-slate-700"}`}
                >
                  <Pin className="h-4 w-4" />
                </button>
              </div>

              <p className="mt-4 max-h-32 flex-1 overflow-hidden whitespace-pre-wrap break-words text-sm leading-6 text-slate-600">
                {note.content}
              </p>

              {note.tags.length > 0 && (
                <div className="mt-4 flex flex-wrap gap-1.5">
                  {note.tags.map((tag) => (
                    <span key={tag} className="rounded-full bg-slate-100 px-2.5 py-1 text-[10px] font-medium text-slate-600">
                      {tag}
                    </span>
                  ))}
                </div>
              )}

              <div className="mt-4 flex items-center justify-between border-t border-slate-100 pt-3">
                <time className="text-[10px] text-slate-400" dateTime={note.updated_at || note.created_at}>
                  Updated {new Date(note.updated_at || note.created_at).toLocaleDateString()}
                </time>
                <div className="flex items-center gap-1">
                  <button
                    type="button"
                    onClick={() => openEditor(note)}
                    aria-label={`Edit ${note.title}`}
                    className="rounded-lg p-2 text-slate-500 transition hover:bg-indigo-50 hover:text-indigo-600"
                  >
                    <Pencil className="h-4 w-4" />
                  </button>
                  <button
                    type="button"
                    onClick={() => void handleDelete(note)}
                    aria-label={`Delete ${note.title}`}
                    className="rounded-lg p-2 text-slate-500 transition hover:bg-rose-50 hover:text-rose-600"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </div>
            </article>
          ))}
        </div>
      )}

      {!loading && hasMore && visibleNotes.length > 0 && (
        <div className="flex justify-center">
          <Button type="button" variant="ghost" onClick={() => void loadMoreNotes()} disabled={loadingMore}>
            {loadingMore ? "Loading more…" : "Load more notes"}
          </Button>
        </div>
      )}

      {editorOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/40 p-4 backdrop-blur-sm">
          <section
            role="dialog"
            aria-modal="true"
            aria-labelledby="note-editor-title"
            className="max-h-[95vh] w-full max-w-2xl overflow-y-auto rounded-2xl bg-white p-6 shadow-2xl"
          >
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2 id="note-editor-title" className="text-lg font-bold text-slate-900">
                  {editingNote ? "Edit note" : "Create a note"}
                </h2>
                <p className="mt-1 text-xs text-slate-500">Save a thought now; organize it by subject or topic when useful.</p>
              </div>
              <button
                type="button"
                aria-label="Close note editor"
                onClick={() => setEditorOpen(false)}
                className="rounded-lg p-2 text-slate-400 hover:bg-slate-100 hover:text-slate-700"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <form onSubmit={handleSave} className="mt-5 space-y-4">
              <div>
                <label htmlFor="note-title" className="block text-xs font-semibold text-slate-700">Title *</label>
                <input
                  id="note-title"
                  required
                  maxLength={180}
                  autoFocus
                  value={draft.title}
                  onChange={(event) => setDraft({ ...draft, title: event.target.value })}
                  placeholder="e.g. Big-O quick reference"
                  className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
                />
              </div>

              <div className="grid gap-3 sm:grid-cols-2">
                <div>
                  <label htmlFor="note-subject" className="block text-xs font-semibold text-slate-700">Subject</label>
                  <select
                    id="note-subject"
                    value={draft.subject_id}
                    onChange={(event) => setDraft({ ...draft, subject_id: event.target.value, topic_id: "" })}
                    className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
                  >
                    <option value="">General note</option>
                    {subjects.map((subject) => (
                      <option key={subject.id} value={subject.id}>{subject.name}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label htmlFor="note-topic" className="block text-xs font-semibold text-slate-700">Syllabus topic</label>
                  <select
                    id="note-topic"
                    value={draft.topic_id}
                    onChange={(event) => setDraft({ ...draft, topic_id: event.target.value })}
                    disabled={!selectedSubjectId || availableTopics.length === 0}
                    className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100 disabled:bg-slate-50 disabled:text-slate-400"
                  >
                    <option value="">No topic selected</option>
                    {availableTopics.map((topic: Topic) => (
                      <option key={topic.id} value={topic.id}>{topic.name}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label htmlFor="note-content" className="block text-xs font-semibold text-slate-700">Note *</label>
                <textarea
                  id="note-content"
                  required
                  maxLength={100_000}
                  rows={9}
                  value={draft.content}
                  onChange={(event) => setDraft({ ...draft, content: event.target.value })}
                  placeholder="Write your class notes, key concepts, or revision checklist…"
                  className="mt-1 w-full resize-y rounded-lg border border-slate-300 px-3 py-2.5 text-sm leading-6 outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
                />
              </div>

              <div className="grid gap-3 sm:grid-cols-[1fr_auto] sm:items-end">
                <div>
                  <label htmlFor="note-tags" className="block text-xs font-semibold text-slate-700">Tags</label>
                  <input
                    id="note-tags"
                    value={draft.tags}
                    onChange={(event) => setDraft({ ...draft, tags: event.target.value })}
                    placeholder="comma, separated, tags"
                    className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
                  />
                  <p className="mt-1 text-[10px] text-slate-400">Up to 20 tags, 40 characters each.</p>
                </div>
                <label className="flex h-10 items-center gap-2 rounded-lg border border-slate-200 px-3 text-sm text-slate-700">
                  <input
                    type="checkbox"
                    checked={draft.is_pinned}
                    onChange={(event) => setDraft({ ...draft, is_pinned: event.target.checked })}
                    className="h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
                  />
                  Pin this note
                </label>
              </div>

              {formError && (
                <p role="alert" className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-xs text-rose-700">{formError}</p>
              )}

              <div className="flex justify-end gap-2 border-t border-slate-100 pt-4">
                <Button type="button" variant="ghost" onClick={() => setEditorOpen(false)}>Cancel</Button>
                <Button type="submit" disabled={saving}>{saving ? "Saving…" : editingNote ? "Save changes" : "Create note"}</Button>
              </div>
            </form>
          </section>
        </div>
      )}
    </section>
  );
}
