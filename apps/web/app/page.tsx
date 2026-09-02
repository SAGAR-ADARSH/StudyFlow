import Link from "next/link";
import { ArrowRight, BrainCircuit, CalendarDays, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";

const benefits = [
  [BrainCircuit, "Learn your way", "Personalized guidance that meets you where you are."],
  [CalendarDays, "Stay on track", "Turn your goals into a study plan you can follow."],
  [Sparkles, "Study with clarity", "Use focused tools for notes, revision, and practice."]
];

export default function HomePage() {
  return (
    <main className="min-h-screen">
      <nav className="mx-auto flex max-w-6xl items-center justify-between px-6 py-6">
        <span className="text-xl font-bold tracking-tight">Study<span className="text-indigo-600">Flow</span></span>
        <Button variant="ghost" asChild><Link href="/login">Sign in</Link></Button>
      </nav>
      <section className="mx-auto max-w-4xl px-6 pb-20 pt-24 text-center sm:pt-32">
        <p className="mb-5 text-sm font-semibold uppercase tracking-[0.2em] text-indigo-600">Your personal AI study companion</p>
        <h1 className="text-5xl font-bold tracking-tight text-slate-950 sm:text-7xl">Make every study session count.</h1>
        <p className="mx-auto mt-7 max-w-2xl text-lg leading-8 text-slate-600">Plan with confidence, focus without friction, and build lasting learning habits—one thoughtful day at a time.</p>
        <Button size="lg" className="mt-9" asChild><Link href="/login">Start your flow <ArrowRight className="ml-2 size-4" /></Link></Button>
      </section>
      <section className="mx-auto grid max-w-6xl gap-5 px-6 pb-20 md:grid-cols-3">
        {benefits.map(([Icon, title, description]) => <article key={title as string} className="rounded-2xl border bg-white p-6 shadow-sm"><Icon className="mb-5 size-6 text-indigo-600" /><h2 className="font-semibold">{title as string}</h2><p className="mt-2 text-sm leading-6 text-slate-600">{description as string}</p></article>)}
      </section>
    </main>
  );
}
