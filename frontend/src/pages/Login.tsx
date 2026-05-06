import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { authApi } from "../lib/api";

export default function Login() {
  const nav = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(""); setLoading(true);
    try {
      const { data } = await authApi.login(email, password);
      localStorage.setItem("ll_token", data.access_token);
      localStorage.setItem("ll_name", data.name);
      nav(data.onboarded ? "/dashboard" : "/onboarding", { replace: true });
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Invalid email or password.");
    } finally { setLoading(false); }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-950 px-4">
      <div className="w-full max-w-sm">
        <Link to="/" className="block text-center font-extrabold text-xl mb-8">
          Lean<span className="text-brand-400">Lead</span>
        </Link>
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-8 animate-fade-in">
          <h1 className="text-lg font-semibold mb-6">Welcome back</h1>
          <form onSubmit={submit} className="space-y-4">
            <div>
              <label className="block text-xs text-slate-400 mb-1">Email</label>
              <input type="email" required value={email} onChange={e => setEmail(e.target.value)}
                className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:border-brand-500 transition-colors"
                placeholder="you@example.com" />
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Password</label>
              <input type="password" required value={password} onChange={e => setPassword(e.target.value)}
                className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:border-brand-500 transition-colors"
                placeholder="••••••••" />
            </div>
            {error && <p className="text-red-400 text-xs bg-red-950/40 border border-red-900/40 rounded-lg px-3 py-2">{error}</p>}
            <button type="submit" disabled={loading}
              className="w-full py-2.5 bg-brand-500 hover:bg-brand-400 disabled:opacity-50 rounded-xl text-sm font-semibold transition-colors">
              {loading ? "Signing in…" : "Sign in"}
            </button>
          </form>
          <p className="text-center text-xs text-slate-500 mt-5">
            No account?{" "}
            <Link to="/register" className="text-brand-400 hover:underline">Create one free</Link>
          </p>
        </div>
      </div>
    </div>
  );
}
