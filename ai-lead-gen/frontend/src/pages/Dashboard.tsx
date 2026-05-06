import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { authApi, leadsApi, pipelineApi, followupsApi, type Lead } from "../lib/api";
import KanbanBoard from "../components/KanbanBoard";
import ProspectingPanel from "../components/ProspectingPanel";
import FollowupQueue from "../components/FollowupQueue";

/* ─── Add-lead modal ─────────────────────────────────────────────── */
function AddLeadModal({ onClose }: { onClose: () => void }) {
  const qc = useQueryClient();
  const [form, setForm] = useState({
    name: "",
    handle: "",
    platform: "instagram",
    profile_url: "",
    bio: "",
    followers: "",
    posts_summary: "",
    notes: "",
  });
  const [autoQualify, setAutoQualify] = useState(true);

  const create = useMutation({
    mutationFn: async () => {
      const { data: lead } = await leadsApi.create({
        ...form,
        followers: parseInt(form.followers) || 0,
      });
      if (autoQualify) await pipelineApi.qualify(lead.id);
      return lead;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["leads"] });
      onClose();
    },
  });

  function set(key: string, val: string) {
    setForm((f) => ({ ...f, [key]: val }));
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="w-full max-w-lg bg-slate-900 border border-slate-700 rounded-2xl overflow-hidden shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between p-5 border-b border-slate-800">
          <h2 className="font-semibold text-white">Add a lead manually</h2>
          <button onClick={onClose} className="text-slate-500 hover:text-white text-xl leading-none">×</button>
        </div>
        <div className="p-5 space-y-4 overflow-y-auto max-h-[70vh]">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-xs text-slate-400 mb-1 block">Full name</label>
              <input
                value={form.name}
                onChange={(e) => set("name", e.target.value)}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:border-sky-500"
                placeholder="Jane Smith"
              />
            </div>
            <div>
              <label className="text-xs text-slate-400 mb-1 block">Handle</label>
              <div className="flex">
                <span className="bg-slate-700 border border-slate-600 border-r-0 rounded-l-lg px-2.5 text-slate-400 text-sm flex items-center">@</span>
                <input
                  value={form.handle}
                  onChange={(e) => set("handle", e.target.value)}
                  className="flex-1 bg-slate-800 border border-slate-700 rounded-r-lg px-3 py-2.5 text-sm focus:outline-none focus:border-sky-500"
                  placeholder="janesmith"
                />
              </div>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-xs text-slate-400 mb-1 block">Platform</label>
              <select
                value={form.platform}
                onChange={(e) => set("platform", e.target.value)}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:border-sky-500"
              >
                <option value="instagram">Instagram</option>
                <option value="tiktok">TikTok</option>
                <option value="twitter">Twitter / X</option>
                <option value="linkedin">LinkedIn</option>
              </select>
            </div>
            <div>
              <label className="text-xs text-slate-400 mb-1 block">Followers</label>
              <input
                type="number"
                value={form.followers}
                onChange={(e) => set("followers", e.target.value)}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:border-sky-500"
                placeholder="0"
              />
            </div>
          </div>
          <div>
            <label className="text-xs text-slate-400 mb-1 block">Profile URL</label>
            <input
              value={form.profile_url}
              onChange={(e) => set("profile_url", e.target.value)}
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:border-sky-500"
              placeholder="https://instagram.com/janesmith"
            />
          </div>
          <div>
            <label className="text-xs text-slate-400 mb-1 block">Bio</label>
            <textarea
              value={form.bio}
              onChange={(e) => set("bio", e.target.value)}
              rows={3}
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:border-sky-500 resize-none"
              placeholder="Paste their full bio for best AI results…"
            />
          </div>
          <div>
            <label className="text-xs text-slate-400 mb-1 block">Recent posts / content notes</label>
            <textarea
              value={form.posts_summary}
              onChange={(e) => set("posts_summary", e.target.value)}
              rows={2}
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:border-sky-500 resize-none"
              placeholder="What do they post about? Any relevant captions…"
            />
          </div>
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={autoQualify}
              onChange={(e) => setAutoQualify(e.target.checked)}
              className="accent-sky-500 w-4 h-4"
            />
            <span className="text-sm text-slate-300">Auto-qualify with AI after adding</span>
          </label>
          {create.isError && (
            <p className="text-red-400 text-xs">
              {(create.error as any)?.response?.data?.detail || "Failed to add lead."}
            </p>
          )}
        </div>
        <div className="p-5 border-t border-slate-800">
          <button
            onClick={() => create.mutate()}
            disabled={create.isPending || !form.handle}
            className="w-full py-2.5 bg-sky-500 hover:bg-sky-400 disabled:opacity-40 rounded-xl text-sm font-semibold transition-colors"
          >
            {create.isPending
              ? autoQualify ? "Adding & qualifying…" : "Adding…"
              : "Add lead"}
          </button>
        </div>
      </div>
    </div>
  );
}

/* ─── Main dashboard ─────────────────────────────────────────────── */
type Tab = "pipeline" | "prospects" | "followups";

export default function Dashboard() {
  const nav = useNavigate();
  const [tab, setTab] = useState<Tab>("pipeline");
  const [showAdd, setShowAdd] = useState(false);
  const [search, setSearch] = useState("");

  const { data: coach } = useQuery({
    queryKey: ["me"],
    queryFn: () => authApi.me().then((r) => r.data),
  });
  const { data: leads = [], isLoading } = useQuery({
    queryKey: ["leads"],
    queryFn: () => leadsApi.list().then((r) => r.data),
    refetchInterval: 15_000,
  });
  const { data: dueFollowups = [] } = useQuery({
    queryKey: ["followups-due"],
    queryFn: () => followupsApi.due().then((r) => r.data),
    refetchInterval: 60_000,
  });

  function logout() {
    localStorage.removeItem("ll_token");
    localStorage.removeItem("ll_name");
    nav("/", { replace: true });
  }

  const filtered: Lead[] = search
    ? leads.filter(
        (l) =>
          l.name?.toLowerCase().includes(search.toLowerCase()) ||
          l.handle?.toLowerCase().includes(search.toLowerCase()) ||
          l.bio?.toLowerCase().includes(search.toLowerCase())
      )
    : leads;

  const stats = {
    total: leads.length,
    contacted: leads.filter((l) => l.stage === "contacted").length,
    replied: leads.filter((l) => l.stage === "replied").length,
    booked: leads.filter((l) => l.stage === "booked").length,
  };

  const TABS: { id: Tab; label: string; badge?: number }[] = [
    { id: "pipeline", label: "Pipeline" },
    { id: "prospects", label: "Prospects" },
    { id: "followups", label: "Follow-ups", badge: dueFollowups.length || undefined },
  ];

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col">
      {/* ── Nav ── */}
      <nav className="flex items-center justify-between px-5 py-3 border-b border-slate-800 bg-slate-950/90 backdrop-blur sticky top-0 z-40">
        <div className="flex items-center gap-4">
          <span className="text-sky-400 font-extrabold text-lg tracking-tight">
            Lean<span className="text-white">Lead</span>
          </span>
          {/* Tab nav */}
          <div className="hidden sm:flex items-center gap-1 bg-slate-900 border border-slate-800 rounded-xl p-1">
            {TABS.map((t) => (
              <button
                key={t.id}
                onClick={() => setTab(t.id)}
                className={`relative px-4 py-1.5 rounded-lg text-sm font-medium transition-all ${
                  tab === t.id
                    ? "bg-slate-800 text-white"
                    : "text-slate-500 hover:text-slate-300"
                }`}
              >
                {t.label}
                {t.badge ? (
                  <span className="absolute -top-1 -right-1 w-4 h-4 bg-amber-500 text-slate-900 text-[9px] font-bold rounded-full flex items-center justify-center">
                    {t.badge}
                  </span>
                ) : null}
              </button>
            ))}
          </div>
        </div>

        <div className="flex items-center gap-3">
          {tab === "pipeline" && (
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search leads…"
              className="hidden sm:block bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:border-sky-500 w-40"
            />
          )}
          <button
            onClick={() => setShowAdd(true)}
            className="px-3 py-1.5 bg-sky-500 hover:bg-sky-400 rounded-lg text-sm font-medium transition-colors"
          >
            + Add lead
          </button>
          {/* Account menu */}
          <div className="relative group">
            <button className="flex items-center gap-1.5 text-sm text-slate-400 hover:text-white transition-colors">
              <div className="w-7 h-7 rounded-full bg-sky-900 flex items-center justify-center text-xs font-bold text-sky-300">
                {(coach?.name || "?")[0].toUpperCase()}
              </div>
            </button>
            <div className="absolute right-0 mt-2 bg-slate-800 border border-slate-700 rounded-xl overflow-hidden shadow-xl opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all w-44">
              <div className="px-4 py-2.5 border-b border-slate-700">
                <p className="text-xs font-medium text-white truncate">{coach?.name}</p>
                <p className="text-[10px] text-slate-500 truncate">{coach?.email}</p>
              </div>
              <button
                onClick={() => nav("/onboarding")}
                className="block w-full text-left px-4 py-2.5 text-xs text-slate-300 hover:bg-slate-700 transition-colors"
              >
                Settings
              </button>
              <button
                onClick={logout}
                className="block w-full text-left px-4 py-2.5 text-xs text-red-400 hover:bg-slate-700 transition-colors"
              >
                Log out
              </button>
            </div>
          </div>
        </div>
      </nav>

      {/* ── Stats bar (pipeline tab only) ── */}
      {tab === "pipeline" && (
        <div className="flex gap-6 px-6 py-3.5 border-b border-slate-900 bg-slate-950/60">
          {[
            { label: "Total", value: stats.total, color: "text-white" },
            { label: "Contacted", value: stats.contacted, color: "text-sky-400" },
            { label: "Replied", value: stats.replied, color: "text-violet-400" },
            { label: "Booked", value: stats.booked, color: "text-emerald-400" },
            {
              label: "Conversion",
              value: stats.total ? `${Math.round((stats.booked / stats.total) * 100)}%` : "—",
              color: "text-amber-400",
            },
          ].map((s) => (
            <div key={s.label}>
              <p className="text-[10px] text-slate-600 uppercase tracking-wider">{s.label}</p>
              <p className={`text-lg font-bold ${s.color}`}>{s.value}</p>
            </div>
          ))}
        </div>
      )}

      {/* ── Tab content ── */}
      <div className="flex-1 min-h-0">
        {tab === "pipeline" && (
          <div className="h-full px-5 py-4 overflow-auto">
            {isLoading ? (
              <div className="flex items-center justify-center h-64 text-slate-600 text-sm">
                Loading pipeline…
              </div>
            ) : (
              <KanbanBoard leads={filtered} />
            )}
          </div>
        )}

        {tab === "prospects" && (
          <div className="px-5 py-6 overflow-auto">
            <ProspectingPanel />
          </div>
        )}

        {tab === "followups" && (
          <div className="px-5 py-6 overflow-auto">
            <FollowupQueue />
          </div>
        )}
      </div>

      {/* Mobile tab bar */}
      <div className="sm:hidden flex border-t border-slate-800 bg-slate-950">
        {TABS.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`flex-1 relative py-3 text-xs font-medium transition-colors ${
              tab === t.id ? "text-sky-400" : "text-slate-600"
            }`}
          >
            {t.label}
            {t.badge ? (
              <span className="absolute top-2 right-1/4 w-3.5 h-3.5 bg-amber-500 text-slate-900 text-[8px] font-bold rounded-full flex items-center justify-center">
                {t.badge}
              </span>
            ) : null}
          </button>
        ))}
      </div>

      {showAdd && <AddLeadModal onClose={() => setShowAdd(false)} />}
    </div>
  );
}
