"use client";

import { useState } from "react";
import Link from "next/link";
import {
  verifyClaim,
  searchEvidence,
  type ClaimVerifyResponse,
  type EvidenceSearchResult,
} from "@/lib/api/client";
import { PageHeader } from "@/components/PageHeader";
import { Rule } from "@/components/Rule";
import { StatusBadge } from "@/components/StatusBadge";

const STATUS_CONFIG: Record<string, { label: string; color: string }> = {
  SUPPORTED: { label: "SUPPORTED", color: "text-emerald-600 border-emerald-600/20 bg-emerald-600/10" },
  INFERRED: { label: "INFERRED", color: "text-amber-600 border-amber-600/20 bg-amber-600/10" },
  UNCERTAIN: { label: "UNCERTAIN", color: "text-muted border-muted/20 bg-muted/10" },
  CONTRADICTED: { label: "CONTRADICTED", color: "text-red-600 border-red-600/20 bg-red-600/10" },
};

export default function TrustPage() {
  const [claimText, setClaimText] = useState("");
  const [claimType, setClaimType] = useState("other");
  const [verifying, setVerifying] = useState(false);
  const [verifyError, setVerifyError] = useState<string | null>(null);
  const [result, setResult] = useState<ClaimVerifyResponse | null>(null);
  const [searchResults, setSearchResults] = useState<EvidenceSearchResult[]>([]);
  const [searchLoading, setSearchLoading] = useState(false);

  const [profileId] = useState<string | null>(() => {
    if (typeof window !== "undefined") {
      return localStorage.getItem("ct:profileId");
    }
    return null;
  });

  const handleVerify = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!claimText.trim()) return;
    if (!profileId) {
      setVerifyError("No confirmed profile found. Build one via onboarding first.");
      return;
    }
    setVerifying(true);
    setVerifyError(null);
    setResult(null);
    try {
      const response = await verifyClaim({
        claim_text: claimText,
        claim_type: claimType,
        profile_id: profileId,
        context: "trust-center-verification",
      });
      setResult(response);
      // Also search for supporting evidence.
      const evidence = await searchEvidence({
        query: claimText,
        top_k: 5,
      });
      setSearchResults(evidence);
    } catch (err: unknown) {
      setVerifyError((err as Error).message);
    } finally {
      setVerifying(false);
    }
  };

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!claimText.trim()) return;
    setSearchLoading(true);
    try {
      const evidence = await searchEvidence({
        query: claimText,
        top_k: 5,
      });
      setSearchResults(evidence);
    } catch (err: unknown) {
      setVerifyError((err as Error).message);
    } finally {
      setSearchLoading(false);
    }
  };

  if (!profileId) {
    return (
      <div className="flex flex-col min-h-[calc(100vh-4rem)] py-10 px-6 md:px-10 lg:px-12">
        <PageHeader
          title="Evidence Intelligence"
          subtitle="Build your profile first to verify claims against evidence."
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

  return (
    <div className="flex flex-col min-h-[calc(100vh-4rem)] py-10 px-6 md:px-10 lg:px-12">
      <PageHeader
        title="Evidence Intelligence"
        subtitle="Verify claims against traceable evidence. Confidence is calculated deterministically from source hierarchy and evidence agreement — never from an LLM's own confidence."
      />

      <form
        onSubmit={handleVerify}
        className="rounded-sm border border-border-soft bg-panel p-8 mb-10"
      >
        <div className="flex items-center gap-2 mb-2">
          <StatusBadge>VERIFY CLAIM</StatusBadge>
        </div>
        <h2 className="text-xl font-semibold mb-4">Enter a claim to verify</h2>
        <div className="grid md:grid-cols-2 gap-4 mb-4">
          <label className="flex flex-col gap-1">
            <span className="text-mono-xs font-medium text-muted">Claim text</span>
            <input
              type="text"
              value={claimText}
              onChange={(e) => setClaimText(e.target.value)}
              placeholder="e.g. Python is a core skill for Software Engineers"
              className="rounded-sm border border-border-soft bg-background px-4 py-2 font-mono text-sm focus:border-accent outline-none transition-colors"
            />
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-mono-xs font-medium text-muted">Claim type</span>
            <select
              value={claimType}
              onChange={(e) => setClaimType(e.target.value)}
              className="rounded-sm border border-border-soft bg-background px-4 py-2 font-mono text-sm focus:border-accent outline-none transition-colors"
            >
              <option value="other">Other</option>
              <option value="skill_requirement">Skill requirement</option>
              <option value="education">Education</option>
              <option value="tool">Tool</option>
              <option value="experience">Experience</option>
              <option value="certification">Certification</option>
            </select>
          </label>
        </div>
        <button
          type="submit"
          disabled={verifying || !claimText.trim()}
          className="inline-flex items-center gap-2 rounded-sm border border-border-soft bg-panel px-6 py-2 font-mono text-sm font-medium transition-colors hover:bg-panel-hover disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {verifying ? "Verifying…" : "Verify Claim"}
        </button>
        {verifyError && (
          <div className="mt-4 rounded-sm border border-red/30 bg-red/10 p-4 text-red text-sm">
            {verifyError}
          </div>
        )}
      </form>

      {result && (
        <>
          <Rule />
          <div className="mb-10">
            <div className="flex items-start justify-between mb-6">
              <div>
                <h2 className="text-2xl font-semibold">Verification Result</h2>
                <p className="text-muted text-sm mt-1">
                  Deterministic confidence classification
                </p>
              </div>
              <div className={`rounded-sm border px-4 py-2 font-mono text-sm font-semibold ${STATUS_CONFIG[result.status].color}`}>
                {STATUS_CONFIG[result.status].label}
              </div>
            </div>
            <div className="flex items-center gap-6 mb-6">
              <div className="rounded-sm border border-border-soft bg-panel p-6">
                <dt className="text-mono-xs font-medium text-muted mb-1">
                  Confidence score
                </dt>
                <dd className="text-3xl font-semibold font-mono">
                  {(result.confidence * 100).toFixed(0)}%
                </dd>
              </div>
              <div className="rounded-sm border border-border-soft bg-panel p-6">
                <dt className="text-mono-xs font-medium text-muted mb-1">
                  Evidence sources
                </dt>
                <dd className="text-3xl font-semibold font-mono">
                  {result.evidence.length}
                </dd>
              </div>
              <div className="rounded-sm border border-border-soft bg-panel p-6">
                <dt className="text-mono-xs font-medium text-muted mb-1">
                  Contradictions
                </dt>
                <dd className="text-3xl font-semibold font-mono">
                  {result.contradictions.length}
                </dd>
              </div>
            </div>

            <section className="mb-6">
              <h3 className="text-lg font-semibold mb-2">Claim</h3>
              <div className="rounded-sm border border-border-soft bg-background p-6">
                <p className="text-muted text-sm leading-relaxed">
                  &quot;{result.claim}&quot;
                </p>
                <p className="mt-2 text-mono-xs text-muted-soft">
                  Type: {result.claim_type} &bull; Importance:
                  {result.importance}
                </p>
              </div>
            </section>

            <section className="mb-6">
              <h3 className="text-lg font-semibold mb-2">Explanation</h3>
              <div className="rounded-sm border border-border-soft bg-panel p-6">
                <p className="text-muted text-sm leading-relaxed">
                  {result.explanation}
                </p>
              </div>
            </section>

            {result.factors && Object.keys(result.factors).length > 0 && (
              <section className="mb-6">
                <h3 className="text-lg font-semibold mb-2">Confidence factors</h3>
                <div className="rounded-sm border border-border-soft bg-panel p-6">
                  <dl className="grid sm:grid-cols-2 gap-4 text-muted text-sm">
                    <div>
                      <dt className="text-mono-xs font-medium text-muted mb-1">
                        Base score
                      </dt>
                      <dd className="font-mono">
                        {(
                          result.factors.base_score as number
                        ).toFixed(3)}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-mono-xs font-medium text-muted mb-1">
                        Agreement score
                      </dt>
                      <dd className="font-mono">
                        {(
                          result.factors.agreement_score as number
                        ).toFixed(3)}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-mono-xs font-medium text-muted mb-1">
                        Contradiction penalty
                      </dt>
                      <dd className="font-mono">
                        {(
                          result.factors.contradiction_penalty as number
                        ).toFixed(3)}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-mono-xs font-medium text-muted mb-1">
                        Source count
                      </dt>
                      <dd className="font-mono">
                        {result.factors.source_count as number}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-mono-xs font-medium text-muted mb-1">
                        Support count
                      </dt>
                      <dd className="font-mono">
                        {result.factors.support_count as number}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-mono-xs font-medium text-muted mb-1">
                        Contradiction count
                      </dt>
                      <dd className="font-mono">
                        {result.factors.contradiction_count as number}
                      </dd>
                    </div>
                  </dl>
                </div>
              </section>
            )}

            {result.evidence.length > 0 && (
              <section className="mb-6">
                <h3 className="text-lg font-semibold mb-2">Supporting evidence</h3>
                <div className="rounded-sm border border-border-soft bg-panel p-8">
                  <ul className="space-y-4">
                    {result.evidence.map((ev, i) => (
                      <li
                        key={i}
                        className="p-4 rounded-sm border border-border-soft bg-background"
                      >
                        <div className="flex justify-between mb-1">
                          <span className="font-mono text-sm font-semibold">
                            {ev.title}
                          </span>
                          <span className="text-mono-xs text-muted">
                            {ev.source_type}
                          </span>
                        </div>
                        <p className="text-muted-soft text-mono-xs">
                          {ev.publisher}
                        </p>
                        {ev.url && (
                          <a
                            href={ev.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="mt-1 inline-block text-mono-xs text-accent hover:underline"
                          >
                            View source &rarr;
                          </a>
                        )}
                        <p className="mt-2 text-muted-soft text-mono-xs">
                          {ev.content || ev.content.slice(0, 200)}…
                        </p>
                      </li>
                    ))}
                  </ul>
                </div>
              </section>
            )}

            {result.contradictions.length > 0 && (
              <section className="mb-6">
                <h3 className="text-lg font-semibold mb-2 text-red-600">
                  Contradictions
                </h3>
                <div className="rounded-sm border border-red/30 bg-red/10 p-8">
                  <ul className="space-y-4">
                    {result.contradictions.map((ev, i) => (
                      <li
                        key={i}
                        className="p-4 rounded-sm border border-border-soft bg-background"
                      >
                        <div className="flex justify-between mb-1">
                          <span className="font-mono text-sm font-semibold text-red-600">
                            {ev.title}
                          </span>
                          <span className="text-mono-xs text-muted">
                            {ev.source_type}
                          </span>
                        </div>
                        <p className="text-muted-soft text-mono-xs">
                          {ev.publisher}
                        </p>
                        <p className="mt-2 text-muted-soft text-mono-xs">
                          {ev.content || ev.content.slice(0, 200)}…
                        </p>
                      </li>
                    ))}
                  </ul>
                </div>
              </section>
            )}
          </div>
        </>
      )}

      <Rule />
      <div className="mb-10">
        <h2 className="text-xl font-semibold mb-4">Semantic evidence search</h2>
        <form onSubmit={handleSearch} className="flex flex-col sm:flex-row gap-4 mb-6">
          <input
            type="text"
            value={claimText}
            onChange={(e) => setClaimText(e.target.value)}
            placeholder="Search evidence by semantic similarity…"
            className="flex-1 rounded-sm border border-border-soft bg-panel px-4 py-2 font-mono text-sm focus:border-accent outline-none transition-colors"
          />
          <button
            type="submit"
            disabled={searchLoading || !claimText.trim()}
            className="rounded-sm border border-border-soft bg-panel px-6 py-2 font-mono text-sm font-medium transition-colors hover:bg-panel-hover disabled:opacity-50"
          >
            {searchLoading ? "Searching…" : "Search Evidence"}
          </button>
        </form>
        {searchResults.length > 0 && (
          <div className="rounded-sm border border-border-soft bg-panel p-8">
            <h3 className="text-lg font-semibold mb-4">Search results</h3>
            <ul className="space-y-4">
              {searchResults.map((ev, i) => (
                <li key={i} className="p-4 rounded-sm border border-border-soft bg-background">
                  <div className="flex justify-between mb-1">
                    <span className="font-mono text-sm font-semibold">
                      {ev.title}
                    </span>
                    <span className="text-mono-xs text-muted">
                      {(ev.similarity_score * 100).toFixed(0)}% match
                    </span>
                  </div>
                  <p className="text-muted-soft text-mono-xs">{ev.publisher}</p>
                  <p className="mt-2 text-muted-soft text-mono-xs">
                    {ev.content.slice(0, 200)}…
                  </p>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}
