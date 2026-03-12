import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Contact & Support — PcCoach",
  description: "Get in touch with the PcCoach team or find answers to common questions.",
};

const FAQ = [
  {
    q: "Is PcCoach free to use?",
    a: "Yes, completely free. We earn a small affiliate commission when you buy through our links, which keeps the service running at no cost to you.",
  },
  {
    q: "Do I need to create an account?",
    a: "No. There is no sign-up or login required. Simply fill in the form and get your build instantly.",
  },
  {
    q: "How accurate are the prices shown?",
    a: "Prices are estimates provided by our AI based on current market data. Actual prices at checkout may vary. Always check the retailer's listing before purchasing.",
  },
  {
    q: "Can I save or share my build?",
    a: "Yes. Every build has a unique URL that you can bookmark or share with others.",
  },
  {
    q: "Do the affiliate links cost me anything extra?",
    a: "No. The price you pay at the retailer is exactly the same whether you arrive via our link or directly.",
  },
  {
    q: "My recommended component is out of stock — what do I do?",
    a: "Contact us and we'll generate an alternative recommendation, or simply start a new build with a note specifying the component you'd like to replace.",
  },
  {
    q: "Can PcCoach help me upgrade an existing PC?",
    a: "Yes. On the build form, select the parts you already own under \"Parts You Already Own\" and we'll skip recommending those.",
  },
  {
    q: "Which countries does PcCoach cover?",
    a: "We focus primarily on Cyprus and the broader European market. Retailers and pricing are selected based on availability in the region.",
  },
];

export default function ContactPage() {
  return (
    <main className="min-h-screen bg-gray-900 text-white py-12 px-4">
      <div className="max-w-2xl mx-auto">
        <div className="mb-10">
          <Link href="/" className="text-gray-400 hover:text-white text-sm">
            &larr; Home
          </Link>
          <h1 className="text-4xl font-bold mt-4">Contact & Support</h1>
          <p className="text-gray-400 mt-2">
            We&apos;re happy to help — reach out or browse the FAQ below.
          </p>
        </div>

        {/* Contact details */}
        <section className="mb-12">
          <h2 className="text-xl font-semibold text-white mb-4">Get in Touch</h2>
          <div className="bg-gray-800 border border-gray-700 rounded-xl p-5">
            <div className="text-sm text-gray-400 mb-1">Email</div>
            <a
              href="mailto:support@thepccoach.com"
              className="text-blue-400 hover:text-blue-300 font-medium"
            >
              support@thepccoach.com
            </a>
            <p className="text-gray-500 text-xs mt-2">
              We aim to respond within 1 business day.
            </p>
          </div>

          <div className="bg-gray-800 border border-gray-700 rounded-xl p-5 mt-4">
            <div className="text-sm text-gray-400 mb-1">Address</div>
            <p className="text-white font-medium">Limassol, Cyprus</p>
            <p className="text-gray-500 text-xs mt-2">
              For privacy or data requests, email us with the subject line &ldquo;Data Request&rdquo;.
              See our{" "}
              <Link href="/privacy" className="text-blue-400 hover:text-blue-300 underline">
                Privacy Policy
              </Link>{" "}
              for details on your rights.
            </p>
          </div>
        </section>

        {/* FAQ */}
        <section>
          <h2 className="text-xl font-semibold text-white mb-4">Frequently Asked Questions</h2>
          <div className="space-y-3">
            {FAQ.map((item) => (
              <div
                key={item.q}
                className="bg-gray-800 border border-gray-700 rounded-xl p-5"
              >
                <div className="font-semibold text-white mb-2">{item.q}</div>
                <div className="text-gray-400 text-sm leading-relaxed">{item.a}</div>
              </div>
            ))}
          </div>
        </section>

        <div className="mt-12 bg-blue-500/10 border border-blue-500/20 rounded-xl p-5 text-center">
          <p className="text-gray-300 mb-3">Ready to build your PC?</p>
          <Link
            href="/build"
            className="inline-block bg-blue-600 hover:bg-blue-500 text-white font-semibold px-6 py-3 rounded-xl transition-colors"
          >
            Build My PC &rarr;
          </Link>
        </div>
      </div>
    </main>
  );
}
