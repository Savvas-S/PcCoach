import Link from "next/link";
import type { BudgetRange, UserGoal } from "@/lib/api";

type ExampleBuild = {
  title: string;
  badge: string;
  desc: string;
  bullets: string[];
  budget: BudgetRange;
  goal: UserGoal;
};

const EXAMPLE_BUILDS: ExampleBuild[] = [
  {
    title: "Budget Gaming",
    badge: "Under €1,000",
    desc: "1080p gaming at medium to high settings",
    bullets: ["Mid-range dedicated GPU", "16 GB DDR5 RAM", "500 GB NVMe SSD"],
    budget: "0_1000",
    goal: "low_end_gaming",
  },
  {
    title: "1440p Gaming",
    badge: "€1,500 – €2,000",
    desc: "High-refresh 1440p gaming at high settings",
    bullets: ["High-tier GPU for 1440p", "Strong gaming CPU", "32 GB DDR5, 1 TB NVMe"],
    budget: "1500_2000",
    goal: "mid_range_gaming",
  },
  {
    title: "Productivity",
    badge: "€1,000 – €1,500",
    desc: "Fast multi-core machine for heavy workloads",
    bullets: ["High core-count CPU", "32 GB DDR5 RAM", "Large, fast NVMe storage"],
    budget: "1000_1500",
    goal: "heavy_work",
  },
  {
    title: "Creator / Editing",
    badge: "€2,000 – €3,000",
    desc: "Video editing, rendering, and creative work",
    bullets: ["High core-count CPU + capable GPU", "32–64 GB DDR5", "Fast NVMe, high capacity"],
    budget: "2000_3000",
    goal: "heavy_work",
  },
];

export default function Home() {
  return (
    <main className="min-h-screen text-obsidian-text">

      {/* Early access notice */}
      <div className="border-b border-obsidian-border py-2 px-4 text-center bg-obsidian-surface">
        <p className="text-xs text-obsidian-muted uppercase tracking-widest">
          Early access — some features are still being built
        </p>
      </div>

      {/* Hero */}
      <section
        className="relative flex flex-col items-center justify-center min-h-screen px-4 text-center bg-obsidian-bg"
        style={{ backgroundImage: "radial-gradient(ellipse 70% 50% at 50% 0%, rgba(201,168,76,0.06) 0%, transparent 65%)" }}
      >
        <div className="opacity-0 animate-fade-up [animation-delay:0ms] mb-8 inline-flex items-center gap-3 border border-obsidian-border px-5 py-2">
          <span className="text-xs text-obsidian-muted uppercase tracking-[0.2em]">
            Free to use &nbsp;&bull;&nbsp; No account required
          </span>
        </div>

        <h1 className="opacity-0 animate-fade-up [animation-delay:120ms] font-display font-light text-6xl md:text-8xl text-obsidian-text leading-tight mb-8">
          Build the PC<br className="hidden sm:block" /> you{" "}
          <em className="text-obsidian not-italic font-normal">actually need.</em>
        </h1>

        <p className="opacity-0 animate-fade-up [animation-delay:240ms] text-lg text-obsidian-muted max-w-xl mb-3 leading-relaxed font-body">
          Set your budget and use case. AI picks every component, checks
          compatibility end-to-end, and gives you direct buy links from
          trusted EU PC stores.
        </p>

        <p className="opacity-0 animate-fade-up [animation-delay:300ms] text-sm text-obsidian-muted-light mb-12 font-body">
          Builds complete in under a minute. No guesswork, no mismatched parts.
        </p>

        <div className="opacity-0 animate-fade-up [animation-delay:380ms] flex flex-col sm:flex-row gap-4">
          <Link
            href="/build"
            className="bg-obsidian text-obsidian-bg font-body font-semibold px-8 py-4 text-base hover:brightness-110 transition-all"
          >
            Build My PC &rarr;
          </Link>
          <Link
            href="/find"
            className="border border-obsidian-border hover:border-obsidian-bright text-obsidian-muted hover:text-obsidian-text font-body font-semibold px-8 py-4 text-base transition-colors"
          >
            Find a Component
          </Link>
        </div>

        {/* Scroll indicator */}
        <div className="absolute bottom-10 left-1/2 -translate-x-1/2 animate-bounce text-obsidian-muted-light" aria-hidden="true">
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="6 9 12 15 18 9" />
          </svg>
        </div>
      </section>

      {/* How it works */}
      <section className="border-t border-obsidian-border py-24 px-4 bg-obsidian-bg">
        <div className="max-w-3xl mx-auto">
          <p className="text-xs text-obsidian uppercase tracking-[0.25em] text-center mb-4">How it works</p>
          <h2 className="font-display font-light text-4xl text-obsidian-text text-center mb-16">
            From budget to build in three steps
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-px bg-obsidian-border">
            {[
              {
                step: "I",
                title: "Set your budget and goal",
                desc: "Pick a budget range and choose your use case — gaming, design, everyday work, or engineering. Budget-incompatible goals are filtered out automatically.",
              },
              {
                step: "II",
                title: "AI picks compatible parts",
                desc: "Every component is selected for full compatibility. No mismatched CPU sockets, undersized PSUs, or GPU clearance issues — the build just works.",
              },
              {
                step: "III",
                title: "Buy direct — no searching",
                desc: "Each part comes with a direct link from trusted EU shops. See the price, click the link, order the part.",
              },
            ].map((item) => (
              <div
                key={item.step}
                className="bg-obsidian-surface p-8 hover:bg-obsidian-raised transition-colors"
              >
                <div className="font-mono text-obsidian text-xs mb-6 tracking-widest">{item.step}</div>
                <h3 className="font-body font-semibold text-obsidian-text mb-3 text-sm">{item.title}</h3>
                <p className="text-obsidian-muted text-sm leading-relaxed">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Example Builds */}
      <section className="border-t border-obsidian-border py-24 px-4 bg-obsidian-surface">
        <div className="max-w-3xl mx-auto">
          <p className="text-xs text-obsidian uppercase tracking-[0.25em] text-center mb-4">Example builds</p>
          <h2 className="font-display font-light text-4xl text-obsidian-text text-center mb-16">
            Not sure where to start?
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-px bg-obsidian-border">
            {EXAMPLE_BUILDS.map((ex) => (
              <div
                key={ex.title}
                className="bg-obsidian-bg p-8 flex flex-col hover:bg-obsidian-raised transition-colors"
              >
                <div className="flex items-start justify-between gap-3 mb-4">
                  <h3 className="font-display font-normal text-xl text-obsidian-text">{ex.title}</h3>
                  <span className="text-xs font-mono text-obsidian border border-obsidian/30 px-2 py-0.5 whitespace-nowrap">
                    {ex.badge}
                  </span>
                </div>
                <p className="text-obsidian-muted text-sm mb-5">{ex.desc}</p>
                <ul className="space-y-2 mb-8 flex-1">
                  {ex.bullets.map((b) => (
                    <li key={b} className="text-obsidian-muted text-sm flex items-start gap-3">
                      <span className="text-obsidian select-none mt-0.5">—</span>
                      {b}
                    </li>
                  ))}
                </ul>
                <Link
                  href={`/build?budget=${ex.budget}&goal=${ex.goal}`}
                  className="text-center border border-obsidian-border hover:border-obsidian text-obsidian-muted hover:text-obsidian text-sm py-3 transition-colors font-body"
                >
                  Build this &rarr;
                </Link>
              </div>
            ))}
          </div>
          <p className="text-obsidian-muted-light text-xs text-center mt-8">
            Exact parts vary by availability and current pricing.
          </p>
        </div>
      </section>

      {/* Why trust PcCoach */}
      <section className="border-t border-obsidian-border py-24 px-4 bg-obsidian-bg">
        <div className="max-w-3xl mx-auto">
          <p className="text-xs text-obsidian uppercase tracking-[0.25em] text-center mb-4">Why trust us</p>
          <h2 className="font-display font-light text-4xl text-obsidian-text text-center mb-16">
            Honest recommendations, always
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-10">
            {[
              {
                title: "Recommendations follow your budget",
                desc: "Goals you can't afford are filtered out before you see them. Every component is picked within your actual budget range — not a theoretical one.",
              },
              {
                title: "Compatibility is checked, not assumed",
                desc: "CPU socket, RAM type, case dimensions, GPU clearance, and PSU wattage are cross-checked automatically. The build is meant to actually work.",
              },
              {
                title: "Affiliate links cost you nothing extra",
                desc: "We earn a small commission if you buy through a link. The price you see is the same price you'd pay going directly to the store.",
              },
              {
                title: "Practical picks, not part-list padding",
                desc: "The goal is a balanced, working build for your use case — not a list of the most expensive compatible components or whatever's in stock.",
              },
            ].map((item) => (
              <div key={item.title} className="border-l border-obsidian/30 pl-6">
                <h3 className="font-body font-semibold text-obsidian-text mb-2 text-sm">{item.title}</h3>
                <p className="text-obsidian-muted text-sm leading-relaxed">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Bottom CTA */}
      <section className="border-t border-obsidian-border py-20 px-4 bg-obsidian-surface text-center">
        <div className="max-w-lg mx-auto">
          <h2 className="font-display font-light text-4xl text-obsidian-text mb-4">Ready to start?</h2>
          <p className="text-obsidian-muted text-sm mb-10">
            Budgets from €500 to €3,000+. Gaming, workstation, everyday use, and more.
          </p>
          <Link
            href="/build"
            className="inline-block bg-obsidian text-obsidian-bg font-body font-semibold px-10 py-4 text-base hover:brightness-110 transition-all"
          >
            Build My PC &rarr;
          </Link>
        </div>
      </section>

    </main>
  );
}
