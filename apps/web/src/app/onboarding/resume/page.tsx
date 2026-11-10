"use client";

import { useState, useCallback } from "react";
import { motion } from "framer-motion";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  extractResumeDraft,
  uploadResume,
  createProfile,
  addChild,
  type ProfileDraft,
  type ResumeExtractResponse,
  apiErrorMessage,
} from "@/lib/api/client";
import { notifyProfilesUpdated } from "@/lib/profile/context";
import { Section } from "@/components/Section";
import { StatusBadge } from "@/components/StatusBadge";
import { PageHeader } from "@/components/PageHeader";

type Step = "select" | "extracting" | "extracted" | "draft" | "created";

const ACCEPTED_TYPES =
  ".pdf,.docx,.txt,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain";

export default function OnboardingResumePage() {
  const router = useRouter();
  const [step, setStep] = useState<Step>("select");
  const [file, setFile] = useState<File | null>(null);
  const [extractResult, setExtractResult] = useState<ResumeExtractResponse | null>(null);
  const [draft, setDraft] = useState<ProfileDraft | null>(null);
  const [profileId, setProfileId] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [processing, setProcessing] = useState(false);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0] ?? null;
    setFile(f);
    setUploadError(null);
    if (f) setStep("select");
  };

  const handleUpload = useCallback(async () => {
    if (!file) return;
    setProcessing(true);
    setUploadError(null);
    try {
      const result = await uploadResume(file);
      setExtractResult(result);
      setStep("extracted");
    } catch (err) {
      setUploadError(apiErrorMessage(err) || "Upload failed.");
    } finally {
      setProcessing(false);
    }
  }, [file]);

  const handleCreateDraft = useCallback(async () => {
    if (!extractResult) return;
    setProcessing(true);
    try {
      const profileDraft = await extractResumeDraft(file!);
      setDraft(profileDraft);
      setStep("draft");
    } catch (err) {
      setUploadError(apiErrorMessage(err) || "Draft extraction failed.");
    } finally {
      setProcessing(false);
    }
  }, [extractResult, file]);

  const handleSaveDraft = useCallback(async () => {
    if (!draft) return;
    setProcessing(true);
    setUploadError(null);
    try {
      // Reuse the profile from a previous failed attempt instead of creating
      // a duplicate on retry.
      let id = profileId;
      if (!id) {
        const created = await createProfile(draft.profile);
        id = created.id;
        setProfileId(id);
        localStorage.setItem("ct:profileId", id);
      }
      const targetId = id;

      // Persist extracted children; collect failures rather than aborting.
      const jobs: Array<[string, Promise<unknown>]> = [
        ...draft.education.map((e): [string, Promise<unknown>] => ["education", addChild(targetId, "education", e)]),
        ...draft.skills.map((s): [string, Promise<unknown>] => ["skill", addChild(targetId, "skills", s)]),
        ...draft.projects.map((p): [string, Promise<unknown>] => ["project", addChild(targetId, "projects", p)]),
        ...draft.experience.map((x): [string, Promise<unknown>] => ["experience", addChild(targetId, "experience", x)]),
        ...draft.career_goals.map((g): [string, Promise<unknown>] => ["career goal", addChild(targetId, "career-goals", g)]),
      ];
      const results = await Promise.allSettled(jobs.map(([, job]) => job));
      const failed = results.filter((r) => r.status === "rejected").length;
      if (failed > 0) {
        setUploadError(
          `${failed} of ${jobs.length} extracted items could not be saved. ` +
            "Your profile was created; add the missing items on the next screen.",
        );
      }
      notifyProfilesUpdated();
      setStep("created");
    } catch (err) {
      setUploadError(apiErrorMessage(err) || "Failed to save draft profile.");
    } finally {
      setProcessing(false);
    }
  }, [draft, profileId]);

  return (
    <div className="flex flex-col min-h-[calc(100vh-4rem)] py-10 px-6 md:px-10 lg:px-12">
      <div className="flex items-center gap-2 mb-2">
        <StatusBadge>DOCUMENT EXTRACTION</StatusBadge>
      </div>
      <PageHeader
        title="Upload your resume"
        subtitle="We read your resume and present a structured draft for you to review and edit before confirming. Nothing is saved as confirmed until you approve it, and skill levels are left for you to set."
      />

      {step === "select" && (
        <Section className="rounded-sm border border-border-soft bg-panel p-10">
          <div className="flex flex-col items-center gap-4 mb-8">
            <label
              className="inline-flex items-center justify-center gap-3 rounded-sm border border-border-soft bg-background px-6 py-4 text-sm font-medium transition-colors hover:bg-panel-hover cursor-pointer"
            >
              Choose file
              <input
                type="file"
                accept={ACCEPTED_TYPES}
                className="sr-only"
                onChange={handleFileChange}
              />
            </label>
            {file && (
              <div className="text-mono-xs text-muted">
                {file.name} ({(file.size / 1024).toFixed(1)} KB)
              </div>
            )}
          </div>
          <p className="text-muted text-sm leading-relaxed max-w-[40rem]">
            Supported: PDF, DOCX, TXT. Maximum size 10 MB. OCR and image
            resumes are not supported yet.
          </p>
          <div className="mt-10 flex gap-4">
            <button
              onClick={handleUpload}
              disabled={!file || processing}
              className="inline-flex items-center justify-center gap-2 rounded-sm border border-border-soft bg-panel px-6 py-3 font-medium text-sm transition-colors hover:bg-panel-hover disabled:opacity-50 disabled:pointer-events-none"
            >
              {processing ? "Extracting…" : "Extract text"}
            </button>
            <Link
              href="/onboarding/start"
              className="inline-flex items-center gap-1.5 rounded-sm border border-border-soft bg-transparent px-5 py-3 font-medium text-sm text-muted transition-colors hover:bg-panel-hover"
            >
              <span aria-hidden="true">←</span> Back
            </Link>
          </div>
          {uploadError && (
            <div className="mt-6 rounded-sm border border-accent/30 bg-accent/10 px-4 py-3 text-mono-xs text-accent">
              {uploadError}
            </div>
          )}
        </Section>
      )}

      {step === "extracted" && (
        <Section className="rounded-sm border border-border-soft bg-panel p-10">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-semibold">Extracted text</h2>
            <span className="text-mono-xs text-muted">
              {extractResult?.character_count ?? 0} chars ·
              {extractResult?.word_count ?? 0} words
            </span>
          </div>
          <div className="rounded-sm border border-border-soft bg-background p-5 mb-6 max-h-96 overflow-y-auto font-mono text-xs text-muted-soft leading-relaxed">
            {extractResult?.extracted_text || "(no text extracted)"}
          </div>
          <p className="text-muted text-sm mb-8">
            Review the extracted text. When ready, we will structure it into a
            draft profile for your review.
          </p>
          <div className="flex gap-4">
            <button
              onClick={handleCreateDraft}
              disabled={processing}
              className="rounded-sm border border-border-soft bg-panel px-6 py-3 font-medium text-sm transition-colors hover:bg-panel-hover disabled:opacity-50 disabled:pointer-events-none"
            >
              {processing ? "Structuring…" : "Structure into draft"}
            </button>
            <Link
              href="/onboarding/resume"
              className="inline-flex items-center gap-1.5 rounded-sm border border-border-soft bg-transparent px-5 py-3 font-medium text-sm text-muted transition-colors hover:bg-panel-hover"
            >
              <span aria-hidden="true">←</span> Re-upload
            </Link>
          </div>
          {uploadError && (
            <div className="mt-6 rounded-sm border border-accent/30 bg-accent/10 px-4 py-3 text-mono-xs text-accent">
              {uploadError}
            </div>
          )}
        </Section>
      )}

      {step === "draft" && draft && (
        <Section className="rounded-sm border border-border-soft bg-panel p-10">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-semibold">Structured draft</h2>
            <span className="text-mono-xs text-muted">
              {draft.extraction_metadata.source_type}
            </span>
          </div>
          <div className="mb-6">
            <label className="block text-mono-xs font-medium text-muted mb-1 uppercase tracking-wider">
              Name
            </label>
            <p className="text-lg font-semibold">{draft.profile.full_name || "(not detected)"}</p>
          </div>
          <div className="grid md:grid-cols-2 gap-6 mb-8">
            <div>
              <h3 className="text-mono-xs font-medium text-muted uppercase tracking-wider mb-3">
                Skills ({draft.skills.length})
              </h3>
              <ul className="text-muted text-sm space-y-1">
                {draft.skills.map((s) => (
                  <li key={s.name}>{s.name}</li>
                ))}
                {draft.skills.length === 0 && <li className="text-muted-soft">none detected</li>}
              </ul>
            </div>
            <div>
              <h3 className="text-mono-xs font-medium text-muted uppercase tracking-wider mb-3">
                Education ({draft.education.length})
              </h3>
              <ul className="text-muted text-sm space-y-1">
                {draft.education.map((e) => (
                  <li key={e.institution}>{e.institution}</li>
                ))}
                {draft.education.length === 0 && (
                  <li className="text-muted-soft">none detected</li>
                )}
              </ul>
            </div>
          </div>
          {draft.extraction_metadata.extraction_warnings.length > 0 && (
            <div className="rounded-sm border border-accent/30 bg-accent/10 px-4 py-3 mb-6">
              <h4 className="text-mono-xs font-medium text-accent mb-2">Notes</h4>
              <ul className="text-mono-xs text-muted space-y-1">
                {draft.extraction_metadata.extraction_warnings.map((w, i) => (
                  <li key={i}>• {w}</li>
                ))}
              </ul>
            </div>
          )}
          <p className="text-muted text-sm mb-8">
            The draft has been structured from your resume. Save it as a draft
            profile, then review and confirm it.
          </p>
          <div className="flex gap-4">
            <button
              onClick={handleSaveDraft}
              disabled={processing}
              className="rounded-sm border border-border-soft bg-panel px-6 py-3 font-medium text-sm transition-colors hover:bg-panel-hover disabled:opacity-50 disabled:pointer-events-none"
            >
              {processing ? "Saving…" : "Save draft profile"}
            </button>
            <Link
              href="/onboarding/resume"
              className="inline-flex items-center gap-1.5 rounded-sm border border-border-soft bg-transparent px-5 py-3 font-medium text-sm text-muted transition-colors hover:bg-panel-hover"
            >
              <span aria-hidden="true">←</span> Re-upload
            </Link>
          </div>
          {uploadError && (
            <div className="mt-6 rounded-sm border border-accent/30 bg-accent/10 px-4 py-3 text-mono-xs text-accent">
              {uploadError}
            </div>
          )}
        </Section>
      )}

      {step === "created" && (
        <Section className="rounded-sm border border-border-soft bg-panel p-10 flex flex-col items-center text-center">
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            className="mb-6"
          >
            <span className="rounded-sm border border-accent/30 bg-accent/10 px-3 py-1 text-mono-xs text-accent">
              Draft saved
            </span>
          </motion.div>
          <h2 className="text-2xl font-semibold mb-3">Draft profile saved</h2>
          <p className="text-muted text-sm mb-8">
            Your resume-derived profile has been saved as a DRAFT. Review it,
            make any edits, then confirm your CareerTwin.
          </p>
          <button
            onClick={() =>
              router.push(`/onboarding/review?profileId=${profileId}`)
            }
            className="rounded-sm border border-border-soft bg-panel px-6 py-3 font-medium text-sm transition-colors hover:bg-panel-hover"
          >
            Go to review
          </button>
        </Section>
      )}
    </div>
  );
}
