import Link from "next/link";

export const metadata = {
  title: "The \u20AC1000\u20131200 1080p 144Hz Sweet Spot Build (March 2026) | The PC Coach",
  description:
    "The best price-to-performance ratio for a 1080p 144Hz gaming PC in March 2026.",
};

export default function SweetSpotBuildGuide() {
  return (
    <main className="min-h-screen bg-obsidian-bg py-12 px-4">
      <article className="max-w-2xl mx-auto">
        <Link
          href="/"
          className="text-obsidian-muted hover:text-obsidian-text text-xs uppercase tracking-widest transition-colors"
        >
          &larr; Back
        </Link>

        <h1 className="font-display font-light text-5xl text-obsidian-text mt-8 mb-4">
          The &euro;1000&ndash;1200 1080p 144Hz &ldquo;Sweet Spot&rdquo; Build
        </h1>

        <p className="text-obsidian-muted text-sm mb-10 font-mono uppercase tracking-widest">
          March 2026 &middot; 10 min read
        </p>

        <div className="space-y-6 text-obsidian-text text-sm leading-relaxed">
          <p>
            The &euro;1,000&ndash;1,200 range has always been the sweet spot for PC
            gaming. It&rsquo;s where you get solid performance without overspending,
            and in March 2026 it&rsquo;s the ideal budget for a smooth 1080p 144Hz
            experience.
          </p>
          <p>
            At this price point, current-generation mid-range GPUs deliver consistent
            1080p performance at high to ultra settings, easily pushing past 144 fps
            in competitive titles and holding 60+ fps in demanding AAA games. Pair
            that with DDR5 RAM prices finally settling into affordable territory, and
            you have a build that feels fast in every scenario.
          </p>
          <p>
            In this guide we walk through the ideal component allocation &mdash; where
            to spend, where to save, and what upgrades are worth considering if you
            want to push into the upper end of the &euro;1,200 budget.
          </p>

          <div className="border-t border-obsidian-border pt-8 mt-8">
            <p className="text-obsidian-muted text-xs">
              Full article coming soon. In the meantime,{" "}
              <Link href="/build" className="text-obsidian hover:brightness-110">
                try a build
              </Link>{" "}
              with a &euro;1,000 budget and see what our AI recommends.
            </p>
          </div>
        </div>
      </article>
    </main>
  );
}
