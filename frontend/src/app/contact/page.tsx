import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Contact & Support — PcCoach",
  description: "Get in touch with the PcCoach team or find answers to common questions.",
};

const FAQ = [
  { q: "Is PcCoach free to use?", a: "Yes, completely free. We earn a small affiliate commission when you buy through our links, which keeps the service running at no cost to you." },
  { q: "Do I need to create an account?", a: "No. There is no sign-up or login required. Simply fill in the form and get your build instantly." },
  { q: "How accurate are the prices shown?", a: "Prices are estimates provided by our AI based on current market data. Actual prices at checkout may vary. Always check the retailer's listing before purchasing." },
  { q: "Can I save or share my build?", a: "Yes. Every build has a unique URL that you can bookmark or share with others." },
  { q: "Do the affiliate links cost me anything extra?", a: "No. The price you pay at the retailer is exactly the same whether you arrive via our link or directly." },
  { q: "My recommended component is out of stock — what do I do?", a: "Contact us and we'll generate an alternative recommendation, or simply start a new build with a note specifying the component you'd like to replace." },
  { q: "Can PcCoach help me upgrade an existing PC?", a: "Yes. On the build form, select the parts you already own under \"Parts You Already Own\" and we'll skip recommending those." },
  { q: "Which countries does PcCoach cover?", a: "We focus primarily on Cyprus and the broader European market. Retailers and pricing are selected based on availability in the region." },
];

export default function ContactPage() {
  return (
    <main className="min-h-screen bg-obsidian-bg py-12 px-4">
      <div className="max-w-2xl mx-auto">
        <div className="mb-12">
          <Link href="/" className="text-obsidian-muted hover:text-obsidian-text text-xs uppercase tracking-widest transition-colors">
            &larr; Home
          </Link>
          <h1 className="font-display font-light text-5xl text-obsidian-text mt-6">Contact & Support</h1>
          <p className="text-obsidian-muted mt-3">
            We&apos;re happy to help — reach out or browse the FAQ below.
          </p>
        </div>

        {/* Contact details */}
        <section className="mb-14">
          <h2 className="font-display font-normal text-2xl text-obsidian-text mb-6">Get in Touch</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-px bg-obsidian-border">
            <div className="bg-obsidian-surface p-6">
              <div className="text-xs text-obsidian-muted uppercase tracking-widest mb-3">General enquiries</div>
              <a href="mailto:info@thepccoach.com" className="text-obsidian hover:brightness-110 font-body font-medium">
                info@thepccoach.com
              </a>
              <p className="text-obsidian-muted text-xs mt-2">Questions, feedback, or anything else.</p>
            </div>
            <div className="bg-obsidian-surface p-6">
              <div className="text-xs text-obsidian-muted uppercase tracking-widest mb-3">Support</div>
              <a href="mailto:support@thepccoach.com" className="text-obsidian hover:brightness-110 font-body font-medium">
                support@thepccoach.com
              </a>
              <p className="text-obsidian-muted text-xs mt-2">Build issues. We aim to respond within 1 business day.</p>
            </div>
          </div>
          <div className="bg-obsidian-surface border-x border-b border-obsidian-border p-6">
            <div className="text-xs text-obsidian-muted uppercase tracking-widest mb-3">Address</div>
            <p className="text-obsidian-text font-body font-medium">Limassol, Cyprus</p>
            <p className="text-obsidian-muted text-xs mt-2">
              For data requests, email with subject &ldquo;Data Request&rdquo;. See our{" "}
              <Link href="/privacy" className="text-obsidian hover:brightness-110 underline">Privacy Policy</Link>.
            </p>
          </div>
        </section>

        {/* FAQ */}
        <section>
          <h2 className="font-display font-normal text-2xl text-obsidian-text mb-6">Frequently Asked Questions</h2>
          <div className="space-y-px bg-obsidian-border">
            {FAQ.map((item) => (
              <div key={item.q} className="bg-obsidian-surface p-6">
                <div className="font-body font-semibold text-obsidian-text mb-2">{item.q}</div>
                <div className="text-obsidian-muted text-sm leading-relaxed">{item.a}</div>
              </div>
            ))}
          </div>
        </section>

        <div className="mt-12 border border-obsidian/20 p-8 text-center">
          <p className="font-display font-light text-2xl text-obsidian-text mb-2">Ready to build?</p>
          <p className="text-obsidian-muted text-sm mb-6">Get your personalised build in under a minute.</p>
          <Link
            href="/build"
            className="inline-block bg-obsidian text-obsidian-bg font-body font-semibold px-8 py-3 hover:brightness-110 transition-all"
          >
            Build My PC &rarr;
          </Link>
        </div>
      </div>
    </main>
  );
}
