"use client";

import { useCallback, useEffect, useState } from "react";
import { BarChart3, BookOpen, CheckCircle2, Clock, FileText, Layers, Target, TrendingUp, AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { AnalyticsResponse, getAnalytics } from "@/lib/api";

function ProgressBar({ percent, color = "bg-indigo-600" }: { percent: number; color?: string }) {
  const clamped = Math.max(0, Math.min(100, percent));
  return (
    <div className="h-2 w-full rounded-full bg-slate-100 overflow-hidden">
      <div className={`h-2 rounded-full ${color}`} style={{ width: `${clamped}%` }} />
    </div>
  );
}

function StatCard({ title, value, subtitle, icon, color }: { title: string; value: string; subtitle?: string; icon: React.ReactNode; color: string }) {
  return (
    <div className={`rounded-xl border p-4 ${color}`}>
      <div className="flex items-center justify-between">
        <p className="text-xs font-semibold uppercase tracking-wide opacity-70">{title}</p>
        <span className="opacity-70">{icon}</span>
      </div>
      <p className="mt-2 text-2xl font-bold">{value}</p>
      {subtitle && <p className="mt-1 text-xs opacity-70">{subtitle}</p>}
    </div>
  );
}

export function AnalyticsPanel() {
  const [data, setData] = useState<AnalyticsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await getAnalytics();
      setData(result);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to load analytics.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void refresh(); }, [refresh]);

  if (loading) return <div className="p-8 text-sm text-slate-600">Loading analytics…</div>;
  if (error) return <div role="alert" className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800">{error}</div>;
  if (!data) return <div className="p-8 text-sm text-slate-600">No data yet.</div>;

  const totalRecordedHours = data.study_time.recorded_hours_total;
  const estimatedHours = data.study_time.estimated_hours_total;

  return (
    <section className="space-y-6">
      <header className="rounded-2xl border border-slate-200 bg-gradient-to-br from-slate-50 to-white p-6">
        <Button variant="ghost" className="float-right border" onClick={() => void refresh()}>Refresh report</Button>
        <h1 className="flex items-center gap-2 text-xl font-bold text-slate-900"><BarChart3 className="h-5 w-5 text-indigo-600" /> Analytics & Progress Reports</h1>
        <p className="mt-1 text-sm text-slate-600">All numbers come from your actual records — no fabricated percentages. Empty datasets show “No data yet” correctly.</p>
        <p className="mt-1 text-xs text-slate-500">Generated at {new Date(data.generated_at).toLocaleString()} · Refresh to see latest.</p>
      </header>

      {/* Top stats */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard title="Topic Completion" value={`${data.topic_completion.completion_percent}%`} subtitle={`${data.topic_completion.completed} / ${data.topic_completion.total} topics`} icon={<Target className="h-4 w-4" />} color="bg-indigo-50 border-indigo-200 text-indigo-900" />
        <StatCard title="Quiz Average" value={data.quiz_average_score !== null ? `${data.quiz_average_score}%` : "No attempts"} subtitle={data.quiz_best_score !== null ? `Best: ${data.quiz_best_score}%` : "Take a quiz to see trend"} icon={<TrendingUp className="h-4 w-4" />} color="bg-violet-50 border-violet-200 text-violet-900" />
        <StatCard title="Recorded Study Time" value={`${totalRecordedHours}h`} subtitle={`${data.study_time.completed_sessions} completed sessions · ${data.study_time.recorded_seconds_total}s total`} icon={<Clock className="h-4 w-4" />} color="bg-teal-50 border-teal-200 text-teal-900" />
        <StatCard title="Pending Tasks" value={`${data.tasks.pending}`} subtitle={`Overdue: ${data.tasks.overdue} · Total: ${data.tasks.total}`} icon={<AlertTriangle className="h-4 w-4" />} color="bg-amber-50 border-amber-200 text-amber-900" />
      </div>

      {/* Topic completion breakdown */}
      <div className="rounded-2xl border bg-white p-5">
        <h2 className="font-semibold text-sm flex items-center gap-2"><Target className="h-4 w-4 text-indigo-600" /> Overall Topic Completion</h2>
        {data.topic_completion.total === 0 ? (
          <p className="mt-2 text-sm text-slate-500">No topics created yet. Add topics in the Topics tab to track completion.</p>
        ) : (
          <div className="mt-3 space-y-2">
            <div className="flex items-center justify-between text-xs text-slate-600">
              <span>Completed {data.topic_completion.completed} · In Progress {data.topic_completion.in_progress} · Pending {data.topic_completion.pending}</span>
              <span className="font-semibold">{data.topic_completion.completion_percent}%</span>
            </div>
            <ProgressBar percent={data.topic_completion.completion_percent} />
          </div>
        )}
      </div>

      {/* Subject-wise progress */}
      <div className="rounded-2xl border bg-white p-5">
        <h2 className="font-semibold text-sm flex items-center gap-2"><Layers className="h-4 w-4 text-indigo-600" /> Subject-wise Progress</h2>
        {data.subject_progress.length === 0 ? (
          <p className="mt-2 text-sm text-slate-500">No subjects yet. Create a subject to see per-subject progress.</p>
        ) : (
          <div className="mt-3 space-y-3">
            {data.subject_progress.map((s) => (
              <div key={s.subject_id} className="rounded-xl border bg-slate-50 p-3">
                <div className="flex items-center justify-between">
                  <p className="font-medium text-sm text-slate-900">{s.subject_name} {s.semester_name ? <span className="text-xs text-slate-500">· {s.semester_name}</span> : null}</p>
                  <span className="text-xs font-semibold text-indigo-700">{s.completion_percent}%</span>
                </div>
                <p className="text-xs text-slate-500">{s.completed_topics} / {s.total_topics} topics · {s.completed_hours}h manually/estimate-derived completed / {s.estimated_hours}h estimated</p>
                <div className="mt-2"><ProgressBar percent={s.completion_percent} /></div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Quiz history & trends */}
      <div className="rounded-2xl border bg-white p-5">
        <h2 className="font-semibold text-sm flex items-center gap-2"><TrendingUp className="h-4 w-4 text-violet-600" /> Quiz Attempt History & Score Trends</h2>
        {data.quiz_history.length === 0 ? (
          <p className="mt-2 text-sm text-slate-500">No quiz attempts yet. Generate a quiz from a note or PDF and submit an attempt to see your trend.</p>
        ) : (
          <div className="mt-3 space-y-2">
            <div className="flex flex-wrap gap-2 text-xs">
              <span className="rounded-full bg-violet-50 border border-violet-200 px-2 py-0.5">Average: {data.quiz_average_score}%</span>
              <span className="rounded-full bg-emerald-50 border border-emerald-200 px-2 py-0.5 text-emerald-800">Best: {data.quiz_best_score}%</span>
              <span className="rounded-full bg-white border px-2 py-0.5">{data.quiz_history.length} attempts (latest 30)</span>
            </div>
            <div className="mt-2 max-h-[260px] overflow-y-auto divide-y text-sm">
              {data.quiz_history.map((a, idx) => (
                <div key={idx} className="flex items-center justify-between py-2">
                  <div>
                    <p className="font-medium text-slate-900">{a.quiz_title}</p>
                    <p className="text-xs text-slate-500">{new Date(a.submitted_at).toLocaleDateString()} · {a.date}</p>
                  </div>
                  <span className={`rounded-full border px-3 py-1 text-xs font-semibold ${a.score_percent >= 70 ? "bg-emerald-50 border-emerald-200 text-emerald-700" : a.score_percent >= 50 ? "bg-amber-50 border-amber-200 text-amber-800" : "bg-red-50 border-red-200 text-red-700"}`}>{a.score_percent}%</span>
                </div>
              ))}
            </div>
            <p className="text-xs text-slate-500">Scores are practice results, not proof of mastery. Use them as revision signals alongside topic completion.</p>
          </div>
        )}
      </div>

      {/* Exams */}
      <div className="grid gap-4 md:grid-cols-2">
        <div className="rounded-2xl border bg-white p-5">
          <h2 className="font-semibold text-sm flex items-center gap-2"><CheckCircle2 className="h-4 w-4 text-emerald-600" /> Upcoming Exams</h2>
          {data.upcoming_exams.length === 0 ? (
            <p className="mt-2 text-sm text-slate-500">No upcoming exams. Schedule an exam to see countdowns.</p>
          ) : (
            <div className="mt-3 space-y-2">
              {data.upcoming_exams.map((e) => (
                <div key={e.id} className="rounded-xl border bg-slate-50 p-3 flex items-center justify-between">
                  <div>
                    <p className="font-medium text-sm text-slate-900">{e.title}</p>
                    <p className="text-xs text-slate-500">{e.subject_name || "No subject"} · {e.exam_date} · {e.days_remaining !== null ? `${e.days_remaining} days remaining` : e.status}</p>
                  </div>
                  <span className="rounded-full bg-indigo-50 border border-indigo-200 px-2 py-0.5 text-xs text-indigo-700">{e.status}</span>
                </div>
              ))}
            </div>
          )}
        </div>
        <div className="rounded-2xl border bg-white p-5">
          <h2 className="font-semibold text-sm flex items-center gap-2"><FileText className="h-4 w-4 text-slate-600" /> Completed Exams</h2>
          {data.completed_exams.length === 0 ? (
            <p className="mt-2 text-sm text-slate-500">No completed exams yet.</p>
          ) : (
            <div className="mt-3 space-y-2">
              {data.completed_exams.map((e) => (
                <div key={e.id} className="rounded-xl border bg-slate-50 p-3 flex items-center justify-between">
                  <div>
                    <p className="font-medium text-sm text-slate-900">{e.title}</p>
                    <p className="text-xs text-slate-500">{e.subject_name || "No subject"} · {e.exam_date}</p>
                  </div>
                  <span className="rounded-full bg-slate-100 border px-2 py-0.5 text-xs">{e.status}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Estimated vs recorded study time */}
      <div className="rounded-2xl border bg-white p-5">
        <h2 className="font-semibold text-sm flex items-center gap-2"><Clock className="h-4 w-4 text-teal-600" /> Estimated vs Recorded Study Time</h2>
        <div className="mt-3 grid gap-4 sm:grid-cols-3 text-sm">
          <div className="rounded-xl bg-indigo-50 border border-indigo-200 p-3 text-center">
            <p className="text-xs font-semibold uppercase tracking-wide text-indigo-700">Estimated</p>
            <p className="mt-1 text-xl font-bold text-indigo-900">{data.study_time.estimated_hours_total}h</p>
            <p className="text-xs text-slate-600">Sum of topic estimated_hours</p>
          </div>
          <div className="rounded-xl bg-teal-50 border border-teal-200 p-3 text-center">
            <p className="text-xs font-semibold uppercase tracking-wide text-teal-700">Recorded</p>
            <p className="mt-1 text-xl font-bold text-teal-900">{data.study_time.recorded_hours_total}h</p>
            <p className="text-xs text-slate-600">{data.study_time.recorded_seconds_total}s · {data.study_time.completed_sessions} sessions</p>
          </div>
          <div className="rounded-xl bg-white border p-3 text-center">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-600">Difference</p>
            <p className="mt-1 text-xl font-bold text-slate-900">{(data.study_time.recorded_hours_total - data.study_time.estimated_hours_total).toFixed(2)}h</p>
            <p className="text-xs text-slate-500">Recorded − Estimated (negative = fewer recorded hours than estimated)</p>
          </div>
        </div>
        <p className="mt-2 text-xs text-slate-500">Estimated hours are manual topic estimates; recorded hours are measured via Start → Pause/Finish study sessions. They are displayed separately, not merged.</p>
      </div>

      {/* Pending / overdue / completed tasks */}
      <div className="rounded-2xl border bg-white p-5">
        <h2 className="font-semibold text-sm flex items-center gap-2"><BookOpen className="h-4 w-4 text-amber-600" /> Study Tasks Overview</h2>
        {data.tasks.total === 0 ? (
          <p className="mt-2 text-sm text-slate-500">No study tasks yet. Create a task in the Tasks tab to see pending/overdue/completed breakdown.</p>
        ) : (
          <div className="mt-3 grid gap-3 sm:grid-cols-4 text-center text-sm">
            <div className="rounded-xl bg-slate-50 border p-3"><p className="text-xs text-slate-500">Total</p><p className="text-lg font-bold">{data.tasks.total}</p></div>
            <div className="rounded-xl bg-amber-50 border border-amber-200 p-3"><p className="text-xs text-amber-800">Pending</p><p className="text-lg font-bold text-amber-900">{data.tasks.pending}</p></div>
            <div className="rounded-xl bg-red-50 border border-red-200 p-3"><p className="text-xs text-red-700">Overdue</p><p className="text-lg font-bold text-red-800">{data.tasks.overdue}</p></div>
            <div className="rounded-xl bg-emerald-50 border border-emerald-200 p-3"><p className="text-xs text-emerald-700">Completed</p><p className="text-lg font-bold text-emerald-900">{data.tasks.completed}</p></div>
            <div className="rounded-xl bg-indigo-50 border border-indigo-200 p-3"><p className="text-xs text-indigo-700">In Progress</p><p className="text-lg font-bold text-indigo-900">{data.tasks.in_progress}</p></div>
          </div>
        )}
      </div>

      {/* Flashcard review statistics */}
      <div className="rounded-2xl border bg-white p-5">
        <h2 className="font-semibold text-sm flex items-center gap-2"><Layers className="h-4 w-4 text-violet-600" /> Flashcard Review Statistics</h2>
        {data.flashcards.total === 0 ? (
          <p className="mt-2 text-sm text-slate-500">No flashcards yet. Create flashcards to see review statistics.</p>
        ) : (
          <div className="mt-3 space-y-3">
            <div className="flex items-center justify-between text-xs text-slate-600"><span>Known {data.flashcards.known} · Needs revision {data.flashcards.needs_revision}</span><span>{data.flashcards.total} total</span></div>
            <ProgressBar percent={data.flashcards.total ? (data.flashcards.known / data.flashcards.total) * 100 : 0} color="bg-violet-600" />
            <div className="grid gap-3 sm:grid-cols-3 text-center text-sm">
              <div className="rounded-xl bg-slate-50 border p-3"><p className="text-xs text-slate-500">Total</p><p className="text-lg font-bold">{data.flashcards.total}</p></div>
              <div className="rounded-xl bg-emerald-50 border border-emerald-200 p-3"><p className="text-xs text-emerald-700">Known</p><p className="text-lg font-bold text-emerald-900">{data.flashcards.known}</p></div>
              <div className="rounded-xl bg-amber-50 border border-amber-200 p-3"><p className="text-xs text-amber-800">Needs revision</p><p className="text-lg font-bold text-amber-900">{data.flashcards.needs_revision}</p></div>
            </div>
          </div>
        )}
      </div>

      <p className="text-xs text-slate-500 text-center">Tip: All metrics refresh from the database. If you create topics, take quizzes, or finish study sessions, reload this view to see updated progress.</p>
    </section>
  );
}
