"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  getCareerTwinState,
  type CareerTwinState,
} from "@/lib/api/client";
import { Section } from "@/components/Section";
import { StatusBadge } from "@/components/StatusBadge";
import { PageHeader } from "@/components/PageHeader";
import { Rule } from "@/components/Rule";

const READINESS_LABELS: Record<string, string> = {
  NOT_READY: "Not ready",
  EARLY: "Early",
  DEVELOPING: "Developing",
  COMPETITIVE: "Competitive",
  STRONG: "Strong",
};

export default function TwinPage() {
  const [profileId] = useState<string | null>(() => {
    if (typeof window !== "undefined") {
      return localStorage.getItem("ct:profileId");
    }
    return null;
  });
  const [state, setState] = useState<CareerTwinState | null>(null);
  const [loading, setLoading] = useState(() => !!profileId);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!profileId) return;
    let cancelled = false;
    async function load() {
      try {
        const data = await getCareerTwinState(profileId!);
        if (!cancelled) setState(data);
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
  }, [profileId]);

  if (loading) {
    return (
      <div className="flex flex-col min-h-[calc(100vh-4rem)] py-10 px-6 md:px-10 lg:px-12">
        <PageHeader title="Your CareerTwin" subtitle="Loading…" />
      </div>
    );
  }

  if (!profileId) {
    return (
      <div className="flex flex-col min-h-[calc(100vh-4rem)] py-10 px-6 md:px-10 lg:px-12">
        <PageHeader
          title="Your CareerTwin"
          subtitle="No profile found. Build one via onboarding to see it here."
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

  if (error) {
    return (
      <div className="flex flex-col min-h-[calc(100vh-4rem)] py-10 px-6 md:px-10 lg:px-12">
        <PageHeader title="Your CareerTwin" subtitle="Unable to load state." />
        <div className="rounded-sm border border-border-soft bg-panel p-8 text-muted text-sm">
          {error}
        </div>
      </div>
    );
  }

  if (!state) {
    return (
      <div className="flex flex-col min-h-[calc(100vh-4rem)] py-10 px-6 md:px-10 lg:px-12">
        <PageHeader title="Your CareerTwin" subtitle="No state available." />
      </div>
    );
  }

  const topInsights = state.insights.slice(0, 5);
  const topGaps = state.skill_gaps
    .filter((g) => g.status === "MISSING")
    .slice(0, 5);

  return (
    <div className="flex flex-col min-h-[calc(100vh-4rem)] py-10 px-6 md:px-10 lg:px-12">
      <div className="flex items-center gap-2 mb-2">
        <StatusBadge>CAREERTWIN — UNIFIED STATE</StatusBadge>
      </div>
      <PageHeader
        title="Your Career. Understood."
        subtitle={state.headline || "Your evolving career intelligence system."}
      />

      <Section className="grid md:grid-cols-3 gap-6 mb-10">
        <div className="rounded-sm border border-border-soft bg-panel p-6">
          <dt className="text-mono-xs font-medium text-muted mb-1">
            Active career
          </dt>
          <dd className="font-mono text-sm font-semibold">
            {state.active_target_career || "Not set"}
          </dd>
        </div>
        <div className="rounded-sm border border-border-soft bg-panel p-6">
          <dt className="text-mono-xs font-medium text-muted mb-1">
            Readiness
          </dt>
          <dd className="font-mono text-sm font-semibold">
            {READINESS_LABELS[state.readiness_level] || state.readiness_level}{" "}
            ({(state.readiness_score * 100).toFixed(0)}%)
          </dd>
        </div>
        <div className="rounded-sm border border-border-soft bg-panel p-6">
          <dt className="text-mono-xs font-medium text-muted mb-1">
            Skills
          </dt>
          <dd className="text-2xl font-semibold">
            {state.confirmed_skills.length}
          </dd>
        </div>
      </Section>

      <Section className="mb-10">
        <h2 className="text-xl font-semibold mb-4">Current Signal</h2>
        <div className="grid md:grid-cols-2 gap-6">
          <div className="rounded-sm border border-border-soft bg-panel p-6">
            <h3 className="text-sm font-semibold mb-2 text-muted">
              Strongest skill
            </h3>
            <p className="font-mono text-sm">
              {state.confirmed_skills.length > 0
                ? state.confirmed_skills[0].name
                : "None"}
            </p>
          </div>
          <div className="rounded-sm border border-border-soft bg-panel p-6">
            <h3 className="text-sm font-semibold mb-2 text-muted">
              Biggest gap
            </h3>
            <p className="font-mono text-sm">
              {topGaps.length > 0 ? topGaps[0].skill_name : "None"}
            </p>
          </div>
          <div className="rounded-sm border border-border-soft bg-panel p-6">
            <h3 className="text-sm font-semibold mb-2 text-muted">
              Interview weakness
            </h3>
            <p className="font-mono text-sm">
              {state.interview_summary.weaknesses.length > 0
                ? state.interview_summary.weaknesses[0]
                : "None"}
            </p>
          </div>
          <div className="rounded-sm border border-border-soft bg-panel p-6">
            <h3 className="text-sm font-semibold mb-2 text-muted">
              Roadmap priority
            </h3>
            <p className="font-mono text-sm">
              {state.roadmap_summary.p0_count > 0
                ? `${state.roadmap_summary.p0_count} critical items`
                : "No roadmap"}
            </p>
          </div>
        </div>
      </Section>

      {state.career_fit && (
        <Section className="mb-10">
          <h2 className="text-xl font-semibold mb-4">Career Position</h2>
          <div className="rounded-sm border border-border-soft bg-panel p-8">
            <div className="mb-4">
              <div className="flex justify-between text-mono-xs text-muted mb-1">
                <span>Fit score</span>
                <span>{(state.career_fit.fit_score * 100).toFixed(0)}%</span>
              </div>
              <div className="h-2 rounded bg-background overflow-hidden">
                <div
                  className="h-full bg-accent transition-all"
                  style={{ width: `${state.career_fit.fit_score * 100}%` }}
                />
              </div>
            </div>
            <p className="text-muted text-sm leading-relaxed">
              {state.career_fit.rationale}
            </p>
          </div>
        </Section>
      )}

      {topGaps.length > 0 && (
        <Section className="mb-10">
          <h2 className="text-xl font-semibold mb-4">Skill Gaps</h2>
          <div className="rounded-sm border border-border-soft bg-panel p-8">
            <ul className="space-y-3">
              {topGaps.map((gap, i) => (
                <li
                  key={i}
                  className="p-4 rounded-sm border border-border-soft bg-background"
                >
                  <div className="flex justify-between mb-1">
                    <span className="font-mono text-sm font-semibold">
                      {gap.skill_name}
                    </span>
                    <span className="text-mono-xs text-muted">
                      {gap.importance}
                    </span>
                  </div>
                  <p className="text-muted-soft text-mono-xs">
                    {gap.status} — {gap.current_level || "not listed"} →{" "}
                    {gap.required_level || "unspecified"}
                  </p>
                </li>
              ))}
            </ul>
          </div>
        </Section>
      )}

      {topInsights.length > 0 && (
        <Section className="mb-10">
          <h2 className="text-xl font-semibold mb-4">Insights</h2>
          <div className="rounded-sm border border-border-soft bg-panel p-8">
            <ul className="space-y-3">
              {topInsights.map((insight, i) => (
                <li
                  key={i}
                  className="p-4 rounded-sm border border-border-soft bg-background"
                >
                  <div className="flex justify-between mb-1">
                    <span className="font-mono text-sm font-semibold">
                      {insight.title}
                    </span>
                    <span className="text-mono-xs text-muted">
                      {insight.severity}
                    </span>
                  </div>
                  <p className="text-muted text-sm leading-relaxed">
                    {insight.reason}
                  </p>
                  {insight.recommended_action && (
                    <p className="mt-2 text-mono-xs text-accent">
                      {insight.recommended_action}
                    </p>
                  )}
                </li>
              ))}
            </ul>
          </div>
        </Section>
      )}

      {state.conflicts.length > 0 && (
        <Section className="mb-10">
          <h2 className="text-xl font-semibold mb-4">Conflicts</h2>
          <div className="rounded-sm border border-border-soft bg-panel p-8">
            <ul className="space-y-3">
              {state.conflicts.map((conflict, i) => (
                <li
                  key={i}
                  className="p-4 rounded-sm border border-border-soft bg-background"
                >
                  <div className="flex justify-between mb-1">
                    <span className="font-mono text-sm font-semibold">
                      {conflict.title}
                    </span>
                    <span className="text-mono-xs text-muted">
                      {conflict.severity}
                    </span>
                  </div>
                  <p className="text-muted text-sm leading-relaxed">
                    {conflict.description}
                  </p>
                  {conflict.resolution && (
                    <p className="mt-2 text-mono-xs text-muted">
                      {conflict.resolution}
                    </p>
                  )}
                </li>
              ))}
            </ul>
          </div>
        </Section>
      )}

      <Rule />
      <Section className="flex gap-4">
        <Link
          href="/app/careers"
          className="inline-flex items-center gap-2 rounded-sm border border-border-soft bg-panel px-6 py-3 font-medium text-sm transition-colors hover:bg-panel-hover"
        >
          Career Intelligence
        </Link>
        <Link
          href="/app/skills"
          className="inline-flex items-center gap-2 rounded-sm border border-border-soft bg-panel px-6 py-3 font-medium text-sm transition-colors hover:bg-panel-hover"
        >
          Skill Gap
        </Link>
        <Link
          href="/app/roadmap"
          className="inline-flex items-center gap-2 rounded-sm border border-border-soft bg-panel px-6 py-3 font-medium text-sm transition-colors hover:bg-panel-hover"
        >
          Learning Roadmap
        </Link>
        <Link
          href="/app/interview"
          className="inline-flex items-center gap-2 rounded-sm border border-border-soft bg-panel px-6 py-3 font-medium text-sm transition-colors hover:bg-panel-hover"
        >
          Interview
        </Link>
      </Section>
    </div>
  );
}
