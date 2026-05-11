import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import type { Lead, SalesScript, NurtureMessage } from "../lib/api";
import { leadsApi, pipelineApi } from "../lib/api";

interface Props {
  lead: Lead;
  onClose: () => void;
}

type Tab = "info" | "outreach" | "reply" | "intel" | "script" | "nurture";

export default function LeadModal({ lead, onClose }: Props) {
  const qc = useQueryClient();
  const [tab, setTab] = useState<Tab>("info");
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
  const saveNotes = useMutation({ mutationFn: () => leadsApi.update(lead.id, { notes }), onSuccess: invalidate });
  const deleteLead = useMutation({
    mutationFn: () => leadsApi.delete(lead.id),
    onSuccess: () => { invalidate(); onClose(); },
  });
  const enrich = useMutation({ mutationFn: () => pipelineApi.enrich(lead.id), onSuccess: invalidate });
  const genScript = useMutation({ mutationFn: () => pipelineApi.salesScript(lead.id), onSuccess: invalidate });
  const genNurture = useMutation({ mutationFn: () => pipelineApi.nurture(lead.id), onSuccess: invalidate });
  const reengage = useMutation({ mutationFn: () => pipelineApi.reengage(lead.id), onSuccess: invalidate });

  function copy(text: string) {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  const loading = qualify.isPending || write.isPending || reply.isPending || syncCrm.isPending;

  const TABS: { id: Tab; label: string }[] = [
    { id: "info", label: "Profile" },
    { id: "outreach", label: "DM Draft" },
    { id: "reply", label: "Reply" },
    { id: "intel", label: "Intel" },
    { id: "script", label: "Script" },
    { id: "nurture", label: "Nurture" },
  ];

  const script: SalesScript | undefined = lead.sales_script as SalesScript | undefined;
  const nurture: NurtureMessage[] | undefined = lead.nurture_sequence as NurtureMessage[] | undefined;

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
          <div className="flex items-center gap-2">
            {lead.price_tier === "premium" && (
              <span className="text-xs bg-amber-950 text-amber-400 border border-amber-800 px-2 py-0.5 rounded-full">💎 Premium</span>
            )}
            {lead.trust_velocity === "fast" && (
              <span className="text-xs bg-emerald-950 text-emerald-400 border border-emerald-800 px-2 py-0.5 rounded-full">⚡ Fast truster</span>
            )}
            {(lead.churn_risk ?? 0) >= 0.7 && (
              <span className="text-xs bg-red-950 text-red-400 border border-red-800 px-2 py-0.5 rounded-full animate-pulse">🧊 Cold</span>
            )}
            <button onClick={onClose} className="text-slate-500 hover:text-white text-xl leading-none ml-2">×</button>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-slate-800 overflow-x-auto">
          {TABS.map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={`flex-shrink-0 px-4 py-2.5 text-xs font-medium capitalize transition-colors ${
                tab === t.id ? "text-sky-400 border-b-2 border-sky-400" : "text-slate-500 hover:text-slate-300"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>

        <div className="p-5 overflow-y-auto max-h-[60vh] space-y-4">

          {/* ── Profile tab ── */}
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
                    {lead.aspiration_gap_score != null && lead.aspiration_gap_score >= 70 && (
                      <span className="text-xs bg-violet-950 text-violet-400 px-2 py-0.5 rounded-full">
                        Gap {lead.aspiration_gap_score}
                      </span>
                    )}
                  </div>
                  {lead.qualification_reason && (
                    <p className="text-xs text-slate-400 mb-2">{lead.qualification_reason}</p>
                  )}
                  {lead.pain_points?.length > 0 && (
                    <div className="flex flex-wrap gap-1 mb-2">
                      {lead.pain_points.map((p) => (
                        <span key={p} className="text-[10px] bg-sky-950 text-sky-400 px-2 py-0.5 rounded-full">{p}</span>
                      ))}
                    </div>
                  )}
                  {lead.recommended_angle && (
                    <p className="text-xs text-slate-500">Angle: <span className="text-slate-300">{lead.recommended_angle}</span></p>
                  )}
                  {lead.predicted_objection && (
                    <p className="text-xs text-slate-500 mt-1">Predicted objection: <span className="text-orange-300">{lead.predicted_objection}</span></p>
                  )}
                </div>
              )}

              {/* Churn alert */}
              {(lead.churn_risk ?? 0) >= 0.5 && (
                <div className="bg-red-950/40 border border-red-900 rounded-xl p-4">
                  <p className="text-xs font-medium text-red-400 mb-1">
                    Churn risk {Math.round((lead.churn_risk ?? 0) * 100)}%
                  </p>
                  {lead.reengagement_message ? (
                    <>
                      <p className="text-xs text-slate-300 whitespace-pre-wrap mb-2">{lead.reengagement_message}</p>
                      <button onClick={() => copy(lead.reengagement_message!)} className="text-xs text-red-400 hover:text-red-300">
                        {copied ? "Copied!" : "Copy re-engagement DM"}
                      </button>
                    </>
                  ) : (
                    <button
                      onClick={() => reengage.mutate()}
                      disabled={reengage.isPending}
                      className="text-xs text-red-400 hover:text-red-300"
                    >
                      {reengage.isPending ? "Generating…" : "Generate re-engagement DM"}
                    </button>
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
                <button onClick={() => saveNotes.mutate()} className="text-xs text-sky-400 hover:text-sky-300 mt-1">
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

          {/* ── DM Draft tab ── */}
          {tab === "outreach" && (
            <>
              {lead.outreach_message ? (
                <div>
                  <p className="text-xs text-slate-500 mb-2">Generated DM</p>
                  <div className="bg-slate-800 rounded-xl p-4 text-sm text-slate-200 whitespace-pre-wrap leading-relaxed">
                    {lead.outreach_message}
                  </div>
                  <button onClick={() => copy(lead.outreach_message!)} className="text-xs text-sky-400 hover:text-sky-300 mt-2">
                    {copied ? "Copied!" : "Copy to clipboard"}
                  </button>
                </div>
              ) : (
                <p className="text-sm text-slate-500 text-center py-4">No DM generated yet.</p>
              )}
              {lead.dm_variant_b && (
                <div>
                  <p className="text-xs text-slate-500 mb-2">Variant B</p>
                  <div className="bg-slate-800/60 rounded-xl p-4 text-sm text-slate-300 whitespace-pre-wrap leading-relaxed border border-slate-700">
                    {lead.dm_variant_b}
                  </div>
                </div>
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

          {/* ── Reply tab ── */}
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
                  <button onClick={() => copy(lead.suggested_reply!)} className="text-xs text-sky-400 hover:text-sky-300 mt-2">
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

          {/* ── Intel tab (CRM enrichment) ── */}
          {tab === "intel" && (
            <>
              {lead.enriched_data ? (
                <div className="space-y-3">
                  <p className="text-xs text-slate-500">
                    Last enriched {lead.enriched_at ? new Date(lead.enriched_at).toLocaleDateString() : "recently"}
                  </p>
                  {lead.enriched_data.linkedin_role && (
                    <div className="bg-slate-800 rounded-xl p-3">
                      <p className="text-xs text-slate-500 mb-1">LinkedIn / Role</p>
                      <p className="text-sm text-slate-200">
                        {lead.enriched_data.linkedin_role}
                        {lead.enriched_data.linkedin_company ? ` @ ${lead.enriched_data.linkedin_company}` : ""}
                      </p>
                    </div>
                  )}
                  {lead.enriched_data.estimated_income && (
                    <div className="bg-slate-800 rounded-xl p-3">
                      <p className="text-xs text-slate-500 mb-1">Income Bracket</p>
                      <p className="text-sm text-slate-200">{lead.enriched_data.estimated_income}</p>
                      {lead.enriched_data.income_confidence && (
                        <p className="text-xs text-slate-500 mt-0.5">Confidence: {lead.enriched_data.income_confidence}</p>
                      )}
                    </div>
                  )}
                  {lead.enriched_data.tech_stack && lead.enriched_data.tech_stack.length > 0 && (
                    <div className="bg-slate-800 rounded-xl p-3">
                      <p className="text-xs text-slate-500 mb-1">Tech Stack</p>
                      <div className="flex flex-wrap gap-1">
                        {lead.enriched_data.tech_stack.map((t) => (
                          <span key={t} className="text-[10px] bg-slate-700 text-slate-300 px-2 py-0.5 rounded-full">{t}</span>
                        ))}
                      </div>
                    </div>
                  )}
                  {lead.enriched_data.interests && lead.enriched_data.interests.length > 0 && (
                    <div className="bg-slate-800 rounded-xl p-3">
                      <p className="text-xs text-slate-500 mb-1">Interests / Content Consumed</p>
                      <div className="flex flex-wrap gap-1">
                        {lead.enriched_data.interests.map((i) => (
                          <span key={i} className="text-[10px] bg-violet-950 text-violet-300 px-2 py-0.5 rounded-full">{i}</span>
                        ))}
                      </div>
                    </div>
                  )}
                  {lead.enriched_data.business_type && (
                    <div className="bg-slate-800 rounded-xl p-3">
                      <p className="text-xs text-slate-500 mb-1">Business Type</p>
                      <p className="text-sm text-slate-200">{lead.enriched_data.business_type}</p>
                    </div>
                  )}
                </div>
              ) : (
                <p className="text-sm text-slate-500 text-center py-4">No enrichment data yet.</p>
              )}
              <button
                onClick={() => enrich.mutate()}
                disabled={enrich.isPending}
                className="w-full py-2.5 bg-violet-700 hover:bg-violet-600 disabled:opacity-40 rounded-lg text-sm font-medium transition-colors"
              >
                {enrich.isPending ? "Enriching…" : lead.enriched_data ? "🔍 Re-enrich" : "🔍 Enrich from Web"}
              </button>
              {enrich.isError && <p className="text-red-400 text-xs">{(enrich.error as any)?.response?.data?.detail}</p>}
            </>
          )}

          {/* ── Sales Script tab ── */}
          {tab === "script" && (
            <>
              {script ? (
                <div className="space-y-4">
                  {script.opener && (
                    <div className="bg-slate-800 rounded-xl p-4">
                      <p className="text-xs font-medium text-emerald-400 mb-2">Opener</p>
                      <p className="text-sm text-slate-200 whitespace-pre-wrap">{script.opener}</p>
                    </div>
                  )}
                  {script.discovery_questions && script.discovery_questions.length > 0 && (
                    <div className="bg-slate-800 rounded-xl p-4">
                      <p className="text-xs font-medium text-sky-400 mb-2">Discovery Questions</p>
                      <ol className="space-y-1">
                        {script.discovery_questions.map((q, i) => (
                          <li key={i} className="text-sm text-slate-300"><span className="text-slate-500">{i + 1}.</span> {q}</li>
                        ))}
                      </ol>
                    </div>
                  )}
                  {script.objections && script.objections.length > 0 && (
                    <div className="bg-slate-800 rounded-xl p-4">
                      <p className="text-xs font-medium text-orange-400 mb-2">Objection Handlers</p>
                      <div className="space-y-3">
                        {script.objections.map((obj, i) => (
                          <div key={i}>
                            <p className="text-xs text-orange-300/70 mb-0.5">"{obj.objection}"</p>
                            <p className="text-sm text-slate-300">{obj.response}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  {script.closing && (
                    <div className="bg-slate-800 rounded-xl p-4">
                      <p className="text-xs font-medium text-amber-400 mb-2">Closing</p>
                      <p className="text-sm text-slate-200 whitespace-pre-wrap">{script.closing}</p>
                    </div>
                  )}
                  {script.post_call_followup && (
                    <div className="bg-slate-800 rounded-xl p-4">
                      <p className="text-xs font-medium text-slate-400 mb-2">Post-Call Follow-up</p>
                      <p className="text-sm text-slate-300 whitespace-pre-wrap">{script.post_call_followup}</p>
                      <button onClick={() => copy(script.post_call_followup!)} className="text-xs text-sky-400 hover:text-sky-300 mt-2">
                        {copied ? "Copied!" : "Copy"}
                      </button>
                    </div>
                  )}
                </div>
              ) : (
                <p className="text-sm text-slate-500 text-center py-4">No sales script generated yet.</p>
              )}
              <button
                onClick={() => genScript.mutate()}
                disabled={genScript.isPending || !lead.qualification_reason}
                className="w-full py-2.5 bg-emerald-700 hover:bg-emerald-600 disabled:opacity-40 rounded-lg text-sm font-medium transition-colors"
              >
                {genScript.isPending ? "Writing script…" : script ? "📋 Regenerate Script" : "📋 Generate Sales Script"}
              </button>
              {!lead.qualification_reason && (
                <p className="text-xs text-slate-500 text-center">Qualify first to generate a script.</p>
              )}
              {genScript.isError && <p className="text-red-400 text-xs">{(genScript.error as any)?.response?.data?.detail}</p>}
            </>
          )}

          {/* ── Nurture tab ── */}
          {tab === "nurture" && (
            <>
              {nurture && nurture.length > 0 ? (
                <div className="space-y-3">
                  {nurture.map((msg, i) => (
                    <div
                      key={i}
                      className={`rounded-xl p-4 border ${
                        i < (lead.nurture_step ?? 0)
                          ? "bg-slate-800/40 border-slate-700 opacity-60"
                          : i === (lead.nurture_step ?? 0)
                          ? "bg-sky-950/50 border-sky-800"
                          : "bg-slate-800 border-slate-700"
                      }`}
                    >
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-bold text-slate-400">Day {msg.day}</span>
                          <span className="text-[10px] bg-slate-700 text-slate-400 px-2 py-0.5 rounded-full">{msg.angle}</span>
                        </div>
                        {i === (lead.nurture_step ?? 0) && (
                          <span className="text-[10px] bg-sky-900 text-sky-400 px-2 py-0.5 rounded-full">Next</span>
                        )}
                        {i < (lead.nurture_step ?? 0) && (
                          <span className="text-[10px] text-slate-600">Sent</span>
                        )}
                      </div>
                      <p className="text-xs text-slate-500 mb-2">Trigger: {msg.trigger}</p>
                      <p className="text-sm text-slate-300 whitespace-pre-wrap leading-relaxed">{msg.message}</p>
                      {i >= (lead.nurture_step ?? 0) && (
                        <button onClick={() => copy(msg.message)} className="text-xs text-sky-400 hover:text-sky-300 mt-2">
                          Copy
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-slate-500 text-center py-4">No nurture sequence yet.</p>
              )}
              <button
                onClick={() => genNurture.mutate()}
                disabled={genNurture.isPending || !lead.qualification_reason}
                className="w-full py-2.5 bg-violet-700 hover:bg-violet-600 disabled:opacity-40 rounded-lg text-sm font-medium transition-colors"
              >
                {genNurture.isPending ? "Building sequence…" : nurture ? "🔄 Regenerate Sequence" : "🌱 Build Nurture Sequence"}
              </button>
              {!lead.qualification_reason && (
                <p className="text-xs text-slate-500 text-center">Qualify first to build a nurture sequence.</p>
              )}
              {genNurture.isError && <p className="text-red-400 text-xs">{(genNurture.error as any)?.response?.data?.detail}</p>}
            </>
          )}

        </div>
      </div>
    </div>
  );
}
