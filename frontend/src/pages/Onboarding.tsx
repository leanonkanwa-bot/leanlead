import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { authApi } from "../lib/api";

const STEPS = ["Votre créneau", "Points de douleur", "Votre offre", "Intégrations"];

function Step({ n, label, active, done }: { n: number; label: string; active: boolean; done: boolean }) {
  return (
    <div className="flex items-center gap-2">
      <div className={`w-8 h-8 rounded-full border-2 flex items-center justify-center text-xs font-bold transition-all ${
        done ? "bg-brand-500 border-brand-500 text-white"
        : active ? "border-brand-500 text-brand-400"
        : "border-slate-700 text-slate-600"}`}>
        {done ? "✓" : n}
      </div>
      <span className={`text-xs hidden sm:block ${active ? "text-white" : "text-slate-600"}`}>{label}</span>
    </div>
  );
}

export default function Onboarding() {
  const nav = useNavigate();
  const [step, setStep] = useState(0);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [painInput, setPainInput] = useState("");
  const [form, setForm] = useState({
    niche: "", offer_description: "", target_audience: "",
    icp_pain_points: [] as string[],
    calendly_link: "",
    airtable_base_id: "appfdB2W41J5sVZ2U", airtable_api_key: "", apify_api_key: "",
  });

  const set = (k: string) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
    setForm(f => ({ ...f, [k]: e.target.value }));

  function addPain() {
    const trimmed = painInput.trim();
    if (!trimmed || form.icp_pain_points.includes(trimmed)) return;
    setForm(f => ({ ...f, icp_pain_points: [...f.icp_pain_points, trimmed] }));
    setPainInput("");
  }

  function removePain(pain: string) {
    setForm(f => ({ ...f, icp_pain_points: f.icp_pain_points.filter(p => p !== pain) }));
  }

  async function finish() {
    setSaving(true); setError("");
    try {
      await authApi.onboard(form);
      nav("/dashboard", { replace: true });
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Échec de l'enregistrement. Réessayez.");
    } finally { setSaving(false); }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-950 px-4 py-12">
      <div className="w-full max-w-lg">
        {/* Progression */}
        <div className="flex items-center justify-center gap-3 mb-8">
          {STEPS.map((label, i) => (
            <div key={label} className="flex items-center gap-3">
              <Step n={i + 1} label={label} active={i === step} done={i < step} />
              {i < STEPS.length - 1 && (
                <div className={`w-8 h-px transition-all ${i < step ? "bg-brand-500" : "bg-slate-800"}`} />
              )}
            </div>
          ))}
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-8 animate-fade-in">
          {/* ── Étape 0 : Créneau ── */}
          {step === 0 && (
            <>
              <h1 className="font-heading text-lg font-semibold mb-1">Dans quoi êtes-vous coach ?</h1>
              <p className="text-xs text-slate-500 mb-6">L'IA utilise ces informations pour noter les leads et personnaliser chaque message.</p>
              <div className="space-y-5">
                <div>
                  <label className="block text-xs text-slate-400 mb-1.5">Votre créneau de coaching *</label>
                  <input value={form.niche} onChange={set("niche")}
                    className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:border-brand-500"
                    placeholder="ex. Coaching business pour entrepreneurs en ligne" />
                </div>
                <div>
                  <label className="block text-xs text-slate-400 mb-1.5">Quel est votre client idéal ? *</label>
                  <textarea value={form.target_audience} onChange={set("target_audience")} rows={3}
                    className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:border-brand-500 resize-none"
                    placeholder="ex. Coachs en ligne souhaitant décrocher 5 clients premium en 90 jours sans publicité payante…" />
                </div>
              </div>
              <button onClick={() => setStep(1)} disabled={!form.niche || !form.target_audience}
                className="mt-6 w-full py-2.5 bg-brand-500 hover:bg-brand-400 shadow-glow-brand hover:shadow-glow-brand-lg disabled:opacity-40 disabled:shadow-none rounded-xl text-sm font-semibold transition-colors">
                Continuer →
              </button>
            </>
          )}

          {/* ── Étape 1 : Points de douleur ── */}
          {step === 1 && (
            <>
              <h1 className="font-heading text-lg font-semibold mb-1">Quelles douleurs exprime votre client idéal ?</h1>
              <p className="text-xs text-slate-500 mb-6">L'IA cherchera des personnes qui <span className="text-slate-300 font-medium">vivent ces problèmes en ce moment</span> — pas des coaches ou des prestataires. Soyez précis : décrivez ce qu'ils postent, pas ce qu'ils veulent.</p>
              <div className="space-y-3">
                <div className="flex gap-2">
                  <input
                    value={painInput}
                    onChange={e => setPainInput(e.target.value)}
                    onKeyDown={e => { if (e.key === "Enter") { e.preventDefault(); addPain(); } }}
                    className="flex-1 bg-slate-800 border border-slate-700 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:border-brand-500"
                    placeholder="ex. Je n'arrive pas à trouver mes premiers clients"
                  />
                  <button onClick={addPain} disabled={!painInput.trim()}
                    className="px-4 py-2.5 bg-brand-500 hover:bg-brand-400 disabled:opacity-40 rounded-xl text-sm font-semibold transition-colors">
                    +
                  </button>
                </div>
                {form.icp_pain_points.length > 0 && (
                  <ul className="space-y-2">
                    {form.icp_pain_points.map(pain => (
                      <li key={pain} className="flex items-start gap-2 bg-slate-800/60 border border-slate-700 rounded-lg px-3 py-2 text-sm">
                        <span className="flex-1 text-slate-200">{pain}</span>
                        <button onClick={() => removePain(pain)} className="text-slate-500 hover:text-red-400 transition-colors text-xs mt-0.5">✕</button>
                      </li>
                    ))}
                  </ul>
                )}
                {form.icp_pain_points.length === 0 && (
                  <div className="text-xs text-slate-600 bg-slate-800/30 border border-slate-800 rounded-lg px-3 py-3 space-y-1">
                    <p className="text-slate-500 font-medium mb-1">Exemples :</p>
                    {["Je galère à remplir mon agenda de clients", "Je poste tous les jours mais personne n'achète", "Je vends pas assez cher et je m'épuise"].map(ex => (
                      <button key={ex} onClick={() => { setForm(f => ({ ...f, icp_pain_points: [...f.icp_pain_points, ex] })); }} className="block w-full text-left hover:text-slate-300 transition-colors truncate">
                        + {ex}
                      </button>
                    ))}
                  </div>
                )}
              </div>
              <div className="flex gap-3 mt-6">
                <button onClick={() => setStep(0)}
                  className="flex-1 py-2.5 border border-slate-700 hover:border-slate-600 rounded-xl text-sm transition-colors">
                  ← Retour
                </button>
                <button onClick={() => setStep(2)} disabled={form.icp_pain_points.length === 0}
                  className="flex-1 py-2.5 bg-brand-500 hover:bg-brand-400 shadow-glow-brand hover:shadow-glow-brand-lg disabled:opacity-40 disabled:shadow-none rounded-xl text-sm font-semibold transition-colors">
                  Continuer →
                </button>
              </div>
              <button onClick={() => setStep(2)} className="w-full text-center text-xs text-slate-600 hover:text-slate-400 mt-3 transition-colors">
                Passer (vous pourrez les ajouter plus tard)
              </button>
            </>
          )}

          {/* ── Étape 2 : Offre ── */}
          {step === 2 && (
            <>
              <h1 className="font-heading text-lg font-semibold mb-1">Décrivez votre offre</h1>
              <p className="text-xs text-slate-500 mb-6">L'IA rédige des DMs ciblant directement cette transformation.</p>
              <div className="space-y-5">
                <div>
                  <label className="block text-xs text-slate-400 mb-1.5">Quelle transformation apportez-vous ? *</label>
                  <textarea value={form.offer_description} onChange={set("offer_description")} rows={4}
                    className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:border-brand-500 resize-none"
                    placeholder="ex. J'aide les coachs en ligne à décrocher leurs 5 premiers clients premium en 90 jours grâce à une stratégie de DM éprouvée, sans publicité payante." />
                </div>
                <div>
                  <label className="block text-xs text-slate-400 mb-1.5">Lien Calendly / réservation</label>
                  <input value={form.calendly_link} onChange={set("calendly_link")}
                    className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:border-brand-500"
                    placeholder="https://calendly.com/yourname/30min" />
                  <p className="text-xs text-slate-600 mt-1">Utilisé quand l'IA suggère de réserver un appel avec un lead.</p>
                </div>
              </div>
              <div className="flex gap-3 mt-6">
                <button onClick={() => setStep(1)}
                  className="flex-1 py-2.5 border border-slate-700 hover:border-slate-600 rounded-xl text-sm transition-colors">
                  ← Retour
                </button>
                <button onClick={() => setStep(3)} disabled={!form.offer_description}
                  className="flex-1 py-2.5 bg-brand-500 hover:bg-brand-400 shadow-glow-brand hover:shadow-glow-brand-lg disabled:opacity-40 disabled:shadow-none rounded-xl text-sm font-semibold transition-colors">
                  Continuer →
                </button>
              </div>
            </>
          )}

          {/* ── Étape 3 : Intégrations ── */}
          {step === 3 && (
            <>
              <h1 className="font-heading text-lg font-semibold mb-1">Connectez vos outils</h1>
              <p className="text-xs text-slate-500 mb-6">Facultatif — vous pouvez les ajouter plus tard dans les Paramètres.</p>
              <div className="space-y-4">
                <div>
                  <label className="block text-xs text-slate-400 mb-1.5">Airtable Base ID</label>
                  <input value={form.airtable_base_id} onChange={set("airtable_base_id")}
                    className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2.5 text-sm font-mono focus:outline-none focus:border-brand-500"
                    placeholder="appfdB2W41J5sVZ2U" />
                </div>
                <div>
                  <label className="block text-xs text-slate-400 mb-1.5">Jeton d'accès personnel Airtable</label>
                  <input type="password" value={form.airtable_api_key} onChange={set("airtable_api_key")}
                    className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:border-brand-500"
                    placeholder="pat••••••••••••••••" />
                  <p className="text-xs text-slate-600 mt-1">airtable.com/create/tokens — nécessite la portée data.records:read + write</p>
                </div>
                <div>
                  <label className="block text-xs text-slate-400 mb-1.5">Clé API Apify <span className="text-slate-600">(pour le scraping Instagram/TikTok)</span></label>
                  <input type="password" value={form.apify_api_key} onChange={set("apify_api_key")}
                    className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:border-brand-500"
                    placeholder="apify_api_••••••••" />
                </div>
              </div>
              {error && <p className="text-red-400 text-xs mt-4 bg-red-950/40 border border-red-900/40 rounded-lg px-3 py-2">{error}</p>}
              <div className="flex gap-3 mt-6">
                <button onClick={() => setStep(2)}
                  className="flex-1 py-2.5 border border-slate-700 hover:border-slate-600 rounded-xl text-sm transition-colors">
                  ← Retour
                </button>
                <button onClick={finish} disabled={saving}
                  className="flex-1 py-2.5 bg-brand-500 hover:bg-brand-400 shadow-glow-brand hover:shadow-glow-brand-lg disabled:opacity-50 rounded-xl text-sm font-semibold transition-colors">
                  {saving ? "Enregistrement…" : "Accéder au tableau de bord →"}
                </button>
              </div>
              <button onClick={finish} className="w-full text-center text-xs text-slate-600 hover:text-slate-400 mt-3 transition-colors">
                Passer pour l'instant
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
