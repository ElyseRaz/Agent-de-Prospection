// Types miroir des schemas Pydantic du backend (backend/app/schemas/*.py).
// Les champs Decimal sont serialises en string par Pydantic v2 (precision),
// jamais en number : garder `string | null` cote TypeScript.

export type UserRole = "admin" | "user";

export interface User {
  id: string;
  email: string;
  role: UserRole;
  is_active: boolean;
  totp_enabled: boolean;
  created_at: string;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface AccessToken {
  access_token: string;
  token_type: string;
}

export type ContractType = "freelance" | "cdi" | "mission";
export type SeniorityLevel = "junior" | "intermediate" | "senior" | "lead" | "expert";
export type RemoteType = "full_remote" | "remote_zone_restricted" | "hybrid" | "onsite";
export type RatePeriod = "hour" | "day" | "month" | "year" | "fixed";
export type JobStatus = "active" | "expired" | "archived";

export interface RiskReason {
  code: string;
  label: string;
  severity: "low" | "medium" | "high";
}

export interface Job {
  id: string;
  company_id: string | null;
  source_id: string;
  url: string;
  title: string;
  description_clean: string;
  language: string;
  contract_type: ContractType | null;
  seniority: SeniorityLevel | null;
  rate_min: string | null;
  rate_max: string | null;
  rate_currency: string | null;
  rate_period: RatePeriod | null;
  rate_eur_normalized: string | null;
  duration_months: string | null;
  workload_days_week: string | null;
  remote_type: RemoteType | null;
  timezone_constraint: string | null;
  required_languages: string[];
  billing_mode: string | null;
  application_channel: string | null;
  posted_at: string | null;
  detected_at: string;
  last_seen_at: string;
  status: JobStatus;
  quality_score: number;
  risk_score: number;
  risk_reasons: RiskReason[];
  risk_assessed_at: string | null;
}

export interface JobDetail extends Job {
  duplicate_urls: string[];
}

export interface JobSearchResult {
  job: Job;
  score: number;
}

export interface JobSearchResponse {
  results: JobSearchResult[];
  total: number;
  limit: number;
  offset: number;
}

export interface JobSearchFilters {
  q?: string;
  rate_min_eur?: string;
  rate_max_eur?: string;
  rate_currency?: string;
  skill?: string[];
  seniority?: SeniorityLevel;
  language?: string;
  remote_type?: RemoteType;
  contract_type?: ContractType;
  source_slug?: string;
  status?: JobStatus;
  sort?: "relevance" | "freshness" | "rate";
  limit?: number;
  offset?: number;
}

export type SkillLevel = "beginner" | "intermediate" | "advanced" | "expert";

export interface ProfileSkill {
  skill_slug: string;
  skill_label: string;
  level: SkillLevel;
  years: string | null;
  is_required: boolean;
}

export interface ProfileWeights {
  semantic: number;
  skills: number;
  rate: number;
  timezone: number;
  reliability: number;
  [key: string]: number;
}

export interface Profile {
  id: string;
  user_id: string;
  name: string;
  target_rate: string | null;
  floor_rate: string | null;
  currency: string | null;
  availability_date: string | null;
  timezone: string | null;
  languages: string[];
  excluded_industries: string[];
  desired_contract_types: string[];
  weights: ProfileWeights;
  created_at: string;
  updated_at: string;
}

export interface ProfileDetail extends Profile {
  skills: ProfileSkill[];
}

export interface ProfileCreatePayload {
  name: string;
  target_rate?: string | null;
  floor_rate?: string | null;
  currency?: string | null;
  availability_date?: string | null;
  timezone?: string | null;
  languages?: string[];
  excluded_industries?: string[];
  desired_contract_types?: string[];
}

export type ProfileUpdatePayload = Partial<ProfileCreatePayload>;

export interface ProfileSkillInput {
  skill_slug: string;
  level: SkillLevel;
  years?: string | null;
  is_required: boolean;
}

export interface ScoreBreakdownItem {
  criterion: string;
  points: number;
  label: string;
}

export interface MatchResult {
  job: Job;
  score: number;
  breakdown: ScoreBreakdownItem[];
}

export interface MatchListResponse {
  results: MatchResult[];
}

export type MatchFeedbackAction = "saved" | "rejected";

export type ApplicationStage =
  | "spotted"
  | "to_apply"
  | "applied"
  | "in_discussion"
  | "proposal"
  | "won"
  | "lost";

export interface Application {
  id: string;
  profile_id: string;
  job_id: string;
  stage: ApplicationStage;
  applied_at: string | null;
  last_contact_at: string | null;
  next_followup_at: string | null;
  expected_value: string | null;
  outcome: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface ApplicationEvent {
  id: string;
  type: "stage_changed" | "note_updated" | "followup_scheduled";
  payload: Record<string, unknown>;
  occurred_at: string;
}

export interface ApplicationDetail extends Application {
  job: Job;
  events: ApplicationEvent[];
}

export interface ApplicationUpdatePayload {
  notes?: string | null;
  next_followup_at?: string | null;
  expected_value?: string | null;
  outcome?: string | null;
}

export type BlacklistEntityType = "company" | "recruiter";

export interface BlacklistEntry {
  id: string;
  user_id: string | null;
  entity_type: BlacklistEntityType;
  value: string;
  reason: string | null;
  created_at: string;
}

export interface ApiErrorBody {
  detail?: string | { msg: string; loc: (string | number)[] }[];
}
