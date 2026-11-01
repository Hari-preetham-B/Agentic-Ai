"use client";

/**
 * CareerTwin frontend API client.
 *
 * Centralised, typed HTTP client so components never scatter raw fetch()
 * calls. All calls go to NEXT_PUBLIC_API_URL (the FastAPI backend).
 * Provider API keys and Supabase service-role keys are NEVER handled here —
 * they remain server-side only.
 */

const API_BASE =
  typeof process !== "undefined" && process.env.NEXT_PUBLIC_API_URL
    ? process.env.NEXT_PUBLIC_API_URL
    : "http://localhost:8000";

// ---------------------------------------------------------------------------
// Auth token management (in-memory, never persisted to localStorage)
// ---------------------------------------------------------------------------

let _authToken: string | null = null;

export function setAuthToken(token: string | null): void {
  _authToken = token;
}

export function getAuthToken(): string | null {
  return _authToken;
}

class ApiError extends Error {
  constructor(
    public status: number,
    public body: unknown,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(
  input: RequestInfo | URL,
  init?: RequestInit,
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...((init?.headers as Record<string, string>) || {}),
  };
  if (_authToken) {
    headers["Authorization"] = `Bearer ${_authToken}`;
  }
  const res = await fetch(input, {
    headers,
    ...init,
  });

  if (!res.ok) {
    let body: unknown = null;
    try {
      body = await res.json();
    } catch {
      body = await res.text();
    }
    throw new ApiError(
      res.status,
      body,
      (body as { message?: string })?.message || `Request failed: ${res.status}`,
    );
  }

  if (res.status === 204) {
    return undefined as T;
  }

  return res.json();
}

export { ApiError };

export function apiErrorMessage(err: unknown): string {
  if (err instanceof ApiError) return err.message;
  if (err && typeof err === "object" && "message" in err) {
    return String((err as { message?: unknown }).message ?? "Unknown error");
  }
  return String(err);
}

export function apiErrorBody(err: unknown): unknown {
  if (err instanceof ApiError) return err.body;
  if (err && typeof err === "object" && "body" in err) {
    return (err as { body?: unknown }).body;
  }
  return undefined;
}

// ---------------------------------------------------------------------------
// Shared types (mirror backend Pydantic schemas)
// ---------------------------------------------------------------------------

export type ProfileStatus = "DRAFT" | "REVIEW" | "CONFIRMED";
export type Proficiency = "BEGINNER" | "INTERMEDIATE" | "ADVANCED" | "EXPERT";
export type Source = "USER_CONFIRMED" | "DOCUMENT_EXTRACTED" | "SYSTEM_INFERRED";

export interface Profile {
  id: string;
  user_id?: string;
  full_name?: string;
  headline?: string;
  email?: string;
  phone?: string;
  location?: string;
  summary?: string;
  profile_status: ProfileStatus;
  created_at: string;
  updated_at: string;
}

export interface ProfileCreate {
  full_name?: string;
  headline?: string;
  email?: string;
  phone?: string;
  location?: string;
  summary?: string;
  profile_status?: ProfileStatus;
}

export interface ProfileUpdate {
  full_name?: string;
  headline?: string;
  email?: string;
  phone?: string;
  location?: string;
  summary?: string;
  profile_status?: ProfileStatus;
}

export interface Education {
  id: string;
  profile_id: string;
  institution: string;
  degree?: string;
  field_of_study?: string;
  start_date?: string;
  end_date?: string;
  description?: string;
  source: Source;
  created_at: string;
}

export interface EducationCreate {
  institution: string;
  degree?: string;
  field_of_study?: string;
  start_date?: string;
  end_date?: string;
  description?: string;
}

export interface Skill {
  id: string;
  profile_id: string;
  name: string;
  category?: string;
  proficiency?: Proficiency;
  years_experience?: number;
  source: Source;
  created_at: string;
}

export interface SkillCreate {
  name: string;
  category?: string;
  proficiency?: Proficiency;
  years_experience?: number;
  source?: Source;
}

export interface Project {
  id: string;
  profile_id: string;
  name: string;
  description?: string;
  technologies?: string[];
  role?: string;
  outcomes?: string;
  start_date?: string;
  end_date?: string;
  source: Source;
  created_at: string;
}

export interface ProjectCreate {
  name: string;
  description?: string;
  technologies?: string[];
  role?: string;
  outcomes?: string;
  start_date?: string;
  end_date?: string;
  source?: Source;
}

export interface Experience {
  id: string;
  profile_id: string;
  organization: string;
  role: string;
  description?: string;
  achievements?: string;
  start_date?: string;
  end_date?: string;
  is_current: boolean;
  source: Source;
  created_at: string;
}

export interface ExperienceCreate {
  organization: string;
  role: string;
  description?: string;
  achievements?: string;
  start_date?: string;
  end_date?: string;
  is_current?: boolean;
  source?: Source;
}

export interface CareerGoal {
  id: string;
  profile_id: string;
  target_role: string;
  target_industry?: string;
  target_domain?: string;
  goal_description?: string;
  priority: number;
  created_at: string;
}

export interface CareerGoalCreate {
  target_role: string;
  target_industry?: string;
  target_domain?: string;
  goal_description?: string;
  priority?: number;
}

export interface ProfileDetail extends Profile {
  education: Education[];
  skills: Skill[];
  projects: Project[];
  experience: Experience[];
  career_goals: CareerGoal[];
}

export interface ValidationErrorDetail {
  field: string;
  code: string;
  message: string;
}

export interface ValidationResult {
  valid: boolean;
  errors: ValidationErrorDetail[];
  warnings: ValidationErrorDetail[];
}

export interface ResumeExtractResponse {
  extracted_text: string;
  file_name: string;
  content_type: string;
  size_bytes: number;
  character_count: number;
  word_count: number;
}

export interface ExtractionMetadata {
  source_type: string;
  source_file_name?: string;
  extraction_warnings: string[];
}

export interface ProfileDraft {
  profile: ProfileCreate;
  education: EducationCreate[];
  skills: SkillCreate[];
  projects: ProjectCreate[];
  experience: ExperienceCreate[];
  career_goals: CareerGoalCreate[];
  extraction_metadata: ExtractionMetadata;
}

// ---------------------------------------------------------------------------
// Profiles
// ---------------------------------------------------------------------------

export async function createProfile(
  data: ProfileCreate,
): Promise<Profile> {
  return request<Profile>(`${API_BASE}/profiles`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function getProfile(profileId: string): Promise<Profile> {
  return request<Profile>(`${API_BASE}/profiles/${profileId}`);
}

export async function getProfileDetail(
  profileId: string,
): Promise<ProfileDetail> {
  return request<ProfileDetail>(`${API_BASE}/profiles/${profileId}/detail`);
}

export async function updateProfile(
  profileId: string,
  data: ProfileUpdate,
): Promise<Profile> {
  return request<Profile>(`${API_BASE}/profiles/${profileId}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export async function deleteProfile(profileId: string): Promise<void> {
  return request<void>(`${API_BASE}/profiles/${profileId}`, {
    method: "DELETE",
  });
}

export async function validateProfile(
  profileId: string,
): Promise<ValidationResult> {
  return request<ValidationResult>(
    `${API_BASE}/profiles/${profileId}/validate`,
  );
}

export async function confirmProfile(
  profileId: string,
): Promise<Profile> {
  return request<Profile>(`${API_BASE}/profiles/${profileId}/confirm`, {
    method: "POST",
  });
}

// ---------------------------------------------------------------------------
// Child records
// ---------------------------------------------------------------------------

type ChildMap = {
  education: { create: EducationCreate; response: Education };
  skills: { create: SkillCreate; response: Skill };
  projects: { create: ProjectCreate; response: Project };
  experience: { create: ExperienceCreate; response: Experience };
  "career-goals": { create: CareerGoalCreate; response: CareerGoal };
};

type Section = keyof ChildMap;

export async function addChild<T extends Section>(
  profileId: string,
  section: T,
  data: ChildMap[T]["create"],
): Promise<ChildMap[T]["response"]> {
  return request<ChildMap[T]["response"]>(
    `${API_BASE}/profiles/${profileId}/${section}`,
    {
      method: "POST",
      body: JSON.stringify(data),
    },
  );
}

export async function listChildren<T extends Section>(
  profileId: string,
  section: T,
): Promise<ChildMap[T]["response"][]> {
  return request<ChildMap[T]["response"][]>(
    `${API_BASE}/profiles/${profileId}/${section}`,
  );
}

export async function updateChild<T extends Section>(
  profileId: string,
  section: T,
  childId: string,
  data: Partial<ChildMap[T]["create"]>,
): Promise<ChildMap[T]["response"]> {
  return request<ChildMap[T]["response"]>(
    `${API_BASE}/profiles/${profileId}/${section}/${childId}`,
    {
      method: "PUT",
      body: JSON.stringify(data),
    },
  );
}

export async function deleteChild(
  profileId: string,
  section: Section,
  childId: string,
): Promise<void> {
  return request<void>(
    `${API_BASE}/profiles/${profileId}/${section}/${childId}`,
    { method: "DELETE" },
  );
}

// ---------------------------------------------------------------------------
// Resume
// ---------------------------------------------------------------------------

export async function uploadResume(
  file: File,
): Promise<ResumeExtractResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${API_BASE}/profiles/extract-resume`, {
    method: "POST",
    body: formData,
    // Do NOT set Content-Type; the browser sets the multipart boundary.
  });

  if (!res.ok) {
    let body: unknown = null;
    try {
      body = await res.json();
    } catch {
      body = await res.text();
    }
    throw new ApiError(
      res.status,
      body,
      (body as { message?: string })?.message || `Upload failed: ${res.status}`,
    );
  }

  return res.json();
}

// ---------------------------------------------------------------------------
// Careers
// ---------------------------------------------------------------------------

export interface CareerSkill {
  skill_name: string;
  category: string | null;
  importance: string;
  minimum_level: string | null;
  description: string | null;
}

export interface CareerTool {
  tool_name: string;
  category: string | null;
  importance: string;
}

export interface CareerProject {
  project_type: string;
  description: string;
  skills_demonstrated: string[] | null;
  difficulty: string | null;
}

export interface CareerSource {
  title: string;
  publisher: string;
  url: string | null;
  source_type: string;
  published_at: string | null;
  reliability: string;
}

export interface CareerResponse {
  id: string;
  slug: string;
  title: string;
  domain: string;
  summary: string | null;
  description: string | null;
  education_expectations: Record<string, unknown> | null;
  experience_expectations: Record<string, unknown> | null;
  skills: CareerSkill[];
  tools: CareerTool[];
  projects: CareerProject[];
  sources: CareerSource[];
}

export interface CareerListResponse {
  careers: CareerResponse[];
}

export interface CareerRequirementsResponse {
  career_id: string;
  slug: string;
  title: string;
  domain: string;
  skills: CareerSkill[];
  tools: CareerTool[];
  projects: CareerProject[];
  sources: CareerSource[];
}

export interface CareerRecommendationItem {
  career_id: string;
  career_title: string;
  career_domain: string;
  fit_score: number;
  matched_core_skills: string[];
  top_gaps: string[];
  reason: string;
}

export interface CareerRecommendationsResponse {
  recommendations: CareerRecommendationItem[];
}

export interface CareerRecommendationsRequest {
  profile_id: string;
  limit?: number;
}

export interface SkillMatchDetail {
  skill_name: string;
  category: string | null;
  importance: string;
  user_level: string | null;
  required_level: string | null;
  status: string;
  score: number;
  reason: string;
}

export interface CareerAnalysisOutput {
  career_id: string;
  career_title: string;
  fit_score: number;
  fit_summary: string;
  strengths: string[];
  skill_gaps: string[];
  recommended_focus: string[];
  relevant_projects: string[];
  caveats: string[];
  metadata: Record<string, unknown>;
}

export interface SkillGapAnalysisOutput {
  career_id: string;
  career_title: string;
  overall_score: number;
  priority_gaps: string[];
  matched_strengths: string[];
  recommendations: string[];
  caveats: string[];
  metadata: Record<string, unknown>;
}

// ---------------------------------------------------------------------------
// Career API functions
// ---------------------------------------------------------------------------

export async function listCareers(): Promise<CareerResponse[]> {
  const { careers } = await request<CareerListResponse>(
    `${API_BASE}/careers`,
  );
  return careers;
}

export async function getCareer(slug: string): Promise<CareerResponse> {
  return request<CareerResponse>(`${API_BASE}/careers/${encodeURIComponent(slug)}`);
}

export async function getCareerRequirements(
  slug: string,
): Promise<CareerRequirementsResponse> {
  return request<CareerRequirementsResponse>(
    `${API_BASE}/careers/${encodeURIComponent(slug)}/requirements`,
  );
}

export async function getCareerRecommendations(
  payload: CareerRecommendationsRequest,
): Promise<CareerRecommendationItem[]> {
  const { recommendations } = await request<CareerRecommendationsResponse>(
    `${API_BASE}/careers/recommendations`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
  );
  return recommendations;
}

// ---------------------------------------------------------------------------
// Evidence API functions
// ---------------------------------------------------------------------------

export interface EvidenceSearchRequest {
  query: string;
  top_k?: number;
  min_similarity?: number;
  source_type?: string;
}

export interface EvidenceSearchResponse {
  results: EvidenceSearchResult[];
}

export interface EvidenceSearchResult {
  chunk_id: string;
  document_id: string;
  source_id: string;
  source_type: string;
  title: string;
  publisher: string;
  url: string | null;
  similarity_score: number;
  content: string;
  chunk_index: number;
}

export interface ClaimVerifyRequest {
  claim_text: string;
  claim_type?: string;
  importance?: string;
  profile_id?: string;
  context?: string;
}

export interface ClaimVerifyResponse {
  claim: string;
  claim_type: string;
  importance: string;
  status: string;
  confidence: number;
  evidence: EvidenceSearchResult[];
  contradictions: EvidenceSearchResult[];
  explanation: string;
  factors: Record<string, unknown>;
}

export interface ClaimResponse {
  id: string;
  profile_id: string | null;
  claim_text: string;
  claim_type: string;
  status: string;
  confidence_score: number | null;
  created_at: string;
}

export interface EvidenceClaimLink {
  evidence_chunk_id: string;
  relationship: string;
  support_score: number | null;
  contradiction_score: number | null;
}

export async function searchEvidence(
  payload: EvidenceSearchRequest,
): Promise<EvidenceSearchResult[]> {
  const { results } = await request<EvidenceSearchResponse>(
    `${API_BASE}/evidence/search`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
  );
  return results;
}

export async function verifyClaim(
  payload: ClaimVerifyRequest,
): Promise<ClaimVerifyResponse> {
  return request<ClaimVerifyResponse>(`${API_BASE}/claims/verify`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getClaim(claimId: string): Promise<ClaimResponse> {
  return request<ClaimResponse>(
    `${API_BASE}/claims/${encodeURIComponent(claimId)}`
  );
}

export async function getClaimEvidence(
  claimId: string,
): Promise<EvidenceClaimLink[]> {
  return request<EvidenceClaimLink[]>(
    `${API_BASE}/claims/${encodeURIComponent(claimId)}/evidence`,
  );
}

// ---------------------------------------------------------------------------
// CareerTwin unified intelligence
// ---------------------------------------------------------------------------

export interface CareerTwinSkill {
  name: string;
  category: string | null;
  proficiency: string | null;
  source: string;
  years_experience: number | null;
}

export interface CareerTwinCareerFit {
  career_id: string;
  career_title: string;
  fit_score: number;
  readiness_level: string;
  strongest_areas: string[];
  weakest_areas: string[];
  blockers: string[];
  rationale: string;
}

export interface CareerTwinSkillGap {
  skill_name: string;
  importance: string;
  current_level: string | null;
  required_level: string | null;
  status: string;
  priority: string | null;
}

export interface CareerTwinRoadmapSummary {
  roadmap_id: string | null;
  total_skills: number;
  p0_count: number;
  p1_count: number;
  p2_count: number;
  total_estimated_hours: number;
  status: string;
  generated_at: string | null;
  stale: boolean;
}

export interface CareerTwinInterviewSummary {
  sessions_count: number;
  latest_overall_score: number | null;
  skill_performance: Record<string, unknown>[];
  strengths: string[];
  weaknesses: string[];
  recommended_skills: string[];
  last_interview_at: string | null;
}

export interface CareerTwinEvidenceSummary {
  total_claims: number;
  supported_count: number;
  inferred_count: number;
  uncertain_count: number;
  contradicted_count: number;
  last_verified_at: string | null;
}

export interface CareerTwinInsight {
  id: string;
  type: string;
  severity: string;
  title: string;
  reason: string;
  affected_entity: string | null;
  affected_skill: string | null;
  affected_career: string | null;
  source_signals: string[];
  recommended_action: string | null;
  classification: string;
}

export interface CareerTwinConflict {
  id: string;
  type: string;
  severity: string;
  title: string;
  description: string;
  affected_entity: string | null;
  affected_skill: string | null;
  source_a: string | null;
  source_b: string | null;
  resolution: string | null;
}

export interface CareerTwinStaleState {
  component: string;
  generated_at: string | null;
  source_updated_at: string | null;
  is_stale: boolean;
  reason: string | null;
}

export interface CareerTwinState {
  profile_id: string;
  profile_name: string | null;
  profile_status: string;
  headline: string | null;
  education: Record<string, unknown>[];
  experience: Record<string, unknown>[];
  projects: Record<string, unknown>[];
  confirmed_skills: CareerTwinSkill[];
  documented_skills: CareerTwinSkill[];
  target_careers: string[];
  active_target_career: string | null;
  career_fit: CareerTwinCareerFit | null;
  skill_gaps: CareerTwinSkillGap[];
  roadmap_summary: CareerTwinRoadmapSummary;
  interview_summary: CareerTwinInterviewSummary;
  evidence_summary: CareerTwinEvidenceSummary;
  insights: CareerTwinInsight[];
  conflicts: CareerTwinConflict[];
  stale_components: CareerTwinStaleState[];
  readiness_level: string;
  readiness_score: number;
  last_updated_at: string | null;
  metadata: Record<string, unknown>;
}

export async function getCareerTwinState(
  profileId: string,
  activeTargetCareer?: string,
): Promise<CareerTwinState> {
  const params = new URLSearchParams({ profile_id: profileId });
  if (activeTargetCareer) params.set("active_target_career", activeTargetCareer);
  return request<CareerTwinState>(`${API_BASE}/careertwin?${params.toString()}`);
}

export async function getCareerTwinInsights(
  profileId: string,
  activeTargetCareer?: string,
): Promise<CareerTwinInsight[]> {
  const params = new URLSearchParams({ profile_id: profileId });
  if (activeTargetCareer) params.set("active_target_career", activeTargetCareer);
  const { insights } = await request<{ insights: CareerTwinInsight[] }>(
    `${API_BASE}/careertwin/insights?${params.toString()}`,
  );
  return insights;
}

export async function getCareerTwinConflicts(
  profileId: string,
  activeTargetCareer?: string,
): Promise<CareerTwinConflict[]> {
  const params = new URLSearchParams({ profile_id: profileId });
  if (activeTargetCareer) params.set("active_target_career", activeTargetCareer);
  const { conflicts } = await request<{ conflicts: CareerTwinConflict[] }>(
    `${API_BASE}/careertwin/conflicts?${params.toString()}`,
  );
  return conflicts;
}

export async function getCareerTwinReadiness(
  profileId: string,
  careerSlug: string,
): Promise<{
  readiness_level: string;
  readiness_score: number;
  rationale: string;
  blockers: string[];
}> {
  const params = new URLSearchParams({
    profile_id: profileId,
    career_slug: careerSlug,
  });
  return request<{
    readiness_level: string;
    readiness_score: number;
    rationale: string;
    blockers: string[];
  }>(`${API_BASE}/careertwin/readiness?${params.toString()}`);
}

export async function getCareerTwinStale(
  profileId: string,
  activeTargetCareer?: string,
): Promise<CareerTwinStaleState[]> {
  const params = new URLSearchParams({ profile_id: profileId });
  if (activeTargetCareer) params.set("active_target_career", activeTargetCareer);
  const { stale_components } = await request<{ stale_components: CareerTwinStaleState[] }>(
    `${API_BASE}/careertwin/stale?${params.toString()}`,
  );
  return stale_components;
}

export async function refreshCareerTwin(
  profileId: string,
): Promise<{ refreshed_components: string[]; unchanged_components: string[]; message: string }> {
  return request<{ refreshed_components: string[]; unchanged_components: string[]; message: string }>(
    `${API_BASE}/careertwin/refresh`,
    {
      method: "POST",
      body: JSON.stringify({ profile_id: profileId, force: false }),
    },
  );
}

// ---------------------------------------------------------------------------
// Agent runs
// ---------------------------------------------------------------------------

export interface AgentRunRequest {
  profile_id: string;
  capability: string;
  input: string;
}

export interface AgentRunResponse {
  run_id: string | null;
  status: string;
  agent: string | null;
  result: Record<string, unknown> | null;
  error: string | null;
}

export async function runAgentCapability(
  payload: AgentRunRequest,
): Promise<AgentRunResponse> {
  return request<AgentRunResponse>(`${API_BASE}/agent-runs`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function extractResumeDraft(
  file: File,
): Promise<ProfileDraft> {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${API_BASE}/profiles/extract-resume/draft`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    let body: unknown = null;
    try {
      body = await res.json();
    } catch {
      body = await res.text();
    }
    throw new ApiError(
      res.status,
      body,
      (body as { message?: string })?.message || `Draft extraction failed: ${res.status}`,
    );
  }

  return res.json();
}
