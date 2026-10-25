"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  confirmProfile,
  getProfileDetail,
  type CareerGoal,
  type Education,
  type Experience,
  type ProfileDetail,
  type Project,
  type Skill,
  apiErrorMessage,
  apiErrorBody,
} from "@/lib/api/client";
import { StatusBadge } from "@/components/StatusBadge";
import { PageHeader } from "@/components/PageHeader";
import { Rule } from "@/components/Rule";

const SOURCE_LABELS: Record<string, { label: string; color: string }> = {
  USER_CONFIRMED: { label: "User", color: "text-accent" },
  DOCUMENT_EXTRACTED: { label: "Extracted", color: "text-muted" },
  SYSTEM_INFERRED: { label: "Inferred", color: "text-muted" },
};

function SourceBadge({ source }: { source: string }) {
  const info = SOURCE_LABELS[source] ?? SOURCE_LABELS.USER_CONFIRMED;
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-sm border border-border-soft bg-panel px-2 py-0.5 ${info.color} text-mono-xs`}
    >
      {info.label}
    </span>
  );
}

export default function OnboardingReviewPage() {
  const router = useRouter();
  const [profile, setProfile] = useState<ProfileDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [confirming, setConfirming] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const id = localStorage.getItem("ct:profileId");
        if (!id) {
          setError("No draft profile found. Start onboarding first.");
          setLoading(false);
          return;
        }
        const detail = await getProfileDetail(id);
        setProfile(detail);
      } catch (err) {
        setError(apiErrorMessage(err) || "Failed to load profile.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, []);

  const handleConfirm = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!profile) return;
    setConfirming(true);
    setError(null);
    try {
      const confirmed = await confirmProfile(profile.id);
      localStorage.removeItem("ct:profileId");
      router.push(`/app/twin?profileId=${confirmed.id}&confirmed=1`);
    } catch (err) {
      const body = apiErrorBody(err);
      const validationErrors =
        body && typeof body === "object" && "errors" in body
          ? (body as { errors: Array<{ message: string }> }).errors.map(
              (e) => e.message,
            )
          : [];
      setError(
        validationErrors.length
          ? "Cannot confirm: " + validationErrors.join(", ")
          : apiErrorMessage(err) || "Confirmation failed.",
      );
    } finally {
      setConfirming(false);
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col min-h-[calc(100vh-4rem)] py-10 px-6 md:px-10 lg:px-12">
        <PageHeader title="Reviewing your profile" subtitle="Loading…" />
        <p className="text-muted">Loading your profile…</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col min-h-[calc(100vh-4rem)] py-10 px-6 md:px-10 lg:px-12">
        <PageHeader title="Review" />
        <div className="rounded-sm border border-accent/30 bg-accent/10 px-4 py-3 text-mono-xs text-accent mb-6">
          {error}
        </div>
        <Link
          href="/onboarding/start"
          className="rounded-sm border border-border-soft bg-panel px-5 py-3 font-medium text-sm transition-colors hover:bg-panel-hover"
        >
          Back to start
        </Link>
      </div>
    );
  }

  if (!profile) {
    return (
      <div className="flex flex-col min-h-[calc(100vh-4rem)] py-10 px-6 md:px-10 lg:px-12">
        <PageHeader title="Review" />
        <p className="text-muted">No profile found. Start onboarding first.</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col min-h-[calc(100vh-4rem)] py-10 px-6 md:px-10 lg:px-12">
      <div className="flex items-center gap-2 mb-2">
        <StatusBadge>REVIEW BEFORE CONFIRMING</StatusBadge>
      </div>
      <PageHeader
        title="Review your CareerTwin"
        subtitle="Inspect your structured profile before confirming. Everything shown here will become your confirmed CareerTwin."
      />

      <form onSubmit={handleConfirm}>
        <section className="rounded-sm border border-border-soft bg-panel p-8 mb-10">
          <h2 className="text-xl font-semibold mb-4">Personal information</h2>
          <dl className="grid md:grid-cols-2 gap-4 text-muted text-sm">
            <div className="col-span-2">
              <dt className="text-mono-xs font-medium text-muted mb-1">Full name</dt>
              <dd className="font-semibold">{profile.full_name || "—"}</dd>
            </div>
            <div>
              <dt className="text-mono-xs font-medium text-muted mb-1">Headline</dt>
              <dd>{profile.headline || "—"}</dd>
            </div>
            <div>
              <dt className="text-mono-xs font-medium text-muted mb-1">Email</dt>
              <dd>{profile.email || "—"}</dd>
            </div>
            <div>
              <dt className="text-mono-xs font-medium text-muted mb-1">Location</dt>
              <dd>{profile.location || "—"}</dd>
            </div>
          </dl>
          {profile.summary && (
            <>
              <dt className="text-mono-xs font-medium text-muted mb-1 mt-6">Summary</dt>
              <dd className="text-sm leading-relaxed">{profile.summary}</dd>
            </>
          )}
          <p className="mt-6 text-mono-xs text-muted">
            Source: all fields entered or confirmed by you.
          </p>
        </section>

        {renderSection("Education", profile.education ?? [], "education")}
        {renderSection("Skills", profile.skills ?? [], "skills")}
        {renderSection("Projects", profile.projects ?? [], "projects")}
        {renderSection("Experience", profile.experience ?? [], "experience")}
        {renderSection("Career goals", profile.career_goals ?? [], "goals")}

        <Rule />

        <div className="pt-8 border-t border-border-soft">
          {error && (
            <div className="rounded-sm border border-accent/30 bg-accent/10 px-4 py-3 text-mono-xs text-accent mb-6">
              {error}
            </div>
          )}
          <button
            type="submit"
            disabled={confirming}
            className="inline-flex items-center justify-center gap-2 rounded-sm border border-border-soft bg-panel px-6 py-3 font-medium text-sm transition-colors hover:bg-panel-hover disabled:opacity-50 disabled:pointer-events-none"
          >
            {confirming ? "Confirming…" : "CONFIRM CAREERTWIN"}
          </button>
          <p className="mt-3 text-mono-xs text-muted-soft max-w-[48rem]">
            Confirming saves your profile as CONFIRMED and opens your CareerTwin
            overview. Your profile remains editable after confirmation.
          </p>
          <div className="mt-6 flex gap-3">
            <Link
              href="/onboarding/profile"
              className="inline-flex items-center gap-1.5 rounded-sm border border-border-soft bg-transparent px-5 py-3 font-medium text-sm text-muted transition-colors hover:bg-panel-hover"
            >
              <span aria-hidden="true">←</span> Edit profile
            </Link>
          </div>
        </div>
      </form>
    </div>
  );
}

function renderSection(
  title: string,
  items: (Education | Skill | Project | Experience | CareerGoal)[],
  kind: "education" | "skills" | "projects" | "experience" | "goals",
) {
  if (!items || items.length === 0) {
    return (
      <section key={title} className="my-10">
        <h2 className="text-xl font-semibold mb-3">{title}</h2>
        <p className="text-muted-soft text-mono-xs">None added yet.</p>
      </section>
    );
  }

  return (
    <section key={title} className="my-10">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold">{title}</h2>
        <span className="text-mono-xs text-muted">{items.length}</span>
      </div>
      <div className="space-y-3">
        {items.map((item, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="rounded-sm border border-border-soft bg-background p-5"
          >
            {kind === "education" && renderEducation(item as Education)}
            {kind === "skills" && renderSkill(item as Skill)}
            {kind === "projects" && renderProject(item as Project)}
            {kind === "experience" && renderExperience(item as Experience)}
            {kind === "goals" && renderGoal(item as CareerGoal)}
          </motion.div>
        ))}
      </div>
    </section>
  );
}

function renderEducation(e: Education) {
  return (
    <dl className="grid md:grid-cols-3 gap-4 text-sm">
      <div className="col-span-2">
        <dt className="text-mono-xs font-medium text-muted mb-1">Institution</dt>
        <dd className="font-semibold">{e.institution}</dd>
      </div>
      <div>
        <dt className="text-mono-xs font-medium text-muted mb-1">Degree</dt>
        <dd>{e.degree || "—"}</dd>
      </div>
      <div>
        <dt className="text-mono-xs font-medium text-muted mb-1">Field</dt>
        <dd>{e.field_of_study || "—"}</dd>
      </div>
      <div className="col-span-2">
        <dt className="text-mono-xs font-medium text-muted mb-1">Dates</dt>
        <dd className="font-mono text-mono-sm">
          {formatDate(e.start_date)} — {formatDate(e.end_date)}
        </dd>
      </div>
      {e.description && (
        <div className="col-span-3">
          <dt className="text-mono-xs font-medium text-muted mb-1">Description</dt>
          <dd className="text-sm leading-relaxed">{e.description}</dd>
        </div>
      )}
      <div className="col-span-3 flex items-end gap-2">
        <SourceBadge source={e.source} />
      </div>
    </dl>
  );
}

function renderSkill(s: Skill) {
  return (
    <dl className="grid md:grid-cols-4 gap-4 text-sm">
      <div className="col-span-2">
        <dt className="text-mono-xs font-medium text-muted mb-1">Skill</dt>
        <dd className="font-semibold">{s.name}</dd>
      </div>
      <div>
        <dt className="text-mono-xs font-medium text-muted mb-1">Category</dt>
        <dd>{s.category || "—"}</dd>
      </div>
      <div>
        <dt className="text-mono-xs font-medium text-muted mb-1">Proficiency</dt>
        <dd>{s.proficiency || "—"}</dd>
      </div>
      <div className="col-span-3 flex items-end gap-2">
        <SourceBadge source={s.source} />
      </div>
    </dl>
  );
}

function renderProject(p: Project) {
  return (
    <dl className="grid md:grid-cols-3 gap-4 text-sm">
      <div className="col-span-2">
        <dt className="text-mono-xs font-medium text-muted mb-1">Project</dt>
        <dd className="font-semibold">{p.name}</dd>
      </div>
      <div>
        <dt className="text-mono-xs font-medium text-muted mb-1">Role</dt>
        <dd>{p.role || "—"}</dd>
      </div>
      <div className="col-span-3">
        <dt className="text-mono-xs font-medium text-muted mb-1">Technologies</dt>
        <dd className="font-mono text-mono-sm">
          {(p.technologies ?? []).join(", ") || "—"}
        </dd>
      </div>
      <div className="col-span-3">
        <dt className="text-mono-xs font-medium text-muted mb-1">Outcomes</dt>
        <dd className="text-sm leading-relaxed">{p.outcomes || "—"}</dd>
      </div>
      <div className="col-span-3 flex items-end gap-2">
        <SourceBadge source={p.source} />
      </div>
    </dl>
  );
}

function renderExperience(e: Experience) {
  return (
    <dl className="grid md:grid-cols-3 gap-4 text-sm">
      <div className="col-span-2">
        <dt className="text-mono-xs font-medium text-muted mb-1">Organization</dt>
        <dd className="font-semibold">{e.organization}</dd>
      </div>
      <div>
        <dt className="text-mono-xs font-medium text-muted mb-1">Role</dt>
        <dd>{e.role}</dd>
      </div>
      <div className="col-span-3">
        <dt className="text-mono-xs font-medium text-muted mb-1">Dates</dt>
        <dd className="font-mono text-mono-sm">
          {formatDate(e.start_date)} —
          {e.is_current ? "Present" : formatDate(e.end_date)}
        </dd>
      </div>
      <div className="col-span-3">
        <dt className="text-mono-xs font-medium text-muted mb-1">Achievements</dt>
        <dd className="text-sm leading-relaxed">{e.achievements || "—"}</dd>
      </div>
      <div className="col-span-3 flex items-end gap-2">
        <SourceBadge source={e.source} />
      </div>
    </dl>
  );
}

function renderGoal(g: CareerGoal) {
  return (
    <dl className="grid md:grid-cols-3 gap-4 text-sm">
      <div className="col-span-2">
        <dt className="text-mono-xs font-medium text-muted mb-1">Target role</dt>
        <dd className="font-semibold">{g.target_role}</dd>
      </div>
      <div>
        <dt className="text-mono-xs font-medium text-muted mb-1">Industry</dt>
        <dd>{g.target_industry || "—"}</dd>
      </div>
      <div>
        <dt className="text-mono-xs font-medium text-muted mb-1">Domain</dt>
        <dd>{g.target_domain || "—"}</dd>
      </div>
      <div className="col-span-3">
        <dt className="text-mono-xs font-medium text-muted mb-1">Description</dt>
        <dd className="text-sm leading-relaxed">{g.goal_description || "—"}</dd>
      </div>
      <div className="col-span-3 flex items-end gap-2">
        <span className="text-mono-xs text-muted">Priority {g.priority}</span>
      </div>
    </dl>
  );
}

function formatDate(d?: string) {
  if (!d) return "—";
  return d;
}
