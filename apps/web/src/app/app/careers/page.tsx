"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import {
  listCareers,
  getCareer,
  type CareerResponse,
} from "@/lib/api/client";
import { Section } from "@/components/Section";
import { PageHeader } from "@/components/PageHeader";

const IMPORTANCE_LABELS: Record<string, string> = {
  CORE: "Core",
  IMPORTANT: "Important",
  SUPPORTING: "Supporting",
};

const LEVEL_LABELS: Record<string, string> = {
  BEGINNER: "Beginner",
  INTERMEDIATE: "Intermediate",
  ADVANCED: "Advanced",
  EXPERT: "Expert",
};

export default function CareersPage() {
  const [careers, setCareers] = useState<CareerResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [detailCareer, setDetailCareer] = useState<CareerResponse | null>(
    null,
  );
  const [detailLoading, setDetailLoading] = useState(false);

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

  async function loadDetail(slug: string) {
    setDetailLoading(true);
    try {
      const career = await getCareer(slug);
      setDetailCareer(career);
    } catch (err: unknown) {
      setError((err as Error).message);
      setDetailCareer(null);
    } finally {
      setDetailLoading(false);
    }
  }

  if (loading) {
    return (
      <div className="flex flex-col min-h-[calc(100vh-4rem)] py-10 px-6 md:px-10 lg:px-12">
        <PageHeader title="Career Intelligence" subtitle="Loading…" />
      </div>
    );
  }

  if (error && careers.length === 0) {
    return (
      <div className="flex flex-col min-h-[calc(100vh-4rem)] py-10 px-6 md:px-10 lg:px-12">
        <PageHeader
          title="Career Intelligence"
          subtitle="Unable to load career data."
        />
        <div className="rounded-sm border border-border-soft bg-panel p-8 text-muted text-sm">
          {error}
        </div>
      </div>
    );
  }

  if (detailCareer && detailLoading === false) {
    return (
      <div className="flex flex-col min-h-[calc(100vh-4rem)] py-10 px-6 md:px-10 lg:px-12">
        <div className="flex items-center gap-2 mb-2">
          <Link
            href="/app/careers"
            className="inline-flex items-center gap-2 rounded-sm border border-border-soft bg-panel px-3 py-1 font-mono text-xs text-muted hover:bg-panel-hover"
          >
            ← Back to careers
          </Link>
          <Link
            href={`/app/roadmap`}
            className="inline-flex items-center gap-2 rounded-sm border border-border-soft bg-panel px-3 py-1 font-mono text-xs text-muted hover:bg-panel-hover"
          >
            Build roadmap →
          </Link>
        </div>
        <PageHeader
          title={detailCareer.title}
          subtitle={detailCareer.summary || undefined}
        />
        <dl className="grid md:grid-cols-3 gap-6 mb-10">
          <div className="rounded-sm border border-border-soft bg-panel p-6">
            <dt className="text-mono-xs font-medium text-muted mb-1">Domain</dt>
            <dd className="font-mono text-sm font-semibold">
              {detailCareer.domain}
            </dd>
          </div>
          <div className="rounded-sm border border-border-soft bg-panel p-6">
            <dt className="text-mono-xs font-medium text-muted mb-1">Slug</dt>
            <dd className="font-mono text-mono-xs text-muted">
              {detailCareer.slug}
            </dd>
          </div>
        </dl>

        <section className="mb-10">
          <h2 className="text-xl font-semibold mb-4">Description</h2>
          <div className="rounded-sm border border-border-soft bg-panel p-8">
            <p className="text-muted text-sm leading-relaxed">
              {detailCareer.description || "No description available."}
            </p>
          </div>
        </section>

        <section className="mb-10">
          <h2 className="text-xl font-semibold mb-4">Core Skills</h2>
          <div className="rounded-sm border border-border-soft bg-panel p-8">
            <ul className="grid sm:grid-cols-2 md:grid-cols-3 gap-4">
              {detailCareer.skills
                .filter((s) => s.importance === "CORE")
                .map((s) => (
                  <li
                    key={`${s.skill_name}-${s.category}`}
                    className="rounded-sm border border-border-soft bg-background p-4"
                  >
                    <div className="flex justify-between mb-1">
                      <span className="font-mono text-sm font-semibold">
                        {s.skill_name}
                      </span>
                      <span className="text-mono-xs text-muted">
                        {IMPORTANCE_LABELS[s.importance]}
                      </span>
                    </div>
                    <p className="text-muted-soft text-mono-xs leading-relaxed">
                      {s.description || ""}
                    </p>
                    {s.minimum_level && (
                      <p className="mt-2 text-mono-xs text-muted">
                        Minimum level: {LEVEL_LABELS[s.minimum_level]}
                      </p>
                    )}
                  </li>
                ))}
            </ul>
          </div>
        </section>

        <section className="mb-10">
          <h2 className="text-xl font-semibold mb-4">Important Skills</h2>
          <div className="rounded-sm border border-border-soft bg-panel p-8">
            <ul className="grid sm:grid-cols-2 md:grid-cols-3 gap-4">
              {detailCareer.skills
                .filter((s) => s.importance === "IMPORTANT")
                .map((s) => (
                  <li
                    key={`${s.skill_name}-${s.category}`}
                    className="rounded-sm border border-border-soft bg-background p-4"
                  >
                    <div className="flex justify-between mb-1">
                      <span className="font-mono text-sm font-semibold">
                        {s.skill_name}
                      </span>
                      <span className="text-mono-xs text-muted">
                        {IMPORTANCE_LABELS[s.importance]}
                      </span>
                    </div>
                    <p className="text-muted-soft text-mono-xs leading-relaxed">
                      {s.description || ""}
                    </p>
                  </li>
                ))}
            </ul>
          </div>
        </section>

        <section className="mb-10">
          <h2 className="text-xl font-semibold mb-4">Tools</h2>
          <div className="rounded-sm border border-border-soft bg-panel p-8">
            <ul className="grid sm:grid-cols-2 md:grid-cols-4 gap-4">
              {detailCareer.tools.map((t) => (
                <li
                  key={t.tool_name}
                  className="rounded-sm border border-border-soft bg-background p-4"
                >
                  <span className="font-mono text-sm font-semibold">
                    {t.tool_name}
                  </span>
                  <span className="text-mono-xs text-muted block mt-1">
                    {t.importance}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        </section>

        <section className="mb-10">
          <h2 className="text-xl font-semibold mb-4">Typical Projects</h2>
          <div className="rounded-sm border border-border-soft bg-panel p-8">
            <ul className="space-y-4">
              {detailCareer.projects.map((p) => (
                <li key={p.project_type} className="p-4 rounded-sm border border-border-soft bg-background">
                  <div className="flex justify-between mb-1">
                    <span className="font-mono text-sm font-semibold">
                      {p.project_type}
                    </span>
                    <span className="text-mono-xs text-muted">
                      {p.difficulty || ""}
                    </span>
                  </div>
                  <p className="text-muted text-sm leading-relaxed">
                    {p.description}
                  </p>
                  {p.skills_demonstrated && p.skills_demonstrated.length > 0 && (
                    <div className="mt-2 flex gap-2 flex-wrap">
                      {p.skills_demonstrated.map((skill) => (
                        <span
                          key={skill}
                          className="rounded border border-border-soft bg-panel px-2 py-0.5 text-mono-xs text-muted"
                        >
                          {skill}
                        </span>
                      ))}
                    </div>
                  )}
                </li>
              ))}
            </ul>
          </div>
        </section>

        <section className="mb-10">
          <h2 className="text-xl font-semibold mb-4">Sources</h2>
          <div className="rounded-sm border border-border-soft bg-panel p-8">
            <ul className="space-y-4">
              {detailCareer.sources.map((src) => (
                <li key={src.title} className="p-4 rounded-sm border border-border-soft bg-background">
                  <div className="flex justify-between mb-1">
                    <span className="font-mono text-sm font-semibold">
                      {src.title}
                    </span>
                    <span className="text-mono-xs text-muted">
                      {src.reliability}
                    </span>
                  </div>
                  <p className="text-muted-soft text-mono-xs text-sm">
                    {src.publisher}
                  </p>
                  {src.url && (
                    <a
                      href={src.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="mt-1 inline-block text-mono-xs text-accent hover:underline"
                    >
                      View source →
                    </a>
                  )}
                </li>
              ))}
            </ul>
          </div>
        </section>
      </div>
    );
  }

  return (
    <div className="flex flex-col min-h-[calc(100vh-4rem)] py-10 px-6 md:px-10 lg:px-12">
      <PageHeader
        title="Career Intelligence"
        subtitle="Where your current profile meets the requirements of the roles you are considering."
      />

      <Section className="grid sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
        {careers.map((career) => (
          <motion.div
            key={career.slug}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="group cursor-pointer rounded-sm border border-border-soft bg-panel p-6 hover:border-accent/50 transition-colors"
            onClick={() => loadDetail(career.slug)}
          >
            <div className="flex items-start justify-between mb-3">
              <span className="font-mono text-xs font-medium text-muted uppercase tracking-tighter">
                {career.domain}
              </span>
            </div>
            <h3 className="text-lg font-semibold mb-2 group-hover:text-accent transition-colors">
              {career.title}
            </h3>
            <p className="text-muted text-sm leading-relaxed mb-4">
              {career.summary || "No summary available."}
            </p>
            <div className="flex flex-wrap gap-2">
              {career.skills
                .filter((s) => s.importance === "CORE")
                .slice(0, 3)
                .map((s) => (
                  <span
                    key={s.skill_name}
                    className="rounded border border-border-soft bg-background px-2 py-0.5 text-mono-xs text-muted"
                  >
                    {s.skill_name}
                  </span>
                ))}
            </div>
          </motion.div>
        ))}
      </Section>

      {careers.length === 0 && (
        <div className="mt-10 rounded-sm border border-border-soft bg-panel p-8 text-muted text-sm text-center">
          No career profiles available yet.
        </div>
      )}
    </div>
  );
}