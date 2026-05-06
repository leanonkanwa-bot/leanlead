import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { authApi } from "../lib/api";

export default function Settings() {
  const nav = useNavigate();
  const qc = useQueryClient();

  const { data: coach } = useQuery({
    queryKey: ["me"],
    queryFn: () => authApi.me().then(r => r.data),
  });

  const [form, setForm] = useState({
    niche: "", offer_description: "", target_audience: "",
    calendly_link: "", apify_api_key: "",
  });
  const [initialized, setInitialized] = useState(false);

  if (coach && !initialized) {
    setForm({
      niche: coach.niche || "",
      offer_description: coach.offer_description || "",
      target_audience: coach.target_audience || "",
      calendly_link: coach.calendly_link || "",
      apify_api_key: "",
    });
    setInitialized(true);
  }

  const set = (k: string) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
    setForm(f => ({ ...f, [k]: e.target.value }));

  const save = useMutation({
    mutationFn: () => {
      const payload: Record<string, string> = {
        niche: form.niche,
        offer_description: form.offer_description,
        target_audience: form.target_audience,
        calendly_link: form.calendly_link,
      };
      if (form.apify_api_key) payload.apify_api_key = form.apify_api_key;
      return authApi.updateSettings(payload);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["me"] });
      setForm(f => ({ ...f, apify_api_key: "" }));
    },
  });

  return (
    <div className="min-h-screen bg-slate-950 px-4 py-10">
      <div className="max-w-xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <Link to="/dashboard" className="text-slate-500 hover:text-white text-sm transition-colors">
            ← Retour au tableau de bord
          </Link>
          <span className="font-extrabold text-lg">
            Lean<span className="text-brand-400">Lead</span>
          </span>
        </div>

        <h1 className="text-xl font-semibold text-white mb-6">Paramètres</h1>

        <div className="space-y-5">
          {/* Coaching info */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
            <h2 className="text-sm font-semibold text-white mb-4">Informations de coaching</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-xs text-slate-400 mb-1.5">Créneau de coaching</label>
                <input value={form.niche} onChange={set("niche")}
                  className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:border-brand-500 transition-colors"
                  placeholder="ex. Coaching business pour entrepreneurs en ligne" />
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1.5">Client idéal</label>
                <textarea value={form.target_audience} onChange={set("target_audience")} rows={3}
                  className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:border-brand-500 transition-colors resize-none"
                  placeholder="ex. Coachs en ligne souhaitant décrocher 5 clients premium en 90 jours…" />
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1.5">Description de l'offre</label>
                <textarea value={form.offer_description} onChange={set("offer_description")} rows={3}
                  className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:border-brand-500 transition-colors resize-none"
                  placeholder="ex. J'aide les coachs à décrocher leurs 5 premiers clients premium en 90 jours…" />
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1.5">Lien Calendly</label>
                <input value={form.calendly_link} onChange={set("calendly_link")}
                  className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:border-brand-500 transition-colors"
                  placeholder="https://calendly.com/yourname/30min" />
              </div>
            </div>
          </div>

          {/* API keys */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
            <h2 className="text-sm font-semibold text-white mb-1">Intégrations</h2>
            <p className="text-xs text-slate-500 mb-4">Vos clés sont stockées en sécurité et utilisées uniquement pour votre compte.</p>
            <div>
              <label className="block text-xs text-slate-400 mb-1.5">
                Clé API Apify
                {coach?.has_apify_key && (
                  <span className="ml-2 text-emerald-400">✓ configurée</span>
                )}
              </label>
              <input
                type="password"
                value={form.apify_api_key}
                onChange={set("apify_api_key")}
                className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:border-brand-500 transition-colors"
                placeholder={coach?.has_apify_key ? "Entrez une nouvelle clé pour remplacer" : "apify_api_••••••••"}
              />
              <p className="text-xs text-slate-600 mt-1">
                console.apify.com → Paramètres → Clés API. Requis pour le scraping Instagram et TikTok.
              </p>
            </div>
          </div>

          {/* Save */}
          {save.isError && (
            <p className="text-red-400 text-xs bg-red-950/40 border border-red-900/40 rounded-lg px-3 py-2">
              {(save.error as any)?.response?.data?.detail || "Échec de l'enregistrement."}
            </p>
          )}
          {save.isSuccess && (
            <p className="text-emerald-400 text-xs bg-emerald-950/40 border border-emerald-900/40 rounded-lg px-3 py-2">
              ✓ Paramètres enregistrés.
            </p>
          )}
          <button
            onClick={() => save.mutate()}
            disabled={save.isPending}
            className="w-full py-3 bg-brand-500 hover:bg-brand-400 disabled:opacity-50 rounded-xl text-sm font-semibold transition-colors">
            {save.isPending ? "Enregistrement…" : "Enregistrer les paramètres"}
          </button>
        </div>
      </div>
    </div>
  );
}
