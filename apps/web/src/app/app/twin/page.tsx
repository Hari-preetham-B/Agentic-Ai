"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import {
  getProfileDetail,
  type ProfileDetail,
} from "@/lib/api/client";
import { Section } from "@/components/Section";
import { StatusBadge } from "@/components/StatusBadge";
import { PageHeader } from "@/components/PageHeader";
import { Rule } from "@/components/Rule";

const STATUS_LABELS: Record<string, string> = {
  DRAFT: "Draft — not yet confirmed",
  REVIEW: "In review",
  CONFIRMED: "Confirmed",
};

export default function TwinPage() {
  const [profile, setProfile] = useState<ProfileDetail | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const id = localStorage.getItem("ct:profileId");
        if (!id) {
          setLoading(false);
          return;
        }
        const detail = await getProfileDetail(id);
        setProfile(detail);
      } catch {
        // Profile may not exist yet; that's fine — show empty state.
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, []);

  const skillCount = profile?.skills?.length ?? 0;
  const projectCount = profile?.projects?.length ?? 0;
  const experienceCount = profile?.experience?.length ?? 0;

  return (
    <div className="flex flex-col min-h-[calc(100vh-4rem)] py-10 px-6 md:px-10 lg:px-12">
      <div className="flex items-center gap-2 mb-2">
        <StatusBadge>CAREERTWIN — OVERVIEW</StatusBadge>
      </div>
      {loading ? (
        <PageHeader title="Your CareerTwin" subtitle="Loading…" />
      ) : !profile ? (
        <PageHeader
          title="Your CareerTwin"
          subtitle="No profile found. Build one via onboarding to see it here."
        />
      ) : (
        <>
          <PageHeader
            title={profile.full_name || "Your CareerTwin"}
            subtitle={profile.headline || "Your evolving career intelligence system."}
          />

          <dl className="grid md:grid-cols-3 gap-6 mb-10">
            <div className="rounded-sm border border-border-soft bg-panel p-6">
              <dt className="text-mono-xs font-medium text-muted mb-1">Status</dt>
              <dd className="font-mono text-sm font-semibold">
                {STATUS_LABELS[profile.profile_status] || profile.profile_status}
              </dd>
            </div>
            <div className="rounded-sm border border-border-soft bg-panel p-6">
              <dt className="text-mono-xs font-medium text-muted mb-1">Skills</dt>
              <dd className="text-2xl font-semibold">{skillCount}</dd>
            </div>
            <div className="rounded-sm border border-border-soft bg-panel p-6">
              <dt className="text-mono-xs font-medium text-muted mb-1">
                Projects
              </dt>
              <dd className="text-2xl font-semibold">{projectCount}</dd>
            </div>
            <div className="rounded-sm border border-border-soft bg-panel p-6">
              <dt className="text-mono-xs font-medium text-muted mb-1">
                Experience
              </dt>
              <dd className="text-2xl font-semibold">{experienceCount}</dd>
            </div>
          </dl>

          {profile.summary && (
            <section className="rounded-sm border border-border-soft bg-panel p-8 mb-10">
              <h2 className="text-xl font-semibold mb-3">Summary</h2>
              <p className="text-muted text-sm leading-relaxed">
                {profile.summary}
              </p>
            </section>
          )}

          <Section className="grid md:grid-cols-2 gap-8">
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="rounded-sm border border-border-soft bg-panel p-8"
            >
              <h2 className="text-xl font-semibold mb-3">Education overview</h2>
              {profile.education?.length ? (
                <ul className="text-muted text-sm space-y-3">
                  {profile.education.map((e) => (
                    <li key={e.id} className="flex justify-between">
                      <span>{e.institution}</span>
                      <span className="font-mono text-mono-xs text-muted">
                        {e.degree || ""}
                      </span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-muted-soft text-mono-xs">None added yet.</p>
              )}
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="rounded-sm border border-border-soft bg-panel p-8"
              style={{ animationDelay: "0.08s" }}
            >
              <h2 className="text-xl font-semibold mb-3">Career goal</h2>
              {profile.career_goals?.length ? (
                <div className="text-muted text-sm leading-relaxed">
                  {profile.career_goals[0].target_role}
                  {profile.career_goals[0].goal_description && (
                    <>
                      <br />
                      <span className="text-muted-soft text-mono-xs">
                        {profile.career_goals[0].goal_description}
                      </span>
                    </>
                  )}
                </div>
              ) : (
                <p className="text-muted-soft text-mono-xs">None set yet.</p>
              )}
            </motion.div>
          </Section>

          <Rule />

          <section className="mb-10">
            <h2 className="text-xl font-semibold mb-4">Career intelligence</h2>
            <div className="rounded-sm border border-border-soft bg-background p-8 text-muted text-sm leading-relaxed">
              Coming after profile analysis.<br />
              Your confirmed CareerTwin will power career-path recommendations
              and skill-gap analysis.
            </div>
          </section>

          <section className="mb-10">
            <h2 className="text-xl font-semibold mb-4">Skill intelligence</h2>
            <div className="rounded-sm border border-border-soft bg-background p-8 text-muted text-sm leading-relaxed">
              Coming after skill-gap analysis.<br />
              A granular view of what you know versus what the market is asking
              for.
            </div>
          </section>

          <section className="mb-10">
            <h2 className="text-xl font-semibold mb-4">Learning roadmap</h2>
            <div className="rounded-sm border border-border-soft bg-background p-8 text-muted text-sm leading-relaxed">
              Coming after career targeting.<br />
              A personalized, ordered plan to close your skill gaps.
            </div>
          </section>

          <section>
            <h2 className="text-xl font-semibold mb-4">Interview readiness</h2>
            <div className="rounded-sm border border-border-soft bg-background p-8 text-muted text-sm leading-relaxed">
              Coming after interview assessment.<br />
              Adaptive preparation grounded in your experience.
            </div>
          </section>
        </>
      )}

      {!profile && (
        <div className="mt-10">
          <a
            href="/onboarding/start"
            className="inline-flex items-center gap-2 rounded-sm border border-border-soft bg-panel px-6 py-3 font-medium text-sm transition-colors hover:bg-panel-hover"
          >
            Build your profile
          </a>
        </div>
      )}
    </div>
  );
}
