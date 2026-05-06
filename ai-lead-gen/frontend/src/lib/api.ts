import axios from "axios";

export const api = axios.create({ baseURL: "/api" });

// Inject JWT on every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("ll_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Types
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
  reply_received?: string;
  suggested_reply?: string;
  notes?: string;
  airtable_record_id?: string;
  created_at: string;
  updated_at: string;
}

export type Stage = "new" | "qualified" | "messaged" | "replied" | "booked" | "closed";

// Auth
export const authApi = {
  register: (data: { email: string; password: string; name: string }) =>
    api.post<{ access_token: string; coach_id: number; name: string; onboarded: boolean }>(
      "/auth/register",
      data
    ),
  login: (email: string, password: string) => {
    const form = new URLSearchParams();
    form.set("username", email);
    form.set("password", password);
    return api.post<{ access_token: string; coach_id: number; name: string; onboarded: boolean }>(
      "/auth/login",
      form,
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

// Leads
export const leadsApi = {
  list: (stage?: Stage) =>
    api.get<Lead[]>("/leads", { params: stage ? { stage } : {} }),
  create: (data: Partial<Lead>) => api.post<Lead>("/leads", data),
  update: (id: number, data: Partial<Lead>) => api.patch<Lead>(`/leads/${id}`, data),
  delete: (id: number) => api.delete(`/leads/${id}`),
};

// Pipeline (agents)
export const pipelineApi = {
  qualify: (leadId: number) => api.post(`/pipeline/${leadId}/qualify`),
  write: (leadId: number) => api.post(`/pipeline/${leadId}/write`),
  reply: (leadId: number, data: { lead_reply: string; conversation_history?: string }) =>
    api.post(`/pipeline/${leadId}/reply`, data),
  syncCrm: (leadId: number) => api.post(`/pipeline/${leadId}/sync-crm`),
};
