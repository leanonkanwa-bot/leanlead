import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  authApi, leadsApi, pipelineApi, followupsApi, prospectingApi,
  type Lead, type Stage, type FollowupDue, type Classification, type ReplyAnalysis,
} from "../lib/api";
import KanbanBoard from "../components/KanbanBoard";

/* ════════════════════════════════════════════════════════════════════
   MODAL AJOUT DE LEAD
════════════════════════════════════════════════════════════════════ */
function AddLeadModal({ onClose }: { onClose: () => void }) {
  const qc = useQueryClient();
  const [f, setF] = useState({
    name: "", handle: "", platform: "instagram",
    profile_url: "", bio: "", followers: "", posts_summary: "", notes: "",
  });
  const [autoQualify, setAutoQualify] = useState(true);

  const add = useMutation({
    mutationFn: async () => {
      const { data: lead } = await leadsApi.create({ ...f, followers: parseInt(f.followers) || 0 });
      if (autoQualify) await pipelineApi.qualify(lead.id);
    },
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["leads"] }); onClose(); },
  });

  const set = (k: string) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) =>
    setF(p => ({ ...p, [k]: e.target.value }));

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm" onClick={onClose}>
      <div className="w-full max-w-lg bg-slate-900 border border-slate-700 rounded-2xl overflow-hidden shadow-2xl shadow-black/60 animate-fade-in"
        onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between p-5 border-b border-slate-800">
          <h2 className="font-semibold text-white">Ajouter un lead</h2>
          <button onClick={onClose} className="text-slate-500 hover:text-white text-2xl leading-none">×</button>
        </div>

        <div className="p-5 space-y-4 overflow-y-auto max-h-[68vh]">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-xs text-slate-400 mb-1 block">Nom complet</label>
              <input value={f.name} onChange={set("name")}
                className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:border-brand-500"
                placeholder="Jane Smith" />
            </div>
            <div>
              <label className="text-xs text-slate-400 mb-1 block">Identifiant *</label>
              <div className="flex">
                <span className="bg-slate-700 border border-slate-600 border-r-0 rounded-l-xl px-2.5 text-slate-400 text-sm flex items-center">@</span>
                <input value={f.handle} onChange={set("handle")} required
                  className="flex-1 bg-slate-800 border border-slate-700 rounded-r-xl px-3 py-2.5 text-sm focus:outline-none focus:border-brand-500"
                  placeholder="janesmith" />
              </div>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-xs text-slate-400 mb-1 block">Plateforme</label>
              <select value={f.platform} onChange={set("platform")}
                className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:border-brand-500">
                <option value="instagram">📸 Instagram</option>
                <option value="tiktok">🎵 TikTok</option>
                <option value="twitter">𝕏 Twitter / X</option>
                <option value="linkedin">💼 LinkedIn</option>
              </select>
            </div>
            <div>
              <label className="text-xs text-slate-400 mb-1 block">Abonnés</label>
              <input type="number" value={f.followers} onChange={set("followers")}
                className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:border-brand-500"
                placeholder="0" />
            </div>
          </div>

          <div>
            <label className="text-xs text-slate-400 mb-1 block">URL du profil</label>
            <input value={f.profile_url} onChange={set("profile_url")}
              className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:border-brand-500"
              placeholder="https://instagram.com/janesmith" />
          </div>

          <div>
            <label className="text-xs text-slate-400 mb-1 block">Bio <span className="text-slate-600">(collez la bio complète pour de meilleurs résultats IA)</span></label>
            <textarea value={f.bio} onChange={set("bio")} rows={3}
              className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:border-brand-500 resize-none"
              placeholder="J'aide les mamans à perdre 10 kg en 12 semaines | DM pour mon guide gratuit…" />
          </div>

          <div>
            <label className="text-xs text-slate-400 mb-1 block">Notes sur les publications récentes <span className="text-slate-600">(facultatif)</span></label>
            <textarea value={f.posts_summary} onChange={set("posts_summary")} rows={2}
              className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:border-brand-500 resize-none"
              placeholder="Publications sur la préparation des repas, 3x/semaine. Dernière légende : 'pourquoi j'ai arrêté de compter les calories'…" />
          </div>

          <label className="flex items-center gap-3 cursor-pointer">
            <input type="checkbox" checked={autoQualify} onChange={e => setAutoQualify(e.target.checked)}
              className="w-4 h-4 accent-brand-500" />
            <span className="text-sm text-slate-300">Qualifier automatiquement avec l'IA après l'ajout</span>
          </label>

          {add.isError && (
            <p className="text-red-400 text-xs bg-red-950/40 border border-red-900/40 rounded-lg px-3 py-2">
              {(add.error as any)?.response?.data?.detail || "Échec de l'ajout du lead."}
            </p>
          )}
        </div>

        <div className="p-5 border-t border-slate-800">
          <button onClick={() => add.mutate()} disabled={add.isPending || !f.handle}
            className="w-full py-2.5 bg-brand-500 hover:bg-brand-400 shadow-glow-brand hover:shadow-glow-brand-lg disabled:opacity-40 disabled:shadow-none rounded-xl text-sm font-semibold transition-colors">
            {add.isPending
              ? (autoQualify ? "Ajout et qualification…" : "Ajout…")
              : "Ajouter le lead"}
          </button>
        </div>
      </div>
    </div>
  );
}

/* ════════════════════════════════════════════════════════════════════
   ONGLET PROSPECTION
════════════════════════════════════════════════════════════════════ */
function ProspectsTab() {
  const qc = useQueryClient();
  const [profileUrl, setProfileUrl] = useState("");
  const [autoWrite, setAutoWrite] = useState(true);
  const [urlSuccess, setUrlSuccess] = useState<string | null>(null);

  const fromUrl = useMutation({
    mutationFn: () => prospectingApi.fromUrl({ profile_url: profileUrl, auto_write: autoWrite }).then(r => r.data),
    onSuccess: (lead) => {
      qc.invalidateQueries({ queryKey: ["leads"] });
      setUrlSuccess(`@${lead.handle} ajouté au pipeline${lead.outreach_message ? " avec DM généré" : ""} !`);
      setProfileUrl("");
      setTimeout(() => setUrlSuccess(null), 6000);
    },
  });

  const [platform, setPlatform] = useState("instagram");
  const [tagInput, setTagInput] = useState("");
  const [tags, setTags] = useState<string[]>([]);
  const [maxResults, setMaxResults] = useState(20);
  const [autoQualify, setAutoQualify] = useState(true);

  const { data: jobs = [] } = useQuery({
    queryKey: ["jobs"],
    queryFn: () => prospectingApi.jobs().then(r => r.data),
    refetchInterval: 5_000,
  });

  const suggest = useMutation({
    mutationFn: () => prospectingApi.suggestHashtags().then(r => r.data.hashtags),
    onSuccess: t => setTags(t),
  });

  const run = useMutation({
    mutationFn: () => prospectingApi.run({ platform, hashtags: tags, max_results: maxResults, auto_qualify: autoQualify }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["jobs"] }); qc.invalidateQueries({ queryKey: ["leads"] }); },
  });

  function addTag() {
    const t = tagInput.replace(/^#/, "").trim().toLowerCase();
    if (t && !tags.includes(t)) setTags(p => [...p, t]);
    setTagInput("");
  }

  const running = jobs.some(j => j.status === "running" || j.status === "pending");

  const statusColors: Record<string, string> = {
    pending: "text-amber-400", running: "text-brand-400", done: "text-emerald-400", error: "text-red-400",
  };
  const statusLabels: Record<string, string> = {
    pending: "en attente", running: "en cours", done: "terminé", error: "erreur",
  };

  return (
    <div className="max-w-2xl mx-auto space-y-5">
      {/* ── Prospection par URL ── */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
        <h2 className="font-semibold text-white mb-1">🚀 Lancer la prospection</h2>
        <p className="text-xs text-slate-500 mb-5">Collez l'URL d'un profil TikTok ou Instagram — l'IA le qualifie et rédige le DM automatiquement.</p>

        <div className="mb-4">
          <label className="text-xs text-slate-400 mb-1.5 block">URL du profil</label>
          <input
            value={profileUrl}
            onChange={e => { setProfileUrl(e.target.value); setUrlSuccess(null); fromUrl.reset(); }}
            className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:border-brand-500 transition-colors"
            placeholder="https://tiktok.com/@nomduprofil ou https://instagram.com/nomduprofil"
          />
        </div>

        <label className="flex items-center gap-2 cursor-pointer mb-5">
          <input type="checkbox" checked={autoWrite} onChange={e => setAutoWrite(e.target.checked)}
            className="w-4 h-4 accent-brand-500" />
          <span className="text-sm text-slate-300">Générer le DM automatiquement</span>
        </label>

        {fromUrl.isError && (
          <p className="text-red-400 text-xs mb-3 bg-red-950/40 border border-red-900/40 rounded-lg px-3 py-2">
            {(fromUrl.error as any)?.response?.data?.detail || "Échec de la prospection."}
          </p>
        )}
        {urlSuccess && (
          <p className="text-emerald-400 text-xs mb-3 bg-emerald-950/40 border border-emerald-900/40 rounded-lg px-3 py-2">
            ✓ {urlSuccess}
          </p>
        )}

        <button
          onClick={() => fromUrl.mutate()}
          disabled={fromUrl.isPending || !profileUrl.trim()}
          className="w-full py-3 bg-brand-500 hover:bg-brand-400 shadow-glow-brand hover:shadow-glow-brand-lg disabled:opacity-40 disabled:shadow-none rounded-xl text-sm font-semibold transition-colors">
          {fromUrl.isPending
            ? (autoWrite ? "Qualification + rédaction du DM…" : "Qualification en cours…")
            : "🚀 Lancer la prospection"}
        </button>
      </div>

      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
        <h2 className="font-semibold text-white mb-1">Trouver de nouveaux leads</h2>
        <p className="text-xs text-slate-500 mb-5">Scraper des profils publics par hashtag et les qualifier automatiquement.</p>

        {/* Plateforme */}
        <div className="mb-5">
          <label className="text-xs text-slate-400 mb-2 block">Plateforme</label>
          <div className="grid grid-cols-2 gap-3">
            {[["instagram","📸 Instagram"],["tiktok","🎵 TikTok"]].map(([v,l]) => (
              <button key={v} onClick={() => setPlatform(v)}
                className={`py-2.5 rounded-xl border text-sm font-medium transition-all ${
                  platform === v
                    ? "bg-brand-900/40 border-brand-600 text-brand-300"
                    : "bg-slate-800 border-slate-700 text-slate-400 hover:border-slate-600"}`}>
                {l}
              </button>
            ))}
          </div>
        </div>

        {/* Hashtags */}
        <div className="mb-5">
          <div className="flex justify-between mb-2">
            <label className="text-xs text-slate-400">Hashtags *</label>
            <button onClick={() => suggest.mutate()} disabled={suggest.isPending}
              className="text-[10px] text-brand-400 hover:text-brand-300 transition-colors">
              {suggest.isPending ? "Génération…" : "✦ Suggestions IA pour mon créneau"}
            </button>
          </div>
          <div className="flex gap-2 mb-2">
            <div className="flex flex-1 items-center bg-slate-800 border border-slate-700 rounded-xl overflow-hidden focus-within:border-brand-500 transition-colors">
              <span className="pl-3 text-slate-500 text-sm">#</span>
              <input value={tagInput} onChange={e => setTagInput(e.target.value)}
                onKeyDown={e => e.key === "Enter" && (e.preventDefault(), addTag())}
                className="flex-1 bg-transparent px-2 py-2.5 text-sm focus:outline-none"
                placeholder="coachbusiness" />
            </div>
            <button onClick={addTag}
              className="px-4 py-2.5 bg-slate-700 hover:bg-slate-600 rounded-xl text-sm transition-colors">Ajouter</button>
          </div>
          {tags.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {tags.map(t => (
                <span key={t} className="flex items-center gap-1 bg-brand-950 border border-brand-900 text-brand-300 text-xs px-2.5 py-1 rounded-full">
                  #{t}
                  <button onClick={() => setTags(p => p.filter(x => x !== t))} className="text-brand-500 hover:text-white">×</button>
                </span>
              ))}
            </div>
          )}
        </div>

        {/* Options */}
        <div className="flex gap-4 items-end mb-5">
          <div className="flex-1">
            <label className="text-xs text-slate-400 mb-1 block">Profils max</label>
            <select value={maxResults} onChange={e => setMaxResults(Number(e.target.value))}
              className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:border-brand-500">
              {[10,20,50,100].map(n => <option key={n} value={n}>{n} profils</option>)}
            </select>
          </div>
          <label className="flex items-center gap-2 cursor-pointer pb-1">
            <input type="checkbox" checked={autoQualify} onChange={e => setAutoQualify(e.target.checked)}
              className="w-4 h-4 accent-brand-500" />
            <span className="text-sm text-slate-300 whitespace-nowrap">Auto-qualifier</span>
          </label>
        </div>

        {run.isError && (
          <p className="text-red-400 text-xs mb-3 bg-red-950/40 border border-red-900/40 rounded-lg px-3 py-2">
            {(run.error as any)?.response?.data?.detail || "Échec du démarrage de la tâche."}
          </p>
        )}

        <button onClick={() => run.mutate()} disabled={run.isPending || !tags.length || running}
          className="w-full py-3 bg-brand-500 hover:bg-brand-400 shadow-glow-brand hover:shadow-glow-brand-lg disabled:opacity-40 disabled:shadow-none rounded-xl text-sm font-semibold transition-colors">
          {run.isPending ? "Démarrage…" : running ? "Tâche en cours…" : `🔍 Trouver des leads sur ${platform}`}
        </button>
        {running && (
          <p className="text-center text-xs text-amber-400 mt-2">
            Scraping en arrière-plan — les leads apparaîtront dans votre pipeline une fois terminé.
          </p>
        )}
      </div>

      {/* Historique des tâches */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
        <h3 className="font-medium text-white mb-4 text-sm">Tâches récentes</h3>
        {jobs.length === 0 ? (
          <p className="text-xs text-slate-600 text-center py-6">Aucune tâche — lancez une recherche ci-dessus.</p>
        ) : (
          <div className="space-y-3">
            {jobs.map(j => (
              <div key={j.id} className="flex items-center justify-between gap-4 py-3 border-b border-slate-800 last:border-0">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <span className={`text-[10px] font-bold uppercase ${statusColors[j.status]}`}>
                      {j.status === "running" ? "⟳ en cours" : statusLabels[j.status] || j.status}
                    </span>
                    <span className="text-xs text-slate-600 capitalize">{j.platform}</span>
                  </div>
                  <div className="flex flex-wrap gap-1">
                    {j.hashtags.slice(0, 5).map(t => (
                      <span key={t} className="text-[10px] text-slate-600">#{t}</span>
                    ))}
                  </div>
                  {j.error_message && <p className="text-[10px] text-red-400 mt-1 truncate max-w-xs">{j.error_message}</p>}
                </div>
                <div className="text-right flex-shrink-0">
                  <p className="text-sm font-semibold text-white">{j.leads_found} leads</p>
                  <p className="text-[10px] text-slate-600">{j.started_at ? new Date(j.started_at).toLocaleTimeString() : ""}</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

/* ════════════════════════════════════════════════════════════════════
   ONGLET RELANCES
════════════════════════════════════════════════════════════════════ */
const DAY_CONFIG = {
  2: { label: "J+2", sublabel: "Rappel léger",       badge: "bg-amber-950/70 border-amber-800/60 text-amber-400", ring: "ring-amber-800/20" },
  4: { label: "J+4", sublabel: "Valeur ajoutée",      badge: "bg-brand-950/70 border-brand-800/60 text-brand-400", ring: "ring-brand-800/20" },
  7: { label: "J+7", sublabel: "Dernière relance",    badge: "bg-rose-950/70 border-rose-900/60 text-rose-400",    ring: "ring-rose-900/20" },
} as const;

function msgKey(day: number): keyof FollowupDue {
  return day === 2 ? "followup_d2_message" : day === 4 ? "followup_d4_message" : "followup_d7_message";
}

function daysSince(iso: string) {
  const d = Math.floor((Date.now() - new Date(iso).getTime()) / 86_400_000);
  return d === 1 ? "il y a 1 jour" : `il y a ${d} jours`;
}

function FollowupRow({ item }: { item: FollowupDue }) {
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [localMessage, setLocalMessage] = useState<string | undefined>(
    item[msgKey(item.due_day)] as string | undefined
  );
  const [sent, setSent] = useState(false);

  const cfg = DAY_CONFIG[item.due_day as 2 | 4 | 7];
  const refresh = () => { qc.invalidateQueries({ queryKey: ["followups"] }); qc.invalidateQueries({ queryKey: ["leads"] }); };

  const generate = useMutation({
    mutationFn: () => followupsApi.generate(item.lead_id, item.due_day),
    onSuccess: ({ data }) => setLocalMessage(data.message),
  });

  // Primary action: generate if needed → copy → mark sent
  const send = useMutation({
    mutationFn: () => followupsApi.send(item.lead_id, item.due_day),
    onSuccess: ({ data }) => {
      setLocalMessage(data.message);
      navigator.clipboard.writeText(data.message).catch(() => {});
      setSent(true);
      setTimeout(refresh, 800);
    },
  });

  return (
    <div className={`bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden transition-all ${
      open ? `ring-1 ${cfg.ring}` : ""
    }`}>
      {/* Header row */}
      <div
        className="flex items-center justify-between px-5 py-4 cursor-pointer hover:bg-slate-800/20 transition-colors"
        onClick={() => setOpen(o => !o)}
      >
        <div className="flex items-center gap-3 min-w-0">
          <div className={`flex-shrink-0 px-2.5 py-1 rounded-lg border text-[10px] font-bold ${cfg.badge}`}>
            {cfg.label}
            <span className="hidden sm:inline"> · {cfg.sublabel}</span>
          </div>
          <div className="min-w-0">
            <p className="text-sm font-semibold text-slate-100 truncate">{item.name || `@${item.handle}`}</p>
            <p className="text-[11px] text-slate-600">@{item.handle} · contacté {daysSince(item.messaged_at)}</p>
          </div>
        </div>
        <div className="flex items-center gap-3 ml-3 flex-shrink-0">
          {sent && <span className="text-[10px] text-emerald-400">✓ envoyé</span>}
          <span className="text-slate-700 text-xs">{open ? "▲" : "▼"}</span>
        </div>
      </div>

      {/* Expanded content */}
      {open && (
        <div className="border-t border-slate-800/60 px-5 pt-4 pb-5 space-y-4 animate-fade-in">
          {/* Original DM context */}
          {item.outreach_message && (
            <div>
              <p className="text-[10px] font-medium text-slate-600 uppercase tracking-wider mb-1.5">DM original</p>
              <p className="text-xs text-slate-500 bg-slate-800/40 rounded-xl p-3 leading-relaxed line-clamp-2 italic">
                "{item.outreach_message}"
              </p>
            </div>
          )}

          {/* Follow-up message */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <p className="text-[10px] font-medium text-slate-600 uppercase tracking-wider">Message de relance</p>
              {localMessage && !send.isPending && (
                <button
                  onClick={() => generate.mutate()}
                  disabled={generate.isPending}
                  className="text-[10px] text-slate-600 hover:text-slate-400 transition-colors"
                >
                  {generate.isPending ? "Réécriture…" : "↻ Régénérer"}
                </button>
              )}
            </div>

            {localMessage ? (
              <div className="bg-slate-800/60 border border-slate-700/40 rounded-xl p-4 text-sm text-slate-200 whitespace-pre-wrap leading-relaxed">
                {localMessage}
              </div>
            ) : (
              <div className="bg-slate-800/30 border border-dashed border-slate-700/40 rounded-xl px-4 py-6 text-center">
                <p className="text-xs text-slate-600">
                  {generate.isPending ? "Rédaction en cours…" : "Le message sera généré à l'envoi"}
                </p>
              </div>
            )}
          </div>

          {/* Errors */}
          {(send.isError || generate.isError) && (
            <p className="text-red-400 text-xs bg-red-950/30 border border-red-900/40 rounded-xl px-3 py-2">
              {((send.error || generate.error) as any)?.response?.data?.detail || "Erreur lors de la génération"}
            </p>
          )}

          {/* Actions */}
          {sent ? (
            <div className="flex items-center gap-2 py-2.5 px-4 bg-emerald-950/30 border border-emerald-900/40 rounded-xl">
              <span className="text-emerald-400 text-sm">✓</span>
              <span className="text-sm text-emerald-400 font-medium">Copié dans le presse-papier · Marqué comme envoyé</span>
            </div>
          ) : (
            <button
              onClick={() => send.mutate()}
              disabled={send.isPending}
              className="w-full py-3 bg-brand-500 hover:bg-brand-400 shadow-glow-brand hover:shadow-glow-brand-lg disabled:opacity-40 disabled:shadow-none rounded-xl text-sm font-semibold transition-all duration-150"
            >
              {send.isPending
                ? (localMessage ? "Copie + marquage…" : "Génération + envoi…")
                : (localMessage ? "📋 Copier & marquer envoyé" : "✨ Générer & envoyer")}
            </button>
          )}
        </div>
      )}
    </div>
  );
}

function FollowupsTab() {
  const { data: items = [], isLoading, refetch } = useQuery({
    queryKey: ["followups"],
    queryFn: () => followupsApi.due().then(r => r.data),
    refetchInterval: 30_000,
  });

  const byDay = (d: number) => items.filter(i => i.due_day === d);
  const total = items.length;

  return (
    <div className="max-w-2xl mx-auto space-y-5">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h2 className="font-heading font-semibold text-white text-lg">File de relances</h2>
          <p className="text-xs text-slate-500 mt-0.5">
            {total === 0 ? "Aucune relance en attente" : `${total} relance${total > 1 ? "s" : ""} à traiter`}
          </p>
        </div>
        <button onClick={() => refetch()} className="text-xs text-slate-600 hover:text-slate-400 transition-colors mt-1">
          ↻ Actualiser
        </button>
      </div>

      {isLoading ? (
        <div className="space-y-3">
          {[1,2,3].map(i => <div key={i} className="h-16 bg-slate-900 rounded-2xl animate-pulse" />)}
        </div>
      ) : items.length === 0 ? (
        <div className="text-center py-16 bg-slate-900 border border-slate-800 rounded-2xl">
          <p className="text-3xl mb-3">🎉</p>
          <p className="font-heading font-semibold text-white mb-1">File vide</p>
          <p className="text-xs text-slate-500 max-w-xs mx-auto">
            Aucune relance en attente. Les leads apparaissent ici automatiquement J+2, J+4 et J+7 après votre premier contact.
          </p>
        </div>
      ) : (
        <>
          {/* Stats */}
          <div className="grid grid-cols-3 gap-3">
            {([2, 4, 7] as const).map(day => {
              const cfg = DAY_CONFIG[day];
              const count = byDay(day).length;
              return (
                <div key={day} className="bg-slate-900 border border-slate-800 rounded-xl px-4 py-3 text-center">
                  <p className={`font-heading text-2xl font-black ${count > 0 ? cfg.badge.split(" ").find(c => c.startsWith("text-")) : "text-slate-700"}`}>
                    {count}
                  </p>
                  <p className="text-[10px] text-slate-600 mt-0.5">{cfg.label} · {cfg.sublabel}</p>
                </div>
              );
            })}
          </div>

          {/* Rows — most urgent first (7 → 4 → 2) */}
          <div className="space-y-3">
            {[7, 4, 2].flatMap(day => byDay(day)).map(item => (
              <FollowupRow key={`${item.lead_id}-${item.due_day}`} item={item} />
            ))}
          </div>
        </>
      )}
    </div>
  );
}

/* ════════════════════════════════════════════════════════════════════
   ONGLET RÉPONSES
════════════════════════════════════════════════════════════════════ */
const CLASS_CONFIG: Record<Classification, { label: string; bg: string; border: string; text: string; icon: string }> = {
  POSITIF:      { label: "Positif",        bg: "bg-emerald-950/60", border: "border-emerald-800/50", text: "text-emerald-400", icon: "↗" },
  NEUTRE:       { label: "Neutre",          bg: "bg-slate-800/60",   border: "border-slate-700/50",   text: "text-slate-400",   icon: "→" },
  NEGATIF:      { label: "Négatif",         bg: "bg-rose-950/60",    border: "border-rose-900/50",    text: "text-rose-400",    icon: "✕" },
  SIGNAL_ACHAT: { label: "Signal d'achat!", bg: "bg-brand-950/60",   border: "border-brand-800/50",   text: "text-brand-400",   icon: "🎯" },
};

const STAGE_LABELS: Record<string, string> = {
  replied: "Répondu", booked: "Réservé", closed: "Clôturé",
};

function RepliesTab({ leads }: { leads: Lead[] }) {
  const qc = useQueryClient();
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [replyText, setReplyText] = useState("");
  const [convHistory, setConvHistory] = useState("");
  const [search, setSearch] = useState("");
  const [analysis, setAnalysis] = useState<ReplyAnalysis | null>(null);
  const [copied, setCopied] = useState(false);

  const contactedLeads = leads.filter(l => l.stage === "contacted" || l.stage === "replied");
  const filteredLeads = search
    ? contactedLeads.filter(l =>
        l.name?.toLowerCase().includes(search.toLowerCase()) ||
        l.handle?.toLowerCase().includes(search.toLowerCase())
      )
    : contactedLeads;

  const selected = leads.find(l => l.id === selectedId) ?? null;

  const analyze = useMutation({
    mutationFn: () => pipelineApi.reply(selectedId!, { lead_reply: replyText, conversation_history: convHistory }),
    onSuccess: ({ data }) => {
      setAnalysis(data);
      qc.invalidateQueries({ queryKey: ["leads"] });
    },
  });

  function selectLead(lead: Lead) {
    setSelectedId(lead.id);
    setReplyText("");
    setConvHistory("");
    setAnalysis(null);
    setCopied(false);
  }

  function copy(text: string) {
    navigator.clipboard.writeText(text).catch(() => {});
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  const inputCls = "w-full bg-slate-900 border border-slate-800 rounded-xl px-3 py-2.5 text-sm text-slate-100 placeholder-slate-600 focus:outline-none focus:border-brand-500 focus:shadow-glow-sm transition-all resize-none";

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-5">
        <h2 className="font-heading font-semibold text-white text-lg">Gestion des réponses</h2>
        <p className="text-xs text-slate-500 mt-0.5">
          Collez la réponse reçue — Claude la classifie et génère la réponse parfaite.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[280px_1fr] gap-5">
        {/* ── Lead selector ── */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden flex flex-col" style={{ maxHeight: "72vh" }}>
          <div className="px-4 pt-4 pb-3 border-b border-slate-800">
            <p className="text-[11px] font-medium text-slate-500 uppercase tracking-wider mb-2">
              Leads contactés ({contactedLeads.length})
            </p>
            <input
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2 text-sm text-slate-100 placeholder-slate-600 focus:outline-none focus:border-brand-500 transition-all"
              placeholder="Rechercher…"
            />
          </div>

          <div className="flex-1 overflow-y-auto scrollbar-thin p-2 space-y-1">
            {filteredLeads.length === 0 ? (
              <p className="text-xs text-slate-600 text-center py-8 px-4">
                {contactedLeads.length === 0
                  ? "Aucun lead contacté. Envoyez des DMs d'abord."
                  : "Aucun résultat."}
              </p>
            ) : filteredLeads.map(lead => (
              <button
                key={lead.id}
                onClick={() => selectLead(lead)}
                className={`w-full text-left px-3 py-2.5 rounded-xl transition-all ${
                  selectedId === lead.id
                    ? "bg-brand-950/60 border border-brand-800/50 shadow-glow-sm"
                    : "hover:bg-slate-800/50 border border-transparent"
                }`}
              >
                <p className="text-sm font-medium text-slate-200 truncate">{lead.name || `@${lead.handle}`}</p>
                <div className="flex items-center gap-2 mt-0.5">
                  <p className="text-[11px] text-slate-600 truncate">@{lead.handle}</p>
                  {lead.reply_received && (
                    <span className="text-[9px] bg-emerald-950/60 text-emerald-500 border border-emerald-900/50 px-1.5 py-0.5 rounded-full flex-shrink-0">
                      déjà analysé
                    </span>
                  )}
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* ── Reply composer ── */}
        <div className="space-y-4">
          {!selected ? (
            <div className="bg-slate-900 border border-slate-800 rounded-2xl flex items-center justify-center" style={{ minHeight: "320px" }}>
              <div className="text-center px-8">
                <p className="text-3xl mb-3">💬</p>
                <p className="font-heading font-semibold text-slate-400 mb-1">Sélectionnez un lead</p>
                <p className="text-xs text-slate-600">Choisissez un lead contacté dans la liste pour analyser sa réponse.</p>
              </div>
            </div>
          ) : (
            <>
              {/* Lead info header */}
              <div className="bg-slate-900 border border-slate-800 rounded-2xl px-5 py-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-semibold text-white">{selected.name || `@${selected.handle}`}</p>
                    <p className="text-xs text-slate-500 mt-0.5">@{selected.handle} · {selected.platform}</p>
                  </div>
                  {selected.outreach_message && (
                    <div className="text-right hidden sm:block">
                      <p className="text-[10px] text-slate-600 mb-1">DM envoyé</p>
                      <p className="text-xs text-slate-500 max-w-[200px] truncate italic">"{selected.outreach_message}"</p>
                    </div>
                  )}
                </div>
              </div>

              {/* Input form */}
              <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-4">
                <div>
                  <label className="text-[11px] font-medium text-slate-500 uppercase tracking-wider block mb-2">
                    Réponse reçue *
                  </label>
                  <textarea
                    value={replyText}
                    onChange={e => { setReplyText(e.target.value); setAnalysis(null); }}
                    rows={4}
                    className={inputCls}
                    placeholder="Collez ici le message reçu du lead…"
                  />
                </div>
                <div>
                  <label className="text-[11px] font-medium text-slate-500 uppercase tracking-wider block mb-2">
                    Historique de conversation <span className="normal-case text-slate-700">(facultatif)</span>
                  </label>
                  <textarea
                    value={convHistory}
                    onChange={e => setConvHistory(e.target.value)}
                    rows={2}
                    className={inputCls}
                    placeholder={"Vous : [votre DM]\nEux : [leur réponse précédente]\n…"}
                  />
                </div>

                {analyze.isError && (
                  <p className="text-red-400 text-xs bg-red-950/30 border border-red-900/40 rounded-xl px-3 py-2">
                    {(analyze.error as any)?.response?.data?.detail || "Erreur lors de l'analyse."}
                  </p>
                )}

                <button
                  onClick={() => analyze.mutate()}
                  disabled={analyze.isPending || !replyText.trim()}
                  className="w-full py-3 bg-brand-500 hover:bg-brand-400 shadow-glow-brand hover:shadow-glow-brand-lg disabled:opacity-40 disabled:shadow-none rounded-xl text-sm font-semibold transition-all duration-150"
                >
                  {analyze.isPending ? "Analyse en cours…" : "🤖 Analyser et générer la réponse"}
                </button>
              </div>

              {/* Analysis result */}
              {analysis && (() => {
                const cfg = CLASS_CONFIG[analysis.classification];
                const newStage = analysis.classification === "SIGNAL_ACHAT" ? "booked"
                               : analysis.classification === "NEGATIF" ? "closed"
                               : "replied";
                return (
                  <div className={`border rounded-2xl p-5 space-y-4 animate-slide-up ${cfg.bg} ${cfg.border}`}>
                    {/* Classification */}
                    <div className="flex items-start gap-3">
                      <div className={`flex-shrink-0 flex items-center gap-2 px-3 py-1.5 rounded-xl border ${cfg.bg} ${cfg.border}`}>
                        <span className="text-base">{cfg.icon}</span>
                        <span className={`text-sm font-bold ${cfg.text}`}>{cfg.label}</span>
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-xs text-slate-400 leading-relaxed">{analysis.reasoning}</p>
                        <p className="text-[10px] text-slate-600 mt-1">
                          Lead déplacé vers : <span className="text-slate-400">{STAGE_LABELS[newStage] ?? newStage}</span>
                        </p>
                      </div>
                    </div>

                    {analysis.inject_calendly && (
                      <div className="flex items-center gap-2 bg-brand-950/40 border border-brand-800/40 rounded-xl px-3 py-2">
                        <span className="text-brand-400 text-sm">📅</span>
                        <p className="text-xs text-brand-300">Lien Calendly injecté dans la réponse</p>
                      </div>
                    )}

                    {/* Generated reply */}
                    <div>
                      <p className="text-[11px] font-medium text-slate-500 uppercase tracking-wider mb-2">Réponse suggérée</p>
                      <div className="bg-slate-900/60 border border-slate-700/40 rounded-xl p-4 text-sm text-slate-200 whitespace-pre-wrap leading-relaxed">
                        {analysis.suggested_reply}
                      </div>
                    </div>

                    {/* Copy CTA */}
                    <button
                      onClick={() => copy(analysis.suggested_reply)}
                      className={`w-full py-3 rounded-xl text-sm font-semibold transition-all duration-150 ${
                        copied
                          ? "bg-emerald-900/50 border border-emerald-800/50 text-emerald-400"
                          : "bg-brand-500 hover:bg-brand-400 shadow-glow-brand hover:shadow-glow-brand-lg text-white"
                      }`}
                    >
                      {copied ? "✓ Copié dans le presse-papiers !" : "📋 Copier la réponse"}
                    </button>
                  </div>
                );
              })()}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

/* ════════════════════════════════════════════════════════════════════
   TABLEAU DE BORD
════════════════════════════════════════════════════════════════════ */
type Tab = "pipeline" | "prospects" | "followups" | "replies";

export default function Dashboard() {
  const nav = useNavigate();
  const [tab, setTab] = useState<Tab>("pipeline");
  const [showAdd, setShowAdd] = useState(false);
  const [search, setSearch] = useState("");

  const { data: coach } = useQuery({
    queryKey: ["me"],
    queryFn: () => authApi.me().then(r => r.data),
  });

  const { data: leads = [], isLoading } = useQuery({
    queryKey: ["leads"],
    queryFn: () => leadsApi.list().then(r => r.data),
    refetchInterval: 15_000,
  });

  const { data: followups = [] } = useQuery({
    queryKey: ["followups"],
    queryFn: () => followupsApi.due().then(r => r.data),
    refetchInterval: 60_000,
  });

  function logout() {
    localStorage.removeItem("ll_token");
    localStorage.removeItem("ll_name");
    nav("/", { replace: true });
  }

  const filtered = search
    ? leads.filter(l =>
        l.name?.toLowerCase().includes(search.toLowerCase()) ||
        l.handle?.toLowerCase().includes(search.toLowerCase()) ||
        l.bio?.toLowerCase().includes(search.toLowerCase())
      )
    : leads;

  const stats = {
    total:     leads.length,
    contacted: leads.filter(l => l.stage === "contacted").length,
    replied:   leads.filter(l => l.stage === "replied").length,
    booked:    leads.filter(l => l.stage === "booked").length,
  };

  const TABS: { id: Tab; label: string; badge?: number }[] = [
    { id: "pipeline",  label: "Pipeline" },
    { id: "prospects", label: "Prospection" },
    { id: "followups", label: "Relances", badge: followups.length || undefined },
    { id: "replies",   label: "Réponses" },
  ];

  const initials = (coach?.name ?? "?")[0].toUpperCase();

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col">
      {/* ── Barre de navigation ── */}
      <nav className="sticky top-0 z-40 flex items-center justify-between gap-4 px-5 py-3
                      border-b border-slate-800 bg-[#0a0a0a]/90 backdrop-blur-md">
        <div className="flex items-center gap-4 min-w-0">
          <span className="font-heading font-extrabold text-lg flex-shrink-0">
            Lean<span className="text-brand-400">Lead</span>
          </span>

          {/* Sélecteur d'onglets */}
          <div className="hidden sm:flex items-center gap-1 bg-slate-900 border border-slate-800 rounded-xl p-1">
            {TABS.map(t => (
              <button key={t.id} onClick={() => setTab(t.id)}
                className={`relative px-4 py-1.5 rounded-lg text-sm font-medium transition-all ${
                  tab === t.id ? "bg-slate-800 text-white shadow-glow-sm" : "text-slate-500 hover:text-slate-300"}`}>
                {t.label}
                {t.badge ? (
                  <span className="absolute -top-1.5 -right-1.5 w-4 h-4 flex items-center justify-center
                                   bg-amber-500 text-slate-900 text-[9px] font-black rounded-full">
                    {t.badge > 9 ? "9+" : t.badge}
                  </span>
                ) : null}
              </button>
            ))}
          </div>
        </div>

        <div className="flex items-center gap-3">
          {tab === "pipeline" && (
            <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Rechercher…"
              className="hidden sm:block bg-slate-800 border border-slate-700 rounded-xl px-3 py-1.5
                         text-sm focus:outline-none focus:border-brand-500 w-36 transition-colors" />
          )}
          <button onClick={() => setShowAdd(true)}
            className="px-3.5 py-1.5 bg-brand-500 hover:bg-brand-400 shadow-glow-brand hover:shadow-glow-brand-lg rounded-xl text-sm font-semibold transition-colors">
            + Ajouter un lead
          </button>

          {/* Menu compte */}
          <div className="relative group">
            <button className="w-8 h-8 rounded-full bg-brand-900 border border-brand-800 flex items-center justify-center
                               text-xs font-bold text-brand-300 hover:border-brand-600 transition-colors">
              {initials}
            </button>
            <div className="absolute right-0 mt-2 w-44 bg-slate-800 border border-slate-700 rounded-xl overflow-hidden
                            shadow-xl opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all">
              <div className="px-4 py-3 border-b border-slate-700">
                <p className="text-xs font-semibold text-white truncate">{coach?.name}</p>
                <p className="text-[10px] text-slate-500 truncate">{coach?.email}</p>
              </div>
              <button onClick={() => nav("/settings")}
                className="w-full text-left px-4 py-2.5 text-xs text-slate-300 hover:bg-slate-700 transition-colors">
                Paramètres
              </button>
              <button onClick={logout}
                className="w-full text-left px-4 py-2.5 text-xs text-red-400 hover:bg-slate-700 transition-colors">
                Déconnexion
              </button>
            </div>
          </div>
        </div>
      </nav>

      {/* ── Barre de stats (pipeline uniquement) ── */}
      {tab === "pipeline" && (
        <div className="flex gap-6 px-6 py-3 border-b border-slate-900">
          {[
            { label: "Total",      value: stats.total,     color: "text-white" },
            { label: "Contactés",  value: stats.contacted, color: "text-brand-400" },
            { label: "Répondus",   value: stats.replied,   color: "text-brand-400" },
            { label: "Réservés",   value: stats.booked,    color: "text-emerald-400" },
            {
              label: "Taux conv.",
              value: stats.total ? `${Math.round((stats.booked / stats.total) * 100)} %` : "—",
              color: "text-amber-400",
            },
          ].map(s => (
            <div key={s.label}>
              <p className="text-[10px] text-slate-600 uppercase tracking-wider">{s.label}</p>
              <p className={`text-lg font-black ${s.color}`}>{s.value}</p>
            </div>
          ))}
        </div>
      )}

      {/* ── Contenu des onglets ── */}
      <div className="flex-1 min-h-0">
        {tab === "pipeline" && (
          <div className="h-full px-5 py-4 overflow-auto">
            {isLoading ? (
              <div className="flex items-center justify-center h-64 text-slate-600 text-sm">
                Chargement du pipeline…
              </div>
            ) : leads.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-64 text-center">
                <p className="text-4xl mb-3">📭</p>
                <p className="text-sm font-semibold text-white mb-1">Aucun lead pour l'instant</p>
                <p className="text-xs text-slate-500 mb-4">Ajoutez des leads manuellement ou utilisez l'onglet Prospection pour scraper Instagram/TikTok.</p>
                <button onClick={() => setShowAdd(true)}
                  className="px-4 py-2 bg-brand-500 hover:bg-brand-400 shadow-glow-brand hover:shadow-glow-brand-lg rounded-xl text-sm font-medium transition-colors">
                  + Ajouter votre premier lead
                </button>
              </div>
            ) : (
              <KanbanBoard leads={filtered} />
            )}
          </div>
        )}

        {tab === "prospects" && (
          <div className="px-5 py-6 overflow-auto">
            <ProspectsTab />
          </div>
        )}

        {tab === "followups" && (
          <div className="px-5 py-6 overflow-auto">
            <FollowupsTab />
          </div>
        )}

        {tab === "replies" && (
          <div className="px-5 py-6 overflow-auto">
            <RepliesTab leads={leads} />
          </div>
        )}
      </div>

      {/* ── Navigation mobile bas ── */}
      <div className="sm:hidden flex border-t border-slate-800 bg-slate-950">
        {TABS.map(t => (
          <button key={t.id} onClick={() => setTab(t.id)}
            className={`relative flex-1 py-3 text-xs font-medium transition-colors ${
              tab === t.id ? "text-brand-400" : "text-slate-600 hover:text-slate-400"}`}>
            {t.label}
            {t.badge ? (
              <span className="absolute top-2 right-1/4 w-3.5 h-3.5 flex items-center justify-center
                               bg-amber-500 text-slate-900 text-[8px] font-black rounded-full">
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
