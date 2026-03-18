import Link from "next/link";

type GuideCard = {
  title: string;
  excerpt: string;
  href: string;
};

const GUIDES: GuideCard[] = [
  {
    title: "Building a PC for the 40\u00B0C Cyprus Summer",
    excerpt:
      "Air cooling often isn\u2019t enough in the Mediterranean heat. Discover why high-airflow mesh cases and 360mm AIOs are mandatory for high-end builds here.",
    href: "/guides/cyprus-summer-pc-build",
  },
  {
    title: "Why We Recommend Amazon.de for EU Builders",
    excerpt:
      "Stop paying surprise customs duties and 19% import VAT. Here is our guide to sourcing parts directly from Germany for the best prices and local warranties.",
    href: "/guides/amazon-de-shipping-guide",
  },
  {
    title: "The \u20AC1000\u20131200 1080p 144Hz \u201CSweet Spot\u201D Build (March 2026)",
    excerpt:
      "We analyze the current market to bring you the best price-to-performance ratio for a smooth 1080p 144Hz gaming PC.",
    href: "/guides/1000-euro-sweet-spot-build",
  },
];

export function EditorialSection() {
  return (
    <section className="border-t border-obsidian-border/50 py-24 px-4 bg-obsidian-surface/50">
      <div className="max-w-3xl mx-auto">
        <p className="text-xs text-obsidian uppercase tracking-[0.25em] text-center mb-4">
          Latest guides
        </p>
        <h2 className="font-display font-light text-4xl text-obsidian-text text-center mb-16">
          From the workshop
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-px bg-obsidian-border">
          {GUIDES.map((guide) => (
            <Link
              key={guide.href}
              href={guide.href}
              className="bg-obsidian-bg/65 p-8 flex flex-col hover:bg-obsidian-raised transition-colors group card-glow"
            >
              <h3 className="font-body font-semibold text-obsidian-text text-sm mb-3 group-hover:text-obsidian transition-colors leading-snug">
                {guide.title}
              </h3>
              <p className="text-obsidian-muted text-sm leading-relaxed flex-1">
                {guide.excerpt}
              </p>
              <span className="text-obsidian text-xs uppercase tracking-widest mt-6 font-body">
                Read more &rarr;
              </span>
            </Link>
          ))}
        </div>
      </div>
    </section>
  );
}
