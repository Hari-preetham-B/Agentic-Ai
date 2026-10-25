"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { itemVariants } from "@/components/Section";
import { PageHeader } from "@/components/PageHeader";
import { StatusBadge } from "@/components/StatusBadge";
import { Rule } from "@/components/Rule";

const sections = [
  {
    title: "CareerTwin",
    body:
      "An evolving structured representation of your professional state — education, skills, projects, experience, goals, and evidence — maintained over time.",
  },
  {
    title: "Career Intelligence",
    body:
      "Analysis of your current position against plausible career directions, with the gaps between them made explicit.",
  },
  {
    title: "Skill Intelligence",
    body:
      "A granular view of what you know, what you have evidenced, and what the market is actually asking for.",
  },
  {
    title: "Learning Roadmap",
    body:
      "A personalized, ordered plan that closes skill gaps using evidence-backed resources and measurable milestones.",
  },
  {
    title: "Interview Lab",
    body:
      "Adaptive preparation grounded in your actual experience and the roles you are targeting.",
  },
  {
    title: "Evidence Intelligence",
    body:
      "Claim-level confidence classification that separates supported information from inference, with traceable evidence references.",
  },
];

export default function Home() {
  return (
    <div className="flex flex-col flex-1 min-h-screen">
      <section className="relative flex-1 flex flex-col py-20 px-6 md:px-10 lg:px-12 overflow-hidden">
        {/* Subtle technical grid texture */}
        <div className="absolute inset-0 grid-bg pointer-events-none" />

        <div className="relative z-10 flex-1 flex flex-col">
          {/* Navbar / kicker */}
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-16">
            <div className="flex items-center gap-2">
              <span className="font-mono text-xs font-bold tracking-tighter text-muted">
                CAREERTWIN
              </span>
            </div>
            <div className="hidden md:flex items-center gap-6 text-mono-sm text-muted">
              <a href="/app/twin" className="hover:text-foreground transition-colors">
                Twin
              </a>
              <a href="/app/careers" className="hover:text-foreground transition-colors">
                Careers
              </a>
              <a href="/app/skills" className="hover:text-foreground transition-colors">
                Skills
              </a>
              <a href="/onboarding/start" className="hover:text-foreground transition-colors">
                Onboarding
              </a>
            </div>
          </div>

          {/* Hero */}
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            <div className="flex flex-col gap-6">
              <StatusBadge>FOUNDATION BUILD</StatusBadge>
              <h1 className="text-5xl md:text-6xl font-semibold tracking-tight leading-tight">
                YOUR CAREER.<br />
                <span className="text-accent">UNDERSTOOD.</span>
              </h1>
              <p className="text-muted text-lg leading-relaxed max-w-[42rem]">
                CareerTwin turns your experience, skills, goals, learning progress, and evidence into
                an evolving career intelligence system.
              </p>
              <div className="flex flex-col sm:flex-row gap-4">
                <Link
                  href="/onboarding/start"
                  className="flex h-11 w-full sm:w-auto items-center justify-center rounded-sm border border-border-soft bg-panel px-5 font-medium text-sm transition-colors hover:bg-panel-hover"
                >
                  Start onboarding
                </Link>
                <Link
                  href="/app/twin"
                  className="flex h-11 w-full sm:w-auto items-center justify-center rounded-sm border border-border-soft bg-transparent px-5 font-medium text-sm transition-colors hover:bg-panel-hover"
                >
                  Explore the twin
                </Link>
              </div>
            </div>

            <aside className="flex flex-col gap-6 border-l border-border-soft pl-8">
              {sections.map((s) => (
                <div key={s.title} className="flex flex-col gap-2">
                  <span className="font-mono text-xs font-medium text-muted uppercase tracking-wider">
                    {s.title}
                  </span>
                  <p className="text-sm text-muted-soft leading-relaxed">{s.body}</p>
                </div>
              ))}
            </aside>
          </div>
        </div>
      </section>

      {/* System sections — editorial, large visual sections */}
      <section className="border-t border-border-soft bg-panel py-24 px-6 md:px-10 lg:px-12">
        <div className="max-w-7xl mx-auto">
          <PageHeader
            label="How it works"
            title="From profile to intelligence"
            subtitle="CareerTwin is not a collection of disconnected AI requests. It is a continuously evolving model of your career."
          />

          <div className="mt-16 grid md:grid-cols-3 gap-8">
            {sections.map((s, i) => (
              <motion.div
                key={s.title}
                variants={itemVariants}
                initial="hidden"
                animate="visible"
                transition={{ delay: i * 0.08 }}
                className="flex flex-col gap-4 p-8 rounded-sm border border-border-soft bg-background"
              >
                <span className="font-mono text-xs font-bold tracking-tighter text-muted">
                  {i + 1}. {s.title.toUpperCase()}
                </span>
                <h3 className="text-lg font-semibold">{s.title}</h3>
                <p className="text-muted text-sm leading-relaxed">{s.body}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      <Rule />

      <section className="py-24 px-6 md:px-10 lg:px-12">
        <div className="max-w-4xl mx-auto text-center">
          <h2 className="text-3xl md:text-4xl font-semibold tracking-tight">Coming next</h2>
          <p className="mt-4 text-muted text-lg leading-relaxed">
            Resume onboarding, agentic career analysis, skill-gap mathematics, adaptive interview
            preparation, and evidence-aware verification. Connecting in later phases.
          </p>
          <div className="mt-10">
            <Link
              href="/onboarding/start"
              className="inline-flex items-center justify-center gap-2 rounded-sm border border-border-soft bg-panel px-6 py-3 font-medium text-sm transition-colors hover:bg-panel-hover"
            >
              Begin onboarding
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}
