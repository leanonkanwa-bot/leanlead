import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  authApi, leadsApi, pipelineApi, followupsApi, prospectingApi,
  type Lead, type Stage, type FollowupDue,
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
      <div className="w-full max-w-lg bg-slate-900 border border-slate-700 rounded-2xl overflow-hidden shadow-2xl animate-fade-in"
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
            className="w-full py-2.5 bg-brand-500 hover:bg-brand-400 disabled:opacity-40 rounded-xl text-sm font-semibold transition-colors">
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
          className="w-full py-3 bg-brand-500 hover:bg-brand-400 disabled:opacity-40 rounded-xl text-sm font-semibold transition-colors">
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
          className="w-full py-3 bg-brand-500 hover:bg-brand-400 disabled:opacity-40 rounded-xl text-sm font-semibold transition-colors">
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
function dayLabel(day: number) {
  return day === 2 ? "J+2 · Rappel léger" : day === 4 ? "J+4 · Valeur ajoutée" : "J+7 · Dernière relance";
}

function dayClasses(day: number) {
  return day === 2 ? "bg-amber-950 border-amber-800 text-amber-400"
       : day === 4 ? "bg-brand-950 border-brand-800 text-brand-400"
       : "bg-rose-950 border-rose-900 text-rose-400";
}

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
  const [copied, setCopied] = useState(false);
  const refresh = () => { qc.invalidateQueries({ queryKey: ["followups"] }); qc.invalidateQueries({ queryKey: ["leads"] }); };

  const generate = useMutation({ mutationFn: () => followupsApi.generate(item.lead_id, item.due_day), onSuccess: refresh });
  const markSent = useMutation({ mutationFn: () => followupsApi.markSent(item.lead_id, item.due_day), onSuccess: refresh });

  const message = item[msgKey(item.due_day)] as string | undefined;

  function copy() {
    if (!message) return;
    navigator.clipboard.writeText(message);
    setCopied(true); setTimeout(() => setCopied(false), 1500);
  }

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden">
      <div className="flex items-center justify-between px-5 py-4 cursor-pointer hover:bg-slate-800/30 transition-colors"
        onClick={() => setOpen(o => !o)}>
        <div className="flex items-center gap-3 min-w-0">
          <span className={`text-[10px] font-bold px-2.5 py-1 rounded-lg border flex-shrink-0 ${dayClasses(item.due_day)}`}>
            {dayLabel(item.due_day)}
          </span>
          <div className="min-w-0">
            <p className="text-sm font-medium text-white truncate">{item.name || `@${item.handle}`}</p>
            <p className="text-xs text-slate-500">@{item.handle} · contacté {daysSince(item.messaged_at)}</p>
          </div>
        </div>
        <span className="text-slate-600 ml-3 flex-shrink-0">{open ? "▲" : "▼"}</span>
      </div>

      {open && (
        <div className="px-5 pb-5 border-t border-slate-800 space-y-4">
          {item.outreach_message && (
            <div className="mt-4">
              <p className="text-xs text-slate-500 mb-1">DM original</p>
              <p className="text-xs text-slate-400 bg-slate-800/60 rounded-xl p-3 leading-relaxed line-clamp-3">
                {item.outreach_message}
              </p>
            </div>
          )}

          {message ? (
            <div>
              <p className="text-xs text-slate-500 mb-2">Message de relance</p>
              <div className="bg-slate-800 rounded-xl p-4 text-sm text-slate-200 whitespace-pre-wrap leading-relaxed">
                {message}
              </div>
              <div className="flex gap-4 mt-2">
                <button onClick={copy} className="text-xs text-brand-400 hover:text-brand-300 transition-colors">
                  {copied ? "Copié !" : "📋 Copier"}
                </button>
                <button onClick={() => generate.mutate()} disabled={generate.isPending}
                  className="text-xs text-slate-500 hover:text-slate-300 transition-colors">
                  {generate.isPending ? "Réécriture…" : "↻ Régénérer"}
                </button>
              </div>
            </div>
          ) : (
            <button onClick={() => generate.mutate()} disabled={generate.isPending}
              className="w-full py-2.5 bg-slate-800 hover:bg-slate-700 disabled:opacity-50 rounded-xl text-sm text-slate-300 transition-colors">
              {generate.isPending ? "Rédaction…" : `✍️ Générer le message ${dayLabel(item.due_day)}`}
            </button>
          )}

          <div className="flex gap-3">
            <button onClick={() => markSent.mutate()} disabled={markSent.isPending || !message}
              className="flex-1 py-2.5 bg-emerald-900 hover:bg-emerald-800 disabled:opacity-40 text-emerald-300 rounded-xl text-sm font-medium transition-colors">
              {markSent.isPending ? "Marquage…" : "✓ Marquer comme envoyé"}
            </button>
            <button onClick={() => markSent.mutate()}
              className="px-4 py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-500 rounded-xl text-sm transition-colors"
              title="Ignorer cette relance">
              Ignorer
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

function FollowupsTab() {
  const { data: items = [], isLoading, refetch } = useQuery({
    queryKey: ["followups"],
    queryFn: () => followupsApi.due().then(r => r.data),
    refetchInterval: 60_000,
  });

  const byDay = (d: number) => items.filter(i => i.due_day === d);

  return (
    <div className="max-w-2xl mx-auto space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="font-semibold text-white">File de relances</h2>
          <p className="text-xs text-slate-500 mt-0.5">Leads nécessitant une relance J+2, J+4 ou J+7 aujourd'hui</p>
        </div>
        <button onClick={() => refetch()} className="text-xs text-slate-500 hover:text-slate-300 transition-colors">↻ Actualiser</button>
      </div>

      {isLoading ? (
        <p className="text-sm text-slate-600 text-center py-12">Chargement…</p>
      ) : items.length === 0 ? (
        <div className="text-center py-16 bg-slate-900 border border-slate-800 rounded-2xl">
          <p className="text-2xl mb-2">🎉</p>
          <p className="text-sm font-medium text-white mb-1">File vide</p>
          <p className="text-xs text-slate-500">Aucune relance en attente. Revenez demain.</p>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-3 gap-3">
            {[
              { day: 2, label: "J+2 à faire", cls: "text-amber-400" },
              { day: 4, label: "J+4 à faire", cls: "text-brand-400" },
              { day: 7, label: "J+7 à faire", cls: "text-rose-400" },
            ].map(({ day, label, cls }) => (
              <div key={day} className="bg-slate-900 border border-slate-800 rounded-xl px-4 py-3 text-center">
                <p className={`text-xl font-black ${cls}`}>{byDay(day).length}</p>
                <p className="text-[10px] text-slate-500 mt-0.5">{label}</p>
              </div>
            ))}
          </div>
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
   TABLEAU DE BORD
════════════════════════════════════════════════════════════════════ */
type Tab = "pipeline" | "prospects" | "followups";

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
  ];

  const initials = (coach?.name ?? "?")[0].toUpperCase();

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col">
      {/* ── Barre de navigation ── */}
      <nav className="sticky top-0 z-40 flex items-center justify-between gap-4 px-5 py-3
                      border-b border-slate-800 bg-slate-950/90 backdrop-blur-md">
        <div className="flex items-center gap-4 min-w-0">
          <span className="font-extrabold text-lg flex-shrink-0">
            Lean<span className="text-brand-400">Lead</span>
          </span>

          {/* Sélecteur d'onglets */}
          <div className="hidden sm:flex items-center gap-1 bg-slate-900 border border-slate-800 rounded-xl p-1">
            {TABS.map(t => (
              <button key={t.id} onClick={() => setTab(t.id)}
                className={`relative px-4 py-1.5 rounded-lg text-sm font-medium transition-all ${
                  tab === t.id ? "bg-slate-800 text-white" : "text-slate-500 hover:text-slate-300"}`}>
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
            className="px-3.5 py-1.5 bg-brand-500 hover:bg-brand-400 rounded-xl text-sm font-semibold transition-colors">
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
              <button onClick={() => nav("/onboarding")}
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
                  className="px-4 py-2 bg-brand-500 hover:bg-brand-400 rounded-xl text-sm font-medium transition-colors">
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
