import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { authApi } from "../lib/api";

const STEPS = ["Your niche", "Your offer", "Integrations"];

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
  const [form, setForm] = useState({
    niche: "", offer_description: "", target_audience: "",
    calendly_link: "",
    airtable_base_id: "appfdB2W41J5sVZ2U", airtable_api_key: "", apify_api_key: "",
  });

  const set = (k: string) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
    setForm(f => ({ ...f, [k]: e.target.value }));

  async function finish() {
    setSaving(true); setError("");
    try {
      await authApi.onboard(form);
      nav("/dashboard", { replace: true });
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Failed to save. Try again.");
    } finally { setSaving(false); }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-950 px-4 py-12">
      <div className="w-full max-w-lg">
        {/* Progress */}
        <div className="flex items-center justify-center gap-3 mb-8">
          {STEPS.map((label, i) => (
            <div key={label} className="flex items-center gap-3">
              <Step n={i + 1} label={label} active={i === step} done={i < step} />
              {i < STEPS.length - 1 && (
                <div className={`w-12 h-px transition-all ${i < step ? "bg-brand-500" : "bg-slate-800"}`} />
              )}
            </div>
          ))}
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-8 animate-fade-in">
          {/* ── Step 0: Niche ── */}
          {step === 0 && (
            <>
              <h1 className="text-lg font-semibold mb-1">What do you coach?</h1>
              <p className="text-xs text-slate-500 mb-6">The AI uses this to score leads and personalize every message.</p>
              <div className="space-y-5">
                <div>
                  <label className="block text-xs text-slate-400 mb-1.5">Your coaching niche *</label>
                  <input value={form.niche} onChange={set("niche")}
                    className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:border-brand-500"
                    placeholder="e.g. Business coaching for online entrepreneurs" />
                </div>
                <div>
                  <label className="block text-xs text-slate-400 mb-1.5">Who is your ideal client? *</label>
                  <textarea value={form.target_audience} onChange={set("target_audience")} rows={3}
                    className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:border-brand-500 resize-none"
                    placeholder="e.g. Online coaches who want to land 5 premium clients in 90 days without paid ads…" />
                </div>
              </div>
              <button onClick={() => setStep(1)} disabled={!form.niche || !form.target_audience}
                className="mt-6 w-full py-2.5 bg-brand-500 hover:bg-brand-400 disabled:opacity-40 rounded-xl text-sm font-semibold transition-colors">
                Continue →
              </button>
            </>
          )}

          {/* ── Step 1: Offer ── */}
          {step === 1 && (
            <>
              <h1 className="text-lg font-semibold mb-1">Describe your offer</h1>
              <p className="text-xs text-slate-500 mb-6">The AI writes DMs that speak directly to this transformation.</p>
              <div className="space-y-5">
                <div>
                  <label className="block text-xs text-slate-400 mb-1.5">What transformation do you deliver? *</label>
                  <textarea value={form.offer_description} onChange={set("offer_description")} rows={4}
                    className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:border-brand-500 resize-none"
                    placeholder="e.g. I help online coaches land their first 5 premium clients in 90 days through a proven DM strategy, without paid ads." />
                </div>
                <div>
                  <label className="block text-xs text-slate-400 mb-1.5">Calendly / booking link</label>
                  <input value={form.calendly_link} onChange={set("calendly_link")}
                    className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:border-brand-500"
                    placeholder="https://calendly.com/yourname/30min" />
                  <p className="text-xs text-slate-600 mt-1">Used when the AI suggests booking a call with a lead.</p>
                </div>
              </div>
              <div className="flex gap-3 mt-6">
                <button onClick={() => setStep(0)}
                  className="flex-1 py-2.5 border border-slate-700 hover:border-slate-600 rounded-xl text-sm transition-colors">
                  ← Back
                </button>
                <button onClick={() => setStep(2)} disabled={!form.offer_description}
                  className="flex-1 py-2.5 bg-brand-500 hover:bg-brand-400 disabled:opacity-40 rounded-xl text-sm font-semibold transition-colors">
                  Continue →
                </button>
              </div>
            </>
          )}

          {/* ── Step 2: Integrations ── */}
          {step === 2 && (
            <>
              <h1 className="text-lg font-semibold mb-1">Connect your tools</h1>
              <p className="text-xs text-slate-500 mb-6">Optional — you can add these later in Settings.</p>
              <div className="space-y-4">
                <div>
                  <label className="block text-xs text-slate-400 mb-1.5">Airtable Base ID</label>
                  <input value={form.airtable_base_id} onChange={set("airtable_base_id")}
                    className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2.5 text-sm font-mono focus:outline-none focus:border-brand-500"
                    placeholder="appfdB2W41J5sVZ2U" />
                </div>
                <div>
                  <label className="block text-xs text-slate-400 mb-1.5">Airtable Personal Access Token</label>
                  <input type="password" value={form.airtable_api_key} onChange={set("airtable_api_key")}
                    className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:border-brand-500"
                    placeholder="pat••••••••••••••••" />
                  <p className="text-xs text-slate-600 mt-1">airtable.com/create/tokens — needs data.records:read + write scope</p>
                </div>
                <div>
                  <label className="block text-xs text-slate-400 mb-1.5">Apify API Key <span className="text-slate-600">(for Instagram/TikTok scraping)</span></label>
                  <input type="password" value={form.apify_api_key} onChange={set("apify_api_key")}
                    className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:border-brand-500"
                    placeholder="apify_api_••••••••" />
                </div>
              </div>
              {error && <p className="text-red-400 text-xs mt-4 bg-red-950/40 border border-red-900/40 rounded-lg px-3 py-2">{error}</p>}
              <div className="flex gap-3 mt-6">
                <button onClick={() => setStep(1)}
                  className="flex-1 py-2.5 border border-slate-700 hover:border-slate-600 rounded-xl text-sm transition-colors">
                  ← Back
                </button>
                <button onClick={finish} disabled={saving}
                  className="flex-1 py-2.5 bg-brand-500 hover:bg-brand-400 disabled:opacity-50 rounded-xl text-sm font-semibold transition-colors">
                  {saving ? "Saving…" : "Launch dashboard →"}
                </button>
              </div>
              <button onClick={finish} className="w-full text-center text-xs text-slate-600 hover:text-slate-400 mt-3 transition-colors">
                Skip for now
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
