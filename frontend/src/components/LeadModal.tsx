import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import type { Lead } from "../lib/api";
import { leadsApi, pipelineApi } from "../lib/api";

const EMOTION_COLORS: Record<string, string> = {
  frustration: "text-orange-400",
  fear: "text-red-400",
  hope: "text-emerald-400",
  excitement: "text-brand-400",
  shame: "text-purple-400",
  anxiety: "text-amber-400",
};
const EMOTION_LABELS: Record<string, string> = {
  frustration: "😤 Frustration",
  fear: "😟 Peur",
  hope: "🌱 Espoir",
  excitement: "⚡ Excitation",
  shame: "😔 Honte",
  anxiety: "😰 Anxiété",
};
const AWARENESS_LABELS: Record<string, string> = {
  unaware: "Inconscient du problème",
  problem_aware: "Conscient du problème",
  solution_aware: "Cherche une solution",
  product_aware: "Prêt à acheter",
};
const WARMING_LABELS: Record<string, string> = {
  none: "—",
  comment_ready: "Commentaire prêt",
  commented: "Commentaire posté ✓",
  dm_ready: "Prêt pour le DM ✓✓",
};
const SOURCE_BADGES: Record<string, { label: string; cls: string }> = {
  viral_post:          { label: "🔥 Post viral",      cls: "bg-orange-950/60 text-orange-400 border-orange-900/40" },
  competitor_audience: { label: "🎯 Concurrent",      cls: "bg-brand-950/60 text-brand-400 border-brand-900/40" },
  direct:              { label: "➕ Ajout direct",    cls: "bg-slate-800 text-slate-400 border-slate-700" },
  hashtag:             { label: "# Hashtag",          cls: "bg-slate-800 text-slate-500 border-slate-700" },
};

export default function LeadModal({ lead, onClose }: { lead: Lead; onClose: () => void }) {
  const qc = useQueryClient();
  const [tab, setTab] = useState<"info" | "dm" | "warming" | "reply">("info");
  const [replyText, setReplyText] = useState(lead.reply_received || "");
  const [convHistory, setConvHistory] = useState("");
  const [notes, setNotes] = useState(lead.notes || "");
  const [copied, setCopied] = useState<string | null>(null);
  const [activeVariant, setActiveVariant] = useState<"A" | "B">(lead.dm_variant_sent || "A");

  const refetch = () => qc.invalidateQueries({ queryKey: ["leads"] });

  const qualify   = useMutation({ mutationFn: () => pipelineApi.qualify(lead.id), onSuccess: refetch });
  const rescan    = useMutation({ mutationFn: () => pipelineApi.rescan(lead.id), onSuccess: refetch });
  const writeAb   = useMutation({ mutationFn: () => pipelineApi.writeAb(lead.id), onSuccess: refetch });
  const warm      = useMutation({ mutationFn: () => pipelineApi.warm(lead.id), onSuccess: refetch });
  const markWarmed = useMutation({
    mutationFn: (status: string) => pipelineApi.markWarmed(lead.id, status),
    onSuccess: refetch,
  });
  const markVariant = useMutation({
    mutationFn: (v: "A" | "B") => pipelineApi.markVariant(lead.id, v),
    onSuccess: refetch,
  });
  const reply = useMutation({
    mutationFn: () => pipelineApi.reply(lead.id, { lead_reply: replyText, conversation_history: convHistory }),
    onSuccess: refetch,
  });
  const saveNotes = useMutation({ mutationFn: () => leadsApi.update(lead.id, { notes }), onSuccess: refetch });
  const del = useMutation({ mutationFn: () => leadsApi.delete(lead.id), onSuccess: () => { refetch(); onClose(); } });

  function copy(text: string, key: string) {
    navigator.clipboard.writeText(text);
    setCopied(key); setTimeout(() => setCopied(null), 1500);
  }

  const busy = qualify.isPending || rescan.isPending || writeAb.isPending || reply.isPending || warm.isPending;
  const psycho = lead.psychographic_profile;
  const sourceBadge = lead.source_tag ? SOURCE_BADGES[lead.source_tag] : null;

  const TABS = [
    { id: "info" as const, label: "Profil" },
    { id: "dm" as const, label: "DM A/B" },
    { id: "warming" as const, label: "Warming" },
    { id: "reply" as const, label: "Réponse" },
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm" onClick={onClose}>
      <div className="w-full max-w-xl bg-slate-900 border border-[#2a2a2a] rounded-2xl overflow-hidden shadow-2xl shadow-black/60 animate-fade-in"
        onClick={e => e.stopPropagation()}>

        {/* Header */}
        <div className="flex items-start justify-between p-5 border-b border-[#2a2a2a]">
          <div className="min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <h2 className="font-semibold text-white">{lead.name}</h2>
              {sourceBadge && (
                <span className={`text-[10px] border px-1.5 py-0.5 rounded-full ${sourceBadge.cls}`}>
                  {sourceBadge.label}
                </span>
              )}
            </div>
            <div className="flex items-center gap-3 mt-0.5">
              <p className="text-sm text-slate-400">@{lead.handle} · {lead.platform}</p>
              {lead.response_probability != null && (
                <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${
                  lead.response_probability >= 60 ? "bg-emerald-950/60 text-emerald-400" :
                  lead.response_probability >= 40 ? "bg-amber-950/60 text-amber-400" :
                  "bg-slate-800 text-slate-500"
                }`}>
                  {lead.response_probability}% réponse
                </span>
              )}
            </div>
          </div>
          <button onClick={onClose} className="text-slate-500 hover:text-white text-2xl leading-none ml-3 flex-shrink-0">×</button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-[#2a2a2a]">
          {TABS.map(t => (
            <button key={t.id} onClick={() => setTab(t.id)}
              className={`flex-1 py-2.5 text-xs font-medium transition-colors border-b-2 ${
                tab === t.id ? "text-brand-400 border-brand-500" : "text-slate-500 border-transparent hover:text-slate-300"}`}>
              {t.label}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="p-5 overflow-y-auto max-h-[60vh] space-y-4">

          {/* ── PROFIL tab ── */}
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
                    {lead.score_delta != null && lead.score_delta !== 0 && (
                      <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${
                        lead.score_delta > 0 ? "bg-red-950/60 text-red-400" : "bg-slate-800 text-slate-500"
                      }`}>
                        {lead.score_delta > 0 ? "⚡" : "▼"} {lead.score_delta > 0 ? "+" : ""}{lead.score_delta.toFixed(0)} pts
                      </span>
                    )}
                    {lead.language && (
                      <span className="ml-auto text-[10px] bg-slate-700 text-slate-400 px-2 py-0.5 rounded uppercase">
                        {lead.language}
                      </span>
                    )}
                  </div>
                  {lead.qualification_reason && (
                    <p className="text-xs text-slate-400 mb-3 leading-relaxed">{lead.qualification_reason}</p>
                  )}
                  {lead.pain_points?.length > 0 && (
                    <div className="flex flex-wrap gap-1.5 mb-3">
                      {lead.pain_points.map(p => (
                        <span key={p} className="text-[10px] bg-[#1a1a1a] text-brand-400 border border-white/[0.08] px-2 py-0.5 rounded-full">{p}</span>
                      ))}
                    </div>
                  )}
                  {lead.predicted_objection && (
                    <div className="mt-2 bg-amber-950/20 border border-amber-900/30 rounded-lg px-3 py-2">
                      <p className="text-[10px] text-amber-600 mb-0.5">Objection probable pré-emtée dans le DM</p>
                      <p className="text-xs text-amber-400 italic">"{lead.predicted_objection}"</p>
                    </div>
                  )}
                  <button
                    onClick={() => rescan.mutate()}
                    disabled={rescan.isPending}
                    className="mt-3 text-[10px] text-slate-600 hover:text-slate-400 transition-colors disabled:opacity-40"
                  >
                    {rescan.isPending ? "⟳ Rescan…" : "⟳ Rescan douleur"}
                  </button>
                </div>
              )}

              {/* Psychographic profile */}
              {psycho && (
                <div className="bg-slate-800/60 rounded-xl p-4">
                  <p className="text-xs text-slate-500 mb-3 font-medium">Profil psychographique</p>
                  <div className="grid grid-cols-2 gap-3">
                    {psycho.dominant_emotion && (
                      <div>
                        <p className="text-[10px] text-slate-600 mb-0.5">Émotion dominante</p>
                        <p className={`text-xs font-medium ${EMOTION_COLORS[psycho.dominant_emotion] || "text-slate-300"}`}>
                          {EMOTION_LABELS[psycho.dominant_emotion] || psycho.dominant_emotion}
                        </p>
                      </div>
                    )}
                    {psycho.awareness_stage && (
                      <div>
                        <p className="text-[10px] text-slate-600 mb-0.5">Niveau de conscience</p>
                        <p className="text-xs text-slate-300">{AWARENESS_LABELS[psycho.awareness_stage] || psycho.awareness_stage}</p>
                      </div>
                    )}
                    {psycho.communication_style && (
                      <div>
                        <p className="text-[10px] text-slate-600 mb-0.5">Style de communication</p>
                        <p className="text-xs text-slate-300 capitalize">{psycho.communication_style}</p>
                      </div>
                    )}
                    {psycho.best_contact_time && (
                      <div>
                        <p className="text-[10px] text-slate-600 mb-0.5">Meilleur moment</p>
                        <p className="text-xs text-slate-300 capitalize">{psycho.best_contact_time}</p>
                      </div>
                    )}
                  </div>
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
                <button onClick={() => qualify.mutate()} disabled={busy}
                  className="px-3 py-2 rounded-lg text-xs font-medium bg-[#1a1a1a] hover:bg-[#222] border border-[#2a2a2a] text-brand-400 transition-colors disabled:opacity-40">
                  {qualify.isPending ? "Qualification…" : "🎯 Re-qualifier"}
                </button>
                <button onClick={() => { if (confirm("Supprimer ce lead ?")) del.mutate(); }}
                  className="ml-auto px-3 py-2 bg-red-950 hover:bg-red-900 text-red-400 rounded-lg text-xs transition-colors">
                  Supprimer
                </button>
              </div>
            </>
          )}

          {/* ── DM A/B tab ── */}
          {tab === "dm" && (
            <>
              {(lead.outreach_message || lead.dm_variant_b) ? (
                <>
                  {/* Variant selector */}
                  <div className="flex gap-2 mb-3">
                    {(["A", "B"] as const).map(v => (
                      <button key={v} onClick={() => setActiveVariant(v)}
                        className={`flex-1 py-2 rounded-xl text-xs font-semibold border transition-colors ${
                          activeVariant === v
                            ? "bg-brand-500/20 border-brand-500 text-brand-300"
                            : "bg-slate-800 border-[#2a2a2a] text-slate-500"
                        }`}>
                        Variante {v}
                        {lead.dm_variant_sent === v && (
                          <span className="ml-1.5 text-[9px] bg-emerald-950/60 text-emerald-400 px-1 py-0.5 rounded">envoyé</span>
                        )}
                      </button>
                    ))}
                  </div>

                  {/* DM text */}
                  {((activeVariant === "A" && lead.outreach_message) || (activeVariant === "B" && lead.dm_variant_b)) ? (
                    <div>
                      <div className="bg-slate-800 rounded-xl p-4 text-sm text-slate-200 whitespace-pre-wrap leading-relaxed">
                        {activeVariant === "A" ? lead.outreach_message : lead.dm_variant_b}
                      </div>
                      <div className="flex gap-3 mt-2">
                        <button onClick={() => copy(activeVariant === "A" ? lead.outreach_message! : lead.dm_variant_b!, `dm-${activeVariant}`)}
                          className="text-xs text-brand-400 hover:text-brand-300 transition-colors">
                          {copied === `dm-${activeVariant}` ? "Copié !" : "📋 Copier"}
                        </button>
                        {lead.dm_variant_sent !== activeVariant && (
                          <button onClick={() => { copy(activeVariant === "A" ? lead.outreach_message! : lead.dm_variant_b!, `dm-${activeVariant}`); markVariant.mutate(activeVariant); }}
                            className="text-xs text-emerald-400 hover:text-emerald-300 transition-colors">
                            ✓ Marquer comme envoyé
                          </button>
                        )}
                      </div>
                    </div>
                  ) : (
                    <p className="text-xs text-slate-600 py-4 text-center">Pas de variante {activeVariant} encore.</p>
                  )}
                </>
              ) : (
                <div className="text-center py-6">
                  <p className="text-sm text-slate-500 mb-4">
                    {!lead.qualification_reason
                      ? "Qualifiez d'abord ce lead."
                      : "Aucun DM généré pour l'instant."}
                  </p>
                </div>
              )}

              <button onClick={() => writeAb.mutate()} disabled={busy || !lead.qualification_reason}
                className="w-full py-2.5 bg-brand-500 hover:bg-brand-400 shadow-glow-brand disabled:opacity-40 disabled:shadow-none rounded-xl text-sm font-semibold transition-colors">
                {writeAb.isPending ? "Génération A/B…" : (lead.outreach_message ? "↻ Régénérer variantes A/B" : "✍️ Générer variantes A/B")}
              </button>
              {writeAb.isError && (
                <p className="text-red-400 text-xs">{(writeAb.error as any)?.response?.data?.detail}</p>
              )}
            </>
          )}

          {/* ── WARMING tab ── */}
          {tab === "warming" && (
            <>
              <div className="bg-slate-800/60 rounded-xl p-4">
                <p className="text-xs text-slate-500 mb-2 font-medium">Séquence de warming</p>
                <p className="text-[11px] text-slate-600 leading-relaxed mb-3">
                  Postez un commentaire genuinement sur leur contenu → attendez 24-48h → envoyez le DM.
                  Augmente le taux de réponse de 3% à 25%+.
                </p>
                <div className="flex items-center gap-2 flex-wrap">
                  {(["none", "comment_ready", "commented", "dm_ready"] as const).map((s, i) => (
                    <div key={s} className="flex items-center gap-1">
                      {i > 0 && <span className="text-slate-700 text-xs">→</span>}
                      <span className={`text-[10px] px-2 py-0.5 rounded-full border ${
                        lead.warming_status === s
                          ? "bg-brand-500/20 border-brand-500/50 text-brand-400"
                          : "bg-slate-800 border-[#2a2a2a] text-slate-600"
                      }`}>
                        {WARMING_LABELS[s]}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Warming comment */}
              {lead.warming_comment ? (
                <div>
                  <p className="text-xs text-slate-500 mb-2">Commentaire IA à poster</p>
                  <div className="bg-slate-800 rounded-xl p-4 text-sm text-slate-200 italic leading-relaxed">
                    "{lead.warming_comment}"
                  </div>
                  <div className="flex gap-3 mt-2">
                    <button onClick={() => copy(lead.warming_comment!, "comment")}
                      className="text-xs text-brand-400 hover:text-brand-300 transition-colors">
                      {copied === "comment" ? "Copié !" : "📋 Copier le commentaire"}
                    </button>
                    {lead.warming_status === "comment_ready" && (
                      <button onClick={() => markWarmed.mutate("commented")}
                        className="text-xs text-emerald-400 hover:text-emerald-300 transition-colors">
                        ✓ Commentaire posté
                      </button>
                    )}
                    {lead.warming_status === "commented" && (
                      <button onClick={() => markWarmed.mutate("dm_ready")}
                        className="text-xs text-emerald-400 hover:text-emerald-300 transition-colors">
                        ✓ Prêt pour le DM
                      </button>
                    )}
                  </div>
                </div>
              ) : (
                <div className="text-center py-4">
                  <p className="text-xs text-slate-600">Générez un commentaire personnalisé ci-dessous.</p>
                </div>
              )}

              <button onClick={() => warm.mutate()} disabled={busy}
                className="w-full py-2.5 bg-brand-500 hover:bg-brand-400 shadow-glow-brand disabled:opacity-40 disabled:shadow-none rounded-xl text-sm font-semibold transition-colors">
                {warm.isPending ? "Génération…" : (lead.warming_comment ? "↻ Régénérer le commentaire" : "🔥 Générer un commentaire warming")}
              </button>
              {warm.isError && (
                <p className="text-red-400 text-xs">{(warm.error as any)?.response?.data?.detail}</p>
              )}
            </>
          )}

          {/* ── RÉPONSE tab ── */}
          {tab === "reply" && (
            <>
              <div>
                <label className="text-xs text-slate-500 mb-1 block">Sa réponse</label>
                <textarea value={replyText} onChange={e => setReplyText(e.target.value)} rows={3}
                  className="w-full bg-slate-800 border border-[#2a2a2a] rounded-xl px-3 py-2 text-sm resize-none focus:outline-none focus:border-brand-500"
                  placeholder="Collez leur message ici…" />
              </div>
              <div>
                <label className="text-xs text-slate-500 mb-1 block">Historique <span className="text-slate-700">(facultatif)</span></label>
                <textarea value={convHistory} onChange={e => setConvHistory(e.target.value)} rows={3}
                  className="w-full bg-slate-800 border border-[#2a2a2a] rounded-xl px-3 py-2 text-sm resize-none focus:outline-none focus:border-brand-500"
                  placeholder={"Vous : [DM]\nEux : [réponse]\n…"} />
              </div>
              {lead.suggested_reply && (
                <div>
                  <p className="text-xs text-slate-500 mb-2">Réponse suggérée</p>
                  <div className="bg-slate-800 rounded-xl p-4 text-sm text-slate-200 whitespace-pre-wrap leading-relaxed">
                    {lead.suggested_reply}
                  </div>
                  <button onClick={() => copy(lead.suggested_reply!, "reply")}
                    className="text-xs text-brand-400 hover:text-brand-300 mt-2 transition-colors">
                    {copied === "reply" ? "Copié !" : "📋 Copier"}
                  </button>
                </div>
              )}
              <button onClick={() => reply.mutate()} disabled={busy || !replyText}
                className="w-full py-2.5 bg-brand-500 hover:bg-brand-400 shadow-glow-brand disabled:opacity-40 disabled:shadow-none rounded-xl text-sm font-semibold transition-colors">
                {reply.isPending ? "Génération…" : "🤖 Générer une réponse"}
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
