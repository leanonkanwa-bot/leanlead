import { Link } from "react-router-dom";

export default function Landing() {
  return (
    <div className="min-h-screen bg-slate-950 text-white">
      {/* Nav */}
      <nav className="flex items-center justify-between px-6 py-4 border-b border-slate-800">
        <span className="text-xl font-bold text-sky-400">LeanLead</span>
        <div className="flex gap-3">
          <Link to="/login" className="px-4 py-2 text-sm text-slate-300 hover:text-white transition-colors">
            Log in
          </Link>
          <Link
            to="/register"
            className="px-4 py-2 text-sm bg-sky-500 hover:bg-sky-400 rounded-lg font-medium transition-colors"
          >
            Get started free
          </Link>
        </div>
      </nav>

      {/* Hero */}
      <section className="max-w-4xl mx-auto px-6 pt-24 pb-20 text-center">
        <div className="inline-flex items-center gap-2 bg-sky-950 border border-sky-800 text-sky-400 text-xs px-3 py-1 rounded-full mb-8">
          ✦ AI-powered lead gen for online coaches
        </div>
        <h1 className="text-5xl font-extrabold leading-tight mb-6">
          Turn cold profiles into{" "}
          <span className="text-sky-400">booked calls</span>
          <br />on autopilot.
        </h1>
        <p className="text-lg text-slate-400 max-w-2xl mx-auto mb-10">
          LeanLead qualifies leads, writes personalized DMs, and handles replies —
          so you spend time on coaching, not cold outreach.
        </p>
        <Link
          to="/register"
          className="inline-block px-8 py-4 bg-sky-500 hover:bg-sky-400 rounded-xl text-lg font-semibold transition-colors shadow-lg shadow-sky-900"
        >
          Start for free →
        </Link>
      </section>

      {/* Features */}
      <section className="max-w-5xl mx-auto px-6 py-16 grid sm:grid-cols-3 gap-8">
        {[
          {
            icon: "🎯",
            title: "AI Lead Qualifier",
            desc: "Claude scores every lead 1-10 against your niche and filters out time-wasters automatically.",
          },
          {
            icon: "✍️",
            title: "Personalized DMs",
            desc: "One-click outreach messages that sound human — referencing the lead's actual bio and pain points.",
          },
          {
            icon: "📋",
            title: "Kanban Pipeline",
            desc: "Visual board from New → Qualified → Messaged → Replied → Booked. Drag and drop to update.",
          },
        ].map((f) => (
          <div key={f.title} className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
            <div className="text-3xl mb-3">{f.icon}</div>
            <h3 className="font-semibold text-white mb-2">{f.title}</h3>
            <p className="text-sm text-slate-400 leading-relaxed">{f.desc}</p>
          </div>
        ))}
      </section>

      {/* How it works */}
      <section className="max-w-3xl mx-auto px-6 py-16">
        <h2 className="text-2xl font-bold text-center mb-12">How it works</h2>
        <div className="space-y-6">
          {[
            { step: "1", title: "Add a lead", desc: "Paste their Instagram handle, bio, and follower count." },
            { step: "2", title: "Qualify with AI", desc: "Claude scores them against your niche and surfaces their pain points." },
            { step: "3", title: "Generate a DM", desc: "One click writes a personalized, non-spammy outreach message." },
            { step: "4", title: "Track replies", desc: "Log their response and get a suggested reply that moves toward a call." },
            { step: "5", title: "Sync to Airtable", desc: "Every lead and message stays in your CRM automatically." },
          ].map((s) => (
            <div key={s.step} className="flex gap-5 items-start">
              <div className="w-9 h-9 shrink-0 bg-sky-900 text-sky-400 rounded-full flex items-center justify-center text-sm font-bold">
                {s.step}
              </div>
              <div>
                <div className="font-medium text-white">{s.title}</div>
                <div className="text-sm text-slate-400 mt-0.5">{s.desc}</div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section className="text-center py-20 px-6">
        <h2 className="text-3xl font-bold mb-4">Ready to fill your calendar?</h2>
        <p className="text-slate-400 mb-8">Free to start. No credit card required.</p>
        <Link
          to="/register"
          className="inline-block px-8 py-4 bg-sky-500 hover:bg-sky-400 rounded-xl text-lg font-semibold transition-colors"
        >
          Create your free account →
        </Link>
      </section>

      <footer className="text-center text-xs text-slate-600 py-6 border-t border-slate-900">
        © {new Date().getFullYear()} LeanLead. Built for coaches who close.
      </footer>
    </div>
  );
}
