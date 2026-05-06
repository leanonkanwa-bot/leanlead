import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import type { Lead } from "../lib/api";
import { leadsApi, pipelineApi } from "../lib/api";

interface Props {
  lead: Lead;
  onClose: () => void;
}

export default function LeadModal({ lead, onClose }: Props) {
  const qc = useQueryClient();
  const [tab, setTab] = useState<"info" | "outreach" | "reply">("info");
  const [replyText, setReplyText] = useState(lead.reply_received || "");
  const [convHistory, setConvHistory] = useState("");
  const [notes, setNotes] = useState(lead.notes || "");
  const [copied, setCopied] = useState(false);

  const invalidate = () => qc.invalidateQueries({ queryKey: ["leads"] });

  const qualify = useMutation({ mutationFn: () => pipelineApi.qualify(lead.id), onSuccess: invalidate });
  const write = useMutation({ mutationFn: () => pipelineApi.write(lead.id), onSuccess: invalidate });
  const reply = useMutation({
    mutationFn: () => pipelineApi.reply(lead.id, { lead_reply: replyText, conversation_history: convHistory }),
    onSuccess: invalidate,
  });
  const syncCrm = useMutation({ mutationFn: () => pipelineApi.syncCrm(lead.id), onSuccess: invalidate });
  const saveNotes = useMutation({
    mutationFn: () => leadsApi.update(lead.id, { notes }),
    onSuccess: invalidate,
  });
  const deleteLead = useMutation({
    mutationFn: () => leadsApi.delete(lead.id),
    onSuccess: () => { invalidate(); onClose(); },
  });

  function copy(text: string) {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  const loading =
    qualify.isPending || write.isPending || reply.isPending || syncCrm.isPending;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm" onClick={onClose}>
      <div
        className="w-full max-w-xl bg-slate-900 border border-slate-700 rounded-2xl overflow-hidden shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-start justify-between p-5 border-b border-slate-800">
          <div>
            <h2 className="font-semibold text-white">{lead.name}</h2>
            <p className="text-sm text-slate-400">@{lead.handle} · {lead.platform}</p>
          </div>
          <button onClick={onClose} className="text-slate-500 hover:text-white text-xl leading-none">×</button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-slate-800">
          {(["info", "outreach", "reply"] as const).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`flex-1 py-2.5 text-xs font-medium capitalize transition-colors ${
                tab === t ? "text-sky-400 border-b-2 border-sky-400" : "text-slate-500 hover:text-slate-300"
              }`}
            >
              {t === "info" ? "Profile" : t === "outreach" ? "DM Draft" : "Reply"}
            </button>
          ))}
        </div>

        <div className="p-5 overflow-y-auto max-h-[60vh] space-y-4">
          {/* Info tab */}
          {tab === "info" && (
            <>
              {lead.bio && (
                <div>
                  <p className="text-xs text-slate-500 mb-1">Bio</p>
                  <p className="text-sm text-slate-300">{lead.bio}</p>
                </div>
              )}
              {lead.qualification_score > 0 && (
                <div className="bg-slate-800 rounded-xl p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-xs text-slate-500">AI Score</span>
                    <span className="text-lg font-bold text-sky-400">{lead.qualification_score}/10</span>
                  </div>
                  {lead.qualification_reason && (
                    <p className="text-xs text-slate-400 mb-2">{lead.qualification_reason}</p>
                  )}
                  {lead.pain_points?.length > 0 && (
                    <div className="flex flex-wrap gap-1">
                      {lead.pain_points.map((p) => (
                        <span key={p} className="text-[10px] bg-sky-950 text-sky-400 px-2 py-0.5 rounded-full">{p}</span>
                      ))}
                    </div>
                  )}
                </div>
              )}
              <div>
                <label className="text-xs text-slate-500 mb-1 block">Notes</label>
                <textarea
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  rows={3}
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm resize-none focus:outline-none focus:border-sky-500"
                  placeholder="Add private notes here..."
                />
                <button
                  onClick={() => saveNotes.mutate()}
                  className="text-xs text-sky-400 hover:text-sky-300 mt-1"
                >
                  {saveNotes.isPending ? "Saving…" : "Save notes"}
                </button>
              </div>
              <div className="flex gap-2 flex-wrap">
                <button
                  onClick={() => qualify.mutate()}
                  disabled={loading}
                  className="px-3 py-2 bg-sky-900 hover:bg-sky-800 disabled:opacity-50 text-sky-300 rounded-lg text-xs font-medium transition-colors"
                >
                  {qualify.isPending ? "Qualifying…" : "🎯 Re-qualify"}
                </button>
                <button
                  onClick={() => syncCrm.mutate()}
                  disabled={loading}
                  className="px-3 py-2 bg-slate-700 hover:bg-slate-600 disabled:opacity-50 text-slate-300 rounded-lg text-xs font-medium transition-colors"
                >
                  {syncCrm.isPending ? "Syncing…" : "↗ Sync to Airtable"}
                </button>
                <button
                  onClick={() => { if (confirm("Delete this lead?")) deleteLead.mutate(); }}
                  className="px-3 py-2 bg-red-950 hover:bg-red-900 text-red-400 rounded-lg text-xs font-medium transition-colors ml-auto"
                >
                  Delete
                </button>
              </div>
              {qualify.isError && <p className="text-red-400 text-xs">{(qualify.error as any)?.response?.data?.detail}</p>}
            </>
          )}

          {/* Outreach tab */}
          {tab === "outreach" && (
            <>
              {lead.outreach_message ? (
                <div>
                  <p className="text-xs text-slate-500 mb-2">Generated DM</p>
                  <div className="bg-slate-800 rounded-xl p-4 text-sm text-slate-200 whitespace-pre-wrap leading-relaxed">
                    {lead.outreach_message}
                  </div>
                  <button
                    onClick={() => copy(lead.outreach_message!)}
                    className="text-xs text-sky-400 hover:text-sky-300 mt-2"
                  >
                    {copied ? "Copied!" : "Copy to clipboard"}
                  </button>
                </div>
              ) : (
                <p className="text-sm text-slate-500 text-center py-4">No DM generated yet.</p>
              )}
              <button
                onClick={() => write.mutate()}
                disabled={loading || !lead.qualification_reason}
                className="w-full py-2.5 bg-sky-500 hover:bg-sky-400 disabled:opacity-40 rounded-lg text-sm font-medium transition-colors"
              >
                {write.isPending ? "Writing DM…" : lead.outreach_message ? "Regenerate DM" : "✍️ Generate DM"}
              </button>
              {!lead.qualification_reason && (
                <p className="text-xs text-slate-500 text-center">Qualify this lead first to generate a DM.</p>
              )}
              {write.isError && <p className="text-red-400 text-xs">{(write.error as any)?.response?.data?.detail}</p>}
            </>
          )}

          {/* Reply tab */}
          {tab === "reply" && (
            <>
              <div>
                <label className="text-xs text-slate-500 mb-1 block">Their reply</label>
                <textarea
                  value={replyText}
                  onChange={(e) => setReplyText(e.target.value)}
                  rows={3}
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm resize-none focus:outline-none focus:border-sky-500"
                  placeholder="Paste their message here..."
                />
              </div>
              <div>
                <label className="text-xs text-slate-500 mb-1 block">Conversation history (optional)</label>
                <textarea
                  value={convHistory}
                  onChange={(e) => setConvHistory(e.target.value)}
                  rows={3}
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm resize-none focus:outline-none focus:border-sky-500"
                  placeholder="You: [your DM]&#10;Them: [their first reply]&#10;..."
                />
              </div>
              {lead.suggested_reply && (
                <div>
                  <p className="text-xs text-slate-500 mb-2">Suggested reply</p>
                  <div className="bg-slate-800 rounded-xl p-4 text-sm text-slate-200 whitespace-pre-wrap leading-relaxed">
                    {lead.suggested_reply}
                  </div>
                  <button
                    onClick={() => copy(lead.suggested_reply!)}
                    className="text-xs text-sky-400 hover:text-sky-300 mt-2"
                  >
                    {copied ? "Copied!" : "Copy to clipboard"}
                  </button>
                </div>
              )}
              <button
                onClick={() => reply.mutate()}
                disabled={loading || !replyText}
                className="w-full py-2.5 bg-sky-500 hover:bg-sky-400 disabled:opacity-40 rounded-lg text-sm font-medium transition-colors"
              >
                {reply.isPending ? "Generating reply…" : "🤖 Generate reply"}
              </button>
              {reply.isError && <p className="text-red-400 text-xs">{(reply.error as any)?.response?.data?.detail}</p>}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
