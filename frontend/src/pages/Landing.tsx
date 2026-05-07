import { Link } from "react-router-dom";

const Chip = ({ children }: { children: React.ReactNode }) => (
  <span className="inline-flex items-center gap-1.5 text-xs bg-brand-950 border border-brand-800/60 text-brand-400 px-3 py-1 rounded-full font-medium">
    {children}
  </span>
);

function KanbanPreview() {
  const cols = [
    { label: "NOUVEAU",   color: "border-slate-600",   count: 47 },
    { label: "CONTACTÉ",  color: "border-brand-700",   count: 28 },
    { label: "RÉPONDU",   color: "border-brand-700",   count: 11 },
    { label: "RÉSERVÉ",   color: "border-emerald-700", count: 6  },
    { label: "CLÔTURÉ",   color: "border-rose-800",    count: 3  },
  ];
  const cards = [
    { name: "Sarah M.", handle: "sarahmfitness",   score: 9.1, tag: "perte de poids",  color: "text-emerald-400" },
    { name: "Jake T.",  handle: "jakethomas_biz",  score: 7.8, tag: "business",        color: "text-amber-400"   },
    { name: "Priya K.", handle: "priyak_life",     score: 8.5, tag: "développement",   color: "text-emerald-400" },
  ];

  return (
    <div className="relative mx-auto max-w-5xl mt-14 select-none">
      <div className="absolute inset-x-0 top-0 h-40 bg-brand-500/5 blur-3xl rounded-full pointer-events-none" />
      <div className="relative rounded-2xl border border-slate-800 bg-slate-900/80 overflow-hidden shadow-2xl backdrop-blur-sm">
        {/* Barre de fenêtre */}
        <div className="flex items-center gap-2 px-4 py-3 border-b border-slate-800 bg-slate-950/50">
          <div className="flex gap-1.5">
            <div className="w-3 h-3 rounded-full bg-red-500/50" />
            <div className="w-3 h-3 rounded-full bg-amber-500/50" />
            <div className="w-3 h-3 rounded-full bg-emerald-500/50" />
          </div>
          <span className="ml-2 text-xs text-slate-600 font-mono">leanlead.app/dashboard</span>
        </div>
        {/* Fausse nav */}
        <div className="flex items-center justify-between px-5 py-3 border-b border-slate-800/50">
          <span className="font-bold text-sm text-brand-400">LeanLead</span>
          <div className="flex gap-5 text-xs">
            <span className="text-brand-400 border-b border-brand-500 pb-0.5">Pipeline</span>
            <span className="text-slate-500">Prospection</span>
            <span className="text-slate-500">Relances</span>
          </div>
          <div className="text-xs bg-brand-500 text-white px-3 py-1 rounded-lg">+ Ajouter</div>
        </div>
        {/* Stats */}
        <div className="flex gap-8 px-5 py-3 border-b border-slate-800/30">
          {[["95","Total"],["28","Contactés"],["11","Répondus"],["6","Réservés"],["6.3%","Conversion"]].map(([v,l]) => (
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
                    <span className="text-[9px] text-slate-700">déposer des leads ici</span>
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

const Feature = ({ icon, title, desc }: { icon: string; title: string; desc: string }) => (
  <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 hover:border-brand-900/60 transition-colors">
    <div className="w-10 h-10 bg-brand-950 rounded-xl flex items-center justify-center text-xl mb-4">{icon}</div>
    <h3 className="text-sm font-semibold text-white mb-2">{title}</h3>
    <p className="text-sm text-slate-400 leading-relaxed">{desc}</p>
  </div>
);

const Pricing = ({
  name, price, sub, features, hot, cta,
}: {
  name: string; price: string; sub?: string; features: string[]; hot?: boolean; cta: string;
}) => (
  <div className={`relative rounded-2xl p-8 border flex flex-col ${hot ? "bg-brand-600 border-brand-500 shadow-2xl shadow-brand-900/40" : "bg-slate-900 border-slate-800"}`}>
    {hot && <span className="absolute -top-3 left-1/2 -translate-x-1/2 bg-amber-400 text-slate-900 text-[10px] font-bold px-3 py-1 rounded-full tracking-wide">LE PLUS POPULAIRE</span>}
    <p className={`text-xs font-semibold mb-1 ${hot ? "text-brand-100" : "text-slate-400"}`}>{name}</p>
    <div className="flex items-baseline gap-1 mb-1">
      <span className="text-4xl font-black text-white">{price}</span>
      {price !== "Gratuit" && <span className={`text-sm ${hot ? "text-brand-200" : "text-slate-500"}`}>/mois</span>}
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

export default function Landing() {
  return (
    <div className="min-h-screen bg-slate-950 text-white overflow-x-hidden">
      {/* Navigation */}
      <nav className="sticky top-0 z-50 flex items-center justify-between px-6 py-4 border-b border-slate-900 bg-[#0a0a0a]/90 backdrop-blur-md">
        <span className="font-extrabold text-lg">Lean<span className="text-brand-400">Lead</span></span>
        <div className="hidden sm:flex gap-7 text-sm text-slate-400">
          {[["#features","Fonctionnalités"],["#how","Comment ça marche"],["#pricing","Tarifs"]].map(([h,l]) => (
            <a key={h} href={h} className="hover:text-white transition-colors">{l}</a>
          ))}
        </div>
        <div className="flex gap-3 items-center">
          <Link to="/login" className="text-sm text-slate-400 hover:text-white transition-colors px-2 py-1.5">Connexion</Link>
          <Link to="/register" className="text-sm bg-brand-500 hover:bg-brand-400 px-4 py-2 rounded-lg font-medium transition-colors shadow-lg shadow-brand-900/30">Commencer</Link>
        </div>
      </nav>

      {/* Héro */}
      <section className="relative px-6 pt-20 pb-8 text-center overflow-hidden">
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[700px] h-[300px] bg-brand-600/8 blur-3xl rounded-full pointer-events-none" />
        <Chip>✦ Prospection IA pour les coachs en ligne</Chip>
        <h1 className="mt-6 text-5xl sm:text-6xl font-black leading-[1.1] tracking-tight max-w-3xl mx-auto">
          Remplissez votre agenda<br />
          <span className="bg-gradient-to-r from-brand-400 to-brand-300 bg-clip-text text-transparent">
            d'appels qualifiés
          </span>{" "}
          — en automatique.
        </h1>
        <p className="mt-5 text-lg text-slate-400 max-w-xl mx-auto leading-relaxed">
          LeanLead trouve vos clients idéaux sur Instagram et TikTok, rédige des DMs
          personnalisés, gère les relances J+2/4/7 et les inscrit dans votre Calendly.
          Sans assistant virtuel.
        </p>
        <div className="mt-8 flex flex-col sm:flex-row gap-4 justify-center">
          <Link to="/register" className="px-8 py-3.5 bg-brand-500 hover:bg-brand-400 shadow-glow-brand hover:shadow-glow-brand-lg rounded-xl font-semibold text-sm transition-colors shadow-lg shadow-brand-900/40">
            Commencer gratuitement →
          </Link>
          <a href="#how" className="px-6 py-3.5 border border-slate-700 hover:border-slate-500 text-slate-300 rounded-xl text-sm transition-colors">
            Voir comment ça marche
          </a>
        </div>
        <p className="mt-3 text-xs text-slate-600">Sans carte bancaire · Plan gratuit · Annulable à tout moment</p>
        <KanbanPreview />
      </section>

      {/* Comment ça marche */}
      <section id="how" className="py-24 px-6">
        <div className="max-w-3xl mx-auto">
          <p className="text-center text-brand-400 text-xs uppercase tracking-widest font-semibold mb-3">Comment ça marche</p>
          <h2 className="text-3xl font-black text-center mb-16">Du profil froid à l'appel réservé en 4 étapes</h2>
          <div className="space-y-0">
            {[
              { n:"01", t:"Indiquez votre créneau à l'IA", d:"Entrez votre créneau de coaching, votre client idéal et votre lien Calendly. 2 minutes suffisent.", detail:"L'IA s'en sert pour noter chaque lead et rédiger chaque message dans votre style." },
              { n:"02", t:"L'IA prospecte Instagram & TikTok", d:"Choisissez une plateforme et des hashtags. LeanLead scrape les profils correspondants et les note de 1 à 10.", detail:"Seuls les leads notés 7+ arrivent dans votre pipeline. Plus de temps perdu sur de mauvais prospects." },
              { n:"03", t:"DMs personnalisés en un clic", d:"Claude rédige un DM de prospection sur mesure par lead, basé sur leur vraie bio et leurs points de douleur.", detail:"Moins de 80 mots. Sonne authentique. Taux de réponse de 8 à 15 %." },
              { n:"04", t:"Séquences de relance J+2 / J+4 / J+7", d:"Pas de réponse ? Trois relances rédigées par l'IA avec des tons différents — rappel, valeur ajoutée, dernière tentative.", detail:"Quand ils répondent, vous obtenez instantanément une réponse IA qui guide la conversation vers une réservation." },
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

      {/* Fonctionnalités */}
      <section id="features" className="py-24 px-6 bg-slate-950/60">
        <div className="max-w-5xl mx-auto">
          <p className="text-center text-brand-400 text-xs uppercase tracking-widest font-semibold mb-3">Fonctionnalités</p>
          <h2 className="text-3xl font-black text-center mb-14">Tout ce qu'il vous faut pour conclure plus de clients</h2>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {[
              { icon:"🔍", t:"Découverte de leads par IA", d:"Scrape Instagram et TikTok par hashtag. Retourne automatiquement des profils qualifiés correspondant à votre créneau." },
              { icon:"🎯", t:"Score de qualification 1-10", d:"Claude note chaque lead par rapport à votre créneau, offre et description du client idéal." },
              { icon:"✍️", t:"Rédacteur de DM personnalisé", d:"Chaque message fait référence à la vraie bio du lead. Moins de 80 mots. Zéro template." },
              { icon:"🔁", t:"Relances J+2 / J+4 / J+7", d:"Trois contacts avec des tons rappel, valeur ajoutée et dernière tentative. Entièrement rédigés par l'IA." },
              { icon:"💬", t:"Gestionnaire de réponses", d:"Collez une réponse, obtenez instantanément une réponse IA qui oriente la conversation vers une réservation." },
              { icon:"📊", t:"Pipeline Kanban", d:"Tableau visuel : Nouveau → Contacté → Répondu → Réservé → Clôturé. Glisser-déposer." },
              { icon:"📋", t:"Synchronisation CRM Airtable", d:"Synchronisation en un clic. Toutes les données, scores et messages vers votre CRM existant." },
              { icon:"📅", t:"Intégration Calendly", d:"Votre lien de réservation est inséré naturellement quand un lead montre de l'intérêt." },
              { icon:"🔒", t:"Comptes multi-coachs", d:"Chaque coach ne voit que son propre pipeline. Parfait pour les agences." },
            ].map(f => <Feature key={f.t} icon={f.icon} title={f.t} desc={f.d} />)}
          </div>
        </div>
      </section>

      {/* Témoignages */}
      <section className="py-24 px-6">
        <div className="max-w-4xl mx-auto">
          <p className="text-center text-brand-400 text-xs uppercase tracking-widest font-semibold mb-3">Résultats</p>
          <h2 className="text-3xl font-black text-center mb-14">De vrais coachs, de vraies réservations</h2>
          <div className="grid sm:grid-cols-3 gap-5">
            {[
              { q:"Je passais 3 heures par jour sur la prospection Instagram. Maintenant LeanLead le fait pendant que je coache. 4 appels réservés dès la première semaine.", name:"Marcus L.", role:"Coach Business", result:"4 appels / semaine 1" },
              { q:"Les DMs ne ressemblent pas du tout à des templates. Un prospect a dit que c'était le DM à froid le plus réfléchi qu'il ait jamais reçu.", name:"Jasmine R.", role:"Coach de Vie", result:"12 % de taux de réponse" },
              { q:"La relance J+7 a converti un lead qui m'avait ghosté pendant une semaine. Cette réservation a payé 6 mois d'abonnement.", name:"Tom A.", role:"Coach Fitness", result:"3 200 $ pour 1 DM" },
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

      {/* Tarifs */}
      <section id="pricing" className="py-24 px-6 bg-slate-950/60">
        <div className="max-w-4xl mx-auto">
          <p className="text-center text-brand-400 text-xs uppercase tracking-widest font-semibold mb-3">Tarifs</p>
          <h2 className="text-3xl font-black text-center mb-3">Tarifs simples et transparents</h2>
          <p className="text-center text-slate-400 text-sm mb-14">Commencez gratuitement. Passez à la version supérieure quand vous concluez.</p>
          <div className="grid sm:grid-cols-3 gap-6 items-start">
            <Pricing name="Démarrage" price="Gratuit" sub="Essayez sans engagement." features={["20 leads / mois","Qualification IA","Rédacteur de DM","Relances manuelles"]} cta="Commencer gratuitement" />
            <Pricing name="Croissance" price="49 $" sub="Pour les coachs en prospection active." features={["200 leads / mois","Scraping Instagram + TikTok","Relances J+2/4/7","Gestionnaire de réponses","Sync Airtable","Support prioritaire"]} hot cta="Démarrer le plan Croissance" />
            <Pricing name="Agence" price="129 $" sub="Gérez plusieurs coachs." features={["Leads illimités","Comptes multi-coachs","Toutes les fonctionnalités Croissance","Prospection en masse","Prompts IA personnalisés","Support Slack"]} cta="Démarrer le plan Agence" />
          </div>
        </div>
      </section>

      {/* FAQ */}
      <section className="py-24 px-6">
        <div className="max-w-2xl mx-auto">
          <h2 className="text-2xl font-black text-center mb-12">Questions fréquentes</h2>
          <div className="space-y-6">
            {[
              { q:"Ça sonne vraiment humain ?", a:"Oui. Claude fait référence à la vraie bio et aux publications du lead. Les coachs obtiennent 8 à 15 % de taux de réponse contre 1 à 3 % en moyenne dans le secteur." },
              { q:"Ai-je besoin d'un compte Instagram ?", a:"Non. LeanLead utilise Apify pour scraper les profils publics par hashtag. Votre compte n'est jamais impliqué." },
              { q:"Puis-je utiliser mon propre Airtable ?", a:"Oui — ajoutez votre Base ID Airtable et votre jeton d'accès dans l'onboarding. Un clic synchronise chaque lead." },
              { q:"Que se passe-t-il quand un lead répond ?", a:"Collez leur réponse dans le tableau de bord, obtenez une réponse IA en quelques secondes. Vous relisez avant d'envoyer quoi que ce soit." },
              { q:"Mes données sont-elles privées ?", a:"Complètement. Chaque compte coach est isolé — vous ne voyez que vos propres leads et pipeline." },
            ].map(({ q, a }) => (
              <div key={q} className="border-b border-slate-800 pb-5">
                <p className="text-sm font-semibold text-white mb-2">{q}</p>
                <p className="text-sm text-slate-400 leading-relaxed">{a}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA final */}
      <section className="py-24 px-6 text-center">
        <h2 className="text-4xl font-black mb-4">Prêt à remplir votre agenda ?</h2>
        <p className="text-slate-400 text-sm mb-8 max-w-xs mx-auto">Configuration en 5 minutes. Premiers leads qualifiés en 10.</p>
        <Link to="/register" className="inline-block px-10 py-4 bg-brand-500 hover:bg-brand-400 shadow-glow-brand hover:shadow-glow-brand-lg rounded-xl font-bold text-base transition-colors shadow-xl shadow-brand-900/40">
          Commencer gratuitement aujourd'hui →
        </Link>
        <p className="text-xs text-slate-700 mt-3">Sans carte bancaire · Annulable à tout moment</p>
      </section>

      {/* Pied de page */}
      <footer className="border-t border-slate-900 py-8 px-6 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-slate-600">
        <span className="font-bold text-slate-500">Lean<span className="text-brand-600">Lead</span></span>
        <div className="flex gap-5">
          <a href="#pricing">Tarifs</a>
          <Link to="/login">Connexion</Link>
          <Link to="/register">S'inscrire</Link>
        </div>
        <p>© {new Date().getFullYear()} LeanLead. Conçu pour les coachs qui concluent.</p>
      </footer>
    </div>
  );
}
