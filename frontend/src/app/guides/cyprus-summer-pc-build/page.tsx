import Link from "next/link";

export const metadata = {
  title: "Building a PC for the 40\u00B0C Cyprus Summer | The PC Coach",
  description:
    "Why high-airflow mesh cases and 360mm AIOs are mandatory for high-end builds in the Mediterranean heat.",
};

export default function CyprusSummerBuildGuide() {
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
          Building a PC for the 40&deg;C Cyprus Summer
        </h1>

        <p className="text-obsidian-muted text-sm mb-10 font-mono uppercase tracking-widest">
          March 2026 &middot; 8 min read
        </p>

        <div className="space-y-6 text-obsidian-text text-sm leading-relaxed">
          <p>
            If you live in Limassol, Nicosia, or anywhere on the island, you already
            know: summers are brutal. Indoor temperatures can sit at 35&ndash;40&deg;C
            even with air conditioning, and your PC components feel every degree.
          </p>
          <p>
            In this guide we break down the cooling strategies that actually work for
            Cyprus builders &mdash; from high-airflow mesh cases like the Fractal Pop
            Air and Phanteks G300A, to 360mm AIO liquid coolers that keep high-TDP
            processors in check when ambient temps soar.
          </p>
          <div className="border-t border-obsidian-border pt-8 mt-8">
            <p className="text-obsidian-muted text-xs">
              Full article coming soon. In the meantime,{" "}
              <Link href="/build" className="text-obsidian hover:brightness-110">
                build your PC
              </Link>{" "}
              and our AI will factor in cooling requirements automatically.
            </p>
          </div>
        </div>
      </article>
    </main>
  );
}
