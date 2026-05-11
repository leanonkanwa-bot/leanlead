import axios from "axios";

export const api = axios.create({ baseURL: "/api" });

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("ll_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

/* ── Types ─────────────────────────────────────────────────────── */
export interface Coach {
  id: number;
  email: string;
  name: string;
  niche?: string;
  offer_description?: string;
  target_audience?: string;
  calendly_link?: string;
  onboarded: boolean;
}

export type Stage = "new" | "contacted" | "replied" | "booked" | "closed";

export interface Lead {
  id: number;
  coach_id: number;
  name: string;
  handle: string;
  platform: string;
  profile_url?: string;
  bio?: string;
  followers: number;
  posts_summary?: string;
  qualification_score: number;
  qualification_reason?: string;
  pain_points: string[];
  recommended_angle?: string;
  stage: Stage;
  outreach_message?: string;
  messaged_at?: string;
  followup_d2_message?: string;
  followup_d2_sent_at?: string;
  followup_d4_message?: string;
  followup_d4_sent_at?: string;
  followup_d7_message?: string;
  followup_d7_sent_at?: string;
  reply_received?: string;
  suggested_reply?: string;
  notes?: string;
  airtable_record_id?: string;
  // v3 intelligence
  language?: string;
  psychographic_profile?: Record<string, unknown>;
  response_probability?: number;
  dm_variant_b?: string;
  dm_variant_sent?: string;
  warming_status?: string;
  warming_comment?: string;
  source_tag?: string;
  // v4 intelligence
  predicted_objection?: string;
  score_delta?: number;
  escalation_alert?: boolean;
  // v5 intelligence
  aspiration_gap_score?: number;
  price_tier?: "premium" | "mid" | "budget";
  trust_velocity?: "fast" | "slow" | "unknown";
  voice_tone_intensity?: number;
  // v6 intelligence
  churn_risk?: number;
  reengagement_message?: string;
  // v7 intelligence
  enriched_data?: EnrichedData;
  enriched_at?: string;
  sales_script?: SalesScript;
  nurture_sequence?: NurtureMessage[];
  nurture_step?: number;
  converting_angle?: string;
  created_at: string;
  updated_at: string;
}

export interface EnrichedData {
  linkedin_role?: string;
  linkedin_company?: string;
  estimated_income?: string;
  income_confidence?: string;
  content_consumption?: string[];
  tech_stack?: string[];
  interests?: string[];
  other_platforms?: string[];
  engagement_signals?: string[];
  business_type?: string;
}

export interface SalesScript {
  opener?: string;
  discovery_questions?: string[];
  objections?: Array<{ objection: string; response: string }>;
  closing?: string;
  post_call_followup?: string;
}

export interface NurtureMessage {
  day: number;
  trigger: string;
  angle: string;
  message: string;
}

export interface ICPData {
  summary?: string;
  demographics?: Record<string, unknown>;
  psychographics?: Record<string, unknown>;
  pain_points?: string[];
  buying_triggers?: string[];
  objections?: string[];
  best_dm_angles?: string[];
  content_consumed?: string[];
  search_terms?: string[];
  platforms_ranked?: string[];
}

export interface CoachICP {
  icp: ICPData | null;
  generated_at: string | null;
  version: number;
}

export interface VelocityData {
  stage_velocity: Record<string, { count: number; avg_days: number; stuck_count: number }>;
  stuck_leads: Array<{ lead_id: number; name: string; handle: string; stage: string; days_in_stage: number; score: number }>;
  focus_today: Array<{ lead_id: number; name: string; handle: string; stage: string; score: number; action: string }>;
  total_active: number;
  avg_days_to_reply: number;
}

export interface RoiData {
  total_leads: number;
  cost_per_lead_leanlead: number;
  cost_per_lead_agency_high: number;
  savings_vs_agency: number;
  revenue_by_source: Record<string, number>;
  predicted_ltv_pipeline: number;
  pipeline_growth_rate: number;
  revenue_closed: number;
}

export interface AttributionData {
  platform_performance: Record<string, { total: number; converted: number; avg_score: number; conversion_rate: number }>;
  followup_wins: Record<string, number>;
  top_converting_angles: Array<{ angle: string; conversions: number }>;
  top_converting_pains: Array<{ pain: string; conversions: number }>;
  source_funnel: Record<string, { leads: number; contacted: number; replied: number; booked: number; closed: number }>;
  total_converted: number;
}

export interface CompetitorScan {
  handle: string;
  platform: string;
  price_signal?: string;
  dissatisfied_count?: number;
  dissatisfied_handles?: string[];
  content_themes?: string[];
  messaging_style?: string;
  gaps?: string[];
  positioning?: string;
  scanned_at?: string;
}

export interface CompetitiveReport {
  competitors: CompetitorScan[];
  report: {
    market_gaps?: string[];
    unique_angle?: string;
    opportunities?: string[];
    avoid?: string[];
    price_position?: string;
    alert?: string;
  } | null;
  last_scanned: string | null;
}

export interface ProspectingJob {
  id: number;
  platform: string;
  hashtags: string[];
  max_results: number;
  status: "pending" | "running" | "done" | "error";
  leads_found: number;
  error_message?: string;
  started_at?: string;
  finished_at?: string;
}

export interface FollowupDue {
  lead_id: number;
  name: string;
  handle: string;
  platform: string;
  bio?: string;
  messaged_at: string;
  outreach_message?: string;
  due_day: 2 | 4 | 7;
  followup_d2_sent_at?: string;
  followup_d4_sent_at?: string;
  followup_d7_sent_at?: string;
  followup_d2_message?: string;
  followup_d4_message?: string;
  followup_d7_message?: string;
}

/* ── Auth ───────────────────────────────────────────────────────── */
export const authApi = {
  register: (data: { email: string; password: string; name: string }) =>
    api.post<{ access_token: string; coach_id: number; name: string; onboarded: boolean }>(
      "/auth/register", data
    ),
  login: (email: string, password: string) => {
    const form = new URLSearchParams();
    form.set("username", email);
    form.set("password", password);
    return api.post<{ access_token: string; coach_id: number; name: string; onboarded: boolean }>(
      "/auth/login", form,
      { headers: { "Content-Type": "application/x-www-form-urlencoded" } }
    );
  },
  me: () => api.get<Coach>("/auth/me"),
  onboard: (data: {
    niche: string;
    offer_description: string;
    target_audience: string;
    calendly_link?: string;
    airtable_base_id?: string;
    airtable_api_key?: string;
    apify_api_key?: string;
  }) => api.post("/auth/onboard", data),
};

/* ── Leads ──────────────────────────────────────────────────────── */
export const leadsApi = {
  list: (stage?: Stage) => api.get<Lead[]>("/leads", { params: stage ? { stage } : {} }),
  create: (data: Partial<Lead>) => api.post<Lead>("/leads", data),
  update: (id: number, data: Partial<Lead>) => api.patch<Lead>(`/leads/${id}`, data),
  delete: (id: number) => api.delete(`/leads/${id}`),
};

/* ── Pipeline agents ────────────────────────────────────────────── */
export const pipelineApi = {
  qualify: (leadId: number) => api.post(`/pipeline/${leadId}/qualify`),
  rescan: (leadId: number) => api.post(`/pipeline/${leadId}/rescan`),
  write: (leadId: number) => api.post(`/pipeline/${leadId}/write`),
  reply: (leadId: number, data: { lead_reply: string; conversation_history?: string }) =>
    api.post(`/pipeline/${leadId}/reply`, data),
  syncCrm: (leadId: number) => api.post(`/pipeline/${leadId}/sync-crm`),
  setStage: (leadId: number, stage: Stage) => api.patch(`/pipeline/${leadId}/stage`, { stage }),
  reengage: (leadId: number) => api.post(`/pipeline/${leadId}/reengage`),
  enrich: (leadId: number) => api.post<Lead>(`/pipeline/${leadId}/enrich`),
  salesScript: (leadId: number) => api.post<Lead>(`/pipeline/${leadId}/sales-script`),
  nurture: (leadId: number) => api.post<Lead>(`/pipeline/${leadId}/nurture`),
};

/* ── Prospecting ────────────────────────────────────────────────── */
export const prospectingApi = {
  run: (data: { platform: string; hashtags: string[]; max_results: number; auto_qualify: boolean }) =>
    api.post<{ job_id: number; status: string }>("/prospecting/run", data),
  jobs: () => api.get<ProspectingJob[]>("/prospecting/jobs"),
  suggestHashtags: () => api.get<{ hashtags: string[] }>("/prospecting/suggest-hashtags"),
};

/* ── Follow-ups ─────────────────────────────────────────────────── */
export const followupsApi = {
  due: () => api.get<FollowupDue[]>("/followups/due"),
  generate: (leadId: number, day: number) =>
    api.post<{ message: string; day: number }>(`/followups/${leadId}/generate`, { day }),
  markSent: (leadId: number, day: number) =>
    api.post(`/followups/${leadId}/mark-sent`, { day }),
};

/* ── ICP ─────────────────────────────────────────────────────────── */
export const icpApi = {
  getQuestions: () => api.get<{ questions: string[] }>("/icp/questions"),
  get: () => api.get<CoachICP>("/icp"),
  generate: (data: { answers?: Record<string, string> }) =>
    api.post<{ ok: boolean; icp: ICPData; version: number }>("/icp/generate", data),
  update: (data: { data: Partial<ICPData> }) => api.patch<{ ok: boolean }>("/icp", data),
  learn: () => api.post<{ ok: boolean; icp: ICPData; version: number; learned_from: Record<string, number> }>("/icp/learn"),
};

/* ── Analytics ───────────────────────────────────────────────────── */
export const analyticsApi = {
  get: () => api.get("/analytics"),
  getRoi: () => api.get<RoiData>("/analytics/roi"),
  getAttribution: () => api.get<AttributionData>("/analytics/attribution"),
  getVelocity: () => api.get<VelocityData>("/analytics/velocity"),
  getCompetitive: () => api.get<CompetitiveReport>("/analytics/competitive"),
  scanCompetitors: () => api.post("/analytics/competitive/scan"),
};
