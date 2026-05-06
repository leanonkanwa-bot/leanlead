import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { followupsApi, type FollowupDue } from "../lib/api";

function dayLabel(day: number) {
  return day === 2 ? "D+2 First touch" : day === 4 ? "D+4 Value-add" : "D+7 Final close";
}

function dayColor(day: number) {
  return day === 2
    ? "bg-amber-950 border-amber-900 text-amber-400"
    : day === 4
    ? "bg-sky-950 border-sky-900 text-sky-400"
    : "bg-rose-950 border-rose-900 text-rose-400";
}

function daysSince(iso: string) {
  const diff = Math.floor((Date.now() - new Date(iso).getTime()) / 86_400_000);
  return diff === 1 ? "1 day ago" : `${diff} days ago`;
}

function messageKey(day: number): keyof FollowupDue {
  return day === 2 ? "followup_d2_message" : day === 4 ? "followup_d4_message" : "followup_d7_message";
}

function FollowupRow({ item }: { item: FollowupDue }) {
  const qc = useQueryClient();
  const [copied, setCopied] = useState(false);
  const [expanded, setExpanded] = useState(false);

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["followups-due"] });
    qc.invalidateQueries({ queryKey: ["leads"] });
  };

  const generate = useMutation({
    mutationFn: () => followupsApi.generate(item.lead_id, item.due_day),
    onSuccess: invalidate,
  });

  const markSent = useMutation({
    mutationFn: () => followupsApi.markSent(item.lead_id, item.due_day),
    onSuccess: invalidate,
  });

  const message = item[messageKey(item.due_day)] as string | undefined;

  function copy() {
    if (!message) return;
    navigator.clipboard.writeText(message);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden">
      {/* Header */}
      <div
        className="flex items-center justify-between px-5 py-4 cursor-pointer hover:bg-slate-800/40 transition-colors"
        onClick={() => setExpanded((e) => !e)}
      >
        <div className="flex items-center gap-3 min-w-0">
          <span className={`text-[10px] font-bold px-2 py-1 rounded-lg border ${dayColor(item.due_day)}`}>
            {dayLabel(item.due_day)}
          </span>
          <div className="min-w-0">
            <p className="text-sm font-medium text-white truncate">{item.name || `@${item.handle}`}</p>
            <p className="text-xs text-slate-500">@{item.handle} · messaged {daysSince(item.messaged_at)}</p>
          </div>
        </div>
        <span className="text-slate-600 text-sm ml-3">{expanded ? "▲" : "▼"}</span>
      </div>

      {expanded && (
        <div className="px-5 pb-5 space-y-4 border-t border-slate-800">
          {/* Original DM */}
          {item.outreach_message && (
            <div className="mt-4">
              <p className="text-xs text-slate-500 mb-1">Original DM sent</p>
              <p className="text-xs text-slate-400 bg-slate-800/60 rounded-lg p-3 leading-relaxed line-clamp-3">
                {item.outreach_message}
              </p>
            </div>
          )}

          {/* Generated follow-up */}
          {message ? (
            <div>
              <p className="text-xs text-slate-500 mb-1">Follow-up message</p>
              <div className="bg-slate-800 rounded-xl p-4 text-sm text-slate-200 whitespace-pre-wrap leading-relaxed">
                {message}
              </div>
              <div className="flex gap-3 mt-3 flex-wrap">
                <button
                  onClick={copy}
                  className="text-xs text-sky-400 hover:text-sky-300 transition-colors"
                >
                  {copied ? "Copied!" : "📋 Copy"}
                </button>
                <button
                  onClick={() => generate.mutate()}
                  disabled={generate.isPending}
                  className="text-xs text-slate-500 hover:text-slate-300 transition-colors"
                >
                  {generate.isPending ? "Regenerating…" : "↻ Regenerate"}
                </button>
              </div>
            </div>
          ) : (
            <button
              onClick={() => generate.mutate()}
              disabled={generate.isPending}
              className="w-full py-2.5 bg-slate-800 hover:bg-slate-700 disabled:opacity-50 rounded-xl text-sm text-slate-300 transition-colors"
            >
              {generate.isPending ? "Writing follow-up…" : `✍️ Generate ${dayLabel(item.due_day)} message`}
            </button>
          )}

          {/* Actions */}
          <div className="flex gap-3">
            <button
              onClick={() => markSent.mutate()}
              disabled={markSent.isPending || !message}
              className="flex-1 py-2.5 bg-emerald-900 hover:bg-emerald-800 disabled:opacity-40 text-emerald-300 rounded-xl text-sm font-medium transition-colors"
            >
              {markSent.isPending ? "Marking…" : "✓ Mark as sent"}
            </button>
            <button
              onClick={() => followupsApi.markSent(item.lead_id, item.due_day)}
              className="px-4 py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-500 rounded-xl text-sm transition-colors"
              title="Skip this follow-up"
            >
              Skip
            </button>
          </div>

          {generate.isError && (
            <p className="text-red-400 text-xs">{(generate.error as any)?.response?.data?.detail}</p>
          )}
        </div>
      )}
    </div>
  );
}

export default function FollowupQueue() {
  const { data: items = [], isLoading, refetch } = useQuery({
    queryKey: ["followups-due"],
    queryFn: () => followupsApi.due().then((r) => r.data),
    refetchInterval: 60_000,
  });

  const byDay = (day: number) => items.filter((i) => i.due_day === day);

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="font-semibold text-white">Follow-up queue</h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Leads that need a D+2, D+4, or D+7 touch today
          </p>
        </div>
        <button
          onClick={() => refetch()}
          className="text-xs text-slate-500 hover:text-slate-300 transition-colors"
        >
          ↻ Refresh
        </button>
      </div>

      {isLoading ? (
        <p className="text-sm text-slate-600 text-center py-12">Loading…</p>
      ) : items.length === 0 ? (
        <div className="text-center py-16 bg-slate-900 border border-slate-800 rounded-2xl">
          <p className="text-2xl mb-3">🎉</p>
          <p className="text-sm font-medium text-white mb-1">Queue is clear</p>
          <p className="text-xs text-slate-500">No follow-ups due right now. Check back tomorrow.</p>
        </div>
      ) : (
        <>
          {/* Stats */}
          <div className="grid grid-cols-3 gap-3">
            {[
              { day: 2, label: "D+2 due", color: "text-amber-400" },
              { day: 4, label: "D+4 due", color: "text-sky-400" },
              { day: 7, label: "D+7 due", color: "text-rose-400" },
            ].map(({ day, label, color }) => (
              <div key={day} className="bg-slate-900 border border-slate-800 rounded-xl px-4 py-3 text-center">
                <p className={`text-xl font-bold ${color}`}>{byDay(day).length}</p>
                <p className="text-[10px] text-slate-500 mt-0.5">{label}</p>
              </div>
            ))}
          </div>

          {/* List grouped by day priority */}
          <div className="space-y-3">
            {items
              .slice()
              .sort((a, b) => b.due_day - a.due_day) // D+7 first (most urgent)
              .map((item) => (
                <FollowupRow key={`${item.lead_id}-${item.due_day}`} item={item} />
              ))}
          </div>
        </>
      )}
    </div>
  );
}
