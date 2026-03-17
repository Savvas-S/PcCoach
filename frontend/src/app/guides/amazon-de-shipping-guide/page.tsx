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

          <h2 className="font-body font-semibold text-obsidian-text text-base pt-2">
            No customs, no surprise VAT
          </h2>
          <p>
            Since Germany and Cyprus are both EU member states, goods ship under the
            single-market rules &mdash; no customs declarations, no import duties, and
            no surprise 19% VAT on top of what you already paid. The price you see at
            checkout is the price you pay.
          </p>

          <h2 className="font-body font-semibold text-obsidian-text text-base pt-2">
            One of the most trusted retailers in the world
          </h2>
          <p>
            Amazon is consistently rated as one of the most trusted online retailers
            globally. Millions of verified customer reviews help you make informed
            decisions &mdash; you can see real feedback from people who bought the
            exact same component before clicking &ldquo;add to cart.&rdquo;
          </p>
          <p>
            Their A-to-Z Guarantee means you&rsquo;re protected on every purchase. If
            something arrives damaged or doesn&rsquo;t match the listing, Amazon
            handles returns and refunds quickly and without hassle.
          </p>

          <h2 className="font-body font-semibold text-obsidian-text text-base pt-2">
            Fast, reliable shipping to Cyprus
          </h2>
          <p>
            Shipping to Cyprus typically takes 5&ndash;10 business days with standard
            delivery. Amazon&rsquo;s logistics network is among the most reliable in
            Europe &mdash; packages are tracked end-to-end, and delivery estimates are
            consistently accurate.
          </p>

          <h2 className="font-body font-semibold text-obsidian-text text-base pt-2">
            EU-wide warranty and returns
          </h2>
          <p>
            Amazon&rsquo;s return policy applies across all EU countries, and
            warranties are honored locally through the EU consumer protection
            directive. If a component fails within warranty, you deal with Amazon
            directly &mdash; no international shipping back to a random warehouse.
          </p>

          <h2 className="font-body font-semibold text-obsidian-text text-base pt-2">
            The widest selection of PC components
          </h2>
          <p>
            From the latest GPUs and CPUs to niche accessories like custom cables and
            fan splitters, Amazon.de stocks virtually everything you need for a
            complete build. Their marketplace also means you often find competitive
            prices from multiple sellers on the same listing.
          </p>

          <div className="border-t border-obsidian-border pt-8 mt-8">
            <p className="text-obsidian-muted text-xs">
              Full article coming soon. In the meantime,{" "}
              <Link href="/build" className="text-obsidian hover:brightness-110">
                build your PC
              </Link>{" "}
              and we&rsquo;ll link you directly to Amazon.de for each part.
            </p>
          </div>
        </div>
      </article>
    </main>
  );
}
