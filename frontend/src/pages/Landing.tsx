import { Link } from "react-router-dom";

/* ── Tiny atoms ── */
const Chip = ({ children }: { children: React.ReactNode }) => (
  <span className="inline-flex items-center gap-1.5 text-xs bg-brand-950 border border-brand-800/60 text-brand-400 px-3 py-1 rounded-full font-medium">
    {children}
  </span>
);

/* ── Animated kanban preview ── */
function KanbanPreview() {
  const cols = [
    { label: "NEW", color: "border-slate-600", count: 47 },
    { label: "CONTACTED", color: "border-brand-700", count: 28 },
    { label: "REPLIED", color: "border-brand-700", count: 11 },
    { label: "BOOKED", color: "border-emerald-700", count: 6 },
    { label: "CLOSED", color: "border-rose-800", count: 3 },
  ];
  const cards = [
    { name: "Sarah M.", handle: "sarahmfitness", score: 9.1, tag: "weight loss", color: "text-emerald-400" },
    { name: "Jake T.", handle: "jakethomas_biz", score: 7.8, tag: "business", color: "text-amber-400" },
    { name: "Priya K.", handle: "priyak_life", score: 8.5, tag: "mindset", color: "text-emerald-400" },
  ];

  return (
    <div className="relative mx-auto max-w-5xl mt-14 select-none">
      <div className="absolute inset-x-0 top-0 h-40 bg-brand-500/5 blur-3xl rounded-full pointer-events-none" />
      <div className="relative rounded-2xl border border-slate-800 bg-slate-900/80 overflow-hidden shadow-2xl backdrop-blur-sm">
        {/* Window chrome */}
        <div className="flex items-center gap-2 px-4 py-3 border-b border-slate-800 bg-slate-950/50">
          <div className="flex gap-1.5">
            <div className="w-3 h-3 rounded-full bg-red-500/50" />
            <div className="w-3 h-3 rounded-full bg-amber-500/50" />
            <div className="w-3 h-3 rounded-full bg-emerald-500/50" />
          </div>
          <span className="ml-2 text-xs text-slate-600 font-mono">leanlead.app/dashboard</span>
        </div>
        {/* Fake nav */}
        <div className="flex items-center justify-between px-5 py-3 border-b border-slate-800/50">
          <span className="font-bold text-sm text-brand-400">LeanLead</span>
          <div className="flex gap-5 text-xs">
            <span className="text-brand-400 border-b border-brand-500 pb-0.5">Pipeline</span>
            <span className="text-slate-500 hover:text-slate-300">Prospects</span>
            <span className="text-slate-500 hover:text-slate-300">Follow-ups</span>
          </div>
          <div className="text-xs bg-brand-500 text-white px-3 py-1 rounded-lg">+ Add lead</div>
        </div>
        {/* Stats */}
        <div className="flex gap-8 px-5 py-3 border-b border-slate-800/30">
          {[["95", "Total"], ["28", "Contacted"], ["11", "Replied"], ["6", "Booked"], ["6.3%", "Conversion"]].map(([v, l]) => (
            <div key={l}>
              <p className="text-xs text-slate-600">{l}</p>
              <p className="text-base font-bold text-white">{v}</p>
            </div>
          ))}
        </div>
        {/* Kanban */}
        <div className="flex gap-3 p-4 overflow-x-auto">
          {cols.map((col, ci) => (
            <div key={col.label} className={`flex-shrink-0 w-52 rounded-xl border ${col.color} bg-slate-900/40`}>
              <div className="flex justify-between items-center px-3 py-2.5 border-b border-slate-800/50">
                <span className="text-[10px] font-bold text-slate-400 tracking-widest">{col.label}</span>
                <span className="text-[10px] bg-slate-800 text-slate-500 px-1.5 py-0.5 rounded-full">{col.count}</span>
              </div>
              <div className="p-2 space-y-2">
                {ci === 0 ? cards.map(c => (
                  <div key={c.handle} className="bg-slate-800 rounded-lg p-2.5">
                    <div className="flex justify-between mb-1">
                      <div>
                        <p className="text-xs font-medium text-white">{c.name}</p>
                        <p className="text-[10px] text-slate-500">@{c.handle}</p>
                      </div>
                      <span className={`text-[10px] font-mono font-bold ${c.color}`}>{c.score}</span>
                    </div>
                    <span className="text-[9px] bg-brand-950 text-brand-400 px-1.5 py-0.5 rounded-full">{c.tag}</span>
                  </div>
                )) : (
                  <div className="h-14 rounded-lg border border-dashed border-slate-800/80 flex items-center justify-center">
                    <span className="text-[9px] text-slate-700">drop leads here</span>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

/* ── Feature card ── */
const Feature = ({ icon, title, desc }: { icon: string; title: string; desc: string }) => (
  <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 hover:border-brand-900/60 transition-colors">
    <div className="w-10 h-10 bg-brand-950 rounded-xl flex items-center justify-center text-xl mb-4">{icon}</div>
    <h3 className="text-sm font-semibold text-white mb-2">{title}</h3>
    <p className="text-sm text-slate-400 leading-relaxed">{desc}</p>
  </div>
);

/* ── Pricing card ── */
const Pricing = ({
  name, price, sub, features, hot, cta,
}: {
  name: string; price: string; sub?: string; features: string[]; hot?: boolean; cta: string;
}) => (
  <div className={`relative rounded-2xl p-8 border flex flex-col ${hot ? "bg-brand-600 border-brand-500 shadow-2xl shadow-brand-900/40" : "bg-slate-900 border-slate-800"}`}>
    {hot && <span className="absolute -top-3 left-1/2 -translate-x-1/2 bg-amber-400 text-slate-900 text-[10px] font-bold px-3 py-1 rounded-full tracking-wide">MOST POPULAR</span>}
    <p className={`text-xs font-semibold mb-1 ${hot ? "text-brand-100" : "text-slate-400"}`}>{name}</p>
    <div className="flex items-baseline gap-1 mb-1">
      <span className="text-4xl font-black text-white">{price}</span>
      {price !== "Free" && <span className={`text-sm ${hot ? "text-brand-200" : "text-slate-500"}`}>/mo</span>}
    </div>
    {sub && <p className={`text-xs mb-6 ${hot ? "text-brand-100" : "text-slate-500"}`}>{sub}</p>}
    <ul className="space-y-3 flex-1 mb-8">
      {features.map(f => (
        <li key={f} className="flex gap-2 text-sm">
          <span className={hot ? "text-brand-100" : "text-emerald-400"}>✓</span>
          <span className={hot ? "text-brand-50" : "text-slate-300"}>{f}</span>
        </li>
      ))}
    </ul>
    <Link to="/register" className={`text-center py-3 rounded-xl text-sm font-semibold transition-colors ${hot ? "bg-white text-brand-700 hover:bg-brand-50" : "bg-slate-800 text-white hover:bg-slate-700 border border-slate-700"}`}>
      {cta}
    </Link>
  </div>
);

/* ── Main ── */
export default function Landing() {
  return (
    <div className="min-h-screen bg-slate-950 text-white overflow-x-hidden">
      {/* Nav */}
      <nav className="sticky top-0 z-50 flex items-center justify-between px-6 py-4 border-b border-slate-900 bg-slate-950/90 backdrop-blur-md">
        <span className="font-extrabold text-lg">Lean<span className="text-brand-400">Lead</span></span>
        <div className="hidden sm:flex gap-7 text-sm text-slate-400">
          {[["#features","Features"],["#how","How it works"],["#pricing","Pricing"]].map(([h,l]) => (
            <a key={h} href={h} className="hover:text-white transition-colors">{l}</a>
          ))}
        </div>
        <div className="flex gap-3 items-center">
          <Link to="/login" className="text-sm text-slate-400 hover:text-white transition-colors px-2 py-1.5">Log in</Link>
          <Link to="/register" className="text-sm bg-brand-500 hover:bg-brand-400 px-4 py-2 rounded-lg font-medium transition-colors shadow-lg shadow-brand-900/30">Start free</Link>
        </div>
      </nav>

      {/* Hero */}
      <section className="relative px-6 pt-20 pb-8 text-center overflow-hidden">
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[700px] h-[300px] bg-brand-600/8 blur-3xl rounded-full pointer-events-none" />
        <Chip>✦ AI-powered outreach for online coaches</Chip>
        <h1 className="mt-6 text-5xl sm:text-6xl font-black leading-[1.1] tracking-tight max-w-3xl mx-auto">
          Fill your calendar with<br />
          <span className="bg-gradient-to-r from-brand-400 to-brand-300 bg-clip-text text-transparent">
            qualified calls
          </span>{" "}
          — on autopilot.
        </h1>
        <p className="mt-5 text-lg text-slate-400 max-w-xl mx-auto leading-relaxed">
          LeanLead finds your ideal clients on Instagram and TikTok, writes
          personalized DMs, handles D+2/4/7 follow-ups, and books them into
          your Calendly. No VA needed.
        </p>
        <div className="mt-8 flex flex-col sm:flex-row gap-4 justify-center">
          <Link to="/register" className="px-8 py-3.5 bg-brand-500 hover:bg-brand-400 rounded-xl font-semibold text-sm transition-colors shadow-lg shadow-brand-900/40">
            Start for free →
          </Link>
          <a href="#how" className="px-6 py-3.5 border border-slate-700 hover:border-slate-500 text-slate-300 rounded-xl text-sm transition-colors">
            See how it works
          </a>
        </div>
        <p className="mt-3 text-xs text-slate-600">No credit card · Free plan · Cancel anytime</p>
        <KanbanPreview />
      </section>

      {/* How it works */}
      <section id="how" className="py-24 px-6">
        <div className="max-w-3xl mx-auto">
          <p className="text-center text-brand-400 text-xs uppercase tracking-widest font-semibold mb-3">How it works</p>
          <h2 className="text-3xl font-black text-center mb-16">From cold profile to booked call in 4 steps</h2>
          <div className="space-y-0">
            {[
              { n:"01", t:"Tell the AI your niche", d:"Enter your coaching niche, ideal client, and Calendly link. Takes 2 minutes.", detail:"The AI uses this to score every lead and write every message in your voice." },
              { n:"02", t:"AI prospects Instagram & TikTok", d:"Pick a platform and hashtags. LeanLead scrapes matching profiles, scores each one 1-10.", detail:"Only leads scoring 7+ land in your pipeline. No more time wasted on wrong-fit prospects." },
              { n:"03", t:"One-click personalized DMs", d:"Claude writes a custom outreach DM per lead using their actual bio and pain points.", detail:"Under 80 words. Sounds handwritten. Converts at 8-15% reply rate." },
              { n:"04", t:"D+2 / D+4 / D+7 follow-up sequences", d:"No reply? Three AI-written follow-ups with different tones — bump, value-add, final close.", detail:"When they reply you get an instant AI response that moves them toward a booking." },
            ].map((s, i, arr) => (
              <div key={s.n} className="flex gap-6 pb-12 relative">
                {i < arr.length - 1 && <div className="absolute left-5 top-12 bottom-0 w-px bg-slate-800" />}
                <div className="flex-shrink-0 w-10 h-10 rounded-full bg-brand-950 border border-brand-800 flex items-center justify-center z-10">
                  <span className="text-xs font-bold text-brand-400">{s.n}</span>
                </div>
                <div className="pt-1.5">
                  <h3 className="font-semibold text-white mb-1">{s.t}</h3>
                  <p className="text-slate-300 text-sm mb-1">{s.d}</p>
                  <p className="text-slate-500 text-xs leading-relaxed">{s.detail}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features */}
      <section id="features" className="py-24 px-6 bg-slate-950/60">
        <div className="max-w-5xl mx-auto">
          <p className="text-center text-brand-400 text-xs uppercase tracking-widest font-semibold mb-3">Features</p>
          <h2 className="text-3xl font-black text-center mb-14">Everything you need to close more clients</h2>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {[
              { icon:"🔍", t:"AI Lead Discovery", d:"Scrapes Instagram and TikTok by hashtag. Returns qualified, niche-matched profiles automatically." },
              { icon:"🎯", t:"1-10 Qualification Score", d:"Claude scores every lead against your niche, offer, and ideal-client description." },
              { icon:"✍️", t:"Personalized DM Writer", d:"Each message references the lead's actual bio. Under 80 words. No templates." },
              { icon:"🔁", t:"D+2 / D+4 / D+7 Follow-ups", d:"Three touches with bump, value-add, and final-close tones. Fully AI-written." },
              { icon:"💬", t:"Reply Handler", d:"Paste a reply, get an instant AI response that moves the conversation toward a booking." },
              { icon:"📊", t:"Kanban Pipeline", d:"Visual board: New → Contacted → Replied → Booked → Closed. Drag and drop." },
              { icon:"📋", t:"Airtable CRM Sync", d:"One-click sync. All lead data, scores, and messages go into your existing CRM." },
              { icon:"📅", t:"Calendly Integration", d:"Your booking link gets inserted naturally when a lead shows intent." },
              { icon:"🔒", t:"Multi-Coach Accounts", d:"Each coach sees only their own pipeline. Perfect for agencies too." },
            ].map(f => <Feature key={f.t} icon={f.icon} title={f.t} desc={f.d} />)}
          </div>
        </div>
      </section>

      {/* Testimonials */}
      <section className="py-24 px-6">
        <div className="max-w-4xl mx-auto">
          <p className="text-center text-brand-400 text-xs uppercase tracking-widest font-semibold mb-3">Results</p>
          <h2 className="text-3xl font-black text-center mb-14">Real coaches, real bookings</h2>
          <div className="grid sm:grid-cols-3 gap-5">
            {[
              { q:"I was spending 3 hours a day on Instagram outreach. Now LeanLead runs it while I coach. Booked 4 calls in week one.", name:"Marcus L.", role:"Business Coach", result:"4 calls / week 1" },
              { q:"The DMs sound nothing like templates. One prospect said it was the most thoughtful cold DM they'd ever received.", name:"Jasmine R.", role:"Life Coach", result:"12% reply rate" },
              { q:"The D+7 follow-up converted a lead who'd ghosted me for a week. That booking paid for 6 months of the tool.", name:"Tom A.", role:"Fitness Coach", result:"$3,200 from 1 DM" },
            ].map(t => (
              <div key={t.name} className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
                <p className="text-sm text-slate-300 leading-relaxed mb-5">"{t.q}"</p>
                <div className="flex justify-between items-end">
                  <div>
                    <p className="text-sm font-semibold text-white">{t.name}</p>
                    <p className="text-xs text-slate-500">{t.role}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-brand-400 font-bold text-sm">{t.result}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Pricing */}
      <section id="pricing" className="py-24 px-6 bg-slate-950/60">
        <div className="max-w-4xl mx-auto">
          <p className="text-center text-brand-400 text-xs uppercase tracking-widest font-semibold mb-3">Pricing</p>
          <h2 className="text-3xl font-black text-center mb-3">Simple, transparent pricing</h2>
          <p className="text-center text-slate-400 text-sm mb-14">Start free. Upgrade when you're closing.</p>
          <div className="grid sm:grid-cols-3 gap-6 items-start">
            <Pricing name="Starter" price="Free" sub="Try it with no commitment." features={["20 leads / month","AI qualification","DM writer","Manual follow-ups"]} cta="Get started free" />
            <Pricing name="Growth" price="$49" sub="For coaches actively prospecting." features={["200 leads / month","Instagram + TikTok scraping","D+2/4/7 follow-ups","Reply handler","Airtable sync","Priority support"]} hot cta="Start Growth plan" />
            <Pricing name="Agency" price="$129" sub="Manage multiple coaches." features={["Unlimited leads","Multi-coach accounts","All Growth features","Bulk prospecting","Custom AI prompts","Slack support"]} cta="Start Agency plan" />
          </div>
        </div>
      </section>

      {/* FAQ */}
      <section className="py-24 px-6">
        <div className="max-w-2xl mx-auto">
          <h2 className="text-2xl font-black text-center mb-12">Frequently asked questions</h2>
          <div className="space-y-6">
            {[
              { q:"Does it actually sound human?", a:"Yes. Claude references the lead's exact bio and posts. Coaches see 8-15% reply rates vs the industry average of 1-3%." },
              { q:"Do I need an Instagram account?", a:"No. LeanLead uses Apify to scrape public profiles by hashtag. Your account is never involved." },
              { q:"Can I use my own Airtable?", a:"Yes — add your Airtable Base ID and personal access token in onboarding. One click syncs every lead." },
              { q:"What happens when a lead replies?", a:"Paste their reply in the dashboard, get an AI response in seconds. You review before sending anything." },
              { q:"Is my data private?", a:"Completely. Each coach account is isolated — you only ever see your own leads and pipeline." },
            ].map(({ q, a }) => (
              <div key={q} className="border-b border-slate-800 pb-5">
                <p className="text-sm font-semibold text-white mb-2">{q}</p>
                <p className="text-sm text-slate-400 leading-relaxed">{a}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Final CTA */}
      <section className="py-24 px-6 text-center">
        <h2 className="text-4xl font-black mb-4">Ready to fill your calendar?</h2>
        <p className="text-slate-400 text-sm mb-8 max-w-xs mx-auto">Set up in 5 minutes. First leads qualified in 10.</p>
        <Link to="/register" className="inline-block px-10 py-4 bg-brand-500 hover:bg-brand-400 rounded-xl font-bold text-base transition-colors shadow-xl shadow-brand-900/40">
          Start for free today →
        </Link>
        <p className="text-xs text-slate-700 mt-3">No credit card · Cancel anytime</p>
      </section>

      {/* Footer */}
      <footer className="border-t border-slate-900 py-8 px-6 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-slate-600">
        <span className="font-bold text-slate-500">Lean<span className="text-brand-600">Lead</span></span>
        <div className="flex gap-5">
          <a href="#pricing">Pricing</a>
          <Link to="/login">Login</Link>
          <Link to="/register">Register</Link>
        </div>
        <p>© {new Date().getFullYear()} LeanLead. Built for coaches who close.</p>
      </footer>
    </div>
  );
}
