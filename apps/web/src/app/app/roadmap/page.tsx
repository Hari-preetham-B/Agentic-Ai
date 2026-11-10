"use client";

import { useActiveProfile } from "@/lib/profile/context";
import { useEffect, useState } from "react";
import Link from "next/link";
import {
  listCareers,
  type CareerResponse,
  runAgentCapability,
  updateRoadmapItemProgress,
} from "@/lib/api/client";
import { PageHeader } from "@/components/PageHeader";

interface RoadmapItem {
  id?: string;
  skill_name: string;
  priority: string;
  sequence_order: number;
  status: string;
  rationale: string | null;
  estimated_hours: number | null;
  current_proficiency: string | null;
  target_proficiency: string | null;
  prerequisites: string[] | null;
  resources: {
    id: string;
    title: string;
    provider: string;
    resource_type: string;
    url: string | null;
    difficulty: string | null;
    estimated_hours: number | null;
    relevance_score: number | null;
  }[];
}

interface RoadmapOutput {
  roadmap_id: string;
  profile_id: string;
  career_id: string;
  career_title: string;
  items: RoadmapItem[];
  summary: {
    total_skills: number;
    p0_count: number;
    p1_count: number;
    p2_count: number;
    total_estimated_hours: number;
  };
}

const PRIORITY_LABELS: Record<string, { label: string; color: string }> = {
  P0: { label: "P0 — Critical", color: "text-white border-red-600 bg-red-600" },
  P1: { label: "P1 — Important", color: "text-red-700 border-red-200 bg-red-50" },
  P2: { label: "P2 — Supporting", color: "text-muted border-muted/20 bg-muted/10" },
};

export default function RoadmapPage() {
  const [careers, setCareers] = useState<CareerResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { profileId } = useActiveProfile();
  const [selectedCareer, setSelectedCareer] = useState<string | null>(null);
  const [roadmapLoading, setRoadmapLoading] = useState(false);
  const [roadmapResult, setRoadmapResult] = useState<RoadmapOutput | null>(null);
  const [roadmapError, setRoadmapError] = useState<string | null>(null);
  const [busyItemId, setBusyItemId] = useState<string | null>(null);
  const [progressError, setProgressError] = useState<string | null>(null);

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

  async function setItemStatus(
    itemId: string,
    status: "PENDING" | "IN_PROGRESS" | "COMPLETED",
  ) {
    if (!roadmapResult) return;
    setBusyItemId(itemId);
    setProgressError(null);
    try {
      await updateRoadmapItemProgress(roadmapResult.roadmap_id, itemId, status);
      setRoadmapResult((current) =>
        current
          ? {
              ...current,
              items: current.items.map((it) =>
                it.id === itemId ? { ...it, status } : it,
              ),
            }
          : current,
      );
    } catch (err: unknown) {
      setProgressError((err as Error).message || "Could not update progress.");
    } finally {
      setBusyItemId(null);
    }
  }

  async function generateRoadmap(slug: string) {
    if (!profileId) {
      setRoadmapError("No confirmed profile found. Build one via onboarding first.");
      return;
    }
    setRoadmapLoading(true);
    setRoadmapError(null);
    setRoadmapResult(null);
    setSelectedCareer(slug);
    try {
      const result = await runAgentCapability({
        profile_id: profileId,
        capability: "learning_roadmap",
        input: slug,
      });
      if (result.status === "COMPLETED" && result.result) {
        setRoadmapResult(result.result as unknown as RoadmapOutput);
      } else {
        setRoadmapError(result.error || "Roadmap generation failed.");
      }
    } catch (err: unknown) {
      setRoadmapError((err as Error).message);
    } finally {
      setRoadmapLoading(false);
    }
  }

  if (loading) {
    return (
      <div className="flex flex-col min-h-[calc(100vh-4rem)] py-10 px-6 md:px-10 lg:px-12">
        <PageHeader title="Learning Roadmap" subtitle="Loading…" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col min-h-[calc(100vh-4rem)] py-10 px-6 md:px-10 lg:px-12">
        <PageHeader title="Learning Roadmap" subtitle="Unable to load careers." />
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
          title="Learning Roadmap"
          subtitle="Build your profile first to generate a learning roadmap."
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

  if (roadmapResult) {
    const career = careers.find((c) => c.slug === selectedCareer);
    return (
      <div className="flex flex-col min-h-[calc(100vh-4rem)] py-10 px-6 md:px-10 lg:px-12">
        <div className="flex items-center gap-2 mb-2">
          <Link
            href="/app/roadmap"
            className="inline-flex items-center gap-2 rounded-sm border border-border-soft bg-panel px-3 py-1 font-mono text-xs text-muted hover:bg-panel-hover"
          >
            ← Back to roadmap
          </Link>
        </div>
        <PageHeader
          title={career?.title || "Learning Roadmap"}
          subtitle={
            `Dependency-aware learning roadmap for ${career?.title || ""}. Sequence and priorities are computed deterministically.`
          }
        />

        <div className="mb-10">
          <div className="flex flex-wrap items-center gap-6 mb-6">
            <div className="rounded-sm border border-border-soft bg-panel p-6">
              <dt className="text-mono-xs font-medium text-muted mb-1">
                Skills to learn
              </dt>
              <dd className="text-3xl font-semibold font-mono">
                {roadmapResult.summary.total_skills}
              </dd>
            </div>
            <div className="rounded-sm border border-border-soft bg-panel p-6">
              <dt className="text-mono-xs font-medium text-muted mb-1">
                Critical (P0)
              </dt>
              <dd className="text-3xl font-semibold font-mono text-red-600">
                {roadmapResult.summary.p0_count}
              </dd>
            </div>
            <div className="rounded-sm border border-border-soft bg-panel p-6">
              <dt className="text-mono-xs font-medium text-muted mb-1">
                Important (P1)
              </dt>
              <dd className="text-3xl font-semibold font-mono text-red-400">
                {roadmapResult.summary.p1_count}
              </dd>
            </div>
            <div className="rounded-sm border border-border-soft bg-panel p-6">
              <dt className="text-mono-xs font-medium text-muted mb-1">
                Supporting (P2)
              </dt>
              <dd className="text-3xl font-semibold font-mono text-muted">
                {roadmapResult.summary.p2_count}
              </dd>
            </div>
            <div className="rounded-sm border border-border-soft bg-panel p-6">
              <dt className="text-mono-xs font-medium text-muted mb-1">
                Est. hours
              </dt>
              <dd className="text-3xl font-semibold font-mono">
                {roadmapResult.summary.total_estimated_hours}
              </dd>
            </div>
          </div>
        </div>

        {progressError && (
          <div className="mb-6 rounded-sm border border-red-200 bg-red-50 p-4 text-sm text-red-700">
            {progressError}
          </div>
        )}

        <div className="relative mb-10">
          {roadmapResult.items.map((item, index) => {
            const priorityConfig = PRIORITY_LABELS[item.priority] || PRIORITY_LABELS.P2;
            return (
              <div key={item.id ?? `${item.skill_name}-${index}`} className="relative flex gap-6 mb-8">
                {/* Connector line */}
                {index < roadmapResult.items.length - 1 && (
                  <div className="absolute left-8 top-16 bottom-0 w-px bg-border-soft" />
                )}
                {/* Sequence number */}
                <div className="flex-shrink-0 w-16 h-16 rounded-sm border border-border-soft bg-panel flex items-center justify-center">
                  <span className="font-mono text-lg font-semibold text-muted">
                    {String(item.sequence_order + 1).padStart(2, "0")}
                  </span>
                </div>
                {/* Content */}
                <div className="flex-1 rounded-sm border border-border-soft bg-panel p-6">
                  <div className="flex items-start justify-between mb-2">
                    <h3 className="text-lg font-semibold">{item.skill_name}</h3>
                    <span
                      className={`text-mono-xs font-medium px-2 py-0.5 rounded border ${priorityConfig.color}`}
                    >
                      {priorityConfig.label}
                    </span>
                  </div>
                  {item.rationale && (
                    <p className="text-muted text-sm leading-relaxed mb-3">
                      {item.rationale}
                    </p>
                  )}
                  <div className="flex flex-wrap gap-4 text-mono-xs text-muted mb-3">
                    {item.current_proficiency && (
                      <span>
                        Current: {item.current_proficiency}
                      </span>
                    )}
                    {item.target_proficiency && (
                      <span>Target: {item.target_proficiency}</span>
                    )}
                    {item.estimated_hours && (
                      <span>Est. {item.estimated_hours}h</span>
                    )}
                    {item.prerequisites && item.prerequisites.length > 0 && (
                      <span>
                        Prereqs: {item.prerequisites.join(", ")}
                      </span>
                    )}
                  </div>
                  {item.id && (
                    <div className="flex flex-wrap items-center gap-2 mb-3">
                      <span className="text-mono-xs text-muted mr-2">
                        Status: {item.status.replace("_", " ")}
                      </span>
                      {(["PENDING", "IN_PROGRESS", "COMPLETED"] as const).map((st) => (
                        <button
                          key={st}
                          type="button"
                          disabled={busyItemId === item.id || item.status === st}
                          onClick={() => setItemStatus(item.id as string, st)}
                          className="rounded-sm border border-border-soft px-3 py-1 text-mono-xs transition-colors hover:bg-panel-hover disabled:cursor-default disabled:opacity-40"
                        >
                          {st === "PENDING" ? "Not started" : st === "IN_PROGRESS" ? "In progress" : "Done"}
                        </button>
                      ))}
                    </div>
                  )}
                  {item.resources && item.resources.length > 0 && (
                    <div className="mt-3 pt-3 border-t border-border-soft">
                      <span className="text-mono-xs font-medium text-muted mb-2 block">
                        Recommended resources
                      </span>
                      <ul className="space-y-2">
                        {item.resources.map((res) => (
                          <li
                            key={res.id}
                            className="flex items-center justify-between text-mono-xs"
                          >
                            <span className="text-muted">{res.title}</span>
                            <span className="text-muted-soft">
                              {res.provider} &bull; {res.resource_type}
                              {res.estimated_hours ? ` &bull; ${res.estimated_hours}h` : ""}
                            </span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col min-h-[calc(100vh-4rem)] py-10 px-6 md:px-10 lg:px-12">
      <PageHeader
        title="Learning Roadmap"
        subtitle="Dependency-aware learning paths from your skill gaps to career readiness. Sequence and priorities are computed deterministically."
      />

      <div className="mb-10">
        <h2 className="text-xl font-semibold mb-4">Select a target career</h2>
        <div className="grid sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          {careers.map((career) => (
            <button
              key={career.slug}
              onClick={() => generateRoadmap(career.slug)}
              disabled={roadmapLoading}
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

      {roadmapLoading && (
        <div className="mt-10 rounded-sm border border-border-soft bg-panel p-8 text-muted text-sm">
          Generating learning roadmap…
        </div>
      )}

      {roadmapError && careers.length > 0 && (
        <div className="mt-10 rounded-sm border border-border-soft bg-red/10 border-red/30 p-8 text-red text-sm">
          {roadmapError}
        </div>
      )}
    </div>
  );
}
