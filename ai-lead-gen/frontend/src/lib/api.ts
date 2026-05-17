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
  created_at: string;
  updated_at: string;
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
  write: (leadId: number) => api.post(`/pipeline/${leadId}/write`),
  reply: (leadId: number, data: { lead_reply: string; conversation_history?: string }) =>
    api.post(`/pipeline/${leadId}/reply`, data),
  syncCrm: (leadId: number) => api.post(`/pipeline/${leadId}/sync-crm`),
  setStage: (leadId: number, stage: Stage) => api.patch(`/pipeline/${leadId}/stage`, { stage }),
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
