import axios from "axios";

export const api = axios.create({ baseURL: import.meta.env.VITE_API_URL || "https://guidable-favorable-pasture.ngrok-free.dev" });

api.interceptors.request.use((cfg) => {
  const t = localStorage.getItem("ll_token");
  if (t) cfg.headers.Authorization = `Bearer ${t}`;
  return cfg;
});

/* ── Types ── */
export interface Coach {
  id: number; email: string; name: string;
  niche?: string; offer_description?: string;
  target_audience?: string; calendly_link?: string;
  icp_pain_points?: string[];
  onboarded: boolean; has_apify_key?: boolean;
  offer_price?: number | null;
}

export interface AnalyticsData {
  leads_this_week: number;
  leads_this_month: number;
  total_leads: number;
  by_stage: Record<string, number>;
  reply_rate: number;
  booking_rate: number;
  top_hashtags: { tag: string; leads: number }[];
  followup_conversions: { label: string; count: number }[];
  followup_sent: { d2: number; d4: number; d7: number };
  closed_leads: number;
  offer_price: number;
  projected_mrr: number;
  onboarding: {
    account_created: boolean;
    niche_set: boolean;
    first_lead: boolean;
    first_dm: boolean;
    first_booking: boolean;
  };
}

export type Stage = "new" | "contacted" | "replied" | "booked" | "closed";
export type Classification = "POSITIF" | "NEUTRE" | "NEGATIF" | "SIGNAL_ACHAT";

export interface ReplyAnalysis {
  classification: Classification;
  reasoning: string;
  suggested_reply: string;
  inject_calendly: boolean;
}

export interface Lead {
  id: number; coach_id: number;
  name: string; handle: string; platform: string;
  profile_url?: string; bio?: string; followers: number; posts_summary?: string;
  qualification_score: number; qualification_reason?: string;
  pain_points: string[]; recommended_angle?: string;
  stage: Stage;
  outreach_message?: string; messaged_at?: string;
  followup_d2_message?: string; followup_d2_sent_at?: string;
  followup_d4_message?: string; followup_d4_sent_at?: string;
  followup_d7_message?: string; followup_d7_sent_at?: string;
  reply_received?: string; suggested_reply?: string;
  notes?: string; airtable_record_id?: string;
  created_at: string; updated_at: string;
}

export interface FollowupDue {
  lead_id: number; name: string; handle: string; platform: string;
  bio?: string; messaged_at: string; outreach_message?: string; due_day: 2 | 4 | 7;
  followup_d2_message?: string; followup_d4_message?: string; followup_d7_message?: string;
  followup_d2_sent_at?: string; followup_d4_sent_at?: string; followup_d7_sent_at?: string;
}

/* ── Auth ── */
export const authApi = {
  register: (d: { email: string; password: string; name: string }) =>
    api.post<{ access_token: string; name: string; onboarded: boolean }>("/auth/register", d),

  login: (email: string, password: string) => {
    const f = new URLSearchParams({ username: email, password });
    return api.post<{ access_token: string; name: string; onboarded: boolean }>(
      "/auth/login", f, { headers: { "Content-Type": "application/x-www-form-urlencoded" } }
    );
  },

  me: () => api.get<Coach>("/auth/me"),

  updateSettings: (d: {
    niche?: string; offer_description?: string; target_audience?: string;
    icp_pain_points?: string[]; calendly_link?: string;
    apify_api_key?: string; offer_price?: number;
  }) => api.patch("/auth/settings", d),

  onboard: (d: {
    niche: string; offer_description: string; target_audience: string;
    icp_pain_points?: string[]; calendly_link?: string;
    airtable_base_id?: string; airtable_api_key?: string; apify_api_key?: string;
  }) => api.post("/auth/onboard", d),

  detectNiche: (description: string) =>
    api.post<{
      niche: string;
      target_audience: string;
      pain_points: string[];
      hashtags: string[];
    }>("/auth/detect-niche", { description }),
};

/* ── Leads ── */
export const leadsApi = {
  list: () => api.get<Lead[]>("/leads"),
  create: (d: Partial<Lead>) => api.post<Lead>("/leads", d),
  update: (id: number, d: Partial<Lead>) => api.patch<Lead>(`/leads/${id}`, d),
  delete: (id: number) => api.delete(`/leads/${id}`),
};

/* ── Pipeline agents ── */
export const pipelineApi = {
  qualify: (id: number) => api.post(`/pipeline/${id}/qualify`),
  write:   (id: number) => api.post(`/pipeline/${id}/write`),
  reply:   (id: number, d: { lead_reply: string; conversation_history?: string }) =>
    api.post<ReplyAnalysis>(`/pipeline/${id}/reply`, d),
};

/* ── Follow-ups ── */
export const followupsApi = {
  due:      () => api.get<FollowupDue[]>("/followups/due"),
  generate: (id: number, day: number) =>
    api.post<{ message: string }>(`/followups/${id}/generate`, { day }),
  send:     (id: number, day: number) =>
    api.post<{ message: string; day: number }>(`/followups/${id}/send`, { day }),
  markSent: (id: number, day: number) =>
    api.post(`/followups/${id}/mark-sent`, { day }),
};

/* ── Analytics ── */
export const analyticsApi = {
  get: () => api.get<AnalyticsData>("/analytics"),
};

/* ── Autonomous Agent ── */
export interface AgentRunSummary {
  id: number; status: string;
  platforms_searched: string[];
  leads_found: number; leads_qualified: number;
  dms_generated: number; high_score_leads: number;
  error_message?: string;
  started_at?: string; finished_at?: string;
}

export interface AgentStatus {
  enabled: boolean;
  frequency_hours: number;
  platforms: string[];
  max_results_per_platform: number;
  dm_threshold: number;
  webhook_url?: string;
  last_run_at?: string;
  next_run_at?: string;
  last_run?: AgentRunSummary | null;
}

export const agentApi = {
  status: () => api.get<AgentStatus>("/agent/status"),
  settings: (d: Partial<{
    enabled: boolean; frequency_hours: number; platforms: string[];
    max_results_per_platform: number; dm_threshold: number; webhook_url: string;
  }>) => api.patch("/agent/settings", d),
  trigger: () => api.post<{ ok: boolean; message: string }>("/agent/trigger"),
  runs: () => api.get<AgentRunSummary[]>("/agent/runs"),
};

/* ── Prospecting ── */
export const prospectingApi = {
  run: (d: { platform: string; hashtags: string[]; max_results: number; auto_qualify: boolean }) =>
    api.post<{ job_id: number }>("/prospecting/run", d),
  jobs: () => api.get<{
    id: number; platform: string; hashtags: string[]; status: string;
    leads_found: number; error_message?: string; started_at?: string;
  }[]>("/prospecting/jobs"),
  suggestHashtags: (platform: string = "instagram") =>
    api.get<{ hashtags: string[] }>("/prospecting/suggest-hashtags", { params: { platform } }),
  fromUrl: (d: { profile_url: string; auto_write: boolean }) =>
    api.post<Lead>("/prospecting/from-url", d),
};
