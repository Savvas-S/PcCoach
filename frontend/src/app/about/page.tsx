import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "About — PcCoach",
  description: "Learn how PcCoach helps you build the perfect PC with AI-powered recommendations.",
};

export default function AboutPage() {
  return (
    <main className="min-h-screen bg-obsidian-bg py-12 px-4">
      <div className="max-w-2xl mx-auto">
        <div className="mb-12">
          <Link href="/" className="text-obsidian-muted hover:text-obsidian-text text-xs uppercase tracking-widest transition-colors">
            &larr; Home
          </Link>
          <h1 className="font-display font-light text-5xl text-obsidian-text mt-6">About PcCoach</h1>
          <p className="text-obsidian-muted mt-3">
            Your AI-powered PC building assistant for the Cyprus market.
          </p>
        </div>

        <div className="space-y-12 text-obsidian-muted leading-relaxed">
          <section>
            <h2 className="font-display font-normal text-2xl text-obsidian-text mb-4">What is PcCoach?</h2>
            <p>
              PcCoach is a free tool that helps you build the ideal PC for your needs and budget.
              You tell us what you want — gaming, creative work, everyday use — and our AI
              generates a tailored component list with direct links to buy each part from trusted
              European retailers.
            </p>
            <p className="mt-3">
              No sign-up required. No upsells. Just instant, honest recommendations.
            </p>
          </section>

          <section>
            <h2 className="font-display font-normal text-2xl text-obsidian-text mb-6">How It Works</h2>
            <div className="space-y-px bg-obsidian-border">
              {[
                { step: "1", title: "Tell us your needs", desc: "Choose your budget, use case, and preferences — brand, form factor, parts you already own." },
                { step: "2", title: "AI builds your list", desc: "Our AI analyses thousands of components and picks the best combination for your exact requirements." },
                { step: "3", title: "Click and buy", desc: "Each component comes with a direct link to a retailer. No searching, no guesswork." },
              ].map((item) => (
                <div key={item.step} className="flex gap-5 bg-obsidian-surface p-6">
                  <div className="font-mono text-obsidian text-sm w-6 shrink-0 pt-0.5">{item.step}</div>
                  <div>
                    <div className="font-body font-semibold text-obsidian-text">{item.title}</div>
                    <div className="text-obsidian-muted text-sm mt-1">{item.desc}</div>
                  </div>
                </div>
              ))}
            </div>
          </section>

          <section id="affiliate-disclosure">
            <h2 className="font-display font-normal text-2xl text-obsidian-text mb-4">Affiliate Disclosure</h2>
            <p>
              PcCoach is free to use. We earn a small commission when you purchase through our
              affiliate links — at no extra cost to you. We participate in affiliate programmes
              with <strong className="text-obsidian-text">Amazon</strong>,{" "}
              <strong className="text-obsidian-text">ComputerUniverse</strong>, and{" "}
              <strong className="text-obsidian-text">Caseking</strong>.
            </p>
            <p className="mt-3">
              Affiliate relationships do not influence which products the AI recommends.
              Recommendations are driven entirely by your stated requirements and budget.
            </p>
            <p className="mt-3">As an Amazon Associate we earn from qualifying purchases.</p>
          </section>

          <section>
            <h2 className="font-display font-normal text-2xl text-obsidian-text mb-4">Who We Are</h2>
            <p>
              PcCoach is built and operated from Limassol, Cyprus. We focus on the local and
              European market, sourcing prices and availability from retailers that ship to Cyprus.
            </p>
            <p className="mt-3">
              Have a question or feedback?{" "}
              <Link href="/contact" className="text-obsidian hover:brightness-110 underline">
                Get in touch
              </Link>
              .
            </p>
          </section>

          <section className="border-t border-obsidian-border pt-8">
            <h2 className="text-xs font-body uppercase tracking-widest text-obsidian-muted mb-4">Legal</h2>
            <div className="flex flex-wrap gap-x-6 gap-y-2 text-sm">
              <Link href="/privacy" className="text-obsidian hover:brightness-110 underline">Privacy Policy</Link>
              <Link href="/terms" className="text-obsidian hover:brightness-110 underline">Terms of Service</Link>
              <Link href="/contact" className="text-obsidian hover:brightness-110 underline">Contact</Link>
            </div>
          </section>
        </div>
      </div>
    </main>
  );
}
