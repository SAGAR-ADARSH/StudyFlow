"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { CheckCircle2, Clock, Filter, Pencil, Plus, Trash2, AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Exam,
  StudyTask,
  Subject,
  Topic,
  getTasks,
  createTask,
  updateTask,
  deleteTask,
} from "@/lib/api";

type TasksPanelProps = {
  subjects: Subject[];
  topics: Topic[];
  exams: Exam[];
};

type TaskDraft = {
  title: string;
  description: string;
  subject_id: string;
  topic_id: string;
  exam_id: string;
  due_date: string;
  estimated_minutes: string;
  priority: string;
  status: string;
};

const emptyDraft = (): TaskDraft => ({
  title: "",
  description: "",
  subject_id: "",
  topic_id: "",
  exam_id: "",
  due_date: "",
  estimated_minutes: "",
  priority: "Medium",
  status: "Pending",
});

export function TasksPanel({ subjects, topics, exams }: TasksPanelProps) {
  const [tasks, setTasks] = useState<StudyTask[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filterStatus, setFilterStatus] = useState("");
  const [filterPriority, setFilterPriority] = useState("");
  const [dueBefore, setDueBefore] = useState("");
  const [dueAfter, setDueAfter] = useState("");
  const [actionBusy, setActionBusy] = useState(false);
  const [showOverdueOnly, setShowOverdueOnly] = useState(false);
  const [editorOpen, setEditorOpen] = useState(false);
  const [editingTask, setEditingTask] = useState<StudyTask | null>(null);
  const [draft, setDraft] = useState<TaskDraft>(emptyDraft);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data: StudyTask[] = [];
      let page: StudyTask[];
      do {
        page = await getTasks({ limit: 100, offset: data.length });
        data.push(...page);
      } while (page.length === 100);
      setTasks(data);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to load tasks.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const filtered = useMemo(() => {
    return tasks.filter((t) => {
      if (filterStatus && t.status !== filterStatus) return false;
      if (filterPriority && t.priority !== filterPriority) return false;
      if (dueBefore && (!t.due_date || t.due_date > dueBefore)) return false;
      if (dueAfter && (!t.due_date || t.due_date < dueAfter)) return false;
      if (showOverdueOnly && !t.is_overdue) return false;
      return true;
    });
  }, [tasks, filterStatus, filterPriority, showOverdueOnly, dueBefore, dueAfter]);

  const grouped = useMemo(() => {
    const overdue = filtered.filter((t) => t.is_overdue);
    const upcoming = filtered.filter((t) => !t.is_overdue && t.status !== "Completed" && t.status !== "Cancelled");
    const completed = filtered.filter((t) => t.status === "Completed");
    return { overdue, upcoming, completed, cancelled: filtered.filter((t) => t.status === "Cancelled"), total: filtered.length };
  }, [filtered]);

  function openEditor(task?: StudyTask) {
    setEditingTask(task || null);
    setFormError(null);
    if (task) {
      setDraft({
        title: task.title,
        description: task.description || "",
        subject_id: task.subject_id?.toString() || "",
        topic_id: task.topic_id?.toString() || "",
        exam_id: task.exam_id?.toString() || "",
        due_date: task.due_date || "",
        estimated_minutes: task.estimated_minutes?.toString() || "",
        priority: task.priority,
        status: task.status,
      });
    } else {
      setDraft(emptyDraft());
    }
    setEditorOpen(true);
  }

  async function handleSave(e: FormEvent) {
    e.preventDefault();
    setFormError(null);
    if (!draft.title.trim()) {
      setFormError("Title is required.");
      return;
    }
    setSaving(true);
    try {
      const payload = {
        title: draft.title.trim(),
        description: draft.description.trim() || null,
        subject_id: draft.subject_id ? Number(draft.subject_id) : null,
        topic_id: draft.topic_id ? Number(draft.topic_id) : null,
        exam_id: draft.exam_id ? Number(draft.exam_id) : null,
        due_date: draft.due_date || null,
        estimated_minutes: draft.estimated_minutes ? Number(draft.estimated_minutes) : null,
        priority: draft.priority,
        status: draft.status,
      };
      if (editingTask) {
        await updateTask(editingTask.id, payload);
      } else {
        await createTask(payload);
      }
      setEditorOpen(false);
      await refresh();
    } catch (cause) {
      setFormError(cause instanceof Error ? cause.message : "Could not save task.");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(task: StudyTask) {
    if (!window.confirm(`Delete task "${task.title}"?`)) return;
    setActionBusy(true);
    try {
      await deleteTask(task.id);
      await refresh();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not delete task.");
    } finally { setActionBusy(false); }
  }

  async function quickToggleStatus(task: StudyTask) {
    const next = task.status === "Completed" ? "Pending" : "Completed";
    setActionBusy(true);
    try {
      await updateTask(task.id, { status: next });
      await refresh();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not update status.");
    } finally { setActionBusy(false); }
  }

  const fieldCls = "w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500";

  if (loading) return <div className="p-8 text-sm text-slate-600">Loading tasks…</div>;

  return (
    <section className="space-y-6">
      <header className="rounded-2xl border border-indigo-100 bg-gradient-to-br from-indigo-50 to-white p-6">
        <h1 className="text-xl font-bold text-slate-900">Study Tasks & Planner</h1>
        <p className="mt-1 text-sm text-slate-600">
          Create standalone study tasks linked to subjects, topics, or exams. These are independent from Sprint Mode tasks and will not be removed when Sprint plans change.
        </p>
        <div className="mt-4 flex flex-wrap gap-2 text-xs">
          <span className="rounded-full bg-white border px-3 py-1">Total: {tasks.length}</span>
          <span className="rounded-full bg-amber-50 border border-amber-200 px-3 py-1 text-amber-800">Overdue: {tasks.filter((t) => t.is_overdue).length}</span>
          <span className="rounded-full bg-emerald-50 border border-emerald-200 px-3 py-1 text-emerald-800">Completed: {tasks.filter((t) => t.status === "Completed").length}</span>
        </div>
      </header>

      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <div className="flex items-center gap-1.5 text-xs text-slate-600"><Filter className="h-4 w-4" /> Filters:</div>
          <select value={filterStatus} onChange={(e) => setFilterStatus(e.target.value)} className="rounded-lg border border-slate-300 bg-white px-2 py-1 text-sm">
            <option value="">All statuses</option>
            <option value="Pending">Pending</option>
            <option value="In Progress">In Progress</option>
            <option value="Completed">Completed</option>
            <option value="Cancelled">Cancelled</option>
          </select>
          <select value={filterPriority} onChange={(e) => setFilterPriority(e.target.value)} className="rounded-lg border border-slate-300 bg-white px-2 py-1 text-sm">
            <option value="">All priorities</option>
            <option value="High">High</option>
            <option value="Medium">Medium</option>
            <option value="Low">Low</option>
          </select>
          <label className="text-xs">Due from <input aria-label="Due from" type="date" value={dueAfter} onChange={(e) => setDueAfter(e.target.value)} /></label>
          <label className="text-xs">Due through <input aria-label="Due through" type="date" value={dueBefore} onChange={(e) => setDueBefore(e.target.value)} /></label>
          <label className="flex items-center gap-1 text-sm">
            <input type="checkbox" checked={showOverdueOnly} onChange={(e) => setShowOverdueOnly(e.target.checked)} />
            Overdue only
          </label>
        </div>
        <Button onClick={() => openEditor()} className="gap-1.5"><Plus className="h-4 w-4" /> New Task</Button>
      </div>

      {error && <p role="alert" className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-800">{error}</p>}

      {filtered.length === 0 ? (
        <div className="rounded-2xl border border-dashed bg-white p-10 text-center text-sm text-slate-600">
          No tasks match the current filters. Create your first study task to get started.
        </div>
      ) : (
        <>
          {grouped.cancelled.length > 0 && <div className="space-y-3"><h2 className="font-semibold text-sm">Cancelled</h2>{grouped.cancelled.map((t) => <TaskCard busy={actionBusy} key={t.id} task={t} onEdit={() => openEditor(t)} onDelete={() => handleDelete(t)} onToggle={() => quickToggleStatus(t)} />)}</div>}
          {grouped.overdue.length > 0 && (
            <div className="space-y-3">
              <h2 className="flex items-center gap-2 text-sm font-bold text-red-700"><AlertTriangle className="h-4 w-4" /> Overdue ({grouped.overdue.length})</h2>
              <div className="grid gap-3 md:grid-cols-2">
                {grouped.overdue.map((t) => (
                  <TaskCard busy={actionBusy} key={t.id} task={t} onEdit={() => openEditor(t)} onDelete={() => handleDelete(t)} onToggle={() => quickToggleStatus(t)} />
                ))}
              </div>
            </div>
          )}
          <div className="space-y-3">
            <h2 className="flex items-center gap-2 text-sm font-bold text-slate-700"><Clock className="h-4 w-4" /> Pending & Upcoming ({grouped.upcoming.length})</h2>
            {grouped.upcoming.length === 0 ? (
              <p className="text-sm text-slate-500">No upcoming tasks.</p>
            ) : (
              <div className="grid gap-3 md:grid-cols-2">
                {grouped.upcoming.map((t) => (
                  <TaskCard busy={actionBusy} key={t.id} task={t} onEdit={() => openEditor(t)} onDelete={() => handleDelete(t)} onToggle={() => quickToggleStatus(t)} />
                ))}
              </div>
            )}
          </div>
          <div className="space-y-3">
            <h2 className="flex items-center gap-2 text-sm font-bold text-emerald-700"><CheckCircle2 className="h-4 w-4" /> Completed ({grouped.completed.length})</h2>
            {grouped.completed.length === 0 ? (
              <p className="text-sm text-slate-500">No completed tasks yet.</p>
            ) : (
              <div className="grid gap-3 md:grid-cols-2">
                {grouped.completed.map((t) => (
                  <TaskCard busy={actionBusy} key={t.id} task={t} onEdit={() => openEditor(t)} onDelete={() => handleDelete(t)} onToggle={() => quickToggleStatus(t)} />
                ))}
              </div>
            )}
          </div>
        </>
      )}

      {editorOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
          <div className="w-full max-w-lg rounded-2xl bg-white p-6 shadow-xl max-h-[90vh] overflow-y-auto">
            <h3 className="text-lg font-bold text-slate-900">{editingTask ? "Edit Task" : "Create Study Task"}</h3>
            <p className="text-xs text-slate-500">General tasks are stored separately from Sprint Mode tasks.</p>
            <form onSubmit={handleSave} className="mt-4 space-y-3">
              <div>
                <label className="block text-xs font-medium text-slate-700">Title *</label>
                <input value={draft.title} onChange={(e) => setDraft({ ...draft, title: e.target.value })} required maxLength={180} placeholder="e.g. Revise Chapter 5 — Thermodynamics" className={fieldCls} />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-700">Description</label>
                <textarea value={draft.description} onChange={(e) => setDraft({ ...draft, description: e.target.value })} rows={3} placeholder="Optional details…" className={fieldCls} />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-700">Subject</label>
                  <select value={draft.subject_id} onChange={(e) => setDraft({ ...draft, subject_id: e.target.value, topic_id: "", exam_id: "" })} className={fieldCls}>
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
              <div>
                <label className="block text-xs font-medium text-slate-700">Exam (optional)</label>
                <select value={draft.exam_id} onChange={(e) => setDraft({ ...draft, exam_id: e.target.value })} className={fieldCls}>
                  <option value="">None</option>
                  {exams.filter((e) => !draft.subject_id || e.subject_id === Number(draft.subject_id)).map((e) => <option key={e.id} value={e.id}>{e.title} — {e.exam_date}</option>)}
                </select>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-700">Due date</label>
                  <input type="date" value={draft.due_date} onChange={(e) => setDraft({ ...draft, due_date: e.target.value })} className={fieldCls} />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-700">Est. minutes</label>
                  <input type="number" min={1} max={1440} value={draft.estimated_minutes} onChange={(e) => setDraft({ ...draft, estimated_minutes: e.target.value })} placeholder="60" className={fieldCls} />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-700">Priority</label>
                  <select value={draft.priority} onChange={(e) => setDraft({ ...draft, priority: e.target.value })} className={fieldCls}>
                    <option value="High">High</option>
                    <option value="Medium">Medium</option>
                    <option value="Low">Low</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-700">Status</label>
                  <select value={draft.status} onChange={(e) => setDraft({ ...draft, status: e.target.value })} className={fieldCls}>
                    <option value="Pending">Pending</option>
                    <option value="In Progress">In Progress</option>
                    <option value="Completed">Completed</option>
                    <option value="Cancelled">Cancelled</option>
                  </select>
                </div>
              </div>
              {formError && <p className="text-sm text-red-600">{formError}</p>}
              <div className="flex justify-end gap-2 pt-2">
                <Button type="button" variant="ghost" onClick={() => setEditorOpen(false)}>Cancel</Button>
                <Button type="submit" disabled={saving}>{saving ? "Saving…" : editingTask ? "Update Task" : "Create Task"}</Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </section>
  );
}

function TaskCard({ busy, task, onEdit, onDelete, onToggle }: { busy: boolean; task: StudyTask; onEdit: () => void; onDelete: () => void; onToggle: () => void }) {
  const priorityColor = task.priority === "High" ? "bg-red-50 text-red-700 border-red-200" : task.priority === "Low" ? "bg-slate-50 text-slate-600 border-slate-200" : "bg-amber-50 text-amber-800 border-amber-200";
  const statusColor = task.status === "Completed" ? "bg-emerald-50 text-emerald-700 border-emerald-200" : task.status === "Cancelled" ? "bg-slate-100 text-slate-500 border-slate-200" : "bg-white text-slate-700 border-slate-200";
  return (
    <div className={`rounded-xl border p-4 shadow-sm ${task.is_overdue ? "border-red-200 bg-red-50/40" : "bg-white border-slate-200"}`}>
      <div className="flex items-start justify-between gap-2">
        <h3 className="font-semibold text-sm text-slate-900">{task.title}</h3>
        <span className={`rounded-full border px-2 py-0.5 text-xs ${task.is_overdue ? "bg-red-100 text-red-700 border-red-200" : statusColor}`}>{task.status}</span>
      </div>
      <p className="mt-1 text-xs text-slate-500" title={task.priority_reason}>Rule-based priority score: {task.priority_score}</p>
      {task.description && <p className="mt-1 text-xs text-slate-600 line-clamp-2">{task.description}</p>}
      <div className="mt-2 flex flex-wrap gap-1.5 text-xs">
        {task.subject_name && <span className="rounded-full bg-indigo-50 border border-indigo-200 px-2 py-0.5 text-indigo-700">{task.subject_name}</span>}
        {task.topic_name && <span className="rounded-full bg-slate-50 border px-2 py-0.5">{task.topic_name}</span>}
        <span className={`rounded-full border px-2 py-0.5 ${priorityColor}`}>{task.priority}</span>
        {task.due_date && <span className={`rounded-full border px-2 py-0.5 ${task.is_overdue ? "bg-red-100 border-red-200 text-red-700" : "bg-white"}`}>Due: {task.due_date}</span>}
        {task.estimated_minutes && <span className="rounded-full bg-white border px-2 py-0.5">{task.estimated_minutes} min</span>}
        {task.is_overdue && <span className="rounded-full bg-red-600 text-white px-2 py-0.5">Overdue</span>}
      </div>
      <div className="mt-3 flex items-center gap-2">
        <label className="flex items-center gap-1.5 text-xs cursor-pointer">
          <input type="checkbox" checked={task.status === "Completed"} disabled={busy} onChange={onToggle} className="h-4 w-4 rounded border-slate-300" />
          Mark completed
        </label>
        <div className="ml-auto flex gap-1">
          <Button variant="ghost" disabled={busy} onClick={onEdit} className="h-8 px-2 text-xs"><Pencil className="h-3 w-3" /> Edit</Button>
          <Button variant="ghost" disabled={busy} onClick={onDelete} className="h-8 px-2 text-xs text-red-600 hover:bg-red-50"><Trash2 className="h-3 w-3" /> Delete</Button>
        </div>
      </div>
    </div>
  );
}
