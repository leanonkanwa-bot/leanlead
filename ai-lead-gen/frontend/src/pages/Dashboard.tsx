import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { authApi, leadsApi, pipelineApi, type Lead } from "../lib/api";
import KanbanBoard from "../components/KanbanBoard";

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

  function set(key: string, value: string) {
    setForm((f) => ({ ...f, [key]: value }));
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm" onClick={onClose}>
      <div
        className="w-full max-w-lg bg-slate-900 border border-slate-700 rounded-2xl overflow-hidden shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between p-5 border-b border-slate-800">
          <h2 className="font-semibold">Add a lead</h2>
          <button onClick={onClose} className="text-slate-500 hover:text-white text-xl">×</button>
        </div>
        <div className="p-5 space-y-4 overflow-y-auto max-h-[70vh]">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-xs text-slate-400 mb-1 block">Full name</label>
              <input
                value={form.name}
                onChange={(e) => set("name", e.target.value)}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-sky-500"
                placeholder="Jane Smith"
              />
            </div>
            <div>
              <label className="text-xs text-slate-400 mb-1 block">Handle</label>
              <div className="flex">
                <span className="bg-slate-700 border border-slate-600 border-r-0 px-2 rounded-l-lg text-slate-400 text-sm flex items-center">@</span>
                <input
                  value={form.handle}
                  onChange={(e) => set("handle", e.target.value)}
                  className="flex-1 bg-slate-800 border border-slate-700 rounded-r-lg px-3 py-2 text-sm focus:outline-none focus:border-sky-500"
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
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-sky-500"
              >
                <option value="instagram">Instagram</option>
                <option value="twitter">Twitter / X</option>
                <option value="linkedin">LinkedIn</option>
                <option value="tiktok">TikTok</option>
              </select>
            </div>
            <div>
              <label className="text-xs text-slate-400 mb-1 block">Followers</label>
              <input
                type="number"
                value={form.followers}
                onChange={(e) => set("followers", e.target.value)}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-sky-500"
                placeholder="0"
              />
            </div>
          </div>
          <div>
            <label className="text-xs text-slate-400 mb-1 block">Profile URL</label>
            <input
              value={form.profile_url}
              onChange={(e) => set("profile_url", e.target.value)}
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-sky-500"
              placeholder="https://instagram.com/janesmith"
            />
          </div>
          <div>
            <label className="text-xs text-slate-400 mb-1 block">Bio</label>
            <textarea
              value={form.bio}
              onChange={(e) => set("bio", e.target.value)}
              rows={3}
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-sky-500 resize-none"
              placeholder="Paste their full bio here for best AI results..."
            />
          </div>
          <div>
            <label className="text-xs text-slate-400 mb-1 block">Recent posts / content notes (optional)</label>
            <textarea
              value={form.posts_summary}
              onChange={(e) => set("posts_summary", e.target.value)}
              rows={2}
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-sky-500 resize-none"
              placeholder="What do they post about? Any relevant captions..."
            />
          </div>
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={autoQualify}
              onChange={(e) => setAutoQualify(e.target.checked)}
              className="accent-sky-500"
            />
            <span className="text-sm text-slate-300">Auto-qualify with AI after adding</span>
          </label>
          {create.isError && (
            <p className="text-red-400 text-xs">{(create.error as any)?.response?.data?.detail || "Failed to add lead."}</p>
          )}
        </div>
        <div className="p-5 border-t border-slate-800">
          <button
            onClick={() => create.mutate()}
            disabled={create.isPending || !form.handle}
            className="w-full py-2.5 bg-sky-500 hover:bg-sky-400 disabled:opacity-40 rounded-lg text-sm font-medium transition-colors"
          >
            {create.isPending ? (autoQualify ? "Adding & qualifying…" : "Adding…") : "Add lead"}
          </button>
        </div>
      </div>
    </div>
  );
}

export default function Dashboard() {
  const nav = useNavigate();
  const [showAdd, setShowAdd] = useState(false);
  const [search, setSearch] = useState("");

  const { data: coach } = useQuery({ queryKey: ["me"], queryFn: () => authApi.me().then((r) => r.data) });
  const { data: leads = [], isLoading } = useQuery({
    queryKey: ["leads"],
    queryFn: () => leadsApi.list().then((r) => r.data),
    refetchInterval: 10_000,
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
    qualified: leads.filter((l) => l.qualification_score >= 7).length,
    booked: leads.filter((l) => l.stage === "booked").length,
  };

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col">
      {/* Navbar */}
      <nav className="flex items-center justify-between px-6 py-3 border-b border-slate-800 bg-slate-950/80 backdrop-blur sticky top-0 z-40">
        <span className="text-sky-400 font-bold text-lg">LeanLead</span>
        <div className="flex items-center gap-4">
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search leads…"
            className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:border-sky-500 w-48"
          />
          <button
            onClick={() => setShowAdd(true)}
            className="px-4 py-1.5 bg-sky-500 hover:bg-sky-400 rounded-lg text-sm font-medium transition-colors"
          >
            + Add lead
          </button>
          <div className="relative group">
            <button className="text-sm text-slate-400 hover:text-white transition-colors">
              {coach?.name ?? "Account"} ▾
            </button>
            <div className="absolute right-0 mt-1 bg-slate-800 border border-slate-700 rounded-xl overflow-hidden shadow-xl invisible group-hover:visible w-40">
              <button
                onClick={() => nav("/onboarding")}
                className="block w-full text-left px-4 py-2.5 text-xs text-slate-300 hover:bg-slate-700"
              >
                Settings
              </button>
              <button
                onClick={logout}
                className="block w-full text-left px-4 py-2.5 text-xs text-red-400 hover:bg-slate-700"
              >
                Log out
              </button>
            </div>
          </div>
        </div>
      </nav>

      {/* Stats bar */}
      <div className="flex gap-6 px-6 py-4 border-b border-slate-900">
        {[
          { label: "Total leads", value: stats.total },
          { label: "High-score (7+)", value: stats.qualified },
          { label: "Booked calls", value: stats.booked },
          { label: "Conversion", value: stats.total ? `${Math.round((stats.booked / stats.total) * 100)}%` : "—" },
        ].map((s) => (
          <div key={s.label}>
            <p className="text-xs text-slate-500">{s.label}</p>
            <p className="text-xl font-bold text-white">{s.value}</p>
          </div>
        ))}
      </div>

      {/* Board */}
      <div className="flex-1 px-6 py-5 overflow-hidden">
        {isLoading ? (
          <div className="flex items-center justify-center h-64 text-slate-500 text-sm">
            Loading leads…
          </div>
        ) : (
          <KanbanBoard leads={filtered} />
        )}
      </div>

      {showAdd && <AddLeadModal onClose={() => setShowAdd(false)} />}
    </div>
  );
}
