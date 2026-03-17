import Link from "next/link";

export const metadata = {
  title: "Why We Recommend Amazon.de for EU Builders | The PC Coach",
  description:
    "How to source PC parts from Germany with no surprise customs duties or import VAT for EU buyers.",
};

export default function AmazonDeShippingGuide() {
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
          Why We Recommend Amazon.de for EU Builders
        </h1>

        <p className="text-obsidian-muted text-sm mb-10 font-mono uppercase tracking-widest">
          March 2026 &middot; 6 min read
        </p>

        <div className="space-y-6 text-obsidian-text text-sm leading-relaxed">
          <p>
            Ordering PC components from the US or UK might seem tempting, but for
            buyers in Cyprus and the rest of the EU, Amazon.de is almost always the
            smarter choice. Here&rsquo;s why.
          </p>
          <p>
            Since Germany and Cyprus are both EU member states, goods ship under the
            single-market rules &mdash; no customs declarations, no import duties, and
            no surprise 19% VAT on top of what you already paid. The price you see at
            checkout is the price you pay.
          </p>
          <p>
            Shipping to Cyprus typically takes 5&ndash;10 business days with standard
            delivery, and Amazon&rsquo;s return policy applies across all EU countries.
            Warranties are honored locally through the EU consumer protection
            directive.
          </p>
          <p>
            We also compare against other EU retailers like ComputerUniverse and
            Caseking when their prices beat Amazon &mdash; but for the widest
            selection and fastest delivery, Amazon.de is our default recommendation.
          </p>

          <div className="border-t border-obsidian-border pt-8 mt-8">
            <p className="text-obsidian-muted text-xs">
              Full article coming soon. In the meantime,{" "}
              <Link href="/build" className="text-obsidian hover:brightness-110">
                build your PC
              </Link>{" "}
              and we&rsquo;ll link you directly to the best EU store for each part.
            </p>
          </div>
        </div>
      </article>
    </main>
  );
}
