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
    <main className="min-h-screen bg-gray-900 text-white">
      {/* Early access notice */}
      <div className="bg-gray-800/60 border-b border-gray-700/60 py-2 px-4 text-center">
        <p className="text-xs text-gray-500">
          Early access — some features are still being built.
        </p>
      </div>

      {/* Hero */}
      <section className="relative flex flex-col items-center justify-center min-h-screen px-4 text-center">
        <div className="mb-6 inline-flex items-center gap-2 rounded-full bg-blue-500/10 border border-blue-500/20 px-4 py-1.5 text-sm text-blue-400">
          Free to use &bull; No account required
        </div>

        <h1 className="text-5xl md:text-7xl font-bold mb-6 bg-gradient-to-b from-white to-gray-400 bg-clip-text text-transparent leading-tight">
          Build the PC<br className="hidden sm:block" /> you actually need.
        </h1>

        <p className="text-xl text-gray-300 max-w-2xl mb-3 leading-relaxed">
          Set your budget and use case. AI picks every component, checks
          compatibility end-to-end, and gives you direct buy links from
          trusted EU PC stores.
        </p>

        <p className="text-sm text-gray-500 mb-10">
          Builds complete in under a minute. No guesswork, no mismatched parts.
        </p>

        <div className="flex flex-col sm:flex-row gap-3">
          <Link
            href="/build"
            className="bg-blue-600 hover:bg-blue-500 text-white font-semibold px-8 py-4 rounded-xl text-lg transition-colors"
          >
            Build My PC &rarr;
          </Link>
          <Link
            href="/find"
            className="border border-gray-600 hover:border-gray-400 text-gray-300 hover:text-white font-semibold px-8 py-4 rounded-xl text-lg transition-colors"
          >
            Find a Component
          </Link>
        </div>

        {/* Scroll indicator */}
        <div className="absolute bottom-10 left-1/2 -translate-x-1/2 animate-bounce text-gray-600" aria-hidden="true">
          <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="6 9 12 15 18 9" />
          </svg>
        </div>
      </section>

      {/* How it works */}
      <section className="border-t border-gray-800 py-20 px-4">
        <div className="max-w-3xl mx-auto">
          <h2 className="text-2xl font-bold text-white text-center mb-3">
            How it works
          </h2>
          <p className="text-gray-500 text-center text-sm mb-12">
            From budget to ready-to-buy list in three steps.
          </p>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {[
              {
                step: "01",
                title: "Set your budget and goal",
                desc: "Pick a budget range and choose your use case — gaming, design, everyday work, or engineering. Budget-incompatible goals are filtered out automatically.",
              },
              {
                step: "02",
                title: "AI picks compatible parts",
                desc: "Every component is selected for full compatibility. No mismatched CPU sockets, undersized PSUs, or GPU clearance issues — the build just works.",
              },
              {
                step: "03",
                title: "Buy direct — no searching",
                desc: "Each part comes with a direct link from the most trusted and top shops in EU. See the price, click the link, order the part.",
              },
            ].map((item) => (
              <div
                key={item.step}
                className="bg-gray-800 rounded-xl p-6 border border-gray-700"
              >
                <div className="text-blue-400 text-sm font-mono font-semibold mb-3">
                  {item.step}
                </div>
                <h3 className="font-semibold text-white mb-2">{item.title}</h3>
                <p className="text-gray-400 text-sm leading-relaxed">
                  {item.desc}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Example Builds */}
      <section className="border-t border-gray-800 py-20 px-4">
        <div className="max-w-3xl mx-auto">
          <h2 className="text-2xl font-bold text-white text-center mb-3">
            Example builds
          </h2>
          <p className="text-gray-500 text-center text-sm mb-12">
            Not sure where to start? Pick one of these as a starting point.
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {EXAMPLE_BUILDS.map((ex) => (
              <div
                key={ex.title}
                className="bg-gray-800 rounded-xl p-6 border border-gray-700 flex flex-col"
              >
                <div className="flex items-start justify-between gap-3 mb-3">
                  <h3 className="font-semibold text-white">{ex.title}</h3>
                  <span className="text-xs text-blue-400 bg-blue-500/10 border border-blue-500/20 rounded-full px-2 py-0.5 whitespace-nowrap">
                    {ex.badge}
                  </span>
                </div>
                <p className="text-gray-400 text-sm mb-4">{ex.desc}</p>
                <ul className="space-y-1.5 mb-6 flex-1">
                  {ex.bullets.map((b) => (
                    <li
                      key={b}
                      className="text-gray-400 text-sm flex items-start gap-2"
                    >
                      <span className="text-blue-400 select-none">·</span>
                      {b}
                    </li>
                  ))}
                </ul>
                <Link
                  href={`/build?budget=${ex.budget}&goal=${ex.goal}`}
                  className="block text-center bg-gray-700 hover:bg-gray-600 text-white text-sm font-medium py-2.5 rounded-lg transition-colors"
                >
                  Build this &rarr;
                </Link>
              </div>
            ))}
          </div>
          <p className="text-gray-600 text-xs text-center mt-8">
            Exact parts vary by availability and current pricing. The builder
            lets you adjust every preference before generating.
          </p>
        </div>
      </section>

      {/* Why trust PcCoach */}
      <section className="border-t border-gray-800 py-20 px-4">
        <div className="max-w-3xl mx-auto">
          <h2 className="text-2xl font-bold text-white text-center mb-3">
            Why trust PcCoach?
          </h2>
          <p className="text-gray-500 text-center text-sm mb-12">
            A few things worth knowing before you rely on these recommendations.
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
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
              <div
                key={item.title}
                className="border-l-2 border-blue-500/30 pl-5"
              >
                <h3 className="font-semibold text-white mb-1.5 text-sm">
                  {item.title}
                </h3>
                <p className="text-gray-400 text-sm leading-relaxed">
                  {item.desc}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Bottom CTA */}
      <section className="border-t border-gray-800 py-16 px-4 text-center">
        <div className="max-w-lg mx-auto">
          <h2 className="text-2xl font-bold text-white text-center mb-3">Ready to start?</h2>
          <p className="text-gray-400 text-sm mb-8">
            Budgets from €500 to €3,000+. Gaming, workstation, everyday use,
            and more.
          </p>
          <Link
            href="/build"
            className="inline-block bg-blue-600 hover:bg-blue-500 text-white font-semibold px-8 py-4 rounded-xl text-lg transition-colors"
          >
            Build My PC &rarr;
          </Link>
        </div>
      </section>
    </main>
  );
}
