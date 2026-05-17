import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { prospectingApi, type ProspectingJob } from "../lib/api";

function StatusBadge({ status }: { status: ProspectingJob["status"] }) {
  const cfg: Record<string, string> = {
    pending: "bg-amber-900/60 text-amber-400",
    running: "bg-sky-900/60 text-sky-400",
    done: "bg-emerald-900/60 text-emerald-400",
    error: "bg-red-900/60 text-red-400",
  };
  return (
    <span className={`text-[10px] px-2 py-0.5 rounded-full font-semibold uppercase tracking-wide ${cfg[status]}`}>
      {status === "running" ? "⟳ running" : status}
    </span>
  );
}

function timeAgo(iso?: string) {
  if (!iso) return "";
  const d = new Date(iso);
  const s = Math.floor((Date.now() - d.getTime()) / 1000);
  if (s < 60) return `${s}s ago`;
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  return `${Math.floor(s / 3600)}h ago`;
}

export default function ProspectingPanel() {
  const qc = useQueryClient();

  const [platform, setPlatform] = useState("instagram");
  const [hashtagInput, setHashtagInput] = useState("");
  const [hashtags, setHashtags] = useState<string[]>([]);
  const [maxResults, setMaxResults] = useState(20);
  const [autoQualify, setAutoQualify] = useState(true);

  const { data: jobs = [], isLoading: jobsLoading } = useQuery({
    queryKey: ["prospecting-jobs"],
    queryFn: () => prospectingApi.jobs().then((r) => r.data),
    refetchInterval: 5_000,
  });

  const suggest = useMutation({
    mutationFn: () => prospectingApi.suggestHashtags().then((r) => r.data.hashtags),
    onSuccess: (tags) => setHashtags(tags),
  });

  const runJob = useMutation({
    mutationFn: () =>
      prospectingApi.run({ platform, hashtags, max_results: maxResults, auto_qualify: autoQualify }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["prospecting-jobs"] });
      qc.invalidateQueries({ queryKey: ["leads"] });
    },
  });

  function addHashtag() {
    const tag = hashtagInput.replace(/^#/, "").trim().toLowerCase();
    if (tag && !hashtags.includes(tag)) setHashtags((h) => [...h, tag]);
    setHashtagInput("");
  }

  function removeHashtag(tag: string) {
    setHashtags((h) => h.filter((t) => t !== tag));
  }

  const runningJob = jobs.find((j) => j.status === "running" || j.status === "pending");

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {/* Config card */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
        <h2 className="font-semibold text-white mb-1">Find new leads</h2>
        <p className="text-xs text-slate-500 mb-6">
          LeanLead scrapes public profiles on Instagram or TikTok and auto-qualifies them.
        </p>

        {/* Platform */}
        <div className="mb-5">
          <label className="text-xs text-slate-400 mb-2 block">Platform</label>
          <div className="flex gap-3">
            {["instagram", "tiktok"].map((p) => (
              <button
                key={p}
                onClick={() => setPlatform(p)}
                className={`flex-1 py-2.5 rounded-xl border text-sm font-medium transition-all capitalize ${
                  platform === p
                    ? "bg-sky-900/40 border-sky-600 text-sky-300"
                    : "bg-slate-800 border-slate-700 text-slate-400 hover:border-slate-600"
                }`}
              >
                {p === "instagram" ? "📸 Instagram" : "🎵 TikTok"}
              </button>
            ))}
          </div>
        </div>

        {/* Hashtags */}
        <div className="mb-5">
          <div className="flex items-center justify-between mb-2">
            <label className="text-xs text-slate-400">Hashtags to search</label>
            <button
              onClick={() => suggest.mutate()}
              disabled={suggest.isPending}
              className="text-[10px] text-sky-400 hover:text-sky-300 transition-colors"
            >
              {suggest.isPending ? "Generating…" : "✦ AI suggest for my niche"}
            </button>
          </div>
          <div className="flex gap-2 mb-2">
            <div className="flex flex-1 bg-slate-800 border border-slate-700 rounded-lg overflow-hidden focus-within:border-sky-500">
              <span className="pl-3 pr-1 flex items-center text-slate-500 text-sm">#</span>
              <input
                value={hashtagInput}
                onChange={(e) => setHashtagInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && addHashtag()}
                className="flex-1 bg-transparent px-2 py-2.5 text-sm focus:outline-none"
                placeholder="businesscoach"
              />
            </div>
            <button
              onClick={addHashtag}
              className="px-4 py-2.5 bg-slate-700 hover:bg-slate-600 rounded-lg text-sm transition-colors"
            >
              Add
            </button>
          </div>
          {hashtags.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {hashtags.map((tag) => (
                <span
                  key={tag}
                  className="flex items-center gap-1.5 bg-sky-950 border border-sky-900 text-sky-300 text-xs px-2.5 py-1 rounded-full"
                >
                  #{tag}
                  <button onClick={() => removeHashtag(tag)} className="text-sky-500 hover:text-sky-300 leading-none">×</button>
                </span>
              ))}
            </div>
          )}
        </div>

        {/* Options row */}
        <div className="flex items-center gap-6 mb-6">
          <div className="flex-1">
            <label className="text-xs text-slate-400 mb-1 block">Max leads to find</label>
            <select
              value={maxResults}
              onChange={(e) => setMaxResults(Number(e.target.value))}
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:border-sky-500"
            >
              {[10, 20, 50, 100].map((n) => (
                <option key={n} value={n}>{n} profiles</option>
              ))}
            </select>
          </div>
          <label className="flex items-center gap-2 cursor-pointer pt-4">
            <input
              type="checkbox"
              checked={autoQualify}
              onChange={(e) => setAutoQualify(e.target.checked)}
              className="accent-sky-500 w-4 h-4"
            />
            <span className="text-sm text-slate-300">Auto-qualify with AI</span>
          </label>
        </div>

        {runJob.isError && (
          <p className="text-red-400 text-xs mb-4">
            {(runJob.error as any)?.response?.data?.detail || "Failed to start job."}
          </p>
        )}

        <button
          onClick={() => runJob.mutate()}
          disabled={runJob.isPending || !hashtags.length || !!runningJob}
          className="w-full py-3 bg-sky-500 hover:bg-sky-400 disabled:opacity-40 rounded-xl text-sm font-semibold transition-colors"
        >
          {runJob.isPending
            ? "Starting…"
            : runningJob
            ? "Job already running…"
            : `🔍 Find leads on ${platform}`}
        </button>
        {!!runningJob && (
          <p className="text-xs text-amber-400 text-center mt-2">
            A prospecting job is running — results appear in your pipeline when done.
          </p>
        )}
      </div>

      {/* Job history */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
        <h3 className="font-medium text-white mb-4 text-sm">Recent jobs</h3>
        {jobsLoading ? (
          <p className="text-xs text-slate-600">Loading…</p>
        ) : jobs.length === 0 ? (
          <p className="text-xs text-slate-600 text-center py-6">No prospecting jobs yet. Run your first search above.</p>
        ) : (
          <div className="space-y-3">
            {jobs.map((job) => (
              <div key={job.id} className="flex items-start justify-between gap-4 py-3 border-b border-slate-800 last:border-0">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <StatusBadge status={job.status} />
                    <span className="text-xs text-slate-500 capitalize">{job.platform}</span>
                  </div>
                  <div className="flex flex-wrap gap-1">
                    {job.hashtags.slice(0, 4).map((t) => (
                      <span key={t} className="text-[10px] text-slate-500">#{t}</span>
                    ))}
                    {job.hashtags.length > 4 && (
                      <span className="text-[10px] text-slate-600">+{job.hashtags.length - 4} more</span>
                    )}
                  </div>
                  {job.error_message && (
                    <p className="text-[10px] text-red-400 mt-1 truncate max-w-sm">{job.error_message}</p>
                  )}
                </div>
                <div className="text-right flex-shrink-0">
                  <p className="text-sm font-semibold text-white">{job.leads_found} leads</p>
                  <p className="text-[10px] text-slate-600">{timeAgo(job.started_at)}</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
