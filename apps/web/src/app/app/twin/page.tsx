"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useActiveProfile } from "@/lib/profile/context";
import {
  apiErrorMessage,
  getAgentRunEvents,
  getCareerTwinState,
  listAgentRuns,
  refreshCareerTwin,
  runAgentCapability,
  type AgentEvent,
  type AgentRunSummary,
  type CareerTwinState,
} from "@/lib/api/client";
import {
  ButtonLink,
  ConfidenceBadge,
  EmptyState,
  ErrorNote,
  Meter,
  Panel,
  PageIntro,
  PriorityBadge,
  SectionTitle,
  Stat,
} from "@/components/ui";

const READINESS_LABELS: Record<string, string> = {
  NOT_READY: "Not ready",
  EARLY: "Early",
  DEVELOPING: "Developing",
  COMPETITIVE: "Competitive",
  STRONG: "Strong",
};

function formatDate(value?: string | null): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString(undefined, {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

export default function TwinPage() {
  const { profileId, profile } = useActiveProfile();
  const [state, setState] = useState<CareerTwinState | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<"refresh" | "agent" | null>(null);
  const [runs, setRuns] = useState<AgentRunSummary[]>([]);
  const [selectedRun, setSelectedRun] = useState<string | null>(null);
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [traceLoading, setTraceLoading] = useState(false);

  const loadState = useCallback(async () => {
    if (!profileId) {
      setLoading(false);
      return;
    }
    try {
      const data = await getCareerTwinState(profileId);
      setState(data);
      setError(null);
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, [profileId]);

  const loadRuns = useCallback(async () => {
    if (!profileId) return;
    try {
      const data = await listAgentRuns(profileId, 8);
      setRuns(data);
      if (data.length > 0) {
        setSelectedRun((current) => current ?? data[0].id);
      }
    } catch {
      // Trace history is supplementary; the dashboard still renders without it.
    }
  }, [profileId]);

  useEffect(() => {
    // Fetch on mount and whenever the active profile changes.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setLoading(true);
    void loadState();
    void loadRuns();
  }, [loadState, loadRuns]);

  useEffect(() => {
    if (!selectedRun) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setEvents([]);
      return;
    }
    let cancelled = false;
     
    setTraceLoading(true);
    getAgentRunEvents(selectedRun)
      .then((data) => {
        if (!cancelled) setEvents(data);
      })
      .catch(() => {
        if (!cancelled) setEvents([]);
      })
      .finally(() => {
        if (!cancelled) setTraceLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [selectedRun]);

  async function handleRefresh() {
    if (!profileId) return;
    setBusy("refresh");
    try {
      await refreshCareerTwin(profileId);
      await loadState();
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setBusy(null);
    }
  }

  async function handleAgentAnalysis() {
    if (!profileId || !state) return;
    setBusy("agent");
    try {
      const target =
        state.active_target_career ||
        state.career_fit?.career_title ||
        state.target_careers[0] ||
        "";
      const run = await runAgentCapability({
        profile_id: profileId,
        capability: "careertwin_analysis",
        input: target,
      });
      await Promise.all([loadState(), loadRuns()]);
      if (run.run_id) setSelectedRun(run.run_id);
      if (run.status === "FAILED" && run.error) setError(run.error);
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setBusy(null);
    }
  }

  if (loading) {
    return (
      <div>
        <PageIntro label="01 / Twin" title="Reading your CareerTwin" />
        <div className="grid gap-4 md:grid-cols-3">
          {[0, 1, 2].map((i) => (
            <div
              key={i}
              className="h-32 animate-pulse border border-border-soft bg-panel/40"
            />
          ))}
        </div>
      </div>
    );
  }

  if (error && !state) {
    return (
      <div>
        <PageIntro label="01 / Twin" title="Your CareerTwin" />
        <ErrorNote>{error}</ErrorNote>
        <button
          onClick={() => void loadState()}
          className="mt-4 border border-border-soft bg-panel px-4 py-2 text-xs"
        >
          Retry
        </button>
      </div>
    );
  }

  if (!state) return null;

  const priorityGaps = [...state.skill_gaps]
    .filter((gap) => gap.status !== "MATCHED")
    .sort((a, b) => {
      const order: Record<string, number> = { P0: 0, P1: 1, P2: 2 };
      return (order[a.priority ?? "P2"] ?? 2) - (order[b.priority ?? "P2"] ?? 2);
    })
    .slice(0, 6);
  const completeness = state.profile_completeness;
  const fit = state.career_fit;
  const roadmap = state.roadmap_summary;
  const interview = state.interview_summary;
  const evidence = state.evidence_summary;
  const stale = state.stale_components.filter((c) => c.is_stale);

  return (
    <div>
      <PageIntro
        label="01 / Twin"
        title={state.profile_name || profile?.full_name || "Your CareerTwin"}
        description={
          state.headline ||
          "A structured, explainable view of your career readiness, gaps, learning and evidence."
        }
        actions={
          <>
            <button
              onClick={() => void handleRefresh()}
              disabled={busy !== null}
              className="border border-border-soft bg-panel px-4 py-2.5 text-xs font-medium transition-colors hover:bg-panel-hover disabled:opacity-50"
            >
              {busy === "refresh" ? "Refreshing…" : "Refresh state"}
            </button>
            <button
              onClick={() => void handleAgentAnalysis()}
              disabled={busy !== null}
              className="border border-accent bg-accent px-4 py-2.5 text-xs font-medium text-white transition-colors hover:bg-accent-hover disabled:opacity-50"
            >
              {busy === "agent" ? "Running agent…" : "Run agent analysis"}
            </button>
          </>
        }
      />

      {error && (
        <div className="mb-6">
          <ErrorNote>{error}</ErrorNote>
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Stat
          label="Career readiness"
          value={`${(state.readiness_score * 100).toFixed(0)}%`}
          detail={READINESS_LABELS[state.readiness_level] ?? state.readiness_level}
          accent
        />
        <Stat
          label="Career fit"
          value={fit ? `${(fit.fit_score * 100).toFixed(0)}%` : "—"}
          detail={fit?.career_title || "Choose a target career"}
        />
        <Stat
          label="Confirmed skills"
          value={state.confirmed_skills.length}
          detail={`${state.documented_skills.length} documented from resumes`}
        />
        <Stat
          label="Critical gaps"
          value={state.skill_gaps.filter((g) => g.priority === "P0").length}
          detail="P0 gaps against the active career"
        />
      </div>

      <div className="mt-8 grid gap-8 xl:grid-cols-[1.55fr_1fr]">
        <div className="space-y-8">
          <Panel className="p-6 md:p-7">
            <SectionTitle
              index="POSITION"
              title={fit?.career_title || "Career position"}
              meta={fit ? `${(fit.fit_score * 100).toFixed(1)}% deterministic fit` : "No target career"}
            />
            {fit ? (
              <>
                <p className="max-w-3xl text-sm leading-relaxed text-muted">
                  {fit.rationale}
                </p>
                <div className="mt-5">
                  <Meter value={fit.fit_score} label="Fit score" />
                </div>
                <div className="mt-6 grid gap-5 md:grid-cols-2">
                  <div>
                    <p className="font-mono text-[9px] uppercase tracking-[0.18em] text-muted">
                      Strongest areas
                    </p>
                    <ul className="mt-2 space-y-1.5 text-sm text-foreground/90">
                      {fit.strongest_areas.length ? (
                        fit.strongest_areas.map((item) => (
                          <li key={item} className="flex gap-2">
                            <span className="text-zinc-500">+</span>
                            {item}
                          </li>
                        ))
                      ) : (
                        <li className="text-muted">No matched core skills yet.</li>
                      )}
                    </ul>
                  </div>
                  <div>
                    <p className="font-mono text-[9px] uppercase tracking-[0.18em] text-muted">
                      Blocking gaps
                    </p>
                    <ul className="mt-2 space-y-1.5 text-sm text-foreground/90">
                      {fit.blockers.length ? (
                        fit.blockers.slice(0, 5).map((item) => (
                          <li key={item} className="flex gap-2">
                            <span className="text-red-600">−</span>
                            {item}
                          </li>
                        ))
                      ) : (
                        <li className="text-muted">No blocking gaps identified.</li>
                      )}
                    </ul>
                  </div>
                </div>
                <div className="mt-6 flex flex-wrap gap-2">
                  <ButtonLink href="/app/careers">Compare careers</ButtonLink>
                  <ButtonLink href="/app/skills">Inspect skill gaps</ButtonLink>
                  <ButtonLink href="/app/roadmap">Open roadmap</ButtonLink>
                </div>
              </>
            ) : (
              <EmptyState
                title="No career position yet"
                body="Add a career goal to your profile or complete a career comparison to anchor your readiness calculation."
                action={<ButtonLink href="/app/careers">Explore careers</ButtonLink>}
              />
            )}
          </Panel>

          <div>
            <SectionTitle
              index="GAPS"
              title="Priority skill gaps"
              meta={`${state.skill_gaps.length} assessed`}
            />
            {priorityGaps.length ? (
              <div className="divide-y divide-border-soft border border-border-soft bg-panel/60">
                {priorityGaps.map((gap) => (
                  <div
                    key={`${gap.skill_name}-${gap.importance}`}
                    className="flex flex-col gap-2 p-4 sm:flex-row sm:items-center sm:justify-between"
                  >
                    <div>
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-mono text-sm font-medium">
                          {gap.skill_name}
                        </span>
                        <PriorityBadge priority={gap.priority ?? "P2"} />
                      </div>
                      <p className="mt-1 font-mono text-[10px] text-muted">
                        {gap.importance} · {gap.status} ·{" "}
                        {gap.current_level || "not listed"} →{" "}
                        {gap.required_level || "unspecified"}
                      </p>
                    </div>
                    <Link
                      href="/app/skills"
                      className="font-mono text-[10px] text-muted transition-colors hover:text-accent"
                    >
                      INSPECT →
                    </Link>
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState
                title="No skill gaps recorded"
                body="Career requirements are compared against your confirmed skills once you select a target career."
              />
            )}
          </div>

          <div>
            <SectionTitle
              index="INSIGHTS"
              title="Career insights"
              meta={`${state.insights.length} derived`}
            />
            {state.insights.length ? (
              <div className="grid gap-3 md:grid-cols-2">
                {state.insights.slice(0, 6).map((insight) => (
                  <Panel key={insight.id} className="p-5">
                    <div className="mb-2 flex items-center justify-between gap-2">
                      <span className="font-mono text-[9px] uppercase tracking-wider text-muted">
                        {insight.type.replaceAll("_", " ")}
                      </span>
                      <span
                        className={`font-mono text-[9px] uppercase ${
                          insight.severity === "CRITICAL" ||
                          insight.severity === "WARNING"
                            ? "text-red-600"
                            : "text-muted"
                        }`}
                      >
                        {insight.severity}
                      </span>
                    </div>
                    <h3 className="text-sm font-medium">{insight.title}</h3>
                    <p className="mt-2 text-xs leading-relaxed text-muted">
                      {insight.reason}
                    </p>
                    {insight.recommended_action && (
                      <p className="mt-3 border-t border-border-soft pt-3 text-[11px] text-accent/90">
                        {insight.recommended_action}
                      </p>
                    )}
                  </Panel>
                ))}
              </div>
            ) : (
              <EmptyState
                title="No insights yet"
                body="Insights appear when the deterministic services detect gaps, conflicts or progress across your career state."
              />
            )}
          </div>

          <div>
            <SectionTitle
              index="TRACE"
              title="Agent execution trace"
              meta={runs.length ? `${runs.length} persisted run(s)` : "No runs yet"}
            />
            <Panel className="overflow-hidden">
              <div className="grid lg:grid-cols-[240px_1fr]">
                <div className="border-b border-border-soft lg:border-b-0 lg:border-r">
                  {runs.length ? (
                    <ul className="max-h-80 overflow-y-auto">
                      {runs.map((run) => (
                        <li key={run.id}>
                          <button
                            onClick={() => setSelectedRun(run.id)}
                            className={`w-full border-b border-border-soft px-4 py-3 text-left transition-colors ${
                              selectedRun === run.id
                                ? "bg-accent/5"
                                : "hover:bg-panel-hover"
                            }`}
                          >
                            <span className="block truncate font-mono text-[10px] text-foreground">
                              {run.capability}
                            </span>
                            <span className="mt-1 flex items-center justify-between font-mono text-[9px] text-muted">
                              <span>{run.status}</span>
                              <span>{formatDate(run.started_at)}</span>
                            </span>
                          </button>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="p-5 text-xs leading-relaxed text-muted">
                      Run an agent capability to create a persisted trace.
                      Events are written by the orchestrator — nothing here is
                      simulated.
                    </p>
                  )}
                </div>
                <div className="max-h-80 overflow-y-auto p-4">
                  {traceLoading ? (
                    <p className="font-mono text-[10px] text-muted">
                      Loading events…
                    </p>
                  ) : events.length ? (
                    <ol className="space-y-0">
                      {events.map((event) => (
                        <li
                          key={event.id}
                          className="relative border-l border-border-soft pb-4 pl-4 last:pb-0"
                        >
                          <span className="absolute -left-[3px] top-1.5 h-1.5 w-1.5 rounded-full bg-accent" />
                          <div className="flex flex-wrap items-center gap-2">
                            <span className="font-mono text-[9px] uppercase tracking-wider text-accent/90">
                              {event.event_type}
                            </span>
                            {event.agent_name && (
                              <span className="font-mono text-[9px] text-muted">
                                {event.agent_name}
                              </span>
                            )}
                            {event.tool_name && (
                              <span className="font-mono text-[9px] text-muted-soft">
                                tool:{event.tool_name}
                              </span>
                            )}
                          </div>
                          {event.message && (
                            <p className="mt-1 text-[11px] leading-relaxed text-muted">
                              {event.message}
                            </p>
                          )}
                        </li>
                      ))}
                    </ol>
                  ) : (
                    <p className="font-mono text-[10px] text-muted">
                      Select a run to inspect its persisted events.
                    </p>
                  )}
                </div>
              </div>
            </Panel>
          </div>
        </div>

        <aside className="space-y-6">
          <Panel className="p-5">
            <SectionTitle
              index="PROFILE"
              title="Completeness"
              meta={`${(completeness.score * 100).toFixed(0)}%`}
            />
            <Meter value={completeness.score} />
            <ul className="mt-4 space-y-2">
              {completeness.sections.map((section) => (
                <li
                  key={section.key}
                  className="flex items-center justify-between gap-3 font-mono text-[10px]"
                >
                  <span className={section.present ? "text-muted" : "text-foreground"}>
                    {section.label}
                  </span>
                  <span
                    className={
                      section.present
                        ? "text-zinc-500"
                        : "text-red-600"
                    }
                  >
                    {section.present ? "PRESENT" : "MISSING"}
                  </span>
                </li>
              ))}
            </ul>
            <ButtonLink href="/onboarding/profile">
              Edit profile
            </ButtonLink>
          </Panel>

          <Panel className="p-5">
            <SectionTitle index="LEARNING" title="Roadmap" meta={roadmap.status} />
            <p className="font-mono text-3xl">
              {(roadmap.progress * 100).toFixed(0)}
              <span className="text-sm text-muted">%</span>
            </p>
            <p className="mt-1 text-[11px] text-muted">
              {roadmap.completed_items} of {roadmap.total_skills} items complete
              {roadmap.total_estimated_hours
                ? ` · ${Math.round(roadmap.total_estimated_hours)}h estimated`
                : ""}
            </p>
            <div className="mt-4">
              <Meter value={roadmap.progress} />
            </div>
            <dl className="mt-4 grid grid-cols-3 gap-2 text-center">
              {[
                ["P0", roadmap.p0_count, "text-red-600"],
                ["P1", roadmap.p1_count, "text-red-400"],
                ["P2", roadmap.p2_count, "text-muted"],
              ].map(([label, count, color]) => (
                <div key={String(label)} className="border border-border-soft p-2">
                  <dt className="font-mono text-[9px] text-muted">{label}</dt>
                  <dd className={`font-mono text-lg ${color}`}>{count}</dd>
                </div>
              ))}
            </dl>
            <ButtonLink href="/app/roadmap">Open roadmap</ButtonLink>
          </Panel>

          <Panel className="p-5">
            <SectionTitle index="INTERVIEW" title="Performance" />
            <p className="font-mono text-3xl">
              {interview.latest_overall_score != null
                ? `${(interview.latest_overall_score * 100).toFixed(0)}%`
                : "—"}
            </p>
            <p className="mt-1 text-[11px] text-muted">
              {interview.sessions_count
                ? `${interview.sessions_count} session(s) · last ${formatDate(interview.last_interview_at)}`
                : "No interview sessions yet."}
            </p>
            {interview.weaknesses.length > 0 && (
              <p className="mt-3 text-[11px] text-muted">
                Focus: {interview.weaknesses.join(", ")}
              </p>
            )}
            <ButtonLink href="/app/interview">Open interview lab</ButtonLink>
          </Panel>

          <Panel className="p-5">
            <SectionTitle index="EVIDENCE" title="Trust centre" />
            <div className="grid grid-cols-2 gap-2">
              {[
                ["Supported", evidence.supported_count, "text-zinc-600"],
                ["Inferred", evidence.inferred_count, "text-red-400"],
                ["Uncertain", evidence.uncertain_count, "text-muted"],
                ["Contradicted", evidence.contradicted_count, "text-red-600"],
              ].map(([label, count, color]) => (
                <div key={String(label)} className="border border-border-soft p-2.5">
                  <p className="font-mono text-[9px] uppercase text-muted">
                    {label}
                  </p>
                  <p className={`font-mono text-lg ${color}`}>{count}</p>
                </div>
              ))}
            </div>
            <p className="mt-3 text-[11px] leading-relaxed text-muted">
              {evidence.total_claims} claim(s) verified
              {evidence.last_verified_at
                ? ` · last ${formatDate(evidence.last_verified_at)}`
                : ""}.
            </p>
            <ButtonLink href="/app/trust">Inspect evidence</ButtonLink>
          </Panel>

          {(state.conflicts.length > 0 || stale.length > 0) && (
            <Panel className="p-5">
              <SectionTitle index="SIGNALS" title="Conflicts & stale state" />
              {state.conflicts.slice(0, 3).map((conflict) => (
                <div
                  key={conflict.id}
                  className="border-b border-border-soft py-3 last:border-0"
                >
                  <p className="text-xs font-medium">{conflict.title}</p>
                  <p className="mt-1 text-[11px] leading-relaxed text-muted">
                    {conflict.description}
                  </p>
                </div>
              ))}
              {stale.map((item) => (
                <div
                  key={item.component}
                  className="border-b border-border-soft py-3 last:border-0"
                >
                  <p className="font-mono text-[10px] text-red-600">
                    STALE · {item.component}
                  </p>
                  <p className="mt-1 text-[11px] text-muted">
                    {item.reason || "Derived state is older than its sources."}
                  </p>
                </div>
              ))}
            </Panel>
          )}

          <div className="border border-border-soft p-4">
            <div className="flex items-center justify-between">
              <span className="font-mono text-[9px] uppercase tracking-[0.18em] text-muted">
                State status
              </span>
              <ConfidenceBadge
                status={state.profile_status === "CONFIRMED" ? "SUPPORTED" : "UNCERTAIN"}
              />
            </div>
            <p className="mt-3 font-mono text-[10px] leading-relaxed text-muted-soft">
              Profile {state.profile_status} · updated{" "}
              {formatDate(state.last_updated_at)}. Scores are deterministic;
              narratives are generated separately and never change them.
            </p>
          </div>
        </aside>
      </div>
    </div>
  );
}
