"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Flame,
  Loader2,
  BookOpen,
  CheckCircle2,
  Clock,
  Pause,
  Play,
  RefreshCw,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Exam,
  SprintPlan,
  SprintResource,
  SprintRecommendation,
  createSprint,
  getSprints,
  getSprintPlan,
  getSprintRecommendations,
  recalculateSprint,
  setSprintStatus,
  updateSprintTask,
} from "@/lib/api";
import { SummaryModal, QuizModal } from "./insight-modals";

export function SprintPanel({
  exams,
  onTopicsChanged,
}: {
  exams: Exam[];
  onTopicsChanged: () => void;
}) {
  const [sprints, setSprints] = useState<SprintPlan[]>([]);
  const [plan, setPlan] = useState<SprintPlan | null>(null);
  const [recommendations, setRecommendations] = useState<
    SprintRecommendation[]
  >([]);
  const [examId, setExamId] = useState("");
  const [minutes, setMinutes] = useState(90);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState("");
  const [material, setMaterial] = useState<{
    resource: SprintResource;
    mode: "summary" | "quiz" | "note";
  } | null>(null);
  const date = new Date();
  const localDate = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
  const upcoming = exams.filter(
    (e) => e.status === "Upcoming" && e.exam_date >= localDate,
  );

  const savePlan = useCallback((next: SprintPlan) => {
    setPlan(next);
    setMinutes(next.budget_minutes);
    setSprints((current) => [next, ...current.filter((s) => s.id !== next.id)]);
  }, []);

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const [saved, recommended] = await Promise.all([
          getSprints(),
          getSprintRecommendations(),
        ]);
        if (!active) return;
        setSprints(saved);
        setRecommendations(recommended);
        const open = saved.find((s) => ["active", "paused"].includes(s.status));
        if (open) {
          const daily = await getSprintPlan(open.id);
          if (active) savePlan(daily);
        }
      } catch (cause) {
        if (active)
          setError(
            cause instanceof Error ? cause.message : "Could not load sprints",
          );
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, [savePlan]);

  async function run(action: () => Promise<SprintPlan>, message: string) {
    setBusy(true);
    setError(null);
    setNotice("");
    try {
      savePlan(await action());
      setNotice(message);
    } catch (cause) {
      setError(
        cause instanceof Error ? cause.message : "Could not update sprint",
      );
    } finally {
      setBusy(false);
    }
  }

  async function closeMaterial() {
    const wasQuiz = material?.mode === "quiz";
    setMaterial(null);
    if (!plan) return;
    // A quiz may have changed the latest performance signal; preserve completed rows.
    await run(
      () =>
        wasQuiz && plan.status === "active" && plan.days_remaining >= 0
          ? recalculateSprint(plan.id)
          : getSprintPlan(plan.id),
      wasQuiz
        ? "Quiz signals refreshed. Completed work was kept."
        : "Plan refreshed.",
    );
  }

  const canEdit = plan?.status === "active" && plan.days_remaining >= 0;
  const field =
    "w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-orange-500";
  if (loading)
    return (
      <div className="flex gap-2 p-8" role="status">
        <Loader2 className="h-5 w-5 animate-spin" />
        Loading Sprint Mode…
      </div>
    );

  return (
    <section className="space-y-6">
      <header className="rounded-2xl border border-orange-200 bg-gradient-to-br from-orange-50 via-amber-50 to-white p-6">
        <div className="flex items-center gap-2 text-orange-800">
          <Flame className="h-6 w-6" />
          <h1 className="text-2xl font-bold">Sprint Mode</h1>
        </div>
        <p className="mt-2 text-sm text-slate-700">
          A focused, realistic plan for one exam. You choose when to start,
          pause, or finish.
        </p>
        {recommendations.length > 0 && (
          <div className="mt-4 rounded-xl bg-white/80 p-3 text-sm text-orange-900">
            <strong>Approaching exams:</strong>{" "}
            {recommendations
              .map((r) => `${r.title} (${r.days_remaining} days)`)
              .join(" · ")}
            . Select an exam below to opt in.
          </div>
        )}
      </header>
      {error && (
        <p
          role="alert"
          className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800"
        >
          {error}
        </p>
      )}
      <p aria-live="polite" className="text-sm text-emerald-800">
        {busy ? "Saving your plan…" : notice}
      </p>

      <div className="grid gap-4 lg:grid-cols-2">
        <form
          className="space-y-3 rounded-2xl border bg-white p-5"
          onSubmit={(event) => {
            event.preventDefault();
            void run(
              () =>
                createSprint(
                  Number(examId),
                  minutes,
                  Intl.DateTimeFormat().resolvedOptions().timeZone,
                ),
              "Sprint activated. Let's focus.",
            );
          }}
        >
          <h2 className="font-bold">Prepare for an exam</h2>
          <label className="block text-sm">
            Upcoming exam
            <select
              aria-label="Upcoming exam"
              className={field}
              required
              value={examId}
              disabled={busy}
              onChange={(e) => setExamId(e.target.value)}
            >
              <option value="">Choose an exam</option>
              {upcoming
                .filter((e) => !sprints.some((s) => s.exam_id === e.id))
                .map((e) => (
                  <option key={e.id} value={e.id}>
                    {e.title} — {e.exam_date}
                  </option>
                ))}
            </select>
          </label>
          <label className="block text-sm">
            Daily study time (minutes)
            <input
              aria-label="Daily study time"
              className={field}
              type="number"
              min={1}
              max={720}
              required
              value={minutes}
              disabled={busy}
              onChange={(e) => setMinutes(Number(e.target.value))}
            />
          </label>
          <Button
            type="submit"
            disabled={busy || !examId}
            className="bg-orange-700 hover:bg-orange-800"
          >
            Activate Sprint
          </Button>
          {!upcoming.length && (
            <p className="text-sm text-slate-600">
              Create an upcoming exam in the Exams tab first.
            </p>
          )}
        </form>
        <div className="space-y-3 rounded-2xl border bg-white p-5">
          <h2 className="font-bold">Your sprints & history</h2>
          <label className="block text-sm">
            Selected sprint
            <select
              aria-label="Selected sprint"
              className={field}
              disabled={busy}
              value={plan?.id ?? ""}
              onChange={(e) => {
                if (e.target.value)
                  void run(
                    () => getSprintPlan(Number(e.target.value)),
                    "Sprint loaded.",
                  );
              }}
            >
              <option value="">Select a saved sprint</option>
              {sprints.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.exam_title} — {s.status}
                </option>
              ))}
            </select>
          </label>
          <p className="text-sm text-slate-600">
            Plans use your timezone. Time spent and quiz scores are useful
            signals, not automatic proof of mastery.
          </p>
        </div>
      </div>

      {plan && (
        <>
          <div className="rounded-2xl border border-orange-200 bg-white p-6">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <p className="text-sm font-semibold uppercase tracking-wide text-orange-800">
                  {plan.status} · {plan.subject_name}
                </p>
                <h2 className="mt-1 text-xl font-bold">{plan.exam_title}</h2>
                <p className="mt-1 text-sm text-slate-600">
                  {plan.exam_date} ·{" "}
                  {plan.days_remaining < 0
                    ? "Exam date passed"
                    : plan.days_remaining === 0
                      ? "Exam today"
                      : `${plan.days_remaining} days remaining`}
                </p>
              </div>
              <div className="flex flex-wrap gap-2">
                {["active", "paused"].includes(plan.status) && (
                  <>
                    <Button
                      variant="ghost"
                      className="border border-slate-300"
                      disabled={busy}
                      onClick={() =>
                        void run(
                          () =>
                            setSprintStatus(
                              plan.id,
                              plan.status === "paused" ? "active" : "paused",
                            ),
                          plan.status === "paused"
                            ? "Sprint resumed."
                            : "Sprint paused.",
                        )
                      }
                    >
                      {plan.status === "paused" ? (
                        <Play className="mr-1 h-4 w-4" />
                      ) : (
                        <Pause className="mr-1 h-4 w-4" />
                      )}
                      {plan.status === "paused" ? "Resume" : "Pause"}
                    </Button>
                    <Button
                      variant="ghost"
                      className="border border-slate-300"
                      disabled={busy}
                      onClick={() => {
                        if (confirm("Finish this sprint and keep its history?"))
                          void run(
                            () => setSprintStatus(plan.id, "completed"),
                            "Sprint completed. History saved.",
                          );
                      }}
                    >
                      Finish sprint
                    </Button>
                    <Button
                      variant="ghost"
                      disabled={busy}
                      onClick={() => {
                        if (
                          confirm(
                            "Exit this sprint? Completed work will remain in history.",
                          )
                        )
                          void run(
                            () => setSprintStatus(plan.id, "cancelled"),
                            "Sprint exited. History saved.",
                          );
                      }}
                    >
                      Exit sprint
                    </Button>
                  </>
                )}
              </div>
            </div>
            <div className="mt-5 flex justify-between text-sm">
              <span>Sprint task completion (all planned days)</span>
              <strong>{plan.progress_percent}%</strong>
            </div>
            <div
              role="progressbar"
              aria-label="Sprint task completion"
              aria-valuenow={plan.progress_percent}
              aria-valuemin={0}
              aria-valuemax={100}
              className="mt-2 h-2 overflow-hidden rounded-full bg-orange-100"
            >
              <div
                className="h-full bg-orange-600 motion-safe:transition-all motion-safe:duration-300"
                style={{ width: `${plan.progress_percent}%` }}
              />
            </div>
            <p className="mt-2 text-xs text-slate-600">
              {plan.completed_tasks}/{plan.total_tasks} saved tasks complete.
              This is not a prediction of exam readiness.
            </p>
            <div className="mt-5 grid grid-cols-2 gap-3 md:grid-cols-4">
              {[
                ["Tasks today", `${plan.completed_today}/${plan.tasks.length}`],
                ["Remaining today", `${plan.remaining_minutes} min`],
                [
                  "Topics completed",
                  `${plan.topics_completed}/${plan.topics_total}`,
                ],
                [
                  "Recent quiz average",
                  plan.quiz_average === null
                    ? "No attempts yet"
                    : `${plan.quiz_average}%`,
                ],
              ].map(([label, value]) => (
                <div key={label} className="rounded-xl bg-amber-50 p-3">
                  <p className="text-xs text-slate-600">{label}</p>
                  <p className="mt-1 font-bold text-slate-900">{value}</p>
                </div>
              ))}
            </div>
          </div>
          {plan.warnings.map((w) => (
            <p
              key={w}
              className="rounded-xl border border-amber-300 bg-amber-50 p-4 text-sm text-amber-950"
            >
              {w}
            </p>
          ))}
          <div className="grid gap-6 lg:grid-cols-[2fr_1fr]">
            <div className="space-y-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <h2 className="text-lg font-bold">
                  Today’s Focus{" "}
                  <span className="text-sm font-normal text-slate-500">
                    {plan.plan_date}
                  </span>
                </h2>
                <Button
                  variant="ghost"
                  className="border border-slate-300"
                  disabled={busy || !canEdit || minutes < 1 || minutes > 720}
                  onClick={() =>
                    void run(
                      () => recalculateSprint(plan.id, minutes),
                      "Plan recalculated. Completed tasks preserved.",
                    )
                  }
                >
                  <RefreshCw className="mr-2 h-4 w-4" />
                  Apply budget & recalculate
                </Button>
              </div>
              <p className="text-xs text-slate-600">
                {plan.budget_minutes} min planned budget · {plan.timezone}.
                Change the minutes above, then apply. Finishing a study block
                does not mark a topic learned unless you choose that explicitly.
              </p>
              {!plan.tasks.length && (
                <p className="rounded-xl border bg-white p-5 text-sm">
                  No tasks for today. Resume an upcoming sprint and reload its
                  daily plan to begin.
                </p>
              )}
              {plan.tasks.map((task) => (
                <article
                  key={task.id}
                  className={`rounded-2xl border bg-white p-5 motion-safe:transition-colors ${task.completed ? "border-emerald-200" : "border-orange-200"}`}
                >
                  <div className="flex items-start gap-3">
                    <input
                      aria-label={`Complete ${task.title}`}
                      type="checkbox"
                      checked={task.completed}
                      disabled={busy || !canEdit}
                      className="mt-1 h-5 w-5 accent-orange-700"
                      onChange={(e) =>
                        void run(
                          () =>
                            updateSprintTask(
                              plan.id,
                              task.id,
                              e.target.checked,
                            ),
                          "Task updated.",
                        )
                      }
                    />
                    <div className="min-w-0 flex-1">
                      <h3
                        className={`font-semibold ${task.completed ? "text-emerald-800" : "text-slate-900"}`}
                      >
                        {task.title}
                      </h3>
                      <p className="mt-1 flex items-center gap-1 text-xs text-orange-900">
                        <Clock className="h-3 w-3" />
                        {task.minutes} min · {task.kind} · priority{" "}
                        {task.priority}
                      </p>
                      <p className="mt-2 text-sm text-slate-600">
                        {task.reason}
                      </p>
                      {task.topic_id && task.completed && canEdit && (
                        <button
                          type="button"
                          className="mt-3 text-sm font-semibold text-emerald-800 underline"
                          disabled={busy}
                          onClick={() => {
                            void run(async () => {
                              const next = await updateSprintTask(
                                plan.id,
                                task.id,
                                true,
                                true,
                              );
                              onTopicsChanged();
                              return next;
                            }, "Topic marked completed.");
                          }}
                        >
                          Also mark topic completed
                        </button>
                      )}
                    </div>
                    {task.completed && (
                      <CheckCircle2 className="h-5 w-5 shrink-0 text-emerald-700" />
                    )}
                  </div>
                </article>
              ))}
            </div>
            <aside className="space-y-5">
              <section className="rounded-2xl border bg-white p-5">
                <h2 className="font-bold">Pending topics</h2>
                <p className="mb-3 text-xs text-slate-600">
                  Priority order; work that remains beyond today is not hidden.
                </p>
                {plan.pending_topics.length ? (
                  plan.pending_topics.map((t) => (
                    <div key={t.id} className="border-t py-3 text-sm">
                      <strong>{t.name}</strong>
                      <p className="text-xs text-slate-600">
                        {t.remaining_minutes} estimated min left · priority{" "}
                        {t.score}
                      </p>
                      <p className="mt-1 text-xs text-slate-600">{t.reason}</p>
                    </div>
                  ))
                ) : (
                  <p className="text-sm text-slate-600">
                    No incomplete topics. Focus on recall and revision.
                  </p>
                )}
              </section>
              <section className="rounded-2xl border bg-white p-5">
                <h2 className="font-bold">Revision signals</h2>
                <p className="mt-2 text-sm text-slate-600">
                  {plan.quiz_attempt_count} saved attempts · latest 3 used for
                  recommendations.
                </p>
                {plan.revision_topics.length ? (
                  plan.revision_topics.map((t) => (
                    <p key={t.id} className="mt-2 text-sm text-red-800">
                      {t.name}: {t.reason}
                    </p>
                  ))
                ) : (
                  <p className="mt-2 text-sm text-slate-600">
                    No low-score signal yet. Continue reviewing; this does not
                    establish mastery.
                  </p>
                )}
              </section>
            </aside>
          </div>
          <section className="rounded-2xl border bg-white p-5">
            <h2 className="flex items-center gap-2 font-bold">
              <BookOpen className="h-5 w-5 text-orange-700" />
              Subject study materials
            </h2>
            <p className="mt-1 text-xs text-slate-600">
              Only your selected subject’s materials. PDFs are subject-level
              resources, not automatically mapped to a topic.
            </p>
            <div className="mt-4 grid gap-3 md:grid-cols-2">
              {plan.resources.map((resource) => (
                <article
                  key={`${resource.kind}-${resource.id}`}
                  className="rounded-xl border p-4"
                >
                  <h3 className="font-semibold">{resource.title}</h3>
                  <p className="mb-3 text-xs text-slate-500">
                    {resource.kind} ·{" "}
                    {resource.has_summary
                      ? "Saved summary available"
                      : "Summary can be generated"}
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {resource.kind === "note" && (
                      <Button
                        variant="ghost"
                        className="border border-slate-300"
                        onClick={() => setMaterial({ resource, mode: "note" })}
                      >
                        Read note
                      </Button>
                    )}
                    <Button
                      variant="ghost"
                      className="border border-slate-300"
                      onClick={() => setMaterial({ resource, mode: "summary" })}
                    >
                      {resource.has_summary
                        ? "Review summary"
                        : "Generate summary"}
                    </Button>
                    <Button
                      variant="ghost"
                      className="border border-slate-300"
                      onClick={() => setMaterial({ resource, mode: "quiz" })}
                    >
                      Quizzes & results
                    </Button>
                  </div>
                </article>
              ))}
            </div>
            {!plan.resources.length && (
              <p className="mt-3 text-sm text-slate-600">
                Study from your textbook or upload relevant materials in Notes &
                PDFs. A PDF is not required to use Sprint Mode.
              </p>
            )}
          </section>
        </>
      )}
      {material?.mode === "summary" && (
        <SummaryModal
          source={material.resource}
          sourceTitle={material.resource.title}
          onClose={() => void closeMaterial()}
        />
      )}
      {material?.mode === "quiz" && (
        <QuizModal
          source={material.resource}
          sourceTitle={material.resource.title}
          onClose={() => void closeMaterial()}
        />
      )}
      {material?.mode === "note" && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/40 p-4">
          <section
            role="dialog"
            aria-modal="true"
            aria-label="Read note"
            className="max-h-[85vh] w-full max-w-2xl overflow-auto rounded-2xl bg-white p-6"
          >
            <h2 className="text-xl font-bold">{material.resource.title}</h2>
            <p className="my-5 whitespace-pre-wrap text-sm leading-7">
              {material.resource.content}
            </p>
            <Button onClick={() => void closeMaterial()}>Close note</Button>
          </section>
        </div>
      )}
    </section>
  );
}
