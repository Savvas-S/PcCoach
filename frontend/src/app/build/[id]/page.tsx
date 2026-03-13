"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { getBuild, SOURCE_LABELS } from "@/lib/api";
import { safeAffiliateUrl } from "@/lib/url";
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
    <div className="bg-obsidian-surface border border-obsidian-border p-5 hover:border-obsidian-bright transition-colors">
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <span className="text-xs font-body text-obsidian border border-obsidian/30 px-2 py-0.5 uppercase tracking-wider">
            {label}
          </span>
          <h3 className="font-body font-semibold text-obsidian-text mt-3 leading-snug">{component.name}</h3>
          <p className="text-obsidian-muted text-sm mt-0.5">{component.brand}</p>

          {specs.length > 0 && (
            <div className="mt-3 flex flex-wrap gap-1.5">
              {specs.map(([k, v]) => (
                <span
                  key={k}
                  className="font-mono text-xs text-obsidian-muted border border-obsidian-border px-2 py-1"
                >
                  <span className="text-obsidian-muted-light">{formatSpecKey(k)}:</span> {v}
                </span>
              ))}
            </div>
          )}
        </div>

        <div className="text-right shrink-0 flex flex-col items-end gap-3">
          {/* TODO: remove ~ when real product URLs land */}
          <div className="font-mono text-xl font-medium text-obsidian">
            ~&euro;{component.price_eur.toFixed(0)}
          </div>
          {safeAffiliateUrl(component.affiliate_url) ? (
            <a
              href={safeAffiliateUrl(component.affiliate_url)!}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-block bg-obsidian text-obsidian-bg font-body font-semibold text-xs px-4 py-2 hover:brightness-110 transition-all whitespace-nowrap uppercase tracking-wide"
            >
              {component.affiliate_source
                ? `${SOURCE_LABELS[component.affiliate_source]} \u2192`
                : "Check price \u2192"}
            </a>
          ) : (
            <span className="text-xs text-obsidian-muted-light">No link yet</span>
          )}
        </div>
      </div>
    </div>
  );
}

function UpgradeCard({ suggestion }: { suggestion: UpgradeSuggestion }) {
  return (
    <div className="bg-amber-950/30 border border-amber-800/30 p-5">
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-3">
            <span className="text-xs text-amber-400 border border-amber-700/40 px-2 py-0.5 uppercase tracking-wider">
              Optional upgrade
            </span>
            <span className="font-mono text-xs text-obsidian-muted border border-obsidian-border px-2 py-0.5">
              {CATEGORY_LABELS[suggestion.component_category] || suggestion.component_category}
            </span>
          </div>
          <p className="text-obsidian-text font-semibold">{suggestion.upgrade_name}</p>
          <p className="text-obsidian-muted text-sm mt-0.5">Replaces the {suggestion.current_name}</p>
          <p className="text-obsidian-text text-sm mt-2">{suggestion.reason}</p>
        </div>
        <div className="text-right shrink-0 flex flex-col items-end gap-3">
          <div className="font-mono text-lg font-medium text-amber-400">
            ~+&euro;{suggestion.extra_cost_eur.toFixed(0)}
          </div>
          {safeAffiliateUrl(suggestion.affiliate_url) && (
            <a
              href={safeAffiliateUrl(suggestion.affiliate_url)!}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-block bg-amber-700 hover:bg-amber-600 text-white text-xs font-semibold px-4 py-2 uppercase tracking-wide transition-colors whitespace-nowrap"
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
    <div className="bg-green-950/30 border border-green-800/30 p-5">
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-3">
            <span className="text-xs text-green-400 border border-green-700/40 px-2 py-0.5 uppercase tracking-wider">
              Budget alternative
            </span>
            <span className="font-mono text-xs text-obsidian-muted border border-obsidian-border px-2 py-0.5">
              {CATEGORY_LABELS[suggestion.component_category] || suggestion.component_category}
            </span>
          </div>
          <p className="text-obsidian-text font-semibold">{suggestion.downgrade_name}</p>
          <p className="text-obsidian-muted text-sm mt-0.5">Replaces the {suggestion.current_name}</p>
          <p className="text-obsidian-text text-sm mt-2">{suggestion.reason}</p>
        </div>
        <div className="text-right shrink-0 flex flex-col items-end gap-3">
          <div className="font-mono text-lg font-medium text-green-400">
            Save ~&euro;{suggestion.savings_eur.toFixed(0)}
          </div>
          {safeAffiliateUrl(suggestion.affiliate_url) && (
            <a
              href={safeAffiliateUrl(suggestion.affiliate_url)!}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-block bg-green-700 hover:bg-green-600 text-white text-xs font-semibold px-4 py-2 uppercase tracking-wide transition-colors whitespace-nowrap"
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
    <h2 className="text-xs font-body uppercase tracking-[0.2em] text-obsidian-muted mb-4">
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
      setCopied("failed");
      setTimeout(() => setCopied("idle"), 3000);
    }
  };

  useEffect(() => {
    const id = Array.isArray(params.id) ? params.id[0] : params.id;
    if (!id) return;

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
    const isExpired = error === "Build not found";
    return (
      <main className="min-h-screen bg-obsidian-bg flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-400 mb-2">
            {isExpired ? "This build link has expired." : error}
          </p>
          {isExpired && (
            <p className="text-obsidian-muted text-sm mb-4">
              Builds are held in memory and cleared after inactivity. Start a new one below.
            </p>
          )}
          <Link href="/build" className="text-obsidian hover:brightness-110 text-sm font-body">
            &larr; Start a new build
          </Link>
        </div>
      </main>
    );
  }

  if (!build) {
    return (
      <main className="min-h-screen bg-obsidian-bg flex items-center justify-center">
        <div className="text-center">
          <div className="w-8 h-8 border border-obsidian-bright border-t-obsidian rounded-full animate-spin mx-auto mb-5" />
          <p className="text-obsidian-muted text-sm font-body">Loading your build&hellip;</p>
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
    <main className="min-h-screen bg-obsidian-bg py-12 px-4">
      <div className="max-w-3xl mx-auto">

        {/* Navigation */}
        <div className="flex items-center justify-between gap-4 mb-12">
          <Link
            href="/build"
            className="text-obsidian-muted hover:text-obsidian-text text-xs uppercase tracking-widest transition-colors"
          >
            &larr; New Build
          </Link>
          <button
            onClick={handleCopyLink}
            className="text-xs text-obsidian-muted hover:text-obsidian-text border border-obsidian-border hover:border-obsidian-bright px-4 py-2 uppercase tracking-widest transition-colors"
          >
            {copyLabel}
          </button>
        </div>

        {/* Header */}
        <div className="mb-10">
          <h1 className="font-display font-light text-5xl text-obsidian-text">Your PC Build</h1>
          {build.total_price_eur != null && (
            <div className="flex items-baseline gap-3 mt-3 flex-wrap">
              {/* TODO: when real product URLs land, remove ~ and toFixed(0) → toFixed(2) */}
              <span className="font-mono text-3xl font-medium text-obsidian">
                ~&euro;{build.total_price_eur.toFixed(0)}
              </span>
              <span className="text-obsidian-muted text-sm">
                estimated total &middot;{" "}
                {build.components.length} component{build.components.length !== 1 ? "s" : ""}
              </span>
            </div>
          )}
        </div>

        {/* Why this build */}
        {build.summary && (
          <div className="border border-obsidian/20 bg-obsidian/5 p-5 mb-8">
            <p className="text-xs font-body uppercase tracking-[0.2em] text-obsidian mb-3">
              Why this build
            </p>
            <p className="text-obsidian-muted text-sm leading-relaxed">{build.summary}</p>
          </div>
        )}

        {/* Core components */}
        {coreComponents.length > 0 && (
          <div className="mb-6">
            <SectionHeading>
              {peripheralComponents.length > 0 ? "Core components" : "What\u2019s included"}
            </SectionHeading>
            <div className="space-y-px bg-obsidian-border">
              {coreComponents.map((c) => (
                <ComponentCard key={c.category} component={c} />
              ))}
            </div>
          </div>
        )}

        {/* Peripherals */}
        {peripheralComponents.length > 0 && (
          <div className="mb-6">
            <SectionHeading>Peripherals</SectionHeading>
            <div className="space-y-px bg-obsidian-border">
              {peripheralComponents.map((c) => (
                <ComponentCard key={c.category} component={c} />
              ))}
            </div>
          </div>
        )}

        <p className="text-obsidian-muted-light text-xs mb-10 font-mono">
          Prices are AI estimates. Verify current prices on the store before ordering.
        </p>

        {/* Alternatives */}
        {(build.upgrade_suggestion || build.downgrade_suggestion) && (
          <div className="mb-10">
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
        <div className="border border-obsidian-border bg-obsidian-surface p-5 mb-8">
          <p className="font-body font-semibold text-obsidian-text mb-1">Ready to order?</p>
          <p className="text-obsidian-muted text-sm leading-relaxed">
            Click each component above to search for it on the store. Prices shown
            here are AI estimates — always confirm the current price before purchasing.
          </p>
        </div>

        {/* Footer CTAs */}
        <div className="flex gap-2">
          <button
            onClick={handleCopyLink}
            className="flex-1 border border-obsidian-border hover:border-obsidian-bright text-obsidian-muted hover:text-obsidian-text py-3 transition-colors text-xs uppercase tracking-widest"
          >
            {copyLabel}
          </button>
          <Link
            href="/build"
            className="flex-1 text-center border border-obsidian-border hover:border-obsidian-bright text-obsidian-muted hover:text-obsidian-text py-3 transition-colors text-xs uppercase tracking-widest"
          >
            Start New Build
          </Link>
        </div>

      </div>
    </main>
  );
}
