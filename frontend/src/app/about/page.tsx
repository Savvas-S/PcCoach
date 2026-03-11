import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "About — PcCoach",
  description: "Learn how PcCoach helps you build the perfect PC with AI-powered recommendations.",
};

export default function AboutPage() {
  return (
    <main className="min-h-screen bg-gray-900 text-white py-12 px-4">
      <div className="max-w-2xl mx-auto">
        <div className="mb-10">
          <Link href="/" className="text-gray-400 hover:text-white text-sm">
            &larr; Home
          </Link>
          <h1 className="text-4xl font-bold mt-4">About PcCoach</h1>
          <p className="text-gray-400 mt-2">
            Your AI-powered PC building assistant for the Cyprus market.
          </p>
        </div>

        <div className="space-y-10 text-gray-300 leading-relaxed">
          <section>
            <h2 className="text-xl font-semibold text-white mb-3">What is PcCoach?</h2>
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
            <h2 className="text-xl font-semibold text-white mb-3">How It Works</h2>
            <div className="space-y-4">
              {[
                {
                  step: "1",
                  title: "Tell us your needs",
                  desc: "Choose your budget, use case, and preferences — brand, form factor, parts you already own.",
                },
                {
                  step: "2",
                  title: "AI builds your list",
                  desc: "Our AI analyses thousands of components and picks the best combination for your exact requirements.",
                },
                {
                  step: "3",
                  title: "Click and buy",
                  desc: "Each component comes with a direct link to a retailer. No searching, no guesswork.",
                },
              ].map((item) => (
                <div key={item.step} className="flex gap-4 bg-gray-800 border border-gray-700 rounded-xl p-5">
                  <div className="w-8 h-8 rounded-full bg-blue-500/20 border border-blue-500/30 text-blue-400 font-bold text-sm flex items-center justify-center shrink-0">
                    {item.step}
                  </div>
                  <div>
                    <div className="font-semibold text-white">{item.title}</div>
                    <div className="text-gray-400 text-sm mt-1">{item.desc}</div>
                  </div>
                </div>
              ))}
            </div>
          </section>

          <section id="affiliate-disclosure">
            <h2 className="text-xl font-semibold text-white mb-3">Affiliate Disclosure</h2>
            <p>
              PcCoach is free to use. We earn a small commission when you purchase through our
              affiliate links — at no extra cost to you. We participate in affiliate programmes
              with <strong className="text-white">Amazon</strong>,{" "}
              <strong className="text-white">ComputerUniverse</strong>, and{" "}
              <strong className="text-white">Caseking</strong>. This commission keeps the service
              running.
            </p>
            <p className="mt-3">
              Affiliate relationships do not influence which products the AI recommends.
              Recommendations are driven entirely by your stated requirements and budget.
              The price you pay at the retailer is the same whether you arrive via our link or directly.
            </p>
            <p className="mt-3">
              As an Amazon Associate we earn from qualifying purchases.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-3">Who We Are</h2>
            <p>
              PcCoach is built and operated from Limassol, Cyprus. We focus on the local and
              European market, sourcing prices and availability from retailers that ship to Cyprus.
            </p>
            <p className="mt-3">
              Have a question or feedback?{" "}
              <Link href="/contact" className="text-blue-400 hover:text-blue-300 underline">
                Get in touch
              </Link>
              .
            </p>
          </section>

          <section className="border-t border-gray-800 pt-8">
            <h2 className="text-base font-semibold text-white mb-3">Legal</h2>
            <div className="flex flex-wrap gap-x-6 gap-y-2 text-sm">
              <Link href="/privacy" className="text-blue-400 hover:text-blue-300 underline">Privacy Policy</Link>
              <Link href="/terms" className="text-blue-400 hover:text-blue-300 underline">Terms of Service</Link>
              <Link href="/contact" className="text-blue-400 hover:text-blue-300 underline">Contact</Link>
            </div>
          </section>
        </div>
      </div>
    </main>
  );
}
