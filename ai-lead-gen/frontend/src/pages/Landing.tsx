import { Link } from "react-router-dom";

/* ─── tiny helpers ──────────────────────────────────────────────── */
function Badge({ children }: { children: React.ReactNode }) {
  return (
    <span className="inline-flex items-center gap-1.5 bg-sky-950/80 border border-sky-800/60 text-sky-400 text-xs px-3 py-1 rounded-full font-medium tracking-wide">
      {children}
    </span>
  );
}

function GradientText({ children }: { children: React.ReactNode }) {
  return (
    <span className="bg-gradient-to-r from-sky-400 to-cyan-300 bg-clip-text text-transparent">
      {children}
    </span>
  );
}

function FeatureCard({ icon, title, desc }: { icon: string; title: string; desc: string }) {
  return (
    <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-6 hover:border-sky-900 transition-colors group">
      <div className="text-2xl mb-4 w-10 h-10 bg-sky-950 rounded-xl flex items-center justify-center">
        {icon}
      </div>
      <h3 className="font-semibold text-white mb-2 text-sm">{title}</h3>
      <p className="text-sm text-slate-400 leading-relaxed">{desc}</p>
    </div>
  );
}

function PricingCard({
  name, price, desc, features, highlight, cta,
}: {
  name: string;
  price: string;
  desc: string;
  features: string[];
  highlight?: boolean;
  cta: string;
}) {
  return (
    <div
      className={`relative rounded-2xl p-8 border flex flex-col ${
        highlight
          ? "bg-sky-600 border-sky-500 shadow-xl shadow-sky-900/40"
          : "bg-slate-900 border-slate-800"
      }`}
    >
      {highlight && (
        <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-amber-400 text-slate-900 text-xs font-bold px-3 py-1 rounded-full">
          MOST POPULAR
        </div>
      )}
      <div className="mb-6">
        <p className={`text-sm font-semibold mb-1 ${highlight ? "text-sky-100" : "text-slate-400"}`}>{name}</p>
        <div className="flex items-baseline gap-1">
          <span className="text-4xl font-extrabold text-white">{price}</span>
          {price !== "Free" && <span className={`text-sm ${highlight ? "text-sky-200" : "text-slate-500"}`}>/month</span>}
        </div>
        <p className={`text-sm mt-2 ${highlight ? "text-sky-100" : "text-slate-500"}`}>{desc}</p>
      </div>
      <ul className="space-y-3 flex-1 mb-8">
        {features.map((f) => (
          <li key={f} className="flex items-start gap-2.5 text-sm">
            <span className={`mt-0.5 flex-shrink-0 ${highlight ? "text-sky-100" : "text-emerald-400"}`}>✓</span>
            <span className={highlight ? "text-sky-50" : "text-slate-300"}>{f}</span>
          </li>
        ))}
      </ul>
      <Link
        to="/register"
        className={`w-full text-center py-3 rounded-xl font-semibold text-sm transition-all ${
          highlight
            ? "bg-white text-sky-700 hover:bg-sky-50"
            : "bg-slate-800 text-white hover:bg-slate-700 border border-slate-700"
        }`}
      >
        {cta}
      </Link>
    </div>
  );
}

function TestimonialCard({
  quote, name, role, result,
}: {
  quote: string; name: string; role: string; result: string;
}) {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
      <p className="text-slate-300 text-sm leading-relaxed mb-5">"{quote}"</p>
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-semibold text-white">{name}</p>
          <p className="text-xs text-slate-500">{role}</p>
        </div>
        <div className="text-right">
          <p className="text-sky-400 font-bold text-sm">{result}</p>
          <p className="text-xs text-slate-600">result</p>
        </div>
      </div>
    </div>
  );
}

/* ─── Pipeline stage preview ────────────────────────────────────── */
function PipelinePreview() {
  const stages = [
    { label: "NEW", count: 47, color: "border-slate-600" },
    { label: "CONTACTED", count: 28, color: "border-sky-700" },
    { label: "REPLIED", count: 11, color: "border-violet-700" },
    { label: "BOOKED", count: 6, color: "border-emerald-700" },
    { label: "CLOSED", count: 3, color: "border-rose-800" },
  ];
  const cards = [
    { name: "Sarah M.", handle: "sarahmfitness", score: 9.1, tag: "Weight loss" },
    { name: "Jake T.", handle: "jaketconsults", score: 7.8, tag: "Business" },
    { name: "Priya K.", handle: "priyakwellness", score: 8.5, tag: "Mindset" },
  ];

  return (
    <div className="relative mx-auto max-w-4xl mt-16 mb-4 select-none">
      {/* Glow */}
      <div className="absolute inset-0 bg-sky-500/5 rounded-3xl blur-3xl" />
      <div className="relative bg-slate-900/80 border border-slate-800 rounded-2xl overflow-hidden shadow-2xl backdrop-blur">
        {/* Top bar */}
        <div className="flex items-center gap-2 px-4 py-3 border-b border-slate-800 bg-slate-950/60">
          <div className="w-2.5 h-2.5 rounded-full bg-red-500/70" />
          <div className="w-2.5 h-2.5 rounded-full bg-amber-500/70" />
          <div className="w-2.5 h-2.5 rounded-full bg-emerald-500/70" />
          <span className="ml-3 text-xs text-slate-600 font-mono">leanlead.app/dashboard</span>
        </div>
        {/* Nav mock */}
        <div className="flex items-center justify-between px-5 py-3 border-b border-slate-800/60">
          <span className="text-sky-400 font-bold text-sm">LeanLead</span>
          <div className="flex gap-4 text-xs text-slate-500">
            <span className="text-sky-400 border-b border-sky-400 pb-0.5">Pipeline</span>
            <span>Prospects</span>
            <span>Follow-ups</span>
          </div>
          <button className="text-xs bg-sky-500 text-white px-3 py-1 rounded-lg">+ Add lead</button>
        </div>
        {/* Stats row */}
        <div className="flex gap-6 px-5 py-3 border-b border-slate-800/40">
          {[["95", "Total leads"], ["28", "Contacted"], ["6", "Booked"], ["6.3%", "Conversion"]].map(([v, l]) => (
            <div key={l}>
              <p className="text-xs text-slate-600">{l}</p>
              <p className="text-base font-bold text-white">{v}</p>
            </div>
          ))}
        </div>
        {/* Kanban columns */}
        <div className="flex gap-3 p-4 overflow-x-auto scrollbar-thin">
          {stages.map((s, si) => (
            <div key={s.label} className={`min-w-[170px] rounded-xl border ${s.color} bg-slate-900/40`}>
              <div className="flex items-center justify-between px-3 py-2 border-b border-slate-800/60">
                <span className="text-[10px] font-bold text-slate-400 tracking-wider">{s.label}</span>
                <span className="text-[10px] bg-slate-800 text-slate-500 px-1.5 py-0.5 rounded-full">{s.count}</span>
              </div>
              <div className="p-2 space-y-2">
                {si === 0 && cards.map((c) => (
                  <div key={c.handle} className="bg-slate-800 rounded-lg p-2.5 text-left">
                    <div className="flex justify-between items-start mb-1">
                      <div>
                        <p className="text-[11px] font-medium text-white">{c.name}</p>
                        <p className="text-[10px] text-slate-500">@{c.handle}</p>
                      </div>
                      <span className="text-[10px] bg-emerald-900/80 text-emerald-400 px-1.5 py-0.5 rounded font-mono">{c.score}</span>
                    </div>
                    <span className="text-[9px] bg-sky-950 text-sky-400 px-1.5 py-0.5 rounded-full">{c.tag}</span>
                  </div>
                ))}
                {si !== 0 && (
                  <div className="h-16 rounded-lg border border-dashed border-slate-800 flex items-center justify-center">
                    <span className="text-[10px] text-slate-700">Drop here</span>
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

/* ─── Main page ─────────────────────────────────────────────────── */
export default function Landing() {
  return (
    <div className="min-h-screen bg-slate-950 text-white overflow-x-hidden">
      {/* ── Nav ── */}
      <nav className="sticky top-0 z-50 flex items-center justify-between px-6 py-4 border-b border-slate-900/80 bg-slate-950/90 backdrop-blur-md">
        <span className="text-lg font-extrabold tracking-tight text-white">
          Lean<span className="text-sky-400">Lead</span>
        </span>
        <div className="hidden sm:flex items-center gap-6 text-sm text-slate-400">
          <a href="#features" className="hover:text-white transition-colors">Features</a>
          <a href="#how" className="hover:text-white transition-colors">How it works</a>
          <a href="#pricing" className="hover:text-white transition-colors">Pricing</a>
        </div>
        <div className="flex items-center gap-3">
          <Link to="/login" className="text-sm text-slate-400 hover:text-white transition-colors px-3 py-1.5">
            Log in
          </Link>
          <Link
            to="/register"
            className="text-sm bg-sky-500 hover:bg-sky-400 text-white px-4 py-2 rounded-lg font-medium transition-colors shadow-lg shadow-sky-900/30"
          >
            Start free
          </Link>
        </div>
      </nav>

      {/* ── Hero ── */}
      <section className="relative pt-20 pb-8 px-6 text-center overflow-hidden">
        {/* Background glow */}
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[600px] h-[300px] bg-sky-600/10 blur-3xl rounded-full pointer-events-none" />

        <Badge>✦ AI-powered outreach for online coaches</Badge>

        <h1 className="mt-6 text-5xl sm:text-6xl font-extrabold leading-[1.1] tracking-tight max-w-3xl mx-auto">
          Fill your calendar with{" "}
          <GradientText>qualified calls</GradientText>
          <br />— without cold-call grind.
        </h1>

        <p className="mt-6 text-lg text-slate-400 max-w-xl mx-auto leading-relaxed">
          LeanLead finds your ideal clients on Instagram and TikTok, writes
          personalized DMs, handles D+2/4/7 follow-ups, and books them straight
          into your Calendly. Fully automated. Fully you.
        </p>

        <div className="mt-8 flex flex-col sm:flex-row items-center justify-center gap-4">
          <Link
            to="/register"
            className="px-8 py-3.5 bg-sky-500 hover:bg-sky-400 text-white rounded-xl font-semibold transition-colors shadow-lg shadow-sky-900/40 text-sm"
          >
            Start free — no card needed →
          </Link>
          <a
            href="#how"
            className="px-6 py-3.5 border border-slate-700 hover:border-slate-500 text-slate-300 rounded-xl text-sm transition-colors"
          >
            See how it works
          </a>
        </div>

        <p className="mt-4 text-xs text-slate-600">
          Free plan · No credit card · Cancel anytime
        </p>

        {/* Dashboard preview */}
        <PipelinePreview />
      </section>

      {/* ── Social proof strip ── */}
      <section className="py-10 border-y border-slate-900 bg-slate-950">
        <div className="max-w-4xl mx-auto px-6">
          <p className="text-center text-xs text-slate-600 uppercase tracking-widest mb-6">
            Coaches using LeanLead this month
          </p>
          <div className="flex flex-wrap justify-center gap-x-10 gap-y-4 text-slate-500 text-sm">
            {["Fitness Coaches", "Business Coaches", "Life Coaches", "Career Coaches", "Mindset Coaches", "Sales Coaches"].map((c) => (
              <span key={c} className="opacity-60 hover:opacity-100 transition-opacity">{c}</span>
            ))}
          </div>
        </div>
      </section>

      {/* ── How it works ── */}
      <section id="how" className="py-24 px-6">
        <div className="max-w-3xl mx-auto">
          <p className="text-center text-sky-400 text-xs uppercase tracking-widest font-semibold mb-3">How it works</p>
          <h2 className="text-3xl font-bold text-center mb-16">From cold profile to booked call in 4 steps</h2>
          <div className="space-y-0">
            {[
              {
                n: "01",
                title: "Tell the AI your niche",
                desc: "Enter your coaching niche, ideal client description, and Calendly link. Takes 2 minutes.",
                detail: "The AI uses this to score every lead and personalize every message to your voice.",
              },
              {
                n: "02",
                title: "AI prospects Instagram & TikTok",
                desc: "Pick a platform and hashtags. LeanLead scrapes matching profiles and scores each one 1-10.",
                detail: "Only leads scoring 7+ get added to your pipeline. No more time wasted on wrong-fit prospects.",
              },
              {
                n: "03",
                title: "One-click personalized DMs",
                desc: "For each qualified lead, Claude writes a custom outreach message using their actual bio and pain points.",
                detail: "Every message sounds handwritten. No templates. No generic openers.",
              },
              {
                n: "04",
                title: "Automated follow-up sequences",
                desc: "No reply? LeanLead generates D+2, D+4, and D+7 follow-ups — each with a different tone.",
                detail: "When they reply, get an instant AI-written response that moves them toward booking a call.",
              },
            ].map((s, i) => (
              <div key={s.n} className="flex gap-6 pb-12 relative">
                {i < 3 && (
                  <div className="absolute left-5 top-12 bottom-0 w-px bg-slate-800" />
                )}
                <div className="flex-shrink-0 w-10 h-10 rounded-full bg-sky-950 border border-sky-900 flex items-center justify-center z-10">
                  <span className="text-xs font-bold text-sky-400">{s.n}</span>
                </div>
                <div className="pt-1.5">
                  <h3 className="font-semibold text-white mb-1">{s.title}</h3>
                  <p className="text-slate-300 text-sm mb-2">{s.desc}</p>
                  <p className="text-slate-500 text-xs leading-relaxed">{s.detail}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Features ── */}
      <section id="features" className="py-24 px-6 bg-slate-950/50">
        <div className="max-w-5xl mx-auto">
          <p className="text-center text-sky-400 text-xs uppercase tracking-widest font-semibold mb-3">Features</p>
          <h2 className="text-3xl font-bold text-center mb-4">Everything you need to close more clients</h2>
          <p className="text-center text-slate-400 text-sm mb-14 max-w-xl mx-auto">
            Built specifically for solo coaches — no VA needed, no complex setup.
          </p>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
            <FeatureCard
              icon="🔍"
              title="AI Lead Discovery"
              desc="Scrapes Instagram and TikTok by hashtag. Filters profiles by engagement, bio fit, and niche alignment."
            />
            <FeatureCard
              icon="🎯"
              title="1-10 Qualification Score"
              desc="Every lead gets scored by Claude based on pain points, audience size, and match to your offer."
            />
            <FeatureCard
              icon="✍️"
              title="Personalized DM Writer"
              desc="Under 80 words. References their actual bio. Sounds like you wrote it after 10 minutes of research."
            />
            <FeatureCard
              icon="🔁"
              title="D+2 / D+4 / D+7 Follow-ups"
              desc="Three follow-up touches with different tones: light bump, value-add, and final close. All AI-written."
            />
            <FeatureCard
              icon="💬"
              title="Reply Handler"
              desc="Paste their reply. Get an instant contextual response that moves the conversation toward a call."
            />
            <FeatureCard
              icon="📊"
              title="Kanban Pipeline"
              desc="Drag leads from New → Contacted → Replied → Booked → Closed. Full visibility at a glance."
            />
            <FeatureCard
              icon="📋"
              title="Airtable CRM Sync"
              desc="One-click sync to Airtable. All lead data, messages, and scores go into your existing CRM."
            />
            <FeatureCard
              icon="📅"
              title="Calendly Integration"
              desc="Your booking link gets inserted naturally when a lead shows interest. Never forget to send it."
            />
            <FeatureCard
              icon="🔒"
              title="Multi-Coach Accounts"
              desc="Each coach sees only their own leads and pipeline. Perfect for agencies managing multiple clients."
            />
          </div>
        </div>
      </section>

      {/* ── Testimonials ── */}
      <section className="py-24 px-6">
        <div className="max-w-4xl mx-auto">
          <p className="text-center text-sky-400 text-xs uppercase tracking-widest font-semibold mb-3">Results</p>
          <h2 className="text-3xl font-bold text-center mb-14">Real coaches, real bookings</h2>
          <div className="grid sm:grid-cols-3 gap-5">
            <TestimonialCard
              quote="I was spending 3 hours a day on Instagram outreach. Now LeanLead runs it while I coach. Booked 4 calls my first week."
              name="Marcus L."
              role="Business Coach"
              result="4 calls / week 1"
            />
            <TestimonialCard
              quote="The DMs sound nothing like templates. One prospect literally said 'this is the most thoughtful cold DM I've ever gotten.'"
              name="Jasmine R."
              role="Life Coach"
              result="12% reply rate"
            />
            <TestimonialCard
              quote="The D+7 follow-up converted a lead who ghosted me for a week. That one booking paid for 6 months of the tool."
              name="Tom A."
              role="Fitness Coach"
              result="$3,200 from 1 DM"
            />
          </div>
        </div>
      </section>

      {/* ── Pricing ── */}
      <section id="pricing" className="py-24 px-6 bg-slate-950/50">
        <div className="max-w-4xl mx-auto">
          <p className="text-center text-sky-400 text-xs uppercase tracking-widest font-semibold mb-3">Pricing</p>
          <h2 className="text-3xl font-bold text-center mb-3">Simple, transparent pricing</h2>
          <p className="text-center text-slate-400 text-sm mb-14">
            Start free. Upgrade when you're closing.
          </p>
          <div className="grid sm:grid-cols-3 gap-6 items-start">
            <PricingCard
              name="Starter"
              price="Free"
              desc="Try it out with no commitment."
              features={[
                "Up to 20 leads / month",
                "AI qualification",
                "DM writer",
                "Manual follow-ups",
                "1 pipeline",
              ]}
              cta="Get started free"
            />
            <PricingCard
              name="Growth"
              price="$49"
              desc="For coaches actively prospecting."
              features={[
                "Up to 200 leads / month",
                "Instagram + TikTok scraping",
                "D+2/4/7 follow-up automation",
                "Reply handler",
                "Airtable CRM sync",
                "Priority support",
              ]}
              highlight
              cta="Start Growth plan"
            />
            <PricingCard
              name="Agency"
              price="$129"
              desc="Manage multiple coaches from one account."
              features={[
                "Unlimited leads",
                "Multi-coach accounts",
                "All Growth features",
                "Bulk prospecting jobs",
                "Custom AI prompts",
                "Dedicated Slack support",
              ]}
              cta="Start Agency plan"
            />
          </div>
        </div>
      </section>

      {/* ── FAQ ── */}
      <section className="py-24 px-6">
        <div className="max-w-2xl mx-auto">
          <h2 className="text-2xl font-bold text-center mb-12">Frequently asked questions</h2>
          <div className="space-y-6">
            {[
              {
                q: "Does this actually sound human, or is it obvious AI?",
                a: "Claude references specific details from the lead's bio and posts. Coaches report reply rates of 8-15%, which is well above typical cold DM averages of 1-3%.",
              },
              {
                q: "Do I need an Instagram or TikTok account?",
                a: "No. LeanLead uses Apify to scrape public profiles. You just enter hashtags, and the AI finds the leads. Your account is never involved.",
              },
              {
                q: "Can I connect my own Airtable?",
                a: "Yes — enter your Airtable base ID and personal access token in onboarding. All lead data, scores, and messages sync automatically.",
              },
              {
                q: "What happens when a lead replies?",
                a: "You'll see their reply in the dashboard. Paste it in and get an AI-generated response within seconds. You review it before sending anything.",
              },
              {
                q: "Is my data private?",
                a: "Each coach account is completely isolated. You only ever see your own leads, messages, and pipeline.",
              },
            ].map(({ q, a }) => (
              <div key={q} className="border-b border-slate-800 pb-6">
                <p className="font-medium text-white mb-2 text-sm">{q}</p>
                <p className="text-slate-400 text-sm leading-relaxed">{a}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Final CTA ── */}
      <section className="py-24 px-6 text-center relative overflow-hidden">
        <div className="absolute inset-0 bg-sky-600/5 blur-3xl" />
        <div className="relative">
          <h2 className="text-4xl font-extrabold mb-4">
            Ready to book more calls<br />without more hustle?
          </h2>
          <p className="text-slate-400 mb-8 max-w-sm mx-auto text-sm">
            Set up in 5 minutes. First leads qualified in 10.
          </p>
          <Link
            to="/register"
            className="inline-block px-10 py-4 bg-sky-500 hover:bg-sky-400 text-white rounded-xl font-bold text-base transition-colors shadow-xl shadow-sky-900/40"
          >
            Start free today →
          </Link>
          <p className="text-xs text-slate-700 mt-4">No credit card · No BS · Cancel anytime</p>
        </div>
      </section>

      {/* ── Footer ── */}
      <footer className="border-t border-slate-900 py-10 px-6">
        <div className="max-w-5xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
          <span className="text-sm font-bold text-slate-500">
            Lean<span className="text-sky-500">Lead</span>
          </span>
          <div className="flex gap-6 text-xs text-slate-600">
            <a href="#pricing" className="hover:text-slate-400 transition-colors">Pricing</a>
            <Link to="/login" className="hover:text-slate-400 transition-colors">Log in</Link>
            <Link to="/register" className="hover:text-slate-400 transition-colors">Register</Link>
          </div>
          <p className="text-xs text-slate-700">© {new Date().getFullYear()} LeanLead. Built for coaches who close.</p>
        </div>
      </footer>
    </div>
  );
}
