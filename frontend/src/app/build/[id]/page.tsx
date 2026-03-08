"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { getBuild } from "@/lib/api";
import type { BuildResult, ComponentRecommendation } from "@/lib/api";

const CATEGORY_LABELS: Record<string, string> = {
  cpu: "CPU",
  gpu: "GPU",
  motherboard: "Motherboard",
  ram: "RAM",
  storage: "Storage",
  psu: "Power Supply",
  case: "Case",
  cooling: "Cooling",
  monitor: "Monitor",
  keyboard: "Keyboard",
  mouse: "Mouse",
};

const SOURCE_LABELS: Record<string, string> = {
  amazon: "Amazon",
  computeruniverse: "ComputerUniverse",
  caseking: "Caseking",
};

function ComponentCard({ component }: { component: ComponentRecommendation }) {
  return (
    <div className="bg-gray-800 border border-gray-700 rounded-xl p-5">
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-2 flex-wrap">
            <span className="text-xs font-medium text-blue-400 bg-blue-500/10 px-2 py-0.5 rounded-full">
              {CATEGORY_LABELS[component.category] || component.category}
            </span>
            {component.affiliate_source && (
              <span className="text-xs text-gray-400 bg-gray-700 px-2 py-0.5 rounded-full">
                {SOURCE_LABELS[component.affiliate_source] ||
                  component.affiliate_source}
              </span>
            )}
          </div>
          <h3 className="font-semibold text-white">{component.name}</h3>
          <p className="text-gray-400 text-sm">{component.brand}</p>

          {Object.keys(component.specs).length > 0 && (
            <div className="mt-3 flex flex-wrap gap-2">
              {Object.entries(component.specs).map(([k, v]) => (
                <span
                  key={k}
                  className="text-xs text-gray-400 bg-gray-700/60 px-2 py-1 rounded-lg"
                >
                  {k}: {v}
                </span>
              ))}
            </div>
          )}
        </div>

        <div className="text-right shrink-0">
          <div className="text-xl font-bold text-white">
            &euro;{component.price_eur.toFixed(2)}
          </div>
          {component.affiliate_url && (
            <a
              href={component.affiliate_url}
              target="_blank"
              rel="noopener noreferrer"
              className="mt-2 inline-block bg-blue-600 hover:bg-blue-500 text-white text-sm px-4 py-2 rounded-lg transition-colors"
            >
              Buy &rarr;
            </a>
          )}
        </div>
      </div>
    </div>
  );
}

export default function BuildResultPage() {
  const params = useParams();
  const [build, setBuild] = useState<BuildResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const rawId = Array.isArray(params.id) ? params.id[0] : params.id;
    const id = Number(rawId);
    if (!id) return;

    // Use cached result from form submission to avoid a redundant GET request
    const cached = sessionStorage.getItem("build_result");
    if (cached) {
      try {
        const parsed: BuildResult = JSON.parse(cached);
        if (parsed.id === id) {
          sessionStorage.removeItem("build_result");
          setBuild(parsed);
          return;
        }
      } catch {
        // ignore malformed cache
      }
    }

    const controller = new AbortController();
    getBuild(id, controller.signal)
      .then(setBuild)
      .catch((err: Error) => {
        if (err.name !== "AbortError") setError(err.message);
      });
    return () => controller.abort();
  }, [params.id]);

  if (error) {
    return (
      <main className="min-h-screen bg-gray-900 text-white flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-400 mb-4">{error}</p>
          <Link href="/build" className="text-blue-400 hover:text-blue-300">
            &larr; Start a new build
          </Link>
        </div>
      </main>
    );
  }

  if (!build) {
    return (
      <main className="min-h-screen bg-gray-900 text-white flex items-center justify-center">
        <div className="text-center">
          <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-gray-400">Generating your build&hellip;</p>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-gray-900 text-white py-12 px-4">
      <div className="max-w-3xl mx-auto">
        <div className="mb-8">
          <Link href="/build" className="text-gray-400 hover:text-white text-sm">
            &larr; New Build
          </Link>
          <h1 className="text-3xl font-bold mt-4">Your Build</h1>
          {build.total_price_eur != null && (
            <p className="text-2xl text-blue-400 font-semibold mt-1">
              Total: &euro;{build.total_price_eur.toFixed(2)}
            </p>
          )}
        </div>

        {build.summary && (
          <div className="bg-gray-800 border border-gray-700 rounded-xl p-5 mb-8">
            <h2 className="font-semibold mb-2 text-gray-300">AI Summary</h2>
            <p className="text-gray-300 text-sm leading-relaxed">
              {build.summary}
            </p>
          </div>
        )}

        <div className="space-y-3">
          {build.components.map((c) => (
            <ComponentCard key={c.name} component={c} />
          ))}
        </div>

        <div className="mt-8">
          <Link
            href="/build"
            className="block text-center border border-gray-700 hover:border-gray-500 text-gray-300 hover:text-white py-3 rounded-xl transition-colors"
          >
            Start New Build
          </Link>
        </div>
      </div>
    </main>
  );
}
