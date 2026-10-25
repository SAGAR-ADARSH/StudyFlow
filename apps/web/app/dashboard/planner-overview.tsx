"use client";
import { useEffect, useState } from "react";
import { AnalyticsResponse, getAnalytics } from "@/lib/api";

export function PlannerOverview() {
  const [data, setData] = useState<AnalyticsResponse | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    let live = true;
    getAnalytics().then((value) => { if (live) setData(value); })
      .catch((cause) => { if (live) setError(cause instanceof Error ? cause.message : "Could not load planner overview."); });
    return () => { live = false; };
  }, []);
  if (error) return <p role="alert" className="text-sm text-red-700">{error}</p>;
  if (!data) return <p role="status" className="text-sm text-slate-500">Loading planner overview…</p>;
  return <div className="rounded-2xl border bg-white p-5 text-sm text-slate-700">
    <h2 className="font-semibold text-slate-900">Planner reminders & study time</h2>
    <p className="mt-2">{data.tasks.pending + data.tasks.in_progress} open tasks · <strong className="text-amber-800">{data.tasks.overdue} overdue</strong> · {data.tasks.completed} completed</p>
    <p className="mt-1">{data.study_time.recorded_hours_total}h recorded in completed timer sessions, separately from {data.study_time.estimated_hours_total}h estimated topic work.</p>
    <p className="mt-1 text-xs text-slate-500">Use Tasks for due dates and Study Timer to record time. These do not change completed Sprint work.</p>
  </div>;
}
