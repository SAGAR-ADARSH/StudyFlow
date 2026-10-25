"use client";

import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  AlertCircle,
  FileText,
  Loader2,
  RefreshCw,
  Search,
  Sparkles,
  Trash2,
  Upload,
  X,
  ClipboardList,
  FileStack,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { QuizModal, SummaryModal } from "./insight-modals";
import {
  DocumentProcessingStatus,
  DocumentText,
  StudyDocument,
  Subject,
  deleteDocument,
  getDocumentText,
  getDocuments,
  reprocessDocument,
  uploadDocument,
} from "@/lib/api";

const MAX_UPLOAD_MB = 20;
const STATUS_STYLES: Record<DocumentProcessingStatus, string> = {
  pending: "bg-slate-100 text-slate-600",
  processing: "bg-amber-50 text-amber-700",
  completed: "bg-emerald-50 text-emerald-700",
  failed: "bg-rose-50 text-rose-700",
};

const STATUS_LABELS: Record<DocumentProcessingStatus, string> = {
  pending: "Queued",
  processing: "Extracting text…",
  completed: "Text extracted",
  failed: "Failed",
};

function formatBytes(bytes: number): string {
  if (bytes >= 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  if (bytes >= 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${bytes} B`;
}

type DocumentsPanelProps = {
  subjects: Subject[];
};

type InsightTarget = {
  kind: "document";
  id: number;
  title: string;
};

export function DocumentsPanel({ subjects }: DocumentsPanelProps) {
  const [documents, setDocuments] = useState<StudyDocument[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [subjectFilter, setSubjectFilter] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [subjectId, setSubjectId] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const [textPreview, setTextPreview] = useState<DocumentText | null>(null);
  const [loadingText, setLoadingText] = useState(false);
  const [insightTarget, setInsightTarget] = useState<InsightTarget | null>(null);
  const [insightMode, setInsightMode] = useState<"summary" | "quiz">("summary");
  const fileInputRef = useRef<HTMLInputElement>(null);

  const refresh = useCallback(async () => {
    setError(null);
    try {
      const result = await getDocuments({
        q: query.trim() || undefined,
        subject_id: subjectFilter ? Number(subjectFilter) : undefined,
        limit: 50,
      });
      setDocuments(result.items);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to load your PDFs.");
    } finally {
      setLoading(false);
    }
  }, [query, subjectFilter]);

  useEffect(() => {
    const timeout = window.setTimeout(() => void refresh(), query.trim() ? 250 : 0);
    return () => window.clearTimeout(timeout);
  }, [query, refresh]);

  // Keep polling while any document is still being processed.
  const processing = useMemo(
    () => documents.some((item) => item.processing_status === "pending" || item.processing_status === "processing"),
    [documents],
  );
  useEffect(() => {
    if (!processing) return;
    const interval = window.setInterval(() => void refresh(), 4000);
    return () => window.clearInterval(interval);
  }, [processing, refresh]);

  function pickFile(next: File | null) {
    setFormError(null);
    if (!next) {
      setFile(null);
      return;
    }
    if (next.type !== "application/pdf" && !next.name.toLowerCase().endsWith(".pdf")) {
      setFormError("Only PDF files can be uploaded here.");
      return;
    }
    if (next.size > MAX_UPLOAD_MB * 1024 * 1024) {
      setFormError(`That PDF is larger than the ${MAX_UPLOAD_MB} MB limit.`);
      return;
    }
    if (next.size === 0) {
      setFormError("That file is empty.");
      return;
    }
    setFile(next);
    if (!title.trim()) setTitle(next.name.replace(/\.pdf$/i, "").slice(0, 120));
  }

  async function handleUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file) {
      setFormError("Choose a PDF to upload first.");
      return;
    }
    setUploading(true);
    setFormError(null);
    try {
      const created = await uploadDocument({
        file,
        title: title.trim() || undefined,
        subject_id: subjectId ? Number(subjectId) : null,
      });
      setFile(null);
      setTitle("");
      if (fileInputRef.current) fileInputRef.current.value = "";
      if (created.processing_status === "failed") {
        setFormError(created.error_message || "Text could not be extracted from that PDF.");
      }
      await refresh();
    } catch (cause) {
      setFormError(cause instanceof Error ? cause.message : "Unable to upload that PDF.");
    } finally {
      setUploading(false);
    }
  }

  async function handleRetry(document: StudyDocument) {
    setBusyId(document.id);
    setError(null);
    try {
      const updated = await reprocessDocument(document.id);
      if (updated.processing_status === "failed") {
        setError(updated.error_message || "Extraction failed again for this PDF.");
      }
      await refresh();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to reprocess that PDF.");
    } finally {
      setBusyId(null);
    }
  }

  async function handleDelete(document: StudyDocument) {
    if (!window.confirm(`Delete “${document.title}”? Its summary and quizzes are deleted too.`)) return;
    setBusyId(document.id);
    setError(null);
    try {
      await deleteDocument(document.id);
      await refresh();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to delete that PDF.");
    } finally {
      setBusyId(null);
    }
  }

  async function openText(document: StudyDocument) {
    setLoadingText(true);
    setError(null);
    try {
      setTextPreview(await getDocumentText(document.id));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to load the extracted text.");
    } finally {
      setLoadingText(false);
    }
  }

  function openInsight(document: StudyDocument, mode: "summary" | "quiz") {
    setInsightTarget({ kind: "document", id: document.id, title: document.title });
    setInsightMode(mode);
  }

  return (
    <section className="space-y-6" aria-labelledby="documents-heading">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-indigo-600">Study library</p>
          <h1 id="documents-heading" className="mt-1 text-2xl font-bold tracking-tight text-slate-900">
            PDFs <span className="text-slate-400">({documents.length})</span>
          </h1>
          <p className="mt-1 text-sm text-slate-500">
            Upload lecture PDFs, then generate summaries and practice quizzes from their text.
          </p>
        </div>
      </div>

      <form
        onSubmit={handleUpload}
        className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
      >
        <div className="grid gap-4 md:grid-cols-[1.4fr_1fr_1fr_auto]">
          <div>
            <label htmlFor="document-file" className="block text-xs font-semibold text-slate-700">
              PDF file *
            </label>
            <input
              id="document-file"
              ref={fileInputRef}
              type="file"
              accept="application/pdf,.pdf"
              onChange={(event) => pickFile(event.target.files?.[0] ?? null)}
              className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700 outline-none file:mr-3 file:rounded-md file:border-0 file:bg-indigo-50 file:px-3 file:py-1.5 file:text-xs file:font-semibold file:text-indigo-700 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
            />
            <p className="mt-1 text-[10px] text-slate-400">
              Text-based PDFs only, up to {MAX_UPLOAD_MB} MB. Scanned/image-only PDFs are detected but OCR is not implemented — export a text-based PDF or add a text layer with a local OCR tool (OCRmyPDF with Tesseract) then re-upload. OCR is a planned future enhancement.
            </p>
          </div>
          <div>
            <label htmlFor="document-title" className="block text-xs font-semibold text-slate-700">
              Title
            </label>
            <input
              id="document-title"
              value={title}
              maxLength={180}
              onChange={(event) => setTitle(event.target.value)}
              placeholder="Unit 1 lecture notes"
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
            />
          </div>
          <div>
            <label htmlFor="document-subject" className="block text-xs font-semibold text-slate-700">
              Subject
            </label>
            <select
              id="document-subject"
              value={subjectId}
              onChange={(event) => setSubjectId(event.target.value)}
              className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
            >
              <option value="">General (no subject)</option>
              {subjects.map((subject) => (
                <option key={subject.id} value={subject.id}>
                  {subject.name}
                </option>
              ))}
            </select>
          </div>
          <div className="flex items-end">
            <Button type="submit" disabled={uploading || !file} className="w-full gap-2 md:w-auto">
              {uploading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />}
              {uploading ? "Uploading…" : "Upload PDF"}
            </Button>
          </div>
        </div>

        {file && !formError && (
          <p className="mt-3 flex items-center gap-2 text-xs text-slate-600">
            <FileText className="h-3.5 w-3.5 text-indigo-600" />
            {file.name} · {formatBytes(file.size)}
          </p>
        )}
        {formError && (
          <p role="alert" className="mt-3 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-xs text-rose-700">
            {formError}
          </p>
        )}
      </form>

      <div className="flex flex-col gap-3 sm:flex-row">
        <label className="relative block flex-1">
          <span className="sr-only">Search PDFs</span>
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search by title, filename, or subject…"
            className="w-full rounded-xl border border-slate-200 bg-white py-2.5 pl-10 pr-3 text-sm text-slate-900 outline-none transition focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100"
          />
        </label>
        <select
          value={subjectFilter}
          onChange={(event) => setSubjectFilter(event.target.value)}
          aria-label="Filter PDFs by subject"
          className="rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm text-slate-700 outline-none focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100"
        >
          <option value="">All subjects</option>
          {subjects.map((subject) => (
            <option key={subject.id} value={subject.id}>
              {subject.name}
            </option>
          ))}
        </select>
      </div>

      {error && (
        <div role="alert" className="flex items-start gap-2 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {loading ? (
        <div className="rounded-2xl border border-slate-200 bg-white px-6 py-12 text-center text-sm text-slate-500">
          Loading your PDFs…
        </div>
      ) : documents.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-slate-300 bg-white px-6 py-14 text-center">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-indigo-50 text-indigo-600">
            {query || subjectFilter ? <Search className="h-5 w-5" /> : <FileStack className="h-5 w-5" />}
          </div>
          <h2 className="mt-4 text-base font-semibold text-slate-900">
            {query || subjectFilter ? "No PDFs match this view" : "No PDFs uploaded yet"}
          </h2>
          <p className="mx-auto mt-1 max-w-md text-sm text-slate-500">
            {query || subjectFilter
              ? "Try a different search or clear the subject filter."
              : "Upload a lecture PDF above; StudyFlow extracts its text and unlocks summaries and quizzes."}
          </p>
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {documents.map((document) => {
            const ready = document.processing_status === "completed";
            const busy = busyId === document.id;
            return (
              <article
                key={document.id}
                className="flex flex-col rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex min-w-0 items-start gap-3">
                    <div className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-indigo-50 text-indigo-600">
                      <FileText className="h-4 w-4" />
                    </div>
                    <div className="min-w-0">
                      <h2 className="break-words text-sm font-semibold text-slate-900">{document.title}</h2>
                      <p className="mt-1 truncate text-[11px] text-slate-500">
                        {document.subject_name || "General"}
                        {document.semester_name ? ` · ${document.semester_name}` : ""}
                      </p>
                    </div>
                  </div>
                  <span
                    className={`shrink-0 rounded-full px-2.5 py-1 text-[10px] font-semibold ${STATUS_STYLES[document.processing_status]}`}
                  >
                    {STATUS_LABELS[document.processing_status]}
                  </span>
                </div>

                <dl className="mt-4 grid grid-cols-2 gap-2 text-[11px] text-slate-600">
                  <div className="rounded-lg bg-slate-50 px-2.5 py-1.5">
                    <dt className="text-slate-400">Pages</dt>
                    <dd className="font-semibold text-slate-700">{document.page_count || "—"}</dd>
                  </div>
                  <div className="rounded-lg bg-slate-50 px-2.5 py-1.5">
                    <dt className="text-slate-400">Words</dt>
                    <dd className="font-semibold text-slate-700">
                      {ready ? document.word_count.toLocaleString() : "—"}
                    </dd>
                  </div>
                  <div className="rounded-lg bg-slate-50 px-2.5 py-1.5">
                    <dt className="text-slate-400">File</dt>
                    <dd className="font-semibold text-slate-700">{formatBytes(document.file_size_bytes)}</dd>
                  </div>
                  <div className="rounded-lg bg-slate-50 px-2.5 py-1.5">
                    <dt className="text-slate-400">Generated</dt>
                    <dd className="font-semibold text-slate-700">
                      {document.summary_count} summary{document.summary_count === 1 ? "" : "s"} ·{" "}
                      {document.quiz_count} quiz{document.quiz_count === 1 ? "" : "zes"}
                    </dd>
                  </div>
                </dl>

                {document.error_message && (
                  <div className="mt-3 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-[11px] leading-5 text-rose-700">
                    <p>{document.error_message}</p>
                    {document.error_code === "scanned_pdf" && (
                      <p className="mt-1 text-[10px] text-rose-600">Tip: StudyFlow keeps failed files for you to fix and retry — it never marks a scanned PDF as “completed.” Re-export the lecture slides from PowerPoint/Google Docs as PDF, or run OCRmyPDF locally to add a text layer, then upload the converted file. Retry reprocesses the original stored bytes.</p>
                    )}
                  </div>
                )}

                <div className="mt-4 flex flex-wrap gap-2 border-t border-slate-100 pt-3">
                  <Button
                    type="button"
                    variant="ghost"
                    onClick={() => void openText(document)}
                    disabled={!ready || loadingText}
                    className="h-8 gap-1.5 bg-slate-50 px-2.5 text-[11px] text-slate-700"
                  >
                    <FileText className="h-3.5 w-3.5" /> Text
                  </Button>
                  <Button
                    type="button"
                    variant="ghost"
                    onClick={() => openInsight(document, "summary")}
                    disabled={!ready}
                    className="h-8 gap-1.5 bg-slate-50 px-2.5 text-[11px] text-slate-700"
                  >
                    <Sparkles className="h-3.5 w-3.5" />
                    {document.summary_count > 0 ? "View summary" : "Generate summary"}
                  </Button>
                  <Button
                    type="button"
                    variant="ghost"
                    onClick={() => openInsight(document, "quiz")}
                    disabled={!ready}
                    className="h-8 gap-1.5 bg-slate-50 px-2.5 text-[11px] text-slate-700"
                  >
                    <ClipboardList className="h-3.5 w-3.5" />
                    {document.quiz_count > 0 ? "Take quiz" : "Generate quiz"}
                  </Button>
                  {!ready && document.processing_status === "failed" && (
                    <Button
                      type="button"
                      variant="ghost"
                      onClick={() => void handleRetry(document)}
                      disabled={busy}
                      className="h-8 gap-1.5 bg-amber-50 px-2.5 text-[11px] text-amber-700"
                    >
                      {busy ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />}
                      Retry
                    </Button>
                  )}
                  <button
                    type="button"
                    onClick={() => void handleDelete(document)}
                    disabled={busy}
                    aria-label={`Delete ${document.title}`}
                    className="ml-auto rounded-lg p-2 text-slate-500 transition hover:bg-rose-50 hover:text-rose-600 disabled:opacity-50"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </article>
            );
          })}
        </div>
      )}

      {textPreview && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/40 p-4 backdrop-blur-sm">
          <section
            role="dialog"
            aria-modal="true"
            aria-labelledby="document-text-title"
            className="flex max-h-[95vh] w-full max-w-3xl flex-col overflow-hidden rounded-2xl bg-white shadow-2xl"
          >
            <div className="flex items-start justify-between gap-4 border-b border-slate-100 px-6 py-4">
              <div>
                <h2 id="document-text-title" className="text-lg font-bold text-slate-900">
                  Extracted text
                </h2>
                <p className="mt-1 text-xs text-slate-500">
                  {textPreview.title} · {textPreview.page_count} pages ·{" "}
                  {textPreview.extracted_chars.toLocaleString()} characters
                  {textPreview.text_truncated ? " (truncated for storage)" : ""}
                </p>
              </div>
              <button
                type="button"
                aria-label="Close extracted text"
                onClick={() => setTextPreview(null)}
                className="rounded-lg p-2 text-slate-400 hover:bg-slate-100 hover:text-slate-700"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
            <pre className="flex-1 overflow-y-auto whitespace-pre-wrap px-6 py-5 font-sans text-sm leading-7 text-slate-700">
              {textPreview.text ?? "No text available for this document."}
            </pre>
          </section>
        </div>
      )}

      {insightTarget && insightMode === "summary" && (
        <SummaryModal
          source={{ kind: "document", id: insightTarget.id }}
          sourceTitle={insightTarget.title}
          onClose={() => {
            setInsightTarget(null);
            void refresh();
          }}
        />
      )}
      {insightTarget && insightMode === "quiz" && (
        <QuizModal
          source={{ kind: "document", id: insightTarget.id }}
          sourceTitle={insightTarget.title}
          onClose={() => {
            setInsightTarget(null);
            void refresh();
          }}
        />
      )}
    </section>
  );
}
