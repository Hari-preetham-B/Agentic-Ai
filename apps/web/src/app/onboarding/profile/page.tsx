"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import {
  confirmProfile,
  createProfile,
  getProfileDetail,
  updateProfile,
  type CareerGoalCreate,
  type EducationCreate,
  type ExperienceCreate,
  type ProfileCreate,
  type ProjectCreate,
  type Proficiency,
  type SkillCreate,
  apiErrorMessage,
  apiErrorBody,
} from "@/lib/api/client";
import { StatusBadge } from "@/components/StatusBadge";
import { PageHeader } from "@/components/PageHeader";
import { Rule } from "@/components/Rule";

type SectionKey =
  | "basic"
  | "education"
  | "skills"
  | "projects"
  | "experience"
  | "goals";

const SECTIONS: { key: SectionKey; label: string }[] = [
  { key: "basic", label: "Basic information" },
  { key: "education", label: "Education" },
  { key: "skills", label: "Skills" },
  { key: "projects", label: "Projects" },
  { key: "experience", label: "Experience" },
  { key: "goals", label: "Career goals" },
];

const EMPTY_EDU: EducationCreate = {
  institution: "",
  degree: "",
  field_of_study: "",
  start_date: "",
  end_date: "",
  description: "",
};

const EMPTY_SKILL: SkillCreate = {
  name: "",
  category: "",
  proficiency: undefined,
  years_experience: undefined,
  source: "USER_CONFIRMED",
};

const EMPTY_PROJECT: ProjectCreate = {
  name: "",
  description: "",
  technologies: [],
  role: "",
  outcomes: "",
  start_date: "",
  end_date: "",
  source: "USER_CONFIRMED",
};

const EMPTY_EXP: ExperienceCreate = {
  organization: "",
  role: "",
  description: "",
  achievements: "",
  start_date: "",
  end_date: "",
  is_current: false,
  source: "USER_CONFIRMED",
};

const EMPTY_GOAL: CareerGoalCreate = {
  target_role: "",
  target_industry: "",
  target_domain: "",
  goal_description: "",
  priority: 1,
};

function emptyDraft(): ProfileCreate {
  return {
    full_name: "",
    headline: "",
    email: "",
    phone: "",
    location: "",
    summary: "",
    profile_status: "DRAFT",
  };
}

export default function OnboardingProfilePage() {
  const router = useRouter();
  const [profileId, setProfileId] = useState<string | null>(null);
  const [draft, setDraft] = useState<ProfileCreate>(emptyDraft());
  const [education, setEducation] = useState<EducationCreate[]>([]);
  const [skills, setSkills] = useState<SkillCreate[]>([]);
  const [projects, setProjects] = useState<ProjectCreate[]>([]);
  const [experience, setExperience] = useState<ExperienceCreate[]>([]);
  const [goals, setGoals] = useState<CareerGoalCreate[]>([]);
  const [activeSection, setActiveSection] = useState<SectionKey>("basic");
  const [errors, setErrors] = useState<Record<string, string[]>>({});
  const [saving, setSaving] = useState(false);
  const [confirmError, setConfirmError] = useState<string | null>(null);

  const initialized = useRef(false);
  // Ensure a draft profile exists, then load it.
  useEffect(() => {
    let cancelled = false;
    async function init() {
      if (cancelled) return;
      let id = localStorage.getItem("ct:profileId");
      if (!id) {
        try {
          const created = await createProfile(emptyDraft());
          id = created.id;
          localStorage.setItem("ct:profileId", id);
          setProfileId(id);
        } catch (err) {
          setErrors({
            _global: [apiErrorMessage(err) || "Failed to create draft profile."],
          });
          return;
        }
      } else {
        setProfileId(id);
      }
      try {
        const detail = await getProfileDetail(id);
        setDraft({
          full_name: detail.full_name ?? "",
          headline: detail.headline ?? "",
          email: detail.email ?? "",
          phone: detail.phone ?? "",
          location: detail.location ?? "",
          summary: detail.summary ?? "",
          profile_status: detail.profile_status,
        });
        setEducation(
          detail.education.map((e) => ({
            institution: e.institution,
            degree: e.degree,
            field_of_study: e.field_of_study,
            start_date: e.start_date,
            end_date: e.end_date,
            description: e.description,
          })),
        );
        setSkills(
          detail.skills.map((s) => ({
            name: s.name,
            category: s.category,
            proficiency: s.proficiency,
            years_experience: s.years_experience,
            source: s.source,
          })),
        );
        setProjects(
          detail.projects.map((p) => ({
            name: p.name,
            description: p.description,
            technologies: p.technologies,
            role: p.role,
            outcomes: p.outcomes,
            start_date: p.start_date,
            end_date: p.end_date,
            source: p.source,
          })),
        );
        setExperience(
          detail.experience.map((x) => ({
            organization: x.organization,
            role: x.role,
            description: x.description,
            achievements: x.achievements,
            start_date: x.start_date,
            end_date: x.end_date,
            is_current: x.is_current,
            source: x.source,
          })),
        );
        setGoals(
          detail.career_goals.map((g) => ({
            target_role: g.target_role,
            target_industry: g.target_industry,
            target_domain: g.target_domain,
            goal_description: g.goal_description,
            priority: g.priority,
          })),
        );
      } catch (err) {
        setErrors({ _global: [apiErrorMessage(err) || "Failed to load profile."] });
      }
    }
    init();
    return () => {
      cancelled = true;
    };
  }, []);

  // Save the whole draft to the backend whenever it changes.
  const saveDraft = useCallback(async () => {
    if (!profileId) return;
    setSaving(true);
    try {
      await updateProfile(profileId, draft);
    } catch (err) {
      setErrors({ _global: [apiErrorMessage(err) || "Failed to save profile."] });
    } finally {
      setSaving(false);
    }
  }, [profileId, draft]);

  useEffect(() => {
    if (!initialized.current) {
      initialized.current = true;
      return;
    }
    saveDraft();
  }, [draft, saveDraft]);

  // ------------------------------------------------------------------
  // Section: basic information
  // ------------------------------------------------------------------
  const handleBasicChange = (key: keyof ProfileCreate) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    setDraft({ ...draft, [key]: e.target.value });
    setErrors((prev) => ({ ...prev, [key]: [] }));
  };

  // ------------------------------------------------------------------
  // Validation before moving on / confirming
  // ------------------------------------------------------------------
  const validateDraft = (): boolean => {
    const next: Record<string, string[]> = {};
    if (!draft.full_name?.trim()) next.full_name = ["Full name is required."];
    if (!draft.email?.includes("@")) next.email = ["Valid email is required."];
    if (skills.length === 0) next.skills = ["At least one skill is required."];
    if (goals.length === 0) next.career_goals = ["At least one career goal is required."];
    setErrors(next);
    return Object.keys(next).length === 0;
  };

  const handleConfirm = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validateDraft()) return;
    setConfirmError(null);
    if (!profileId) return;
    try {
      const confirmed = await confirmProfile(profileId);
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
      setConfirmError(
        validationErrors.length
          ? "Validation failed: " + validationErrors.join(", ")
          : apiErrorMessage(err) || "Confirmation failed.",
      );
    }
  };

  return (
    <div className="flex flex-col min-h-[calc(100vh-4rem)] py-10 px-6 md:px-10 lg:px-12">
      <div className="flex items-center gap-2 mb-2">
        <StatusBadge>DRAFT — EDITABLE</StatusBadge>
      </div>
      <PageHeader
        title="Build your profile"
        subtitle="Complete each section. Everything is editable until you confirm your CareerTwin."
      />

      <nav className="flex flex-col md:flex-row gap-3 mb-10 border-b border-border-soft pb-6">
        {SECTIONS.map((s) => {
          const active = activeSection === s.key;
          return (
            <button
              key={s.key}
              onClick={() => setActiveSection(s.key)}
              className={`flex items-center gap-2.5 px-4 py-3 rounded-sm text-sm font-medium transition-colors ${
                active
                  ? "bg-panel border border-accent text-accent"
                  : "border-transparent text-muted hover:text-foreground hover:bg-panel-hover"
              }`}
            >
              {s.label}
            </button>
          );
        })}
      </nav>

      <form onSubmit={handleConfirm} className="space-y-12">
        {/* Basic information */}
        <section
          id="basic"
          className="grid lg:grid-cols-2 gap-6"
          hidden={activeSection !== "basic"}
        >
          <div className="col-span-2">
            <label className="block text-mono-xs font-medium text-muted mb-1 uppercase tracking-wider">
              Full name
            </label>
            <input
              name="full_name"
              value={draft.full_name ?? ""}
              onChange={handleBasicChange("full_name")}
              className="block w-full rounded-sm border border-border-soft bg-background px-4 py-3 text-sm focus:border-accent focus:outline-none transition-colors"
            />
            {errors.full_name && (
              <p className="text-mono-xs text-accent mt-1">{errors.full_name[0]}</p>
            )}
          </div>
          <div className="lg:col-span-2">
            <label className="block text-mono-xs font-medium text-muted mb-1 uppercase tracking-wider">
              Headline
            </label>
            <input
              name="headline"
              value={draft.headline ?? ""}
              onChange={handleBasicChange("headline")}
              placeholder="e.g. Aspiring ML engineer"
              className="block w-full rounded-sm border border-border-soft bg-background px-4 py-3 text-sm focus:border-accent focus:outline-none transition-colors"
            />
          </div>
          <div>
            <label className="block text-mono-xs font-medium text-muted mb-1 uppercase tracking-wider">
              Email
            </label>
            <input
              name="email"
              type="email"
              value={draft.email ?? ""}
              onChange={handleBasicChange("email")}
              className="block w-full rounded-sm border border-border-soft bg-background px-4 py-3 text-sm focus:border-accent focus:outline-none transition-colors"
            />
            {errors.email && <p className="text-mono-xs text-accent mt-1">{errors.email[0]}</p>}
          </div>
          <div>
            <label className="block text-mono-xs font-medium text-muted mb-1 uppercase tracking-wider">
              Location
            </label>
            <input
              name="location"
              value={draft.location ?? ""}
              onChange={handleBasicChange("location")}
              placeholder="e.g. Berlin, Germany"
              className="block w-full rounded-sm border border-border-soft bg-background px-4 py-3 text-sm focus:border-accent focus:outline-none transition-colors"
            />
          </div>
          <div className="lg:col-span-2">
            <label className="block text-mono-xs font-medium text-muted mb-1 uppercase tracking-wider">
              Summary
            </label>
            <textarea
              name="summary"
              value={draft.summary ?? ""}
              onChange={handleBasicChange("summary")}
              rows={4}
              placeholder="A short summary of who you are and where you want to go."
              className="block w-full rounded-sm border border-border-soft bg-background px-4 py-3 text-sm focus:border-accent focus:outline-none transition-colors"
            />
          </div>
        </section>

        <Rule />

        {/* Education */}
        <section id="education" hidden={activeSection !== "education"}>
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-semibold">Education</h2>
            <button
              onClick={() =>
                setEducation([...education, { ...EMPTY_EDU }])
              }
              className="inline-flex items-center gap-2 rounded-sm border border-border-soft bg-panel px-3 py-2 text-mono-xs text-sm hover:bg-panel-hover transition-colors"
            >
              + Add education
            </button>
          </div>
          {education.map((edu, i) => (
            <motion.div
              key={i}
              className="rounded-sm border border-border-soft bg-background p-5 mb-4"
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
            >
              <div className="grid md:grid-cols-3 gap-4 mb-3">
                <input
                  value={edu.institution}
                  onChange={(e) => {
                    const next = [...education];
                    next[i].institution = e.target.value;
                    setEducation(next);
                  }}
                  placeholder="Institution"
                  className="rounded-sm border border-border-soft bg-panel px-3 py-2.5 text-sm focus:border-accent focus:outline-none"
                />
                <input
                  value={edu.degree}
                  onChange={(e) => {
                    const next = [...education];
                    next[i].degree = e.target.value;
                    setEducation(next);
                  }}
                  placeholder="Degree"
                  className="rounded-sm border border-border-soft bg-panel px-3 py-2.5 text-sm focus:border-accent focus:outline-none"
                />
                <input
                  value={edu.field_of_study}
                  onChange={(e) => {
                    const next = [...education];
                    next[i].field_of_study = e.target.value;
                    setEducation(next);
                  }}
                  placeholder="Field of study"
                  className="rounded-sm border border-border-soft bg-panel px-3 py-2.5 text-sm focus:border-accent focus:outline-none"
                />
              </div>
              <div className="grid md:grid-cols-2 gap-4 mb-3">
                <input
                  type="date"
                  value={edu.start_date}
                  onChange={(e) => {
                    const next = [...education];
                    next[i].start_date = e.target.value;
                    setEducation(next);
                  }}
                  className="rounded-sm border border-border-soft bg-panel px-3 py-2.5 text-sm focus:border-accent focus:outline-none"
                />
                <input
                  type="date"
                  value={edu.end_date}
                  onChange={(e) => {
                    const next = [...education];
                    next[i].end_date = e.target.value;
                    setEducation(next);
                  }}
                  className="rounded-sm border border-border-soft bg-panel px-3 py-2.5 text-sm focus:border-accent focus:outline-none"
                />
              </div>
              <textarea
                value={edu.description}
                onChange={(e) => {
                  const next = [...education];
                  next[i].description = e.target.value;
                  setEducation(next);
                }}
                rows={2}
                placeholder="Description"
                className="w-full rounded-sm border border-border-soft bg-panel px-3 py-2.5 text-sm focus:border-accent focus:outline-none"
              />
              <button
                type="button"
                onClick={() => setEducation(education.filter((_, idx) => idx !== i))}
                className="mt-2 inline-flex items-center gap-1 text-mono-xs text-accent hover:underline"
              >
                Remove
              </button>
            </motion.div>
          ))}
          {education.length === 0 && (
            <p className="text-muted-soft text-mono-xs">No education added yet.</p>
          )}
        </section>

        <Rule />

        {/* Skills */}
        <section id="skills" hidden={activeSection !== "skills"}>
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-semibold">Skills</h2>
            <button
              onClick={() => setSkills([...skills, { ...EMPTY_SKILL }])}
              className="inline-flex items-center gap-2 rounded-sm border border-border-soft bg-panel px-3 py-2 text-mono-xs text-sm hover:bg-panel-hover transition-colors"
            >
              + Add skill
            </button>
          </div>
          {skills.map((skill, i) => (
            <motion.div
              key={i}
              className="rounded-sm border border-border-soft bg-background p-5 mb-4"
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
            >
              <div className="grid md:grid-cols-4 gap-4 mb-3">
                <input
                  value={skill.name}
                  onChange={(e) => {
                    const next = [...skills];
                    next[i].name = e.target.value;
                    setSkills(next);
                  }}
                  placeholder="Skill name"
                  className="rounded-sm border border-border-soft bg-panel px-3 py-2.5 text-sm focus:border-accent focus:outline-none"
                />
                <input
                  value={skill.category ?? ""}
                  onChange={(e) => {
                    const next = [...skills];
                    next[i].category = e.target.value;
                    setSkills(next);
                  }}
                  placeholder="Category"
                  className="rounded-sm border border-border-soft bg-panel px-3 py-2.5 text-sm focus:border-accent focus:outline-none"
                />
                <select
                  value={skill.proficiency ?? undefined}
                  onChange={(e) => {
                    const next = [...skills];
                    next[i].proficiency = (e.target.value as Proficiency) || undefined;
                    setSkills(next);
                  }}
                  className="rounded-sm border border-border-soft bg-panel px-3 py-2.5 text-sm focus:border-accent focus:outline-none"
                >
                  <option value="">Proficiency</option>
                  <option>BEGINNER</option>
                  <option>INTERMEDIATE</option>
                  <option>ADVANCED</option>
                  <option>EXPERT</option>
                </select>
                <input
                  type="number"
                  step="0.5"
                  min="0"
                  value={skill.years_experience ?? ""}
                  onChange={(e) => {
                    const next = [...skills];
                    next[i].years_experience = e.target.value ? Number(e.target.value) : undefined;
                    setSkills(next);
                  }}
                  placeholder="Years"
                  className="rounded-sm border border-border-soft bg-panel px-3 py-2.5 text-sm focus:border-accent focus:outline-none"
                />
              </div>
              <button
                type="button"
                onClick={() => setSkills(skills.filter((_, idx) => idx !== i))}
                className="mt-2 inline-flex items-center gap-1 text-mono-xs text-accent hover:underline"
              >
                Remove
              </button>
            </motion.div>
          ))}
          {skills.length === 0 && (
            <p className="text-muted-soft text-mono-xs">No skills added yet.</p>
          )}
        </section>

        <Rule />

        {/* Projects */}
        <section id="projects" hidden={activeSection !== "projects"}>
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-semibold">Projects</h2>
            <button
              onClick={() => setProjects([...projects, { ...EMPTY_PROJECT }])}
              className="inline-flex items-center gap-2 rounded-sm border border-border-soft bg-panel px-3 py-2 text-mono-xs text-sm hover:bg-panel-hover transition-colors"
            >
              + Add project
            </button>
          </div>
          {projects.map((proj, i) => (
            <motion.div
              key={i}
              className="rounded-sm border border-border-soft bg-background p-5 mb-4"
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
            >
              <div className="grid md:grid-cols-2 gap-4 mb-3">
                <input
                  value={proj.name}
                  onChange={(e) => {
                    const next = [...projects];
                    next[i].name = e.target.value;
                    setProjects(next);
                  }}
                  placeholder="Project name"
                  className="rounded-sm border border-border-soft bg-panel px-3 py-2.5 text-sm focus:border-accent focus:outline-none"
                />
                <input
                  value={proj.role ?? ""}
                  onChange={(e) => {
                    const next = [...projects];
                    next[i].role = e.target.value;
                    setProjects(next);
                  }}
                  placeholder="Your role"
                  className="rounded-sm border border-border-soft bg-panel px-3 py-2.5 text-sm focus:border-accent focus:outline-none"
                />
              </div>
              <div className="grid md:grid-cols-2 gap-4 mb-3">
                <input
                  value={proj.technologies?.join(", ") ?? ""}
                  onChange={(e) => {
                    const next = [...projects];
                    next[i].technologies = e.target.value
                      .split(",")
                      .map((t) => t.trim())
                      .filter(Boolean);
                    setProjects(next);
                  }}
                  placeholder="Technologies (comma separated)"
                  className="rounded-sm border border-border-soft bg-panel px-3 py-2.5 text-sm focus:border-accent focus:outline-none"
                />
                <input
                  type="date"
                  value={proj.start_date}
                  onChange={(e) => {
                    const next = [...projects];
                    next[i].start_date = e.target.value;
                    setProjects(next);
                  }}
                  className="rounded-sm border border-border-soft bg-panel px-3 py-2.5 text-sm focus:border-accent focus:outline-none"
                />
                <input
                  type="date"
                  value={proj.end_date}
                  onChange={(e) => {
                    const next = [...projects];
                    next[i].end_date = e.target.value;
                    setProjects(next);
                  }}
                  className="rounded-sm border border-border-soft bg-panel px-3 py-2.5 text-sm focus:border-accent focus:outline-none"
                />
              </div>
              <textarea
                value={proj.description ?? ""}
                onChange={(e) => {
                  const next = [...projects];
                  next[i].description = e.target.value;
                  setProjects(next);
                }}
                rows={2}
                placeholder="Description"
                className="w-full rounded-sm border border-border-soft bg-panel px-3 py-2.5 text-sm focus:border-accent focus:outline-none mb-2"
              />
              <textarea
                value={proj.outcomes ?? ""}
                onChange={(e) => {
                  const next = [...projects];
                  next[i].outcomes = e.target.value;
                  setProjects(next);
                }}
                rows={2}
                placeholder="Outcomes / impact"
                className="w-full rounded-sm border border-border-soft bg-panel px-3 py-2.5 text-sm focus:border-accent focus:outline-none"
              />
              <button
                type="button"
                onClick={() => setProjects(projects.filter((_, idx) => idx !== i))}
                className="mt-2 inline-flex items-center gap-1 text-mono-xs text-accent hover:underline"
              >
                Remove
              </button>
            </motion.div>
          ))}
          {projects.length === 0 && (
            <p className="text-muted-soft text-mono-xs">No projects added yet.</p>
          )}
        </section>

        <Rule />

        {/* Experience */}
        <section id="experience" hidden={activeSection !== "experience"}>
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-semibold">Experience</h2>
            <button
              onClick={() => setExperience([...experience, { ...EMPTY_EXP }])}
              className="inline-flex items-center gap-2 rounded-sm border border-border-soft bg-panel px-3 py-2 text-mono-xs text-sm hover:bg-panel-hover transition-colors"
            >
              + Add experience
            </button>
          </div>
          {experience.map((exp, i) => (
            <motion.div
              key={i}
              className="rounded-sm border border-border-soft bg-background p-5 mb-4"
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
            >
              <div className="grid md:grid-cols-2 gap-4 mb-3">
                <input
                  value={exp.organization}
                  onChange={(e) => {
                    const next = [...experience];
                    next[i].organization = e.target.value;
                    setExperience(next);
                  }}
                  placeholder="Organization"
                  className="rounded-sm border border-border-soft bg-panel px-3 py-2.5 text-sm focus:border-accent focus:outline-none"
                />
                <input
                  value={exp.role}
                  onChange={(e) => {
                    const next = [...experience];
                    next[i].role = e.target.value;
                    setExperience(next);
                  }}
                  placeholder="Your role"
                  className="rounded-sm border border-border-soft bg-panel px-3 py-2.5 text-sm focus:border-accent focus:outline-none"
                />
              </div>
              <div className="grid md:grid-cols-2 gap-4 mb-3">
                <input
                  type="date"
                  value={exp.start_date}
                  onChange={(e) => {
                    const next = [...experience];
                    next[i].start_date = e.target.value;
                    setExperience(next);
                  }}
                  className="rounded-sm border border-border-soft bg-panel px-3 py-2.5 text-sm focus:border-accent focus:outline-none"
                />
                <input
                  type="date"
                  value={exp.end_date}
                  onChange={(e) => {
                    const next = [...experience];
                    next[i].end_date = e.target.value;
                    setExperience(next);
                  }}
                  className="rounded-sm border border-border-soft bg-panel px-3 py-2.5 text-sm focus:border-accent focus:outline-none"
                />
                <label className="flex items-center gap-2 mt-2 lg:mt-0">
                  <input
                    type="checkbox"
                    checked={exp.is_current}
                    onChange={(e) => {
                      const next = [...experience];
                      next[i].is_current = e.target.checked;
                      setExperience(next);
                    }}
                    className="rounded border-border-soft bg-background text-accent focus:ring-accent"
                  />
                  <span className="text-mono-xs text-muted">I currently work here</span>
                </label>
              </div>
              <textarea
                value={exp.description ?? ""}
                onChange={(e) => {
                  const next = [...experience];
                  next[i].description = e.target.value;
                  setExperience(next);
                }}
                rows={2}
                placeholder="Description"
                className="w-full rounded-sm border border-border-soft bg-panel px-3 py-2.5 text-sm focus:border-accent focus:outline-none mb-2"
              />
              <textarea
                value={exp.achievements ?? ""}
                onChange={(e) => {
                  const next = [...experience];
                  next[i].achievements = e.target.value;
                  setExperience(next);
                }}
                rows={2}
                placeholder="Key achievements"
                className="w-full rounded-sm border border-border-soft bg-panel px-3 py-2.5 text-sm focus:border-accent focus:outline-none"
              />
              <button
                type="button"
                onClick={() => setExperience(experience.filter((_, idx) => idx !== i))}
                className="mt-2 inline-flex items-center gap-1 text-mono-xs text-accent hover:underline"
              >
                Remove
              </button>
            </motion.div>
          ))}
          {experience.length === 0 && (
            <p className="text-muted-soft text-mono-xs">No experience added yet.</p>
          )}
        </section>

        <Rule />

        {/* Career goals */}
        <section id="goals" hidden={activeSection !== "goals"}>
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-semibold">Career goals</h2>
            <button
              onClick={() => setGoals([...goals, { ...EMPTY_GOAL }])}
              className="inline-flex items-center gap-2 rounded-sm border border-border-soft bg-panel px-3 py-2 text-mono-xs text-sm hover:bg-panel-hover transition-colors"
            >
              + Add goal
            </button>
          </div>
          {goals.map((goal, i) => (
            <motion.div
              key={i}
              className="rounded-sm border border-border-soft bg-background p-5 mb-4"
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
            >
              <div className="grid md:grid-cols-2 gap-4 mb-3">
                <input
                  value={goal.target_role}
                  onChange={(e) => {
                    const next = [...goals];
                    next[i].target_role = e.target.value;
                    setGoals(next);
                  }}
                  placeholder="Target role"
                  className="rounded-sm border border-border-soft bg-panel px-3 py-2.5 text-sm focus:border-accent focus:outline-none"
                />
                <input
                  value={goal.target_industry ?? ""}
                  onChange={(e) => {
                    const next = [...goals];
                    next[i].target_industry = e.target.value;
                    setGoals(next);
                  }}
                  placeholder="Industry"
                  className="rounded-sm border border-border-soft bg-panel px-3 py-2.5 text-sm focus:border-accent focus:outline-none"
                />
              </div>
              <div className="grid md:grid-cols-2 gap-4 mb-3">
                <input
                  value={goal.target_domain ?? ""}
                  onChange={(e) => {
                    const next = [...goals];
                    next[i].target_domain = e.target.value;
                    setGoals(next);
                  }}
                  placeholder="Domain"
                  className="rounded-sm border border-border-soft bg-panel px-3 py-2.5 text-sm focus:border-accent focus:outline-none"
                />
                <input
                  type="number"
                  min="1"
                  value={goal.priority ?? ""}
                  onChange={(e) => {
                    const next = [...goals];
                    next[i].priority = e.target.value ? Number(e.target.value) : 1;
                    setGoals(next);
                  }}
                  placeholder="Priority"
                  className="rounded-sm border border-border-soft bg-panel px-3 py-2.5 text-sm focus:border-accent focus:outline-none"
                />
              </div>
              <textarea
                value={goal.goal_description ?? ""}
                onChange={(e) => {
                  const next = [...goals];
                  next[i].goal_description = e.target.value;
                  setGoals(next);
                }}
                rows={3}
                placeholder="Describe your goal"
                className="w-full rounded-sm border border-border-soft bg-panel px-3 py-2.5 text-sm focus:border-accent focus:outline-none"
              />
              <button
                type="button"
                onClick={() => setGoals(goals.filter((_, idx) => idx !== i))}
                className="mt-2 inline-flex items-center gap-1 text-mono-xs text-accent hover:underline"
              >
                Remove
              </button>
            </motion.div>
          ))}
          {goals.length === 0 && (
            <p className="text-muted-soft text-mono-xs">No career goals added yet.</p>
          )}
        </section>

        <div className="pt-8 border-t border-border-soft">
          {confirmError && (
            <div className="rounded-sm border border-accent/30 bg-accent/10 px-4 py-3 text-mono-xs text-accent mb-6">
              {confirmError}
            </div>
          )}
          <button
            type="submit"
            disabled={saving}
            className="inline-flex items-center justify-center gap-2 rounded-sm border border-border-soft bg-panel px-6 py-3 font-medium text-sm transition-colors hover:bg-panel-hover disabled:opacity-50 disabled:pointer-events-none"
          >
            {saving ? "Confirming…" : "CONFIRM CAREERTWIN"}
          </button>
          <p className="mt-3 text-mono-xs text-muted-soft max-w-[48rem]">
            Confirming saves your profile as CONFIRMED and opens your CareerTwin
            overview. You can still edit it later.
          </p>
        </div>
      </form>
    </div>
  );
}
