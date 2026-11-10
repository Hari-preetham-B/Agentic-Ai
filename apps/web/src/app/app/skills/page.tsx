"use client";

import { useActiveProfile } from "@/lib/profile/context";
import { useEffect, useState } from "react";
import Link from "next/link";
import {
  listCareers,
  type CareerResponse,
  runAgentCapability,
  type SkillGapAnalysisOutput,
} from "@/lib/api/client";
import { PageHeader } from "@/components/PageHeader";

const PRIORITY_LABELS: Record<string, string> = {
  P0: "P0 — Critical",
  P1: "P1 — Important",
  P2: "P2 — Supporting",
};

const STATUS_LABELS: Record<string, string> = {
  MATCHED: "Matched",
  PARTIAL: "Partial",
  MISSING: "Missing",
};

export default function SkillsPage() {
  const [careers, setCareers] = useState<CareerResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { profileId } = useActiveProfile();
  const [selectedCareer, setSelectedCareer] = useState<string | null>(null);
  const [gapLoading, setGapLoading] = useState(false);
  const [gapResult, setGapResult] = useState<SkillGapAnalysisOutput | null>(
    null,
  );
  const [gapError, setGapError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const data = await listCareers();
        if (!cancelled) setCareers(data);
      } catch (err: unknown) {
        if (!cancelled) setError((err as Error).message);
      }
      if (!cancelled) setLoading(false);
    }
    load();
    return () => {
      cancelled = true;
    };
  }, []);

  async function analyzeGap(slug: string) {
    if (!profileId) {
      setGapError("No confirmed profile found. Build one via onboarding first.");
      return;
    }
    setGapLoading(true);
    setGapError(null);
    setGapResult(null);
    setSelectedCareer(slug);
    try {
      const result = await runAgentCapability({
        profile_id: profileId,
        capability: "skill_gap",
        input: slug,
      });
      if (result.status === "COMPLETED" && result.result) {
        setGapResult(result.result as unknown as SkillGapAnalysisOutput);
      } else {
        setGapError(result.error || "Skill gap analysis failed.");
      }
    } catch (err: unknown) {
      setGapError((err as Error).message);
    } finally {
      setGapLoading(false);
    }
  }

  if (loading) {
    return (
      <div className="flex flex-col min-h-[calc(100vh-4rem)] py-10 px-6 md:px-10 lg:px-12">
        <PageHeader title="Skill Gap" subtitle="Loading…" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col min-h-[calc(100vh-4rem)] py-10 px-6 md:px-10 lg:px-12">
        <PageHeader title="Skill Gap" subtitle="Unable to load careers." />
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
          title="Skill Gap"
          subtitle="Build your profile first to see skill-gap analysis."
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

  if (gapResult) {
    const career = careers.find((c) => c.slug === selectedCareer);
    return (
      <div className="flex flex-col min-h-[calc(100vh-4rem)] py-10 px-6 md:px-10 lg:px-12">
        <div className="flex items-center gap-2 mb-2">
          <Link
            href="/app/skills"
            className="inline-flex items-center gap-2 rounded-sm border border-border-soft bg-panel px-3 py-1 font-mono text-xs text-muted hover:bg-panel-hover"
          >
            ← Back to skills
          </Link>
        </div>
        <PageHeader
          title={career?.title || "Skill Gap Analysis"}
          subtitle={
            `Deterministic skill-gap analysis for ${career?.title || ""}. Scores are computed from stored career requirements, not estimated.`
          }
        />

        <div className="mb-10">
          <div className="flex items-center gap-6 mb-6">
            <div className="rounded-sm border border-border-soft bg-panel p-6">
              <dt className="text-mono-xs font-medium text-muted mb-1">
                Fit score
              </dt>
              <dd className="text-3xl font-semibold font-mono">
                {(gapResult.overall_score * 100).toFixed(0)}%
              </dd>
            </div>
            <div className="rounded-sm border border-border-soft bg-panel p-6">
              <dt className="text-mono-xs font-medium text-muted mb-1">
                Matched skills
              </dt>
              <dd className="text-3xl font-semibold font-mono">
                {gapResult.matched_strengths.length}
              </dd>
            </div>
            <div className="rounded-sm border border-border-soft bg-panel p-6">
              <dt className="text-mono-xs font-medium text-muted mb-1">
                Priority gaps
              </dt>
              <dd className="text-3xl font-semibold font-mono">
                {gapResult.priority_gaps.length}
              </dd>
            </div>
          </div>
        </div>

        <section className="mb-10">
          <h2 className="text-xl font-semibold mb-4">Matched Skills</h2>
          <div className="rounded-sm border border-border-soft bg-panel p-8">
            {gapResult.matched_strengths.length > 0 ? (
              <ul className="space-y-3">
                {gapResult.matched_strengths.map((s, i) => (
                  <li key={i} className="p-4 rounded-sm border border-border-soft bg-background">
                    <span className="font-mono text-sm font-semibold text-accent">
                      {STATUS_LABELS.MATCHED}
                    </span>
                    <p className="text-muted text-sm leading-relaxed mt-1">
                      {s}
                    </p>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-muted-soft text-mono-xs">
                No matched skills identified.
              </p>
            )}
          </div>
        </section>

        <section className="mb-10">
          <h2 className="text-xl font-semibold mb-4">Priority Gaps</h2>
          <div className="rounded-sm border border-border-soft bg-panel p-8">
            {gapResult.priority_gaps.length > 0 ? (
              <ul className="space-y-3">
                {gapResult.priority_gaps.map((gap, i) => {
                  const priorityMatch = gap.match(/^(P\d)/);
                  const priority = priorityMatch ? priorityMatch[1] : "P2";
                  return (
                    <li
                      key={i}
                      className="p-4 rounded-sm border border-border-soft bg-background"
                    >
                      <div className="flex justify-between mb-1">
                        <span className="font-mono text-sm font-semibold">
                          {STATUS_LABELS.MISSING}
                        </span>
                        <span
                          className={`text-mono-xs font-medium px-2 py-0.5 rounded border ${
                            priority === "P0"
                              ? "bg-red/10 border-red/30 text-red"
                              : priority === "P1"
                              ? "bg-amber/10 border-amber/30 text-amber"
                              : "bg-muted/10 border-muted/30 text-muted"
                          }`}
                        >
                          {PRIORITY_LABELS[priority]}
                        </span>
                      </div>
                      <p className="text-muted text-sm leading-relaxed">{gap}</p>
                    </li>
                  );
                })}
              </ul>
            ) : (
              <p className="text-muted-soft text-mono-xs">
                No priority gaps identified.
              </p>
            )}
          </div>
        </section>

        <section className="mb-10">
          <h2 className="text-xl font-semibold mb-4">Recommendations</h2>
          <div className="rounded-sm border border-border-soft bg-panel p-8">
            {gapResult.recommendations.length > 0 ? (
              <ol className="list-decimal list-inside space-y-3 text-muted text-sm leading-relaxed">
                {gapResult.recommendations.map((r, i) => (
                  <li key={i}>{r}</li>
                ))}
              </ol>
            ) : (
              <p className="text-muted-soft text-mono-xs">
                No specific recommendations.
              </p>
            )}
          </div>
        </section>

        {gapResult.caveats && gapResult.caveats.length > 0 && (
          <section className="mb-10">
            <h2 className="text-xl font-semibold mb-4">Caveats</h2>
            <div className="rounded-sm border border-border-soft bg-panel p-8">
              <ul className="space-y-2 text-muted-soft text-mono-xs">
                {gapResult.caveats.map((c, i) => (
                  <li key={i}>{c}</li>
                ))}
              </ul>
            </div>
          </section>
        )}
      </div>
    );
  }

  return (
    <div className="flex flex-col min-h-[calc(100vh-4rem)] py-10 px-6 md:px-10 lg:px-12">
      <PageHeader
        title="Skill Gap"
        subtitle="Compare your confirmed profile against career requirements to see matched, partial, and missing skills."
      />

      <div className="mb-10">
        <h2 className="text-xl font-semibold mb-4">Select a target career</h2>
        <div className="grid sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          {careers.map((career) => (
            <button
              key={career.slug}
              onClick={() => analyzeGap(career.slug)}
              disabled={gapLoading}
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

      {gapLoading && (
        <div className="mt-10 rounded-sm border border-border-soft bg-panel p-8 text-muted text-sm">
          Analyzing skill gaps…
        </div>
      )}

      {gapError && careers.length > 0 && (
        <div className="mt-10 rounded-sm border border-border-soft bg-red/10 border-red/30 p-8 text-red text-sm">
          {gapError}
        </div>
      )}
    </div>
  );
}