import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { authApi, leadsApi, pipelineApi, followupsApi, icpApi, analyticsApi, type Lead, type ICPData } from "../lib/api";
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

/* ─── ICP Panel ─────────────────────────────────────────────────── */
function ICPPanel() {
  const qc = useQueryClient();
  const [answers, setAnswers] = useState<string[]>([]);
  const [showForm, setShowForm] = useState(false);

  const { data: questions } = useQuery({
    queryKey: ["icp-questions"],
    queryFn: () => icpApi.getQuestions().then((r) => r.data.questions),
  });
  const { data: icp, isLoading: icpLoading } = useQuery({
    queryKey: ["icp"],
    queryFn: () => icpApi.get().then((r) => r.data),
  });

  const generate = useMutation({
    mutationFn: () => {
      const answersDict: Record<string, string> = {};
      answers.forEach((a, i) => { answersDict[`q${i + 1}`] = a; });
      return icpApi.generate({ answers: answersDict });
    },
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["icp"] }); setShowForm(false); },
  });
  const learn = useMutation({
    mutationFn: () => icpApi.learn(),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["icp"] }),
  });

  const icpData = icp?.icp as ICPData | undefined;

  return (
    <div className="space-y-6 max-w-2xl">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-white">Ideal Client Profile</h2>
          {icp && <p className="text-xs text-slate-500 mt-0.5">Version {icp.version} · Generated {new Date(icp.generated_at).toLocaleDateString()}</p>}
        </div>
        <div className="flex gap-2">
          {icp && (
            <button
              onClick={() => learn.mutate()}
              disabled={learn.isPending}
              className="px-3 py-1.5 bg-emerald-900 hover:bg-emerald-800 text-emerald-300 rounded-lg text-xs font-medium transition-colors"
            >
              {learn.isPending ? "Learning…" : "🧠 Learn from conversions"}
            </button>
          )}
          <button
            onClick={() => setShowForm(!showForm)}
            className="px-3 py-1.5 bg-sky-700 hover:bg-sky-600 text-white rounded-lg text-xs font-medium transition-colors"
          >
            {showForm ? "Cancel" : icp ? "Regenerate ICP" : "Generate ICP"}
          </button>
        </div>
      </div>

      {showForm && questions && (
        <div className="bg-slate-900 border border-slate-700 rounded-xl p-5 space-y-4">
          <p className="text-sm text-slate-300 font-medium">Answer these questions to build your ICP:</p>
          {questions.map((q, i) => (
            <div key={i}>
              <label className="text-xs text-slate-400 mb-1 block">{q}</label>
              <textarea
                value={answers[i] || ""}
                onChange={(e) => {
                  const newAnswers = [...answers];
                  newAnswers[i] = e.target.value;
                  setAnswers(newAnswers);
                }}
                rows={2}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm resize-none focus:outline-none focus:border-sky-500"
              />
            </div>
          ))}
          <button
            onClick={() => generate.mutate()}
            disabled={generate.isPending}
            className="w-full py-2.5 bg-sky-500 hover:bg-sky-400 disabled:opacity-40 rounded-lg text-sm font-medium transition-colors"
          >
            {generate.isPending ? "Generating ICP…" : "Generate ICP with Claude"}
          </button>
        </div>
      )}

      {icpLoading && <p className="text-slate-500 text-sm">Loading…</p>}

      {icpData && (
        <div className="space-y-4">
          {icpData.summary && (
            <div className="bg-slate-900 border border-slate-700 rounded-xl p-4">
              <p className="text-xs text-slate-500 mb-1">Summary</p>
              <p className="text-sm text-slate-200">{icpData.summary}</p>
            </div>
          )}
          <div className="grid grid-cols-2 gap-4">
            {icpData.pain_points && icpData.pain_points.length > 0 && (
              <div className="bg-slate-900 border border-slate-700 rounded-xl p-4">
                <p className="text-xs font-medium text-orange-400 mb-2">Top Pain Points</p>
                <ul className="space-y-1">
                  {icpData.pain_points.slice(0, 5).map((p, i) => (
                    <li key={i} className="text-xs text-slate-300">• {p}</li>
                  ))}
                </ul>
              </div>
            )}
            {icpData.best_dm_angles && icpData.best_dm_angles.length > 0 && (
              <div className="bg-slate-900 border border-slate-700 rounded-xl p-4">
                <p className="text-xs font-medium text-sky-400 mb-2">Best DM Angles</p>
                <ul className="space-y-1">
                  {icpData.best_dm_angles.slice(0, 5).map((a, i) => (
                    <li key={i} className="text-xs text-slate-300">• {a}</li>
                  ))}
                </ul>
              </div>
            )}
            {icpData.buying_triggers && icpData.buying_triggers.length > 0 && (
              <div className="bg-slate-900 border border-slate-700 rounded-xl p-4">
                <p className="text-xs font-medium text-emerald-400 mb-2">Buying Triggers</p>
                <ul className="space-y-1">
                  {icpData.buying_triggers.slice(0, 4).map((t, i) => (
                    <li key={i} className="text-xs text-slate-300">• {t}</li>
                  ))}
                </ul>
              </div>
            )}
            {icpData.objections && icpData.objections.length > 0 && (
              <div className="bg-slate-900 border border-slate-700 rounded-xl p-4">
                <p className="text-xs font-medium text-amber-400 mb-2">Common Objections</p>
                <ul className="space-y-1">
                  {icpData.objections.slice(0, 4).map((o, i) => (
                    <li key={i} className="text-xs text-slate-300">• {o}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
          {icpData.platforms_ranked && icpData.platforms_ranked.length > 0 && (
            <div className="bg-slate-900 border border-slate-700 rounded-xl p-4">
              <p className="text-xs font-medium text-violet-400 mb-2">Platforms (ranked)</p>
              <div className="flex gap-2">
                {icpData.platforms_ranked.map((p, i) => (
                  <span key={i} className="text-xs bg-violet-950 text-violet-300 px-2 py-0.5 rounded-full">
                    {i + 1}. {p}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {!icpData && !icpLoading && !showForm && (
        <div className="bg-slate-900 border border-slate-700 border-dashed rounded-xl p-8 text-center">
          <p className="text-slate-400 mb-2">No ICP generated yet.</p>
          <p className="text-slate-500 text-sm">Click "Generate ICP" to build your Ideal Client Profile with Claude.</p>
        </div>
      )}
    </div>
  );
}

/* ─── Analytics Panel ───────────────────────────────────────────── */
function AnalyticsPanel() {
  const { data: roi } = useQuery({ queryKey: ["analytics-roi"], queryFn: () => analyticsApi.getRoi().then((r) => r.data) });
  const { data: velocity } = useQuery({ queryKey: ["analytics-velocity"], queryFn: () => analyticsApi.getVelocity().then((r) => r.data) });
  const { data: attribution } = useQuery({ queryKey: ["analytics-attribution"], queryFn: () => analyticsApi.getAttribution().then((r) => r.data) });
  const { data: competitive } = useQuery({ queryKey: ["analytics-competitive"], queryFn: () => analyticsApi.getCompetitive().then((r) => r.data) });
  const scanComp = useMutation({ mutationFn: () => analyticsApi.scanCompetitors() });

  return (
    <div className="space-y-6 max-w-4xl">
      {/* ROI Widget */}
      {roi && (
        <div>
          <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-3">ROI vs Agency</h3>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="bg-slate-900 border border-slate-700 rounded-xl p-4">
              <p className="text-xs text-slate-500">Cost / Lead</p>
              <p className="text-xl font-bold text-emerald-400">€0</p>
              <p className="text-xs text-slate-600 mt-0.5">Agency: €{roi.cost_per_lead_agency_high / Math.max(roi.total_leads, 1)}</p>
            </div>
            <div className="bg-slate-900 border border-slate-700 rounded-xl p-4">
              <p className="text-xs text-slate-500">Saved</p>
              <p className="text-xl font-bold text-emerald-400">€{roi.savings_vs_agency.toLocaleString()}</p>
              <p className="text-xs text-slate-600 mt-0.5">vs agency model</p>
            </div>
            <div className="bg-slate-900 border border-slate-700 rounded-xl p-4">
              <p className="text-xs text-slate-500">LTV Prediction</p>
              <p className="text-xl font-bold text-sky-400">€{roi.predicted_ltv_pipeline.toLocaleString()}</p>
            </div>
            <div className="bg-slate-900 border border-slate-700 rounded-xl p-4">
              <p className="text-xs text-slate-500">Pipeline Growth</p>
              <p className="text-xl font-bold text-amber-400">{roi.pipeline_growth_rate > 0 ? "+" : ""}{roi.pipeline_growth_rate}%</p>
            </div>
          </div>
        </div>
      )}

      {/* Velocity / Stuck Leads */}
      {velocity && (
        <div>
          <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-3">Pipeline Velocity</h3>
          {velocity.stuck_leads && velocity.stuck_leads.length > 0 && (
            <div className="bg-amber-950/30 border border-amber-900 rounded-xl p-4 mb-4">
              <p className="text-xs font-medium text-amber-400 mb-2">⚠ {velocity.stuck_leads.length} stuck lead{velocity.stuck_leads.length !== 1 ? "s" : ""}</p>
              <div className="space-y-1">
                {velocity.stuck_leads.slice(0, 5).map((l) => (
                  <div key={l.lead_id} className="flex items-center justify-between text-xs">
                    <span className="text-slate-300">@{l.handle}</span>
                    <span className="text-slate-500">{l.stage} · {l.days_in_stage}d</span>
                  </div>
                ))}
              </div>
            </div>
          )}
          {velocity.focus_today && velocity.focus_today.length > 0 && (
            <div className="bg-sky-950/30 border border-sky-900 rounded-xl p-4">
              <p className="text-xs font-medium text-sky-400 mb-2">Focus today ({velocity.focus_today.length})</p>
              <div className="space-y-1">
                {velocity.focus_today.map((l) => (
                  <div key={l.lead_id} className="flex items-center justify-between text-xs">
                    <span className="text-slate-300">@{l.handle}</span>
                    <span className="text-sky-500">{l.action}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Attribution */}
      {attribution && (
        <div>
          <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-3">Multi-Touch Attribution</h3>
          <div className="grid grid-cols-2 gap-4">
            {attribution.top_converting_angles && attribution.top_converting_angles.length > 0 && (
              <div className="bg-slate-900 border border-slate-700 rounded-xl p-4">
                <p className="text-xs font-medium text-sky-400 mb-2">Top Converting Angles</p>
                {attribution.top_converting_angles.slice(0, 5).map((a, i) => (
                  <div key={i} className="flex justify-between text-xs py-0.5">
                    <span className="text-slate-300 truncate">{a.angle}</span>
                    <span className="text-sky-400 ml-2">{a.conversions}</span>
                  </div>
                ))}
              </div>
            )}
            {attribution.top_converting_pains && attribution.top_converting_pains.length > 0 && (
              <div className="bg-slate-900 border border-slate-700 rounded-xl p-4">
                <p className="text-xs font-medium text-orange-400 mb-2">Top Converting Pains</p>
                {attribution.top_converting_pains.slice(0, 5).map((p, i) => (
                  <div key={i} className="flex justify-between text-xs py-0.5">
                    <span className="text-slate-300 truncate">{p.pain}</span>
                    <span className="text-orange-400 ml-2">{p.conversions}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Competitive Intel */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider">Competitive Intelligence</h3>
          <button
            onClick={() => scanComp.mutate()}
            disabled={scanComp.isPending}
            className="px-3 py-1.5 bg-slate-700 hover:bg-slate-600 text-slate-300 rounded-lg text-xs font-medium transition-colors"
          >
            {scanComp.isPending ? "Scanning…" : "🔍 Scan Competitors"}
          </button>
        </div>
        {(competitive as any)?.report?.alert && (
          <div className="bg-red-950/30 border border-red-900 rounded-xl p-4 mb-4">
            <p className="text-xs font-medium text-red-400">Alert</p>
            <p className="text-sm text-slate-300 mt-1">{(competitive as any).report.alert}</p>
          </div>
        )}
        {(competitive as any)?.report?.market_gaps?.length > 0 && (
          <div className="bg-slate-900 border border-slate-700 rounded-xl p-4 mb-3">
            <p className="text-xs font-medium text-emerald-400 mb-2">Market Gaps You Can Own</p>
            <ul className="space-y-1">
              {(competitive as any).report.market_gaps.map((g: string, i: number) => (
                <li key={i} className="text-xs text-slate-300">• {g}</li>
              ))}
            </ul>
          </div>
        )}
        {(competitive as any)?.report?.opportunities?.length > 0 && (
          <div className="bg-slate-900 border border-slate-700 rounded-xl p-4">
            <p className="text-xs font-medium text-sky-400 mb-2">Opportunities</p>
            <ul className="space-y-1">
              {(competitive as any).report.opportunities.map((o: string, i: number) => (
                <li key={i} className="text-xs text-slate-300">• {o}</li>
              ))}
            </ul>
          </div>
        )}
        {!(competitive as any)?.report && (
          <p className="text-sm text-slate-500 text-center py-6">No competitive data yet. Click "Scan Competitors" to start.</p>
        )}
      </div>
    </div>
  );
}

/* ─── Main dashboard ─────────────────────────────────────────────── */
type Tab = "pipeline" | "prospects" | "followups" | "analytics" | "icp";

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
    { id: "analytics", label: "Analytics" },
    { id: "icp", label: "ICP" },
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

        {tab === "analytics" && (
          <div className="px-5 py-6 overflow-auto">
            <AnalyticsPanel />
          </div>
        )}

        {tab === "icp" && (
          <div className="px-5 py-6 overflow-auto">
            <ICPPanel />
          </div>
        )}
      </div>

      {/* Mobile tab bar */}
      <div className="sm:hidden flex border-t border-slate-800 bg-slate-950 overflow-x-auto">
        {TABS.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`flex-shrink-0 flex-1 relative py-3 text-[10px] font-medium transition-colors ${
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
