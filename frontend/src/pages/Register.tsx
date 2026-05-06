import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { authApi } from "../lib/api";

export default function Register() {
  const nav = useNavigate();
  const [form, setForm] = useState({ name: "", email: "", password: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (form.password.length < 8) { setError("Password must be at least 8 characters."); return; }
    setError(""); setLoading(true);
    try {
      const { data } = await authApi.register(form);
      localStorage.setItem("ll_token", data.access_token);
      localStorage.setItem("ll_name", data.name);
      nav("/onboarding", { replace: true });
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Registration failed.");
    } finally { setLoading(false); }
  }

  const set = (k: string) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm(f => ({ ...f, [k]: e.target.value }));

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-950 px-4">
      <div className="w-full max-w-sm">
        <Link to="/" className="block text-center font-extrabold text-xl mb-8">
          Lean<span className="text-sky-400">Lead</span>
        </Link>
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-8 animate-fade-in">
          <h1 className="text-lg font-semibold mb-1">Create your account</h1>
          <p className="text-xs text-slate-500 mb-6">Free — no credit card needed.</p>
          <form onSubmit={submit} className="space-y-4">
            {[
              { label:"Your name", key:"name", type:"text", ph:"Alex Coach" },
              { label:"Email", key:"email", type:"email", ph:"you@example.com" },
              { label:"Password", key:"password", type:"password", ph:"Min. 8 characters" },
            ].map(({ label, key, type, ph }) => (
              <div key={key}>
                <label className="block text-xs text-slate-400 mb-1">{label}</label>
                <input type={type} required value={(form as any)[key]} onChange={set(key)}
                  className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:border-sky-500 transition-colors"
                  placeholder={ph} />
              </div>
            ))}
            {error && <p className="text-red-400 text-xs bg-red-950/40 border border-red-900/40 rounded-lg px-3 py-2">{error}</p>}
            <button type="submit" disabled={loading}
              className="w-full py-2.5 bg-sky-500 hover:bg-sky-400 disabled:opacity-50 rounded-xl text-sm font-semibold transition-colors">
              {loading ? "Creating account…" : "Create account →"}
            </button>
          </form>
          <p className="text-center text-xs text-slate-500 mt-5">
            Already have an account?{" "}
            <Link to="/login" className="text-sky-400 hover:underline">Sign in</Link>
          </p>
        </div>
      </div>
    </div>
  );
}
