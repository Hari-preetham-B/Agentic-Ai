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
  const res = await fetch(input, {
    headers: { "Content-Type": "application/json", ...init?.headers },
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
