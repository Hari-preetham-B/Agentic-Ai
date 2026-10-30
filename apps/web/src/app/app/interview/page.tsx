"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  listCareers,
  type CareerResponse,
} from "@/lib/api/client";
import { PageHeader } from "@/components/PageHeader";

interface InterviewSession {
  session_id: string;
  profile_id: string;
  career_id: string | null;
  status: string;
  mode: string;
  difficulty: string;
  started_at: string | null;
  completed_at: string | null;
}

interface InterviewResults {
  session_id: string;
  overall_score: number;
  questions_attempted: number;
  skill_performance: {
    skill_name: string;
    questions_attempted: number;
    average_score: number | null;
    latest_score: number | null;
    trend: string;
    performance_confidence: number | null;
  }[];
  strengths: string[];
  weaknesses: string[];
  recommended_skills: string[];
  difficulty_progression: string[];
}

export default function InterviewPage() {
  const [careers, setCareers] = useState<CareerResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [profileId] = useState<string | null>(() => {
    if (typeof window !== "undefined") {
      return localStorage.getItem("ct:profileId");
    }
    return null;
  });
  const [selectedCareer, setSelectedCareer] = useState<string | null>(null);
  const [session, setSession] = useState<InterviewSession | null>(null);
  const [creating, setCreating] = useState(false);
  const [results, setResults] = useState<InterviewResults | null>(null);
  const [resultsLoading, setResultsLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const data = await listCareers();
        if (!cancelled) setCareers(data);
      } catch (err: unknown) {
        if (!cancelled) setError((err as Error).message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, []);

  async function createSession(slug: string) {
    if (!profileId) {
      setError("No confirmed profile found. Build one via onboarding first.");
      return;
    }
    const career = careers.find((c) => c.slug === slug);
    if (!career) return;
    setCreating(true);
    setError(null);
    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/interviews`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            profile_id: profileId,
            career_id: career.id,
            mode: "MIXED",
            difficulty: "MEDIUM",
            target_question_count: 10,
          }),
        },
      );
      if (!res.ok) throw new Error("Failed to create session");
      const data = await res.json();
      setSession(data);
      setSelectedCareer(slug);
    } catch (err: unknown) {
      setError((err as Error).message);
    } finally {
      setCreating(false);
    }
  }

  async function startSession() {
    if (!session) return;
    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/interviews/${session.session_id}/start`,
        { method: "POST" },
      );
      if (!res.ok) throw new Error("Failed to start session");
      const data = await res.json();
      setSession(data);
    } catch (err: unknown) {
      setError((err as Error).message);
    }
  }

  async function completeSession() {
    if (!session) return;
    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/interviews/${session.session_id}/complete`,
        { method: "POST" },
      );
      if (!res.ok) throw new Error("Failed to complete session");
      const data = await res.json();
      setSession(data);
    } catch (err: unknown) {
      setError((err as Error).message);
    }
  }

  async function loadResults() {
    if (!session) return;
    setResultsLoading(true);
    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/interviews/${session.session_id}/results`,
      );
      if (!res.ok) throw new Error("Failed to load results");
      const data = await res.json();
      setResults(data);
    } catch (err: unknown) {
      setError((err as Error).message);
    } finally {
      setResultsLoading(false);
    }
  }

  if (loading) {
    return (
      <div className="flex flex-col min-h-[calc(100vh-4rem)] py-10 px-6 md:px-10 lg:px-12">
        <PageHeader title="Interview" subtitle="Loading…" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col min-h-[calc(100vh-4rem)] py-10 px-6 md:px-10 lg:px-12">
        <PageHeader title="Interview" subtitle="Unable to load." />
        <div className="rounded-sm border border-border-soft bg-panel p-8 text-muted text-sm">
          {error}
        </div>
      </div>
    );
  }

  if (!profileId) {
    return (
      <div className="flex flex-col min-h-[calc(100vh-4rem)] py-10 px-6 md:px-10 lg:px-12">
        <PageHeader
          title="Interview"
          subtitle="Build your profile first to start an interview."
        />
        <div className="mt-10">
          <Link
            href="/onboarding/start"
            className="inline-flex items-center gap-2 rounded-sm border border-border-soft bg-panel px-6 py-3 font-medium text-sm transition-colors hover:bg-panel-hover"
          >
            Build your profile
          </Link>
        </div>
      </div>
    );
  }

  if (results) {
    return (
      <div className="flex flex-col min-h-[calc(100vh-4rem)] py-10 px-6 md:px-10 lg:px-12">
        <PageHeader
          title="Interview Results"
          subtitle="Deterministic performance analysis from your interview session."
        />
        <div className="mb-10">
          <div className="flex flex-wrap items-center gap-6 mb-6">
            <div className="rounded-sm border border-border-soft bg-panel p-6">
              <dt className="text-mono-xs font-medium text-muted mb-1">
                Overall score
              </dt>
              <dd className="text-3xl font-semibold font-mono">
                {(results.overall_score * 100).toFixed(0)}%
              </dd>
            </div>
            <div className="rounded-sm border border-border-soft bg-panel p-6">
              <dt className="text-mono-xs font-medium text-muted mb-1">
                Questions
              </dt>
              <dd className="text-3xl font-semibold font-mono">
                {results.questions_attempted}
              </dd>
            </div>
            <div className="rounded-sm border border-border-soft bg-panel p-6">
              <dt className="text-mono-xs font-medium text-muted mb-1">
                Strongest
              </dt>
              <dd className="text-lg font-semibold font-mono text-accent">
                {results.strengths.join(", ") || "None"}
              </dd>
            </div>
            <div className="rounded-sm border border-border-soft bg-panel p-6">
              <dt className="text-mono-xs font-medium text-muted mb-1">
                Weakest
              </dt>
              <dd className="text-lg font-semibold font-mono text-red-400">
                {results.weaknesses.join(", ") || "None"}
              </dd>
            </div>
          </div>
        </div>

        <section className="mb-10">
          <h2 className="text-xl font-semibold mb-4">Skill Performance</h2>
          <div className="rounded-sm border border-border-soft bg-panel p-8">
            <ul className="space-y-3">
              {results.skill_performance.map((sp, i) => (
                <li
                  key={i}
                  className="p-4 rounded-sm border border-border-soft bg-background"
                >
                  <div className="flex justify-between mb-1">
                    <span className="font-mono text-sm font-semibold">
                      {sp.skill_name}
                    </span>
                    <span className="text-mono-xs text-muted">
                      {sp.trend}
                    </span>
                  </div>
                  <div className="flex gap-4 text-mono-xs text-muted">
                    <span>Attempted: {sp.questions_attempted}</span>
                    <span>
                      Avg: {sp.average_score !== null ? (sp.average_score * 100).toFixed(0) + "%" : "N/A"}
                    </span>
                    <span>
                      Confidence: {sp.performance_confidence !== null ? (sp.performance_confidence * 100).toFixed(0) + "%" : "N/A"}
                    </span>
                  </div>
                </li>
              ))}
            </ul>
          </div>
        </section>

        {results.recommended_skills.length > 0 && (
          <section className="mb-10">
            <h2 className="text-xl font-semibold mb-4">Recommended Skills to Improve</h2>
            <div className="rounded-sm border border-border-soft bg-panel p-8">
              <ul className="list-disc list-inside space-y-2 text-muted text-sm">
                {results.recommended_skills.map((skill, i) => (
                  <li key={i}>{skill}</li>
                ))}
              </ul>
            </div>
          </section>
        )}

        {results.difficulty_progression.length > 0 && (
          <section className="mb-10">
            <h2 className="text-xl font-semibold mb-4">Difficulty Progression</h2>
            <div className="rounded-sm border border-border-soft bg-panel p-8">
              <div className="flex gap-2 flex-wrap">
                {results.difficulty_progression.map((d, i) => (
                  <span
                    key={i}
                    className="rounded border border-border-soft bg-background px-3 py-1 text-mono-xs"
                  >
                    {d}
                  </span>
                ))}
              </div>
            </div>
          </section>
        )}

        <div className="mt-10">
          <button
            onClick={() => {
              setResults(null);
              setSession(null);
              setSelectedCareer(null);
            }}
            className="inline-flex items-center gap-2 rounded-sm border border-border-soft bg-panel px-6 py-3 font-medium text-sm transition-colors hover:bg-panel-hover"
          >
            Start new interview
          </button>
        </div>
      </div>
    );
  }

  if (session) {
    return (
      <div className="flex flex-col min-h-[calc(100vh-4rem)] py-10 px-6 md:px-10 lg:px-12">
        <PageHeader
          title="Interview Session"
          subtitle={`Status: ${session.status} · Mode: ${session.mode} · Difficulty: ${session.difficulty}`}
        />
        <div className="mb-10">
          <div className="rounded-sm border border-border-soft bg-panel p-8 text-muted text-sm">
            <p className="mb-4">
              Session ID: {session.session_id}
            </p>
            <p className="mb-4">
              Status: {session.status}
            </p>
            <div className="flex gap-4">
              {session.status === "CREATED" && (
                <button
                  onClick={startSession}
                  className="inline-flex items-center gap-2 rounded-sm border border-border-soft bg-panel px-6 py-3 font-medium text-sm transition-colors hover:bg-panel-hover"
                >
                  Start Interview
                </button>
              )}
              {session.status === "ACTIVE" && (
                <button
                  onClick={completeSession}
                  className="inline-flex items-center gap-2 rounded-sm border border-border-soft bg-panel px-6 py-3 font-medium text-sm transition-colors hover:bg-panel-hover"
                >
                  Complete Interview
                </button>
              )}
              {session.status === "COMPLETED" && (
                <button
                  onClick={loadResults}
                  disabled={resultsLoading}
                  className="inline-flex items-center gap-2 rounded-sm border border-border-soft bg-panel px-6 py-3 font-medium text-sm transition-colors hover:bg-panel-hover disabled:opacity-50"
                >
                  {resultsLoading ? "Loading…" : "View Results"}
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col min-h-[calc(100vh-4rem)] py-10 px-6 md:px-10 lg:px-12">
      <PageHeader
        title="Interview"
        subtitle="Adaptive interview preparation grounded in your career target. Questions adapt to your skill gaps and performance."
      />

      <div className="mb-10">
        <h2 className="text-xl font-semibold mb-4">Select a target career</h2>
        <div className="grid sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          {careers.map((career) => (
            <button
              key={career.slug}
              onClick={() => createSession(career.slug)}
              disabled={creating}
              className={`group cursor-pointer rounded-sm border p-6 text-left transition-colors ${
                selectedCareer === career.slug
                  ? "border-accent bg-accent/5"
                  : "border-border-soft bg-panel hover:border-accent/50"
              }`}
            >
              <span className="font-mono text-xs font-medium text-muted uppercase tracking-tighter mb-2 block">
                {career.domain}
              </span>
              <h3 className="text-lg font-semibold mb-2 group-hover:text-accent transition-colors">
                {career.title}
              </h3>
              <p className="text-muted text-sm leading-relaxed">
                {career.summary || "No summary available."}
              </p>
            </button>
          ))}
        </div>
      </div>

      {creating && (
        <div className="mt-10 rounded-sm border border-border-soft bg-panel p-8 text-muted text-sm">
          Creating interview session…
        </div>
      )}
    </div>
  );
}
