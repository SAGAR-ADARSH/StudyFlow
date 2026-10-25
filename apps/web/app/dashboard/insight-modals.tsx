"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  ArrowLeft,
  ArrowRight,
  CheckCircle2,
  ClipboardList,
  FileQuestion,
  Loader2,
  RefreshCw,
  Sparkles,
  Trophy,
  X,
  XCircle,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  AttemptAnswerDetail,
  DocumentSummary,
  InsightSource,
  Quiz,
  QuizAttempt,
  QuizResults,
  generateQuiz,
  generateSummary,
  getQuiz,
  getQuizResults,
  getSummary,
  listQuizzes,
  submitQuizAttempt,
} from "@/lib/api";

const QUESTION_COUNTS = [3, 5, 8, 10];
const SUMMARY_LENGTHS = [
  { label: "Short", words: 120 },
  { label: "Standard", words: 220 },
  { label: "Detailed", words: 400 },
];

function messageOf(cause: unknown, fallback: string): string {
  if (cause instanceof Error) return cause.message;
  return fallback;
}

function Modal({
  title,
  subtitle,
  onClose,
  children,
  labelledBy,
  footer,
}: {
  title: string;
  subtitle?: string;
  onClose: () => void;
  children: React.ReactNode;
  labelledBy: string;
  footer?: React.ReactNode;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/40 p-4 backdrop-blur-sm">
      <section
        role="dialog"
        aria-modal="true"
        aria-labelledby={labelledBy}
        className="flex max-h-[95vh] w-full max-w-2xl flex-col overflow-hidden rounded-2xl bg-white shadow-2xl"
      >
        <div className="flex items-start justify-between gap-4 border-b border-slate-100 px-6 py-4">
          <div>
            <h2 id={labelledBy} className="text-lg font-bold text-slate-900">
              {title}
            </h2>
            {subtitle && <p className="mt-1 text-xs text-slate-500">{subtitle}</p>}
          </div>
          <button
            type="button"
            aria-label="Close"
            onClick={onClose}
            className="rounded-lg p-2 text-slate-400 transition hover:bg-slate-100 hover:text-slate-700"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto px-6 py-5">{children}</div>
        {footer && <div className="border-t border-slate-100 px-6 py-4">{footer}</div>}
      </section>
    </div>
  );
}

function Alert({ tone, children }: { tone: "error" | "info"; children: React.ReactNode }) {
  const styles =
    tone === "error"
      ? "border-rose-200 bg-rose-50 text-rose-700"
      : "border-indigo-200 bg-indigo-50 text-indigo-700";
  return (
    <p role={tone === "error" ? "alert" : undefined} className={`rounded-lg border px-3 py-2 text-xs ${styles}`}>
      {children}
    </p>
  );
}

// ---------------------------------------------------------------------------
// Summary modal
// ---------------------------------------------------------------------------
export function SummaryModal({
  source,
  sourceTitle,
  onClose,
}: {
  source: InsightSource;
  sourceTitle: string;
  onClose: () => void;
}) {
  const [summary, setSummary] = useState<DocumentSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lengthWords, setLengthWords] = useState(220);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);
    getSummary(source)
      .then((existing) => {
        if (active) setSummary(existing);
      })
      .catch((cause) => {
        // A 404 simply means "not generated yet"; anything else is a real failure.
        if (active && !messageOf(cause, "").includes("No summary")) {
          setError(messageOf(cause, "Unable to load the summary."));
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [source]);

  async function handleGenerate() {
    setGenerating(true);
    setError(null);
    try {
      const result = await generateSummary(source, {
        max_words: lengthWords,
        max_key_points: lengthWords <= 120 ? 4 : 6,
      });
      setSummary(result);
    } catch (cause) {
      setError(messageOf(cause, "Unable to generate a summary."));
    } finally {
      setGenerating(false);
    }
  }

  const paragraphs = useMemo(
    () => (summary ? summary.summary_text.split(/\n{2,}/).filter(Boolean) : []),
    [summary],
  );

  return (
    <Modal
      labelledBy="summary-modal-title"
      title="Summary"
      subtitle={sourceTitle}
      onClose={onClose}
      footer={
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-1.5">
            {SUMMARY_LENGTHS.map((option) => (
              <button
                key={option.words}
                type="button"
                onClick={() => setLengthWords(option.words)}
                disabled={generating}
                className={`rounded-lg px-2.5 py-1.5 text-[11px] font-medium transition ${
                  lengthWords === option.words
                    ? "bg-indigo-600 text-white"
                    : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                } disabled:opacity-50`}
              >
                {option.label}
              </button>
            ))}
          </div>
          <div className="flex items-center gap-2">
            <Button type="button" variant="ghost" onClick={onClose}>
              Close
            </Button>
            <Button type="button" onClick={() => void handleGenerate()} disabled={generating} className="gap-2">
              {generating ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
              {summary ? "Regenerate" : "Generate summary"}
            </Button>
          </div>
        </div>
      }
    >
      {error && <div className="mb-4"><Alert tone="error">{error}</Alert></div>}

      {loading ? (
        <div className="flex items-center justify-center gap-2 py-14 text-sm text-slate-500">
          <Loader2 className="h-4 w-4 animate-spin" /> Checking for an existing summary…
        </div>
      ) : !summary ? (
        <div className="py-10 text-center">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-indigo-50 text-indigo-600">
            <Sparkles className="h-5 w-5" />
          </div>
          <h3 className="mt-4 text-base font-semibold text-slate-900">No summary yet</h3>
          <p className="mx-auto mt-1 max-w-md text-sm text-slate-500">
            StudyFlow reads the extracted text of this document and writes an extractive summary
            from its own sentences. Nothing is fetched from the internet.
          </p>
        </div>
      ) : (
        <div className="space-y-5">
          {summary.warnings.length > 0 && (
            <Alert tone="info">{summary.warnings.join(" ")}</Alert>
          )}

          <div className="flex flex-wrap gap-2 text-[10px] font-medium text-slate-500">
            <span className="rounded-full bg-slate-100 px-2.5 py-1">{summary.word_count} words</span>
            <span className="rounded-full bg-slate-100 px-2.5 py-1">
              from {summary.source_sentences} sentences
            </span>
            <span className="rounded-full bg-slate-100 px-2.5 py-1">
              {summary.chunk_count} section{summary.chunk_count === 1 ? "" : "s"}
            </span>
            <span className="rounded-full bg-slate-100 px-2.5 py-1">
              {new Date(summary.created_at).toLocaleString()}
            </span>
            <span className="rounded-full bg-slate-100 px-2.5 py-1">{summary.method} · {summary.engine_version}</span>
          </div>

          {summary.key_points.length > 0 && (
            <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
              <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-600">Key points</h3>
              <ul className="mt-2 space-y-1.5">
                {summary.key_points.map((point) => (
                  <li key={point} className="flex gap-2 text-sm leading-6 text-slate-700">
                    <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-indigo-500" />
                    {point}
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div className="space-y-3">
            {paragraphs.map((paragraph, index) => (
              <p key={`${index}-${paragraph.slice(0, 24)}`} className="text-sm leading-7 text-slate-700">
                {paragraph}
              </p>
            ))}
          </div>
        </div>
      )}
    </Modal>
  );
}

// ---------------------------------------------------------------------------
// Quiz modal
// ---------------------------------------------------------------------------
type QuizMode = "setup" | "take" | "review" | "results";

export function QuizModal({
  source,
  sourceTitle,
  onClose,
}: {
  source: InsightSource;
  sourceTitle: string;
  onClose: () => void;
}) {
  const [mode, setMode] = useState<QuizMode>("setup");
  const [questionCount, setQuestionCount] = useState(5);
  const [quizzes, setQuizzes] = useState<Quiz[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [quiz, setQuiz] = useState<Quiz | null>(null);
  const [step, setStep] = useState(0);
  const [answers, setAnswers] = useState<Record<number, number>>({});
  const [startedAt, setStartedAt] = useState<number | null>(null);
  const [attempt, setAttempt] = useState<QuizAttempt | null>(null);
  const [results, setResults] = useState<QuizResults | null>(null);
  const timerRef = useRef<number | null>(null);

  const loadQuizzes = useCallback(async () => {
    setLoading(true);
    try {
      setQuizzes(await listQuizzes(source));
    } catch (cause) {
      setError(messageOf(cause, "Unable to load your quizzes."));
    } finally {
      setLoading(false);
    }
  }, [source]);

  useEffect(() => {
    void loadQuizzes();
    return () => {
      if (timerRef.current) window.clearInterval(timerRef.current);
    };
  }, [loadQuizzes]);

  function startQuiz(next: Quiz) {
    setQuiz(next);
    setAnswers({});
    setStep(0);
    setAttempt(null);
    setStartedAt(Date.now());
    setMode("take");
  }

  async function handleGenerate() {
    setGenerating(true);
    setError(null);
    try {
      const created = await generateQuiz(source, questionCount);
      setQuizzes((current) => [created, ...current]);
      startQuiz(created);
    } catch (cause) {
      setError(messageOf(cause, "Unable to generate a quiz."));
    } finally {
      setGenerating(false);
    }
  }

  async function handleSubmit() {
    if (!quiz) return;
    setSubmitting(true);
    setError(null);
    try {
      const payload = quiz.questions.map((question) => ({
        question_id: question.id,
        selected_index: answers[question.id] ?? null,
      }));
      const duration = startedAt ? Math.max(1, Math.round((Date.now() - startedAt) / 1000)) : null;
      const graded = await submitQuizAttempt(quiz.id, payload, duration ?? undefined);
      setAttempt(graded);
      setResults(await getQuizResults(quiz.id));
      setMode("review");
      await loadQuizzes();
    } catch (cause) {
      setError(messageOf(cause, "Unable to submit your answers."));
    } finally {
      setSubmitting(false);
    }
  }

  async function openResults(quizId: number) {
    setError(null);
    setLoading(true);
    try {
      const loaded = await getQuizResults(quizId);
      setResults(loaded);
      setQuiz(loaded.quiz);
      setAttempt(loaded.attempts[0] ?? null);
      setMode("results");
    } catch (cause) {
      setError(messageOf(cause, "Unable to load the results."));
    } finally {
      setLoading(false);
    }
  }

  async function retake(quizId: number) {
    setError(null);
    setLoading(true);
    try {
      startQuiz(await getQuiz(quizId));
    } catch (cause) {
      setError(messageOf(cause, "Unable to open this quiz."));
    } finally {
      setLoading(false);
    }
  }

  const answeredCount = quiz ? quiz.questions.filter((q) => answers[q.id] !== undefined).length : 0;
  const currentQuestion = quiz?.questions[step];

  return (
    <Modal
      labelledBy="quiz-modal-title"
      title={mode === "take" ? "Take quiz" : mode === "setup" ? "Practice quiz" : "Quiz results"}
      subtitle={quiz ? quiz.title : sourceTitle}
      onClose={onClose}
      footer={
        mode === "take" && quiz ? (
          <div className="flex items-center justify-between gap-3">
            <span className="text-[11px] text-slate-500">
              {answeredCount} of {quiz.question_count} answered
            </span>
            <div className="flex items-center gap-2">
              <Button
                type="button"
                variant="ghost"
                onClick={() => setStep((value) => Math.max(0, value - 1))}
                disabled={step === 0}
                className="gap-2"
              >
                <ArrowLeft className="h-4 w-4" /> Back
              </Button>
              {step < quiz.question_count - 1 ? (
                <Button
                  type="button"
                  onClick={() => setStep((value) => Math.min(quiz.question_count - 1, value + 1))}
                  className="gap-2"
                >
                  Next <ArrowRight className="h-4 w-4" />
                </Button>
              ) : (
                <Button type="button" onClick={() => void handleSubmit()} disabled={submitting} className="gap-2">
                  {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <CheckCircle2 className="h-4 w-4" />}
                  Submit quiz
                </Button>
              )}
            </div>
          </div>
        ) : (
          <div className="flex items-center justify-between gap-3">
            <span className="text-[11px] text-slate-400">
              {quizzes.length > 0 ? `${quizzes.length} quiz set${quizzes.length === 1 ? "" : "s"} saved` : ""}
            </span>
            <div className="flex items-center gap-2">
              {mode !== "setup" && (
                <Button type="button" variant="ghost" onClick={() => setMode("setup")}>
                  All quizzes
                </Button>
              )}
              <Button type="button" onClick={onClose}>
                Close
              </Button>
            </div>
          </div>
        )
      }
    >
      {error && (
        <div className="mb-4">
          <Alert tone="error">{error}</Alert>
        </div>
      )}

      {mode === "setup" && (
        <div className="space-y-5">
          <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
            <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-600">New quiz</h3>
            <p className="mt-1 text-sm text-slate-500">
              Questions use definitions and quoted factual passages from this material. Answer choices
              come from the same source. Diagram-only content and program code are skipped;
              fewer questions may be returned when there is not enough readable explanation.
            </p>
            <div className="mt-3 flex flex-wrap items-center gap-2">
              {QUESTION_COUNTS.map((count) => (
                <button
                  key={count}
                  type="button"
                  onClick={() => setQuestionCount(count)}
                  disabled={generating}
                  className={`rounded-lg px-3 py-1.5 text-xs font-medium transition ${
                    questionCount === count
                      ? "bg-indigo-600 text-white"
                      : "bg-white text-slate-600 ring-1 ring-slate-200 hover:bg-slate-100"
                  } disabled:opacity-50`}
                >
                  {count} questions
                </button>
              ))}
              <Button type="button" onClick={() => void handleGenerate()} disabled={generating} className="ml-auto gap-2">
                {generating ? <Loader2 className="h-4 w-4 animate-spin" /> : <ClipboardList className="h-4 w-4" />}
                Generate quiz
              </Button>
            </div>
          </div>

          <div>
            <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-600">Saved quizzes</h3>
            {loading ? (
              <div className="mt-3 flex items-center gap-2 text-sm text-slate-500">
                <Loader2 className="h-4 w-4 animate-spin" /> Loading…
              </div>
            ) : quizzes.length === 0 ? (
              <div className="mt-3 rounded-xl border border-dashed border-slate-300 px-4 py-8 text-center">
                <div className="mx-auto flex h-11 w-11 items-center justify-center rounded-2xl bg-indigo-50 text-indigo-600">
                  <FileQuestion className="h-5 w-5" />
                </div>
                <p className="mt-3 text-sm font-semibold text-slate-900">No quizzes yet</p>
                <p className="mt-1 text-xs text-slate-500">
                  Generate your first quiz to start revising from this material.
                </p>
              </div>
            ) : (
              <ul className="mt-3 space-y-2">
                {quizzes.map((item) => (
                  <li
                    key={item.id}
                    className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-200 bg-white px-4 py-3"
                  >
                    <div className="min-w-0">
                      <p className="truncate text-sm font-semibold text-slate-900">{item.title}</p>
                      <p className="mt-0.5 text-[11px] text-slate-500">
                        {item.question_count} questions · {item.attempt_count} attempt
                        {item.attempt_count === 1 ? "" : "s"}
                        {item.best_score_percent !== null ? ` · best ${item.best_score_percent}%` : ""}
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <Button type="button" variant="ghost" onClick={() => void retake(item.id)} disabled={loading}>
                        Retake
                      </Button>
                      <Button type="button" onClick={() => void openResults(item.id)} disabled={loading}>
                        Results
                      </Button>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      )}

      {mode === "take" && quiz && currentQuestion && (
        <div className="space-y-5">
          <div>
            <div className="flex items-center justify-between text-[11px] font-medium text-slate-500">
              <span>
                Question {step + 1} of {quiz.question_count}
              </span>
              {currentQuestion.source_page ? <span>Page {currentQuestion.source_page}</span> : null}
            </div>
            <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-slate-100">
              <div
                className="h-full rounded-full bg-indigo-600 transition-all"
                style={{ width: `${((step + 1) / quiz.question_count) * 100}%` }}
              />
            </div>
          </div>

          <h3 className="text-base font-semibold leading-7 text-slate-900">{currentQuestion.prompt}</h3>

          <div className="space-y-2">
            {currentQuestion.options.map((option, index) => {
              const selected = answers[currentQuestion.id] === index;
              return (
                <button
                  key={`${currentQuestion.id}-${option}`}
                  type="button"
                  onClick={() => setAnswers((current) => ({ ...current, [currentQuestion.id]: index }))}
                  className={`flex w-full items-center gap-3 rounded-xl border px-4 py-3 text-left text-sm transition ${
                    selected
                      ? "border-indigo-500 bg-indigo-50 text-indigo-900"
                      : "border-slate-200 bg-white text-slate-700 hover:border-indigo-300 hover:bg-slate-50"
                  }`}
                >
                  <span
                    className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-[11px] font-semibold ${
                      selected ? "bg-indigo-600 text-white" : "bg-slate-100 text-slate-600"
                    }`}
                  >
                    {String.fromCharCode(65 + index)}
                  </span>
                  {option}
                </button>
              );
            })}
          </div>
        </div>
      )}

      {(mode === "review" || mode === "results") && (attempt || results) && (
        <QuizReview attempt={attempt} results={results} onRetake={() => quiz && void retake(quiz.id)} />
      )}
    </Modal>
  );
}

function QuizReview({
  attempt,
  results,
  onRetake,
}: {
  attempt: QuizAttempt | null;
  results: QuizResults | null;
  onRetake: () => void;
}) {
  const shown = attempt ?? results?.attempts[0] ?? null;
  if (!shown) {
    return (
      <p className="py-8 text-center text-sm text-slate-500">
        No attempt has been recorded for this quiz yet.
      </p>
    );
  }

  const percent = Math.round(shown.score_percent);
  const tone =
    percent >= 80 ? "text-emerald-600" : percent >= 50 ? "text-amber-600" : "text-rose-600";

  return (
    <div className="space-y-5">
      <div className="rounded-xl border border-slate-200 bg-slate-50 p-5 text-center">
        <Trophy className={`mx-auto h-7 w-7 ${tone}`} />
        <p className={`mt-2 text-3xl font-bold ${tone}`}>{percent}%</p>
        <p className="mt-1 text-sm text-slate-600">
          {shown.correct_count} of {shown.total_questions} correct
        </p>
        <p className="mt-1 text-[11px] text-slate-500">
          Submitted {new Date(shown.submitted_at).toLocaleString()}
          {shown.duration_seconds ? ` · ${shown.duration_seconds}s` : ""}
        </p>
        {results && results.attempts.length > 1 && (
          <p className="mt-2 text-[11px] text-slate-500">
            {results.attempts.length} attempts · best {results.best_score_percent}% · average{" "}
            {results.average_score_percent}%
          </p>
        )}
        <Button type="button" variant="ghost" onClick={onRetake} className="mt-3 gap-2">
          <RefreshCw className="h-4 w-4" /> Try again
        </Button>
      </div>

      <ol className="space-y-3">
        {shown.answers.map((answer: AttemptAnswerDetail, index: number) => (
          <li key={answer.question_id} className="rounded-xl border border-slate-200 bg-white p-4">
            <div className="flex items-start gap-2">
              {answer.is_correct ? (
                <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" />
              ) : (
                <XCircle className="mt-0.5 h-4 w-4 shrink-0 text-rose-500" />
              )}
              <div className="min-w-0">
                <p className="text-sm font-semibold text-slate-900">
                  {index + 1}. {answer.prompt}
                </p>
                <ul className="mt-2 space-y-1">
                  {answer.options.map((option, optionIndex) => {
                    const isCorrect = optionIndex === answer.correct_index;
                    const isSelected = optionIndex === answer.selected_index;
                    return (
                      <li
                        key={`${answer.question_id}-${option}`}
                        className={`rounded-lg px-3 py-1.5 text-xs ${
                          isCorrect
                            ? "bg-emerald-50 text-emerald-800 ring-1 ring-emerald-200"
                            : isSelected
                              ? "bg-rose-50 text-rose-700 ring-1 ring-rose-200"
                              : "text-slate-600"
                        }`}
                      >
                        {String.fromCharCode(65 + optionIndex)}. {option}
                        {isCorrect ? " · correct answer" : isSelected ? " · your answer" : ""}
                      </li>
                    );
                  })}
                </ul>
                {answer.selected_index === null && (
                  <p className="mt-1 text-[11px] text-slate-500">You skipped this question.</p>
                )}
                <p className="mt-2 text-xs leading-5 text-slate-600">{answer.explanation}</p>
              </div>
            </div>
          </li>
        ))}
      </ol>
    </div>
  );
}
