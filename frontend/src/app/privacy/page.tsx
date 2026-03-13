import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Privacy Policy — PcCoach",
  description: "How PcCoach collects, uses, and protects your data.",
};

export default function PrivacyPage() {
  return (
    <main className="min-h-screen bg-obsidian-bg py-12 px-4">
      <div className="max-w-2xl mx-auto">
        <div className="mb-10">
          <Link href="/" className="text-obsidian-muted hover:text-obsidian-text text-xs uppercase tracking-widest transition-colors">
            &larr; Home
          </Link>
          <h1 className="font-display font-light text-5xl text-obsidian-text mt-6">Privacy Policy</h1>
          <p className="text-obsidian-muted mt-3 text-sm">Last updated: March 2026</p>
        </div>

        <div className="space-y-10 text-obsidian-muted leading-relaxed">
          <section>
            <h2 className="font-display font-normal text-2xl text-obsidian-text mb-3">Overview</h2>
            <p>
              PcCoach (&ldquo;we&rdquo;, &ldquo;us&rdquo;, &ldquo;our&rdquo;) is committed to protecting your privacy.
              This policy explains what data we collect when you use thepccoach.com, how we use it,
              and your rights regarding that data.
            </p>
          </section>

          <section>
            <h2 className="font-display font-normal text-2xl text-obsidian-text mb-3">Data We Collect</h2>
            <p className="mb-4">
              We collect only the minimum data necessary to provide the service:
            </p>
            <div className="space-y-px bg-obsidian-border">
              {[
                {
                  title: "Build preferences",
                  desc: "Your selected budget, use case, component preferences, and any notes you enter when submitting a build request. This data is stored to generate and retrieve your build result.",
                },
                {
                  title: "No account data",
                  desc: "We do not require you to create an account. We do not collect your name, email address, or any other personal identifiers unless you voluntarily contact us by email.",
                },
              ].map((item) => (
                <div key={item.title} className="bg-obsidian-surface p-5">
                  <div className="font-body font-semibold text-obsidian-text mb-1">{item.title}</div>
                  <div className="text-obsidian-muted text-sm">{item.desc}</div>
                </div>
              ))}
            </div>
          </section>

          <section>
            <h2 className="font-display font-normal text-2xl text-obsidian-text mb-3">How We Use Your Data</h2>
            <ul className="list-disc list-inside space-y-2">
              <li>To generate your personalised PC build recommendation</li>
              <li>To allow you to retrieve a previously generated build via its unique link</li>
              <li>To monitor and maintain the performance and security of the service</li>
            </ul>
            <p className="mt-4">
              We do not sell, rent, or share your personal data with third parties for marketing
              purposes.
            </p>
          </section>

          <section>
            <h2 className="font-display font-normal text-2xl text-obsidian-text mb-3">AI Processing</h2>
            <p>
              Build requests are processed by an AI model to generate component recommendations.
              The content of your request (budget, preferences, notes) is sent to Anthropic
              (anthropic.com) for this purpose. Anthropic&apos;s{" "}
              <a href="https://www.anthropic.com/legal/privacy" target="_blank" rel="noopener noreferrer" className="text-obsidian hover:brightness-110 underline">
                privacy policy
              </a>{" "}
              governs how they handle this data. We do not send any personally identifying
              information unless you include it in your notes field. Please avoid entering
              personal data in the notes field.
            </p>
          </section>

          <section>
            <h2 className="font-display font-normal text-2xl text-obsidian-text mb-3">Affiliate Links</h2>
            <p>
              PcCoach earns commission through affiliate links. When you click a &ldquo;Buy&rdquo; link and
              make a purchase, the retailer may set cookies on your device to attribute the sale.
              These cookies are governed by the respective retailer&apos;s privacy policy, not ours.
              We do not receive any personal data from these transactions — only an anonymised
              commission notification.
            </p>
          </section>

          <section>
            <h2 className="font-display font-normal text-2xl text-obsidian-text mb-3">Cookies</h2>
            <p>
              We do not use cookies. Third-party retailers linked from our site may set their own
              cookies when you visit them — please review their respective privacy policies.
            </p>
          </section>

          <section>
            <h2 className="font-display font-normal text-2xl text-obsidian-text mb-3">Data Retention</h2>
            <p>
              Build results are held temporarily in server memory to allow you to share or revisit
              them via a direct link. They are not permanently stored and may be cleared when the
              server is restarted or after a period of inactivity. If you would like your build data
              removed sooner, please{" "}
              <Link href="/contact" className="text-obsidian hover:brightness-110 underline">
                contact us
              </Link>
              .
            </p>
          </section>

          <section>
            <h2 className="font-display font-normal text-2xl text-obsidian-text mb-3">Your Rights</h2>
            <p className="mb-3">Under applicable data protection law, you have the right to:</p>
            <ul className="list-disc list-inside space-y-2">
              <li>Access the data we hold about you</li>
              <li>Request correction of inaccurate data</li>
              <li>Request deletion of your data</li>
              <li>Object to or restrict how we process your data</li>
            </ul>
            <p className="mt-4">
              To exercise any of these rights, please{" "}
              <Link href="/contact" className="text-obsidian hover:brightness-110 underline">
                contact us
              </Link>
              .
            </p>
          </section>

          <section>
            <h2 className="font-display font-normal text-2xl text-obsidian-text mb-3">Changes to This Policy</h2>
            <p>
              We may update this policy from time to time. The date at the top of this page
              reflects when it was last revised. Continued use of PcCoach after changes
              constitutes acceptance of the updated policy.
            </p>
          </section>

          <section>
            <h2 className="font-display font-normal text-2xl text-obsidian-text mb-3">Contact</h2>
            <p>
              For any privacy-related questions, please reach out via our{" "}
              <Link href="/contact" className="text-obsidian hover:brightness-110 underline">
                contact page
              </Link>
              .
            </p>
          </section>
        </div>
      </div>
    </main>
  );
}
