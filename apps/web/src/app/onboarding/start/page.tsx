"use client";

import { useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { Section } from "@/components/Section";
import { StatusBadge } from "@/components/StatusBadge";

export default function OnboardingStartPage() {
  const [path, setPath] = useState<"manual" | "resume" | null>(null);

  return (
    <div className="flex flex-col min-h-[calc(100vh-4rem)] py-10 px-6 md:px-10 lg:px-12">
      <div className="flex items-center gap-2 mb-2">
        <StatusBadge>ONBOARDING</StatusBadge>
      </div>
      <h1 className="text-4xl md:text-5xl font-semibold tracking-tight mb-6">
        Build your CareerTwin
      </h1>
      <p className="text-muted text-lg leading-relaxed max-w-[42rem] mb-12">
        Create a structured profile of your education, skills, projects,
        experience, and career goals. You can build it manually or start from a
        resume.
      </p>

      <Section className="grid md:grid-cols-2 gap-8 items-start">
        <motion.div
          key="manual"
          whileHover={{ scale: 1.02 }}
          className="rounded-sm border border-border-soft bg-panel p-10 transition-all duration-300"
          style={{
            borderColor: path === "manual" ? "#dc2626" : undefined,
            backgroundColor: path === "manual" ? "rgba(220, 38, 38, 0.06)" : undefined,
          }}
        >
          <div className="flex items-center gap-3 mb-6">
            <span className="rounded-sm border border-border-soft bg-panel px-3 py-1 text-mono-xs font-medium text-muted">
              01
            </span>
            <h2 className="text-xl font-semibold">Build manually</h2>
          </div>
          <p className="text-muted text-sm leading-relaxed mb-8">
            Enter your education, skills, projects, experience, and career
            goals section by section.
          </p>
          <Link
            href="/onboarding/profile"
            className="inline-flex items-center justify-center gap-2 rounded-sm border border-border-soft bg-panel px-5 py-3 font-medium text-sm transition-colors hover:bg-panel-hover w-full"
            onClick={() => setPath("manual")}
          >
            Start building <span aria-hidden="true">→</span>
          </Link>
        </motion.div>

        <motion.div
          key="resume"
          whileHover={{ scale: 1.02 }}
          className="rounded-sm border border-border-soft bg-panel p-10 transition-all duration-300"
          style={{
            borderColor: path === "resume" ? "#dc2626" : undefined,
            backgroundColor: path === "resume" ? "rgba(220, 38, 38, 0.06)" : undefined,
          }}
        >
          <div className="flex items-center gap-3 mb-6">
            <span className="rounded-sm border border-border-soft bg-panel px-3 py-1 text-mono-xs font-medium text-muted">
              02
            </span>
            <h2 className="text-xl font-semibold">Upload resume</h2>
          </div>
          <p className="text-muted text-sm leading-relaxed mb-8">
            Upload a PDF, DOCX, or TXT resume. We extract the text and present
            a structured draft for you to review and edit before confirming.
          </p>
          <Link
            href="/onboarding/resume"
            className="inline-flex items-center justify-center gap-2 rounded-sm border border-border-soft bg-panel px-5 py-3 font-medium text-sm transition-colors hover:bg-panel-hover w-full"
            onClick={() => setPath("resume")}
          >
            Upload resume <span aria-hidden="true">→</span>
          </Link>
        </motion.div>
      </Section>

      <div className="mt-12 pt-8 border-t border-border-soft">
        <Link
          href="/"
          className="inline-flex items-center gap-1.5 font-mono text-xs text-muted hover:text-foreground transition-colors"
        >
          <span aria-hidden="true">←</span> Back to landing
        </Link>
      </div>
    </div>
  );
}
