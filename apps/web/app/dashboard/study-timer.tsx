"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Pause, Play, Square, Trash2, History, Timer } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  StudySession,
  Subject,
  Topic,
  getActiveStudySession,
  getStudySessions,
  startStudySession,
  pauseStudySession,
  resumeStudySession,
  finishStudySession,
  cancelStudySession,
} from "@/lib/api";

type Props = { subjects: Subject[]; topics: Topic[] };

function formatSeconds(total: number): string {
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  if (h > 0) return `${h}h ${String(m).padStart(2, "0")}m ${String(s).padStart(2, "0")}s`;
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

export function StudyTimerPanel({ subjects, topics }: Props) {
  const [active, setActive] = useState<StudySession | null>(null);
  const [recent, setRecent] = useState<StudySession[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [selectedSubject, setSelectedSubject] = useState("");
  const [selectedTopic, setSelectedTopic] = useState("");
  const [tick, setTick] = useState(0);
  const tickRef = useRef<number | null>(null);
  const sampledAt = useRef(0);

  const refresh = useCallback(async () => {
    setError(null);
    try {
      const [a, r] = await Promise.all([getActiveStudySession(), getStudySessions(20)]);
      sampledAt.current = performance.now();
      setActive(a);
      setRecent(r);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to load study sessions.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void refresh(); }, [refresh]);

  // Live ticking for active session
  useEffect(() => {
    if (active?.status === "active") {
      tickRef.current = window.setInterval(() => setTick((t) => t + 1), 1000);
      return () => { if (tickRef.current) window.clearInterval(tickRef.current); };
    } else {
      if (tickRef.current) window.clearInterval(tickRef.current);
      return;
    }
  }, [active?.status, active?.id]);

  // Also poll every 10s to recover from reload / stale elapsed
  useEffect(() => {
    const id = window.setInterval(() => void refresh(), 10000);
    return () => window.clearInterval(id);
  }, [refresh]);

  const preciseElapsed = useMemo(() => {
    if (!active) return 0;
    const sinceSample = active.status === "active"
      ? Math.max(0, Math.floor((performance.now() - sampledAt.current) / 1000)) : 0;
    return active.elapsed_seconds + sinceSample;
  }, [active, tick]);

  async function handleStart() {
    setBusy(true);
    setError(null);
    try {
      const sess = await startStudySession({
        subject_id: Number(selectedSubject),
        topic_id: selectedTopic ? Number(selectedTopic) : null,
      });
      setActive(sess);
      await refresh();
      setTick(0);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not start session.");
    } finally {
      setBusy(false);
    }
  }

  async function handlePause() {
    if (!active) return;
    setBusy(true);
    try {
      const sess = await pauseStudySession(active.id);
      setActive(sess);
      await refresh();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not pause.");
    } finally {
      setBusy(false);
    }
  }

  async function handleResume() {
    if (!active) return;
    setBusy(true);
    try {
      const sess = await resumeStudySession(active.id);
      setActive(sess);
      await refresh();
      setTick(0);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not resume.");
    } finally {
      setBusy(false);
    }
  }

  async function handleFinish() {
    if (!active) return;
    setBusy(true);
    try {
      await finishStudySession(active.id);
      setActive(null);
      await refresh();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not finish.");
    } finally {
      setBusy(false);
    }
  }

  async function handleCancel() {
    if (!active) return;
    if (!window.confirm("Cancel this session? Its time will still be counted as cancelled, but not as completed study time.")) return;
    setBusy(true);
    try {
      await cancelStudySession(active.id);
      setActive(null);
      await refresh();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not cancel.");
    } finally {
      setBusy(false);
    }
  }

  const fieldCls = "w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500";
  const totalRecorded = recent.filter((s) => s.status === "completed" && s.duration_seconds).reduce((acc, s) => acc + (s.duration_seconds || 0), 0);

  if (loading) return <div className="p-8 text-sm text-slate-600">Loading study timer…</div>;

  return (
    <section className="space-y-6">
      <header className="rounded-2xl border border-teal-100 bg-gradient-to-br from-teal-50 to-white p-6">
        <h1 className="text-xl font-bold text-slate-900">Study-Time Tracking</h1>
        <p className="mt-1 text-sm text-slate-600">
          Start a timed session for a subject/topic. Pause when you take a break — paused time is not counted. Only completed sessions contribute to recorded study time shown on analytics. Overlapping sessions are prevented.
        </p>
        <div className="mt-4 flex flex-wrap gap-2 text-xs">
          <span className="rounded-full bg-white border px-3 py-1">Completed sessions (latest 20): {recent.filter((s) => s.status === "completed").length}</span>
          <span className="rounded-full bg-teal-50 border border-teal-200 px-3 py-1 text-teal-800">Recorded (latest 20): {formatSeconds(totalRecorded)} ({(totalRecorded / 3600).toFixed(2)}h)</span>
          <span className="rounded-full bg-white border px-3 py-1">Estimated total (topics): see Analytics</span>
        </div>
      </header>

      {error && <p role="alert" className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-800">{error}</p>}

      {/* Active session card */}
      <div className="rounded-2xl border bg-white p-6">
        <h2 className="flex items-center gap-2 font-semibold text-slate-900"><Timer className="h-5 w-5 text-teal-600" /> Current Session</h2>
        {active ? (
          <div className="mt-4 space-y-4">
            <div className="rounded-xl bg-slate-900 text-white p-6 text-center">
              <p className="text-xs uppercase tracking-widest text-slate-400">Elapsed — {active.status}</p>
              <p className="mt-2 font-mono text-4xl font-bold tracking-tight">{formatSeconds(preciseElapsed)}</p>
              <p className="mt-1 text-xs text-slate-300">
                {active.subject_name || "No subject"} {active.topic_name ? `· ${active.topic_name}` : ""} · since {new Date(active.created_at).toLocaleString()}
              </p>
              <p className="mt-1 text-xs text-slate-400">Backend validates elapsed from persisted timestamps; the timer continues until paused, finished, or cancelled, including while this page is closed. Recover it here after a reload. Paused time is not counted.</p>
            </div>
            <div className="flex flex-wrap gap-2 justify-center">
              {active.status === "active" && (
                <Button onClick={handlePause} disabled={busy} variant="ghost" className="border gap-1.5"><Pause className="h-4 w-4" /> Pause</Button>
              )}
              {active.status === "paused" && (
                <Button onClick={handleResume} disabled={busy} className="gap-1.5 bg-teal-600 hover:bg-teal-700"><Play className="h-4 w-4" /> Resume</Button>
              )}
              <Button onClick={handleFinish} disabled={busy} className="gap-1.5 bg-indigo-600 hover:bg-indigo-700"><Square className="h-4 w-4" /> Finish & Save</Button>
              <Button onClick={handleCancel} disabled={busy} variant="ghost" className="border text-red-600"><Trash2 className="h-4 w-4" /> Cancel</Button>
            </div>
          </div>
        ) : (
          <div className="mt-4 space-y-4">
            <div className="rounded-xl border-2 border-dashed bg-slate-50 p-6 text-center">
              <p className="text-sm text-slate-600">No active session. Start one to begin tracking actual study time.</p>
              <p className="mt-1 text-xs text-slate-500">This is distinct from estimated hours on topics — recorded time is measured, not estimated.</p>
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <div>
                <label className="block text-xs font-medium text-slate-700">Subject (required)</label>
                <select value={selectedSubject} onChange={(e) => { setSelectedSubject(e.target.value); setSelectedTopic(""); }} className={fieldCls}>
                  <option value="">None</option>
                  {subjects.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-700">Topic (optional)</label>
                <select value={selectedTopic} onChange={(e) => setSelectedTopic(e.target.value)} className={fieldCls}>
                  <option value="">None</option>
                  {topics.filter((t) => !selectedSubject || t.subject_id === Number(selectedSubject)).map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
                </select>
              </div>
            </div>
            <Button onClick={handleStart} disabled={busy || !selectedSubject} className="w-full gap-1.5"><Play className="h-4 w-4" /> Start Session</Button>
          </div>
        )}
      </div>

      {/* Recent sessions */}
      <div className="rounded-2xl border bg-white p-5">
        <h2 className="flex items-center gap-2 font-semibold text-sm"><History className="h-4 w-4" /> Recent Sessions</h2>
        {recent.length === 0 ? (
          <p className="mt-2 text-sm text-slate-500">No sessions yet. Start a session and finish it to see history.</p>
        ) : (
          <div className="mt-3 divide-y">
            {recent.map((s) => (
              <div key={s.id} className="flex flex-wrap items-center justify-between gap-2 py-3 text-sm">
                <div>
                  <p className="font-medium text-slate-900">{s.subject_name || "No subject"} {s.topic_name ? `· ${s.topic_name}` : ""}</p>
                  <p className="text-xs text-slate-500">{new Date(s.created_at).toLocaleString()} · {s.status} · {s.duration_seconds ? formatSeconds(s.duration_seconds) : formatSeconds(s.elapsed_seconds)}</p>
                </div>
                <span className={`rounded-full border px-2 py-0.5 text-xs ${s.status === "completed" ? "bg-emerald-50 border-emerald-200 text-emerald-700" : s.status === "active" ? "bg-teal-50 border-teal-200 text-teal-800" : s.status === "paused" ? "bg-amber-50 border-amber-200 text-amber-800" : "bg-slate-50 border-slate-200 text-slate-600"}`}>{s.status}</span>
              </div>
            ))}
          </div>
        )}
        <p className="mt-3 text-xs text-slate-500">Only <strong>completed</strong> sessions count toward recorded study time in Analytics. Paused/cancelled/active sessions do not inflate totals.</p>
      </div>
    </section>
  );
}
