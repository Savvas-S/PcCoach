"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { getBuild, SOURCE_LABELS } from "@/lib/api";
import type {
  AffiliateSource,
  BuildResult,
  ComponentCategory,
  ComponentRecommendation,
  DowngradeSuggestion,
  UpgradeSuggestion,
} from "@/lib/api";

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


// Acronyms that should not be title-cased
const SPEC_KEY_OVERRIDES: Record<string, string> = {
  tdp: "TDP",
  rpm: "RPM",
  vram: "VRAM",
  pcie: "PCIe",
  ddr: "DDR",
};

function formatSpecKey(key: string): string {
  const lower = key.toLowerCase();
  if (SPEC_KEY_OVERRIDES[lower]) return SPEC_KEY_OVERRIDES[lower];
  return key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

const PERIPHERAL_CATEGORIES = new Set<ComponentCategory>(["monitor", "keyboard", "mouse"]);

function ComponentCard({ component }: { component: ComponentRecommendation }) {
  const label = CATEGORY_LABELS[component.category] || component.category;
  const specs = Object.entries(component.specs);

  return (
    <div className="bg-gray-800 border border-gray-700 rounded-xl p-5 hover:border-gray-600 transition-colors">
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <span className="text-xs font-medium text-blue-400 bg-blue-500/10 px-2 py-0.5 rounded-full">
            {label}
          </span>
          <h3 className="font-semibold text-white mt-2 leading-snug">{component.name}</h3>
          <p className="text-gray-500 text-sm">{component.brand}</p>

          {specs.length > 0 && (
            <div className="mt-3 flex flex-wrap gap-1.5">
              {specs.map(([k, v]) => (
                <span
                  key={k}
                  className="text-xs text-gray-400 bg-gray-700/60 px-2 py-1 rounded-md"
                >
                  <span className="text-gray-500">{formatSpecKey(k)}:</span> {v}
                </span>
              ))}
            </div>
          )}
        </div>

        <div className="text-right shrink-0 flex flex-col items-end gap-2">
          {/* TODO: remove ~ when real product URLs land */}
          <div className="text-xl font-bold text-white">
            ~&euro;{component.price_eur.toFixed(0)}
          </div>
          {component.affiliate_url ? (
            <a
              href={component.affiliate_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-block bg-blue-600 hover:bg-blue-500 text-white text-sm px-4 py-2 rounded-lg transition-colors whitespace-nowrap font-medium"
            >
              {component.affiliate_source
                ? `${SOURCE_LABELS[component.affiliate_source]} \u2192`
                : "Check price \u2192"}
            </a>
          ) : (
            <span className="text-xs text-gray-600">No link yet</span>
          )}
        </div>
      </div>
    </div>
  );
}

function UpgradeCard({ suggestion }: { suggestion: UpgradeSuggestion }) {
  return (
    <div className="bg-amber-500/10 border border-amber-500/30 rounded-xl p-5">
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-xs font-medium text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded-full">
              Optional upgrade
            </span>
            <span className="text-xs text-gray-500 bg-gray-700/60 px-2 py-0.5 rounded-full">
              {CATEGORY_LABELS[suggestion.component_category] || suggestion.component_category}
            </span>
          </div>
          <p className="text-white font-semibold">{suggestion.upgrade_name}</p>
          <p className="text-gray-500 text-sm mt-0.5">
            Replaces the {suggestion.current_name}
          </p>
          <p className="text-gray-300 text-sm mt-2">{suggestion.reason}</p>
        </div>
        <div className="text-right shrink-0 flex flex-col items-end gap-2">
          <div className="text-lg font-bold text-amber-400">
            +&euro;{suggestion.extra_cost_eur.toFixed(0)}
          </div>
          {suggestion.affiliate_url && (
            <a
              href={suggestion.affiliate_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-block bg-amber-600 hover:bg-amber-500 text-white text-sm px-4 py-2 rounded-lg transition-colors whitespace-nowrap"
            >
              {suggestion.affiliate_source
                ? `${SOURCE_LABELS[suggestion.affiliate_source]} \u2192`
                : "Check price \u2192"}
            </a>
          )}
        </div>
      </div>
    </div>
  );
}

function DowngradeCard({ suggestion }: { suggestion: DowngradeSuggestion }) {
  return (
    <div className="bg-green-500/10 border border-green-500/30 rounded-xl p-5">
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-xs font-medium text-green-400 bg-green-500/10 px-2 py-0.5 rounded-full">
              Budget alternative
            </span>
            <span className="text-xs text-gray-500 bg-gray-700/60 px-2 py-0.5 rounded-full">
              {CATEGORY_LABELS[suggestion.component_category] || suggestion.component_category}
            </span>
          </div>
          <p className="text-white font-semibold">{suggestion.downgrade_name}</p>
          <p className="text-gray-500 text-sm mt-0.5">
            Replaces the {suggestion.current_name}
          </p>
          <p className="text-gray-300 text-sm mt-2">{suggestion.reason}</p>
        </div>
        <div className="text-right shrink-0 flex flex-col items-end gap-2">
          <div className="text-lg font-bold text-green-400">
            Save ~&euro;{suggestion.savings_eur.toFixed(0)}
          </div>
          {suggestion.affiliate_url && (
            <a
              href={suggestion.affiliate_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-block bg-green-700 hover:bg-green-600 text-white text-sm px-4 py-2 rounded-lg transition-colors whitespace-nowrap"
            >
              {suggestion.affiliate_source
                ? `${SOURCE_LABELS[suggestion.affiliate_source]} \u2192`
                : "Check price \u2192"}
            </a>
          )}
        </div>
      </div>
    </div>
  );
}

function SectionHeading({ children }: { children: React.ReactNode }) {
  return (
    <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
      {children}
    </h2>
  );
}

export default function BuildResultPage() {
  const params = useParams();
  const [build, setBuild] = useState<BuildResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState<"idle" | "success" | "failed">("idle");

  const handleCopyLink = async () => {
    try {
      await navigator.clipboard.writeText(window.location.href);
      setCopied("success");
      setTimeout(() => setCopied("idle"), 2000);
    } catch {
      // Clipboard API unavailable (non-HTTPS or blocked) — prompt user to copy manually
      setCopied("failed");
      setTimeout(() => setCopied("idle"), 3000);
    }
  };

  useEffect(() => {
    const id = Array.isArray(params.id) ? params.id[0] : params.id;
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
    const timeout = setTimeout(() => controller.abort(), 30_000);
    getBuild(id, controller.signal)
      .then(setBuild)
      .catch((err: Error) => {
        if (err.name !== "AbortError") setError(err.message);
      })
      .finally(() => clearTimeout(timeout));
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

  const coreComponents = build.components.filter(
    (c) => !PERIPHERAL_CATEGORIES.has(c.category)
  );
  const peripheralComponents = build.components.filter((c) =>
    PERIPHERAL_CATEGORIES.has(c.category)
  );

  const copyLabel =
    copied === "success"
      ? "Link copied \u2713"
      : copied === "failed"
      ? "Copy the URL manually"
      : "Share this build";

  return (
    <main className="min-h-screen bg-gray-900 text-white py-12 px-4">
      <div className="max-w-3xl mx-auto">

        {/* Navigation */}
        <div className="flex items-center justify-between gap-4 mb-10">
          <Link
            href="/build"
            className="text-gray-400 hover:text-white text-sm transition-colors"
          >
            &larr; New Build
          </Link>
          <button
            onClick={handleCopyLink}
            className="text-sm text-gray-400 hover:text-white border border-gray-700 hover:border-gray-500 px-3 py-1.5 rounded-lg transition-colors"
          >
            {copyLabel}
          </button>
        </div>

        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold">Your PC Build</h1>
          {build.total_price_eur != null && (
            <div className="flex items-baseline gap-3 mt-2 flex-wrap">
              {/* TODO: when real product URLs land, remove ~ and toFixed(0) → toFixed(2) */}
              <span className="text-3xl font-bold text-blue-400">
                ~&euro;{build.total_price_eur.toFixed(0)}
              </span>
              <span className="text-gray-500 text-sm">
                estimated total &middot;{" "}
                {build.components.length} component{build.components.length !== 1 ? "s" : ""}
              </span>
            </div>
          )}
        </div>

        {/* Why this build — summary from the AI */}
        {build.summary && (
          <div className="rounded-xl border border-blue-500/20 bg-blue-500/5 p-5 mb-8">
            <p className="text-xs font-semibold text-blue-400 uppercase tracking-wider mb-2">
              Why this build
            </p>
            <p className="text-gray-200 text-sm leading-relaxed">{build.summary}</p>
          </div>
        )}

        {/* Core components */}
        {coreComponents.length > 0 && (
          <div className="mb-6">
            <SectionHeading>
              {peripheralComponents.length > 0 ? "Core components" : "What\u2019s included"}
            </SectionHeading>
            <div className="space-y-3">
              {/* Claude produces at most one component per category, so category is a stable unique key */}
              {coreComponents.map((c) => (
                <ComponentCard key={c.category} component={c} />
              ))}
            </div>
          </div>
        )}

        {/* Peripherals — only shown when the user opted in */}
        {peripheralComponents.length > 0 && (
          <div className="mb-6">
            <SectionHeading>Peripherals</SectionHeading>
            <div className="space-y-3">
              {peripheralComponents.map((c) => (
                <ComponentCard key={c.category} component={c} />
              ))}
            </div>
          </div>
        )}

        {/* TODO: remove this disclaimer when real product URLs (Awin/Amazon PA API) are integrated */}
        <p className="text-gray-600 text-xs mb-8">
          Prices are AI estimates. Verify current prices on the store before ordering.
        </p>

        {/* Alternatives */}
        {(build.upgrade_suggestion || build.downgrade_suggestion) && (
          <div className="mb-8">
            <SectionHeading>Alternatives to consider</SectionHeading>
            <div className="space-y-3">
              {build.upgrade_suggestion && (
                <UpgradeCard suggestion={build.upgrade_suggestion} />
              )}
              {build.downgrade_suggestion && (
                <DowngradeCard suggestion={build.downgrade_suggestion} />
              )}
            </div>
          </div>
        )}

        {/* Ready to order callout */}
        <div className="border border-gray-700 rounded-xl p-5 mb-6">
          <p className="font-semibold text-white mb-1">Ready to order?</p>
          <p className="text-gray-400 text-sm leading-relaxed">
            Click each component above to search for it on the store. Prices shown
            here are AI estimates — always confirm the current price on the store
            before purchasing.
          </p>
        </div>

        {/* Footer CTAs */}
        <div className="flex gap-3">
          <button
            onClick={handleCopyLink}
            className="flex-1 border border-gray-700 hover:border-gray-500 text-gray-300 hover:text-white py-3 rounded-xl transition-colors text-sm"
          >
            {copyLabel}
          </button>
          <Link
            href="/build"
            className="flex-1 text-center border border-gray-700 hover:border-gray-500 text-gray-300 hover:text-white py-3 rounded-xl transition-colors text-sm"
          >
            Start New Build
          </Link>
        </div>

      </div>
    </main>
  );
}
