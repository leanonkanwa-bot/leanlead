import axios from "axios";

export const api = axios.create({ baseURL: "/api" });

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
  onboarded: boolean;
}

export type Stage = "new" | "contacted" | "replied" | "booked" | "closed";

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

  onboard: (d: {
    niche: string; offer_description: string; target_audience: string;
    calendly_link?: string; airtable_base_id?: string;
    airtable_api_key?: string; apify_api_key?: string;
  }) => api.post("/auth/onboard", d),
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
    api.post(`/pipeline/${id}/reply`, d),
  syncCrm: (id: number) => api.post(`/pipeline/${id}/sync-crm`),
};

/* ── Follow-ups ── */
export const followupsApi = {
  due:      () => api.get<FollowupDue[]>("/followups/due"),
  generate: (id: number, day: number) =>
    api.post<{ message: string }>(`/followups/${id}/generate`, { day }),
  markSent: (id: number, day: number) =>
    api.post(`/followups/${id}/mark-sent`, { day }),
};

/* ── Prospecting ── */
export const prospectingApi = {
  run: (d: { platform: string; hashtags: string[]; max_results: number; auto_qualify: boolean }) =>
    api.post<{ job_id: number }>("/prospecting/run", d),
  jobs: () => api.get<{
    id: number; platform: string; hashtags: string[]; status: string;
    leads_found: number; error_message?: string; started_at?: string;
  }[]>("/prospecting/jobs"),
  suggestHashtags: () => api.get<{ hashtags: string[] }>("/prospecting/suggest-hashtags"),
  fromUrl: (d: { profile_url: string; auto_write: boolean }) =>
    api.post<Lead>("/prospecting/from-url", d),
};
