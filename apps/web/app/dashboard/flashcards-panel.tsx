"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { BookOpen, Filter, Pencil, Plus, RotateCw, Sparkles, Trash2, Eye, EyeOff } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Flashcard,
  Note,
  StudyDocument,
  Subject,
  Topic,
  getDocuments,
  getFlashcards,
  getNotes,
  createFlashcard,
  updateFlashcard,
  reviewFlashcard,
  deleteFlashcard,
  generateFlashcards,
} from "@/lib/api";

type FlashcardsPanelProps = {
  subjects: Subject[];
  topics: Topic[];
};

type Draft = {
  front: string;
  back: string;
  subject_id: string;
  topic_id: string;
};

export function FlashcardsPanel({ subjects, topics }: FlashcardsPanelProps) {
  const [notes, setNotes] = useState<Note[]>([]);
  const [documents, setDocuments] = useState<StudyDocument[]>([]);
  const [reviewBusy, setReviewBusy] = useState(false);
  const [sourceError, setSourceError] = useState("");
  const [cards, setCards] = useState<Flashcard[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filterSubject, setFilterSubject] = useState("");
  const [filterStatus, setFilterStatus] = useState("");
  const [filterGenerated, setFilterGenerated] = useState("");
  const [query, setQuery] = useState("");
  const [editorOpen, setEditorOpen] = useState(false);
  const [editing, setEditing] = useState<Flashcard | null>(null);
  const [draft, setDraft] = useState<Draft>({ front: "", back: "", subject_id: "", topic_id: "" });
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  // Generate form
  const [genOpen, setGenOpen] = useState(false);
  const [genSourceType, setGenSourceType] = useState<"note" | "document">("note");
  const [genSourceId, setGenSourceId] = useState("");
  const [genMaxCards, setGenMaxCards] = useState(8);
  const [genSubject, setGenSubject] = useState("");
  const [genTopic, setGenTopic] = useState("");

  // Study mode
  const [studyIndex, setStudyIndex] = useState(0);
  const [showBack, setShowBack] = useState(false);
  const [studyMode, setStudyMode] = useState(false);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [data, n, d] = await Promise.all([
        (async () => {
          const all: Flashcard[] = [];
          let page: Flashcard[];
          do { page = await getFlashcards({ limit: 100, offset: all.length }); all.push(...page); }
          while (page.length === 100);
          return all;
        })(),
        getNotes({ limit: 50 }).catch(() => { setSourceError("Could not load note sources. Reopen this tab to retry."); return [] as Note[]; }),
        getDocuments({ limit: 50, status: "completed" }).then((r) => r.items).catch(() => { setSourceError("Could not load PDF sources. Reopen this tab to retry."); return [] as StudyDocument[]; }),
      ]);
      setCards(data);
      setNotes(n as Note[]);
      setDocuments(d as StudyDocument[]);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to load flashcards.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void refresh(); }, [refresh]);

  const filtered = useMemo(() => {
    return cards.filter((c) => {
      if (filterSubject && String(c.subject_id) !== filterSubject) return false;
      if (filterStatus && c.review_status !== filterStatus) return false;
      if (filterGenerated === "manual" && c.is_generated) return false;
      if (filterGenerated === "generated" && !c.is_generated) return false;
      if (query.trim()) {
        const q = query.trim().toLowerCase();
        if (!c.front.toLowerCase().includes(q) && !c.back.toLowerCase().includes(q)) return false;
      }
      return true;
    });
  }, [cards, filterSubject, filterStatus, filterGenerated, query]);

  const stats = useMemo(() => {
    const total = cards.length;
    const known = cards.filter((c) => c.review_status === "known").length;
    const needs = total - known;
    return { total, known, needs };
  }, [cards]);

  const safeIndex = Math.min(studyIndex, Math.max(0, filtered.length - 1));
  const currentStudyCard = filtered[safeIndex] || null;
  useEffect(() => { setStudyIndex(0); setShowBack(false); }, [filterSubject, filterStatus, filterGenerated, query]);

  function openEditor(card?: Flashcard) {
    setEditing(card || null);
    setFormError(null);
    if (card) {
      setDraft({ front: card.front, back: card.back, subject_id: card.subject_id?.toString() || "", topic_id: card.topic_id?.toString() || "" });
    } else {
      setDraft({ front: "", back: "", subject_id: "", topic_id: "" });
    }
    setEditorOpen(true);
  }

  async function handleSave(e: FormEvent) {
    e.preventDefault();
    setFormError(null);
    if (!draft.front.trim() || !draft.back.trim()) {
      setFormError("Both front and back are required.");
      return;
    }
    setSaving(true);
    try {
      const payload = {
        front: draft.front.trim(),
        back: draft.back.trim(),
        subject_id: Number(draft.subject_id),
        topic_id: draft.topic_id ? Number(draft.topic_id) : null,
      };
      if (editing) {
        await updateFlashcard(editing.id, payload);
      } else {
        await createFlashcard(payload);
      }
      setEditorOpen(false);
      await refresh();
    } catch (cause) {
      setFormError(cause instanceof Error ? cause.message : "Could not save flashcard.");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(card: Flashcard) {
    if (!window.confirm(`Delete flashcard "${card.front.slice(0, 40)}"?`)) return;
    try {
      await deleteFlashcard(card.id);
      await refresh();
      if (studyMode && studyIndex >= filtered.length - 1) setStudyIndex(Math.max(0, filtered.length - 2));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not delete flashcard.");
    }
  }

  async function handleReview(status: "known" | "needs_revision") {
    if (!currentStudyCard || reviewBusy) return;
    setReviewBusy(true);
    try {
      const reviewed = await reviewFlashcard(currentStudyCard.id, status);
      setCards((current) => current.map((c) => c.id === reviewed.id ? reviewed : c));
      // Move to next
      if (studyIndex + 1 < filtered.length) {
        setStudyIndex((i) => i + 1);
        setShowBack(false);
      } else {
        setShowBack(false);
      }
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not update review status.");
    } finally { setReviewBusy(false); }
  }

  async function handleGenerate(e: FormEvent) {
    e.preventDefault();
    setFormError(null);
    if (!genSourceId) {
      setFormError("Select a source note or document.");
      return;
    }
    setSaving(true);
    try {
      await generateFlashcards({
        subject_id: genSubject ? Number(genSubject) : null,
        topic_id: genTopic ? Number(genTopic) : null,
        source_type: genSourceType,
        source_id: Number(genSourceId),
        max_cards: genMaxCards,
      });
      setGenOpen(false);
      await refresh();
    } catch (cause) {
      setFormError(cause instanceof Error ? cause.message : "Could not generate flashcards.");
    } finally {
      setSaving(false);
    }
  }

  const fieldCls = "w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500";

  if (loading) return <div className="p-8 text-sm text-slate-600">Loading flashcards…</div>;

  return (
    <section className="space-y-6">
      <header className="rounded-2xl border border-violet-100 bg-gradient-to-br from-violet-50 to-white p-6">
        <h1 className="text-xl font-bold text-slate-900">Flashcards</h1>
        <p className="mt-1 text-sm text-slate-600">
          Flip-card review for quick recall. Mark cards as Known or Needs Revision. Generated cards are clearly distinguished from manually created ones.
        </p>
        <div className="mt-4 flex flex-wrap gap-2 text-xs">
          <span className="rounded-full bg-white border px-3 py-1">Total: {stats.total}</span>
          <span className="rounded-full bg-emerald-50 border border-emerald-200 px-3 py-1 text-emerald-800">Known: {stats.known}</span>
          <span className="rounded-full bg-amber-50 border border-amber-200 px-3 py-1 text-amber-800">Needs revision: {stats.needs}</span>
        </div>
      </header>

      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <span className="flex items-center gap-1.5 text-xs text-slate-600"><Filter className="h-4 w-4" /> Filters:</span>
          <input placeholder="Search front/back" value={query} onChange={(e) => setQuery(e.target.value)} className="rounded-lg border border-slate-300 bg-white px-2 py-1 text-sm" />
          <select value={filterSubject} onChange={(e) => setFilterSubject(e.target.value)} className="rounded-lg border border-slate-300 bg-white px-2 py-1 text-sm">
            <option value="">All subjects</option>
            {subjects.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
          </select>
          <select value={filterStatus} onChange={(e) => setFilterStatus(e.target.value)} className="rounded-lg border border-slate-300 bg-white px-2 py-1 text-sm">
            <option value="">All statuses</option>
            <option value="known">Known</option>
            <option value="needs_revision">Needs revision</option>
          </select>
          <select value={filterGenerated} onChange={(e) => setFilterGenerated(e.target.value)} className="rounded-lg border border-slate-300 bg-white px-2 py-1 text-sm">
            <option value="">All cards</option>
            <option value="manual">Manually created</option>
            <option value="generated">Generated</option>
          </select>
        </div>
        <div className="flex gap-2">
          <Button variant="ghost" onClick={() => setGenOpen(true)} className="border"><Sparkles className="h-4 w-4" /> Generate from Note/PDF</Button>
          <Button onClick={() => openEditor()} className="gap-1.5"><Plus className="h-4 w-4" /> New Card</Button>
        </div>
      </div>

      {error && <p role="alert" className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-800">{error}</p>}

      {sourceError && <p role="alert" className="text-sm text-amber-800">{sourceError}</p>}
      {/* Study mode */}
      <div className="rounded-2xl border bg-white p-5">
        <div className="flex items-center justify-between">
          <h2 className="flex items-center gap-2 font-semibold text-sm"><BookOpen className="h-4 w-4" /> Study Session</h2>
          <Button
            variant="ghost"
            className="border"
            onClick={() => {
              if (filtered.length === 0) return;
              setStudyMode(!studyMode);
              setStudyIndex(0);
              setShowBack(false);
            }}
            disabled={filtered.length === 0}
          >
            {studyMode ? "Exit Study Mode" : "Enter Study Mode"}
          </Button>
        </div>

        {studyMode ? (
          filtered.length === 0 ? (
            <p className="mt-4 text-sm text-slate-500">No cards match the filters. Adjust filters or create a card.</p>
          ) : (
            <div className="mt-4 space-y-4">
              <p className="text-xs text-slate-500">Card {safeIndex + 1} of {filtered.length} · {currentStudyCard?.subject_name || "No subject"} · {currentStudyCard?.review_status}</p>
              <div
                className="rounded-xl border-2 border-violet-200 bg-gradient-to-br from-white to-violet-50 p-6 min-h-[160px] flex flex-col justify-center cursor-pointer select-none"
                onClick={() => setShowBack(!showBack)}
                role="button"
                tabIndex={0}
                aria-label="Flip card"
                onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); setShowBack(!showBack); } }}
              >
                {!showBack ? (
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-wide text-violet-700">Question</p>
                    <p className="mt-2 text-lg font-medium text-slate-900">{currentStudyCard?.front}</p>
                    <p className="mt-3 text-xs text-slate-500 flex items-center gap-1"><Eye className="h-3 w-3" /> Tap to reveal answer</p>
                  </div>
                ) : (
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-wide text-emerald-700">Answer</p>
                    <p className="mt-2 text-base text-slate-800">{currentStudyCard?.back}</p>
                    <p className="mt-3 text-xs text-slate-500 flex items-center gap-1"><EyeOff className="h-3 w-3" /> Tap to hide</p>
                  </div>
                )}
                {currentStudyCard?.is_generated && <span className="mt-4 inline-block rounded-full bg-violet-100 border border-violet-200 px-2 py-0.5 text-xs text-violet-700">Generated from {currentStudyCard.source_type}</span>}
              </div>
              <div className="flex flex-wrap gap-2">
                <Button disabled={reviewBusy} onClick={() => handleReview("needs_revision")} variant="ghost" className="border border-amber-300 bg-amber-50">Needs Revision</Button>
                <Button disabled={reviewBusy} onClick={() => handleReview("known")} className="bg-emerald-600 hover:bg-emerald-700">Mark as Known</Button>
                <Button onClick={() => { setShowBack(false); setStudyIndex((i) => Math.max(0, i - 1)); }} disabled={studyIndex === 0} variant="ghost" className="border">Previous</Button>
                <Button onClick={() => { setShowBack(false); setStudyIndex((i) => Math.min(filtered.length - 1, i + 1)); }} disabled={studyIndex >= filtered.length - 1} variant="ghost" className="border">Next</Button>
                <Button onClick={() => setShowBack(!showBack)} variant="ghost" className="border gap-1"><RotateCw className="h-4 w-4" /> Flip</Button>
              </div>
            </div>
          )
        ) : (
          <p className="mt-2 text-xs text-slate-500">Enter study mode to flip through the filtered cards one by one. Your review status is preserved across sessions.</p>
        )}
      </div>

      {/* Grid of all cards */}
      {filtered.length === 0 ? (
        <div className="rounded-2xl border border-dashed bg-white p-10 text-center text-sm text-slate-600">No flashcards yet. Create one or generate from your notes/PDFs.</div>
      ) : (
        <div className="grid gap-3 md:grid-cols-2">
          {filtered.map((c) => (
            <div key={c.id} className="rounded-xl border bg-white p-4 shadow-sm">
              <div className="flex items-start justify-between gap-2">
                <span className={`rounded-full border px-2 py-0.5 text-xs ${c.review_status === "known" ? "bg-emerald-50 border-emerald-200 text-emerald-700" : "bg-amber-50 border-amber-200 text-amber-800"}`}>{c.review_status}</span>
                <span className="text-xs text-slate-500">{c.subject_name || "No subject"} {c.topic_name ? `· ${c.topic_name}` : ""}</span>
              </div>
              <p className="mt-2 font-semibold text-sm text-slate-900 line-clamp-3">{c.front}</p>
              <p className="mt-1 text-xs text-slate-600 line-clamp-3">{c.back}</p>
              <div className="mt-2 flex flex-wrap gap-1.5 text-xs">
                {c.is_generated && <span className="rounded-full bg-violet-50 border border-violet-200 px-2 py-0.5 text-violet-700">Generated</span>}
                {c.last_reviewed_at && <span className="rounded-full bg-slate-50 border px-2 py-0.5">Reviewed: {new Date(c.last_reviewed_at).toLocaleDateString()}</span>}
              </div>
              <div className="mt-3 flex gap-1">
                <Button variant="ghost" onClick={() => openEditor(c)} className="h-8 px-2 text-xs"><Pencil className="h-3 w-3" /> Edit</Button>
                <Button variant="ghost" onClick={() => handleDelete(c)} className="h-8 px-2 text-xs text-red-600 hover:bg-red-50"><Trash2 className="h-3 w-3" /> Delete</Button>
              </div>
            </div>
          ))}
        </div>
      )}

      {editorOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
          <div className="w-full max-w-lg rounded-2xl bg-white p-6 shadow-xl">
            <h3 className="text-lg font-bold text-slate-900">{editing ? "Edit Flashcard" : "Create Flashcard"}</h3>
            <form onSubmit={handleSave} className="mt-4 space-y-3">
              <div>
                <label className="block text-xs font-medium text-slate-700">Front (Question) *</label>
                <textarea value={draft.front} onChange={(e) => setDraft({ ...draft, front: e.target.value })} rows={3} required maxLength={2000} placeholder="e.g. What is an operating system?" className={fieldCls} />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-700">Back (Answer) *</label>
                <textarea value={draft.back} onChange={(e) => setDraft({ ...draft, back: e.target.value })} rows={3} required maxLength={2000} placeholder="System software that manages hardware resources…" className={fieldCls} />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-700">Subject</label>
                  <select value={draft.subject_id} onChange={(e) => setDraft({ ...draft, subject_id: e.target.value, topic_id: "" })} required className={fieldCls}>
                    <option value="">None</option>
                    {subjects.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-700">Topic</label>
                  <select value={draft.topic_id} onChange={(e) => setDraft({ ...draft, topic_id: e.target.value })} className={fieldCls}>
                    <option value="">None</option>
                    {topics.filter((t) => !draft.subject_id || t.subject_id === Number(draft.subject_id)).map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
                  </select>
                </div>
              </div>
              {formError && <p className="text-sm text-red-600">{formError}</p>}
              <div className="flex justify-end gap-2 pt-2">
                <Button type="button" variant="ghost" onClick={() => setEditorOpen(false)}>Cancel</Button>
                <Button type="submit" disabled={saving}>{saving ? "Saving…" : editing ? "Update Card" : "Create Card"}</Button>
              </div>
            </form>
          </div>
        </div>
      )}

      {genOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
          <div className="w-full max-w-lg rounded-2xl bg-white p-6 shadow-xl">
            <h3 className="text-lg font-bold text-slate-900">Generate Flashcards from Source</h3>
            <p className="text-xs text-slate-500">Lightweight rule-based generation — extracts term/definition pairs. Generated cards are marked clearly and can be edited/deleted.</p>
            <form onSubmit={handleGenerate} className="mt-4 space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-700">Source type</label>
                  <select value={genSourceType} onChange={(e) => { setGenSourceType(e.target.value as "note" | "document"); setGenSourceId(""); }} className={fieldCls}>
                    <option value="note">Note</option>
                    <option value="document">PDF Document</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-700">Max cards</label>
                  <input type="number" min={1} max={20} value={genMaxCards} onChange={(e) => setGenMaxCards(Number(e.target.value))} className={fieldCls} />
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-700">Source (latest 50 per type) *</label>
                <select value={genSourceId} onChange={(e) => setGenSourceId(e.target.value)} className={fieldCls} required>
                  <option value="">Select source</option>
                  {(genSourceType === "note" ? notes : documents).map((s) => <option key={s.id} value={s.id}>{s.title}</option>)}
                </select>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-700">Assign subject (optional)</label>
                  <select value={genSubject} onChange={(e) => setGenSubject(e.target.value)} className={fieldCls}>
                    <option value="">None</option>
                    {subjects.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-700">Assign topic (optional)</label>
                  <select value={genTopic} onChange={(e) => setGenTopic(e.target.value)} className={fieldCls}>
                    <option value="">None</option>
                    {topics.filter((t) => !genSubject || t.subject_id === Number(genSubject)).map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
                  </select>
                </div>
              </div>
              {formError && <p className="text-sm text-red-600">{formError}</p>}
              <div className="flex justify-end gap-2 pt-2">
                <Button type="button" variant="ghost" onClick={() => setGenOpen(false)}>Cancel</Button>
                <Button type="submit" disabled={saving}>{saving ? "Generating…" : "Generate"}</Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </section>
  );
}
