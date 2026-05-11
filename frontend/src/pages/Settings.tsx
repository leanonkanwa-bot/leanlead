import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { authApi, type Testimonial } from "../lib/api";

const Field = ({ label, children }: { label: string; children: React.ReactNode }) => (
  <div>
    <label className="block text-xs font-medium text-slate-400 mb-1.5 tracking-wide">{label}</label>
    {children}
  </div>
);

export default function Settings() {
  const qc = useQueryClient();
  const { data: coach, isLoading } = useQuery({
    queryKey: ["me"],
    queryFn: () => authApi.me().then(r => r.data),
  });

  const [form, setForm] = useState({
    niche: "", offer_description: "", target_audience: "", calendly_link: "",
  });
  const [apifyKey, setApifyKey] = useState("");
  const [saved, setSaved] = useState(false);
  const [testimonials, setTestimonials] = useState<Testimonial[]>([]);
  const [newT, setNewT] = useState<Testimonial>({ name: "", situation: "", result: "" });
  const [testimonialSaved, setTestimonialSaved] = useState(false);

  useEffect(() => {
    if (coach) {
      setForm({
        niche:             coach.niche             || "",
        offer_description: coach.offer_description || "",
        target_audience:   coach.target_audience   || "",
        calendly_link:     coach.calendly_link     || "",
      });
      setTestimonials(coach.testimonials || []);
    }
  }, [coach]);

  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
    setForm(f => ({ ...f, [k]: e.target.value }));

  const save = useMutation({
    mutationFn: () => {
      const payload: Record<string, unknown> = { ...form };
      if (apifyKey) payload.apify_api_key = apifyKey;
      return authApi.updateSettings(payload as Parameters<typeof authApi.updateSettings>[0]);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["me"] });
      setApifyKey("");
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    },
  });

  const saveTestimonials = useMutation({
    mutationFn: () => authApi.updateSettings({ testimonials }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["me"] });
      setTestimonialSaved(true);
      setTimeout(() => setTestimonialSaved(false), 2000);
    },
  });

  function addTestimonial() {
    if (!newT.situation && !newT.result) return;
    setTestimonials(t => [...t, { ...newT, name: newT.name || "Client anonyme" }]);
    setNewT({ name: "", situation: "", result: "" });
  }

  const inputCls = "w-full bg-slate-900 border border-[#2a2a2a] rounded-xl px-3 py-2.5 text-sm text-slate-100 placeholder-slate-600 focus:outline-none focus:border-brand-500 focus:shadow-glow-sm transition-all duration-150";

  return (
    <div className="min-h-screen bg-slate-950" style={{ backgroundImage: "radial-gradient(ellipse 80% 50% at 50% -20%, rgba(255,117,31,0.05), transparent)" }}>
      <div className="max-w-xl mx-auto px-4 py-10">
        {/* Header */}
        <div className="flex items-center justify-between mb-10">
          <Link to="/dashboard" className="flex items-center gap-1.5 text-slate-500 hover:text-slate-300 text-sm transition-colors">
            ← Tableau de bord
          </Link>
          <span className="font-heading font-extrabold text-lg tracking-tight">
            Lean<span className="text-brand-400">Lead</span>
          </span>
        </div>

        <h1 className="font-heading text-2xl font-bold text-white mb-1">Paramètres</h1>
        <p className="text-sm text-slate-500 mb-8">Personnalisez votre profil et vos intégrations.</p>

        {isLoading ? (
          <div className="space-y-4 animate-pulse">
            {[1,2,3].map(i => <div key={i} className="h-24 bg-slate-900 rounded-2xl" />)}
          </div>
        ) : (
          <div className="space-y-4">
            {/* Coaching info */}
            <div className="bg-[#1a1a1a] border border-[#2a2a2a] rounded-2xl p-6">
              <p className="font-heading text-sm font-semibold text-white mb-5">Profil de coaching</p>
              <div className="space-y-4">
                <Field label="Votre créneau">
                  <input value={form.niche} onChange={set("niche")} className={inputCls}
                    placeholder="ex. Coaching business pour entrepreneurs en ligne" />
                </Field>
                <Field label="Client idéal">
                  <textarea value={form.target_audience} onChange={set("target_audience")} rows={3}
                    className={inputCls + " resize-none"}
                    placeholder="ex. Coachs en ligne souhaitant décrocher 5 clients premium en 90 jours…" />
                </Field>
                <Field label="Transformation que vous apportez">
                  <textarea value={form.offer_description} onChange={set("offer_description")} rows={3}
                    className={inputCls + " resize-none"}
                    placeholder="ex. J'aide les coachs à décrocher leurs 5 premiers clients premium en 90 jours…" />
                </Field>
                <Field label="Lien Calendly">
                  <input value={form.calendly_link} onChange={set("calendly_link")} className={inputCls}
                    placeholder="https://calendly.com/yourname/30min" />
                </Field>
              </div>
            </div>

            {/* Social Proof Testimonials */}
            <div className="bg-[#1a1a1a] border border-[#2a2a2a] rounded-2xl p-6">
              <p className="font-heading text-sm font-semibold text-white mb-1">Témoignages clients</p>
              <p className="text-[11px] text-slate-500 mb-4">
                L'IA référence naturellement le témoignage le plus pertinent dans les DMs pour augmenter la confiance.
              </p>

              {/* Existing testimonials */}
              {testimonials.length > 0 && (
                <div className="space-y-2 mb-4">
                  {testimonials.map((t, i) => (
                    <div key={i} className="bg-slate-900 border border-[#2a2a2a] rounded-xl px-4 py-3 flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <p className="text-xs font-semibold text-slate-200 truncate">{t.name}</p>
                        <p className="text-[11px] text-slate-500 mt-0.5 truncate">
                          {t.situation} → {t.result}
                        </p>
                      </div>
                      <button
                        onClick={() => setTestimonials(ts => ts.filter((_, j) => j !== i))}
                        className="text-slate-600 hover:text-red-400 text-lg leading-none flex-shrink-0 transition-colors"
                      >×</button>
                    </div>
                  ))}
                </div>
              )}

              {/* Add new testimonial */}
              <div className="space-y-2 border border-dashed border-slate-700/50 rounded-xl p-3">
                <p className="text-[10px] text-slate-600 font-medium">Ajouter un témoignage</p>
                <input
                  value={newT.name}
                  onChange={e => setNewT(t => ({ ...t, name: e.target.value }))}
                  placeholder="Prénom du client (ex. Sarah)"
                  className="w-full bg-slate-900 border border-[#2a2a2a] rounded-xl px-3 py-2 text-xs focus:outline-none focus:border-brand-500 transition-colors text-slate-200 placeholder-slate-600"
                />
                <input
                  value={newT.situation}
                  onChange={e => setNewT(t => ({ ...t, situation: e.target.value }))}
                  placeholder="Situation initiale (ex. coach sans clients, stressée, 2 ans d'échecs)"
                  className="w-full bg-slate-900 border border-[#2a2a2a] rounded-xl px-3 py-2 text-xs focus:outline-none focus:border-brand-500 transition-colors text-slate-200 placeholder-slate-600"
                />
                <input
                  value={newT.result}
                  onChange={e => setNewT(t => ({ ...t, result: e.target.value }))}
                  placeholder="Résultat obtenu (ex. 5 clients premium en 60 jours, +8k€/mois)"
                  className="w-full bg-slate-900 border border-[#2a2a2a] rounded-xl px-3 py-2 text-xs focus:outline-none focus:border-brand-500 transition-colors text-slate-200 placeholder-slate-600"
                />
                <button
                  onClick={addTestimonial}
                  disabled={!newT.situation && !newT.result}
                  className="w-full py-2 bg-slate-800 hover:bg-slate-700 disabled:opacity-40 rounded-xl text-xs font-medium text-slate-300 transition-colors"
                >
                  + Ajouter
                </button>
              </div>

              {testimonials.length > 0 && (
                <button
                  onClick={() => saveTestimonials.mutate()}
                  disabled={saveTestimonials.isPending}
                  className="mt-3 w-full py-2 bg-brand-500/20 hover:bg-brand-500/30 border border-brand-500/30 text-brand-400 text-xs rounded-xl transition-colors disabled:opacity-40"
                >
                  {testimonialSaved ? "✓ Sauvegardé" : saveTestimonials.isPending ? "Enregistrement…" : "Enregistrer les témoignages"}
                </button>
              )}
            </div>

            {/* Account info */}
            <div className="bg-[#1a1a1a] border border-[#2a2a2a] rounded-2xl p-6">
              <p className="font-heading text-sm font-semibold text-white mb-4">Compte</p>
              <div className="flex items-center justify-between py-2 border-b border-[#2a2a2a]">
                <span className="text-xs text-slate-500">Nom</span>
                <span className="text-sm text-slate-300">{coach?.name}</span>
              </div>
              <div className="flex items-center justify-between py-2">
                <span className="text-xs text-slate-500">E-mail</span>
                <span className="text-sm text-slate-300">{coach?.email}</span>
              </div>
            </div>

            {/* Save */}
            {save.isError && (
              <p className="text-red-400 text-xs bg-red-950/40 border border-red-900/40 rounded-xl px-4 py-3">
                {(save.error as any)?.response?.data?.detail || "Échec de l'enregistrement."}
              </p>
            )}
            {saved && (
              <p className="text-emerald-400 text-xs bg-emerald-950/30 border border-emerald-900/40 rounded-xl px-4 py-3">
                ✓ Paramètres enregistrés avec succès.
              </p>
            )}

            <button onClick={() => save.mutate()} disabled={save.isPending}
              className="w-full py-3 bg-brand-500 hover:bg-brand-400 shadow-glow-brand hover:shadow-glow-brand-lg disabled:opacity-40 disabled:shadow-none rounded-xl text-sm font-semibold transition-all duration-150">
              {save.isPending ? "Enregistrement…" : "Enregistrer les paramètres"}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
