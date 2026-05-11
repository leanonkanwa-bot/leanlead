import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import type { Lead } from "../lib/api";
import { leadsApi, pipelineApi } from "../lib/api";

export default function LeadModal({ lead, onClose }: { lead: Lead; onClose: () => void }) {
  const qc = useQueryClient();
  const [tab, setTab] = useState<"info" | "dm" | "reply">("info");
  const [replyText, setReplyText] = useState(lead.reply_received || "");
  const [convHistory, setConvHistory] = useState("");
  const [notes, setNotes] = useState(lead.notes || "");
  const [copied, setCopied] = useState(false);

  const refetch = () => qc.invalidateQueries({ queryKey: ["leads"] });

  const qualify  = useMutation({ mutationFn: () => pipelineApi.qualify(lead.id), onSuccess: refetch });
  const write    = useMutation({ mutationFn: () => pipelineApi.write(lead.id), onSuccess: refetch });
  const reply    = useMutation({
    mutationFn: () => pipelineApi.reply(lead.id, { lead_reply: replyText, conversation_history: convHistory }),
    onSuccess: refetch,
  });
  const saveNotes = useMutation({ mutationFn: () => leadsApi.update(lead.id, { notes }), onSuccess: refetch });
  const del = useMutation({ mutationFn: () => leadsApi.delete(lead.id), onSuccess: () => { refetch(); onClose(); } });

  function copy(text: string) {
    navigator.clipboard.writeText(text);
    setCopied(true); setTimeout(() => setCopied(false), 1500);
  }

  const busy = qualify.isPending || write.isPending || reply.isPending;

  const Btn = ({ label, pending, pendingLabel, onClick, className = "" }: {
    label: string; pending: boolean; pendingLabel: string; onClick: () => void; className?: string;
  }) => (
    <button onClick={onClick} disabled={pending || busy}
      className={`px-3 py-2 rounded-lg text-xs font-medium transition-colors disabled:opacity-40 ${className}`}>
      {pending ? pendingLabel : label}
    </button>
  );

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm" onClick={onClose}>
      <div className="w-full max-w-xl bg-slate-900 border border-[#2a2a2a] rounded-2xl overflow-hidden shadow-2xl shadow-black/60 animate-fade-in"
        onClick={e => e.stopPropagation()}>
        {/* En-tête */}
        <div className="flex items-start justify-between p-5 border-b border-[#2a2a2a]">
          <div>
            <h2 className="font-semibold text-white">{lead.name}</h2>
            <p className="text-sm text-slate-400">@{lead.handle} · {lead.platform}</p>
          </div>
          <button onClick={onClose} className="text-slate-500 hover:text-white text-2xl leading-none">×</button>
        </div>

        {/* Onglets */}
        <div className="flex border-b border-[#2a2a2a]">
          {(["info", "dm", "reply"] as const).map(t => (
            <button key={t} onClick={() => setTab(t)}
              className={`flex-1 py-2.5 text-xs font-medium capitalize transition-colors border-b-2 ${
                tab === t ? "text-brand-400 border-brand-500" : "text-slate-500 border-transparent hover:text-slate-300"}`}>
              {t === "info" ? "Profil" : t === "dm" ? "Brouillon DM" : "Réponse"}
            </button>
          ))}
        </div>

        {/* Contenu */}
        <div className="p-5 overflow-y-auto max-h-[58vh] space-y-4">
          {/* Profil */}
          {tab === "info" && (
            <>
              {lead.bio && (
                <div>
                  <p className="text-xs text-slate-500 mb-1">Bio</p>
                  <p className="text-sm text-slate-300 leading-relaxed">{lead.bio}</p>
                </div>
              )}
              {lead.qualification_score > 0 && (
                <div className="bg-slate-800 rounded-xl p-4">
                  <div className="flex items-center gap-3 mb-2">
                    <span className="text-xs text-slate-500">Score IA</span>
                    <span className="text-2xl font-black text-brand-400">{lead.qualification_score}/100</span>
                  </div>
                  {lead.qualification_reason && (
                    <p className="text-xs text-slate-400 mb-3 leading-relaxed">{lead.qualification_reason}</p>
                  )}
                  {lead.pain_points?.length > 0 && (
                    <div className="flex flex-wrap gap-1.5">
                      {lead.pain_points.map(p => (
                        <span key={p} className="text-[10px] bg-[#1a1a1a] text-brand-400 border border-white/[0.08] px-2 py-0.5 rounded-full">{p}</span>
                      ))}
                    </div>
                  )}
                </div>
              )}
              <div>
                <label className="text-xs text-slate-500 mb-1 block">Notes</label>
                <textarea value={notes} onChange={e => setNotes(e.target.value)} rows={3}
                  className="w-full bg-slate-800 border border-[#2a2a2a] rounded-xl px-3 py-2 text-sm resize-none focus:outline-none focus:border-brand-500" />
                <button onClick={() => saveNotes.mutate()}
                  className="text-xs text-brand-400 hover:text-brand-300 mt-1 transition-colors">
                  {saveNotes.isPending ? "Enregistrement…" : "Enregistrer les notes"}
                </button>
              </div>
              <div className="flex flex-wrap gap-2 pt-1">
                <Btn label="🎯 Re-qualifier" pending={qualify.isPending} pendingLabel="Qualification…"
                  onClick={() => qualify.mutate()}
                  className="bg-[#1a1a1a] hover:bg-[#222] border border-[#2a2a2a] text-brand-400" />
                <button onClick={() => { if (confirm("Supprimer ce lead ?")) del.mutate(); }}
                  className="ml-auto px-3 py-2 bg-red-950 hover:bg-red-900 text-red-400 rounded-lg text-xs transition-colors">
                  Supprimer
                </button>
              </div>
              {qualify.isError && (
                <p className="text-red-400 text-xs">
                  {(qualify.error as any)?.response?.data?.detail}
                </p>
              )}
            </>
          )}

          {/* DM */}
          {tab === "dm" && (
            <>
              {lead.outreach_message ? (
                <div>
                  <p className="text-xs text-slate-500 mb-2">DM généré</p>
                  <div className="bg-slate-800 rounded-xl p-4 text-sm text-slate-200 whitespace-pre-wrap leading-relaxed">
                    {lead.outreach_message}
                  </div>
                  <button onClick={() => copy(lead.outreach_message!)}
                    className="text-xs text-brand-400 hover:text-brand-300 mt-2 transition-colors">
                    {copied ? "Copié !" : "📋 Copier dans le presse-papiers"}
                  </button>
                </div>
              ) : (
                <div className="text-center py-8">
                  <p className="text-sm text-slate-500 mb-4">
                    {!lead.qualification_reason ? "Qualifiez d'abord ce lead pour générer un DM." : "Aucun DM généré pour l'instant."}
                  </p>
                </div>
              )}
              <button onClick={() => write.mutate()} disabled={busy || !lead.qualification_reason}
                className="w-full py-2.5 bg-brand-500 hover:bg-brand-400 shadow-glow-brand hover:shadow-glow-brand-lg disabled:opacity-40 disabled:shadow-none rounded-xl text-sm font-semibold transition-colors">
                {write.isPending ? "Rédaction du DM…" : lead.outreach_message ? "↻ Régénérer le DM" : "✍️ Générer un DM"}
              </button>
              {write.isError && (
                <p className="text-red-400 text-xs">{(write.error as any)?.response?.data?.detail}</p>
              )}
            </>
          )}

          {/* Réponse */}
          {tab === "reply" && (
            <>
              <div>
                <label className="text-xs text-slate-500 mb-1 block">Sa réponse</label>
                <textarea value={replyText} onChange={e => setReplyText(e.target.value)} rows={3}
                  className="w-full bg-slate-800 border border-[#2a2a2a] rounded-xl px-3 py-2 text-sm resize-none focus:outline-none focus:border-brand-500"
                  placeholder="Collez leur message ici…" />
              </div>
              <div>
                <label className="text-xs text-slate-500 mb-1 block">Historique de la conversation <span className="text-slate-700">(facultatif)</span></label>
                <textarea value={convHistory} onChange={e => setConvHistory(e.target.value)} rows={3}
                  className="w-full bg-slate-800 border border-[#2a2a2a] rounded-xl px-3 py-2 text-sm resize-none focus:outline-none focus:border-brand-500"
                  placeholder={"Vous : [votre DM]\nEux : [première réponse]\n…"} />
              </div>
              {lead.suggested_reply && (
                <div>
                  <p className="text-xs text-slate-500 mb-2">Réponse suggérée</p>
                  <div className="bg-slate-800 rounded-xl p-4 text-sm text-slate-200 whitespace-pre-wrap leading-relaxed">
                    {lead.suggested_reply}
                  </div>
                  <button onClick={() => copy(lead.suggested_reply!)}
                    className="text-xs text-brand-400 hover:text-brand-300 mt-2 transition-colors">
                    {copied ? "Copié !" : "📋 Copier"}
                  </button>
                </div>
              )}
              <button onClick={() => reply.mutate()} disabled={busy || !replyText}
                className="w-full py-2.5 bg-brand-500 hover:bg-brand-400 shadow-glow-brand hover:shadow-glow-brand-lg disabled:opacity-40 disabled:shadow-none rounded-xl text-sm font-semibold transition-colors">
                {reply.isPending ? "Génération…" : "🤖 Générer une réponse"}
              </button>
              {reply.isError && (
                <p className="text-red-400 text-xs">{(reply.error as any)?.response?.data?.detail}</p>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
