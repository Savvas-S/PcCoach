import Link from "next/link";

export default function Home() {
  return (
    <main className="min-h-screen bg-gray-900 text-white">
      <div className="flex flex-col items-center justify-center min-h-screen px-4 text-center">
        <div className="mb-6 inline-flex items-center gap-2 rounded-full bg-blue-500/10 border border-blue-500/20 px-4 py-1.5 text-sm text-blue-400">
          AI-powered &bull; Free to use
        </div>

        <h1 className="text-5xl md:text-7xl font-bold mb-6 bg-gradient-to-b from-white to-gray-400 bg-clip-text text-transparent">
          Build Your Perfect PC
        </h1>

        <p className="text-xl text-gray-400 max-w-xl mb-10">
          Tell us your needs and budget. Get a full component list with the best
          prices from trusted European stores.
        </p>

        <div className="flex flex-col sm:flex-row gap-3">
          <Link
            href="/build"
            className="bg-blue-600 hover:bg-blue-500 text-white font-semibold px-8 py-4 rounded-xl text-lg transition-colors"
          >
            Build My PC &rarr;
          </Link>
          <Link
            href="/find"
            className="border border-gray-600 hover:border-gray-400 text-gray-300 hover:text-white font-semibold px-8 py-4 rounded-xl text-lg transition-colors"
          >
            Find a Component &rarr;
          </Link>
        </div>

        <div className="mt-20 grid grid-cols-1 md:grid-cols-3 gap-4 max-w-3xl w-full">
          {[
            {
              icon: "🤖",
              title: "AI Recommendations",
              desc: "AI picks the best parts for your exact needs",
            },
            {
              icon: "🛒",
              title: "Buy Links Included",
              desc: "Direct links to trusted stores — no searching required",
            },
            {
              icon: "⚡",
              title: "Instant Results",
              desc: "Get your full build list in under a minute",
            },
          ].map((f) => (
            <div
              key={f.title}
              className="bg-gray-800 rounded-xl p-6 text-left border border-gray-700"
            >
              <div className="text-3xl mb-3">{f.icon}</div>
              <h3 className="font-semibold text-white mb-1">{f.title}</h3>
              <p className="text-gray-400 text-sm">{f.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </main>
  );
}
