import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { authApi } from "../lib/api";

const steps = ["Your niche", "Your offer", "Integrations"];

export default function Onboarding() {
  const nav = useNavigate();
  const [step, setStep] = useState(0);
  const [form, setForm] = useState({
    niche: "",
    offer_description: "",
    target_audience: "",
    calendly_link: "",
    airtable_base_id: "appfdB2W41J5sVZ2U",
    airtable_api_key: "",
    apify_api_key: "",
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  function set(key: string, value: string) {
    setForm((f) => ({ ...f, [key]: value }));
  }

  async function finish() {
    setLoading(true);
    setError("");
    try {
      await authApi.onboard(form);
      nav("/dashboard", { replace: true });
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Something went wrong.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-950 px-4">
      <div className="w-full max-w-lg">
        {/* Progress */}
        <div className="flex items-center gap-2 justify-center mb-8">
          {steps.map((s, i) => (
            <div key={s} className="flex items-center gap-2">
              <div
                className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold border transition-all ${
                  i < step
                    ? "bg-sky-500 border-sky-500 text-white"
                    : i === step
                    ? "border-sky-500 text-sky-400"
                    : "border-slate-700 text-slate-600"
                }`}
              >
                {i < step ? "✓" : i + 1}
              </div>
              {i < steps.length - 1 && (
                <div className={`w-10 h-px ${i < step ? "bg-sky-500" : "bg-slate-800"}`} />
              )}
            </div>
          ))}
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-8">
          {/* Step 0 – Niche */}
          {step === 0 && (
            <>
              <h1 className="text-lg font-semibold mb-1">What do you coach?</h1>
              <p className="text-xs text-slate-500 mb-6">
                This helps the AI qualify leads that are the right fit for you.
              </p>
              <div className="space-y-4">
                <div>
                  <label className="block text-xs text-slate-400 mb-1">Your coaching niche</label>
                  <input
                    value={form.niche}
                    onChange={(e) => set("niche", e.target.value)}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:border-sky-500"
                    placeholder="e.g. Business coaching for online entrepreneurs"
                  />
                </div>
                <div>
                  <label className="block text-xs text-slate-400 mb-1">Who is your ideal client?</label>
                  <textarea
                    value={form.target_audience}
                    onChange={(e) => set("target_audience", e.target.value)}
                    rows={3}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:border-sky-500 resize-none"
                    placeholder="e.g. Coaches and consultants who want to scale past $10k/month..."
                  />
                </div>
              </div>
              <button
                onClick={() => setStep(1)}
                disabled={!form.niche || !form.target_audience}
                className="mt-6 w-full py-2.5 bg-sky-500 hover:bg-sky-400 disabled:opacity-40 rounded-lg text-sm font-medium transition-colors"
              >
                Next →
              </button>
            </>
          )}

          {/* Step 1 – Offer */}
          {step === 1 && (
            <>
              <h1 className="text-lg font-semibold mb-1">Describe your offer</h1>
              <p className="text-xs text-slate-500 mb-6">
                The AI uses this to write outreach messages and qualify leads.
              </p>
              <div className="space-y-4">
                <div>
                  <label className="block text-xs text-slate-400 mb-1">
                    What transformation do you offer? (1-2 sentences)
                  </label>
                  <textarea
                    value={form.offer_description}
                    onChange={(e) => set("offer_description", e.target.value)}
                    rows={4}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:border-sky-500 resize-none"
                    placeholder="e.g. I help online coaches land their first 5 premium clients in 90 days through a proven DM strategy, without paid ads."
                  />
                </div>
                <div>
                  <label className="block text-xs text-slate-400 mb-1">
                    Calendly / booking link (optional)
                  </label>
                  <input
                    value={form.calendly_link}
                    onChange={(e) => set("calendly_link", e.target.value)}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:border-sky-500"
                    placeholder="https://calendly.com/yourname/30min"
                  />
                </div>
              </div>
              <div className="flex gap-3 mt-6">
                <button
                  onClick={() => setStep(0)}
                  className="flex-1 py-2.5 border border-slate-700 hover:border-slate-600 rounded-lg text-sm transition-colors"
                >
                  ← Back
                </button>
                <button
                  onClick={() => setStep(2)}
                  disabled={!form.offer_description}
                  className="flex-1 py-2.5 bg-sky-500 hover:bg-sky-400 disabled:opacity-40 rounded-lg text-sm font-medium transition-colors"
                >
                  Next →
                </button>
              </div>
            </>
          )}

          {/* Step 2 – Integrations */}
          {step === 2 && (
            <>
              <h1 className="text-lg font-semibold mb-1">Connect your tools</h1>
              <p className="text-xs text-slate-500 mb-6">
                Optional — you can skip and add these later in settings.
              </p>
              <div className="space-y-4">
                <div>
                  <label className="block text-xs text-slate-400 mb-1">Airtable Base ID</label>
                  <input
                    value={form.airtable_base_id}
                    onChange={(e) => set("airtable_base_id", e.target.value)}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:border-sky-500 font-mono"
                    placeholder="appfdB2W41J5sVZ2U"
                  />
                </div>
                <div>
                  <label className="block text-xs text-slate-400 mb-1">Airtable Personal Access Token</label>
                  <input
                    type="password"
                    value={form.airtable_api_key}
                    onChange={(e) => set("airtable_api_key", e.target.value)}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:border-sky-500"
                    placeholder="pat•••••••••••••••"
                  />
                </div>
                <div>
                  <label className="block text-xs text-slate-400 mb-1">Apify API Key (for scraping)</label>
                  <input
                    type="password"
                    value={form.apify_api_key}
                    onChange={(e) => set("apify_api_key", e.target.value)}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:border-sky-500"
                    placeholder="apify_api_•••••••••"
                  />
                </div>
              </div>
              {error && <p className="text-red-400 text-xs mt-3">{error}</p>}
              <div className="flex gap-3 mt-6">
                <button
                  onClick={() => setStep(1)}
                  className="flex-1 py-2.5 border border-slate-700 hover:border-slate-600 rounded-lg text-sm transition-colors"
                >
                  ← Back
                </button>
                <button
                  onClick={finish}
                  disabled={loading}
                  className="flex-1 py-2.5 bg-sky-500 hover:bg-sky-400 disabled:opacity-50 rounded-lg text-sm font-medium transition-colors"
                >
                  {loading ? "Saving…" : "Launch dashboard →"}
                </button>
              </div>
              <button
                onClick={finish}
                className="w-full text-center text-xs text-slate-600 hover:text-slate-400 mt-3 transition-colors"
              >
                Skip integrations for now
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
